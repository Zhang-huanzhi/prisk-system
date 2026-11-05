"""阶段 04：将 Diff 行映射到 Python 代码结构节点。"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, TypedDict

from .changes import load_records, write_jsonl


STRUCTURE_SCHEMA_VERSION = "stage04.v1"
PYTHON_ROLES = {"business", "test"}
PILOT_PR_NUMBERS = (179, 19, 226)


class ParsedStructure(TypedDict):
    status: str
    path: str
    side: str
    nodes: list[dict[str, Any]]
    error: dict[str, Any] | None


class StructureError(RuntimeError):
    """表示读取目标版本源码失败。"""


def _run_git(repo_path: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=False,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or b"git command failed").decode("utf-8", errors="replace").strip()
        raise StructureError(detail)
    return (result.stdout or b"").decode("utf-8", errors="replace")


def read_source_at_commit(repo_path: Path, sha: str, path: str) -> str:
    return _run_git(repo_path, ["show", f"{sha}:{path}"])


def _exception_type_names(node: ast.expr | None) -> list[str]:
    """Return direct exception names. A missing type is a bare except."""
    if node is None:
        return ["bare"]
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Tuple):
        names: list[str] = []
        for element in node.elts:
            if isinstance(element, ast.Name):
                names.append(element.id)
            elif isinstance(element, ast.Tuple):
                names.extend(name for name in _exception_type_names(element) if name != "bare")
        return names
    return []


def _expr_text(source: str, node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        value = ast.get_source_segment(source, node)
    except (AttributeError, ValueError):
        value = None
    if value is None:
        try:
            value = ast.unparse(node)
        except (AttributeError, ValueError):
            value = None
    return value


def _fingerprint(node: ast.AST) -> str:
    payload = ast.dump(node, annotate_fields=True, include_attributes=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _short_source_segment(source: str, node: ast.AST | None, limit: int = 2000) -> tuple[str | None, bool]:
    value = _expr_text(source, node)
    if value is None or len(value) <= limit:
        return value, False
    return value[:limit], True


def _span(node: ast.AST, line_count: int) -> tuple[int, int, int, int]:
    start_line = int(getattr(node, "lineno", 1))
    end_line = int(getattr(node, "end_lineno", start_line))
    start_col = int(getattr(node, "col_offset", 0))
    end_col = int(getattr(node, "end_col_offset", start_col))
    if isinstance(node, ast.Module):
        start_line = 1
        end_line = max(1, line_count)
        start_col = 0
        end_col = 0
    return start_line, end_line, start_col, end_col


def _annotation(source: str, node: ast.arg | ast.AnnAssign | None) -> str | None:
    if isinstance(node, ast.arg):
        return _expr_text(source, node.annotation)
    if isinstance(node, ast.AnnAssign):
        return _expr_text(source, node.annotation)
    return None


def _function_signature(source: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    args = node.args
    positional = list(getattr(args, "posonlyargs", [])) + list(args.args)
    defaults_start = len(positional) - len(args.defaults)
    parameters: list[dict[str, Any]] = []
    for index, item in enumerate(positional):
        parameters.append(
            {
                "name": item.arg,
                "kind": "positional_only" if index < len(getattr(args, "posonlyargs", [])) else "positional",
                "annotation": _annotation(source, item),
                "has_default": index >= defaults_start,
            }
        )
    if args.vararg is not None:
        parameters.append({"name": args.vararg.arg, "kind": "vararg", "annotation": _annotation(source, args.vararg)})
    for item, default in zip(args.kwonlyargs, args.kw_defaults):
        parameters.append(
            {
                "name": item.arg,
                "kind": "keyword_only",
                "annotation": _annotation(source, item),
                "has_default": default is not None,
            }
        )
    if args.kwarg is not None:
        parameters.append({"name": args.kwarg.arg, "kind": "kwarg", "annotation": _annotation(source, args.kwarg)})
    return {
        "parameters": parameters,
        "returns": _expr_text(source, node.returns),
    }


class _StructureVisitor(ast.NodeVisitor):
    def __init__(self, source: str, path: str, side: str) -> None:
        self.source = source
        self.path = path
        self.side = side
        self.nodes: list[dict[str, Any]] = []
        self.scope: list[str] = []
        self.function_depth = 0
        self.in_exception_group = False
        self._counts: Counter[str] = Counter()

    def _qualified_name(self, name: str | None = None) -> str:
        values = [*self.scope]
        if name:
            values.append(name)
        return ".".join(values) if values else "<module>"

    def _add_node(
        self,
        kind: str,
        node: ast.AST,
        name: str | None,
        qualified_name: str,
        match_key: str,
        details: dict[str, Any] | None = None,
        source_node: ast.AST | None = None,
    ) -> dict[str, Any]:
        start_line, end_line, start_col, end_col = _span(node, len(self.source.splitlines()))
        segment, truncated = _short_source_segment(self.source, source_node or node)
        self._counts[match_key] += 1
        occurrence = self._counts[match_key]
        result: dict[str, Any] = {
            "kind": kind,
            "node_id": f"{self.side}:{kind}:{match_key}:{occurrence}",
            "name": name,
            "qualified_name": qualified_name,
            "match_key": match_key,
            "start_line": start_line,
            "end_line": end_line,
            "start_col": start_col,
            "end_col": end_col,
            "source_segment": segment,
            "fingerprint": _fingerprint(source_node or node),
        }
        if truncated:
            result["source_segment_truncated"] = True
        if details:
            result["details"] = details
        self.nodes.append(result)
        return result

    def _decorators(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef, owner: str) -> list[str]:
        values: list[str] = []
        for index, decorator in enumerate(node.decorator_list):
            expression = _expr_text(self.source, decorator) or ""
            values.append(expression)
            self._add_node(
                "decorator",
                decorator,
                expression,
                f"{owner}.@{index}",
                f"decorator:{owner}:{index}",
                {"owner": owner, "expression": expression, "index": index},
                decorator,
            )
        return values

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualified_name = self._qualified_name(node.name)
        decorators = self._decorators(node, qualified_name)
        for decorator in node.decorator_list:
            self.visit(decorator)
        self._add_node(
            "class",
            node,
            node.name,
            qualified_name,
            f"class:{qualified_name}",
            {
                "bases": [_expr_text(self.source, base) for base in node.bases],
                "decorators": decorators,
            },
        )
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        self.scope.append(node.name)
        for item in node.body:
            self.visit(item)
        self.scope.pop()

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        kind = "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
        qualified_name = self._qualified_name(node.name)
        decorators = self._decorators(node, qualified_name)
        self._add_node(
            kind,
            node,
            node.name,
            qualified_name,
            f"{kind}:{qualified_name}",
            {"signature": _function_signature(self.source, node), "decorators": decorators},
        )
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in [*node.args.defaults, *node.args.kw_defaults]:
            if default is not None:
                self.visit(default)
        for item in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
            if item.annotation is not None:
                self.visit(item.annotation)
        if node.args.vararg and node.args.vararg.annotation:
            self.visit(node.args.vararg.annotation)
        if node.args.kwarg and node.args.kwarg.annotation:
            self.visit(node.args.kwarg.annotation)
        if node.returns is not None:
            self.visit(node.returns)
        self.scope.append(node.name)
        self.function_depth += 1
        for item in node.body:
            self.visit(item)
        self.function_depth -= 1
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _field_targets(self, node: ast.Assign | ast.AnnAssign) -> list[ast.Name]:
        targets: list[ast.AST] = []
        if isinstance(node, ast.Assign):
            targets.extend(node.targets)
        else:
            targets.append(node.target)
        result: list[ast.Name] = []
        for target in targets:
            if isinstance(target, ast.Name):
                result.append(target)
            elif isinstance(target, (ast.Tuple, ast.List)):
                result.extend(item for item in target.elts if isinstance(item, ast.Name))
        return result

    def _visit_field(self, node: ast.Assign | ast.AnnAssign) -> None:
        if self.function_depth == 0 and (not self.scope or self.scope):
            scope = ".".join(self.scope) or "<module>"
            value = node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
            for target in self._field_targets(node):
                qualified_name = f"{scope}.{target.id}"
                details = {
                    "scope": scope,
                    "annotation": _annotation(self.source, node if isinstance(node, ast.AnnAssign) else None),
                    "value_fingerprint": _fingerprint(value) if value is not None else None,
                }
                self._add_node("field", node, target.id, qualified_name, f"field:{qualified_name}", details)

    def visit_Assign(self, node: ast.Assign) -> None:
        self._visit_field(node)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._visit_field(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        callee = _expr_text(self.source, node.func) or ""
        direct_name = node.func.id if isinstance(node.func, ast.Name) else None
        qualified_name = self._qualified_name()
        match_key = f"call:{qualified_name}:{callee}"
        self._add_node(
            "call",
            node,
            callee,
            qualified_name,
            match_key,
            {
                "callee": callee,
                "direct_callee_name": direct_name,
                "args_count": len(node.args),
                "keyword_names": [item.arg for item in node.keywords],
            },
        )
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        exception_type = _expr_text(self.source, node.type)
        qualified_name = self._qualified_name()
        match_key = f"except:{qualified_name}:{getattr(node, 'lineno', 0)}"
        self._add_node(
            "except_handler",
            node,
            node.name,
            qualified_name,
            match_key,
            {
                "exception_type": exception_type,
                "bound_name": node.name,
                "handler_type_names": _exception_type_names(node.type),
                "handler_body_is_single_pass": len(node.body) == 1 and isinstance(node.body[0], ast.Pass),
                "ordinary_handler": not self.in_exception_group,
            },
        )
        previous = self.in_exception_group
        self.in_exception_group = False
        self.generic_visit(node)
        self.in_exception_group = previous

    def visit_TryStar(self, node: ast.TryStar) -> None:
        for item in node.body:
            self.visit(item)
        previous = self.in_exception_group
        self.in_exception_group = True
        for handler in node.handlers:
            self.visit(handler)
        self.in_exception_group = previous
        for item in node.orelse:
            self.visit(item)
        for item in node.finalbody:
            self.visit(item)


def parse_python_source(source: str, path: str, side: str) -> ParsedStructure:
    try:
        tree = ast.parse(source, filename=path, type_comments=True)
    except SyntaxError as exc:
        return {
            "status": "failed",
            "path": path,
            "side": side,
            "nodes": [],
            "error": {
                "code": "syntax_error",
                "message": str(exc),
                "line": exc.lineno,
                "column": exc.offset,
            },
        }
    visitor = _StructureVisitor(source, path, side)
    line_count = max(1, len(source.splitlines()))
    module = ast.Module(body=[], type_ignores=[])
    visitor._add_node("module", module, "<module>", "<module>", f"module:{path}")
    visitor.visit(tree)
    return {
        "status": "ok",
        "path": path,
        "side": side,
        "nodes": visitor.nodes,
        "error": None,
    }


def _changed_lines(file_item: dict[str, Any], side: str) -> list[int]:
    values: set[int] = set()
    for hunk in file_item.get("hunks", []):
        for line in hunk.get("lines", []):
            if side == "head" and line.get("kind") == "add" and line.get("new_line") is not None:
                values.add(int(line["new_line"]))
            if side == "base" and line.get("kind") == "delete" and line.get("old_line") is not None:
                values.add(int(line["old_line"]))
    return sorted(values)


def _map_nodes(parsed: ParsedStructure, changed_lines: list[int]) -> list[dict[str, Any]]:
    if parsed["status"] != "ok":
        return []
    mapped: list[dict[str, Any]] = []
    for node in parsed["nodes"]:
        overlap = [line for line in changed_lines if node["start_line"] <= line <= node["end_line"]]
        if not overlap:
            continue
        copy = dict(node)
        copy["side"] = parsed["side"]
        copy["changed_lines"] = overlap
        mapped.append(copy)
    return mapped


def _snapshot(node: dict[str, Any] | None) -> dict[str, Any] | None:
    if node is None:
        return None
    return {key: value for key, value in node.items() if key not in {"side"}}


def _change(
    change_type: str,
    kind: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> dict[str, Any]:
    evidence = sorted(set((before or {}).get("changed_lines", []) + (after or {}).get("changed_lines", [])))
    location = after or before or {}
    return {
        "type": change_type,
        "kind": kind,
        "match_key": location.get("match_key"),
        "node_id": location.get("node_id"),
        "evidence_lines": evidence,
        "location": {
            "start_line": location.get("start_line"),
            "end_line": location.get("end_line"),
            "start_col": location.get("start_col"),
            "end_col": location.get("end_col"),
        },
        "before": _snapshot(before),
        "after": _snapshot(after),
    }


def _structural_changes(base_nodes: list[dict[str, Any]], head_nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    head_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in base_nodes:
        if node["kind"] != "module":
            base_by_key[node["match_key"]].append(node)
    for node in head_nodes:
        if node["kind"] != "module":
            head_by_key[node["match_key"]].append(node)

    changes: list[dict[str, Any]] = []
    for key in sorted(set(base_by_key) | set(head_by_key)):
        before_items = base_by_key.get(key, [])
        after_items = head_by_key.get(key, [])
        pairs = max(len(before_items), len(after_items))
        for index in range(pairs):
            before = before_items[index] if index < len(before_items) else None
            after = after_items[index] if index < len(after_items) else None
            kind = (after or before)["kind"]
            if before is None:
                change_type = "decorator_added" if kind == "decorator" else "node_added"
                changes.append(_change(change_type, kind, None, after))
                continue
            if after is None:
                change_type = "decorator_removed" if kind == "decorator" else "node_removed"
                changes.append(_change(change_type, kind, before, None))
                continue

            before_details = before.get("details", {})
            after_details = after.get("details", {})
            if kind in {"function", "async_function"}:
                if before_details.get("signature") != after_details.get("signature"):
                    changes.append(_change("signature_changed", kind, before, after))
                elif before["fingerprint"] != after["fingerprint"]:
                    changes.append(_change("function_touched", kind, before, after))
            elif kind == "class":
                if before_details != after_details or before["fingerprint"] != after["fingerprint"]:
                    changes.append(_change("class_touched", kind, before, after))
            elif kind == "decorator":
                if before_details.get("expression") != after_details.get("expression"):
                    changes.append(_change("decorator_removed", kind, before, None))
                    changes.append(_change("decorator_added", kind, None, after))
            elif kind == "field":
                if before["fingerprint"] != after["fingerprint"] or before_details != after_details:
                    changes.append(_change("field_modified", kind, before, after))
            elif kind == "call":
                if before["fingerprint"] != after["fingerprint"] or before_details != after_details:
                    changes.append(_change("call_touched", kind, before, after))
            elif kind == "except_handler":
                if before_details != after_details or before["fingerprint"] != after["fingerprint"]:
                    changes.append(_change("exception_handler_changed", kind, before, after))
    return changes


def _side_result(
    repo_path: Path,
    sha: str,
    path: str | None,
    side: str,
    changed_lines: list[int],
) -> dict[str, Any]:
    if path is None:
        return {"status": "absent", "nodes": [], "error": None}
    try:
        source = read_source_at_commit(repo_path, sha, path)
    except StructureError as exc:
        return {
            "status": "failed",
            "nodes": [],
            "error": {"code": "git_show_error", "message": str(exc), "side": side, "path": path},
        }
    parsed = parse_python_source(source, path, side)
    parsed["nodes"] = _map_nodes(parsed, changed_lines)
    return {
        "status": parsed["status"],
        "nodes": parsed["nodes"],
        "error": parsed["error"],
    }


def _file_structure(file_item: dict[str, Any], record: dict[str, Any], repo_path: Path) -> dict[str, Any]:
    path = file_item.get("new_path") or file_item.get("old_path")
    result: dict[str, Any] = {
        "path": path,
        "old_path": file_item.get("old_path"),
        "new_path": file_item.get("new_path"),
        "status": file_item.get("status"),
        "role": file_item.get("role"),
        "parse_status": {"base": "skipped", "head": "skipped"},
        "nodes": [],
        "structural_changes": [],
        "errors": [],
    }
    if file_item.get("role") not in PYTHON_ROLES or not file_item.get("is_python"):
        return result

    base_lines = _changed_lines(file_item, "base")
    head_lines = _changed_lines(file_item, "head")
    base_path = file_item.get("old_path")
    head_path = file_item.get("new_path")
    base_result = _side_result(repo_path, record["base_sha"], base_path, "base", base_lines)
    head_result = _side_result(repo_path, record["head_sha"], head_path, "head", head_lines)
    result["parse_status"] = {"base": base_result["status"], "head": head_result["status"]}
    for side_result in (base_result, head_result):
        if side_result["error"]:
            result["errors"].append(side_result["error"])
    result["nodes"] = [*base_result["nodes"], *head_result["nodes"]]
    result["structural_changes"] = _structural_changes(base_result["nodes"], head_result["nodes"])
    if any(value == "failed" for value in result["parse_status"].values()):
        result["parse_status"]["file"] = "degraded"
    else:
        result["parse_status"]["file"] = "ok"
    return result


def _base_record(record: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "schema_version": STRUCTURE_SCHEMA_VERSION,
        "status": status,
        "repo": record.get("repo"),
        "pr_number": record.get("pr_number"),
        "base_sha": record.get("base_sha"),
        "head_sha": record.get("head_sha"),
        "source_stage03": {"schema_version": record.get("schema_version", "stage03.v1")},
    }


def extract_changed_structures(stage03_record: dict[str, Any], repo_path: Path) -> dict[str, Any]:
    source_status = stage03_record.get("status")
    if source_status == "excluded":
        result = _base_record(stage03_record, "excluded")
        result.update({"files": [], "summary": {"files_attempted": 0, "files_parsed": 0, "files_degraded": 0, "nodes": 0, "structural_changes": 0}, "errors": []})
        return result
    if source_status != "ok":
        result = _base_record(stage03_record, "error")
        result.update({"files": [], "summary": {"files_attempted": 0, "files_parsed": 0, "files_degraded": 0, "nodes": 0, "structural_changes": 0}, "errors": stage03_record.get("errors", [])})
        return result

    files = [_file_structure(item, stage03_record, repo_path) for item in stage03_record.get("files", [])]
    python_files = [item for item in files if item["role"] in PYTHON_ROLES and item.get("is_python", True)]
    parsed_files = sum(item["parse_status"].get("file") == "ok" for item in python_files)
    degraded_files = sum(item["parse_status"].get("file") == "degraded" for item in python_files)
    errors = [error for item in files for error in item.get("errors", [])]
    result = _base_record(stage03_record, "error" if errors and any(error.get("code") == "git_show_error" for error in errors) else "ok")
    result.update(
        {
            "files": files,
            "summary": {
                "files_attempted": len(python_files),
                "files_parsed": parsed_files,
                "files_degraded": degraded_files,
                "nodes": sum(len(item["nodes"]) for item in files),
                "structural_changes": sum(len(item["structural_changes"]) for item in files),
            },
            "errors": errors,
        }
    )
    return result


def _select_records(records: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    if limit is None:
        return records
    if limit < 1:
        raise ValueError("limit 必须大于 0")
    by_pr = {item.get("pr_number"): item for item in records if item.get("status") == "ok"}
    selected = [by_pr[number] for number in PILOT_PR_NUMBERS if number in by_pr]
    for item in sorted(records, key=lambda value: int(value.get("pr_number") or 0)):
        if item.get("status") == "ok" and item not in selected:
            selected.append(item)
        if len(selected) >= limit:
            break
    return selected[:limit]


def build_structure_dataset(
    input_path: Path,
    repo_path: Path,
    output_path: Path,
    manifest_path: Path | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    records = load_records(input_path)
    selected = _select_records(records, limit)
    objects = [extract_changed_structures(record, repo_path) for record in selected]
    write_jsonl(objects, output_path)
    status_counts = Counter(item["status"] for item in objects)
    parse_counts = Counter(
        file_item["parse_status"].get("file", "skipped")
        for item in objects
        for file_item in item.get("files", [])
        if file_item.get("role") in PYTHON_ROLES and file_item.get("is_python", True)
    )
    manifest = {
        "schema_version": STRUCTURE_SCHEMA_VERSION,
        "input_path": str(input_path),
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "repo": "netbox-community/netbox",
        "selection_limit": limit,
        "input_records": len(records),
        "selected_records": len(selected),
        "status_counts": dict(sorted(status_counts.items())),
        "parse_status_counts": dict(sorted(parse_counts.items())),
        "node_count": sum(item["summary"]["nodes"] for item in objects),
        "structural_change_count": sum(item["summary"]["structural_changes"] for item in objects),
        "selected_pr_numbers": [item.get("pr_number") for item in selected if item.get("pr_number") is not None],
        "pilot_pr_numbers": list(PILOT_PR_NUMBERS) if limit == 3 else [],
        "output_path": str(output_path),
    }
    if manifest_path is not None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest
