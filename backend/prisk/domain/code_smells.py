"""三条语言级代码异味规则。

检测对象来自现有 head AST 节点：节点必须已经与三点 Diff 的新增行相交。
命中只生成复核 Finding，不表示缺陷、漏洞或执行已发生。
旧 stage04 节点缺少 004 字段时，只在源码切片能按同一语义还原时回退；否则把文件标为未分析。
"""

from __future__ import annotations

import ast
import re
import textwrap
from typing import Any

from .structure import _exception_type_names


BROAD_HANDLER_NAMES = ("bare", "Exception", "BaseException")
DYNAMIC_CALLEES = ("eval", "exec")

CODE_SMELL_RULES: list[dict[str, str]] = [
    {
        "rule_id": "code.swallowed_exception",
        "severity": "medium",
        "trigger": "新增行与异常处理分支相交，且处理体恰好只有一个 pass",
        "evidence_type": "code_slice",
        "suggested_action": "复核该分支是否应记录、恢复或重新抛出，并确认忽略是否明确",
        "limitations": "只表示处理体为单个 pass，不判断异常是否发生或忽略是否合理；不覆盖 except*",
    },
    {
        "rule_id": "code.bare_exception",
        "severity": "medium",
        "trigger": "新增行与异常处理分支相交，且类型为空或直接名称包含 Exception 或 BaseException",
        "evidence_type": "code_slice",
        "suggested_action": "复核捕获范围、处理体和执行边界；裸 except 与 except Exception 的后果不同",
        "limitations": "按源码直接名称匹配，不解析别名、继承或遮蔽；不覆盖 except*；不判断缺陷",
    },
    {
        "rule_id": "code.dynamic_execution",
        "severity": "medium",
        "trigger": "新增行与直接名称 eval 或 exec 调用相交；compile 不在本规则内",
        "evidence_type": "code_slice",
        "suggested_action": "复核动态代码的来源和调用绑定",
        "limitations": "只报告直接名称 eval 和 exec；不包含 compile、属性调用、别名或字符串中的名字；不判断输入是否不可信",
    },
]

_RULES_BY_ID = {rule["rule_id"]: rule for rule in CODE_SMELL_RULES}
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MISSING = object()
_SWALLOWED_MESSAGE = (
    "异常处理分支的处理体只有 pass。"
    "此线索只要求复核是否有意忽略异常，不判断故障是否发生。"
)


def _broad_names(names: list[str]) -> list[str]:
    found: list[str] = []
    for name in names:
        if name in BROAD_HANDLER_NAMES and name not in found:
            found.append(name)
    return found


def _bare_message(broad: list[str]) -> str:
    if broad == ["bare"]:
        return (
            "捕获形式为裸 except:。"
            "裸 except 等价于捕获 BaseException，会捕获 KeyboardInterrupt 和 SystemExit。"
            "此线索只要求复核，不判断缺陷。"
        )
    if broad == ["Exception"]:
        return (
            "捕获形式为 Exception。"
            "except Exception 不会捕获 KeyboardInterrupt 和 SystemExit。"
            "此线索只要求复核，不判断缺陷。"
        )
    if broad == ["BaseException"]:
        return (
            "捕获形式为 BaseException。"
            "except BaseException 会捕获 KeyboardInterrupt 和 SystemExit。"
            "此线索只要求复核，不判断缺陷。"
        )
    shown = "、".join(broad)
    return (
        f"捕获形式包含 {shown}。"
        "同一异常分支只生成一条线索；裸 except、Exception 与 BaseException 的后果并不相同。"
        "此线索只要求复核，不判断缺陷。"
    )


def _dynamic_message(name: str) -> str:
    return (
        f"直接调用 {name}。"
        "此线索只报告函数位置上的直接名称，不判断输入是否不可信，也不表示代码已经执行。"
        "compile 不在本规则范围内。"
    )


def _slice_record(node: dict[str, Any] | None, *, missing_reason: str) -> dict[str, Any]:
    if node is None:
        return {"status": "unavailable", "reason": missing_reason, "source_segment": None}
    segment = node.get("source_segment")
    if isinstance(segment, str) and segment:
        return {"status": "available", "source_segment": segment}
    return {"status": "unavailable", "reason": "source_missing", "source_segment": None}


def _paired_before(file_item: dict[str, Any], node: dict[str, Any]) -> dict[str, Any] | None:
    node_id = node.get("node_id")
    for change in file_item.get("structural_changes") or []:
        after = change.get("after") or {}
        if node_id and (change.get("node_id") == node_id or after.get("node_id") == node_id):
            before = change.get("before")
            return before if isinstance(before, dict) else None
    match_key = node.get("match_key")
    if not match_key:
        return None
    for candidate in file_item.get("nodes") or []:
        if candidate.get("side") == "base" and candidate.get("match_key") == match_key:
            return candidate
    return None


def _handler_from_segment(segment: str) -> dict[str, Any] | None:
    """Recover handler semantics from a complete ExceptHandler source slice."""
    dedented = textwrap.dedent(segment).strip("\n")
    if not dedented.lstrip().startswith("except"):
        return None
    try:
        tree = ast.parse("try:\n    pass\n" + dedented + "\n")
    except SyntaxError:
        return None
    if len(tree.body) != 1:
        return None
    statement = tree.body[0]
    if isinstance(statement, ast.Try):
        ordinary = True
        handlers = statement.handlers
    elif isinstance(statement, ast.TryStar):
        ordinary = False
        handlers = statement.handlers
    else:
        return None
    if len(handlers) != 1:
        return None
    handler = handlers[0]
    return {
        "handler_type_names": _exception_type_names(handler.type),
        "handler_body_is_single_pass": len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass),
        "ordinary_handler": ordinary,
    }


def _call_name_from_segment(segment: str) -> str | None | object:
    try:
        tree = ast.parse(textwrap.dedent(segment).strip())
    except SyntaxError:
        return _MISSING
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    if len(calls) != 1:
        return _MISSING
    func = calls[0].func
    if isinstance(func, ast.Name):
        return func.id
    return None


def _resolve_handler(node: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    details = node.get("details") or {}
    required = ("handler_type_names", "handler_body_is_single_pass", "ordinary_handler")
    if all(key in details for key in required):
        names = details.get("handler_type_names")
        single_pass = details.get("handler_body_is_single_pass")
        ordinary = details.get("ordinary_handler")
        if isinstance(names, list) and isinstance(single_pass, bool) and isinstance(ordinary, bool):
            return details, True
        return None, False
    if node.get("source_segment_truncated"):
        return None, False
    segment = node.get("source_segment")
    if isinstance(segment, str) and segment.strip():
        recovered = _handler_from_segment(segment)
        if recovered is not None:
            return recovered, True
    return None, False


def _resolve_direct_callee(node: dict[str, Any]) -> tuple[str | None, bool]:
    details = node.get("details") or {}
    if "direct_callee_name" in details:
        name = details.get("direct_callee_name")
        return (name if isinstance(name, str) else None), True
    if "callee" in details and isinstance(details.get("callee"), str) and details["callee"].strip():
        callee = details["callee"].strip()
        if _IDENTIFIER.fullmatch(callee):
            return callee, True
        return None, True
    if node.get("source_segment_truncated"):
        return None, False
    segment = node.get("source_segment")
    if isinstance(segment, str) and segment.strip():
        recovered = _call_name_from_segment(segment)
        if recovered is not _MISSING:
            return recovered if isinstance(recovered, str) else None, True
    return None, False


def _change_type(file_item: dict[str, Any], node_id: str | None) -> str:
    for change in file_item.get("structural_changes", []):
        after = change.get("after") or {}
        if node_id and (change.get("node_id") == node_id or after.get("node_id") == node_id):
            return str(change.get("type") or "added_line_overlap")
    return "added_line_overlap"


def _evidence(
    path: str,
    file_item: dict[str, Any],
    node: dict[str, Any],
    **details: Any,
) -> dict[str, Any]:
    after = _slice_record(node, missing_reason="source_missing")
    before = _slice_record(_paired_before(file_item, node), missing_reason="no_base_node")
    evidence = {
        "path": path,
        "node_id": node.get("node_id"),
        "node_kind": node.get("kind"),
        "structural_change_type": _change_type(file_item, node.get("node_id")),
        "lines": sorted(set(node.get("changed_lines", []))),
        "qualified_name": node.get("qualified_name"),
        "start_line": node.get("start_line"),
        "end_line": node.get("end_line"),
        "impact_type": "pr_intrinsic_risk",
        "source_segment": after["source_segment"],
        "source_status": after["status"],
        "before": before,
        "after": after,
    }
    evidence.update(details)
    return evidence


def _finding(rule_id: str, message: str, evidence: dict[str, Any]) -> dict[str, Any]:
    rule = _RULES_BY_ID[rule_id]
    return {
        "rule_id": rule_id,
        "severity": rule["severity"],
        "confidence": "structural",
        "message": message,
        "impact_type": "pr_intrinsic_risk",
        "evidence": [evidence],
        "suggested_action": rule["suggested_action"],
    }


def _head_nodes(file_item: dict[str, Any]) -> list[dict[str, Any]]:
    if file_item.get("parse_status", {}).get("head") == "failed":
        return []
    return [
        node
        for node in file_item.get("nodes", [])
        if node.get("side") == "head" and node.get("changed_lines")
    ]


def _handler_findings(
    path: str,
    file_item: dict[str, Any],
    node: dict[str, Any],
    enabled: set[str],
) -> tuple[list[dict[str, Any]], bool]:
    if node.get("kind") != "except_handler":
        return [], True
    if not enabled.intersection({"code.swallowed_exception", "code.bare_exception"}):
        return [], True
    details, evaluable = _resolve_handler(node)
    if not evaluable or details is None:
        return [], False
    if details.get("ordinary_handler") is not True:
        return [], True
    findings: list[dict[str, Any]] = []
    names = [str(name) for name in details.get("handler_type_names", [])]
    if "code.swallowed_exception" in enabled and details.get("handler_body_is_single_pass") is True:
        findings.append(
            _finding(
                "code.swallowed_exception",
                _SWALLOWED_MESSAGE,
                _evidence(path, file_item, node, handler_body_is_single_pass=True),
            )
        )
    broad = _broad_names(names)
    if "code.bare_exception" in enabled and broad:
        findings.append(
            _finding(
                "code.bare_exception",
                _bare_message(broad),
                _evidence(path, file_item, node, capture_form=",".join(broad), handler_type_names=names),
            )
        )
    return findings, True


def _call_findings(
    path: str,
    file_item: dict[str, Any],
    node: dict[str, Any],
    enabled: set[str],
) -> tuple[list[dict[str, Any]], bool]:
    if node.get("kind") != "call" or "code.dynamic_execution" not in enabled:
        return [], True
    name, evaluable = _resolve_direct_callee(node)
    if not evaluable:
        return [], False
    if name not in DYNAMIC_CALLEES:
        return [], True
    return [
        _finding(
            "code.dynamic_execution",
            _dynamic_message(str(name)),
            _evidence(path, file_item, node, callee_name=name),
        )
    ], True


def collect_code_smell_findings(
    stage04_record: dict[str, Any],
    enabled: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Match evaluable head nodes. Return findings and files that could not be evaluated."""
    if not enabled.intersection(_RULES_BY_ID):
        return [], []
    findings: list[dict[str, Any]] = []
    gaps: dict[str, list[str]] = {}
    for file_item in stage04_record.get("files", []):
        path = str(file_item.get("path") or file_item.get("new_path") or file_item.get("old_path") or "")
        for node in _head_nodes(file_item):
            handler_findings, handler_ok = _handler_findings(path, file_item, node, enabled)
            call_findings, call_ok = _call_findings(path, file_item, node, enabled)
            if handler_ok and call_ok:
                findings.extend(handler_findings)
                findings.extend(call_findings)
                continue
            node_id = str(node.get("node_id") or "")
            gaps.setdefault(path, []).append(node_id)
    findings.sort(
        key=lambda item: (
            item["evidence"][0].get("path") or "",
            item["rule_id"],
            item["evidence"][0].get("start_line") or 0,
            item["evidence"][0].get("node_id") or "",
        )
    )
    unanalyzed = [
        {"path": path, "reason": "unsupported_stage04_details", "node_ids": sorted(set(node_ids))}
        for path, node_ids in sorted(gaps.items())
    ]
    return findings, unanalyzed
