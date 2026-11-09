"""语言级代码异味规则。

检测对象来自 head AST 节点：节点必须已经与三点 Diff 的新增行相交。
命中只生成复核 Finding，不表示缺陷、漏洞、资源泄漏、秘密已确认或执行已发生。
004 的三条规则在旧节点上做有界回退。005 的 open 与控制流深度同样如此。
006 的字面量绑定和可变状态也一样：无法按卡片语义判断的相关节点写入
summary.unanalyzed，而不是记为通过。
"""

from __future__ import annotations

import ast
import re
import textwrap
from typing import Any

from .structure import _container_kind, _exception_type_names, _expr_text, _literal_facts


BROAD_HANDLER_NAMES = ("bare", "BaseException")
DYNAMIC_CALLEES = ("eval", "exec")
OPEN_CALLEE = "open"
CONTROL_FLOW_DEPTH_THRESHOLD = 4
CONTROL_FLOW_KINDS = frozenset({"if", "for", "async_for", "while", "with", "async_with", "try", "try_star"})
# Card constants. These are not runtime configuration.
CREDENTIAL_BINDING_NAMES = frozenset({
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "client_secret",
    "auth_token",
    "secret_key",
})
SECRET_PLACEHOLDERS = frozenset({
    "password",
    "passwd",
    "secret",
    "token",
    "changeme",
    "placeholder",
    "example",
    "xxx",
    "redacted",
    "todo",
    "test",
    "dummy",
    "none",
    "null",
    "default",
    "fixme",
    "sample",
    "your-secret",
    "your_secret",
})
SECRET_LITERAL_MIN_LENGTH = 8
BINDING_FORMS = frozenset({
    "name_assignment",
    "attribute_assignment",
    "keyword_argument",
    "parameter_default",
})
MUTABLE_VALUE_KINDS = frozenset({
    "list_display",
    "dict_display",
    "set_display",
    "list_call",
    "dict_call",
    "set_call",
})
_BINDING_FORM_LABELS = {
    "name_assignment": "直接名称赋值",
    "attribute_assignment": "属性赋值",
    "keyword_argument": "关键字参数",
    "parameter_default": "参数默认值",
}

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
        "trigger": "新增行与异常处理分支相交，且类型为空或直接名称包含 BaseException（不含 except Exception）",
        "evidence_type": "code_slice",
        "suggested_action": "复核捕获范围、处理体和执行边界；裸 except 与 BaseException 会捕获 KeyboardInterrupt 和 SystemExit",
        "limitations": "按源码直接名称匹配，不解析别名、继承或遮蔽；except Exception 不是本规则 Hit；不覆盖 except*；不判断缺陷",
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
        "trigger": "新增行与直接名称 open 或 Path(...).open / pathlib.Path(...).open 相交，且该调用不是 with 或 async with 的上下文表达式",
        "evidence_type": "code_slice",
        "suggested_action": "复核该 open 是否应由 with 关闭，或是否已有明确的关闭路径",
        "limitations": "覆盖直接名称 open 与接收者为 Path(...) 调用的属性 open；不判断泄漏；io.open / builtins.open / 名字形式 path.open() 不在 Hit 内",
    },
    {
        "rule_id": "code.deep_control_flow",
        "severity": "medium",
        "trigger": "新增行与控制流语句相交，且该语句在当前函数、类或模块内的嵌套深度大于 4",
        "evidence_type": "code_slice",
        "suggested_action": "复核该嵌套是否应拆分；深度阈值是卡片固定值 4，不是运行时配置",
        "limitations": "只比较固定深度阈值；不计算圈复杂度，不判断缺陷；elif 链、match 和推导式不增加深度",
    },
    {
        "rule_id": "code.hardcoded_secret",
        "severity": "medium",
        "trigger": "新增行与凭据名字的赋值、属性赋值、关键字参数或函数默认值相交，且值是长度不少于 8、不在占位符表中的单个 str 字面量",
        "evidence_type": "code_slice",
        "suggested_action": "复核该字面量是示例、测试夹具还是应移出仓库的秘密；命中不是秘密已确认",
        "limitations": "只做名字整段匹配和长度、占位符检查；不确认秘密，不判断漏洞，不扫描任意字符串内容",
    },
    {
        "rule_id": "code.global_mutable_state",
        "severity": "medium",
        "trigger": "新增行与函数体内的 global 语句相交，或与模块、类体中的列表、字典、集合或无参 list/dict/set 绑定相交",
        "evidence_type": "code_slice",
        "suggested_action": "复核该共享绑定是否跨请求或跨测试可见，以及谁负责清空",
        "limitations": "只表示 global 重新绑定或模块、类体可变容器；不判断串扰已经发生，不含函数内局部列表和 defaultdict",
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
        "同一异常分支只生成一条线索；裸 except 与 BaseException 会捕获 KeyboardInterrupt 和 SystemExit。"
        "except Exception 不是本规则的 Hit。此线索只要求复核，不判断缺陷。"
    )


def _dynamic_message(name: str) -> str:
    return (
        f"直接调用 {name}。"
        "此线索只报告函数位置上的直接名称，不判断输入是否不可信，也不表示代码已经执行。"
        "compile 不在本规则范围内。"
    )


def _open_message(*, form: str = "direct_open") -> str:
    if form == "path_open":
        lead = "调用 Path(...).open，且该调用不是 with 或 async with 的上下文表达式。"
    else:
        lead = "直接调用 open，且该调用不是 with 或 async with 的上下文表达式。"
    return (
        lead
        + "此线索只要求复核资源关闭路径，不判断泄漏已经发生。"
        + "io.open、builtins.open 以及接收者不是 Path(...) 调用的属性 open 不在本规则 Hit 内。"
    )


def _secret_message(name: str, form: str, length: int) -> str:
    label = _BINDING_FORM_LABELS.get(form, form)
    return (
        f"绑定 {name}（{label}）的值是长度为 {length} 的 str 字面量。"
        "此线索只要求复核它是示例、测试夹具还是仓库中的字面量，不表示秘密已经确认，也不表示存在漏洞。"
    )


def _mutable_message(form: str, targets: list[str]) -> str:
    shown = "、".join(targets) if targets else "未命名绑定"
    if form == "global_statement":
        return (
            f"函数体内的 global 语句声明了 {shown}。"
            "此线索只表示重新绑定模块级名字，不要求随后的值是可变对象，也不判断已经发生串扰。"
        )
    return (
        f"模块或类体把 {shown} 绑定到可变容器。"
        "此线索只要求复核共享状态，不判断缓存是否有意设计，也不判断已经发生串扰。"
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


def _path_open_from_segment(segment: str) -> bool | None:
    """True when segment is Path(...).open(...) or pathlib.Path(...).open(...)."""
    try:
        tree = ast.parse(textwrap.dedent(segment).strip())
    except SyntaxError:
        return None
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    if len(calls) != 1:
        return None
    func = calls[0].func
    if not isinstance(func, ast.Attribute) or func.attr != "open":
        return False
    receiver = func.value
    if not isinstance(receiver, ast.Call):
        return False
    if isinstance(receiver.func, ast.Name):
        return receiver.func.id == "Path"
    if isinstance(receiver.func, ast.Attribute):
        return receiver.func.attr == "Path"
    return False


_OUT_OF_SCOPE_OPEN_RECEIVERS = frozenset({"io", "builtins"})


def _resolve_open_form(node: dict[str, Any]) -> tuple[str | None, bool, str | None]:
    """Return (form, evaluable, gap_reason).

    form is "direct_open", "path_open", or None when not an open this rule covers as Hit.
    gap_reason is set when a name-receiver attribute open cannot prove Path.
    io.open / builtins.open stay out of scope without a framework gap.
    """
    details = node.get("details") or {}
    if details.get("is_path_open") is True or (
        details.get("attribute_callee_name") == "open" and details.get("receiver_last_segment") == "Path"
    ):
        return "path_open", True, None
    if details.get("attribute_callee_name") == "open":
        receiver = details.get("receiver_last_segment")
        if receiver in _OUT_OF_SCOPE_OPEN_RECEIVERS:
            return None, True, None
        return None, True, "missing_framework_context"
    if "direct_callee_name" in details:
        name = details.get("direct_callee_name")
        if name == OPEN_CALLEE:
            return "direct_open", True, None
        return None, True, None
    name, evaluable = _resolve_direct_callee(node)
    if not evaluable:
        if node.get("source_segment_truncated"):
            return None, False, None
        segment = node.get("source_segment")
        if isinstance(segment, str) and segment.strip():
            path_open = _path_open_from_segment(segment)
            if path_open is True:
                return "path_open", True, None
            if path_open is False:
                try:
                    tree = ast.parse(textwrap.dedent(segment).strip())
                    calls = [item for item in ast.walk(tree) if isinstance(item, ast.Call)]
                    if len(calls) == 1 and isinstance(calls[0].func, ast.Attribute) and calls[0].func.attr == "open":
                        receiver = calls[0].func.value
                        if isinstance(receiver, ast.Name) and receiver.id in _OUT_OF_SCOPE_OPEN_RECEIVERS:
                            return None, True, None
                        return None, True, "missing_framework_context"
                except SyntaxError:
                    return None, False, None
        return None, False, None
    if name == OPEN_CALLEE:
        return "direct_open", True, None
    return None, True, None


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
) -> tuple[list[dict[str, Any]], bool, str | None]:
    if node.get("kind") != "call":
        return [], True, None
    want_dynamic = "code.dynamic_execution" in enabled
    want_open = "code.unmanaged_open" in enabled
    if not want_dynamic and not want_open:
        return [], True, None
    findings: list[dict[str, Any]] = []
    open_gap: str | None = None
    if want_open:
        form, open_evaluable, gap_reason = _resolve_open_form(node)
        if not open_evaluable:
            return [], False, None
        if gap_reason:
            open_gap = gap_reason
        elif form in {"direct_open", "path_open"}:
            used_as_with_context, context_known = _resolve_with_context(node)
            if not context_known:
                return [], False, None
            if used_as_with_context is False:
                findings.append(
                    _finding(
                        "code.unmanaged_open",
                        _open_message(form=form),
                        _evidence(
                            path,
                            file_item,
                            node,
                            callee_name=OPEN_CALLEE,
                            open_form=form,
                            used_as_with_context=False,
                        ),
                    )
                )
    if want_dynamic:
        name, evaluable = _resolve_direct_callee(node)
        if not evaluable:
            return findings, False, open_gap
        if name in DYNAMIC_CALLEES:
            findings.append(
                _finding(
                    "code.dynamic_execution",
                    _dynamic_message(str(name)),
                    _evidence(path, file_item, node, callee_name=name),
                )
            )
    return findings, True, open_gap


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


def _credential_name(name: str) -> bool:
    return name.casefold() in CREDENTIAL_BINDING_NAMES


def _placeholder_value(text: str) -> bool:
    return text.casefold() in SECRET_PLACEHOLDERS


def _secret_qualifies(facts: dict[str, Any]) -> bool:
    text = facts.get("literal_text")
    length = facts.get("literal_length")
    return (
        facts.get("literal_kind") == "str"
        and isinstance(text, str)
        and isinstance(length, int)
        and not isinstance(length, bool)
        and length >= SECRET_LITERAL_MIN_LENGTH
        and len(text) == length
        and not _placeholder_value(text)
    )


def _value_preview(text: str) -> str:
    return f"{text[:2]}…{text[-2:]}"


def _prepared_segment(segment: str) -> str:
    return textwrap.dedent(segment).strip("\n")


def _one_statement(segment: str) -> ast.stmt | None:
    prepared = _prepared_segment(segment)
    if not prepared.strip():
        return None
    try:
        tree = ast.parse(prepared)
    except SyntaxError:
        return None
    if len(tree.body) != 1:
        return None
    return tree.body[0]


def _one_expression(segment: str) -> ast.expr | None:
    prepared = _prepared_segment(segment)
    if not prepared.strip():
        return None
    try:
        expression = ast.parse(prepared, mode="eval")
    except SyntaxError:
        return None
    body = expression.body
    return body if isinstance(body, ast.expr) else None


def _value_facts(source: str, value: ast.AST) -> dict[str, Any]:
    return _literal_facts(value, _expr_text(source, value))


def _assignment_bindings(statement: ast.Assign | ast.AnnAssign, source: str) -> list[tuple[str, str, dict[str, Any]]]:
    if statement.value is None:
        return []
    facts = _value_facts(source, statement.value)
    targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
    bindings: list[tuple[str, str, dict[str, Any]]] = []
    for target in targets:
        if isinstance(target, ast.Name):
            bindings.append((target.id, "name_assignment", facts))
        elif isinstance(target, ast.Attribute):
            bindings.append((target.attr, "attribute_assignment", facts))
    return bindings


def _assignment_labels(statement: ast.Assign | ast.AnnAssign, source: str) -> list[str]:
    targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
    return [text for target in targets if (text := _expr_text(source, target))]


def _call_keyword_facts(call: ast.Call, source: str) -> dict[str, dict[str, Any]]:
    facts: dict[str, dict[str, Any]] = {}
    for keyword in call.keywords:
        if isinstance(keyword.arg, str):
            facts[keyword.arg] = _value_facts(source, keyword.value)
    return facts


def _keywords_from_segment(segment: str) -> dict[str, dict[str, Any]] | None:
    prepared = _prepared_segment(segment)
    expression = _one_expression(prepared)
    if isinstance(expression, ast.Call):
        return _call_keyword_facts(expression, prepared)
    wrapped_source = f"_({prepared})"
    wrapped = _one_expression(wrapped_source)
    if isinstance(wrapped, ast.Call):
        return _call_keyword_facts(wrapped, wrapped_source)
    return None


def _parameter_defaults(function: ast.FunctionDef | ast.AsyncFunctionDef, source: str) -> list[tuple[str, dict[str, Any], int, int]]:
    args = function.args
    positional = list(getattr(args, "posonlyargs", [])) + list(args.args)
    offset = len(positional) - len(args.defaults)
    found: list[tuple[str, dict[str, Any], int, int]] = []
    for index, default in enumerate(args.defaults):
        parameter = positional[offset + index]
        end_line = getattr(default, "end_lineno", None) or default.lineno
        found.append((parameter.arg, _value_facts(source, default), parameter.lineno, end_line))
    for parameter, default in zip(args.kwonlyargs, args.kw_defaults):
        if default is None:
            continue
        end_line = getattr(default, "end_lineno", None) or default.lineno
        found.append((parameter.arg, _value_facts(source, default), parameter.lineno, end_line))
    return found


def _recorded_literal(details: dict[str, Any]) -> dict[str, Any] | None:
    kind = details.get("literal_kind")
    if kind == "str":
        text = details.get("literal_text")
        length = details.get("literal_length")
        if isinstance(text, str) and isinstance(length, int) and not isinstance(length, bool) and len(text) == length:
            return {"literal_kind": "str", "literal_length": length, "literal_text": text}
        return None
    if kind in {"bytes", "implicit_str_concat", "non_literal"}:
        return {"literal_kind": kind, "literal_length": None, "literal_text": None}
    return None


def _recover_literal_bindings(segment: str | None, truncated: bool) -> list[tuple[str, str, dict[str, Any]]] | None:
    if truncated or not isinstance(segment, str) or not segment.strip():
        return None
    statement = _one_statement(segment)
    prepared = _prepared_segment(segment)
    if isinstance(statement, (ast.Assign, ast.AnnAssign)):
        return _assignment_bindings(statement, prepared)
    keywords = _keywords_from_segment(segment)
    parameter_text = f"def _({prepared}):\n    pass\n"
    parameter_statement = _one_statement(parameter_text)
    defaults = None
    if isinstance(parameter_statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
        defaults = _parameter_defaults(parameter_statement, parameter_text)
    # A bare name=value slice is both a keyword and a default. The form is not known.
    if keywords is not None and defaults is not None:
        return None
    if keywords is not None:
        return [(name, "keyword_argument", facts) for name, facts in keywords.items()]
    if defaults is not None:
        return [(name, "parameter_default", facts) for name, _facts, _start, _end in (
            (item[0], item[1], item[2], item[3]) for item in defaults
        )]
    return None


def _line_overlap(origin: int, lineno: int, end_lineno: int | None, changed_lines: set[int]) -> list[int]:
    start = origin + lineno - 1
    end = origin + (end_lineno or lineno) - 1
    return sorted(line for line in changed_lines if start <= line <= end)


def _narrow_node(node: dict[str, Any], start_line: int, end_line: int, changed_lines: list[int], segment: str | None) -> dict[str, Any]:
    narrowed = dict(node)
    narrowed["start_line"] = start_line
    narrowed["end_line"] = end_line
    narrowed["changed_lines"] = changed_lines
    if segment:
        narrowed["source_segment"] = segment
        narrowed.pop("source_segment_truncated", None)
    return narrowed


def _secret_from_parts(
    path: str,
    file_item: dict[str, Any],
    node: dict[str, Any],
    bindings: list[tuple[str, str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for name, form, facts in bindings:
        if not _credential_name(name) or not _secret_qualifies(facts):
            continue
        text = str(facts["literal_text"])
        findings.append(
            _finding(
                "code.hardcoded_secret",
                _secret_message(name, form, int(facts["literal_length"])),
                _evidence(
                    path,
                    file_item,
                    node,
                    binding_name=name,
                    binding_form=form,
                    value_length=int(facts["literal_length"]),
                    value_preview=_value_preview(text),
                ),
            )
        )
    return findings


def _mutable_finding(
    path: str,
    file_item: dict[str, Any],
    node: dict[str, Any],
    form: str,
    targets: list[str],
    value_kind: str | None = None,
) -> dict[str, Any]:
    details: dict[str, Any] = {"mutable_state_form": form, "binding_targets": targets}
    if value_kind is not None:
        details["value_kind"] = value_kind
    return _finding(
        "code.global_mutable_state",
        _mutable_message(form, targets),
        _evidence(path, file_item, node, **details),
    )


def _scan_legacy_function(node: dict[str, Any]) -> dict[str, list[dict[str, Any]]] | None:
    """Recover globals, nested class containers, and credential bindings from one function slice."""
    if node.get("source_segment_truncated"):
        return None
    segment = node.get("source_segment")
    origin = node.get("start_line")
    if not isinstance(segment, str) or not segment.strip() or not isinstance(origin, int):
        return None
    prepared = _prepared_segment(segment)
    statement = _one_statement(segment)
    if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None
    changed = {int(line) for line in node.get("changed_lines") or []}
    secrets: list[dict[str, Any]] = []
    mutables: list[dict[str, Any]] = []

    def add_secret(name: str, form: str, facts: dict[str, Any], lineno: int, end_lineno: int | None, source_segment: str | None) -> None:
        lines = _line_overlap(origin, lineno, end_lineno, changed)
        if not lines or not _credential_name(name) or not _secret_qualifies(facts):
            return
        secrets.append({
            "name": name,
            "form": form,
            "facts": facts,
            "start_line": origin + lineno - 1,
            "end_line": origin + (end_lineno or lineno) - 1,
            "lines": lines,
            "segment": source_segment,
        })

    def add_mutable(form: str, targets: list[str], lineno: int, end_lineno: int | None, value_kind: str | None, source_segment: str | None) -> None:
        lines = _line_overlap(origin, lineno, end_lineno, changed)
        if not lines or not targets:
            return
        mutables.append({
            "form": form,
            "targets": targets,
            "value_kind": value_kind,
            "start_line": origin + lineno - 1,
            "end_line": origin + (end_lineno or lineno) - 1,
            "lines": lines,
            "segment": source_segment,
        })

    def walk(statements: list[ast.stmt], scope: str) -> None:
        for item in statements:
            if isinstance(item, ast.Global) and scope == "function":
                add_mutable("global_statement", list(item.names), item.lineno, item.end_lineno, None, ast.get_source_segment(prepared, item))
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for name, facts, lineno, end_lineno in _parameter_defaults(item, prepared):
                    add_secret(name, "parameter_default", facts, lineno, end_lineno, ast.get_source_segment(prepared, item.args))
                walk(item.body, "function")
            elif isinstance(item, ast.ClassDef):
                walk(item.body, "class")
            elif isinstance(item, (ast.Assign, ast.AnnAssign)):
                if item.value is not None and scope == "class":
                    kind = _container_kind(item.value)
                    if kind is not None:
                        add_mutable(
                            "mutable_binding",
                            _assignment_labels(item, prepared),
                            item.lineno,
                            item.end_lineno,
                            kind,
                            ast.get_source_segment(prepared, item),
                        )
                if item.value is not None:
                    segment_text = ast.get_source_segment(prepared, item)
                    for name, form, facts in _assignment_bindings(item, prepared):
                        add_secret(name, form, facts, item.lineno, item.end_lineno, segment_text)
            elif isinstance(item, ast.If):
                walk(item.body, scope)
                walk(item.orelse, scope)
            elif isinstance(item, (ast.For, ast.AsyncFor, ast.While)):
                walk(item.body, scope)
                walk(item.orelse, scope)
            elif isinstance(item, (ast.With, ast.AsyncWith)):
                walk(item.body, scope)
            elif isinstance(item, (ast.Try, ast.TryStar)):
                walk(item.body, scope)
                for handler in item.handlers:
                    walk(handler.body, scope)
                walk(item.orelse, scope)
                walk(item.finalbody, scope)
            elif isinstance(item, ast.Match):
                for case in item.cases:
                    walk(case.body, scope)

    for name, facts, lineno, end_lineno in _parameter_defaults(statement, prepared):
        add_secret(name, "parameter_default", facts, lineno, end_lineno, ast.get_source_segment(prepared, statement.args))
    walk(statement.body, "function")
    return {"secrets": secrets, "mutables": mutables}


def _legacy_function_findings(
    path: str,
    file_item: dict[str, Any],
    node: dict[str, Any],
    *,
    secrets: bool,
    mutables: bool,
) -> tuple[list[dict[str, Any]], bool]:
    scanned = _scan_legacy_function(node)
    if scanned is None:
        return [], False
    findings: list[dict[str, Any]] = []
    if secrets:
        for item in scanned["secrets"]:
            narrowed = _narrow_node(node, item["start_line"], item["end_line"], item["lines"], item["segment"])
            findings.extend(_secret_from_parts(path, file_item, narrowed, [(item["name"], item["form"], item["facts"])]))
    if mutables:
        for item in scanned["mutables"]:
            narrowed = _narrow_node(node, item["start_line"], item["end_line"], item["lines"], item["segment"])
            findings.append(_mutable_finding(path, file_item, narrowed, item["form"], item["targets"], item["value_kind"]))
    return findings, True


def _group_legacy_fields(file_item: dict[str, Any]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for node in _head_nodes(file_item):
        if node.get("kind") != "field":
            continue
        if "value_form" in (node.get("details") or {}):
            continue
        key = (node.get("start_line"), node.get("end_line"), node.get("source_segment"))
        groups.setdefault(key, []).append(node)
    return groups


def _legacy_field_assignment(node: dict[str, Any]) -> tuple[ast.Assign | ast.AnnAssign, str] | None:
    if node.get("source_segment_truncated"):
        return None
    segment = node.get("source_segment")
    if not isinstance(segment, str) or not segment.strip():
        return None
    statement = _one_statement(segment)
    if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
        return None
    return statement, _prepared_segment(segment)


def _secret_findings(
    path: str,
    file_item: dict[str, Any],
    node: dict[str, Any],
    enabled: set[str],
    *,
    legacy_snapshot: bool,
) -> tuple[list[dict[str, Any]], bool, bool]:
    """Return findings, evaluable, and whether this node was in the rule's context.

    The third value only feeds rule outcomes. It does not change which findings
    are emitted.
    """
    if "code.hardcoded_secret" not in enabled:
        return [], True, False
    kind = node.get("kind")
    if kind == "literal_binding":
        details = node.get("details") or {}
        recorded = _recorded_literal(details)
        form = details.get("binding_form")
        name = details.get("binding_name")
        if isinstance(name, str) and form in BINDING_FORMS and recorded is not None:
            return _secret_from_parts(path, file_item, node, [(name, str(form), recorded)]), True, True
        recovered = _recover_literal_bindings(node.get("source_segment"), bool(node.get("source_segment_truncated")))
        if recovered is None:
            return [], False, True
        return _secret_from_parts(path, file_item, node, recovered), True, True
    if not legacy_snapshot:
        return [], True, False
    if kind == "field":
        field_name = node.get("name")
        details = node.get("details") or {}
        if isinstance(field_name, str) and not _credential_name(field_name):
            return [], True, True
        if isinstance(field_name, str) and "value_fingerprint" in details and details.get("value_fingerprint") is None:
            return [], True, True
        parsed = _legacy_field_assignment(node)
        if parsed is None:
            return [], False, True
        statement, source = parsed
        bindings = _assignment_bindings(statement, source)
        if isinstance(field_name, str):
            bindings = [item for item in bindings if item[0] == field_name and item[1] == "name_assignment"]
        return _secret_from_parts(path, file_item, node, bindings), True, True
    if kind == "call":
        details = node.get("details") or {}
        recovered = None
        if not node.get("source_segment_truncated") and isinstance(node.get("source_segment"), str):
            recovered = _keywords_from_segment(node["source_segment"])
        if "keyword_names" in details and isinstance(details.get("keyword_names"), list):
            names = [item for item in details["keyword_names"] if isinstance(item, str) and _credential_name(item)]
            if not names:
                return [], True, True
            if recovered is None:
                return [], False, True
            bindings = []
            for name in names:
                facts = recovered.get(name)
                if facts is None:
                    return [], False, True
                bindings.append((name, "keyword_argument", facts))
            return _secret_from_parts(path, file_item, node, bindings), True, True
        if recovered is None:
            return [], False, True
        bindings = [(name, "keyword_argument", facts) for name, facts in recovered.items()]
        return _secret_from_parts(path, file_item, node, bindings), True, True
    if kind in {"function", "async_function"}:
        if (node.get("details") or {}).get("literal_bindings_recorded") is True:
            return [], True, True
        findings, evaluable = _legacy_function_findings(path, file_item, node, secrets=True, mutables=False)
        return findings, evaluable, True
    return [], True, False


def _mutable_findings(
    path: str,
    file_item: dict[str, Any],
    node: dict[str, Any],
    enabled: set[str],
    *,
    field_findings: dict[str, list[dict[str, Any]]],
    field_gaps: set[str],
) -> tuple[list[dict[str, Any]], bool, bool]:
    """Return findings, evaluable, and whether this node was in the rule's context."""
    if "code.global_mutable_state" not in enabled:
        return [], True, False
    kind = node.get("kind")
    if kind == "mutable_state":
        details = node.get("details") or {}
        form = details.get("mutable_state_form")
        targets = details.get("binding_targets")
        recorded = form in {"global_statement", "mutable_binding"} and isinstance(targets, list) and all(isinstance(item, str) and item for item in targets)
        if recorded and form == "mutable_binding" and details.get("value_kind") not in MUTABLE_VALUE_KINDS:
            recorded = False
        if recorded:
            return [_mutable_finding(path, file_item, node, str(form), list(targets), details.get("value_kind"))], True, True
        if node.get("source_segment_truncated") or not isinstance(node.get("source_segment"), str):
            return [], False, True
        statement = _one_statement(node["source_segment"])
        prepared = _prepared_segment(node["source_segment"])
        if isinstance(statement, ast.Global) and statement.names:
            return [_mutable_finding(path, file_item, node, "global_statement", list(statement.names))], True, True
        if isinstance(statement, (ast.Assign, ast.AnnAssign)) and statement.value is not None:
            value_kind = _container_kind(statement.value)
            labels = _assignment_labels(statement, prepared)
            if value_kind and labels:
                return [_mutable_finding(path, file_item, node, "mutable_binding", labels, value_kind)], True, True
            if value_kind is None:
                return [], True, True
        return [], False, True
    if kind == "field":
        node_id = str(node.get("node_id") or "")
        if "value_form" in (node.get("details") or {}):
            return [], True, False
        if node_id in field_gaps:
            return [], False, True
        return field_findings.get(node_id, []), True, True
    if kind in {"function", "async_function"}:
        details = node.get("details") or {}
        if isinstance(details.get("contains_global_statement"), bool):
            return [], True, True
        findings, evaluable = _legacy_function_findings(path, file_item, node, secrets=False, mutables=True)
        return findings, evaluable, True
    return [], True, False


def _legacy_mutable_field_index(path: str, file_item: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], set[str]]:
    findings: dict[str, list[dict[str, Any]]] = {}
    gaps: set[str] = set()
    for group in _group_legacy_fields(file_item).values():
        node_ids = [str(node.get("node_id") or "") for node in group]
        parsed = _legacy_field_assignment(group[0])
        if parsed is None:
            gaps.update(node_ids)
            continue
        statement, source = parsed
        if statement.value is None:
            continue
        value_kind = _container_kind(statement.value)
        if value_kind is None:
            continue
        labels = _assignment_labels(statement, source)
        if not labels:
            gaps.update(node_ids)
            continue
        findings[node_ids[0]] = [_mutable_finding(path, file_item, group[0], "mutable_binding", labels, value_kind)]
    return findings, gaps


def _dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse the same 006 binding recovered from both an outer and an inner slice.

    Other rules keep one finding per node. Their evidence often shares a legacy
    fixture's line span, so this key must not apply to them.
    """
    seen: set[tuple[Any, ...]] = set()
    unique: list[dict[str, Any]] = []
    for item in findings:
        if item["rule_id"] not in {"code.hardcoded_secret", "code.global_mutable_state"}:
            unique.append(item)
            continue
        evidence = item["evidence"][0]
        key = (
            evidence.get("path"),
            item["rule_id"],
            evidence.get("binding_form") or evidence.get("mutable_state_form"),
            evidence.get("binding_name"),
            tuple(evidence.get("binding_targets") or []),
            evidence.get("start_line"),
            evidence.get("end_line"),
            evidence.get("value_length"),
            evidence.get("value_kind"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def collect_code_smell_findings(
    stage04_record: dict[str, Any],
    enabled: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Match evaluable head nodes.

    Findings and ``summary.unanalyzed`` stay on the existing path. The trace
    records, per enabled smell rule, how many in-context nodes finished and
    which nodes could not. A suppressed finding is a gap, not a completed miss.
    """
    if not enabled.intersection(_RULES_BY_ID):
        return [], [], {}
    findings: list[dict[str, Any]] = []
    gaps: dict[str, list[tuple[str, str] | str]] = {}
    trace: dict[str, dict[str, Any]] = {
        rule_id: {"examined": 0, "gaps": []}
        for rule_id in _RULES_BY_ID
        if rule_id in enabled
    }

    def mark_gap(rule_id: str, path: str, node_id: str) -> None:
        trace[rule_id]["gaps"].append({"path": path, "node_id": node_id})

    def mark_examined(rule_id: str) -> None:
        trace[rule_id]["examined"] += 1

    def note(rule_id: str, ok: bool, considered: bool, produced: list[dict[str, Any]], all_ok: bool, path: str, node_id: str) -> None:
        if rule_id not in trace or not considered:
            return
        suppressed = (not all_ok) and any(item["rule_id"] == rule_id for item in produced)
        if not ok or suppressed:
            mark_gap(rule_id, path, node_id)
            return
        mark_examined(rule_id)

    for file_item in stage04_record.get("files", []):
        path = str(file_item.get("path") or file_item.get("new_path") or file_item.get("old_path") or "")
        head_nodes = _head_nodes(file_item)
        legacy_secret_snapshot = not any(node.get("kind") == "literal_binding" for node in head_nodes)
        field_findings, field_gaps = ({}, set())
        if "code.global_mutable_state" in enabled:
            field_findings, field_gaps = _legacy_mutable_field_index(path, file_item)
        for node in head_nodes:
            handler_findings, handler_ok = _handler_findings(path, file_item, node, enabled)
            call_findings, call_ok, open_gap = _call_findings(path, file_item, node, enabled)
            control_findings, control_ok = _control_findings(path, file_item, node, enabled)
            secret_findings, secret_ok, secret_considered = _secret_findings(
                path,
                file_item,
                node,
                enabled,
                legacy_snapshot=legacy_secret_snapshot,
            )
            mutable_node_findings, mutable_ok, mutable_considered = _mutable_findings(
                path,
                file_item,
                node,
                enabled,
                field_findings=field_findings,
                field_gaps=field_gaps,
            )
            all_ok = handler_ok and call_ok and control_ok and secret_ok and mutable_ok
            node_id = str(node.get("node_id") or "")
            if node.get("kind") == "except_handler":
                for rule_id in ("code.swallowed_exception", "code.bare_exception"):
                    note(rule_id, handler_ok, True, handler_findings, all_ok, path, node_id)
            if node.get("kind") == "call" and ({"code.dynamic_execution", "code.unmanaged_open"} & enabled):
                form, open_evaluable, gap_reason = _resolve_open_form(node)
                name, callee_known = _resolve_direct_callee(node)
                if not callee_known and form is None and not gap_reason:
                    for rule_id in ("code.dynamic_execution", "code.unmanaged_open"):
                        if rule_id in trace:
                            mark_gap(rule_id, path, node_id)
                else:
                    note("code.dynamic_execution", callee_known, "code.dynamic_execution" in trace, call_findings, all_ok, path, node_id)
                    if "code.unmanaged_open" in trace:
                        if gap_reason or open_gap:
                            mark_gap("code.unmanaged_open", path, node_id)
                            gaps.setdefault(path, []).append((node_id, open_gap or gap_reason or "missing_framework_context"))
                        elif form in {"direct_open", "path_open"}:
                            _used_as_with, with_known = _resolve_with_context(node)
                            note("code.unmanaged_open", with_known and open_evaluable, True, call_findings, all_ok, path, node_id)
                        else:
                            note("code.unmanaged_open", True, True, call_findings, all_ok, path, node_id)
            if node.get("kind") == "control_flow":
                note("code.deep_control_flow", control_ok, True, control_findings, all_ok, path, node_id)
            note("code.hardcoded_secret", secret_ok, secret_considered, secret_findings, all_ok, path, node_id)
            note("code.global_mutable_state", mutable_ok, mutable_considered, mutable_node_findings, all_ok, path, node_id)
            if all_ok:
                findings.extend(handler_findings)
                findings.extend(call_findings)
                findings.extend(control_findings)
                findings.extend(secret_findings)
                findings.extend(mutable_node_findings)
                continue
            gaps.setdefault(path, []).append((node_id, "unsupported_stage04_details"))
    findings = _dedupe_findings(findings)
    findings.sort(
        key=lambda item: (
            item["evidence"][0].get("path") or "",
            item["rule_id"],
            item["evidence"][0].get("start_line") or 0,
            item["evidence"][0].get("node_id") or "",
        )
    )
    unanalyzed = []
    for path, entries in sorted(gaps.items()):
        by_reason: dict[str, list[str]] = {}
        for entry in entries:
            if isinstance(entry, tuple):
                node_id, reason = entry
            else:
                node_id, reason = entry, "unsupported_stage04_details"
            by_reason.setdefault(reason, []).append(node_id)
        for reason, node_ids in sorted(by_reason.items()):
            unanalyzed.append({
                "path": path,
                "reason": reason,
                "node_ids": sorted(set(node_ids)),
            })
    return findings, unanalyzed, trace
