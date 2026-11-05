"""语言级代码异味规则。

检测对象来自 head AST 节点：节点必须已经与三点 Diff 的新增行相交。
命中只生成复核 Finding，不表示缺陷、漏洞、资源泄漏或执行已发生。
004 的三条规则在旧节点上做有界回退。005 的 open 与控制流深度同样如此：
无法按卡片语义判断的相关节点写入 summary.unanalyzed，而不是记为通过。
"""

from __future__ import annotations

import ast
import re
import textwrap
from typing import Any

from .structure import _exception_type_names


BROAD_HANDLER_NAMES = ("bare", "Exception", "BaseException")
DYNAMIC_CALLEES = ("eval", "exec")
OPEN_CALLEE = "open"
CONTROL_FLOW_DEPTH_THRESHOLD = 4
CONTROL_FLOW_KINDS = frozenset({"if", "for", "async_for", "while", "with", "async_with", "try", "try_star"})

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
    {
        "rule_id": "code.unmanaged_open",
        "severity": "medium",
        "trigger": "新增行与直接名称 open 调用相交，且该调用不是 with 或 async with 的上下文表达式",
        "evidence_type": "code_slice",
        "suggested_action": "复核该 open 是否应由 with 关闭，或是否已有明确的关闭路径",
        "limitations": "只表示直接名称 open 未作为 with 上下文表达式；不判断文件是否泄漏；不含 Path.open 等属性调用",
    },
    {
        "rule_id": "code.deep_control_flow",
        "severity": "medium",
        "trigger": "新增行与控制流语句相交，且该语句在当前函数、类或模块内的嵌套深度大于 4",
        "evidence_type": "code_slice",
        "suggested_action": "复核该嵌套是否应拆分；深度阈值是卡片固定值 4，不是运行时配置",
        "limitations": "只比较固定深度阈值；不计算圈复杂度，不判断缺陷；elif 链、match 和推导式不增加深度",
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


def _open_message() -> str:
    return (
        "直接调用 open，且该调用不是 with 或 async with 的上下文表达式。"
        "此线索只要求复核资源关闭路径，不判断泄漏已经发生。"
        "Path.open、io.open 和其他属性调用不在本规则范围内。"
    )


def _depth_message(kind: str, depth: int, basis: str) -> str:
    basis_text = "记录的嵌套深度" if basis == "recorded" else "源码切片内的深度下界"
    return (
        f"控制流 {kind} 的{basis_text}为 {depth}，超过固定阈值 {CONTROL_FLOW_DEPTH_THRESHOLD}。"
        "计入深度的语句是 if、for、async for、while、with、async with 和 try。"
        "此线索只要求复核可读性，不判断缺陷。"
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


def _segment_control_depth(segment: str) -> tuple[str, int] | None:
    """Return the root kind and the deepest counted depth inside one statement."""
    try:
        tree = ast.parse(textwrap.dedent(segment).strip())
    except SyntaxError:
        return None
    if len(tree.body) != 1:
        return None
    statement = tree.body[0]
    kind = _control_statement_kind(statement)
    if kind is None:
        return None
    return kind, _max_control_depth(statement, 0)


def _control_statement_kind(statement: ast.AST) -> str | None:
    if isinstance(statement, ast.If):
        return "if"
    if isinstance(statement, ast.For):
        return "for"
    if isinstance(statement, ast.AsyncFor):
        return "async_for"
    if isinstance(statement, ast.While):
        return "while"
    if isinstance(statement, ast.With):
        return "with"
    if isinstance(statement, ast.AsyncWith):
        return "async_with"
    if isinstance(statement, ast.Try):
        return "try"
    if isinstance(statement, ast.TryStar):
        return "try_star"
    return None


def _max_control_depth(statement: ast.AST, depth: int) -> int:
    if isinstance(statement, ast.If):
        return _max_if_depth(statement, depth, elif_chain=False)
    kind = _control_statement_kind(statement)
    if kind is not None:
        return _max_block_depth(statement, depth)
    if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return _max_statement_depth(statement.body, 0)
    if isinstance(statement, ast.Match):
        best = depth
        for case in statement.cases:
            best = max(best, _max_statement_depth(case.body, depth))
        return best
    return depth


def _max_statement_depth(statements: list[ast.stmt], depth: int) -> int:
    best = depth
    for statement in statements:
        best = max(best, _max_control_depth(statement, depth))
    return best


def _max_if_depth(statement: ast.If, depth: int, *, elif_chain: bool) -> int:
    local = depth if elif_chain else depth + 1
    best = _max_statement_depth(statement.body, local)
    if len(statement.orelse) == 1 and isinstance(statement.orelse[0], ast.If):
        best = max(best, _max_if_depth(statement.orelse[0], local, elif_chain=True))
    else:
        best = max(best, _max_statement_depth(statement.orelse, local))
    return best


def _max_block_depth(statement: ast.AST, depth: int) -> int:
    local = depth + 1
    bodies: list[list[ast.stmt]] = []
    if isinstance(statement, (ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith)):
        bodies.append(statement.body)
    if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
        bodies.append(statement.orelse)
    if isinstance(statement, (ast.Try, ast.TryStar)):
        bodies.extend([statement.body, statement.orelse, statement.finalbody])
        bodies.extend(handler.body for handler in statement.handlers)
    best = local
    for body in bodies:
        best = max(best, _max_statement_depth(body, local))
    return best


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


def _resolve_with_context(node: dict[str, Any]) -> tuple[bool | None, bool]:
    details = node.get("details") or {}
    if "used_as_with_context" not in details:
        return None, False
    flag = details.get("used_as_with_context")
    if isinstance(flag, bool):
        return flag, True
    return None, False


def _resolve_control_flow(node: dict[str, Any]) -> tuple[str | None, int | None, str | None, bool]:
    details = node.get("details") or {}
    kind = details.get("control_kind")
    depth = details.get("nesting_depth")
    if kind in CONTROL_FLOW_KINDS and isinstance(depth, int) and not isinstance(depth, bool) and depth >= 1:
        return str(kind), depth, "recorded", True
    if node.get("source_segment_truncated"):
        return None, None, None, False
    segment = node.get("source_segment")
    if isinstance(segment, str) and segment.strip():
        recovered = _segment_control_depth(segment)
        if recovered is not None:
            relative_kind, relative_depth = recovered
            if relative_depth > CONTROL_FLOW_DEPTH_THRESHOLD:
                return relative_kind, relative_depth, "segment_lower_bound", True
            return None, None, None, False
    return None, None, None, False


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
    if node.get("kind") != "call":
        return [], True
    want_dynamic = "code.dynamic_execution" in enabled
    want_open = "code.unmanaged_open" in enabled
    if not want_dynamic and not want_open:
        return [], True
    name, evaluable = _resolve_direct_callee(node)
    if not evaluable:
        return [], False
    findings: list[dict[str, Any]] = []
    if want_dynamic and name in DYNAMIC_CALLEES:
        findings.append(
            _finding(
                "code.dynamic_execution",
                _dynamic_message(str(name)),
                _evidence(path, file_item, node, callee_name=name),
            )
        )
    if want_open and name == OPEN_CALLEE:
        used_as_with_context, context_known = _resolve_with_context(node)
        if not context_known:
            return [], False
        if used_as_with_context is False:
            findings.append(
                _finding(
                    "code.unmanaged_open",
                    _open_message(),
                    _evidence(
                        path,
                        file_item,
                        node,
                        callee_name=OPEN_CALLEE,
                        used_as_with_context=False,
                    ),
                )
            )
    return findings, True


def _control_findings(
    path: str,
    file_item: dict[str, Any],
    node: dict[str, Any],
    enabled: set[str],
) -> tuple[list[dict[str, Any]], bool]:
    if node.get("kind") != "control_flow" or "code.deep_control_flow" not in enabled:
        return [], True
    kind, depth, basis, evaluable = _resolve_control_flow(node)
    if not evaluable or kind is None or depth is None or basis is None:
        return [], False
    if depth <= CONTROL_FLOW_DEPTH_THRESHOLD:
        return [], True
    return [
        _finding(
            "code.deep_control_flow",
            _depth_message(kind, depth, basis),
            _evidence(
                path,
                file_item,
                node,
                control_kind=kind,
                nesting_depth=depth,
                depth_threshold=CONTROL_FLOW_DEPTH_THRESHOLD,
                nesting_depth_basis=basis,
            ),
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
            control_findings, control_ok = _control_findings(path, file_item, node, enabled)
            if handler_ok and call_ok and control_ok:
                findings.extend(handler_findings)
                findings.extend(call_findings)
                findings.extend(control_findings)
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
