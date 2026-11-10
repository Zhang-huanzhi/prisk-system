"""Second high-value draft detector batch for task 022.

Six rules land as Finding paths with Hit / NotFound / Unanalyzed terminals.
Hits are review clues. Lifecycle promotion happens in the registry when
constructive tests pass; default weight stays 0.
"""

from __future__ import annotations

import ast
import re
import textwrap
from typing import Any

from .framework_bases import resolve_class_bases


DECORATOR_REMOVED_ID = "auth.drf_permission_decorator_removed"
QUERYSET_BYPASS_ID = "auth.drf_queryset_scope_tighten_bypassed"
SIGNAL_LEAK_ID = "data.django_signal_receiver_leak"
FIELD_RENAME_ID = "data.django_field_rename_without_db_column"
PARAM_ADDED_ID = "api.drf_public_parameter_added"
PARAM_REMOVED_ID = "api.drf_public_parameter_removed"

SECOND_BATCH_RULES: list[dict[str, str]] = [
    {
        "rule_id": DECORATOR_REMOVED_ID,
        "severity": "high",
        "trigger": "同一所有者上闭集权限装饰器在 base 有、head 无，且与删除行相交；同文件无 permission_classes 赋值",
        "evidence_type": "code_slice",
        "suggested_action": "复核装饰器是否改成类属性、全局默认权限，以及该视图是否挂在 URL 上。命中不表示请求已越权。",
        "limitations": "五段闭集名字。同文件出现 permission_classes 赋值记 Unanalyzed。别名与截断记 Unanalyzed。",
    },
    {
        "rule_id": QUERYSET_BYPASS_ID,
        "severity": "high",
        "trigger": "闭集 ViewSet 上 get_queryset 返回未过滤 objects.all，且相对 base 为新形态并与新增行相交",
        "evidence_type": "code_slice",
        "suggested_action": "复核父类实现、permission_classes，以及该 ViewSet 是否挂在路由上。命中不表示行已对外可见。",
        "limitations": "只看本文件基类最后一段与映射表。返回切片截断或不在闭集的后续方法记 Unanalyzed。",
    },
    {
        "rule_id": SIGNAL_LEAK_ID,
        "severity": "medium",
        "trigger": "闭集信号的 connect 或 @receiver 与新增行相交，且确认没有 dispatch_uid",
        "evidence_type": "code_slice",
        "suggested_action": "复核接收器是函数还是绑定方法，以及连接是否在 ready()。命中不表示已重复执行。",
        "limitations": "十个模型/管理信号名。闭集外信号、**kwargs、connect 第四位置参数记 Unanalyzed。",
    },
    {
        "rule_id": FIELD_RENAME_ID,
        "severity": "high",
        "trigger": "非 migrations 路径上 Model/NetBoxModel 恰好一对字段名替换、构造器相同且新调用无 db_column",
        "evidence_type": "code_slice",
        "suggested_action": "复核生成的迁移是 RenameField 还是 RemoveField+AddField。命中不表示列数据已丢失。",
        "limitations": "只接受一对一配对。多字段或构造器不同记 Unanalyzed。不读迁移文件。",
    },
    {
        "rule_id": PARAM_ADDED_ID,
        "severity": "high",
        "trigger": "已有 Serializer 表面新增显式 required=True 且无 default= 的字段，或 @api_view/@action 新增无默认参数",
        "evidence_type": "code_slice",
        "suggested_action": "复核路由登记、partial 更新与发布说明。命中不表示线上客户端已失败。",
        "limitations": "省略 required 不猜默认。未列入基类与截断记 Unanalyzed。整类新建不记 Hit。",
    },
    {
        "rule_id": PARAM_REMOVED_ID,
        "severity": "high",
        "trigger": "已有 Serializer 或 @api_view/@action 表面上字段名/参数名消失，或可读 Meta.fields/exclude 成员删除",
        "evidence_type": "code_slice",
        "suggested_action": "复核发布说明与继承链。命中不表示客户端已失败。",
        "limitations": "基类同时变化记 Unanalyzed。不可读 Meta 列表记 Unanalyzed。不跟随父类文件。",
    },
]

_RULES_BY_ID = {rule["rule_id"]: rule for rule in SECOND_BATCH_RULES}
SECOND_BATCH_RULE_IDS = frozenset(_RULES_BY_ID)

_REASON_DETAILS = "unsupported_stage04_details"
_REASON_FRAMEWORK = "missing_framework_context"
_MIGRATIONS = re.compile(r"(?:^|/)migrations(?:/|$)", re.I)
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FIELD_CTOR = re.compile(r"(?:Field|ForeignKey|OneToOneField|ManyToManyField)$")

_PERM_DECORATORS = frozenset({
    "permission_classes",
    "authentication_classes",
    "login_required",
    "permission_required",
    "user_passes_test",
})
_VIEWSET_NATIVE = frozenset({"ViewSet", "GenericViewSet", "ModelViewSet", "ReadOnlyModelViewSet"})
_OBJECTS_ALL_TRAILING = frozenset({
    "select_related", "prefetch_related", "order_by", "distinct", "using", "only", "defer",
})
_SIGNAL_NAMES = frozenset({
    "pre_init", "post_init", "pre_save", "post_save", "pre_delete", "post_delete",
    "m2m_changed", "class_prepared", "pre_migrate", "post_migrate",
})
_OUT_OF_SET_SIGNALS = frozenset({
    "request_started", "request_finished", "got_request_exception",
    "setting_changed", "connection_created",
})
# Card: task signals are outside the closed set. Celery's documented task signal names.
_TASK_SIGNALS = frozenset({
    "before_task_publish", "after_task_publish", "task_sent", "task_prerun", "task_postrun",
    "task_retry", "task_success", "task_failure", "task_internal_error", "task_received",
    "task_revoked", "task_unknown", "task_rejected",
})
# Keyword names of Django's Signal.connect(receiver, sender, weak, dispatch_uid).
_SIGNAL_CONNECT_KEYWORDS = frozenset({"sender", "weak", "dispatch_uid"})
_CUSTOM_SIGNAL_BINDING = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]*)?=\s*(?:[A-Za-z_][A-Za-z0-9_.]*\.)?Signal\s*\("
)
_SERIALIZER_NATIVE = frozenset({"Serializer", "ModelSerializer"})
_MODEL_NATIVE = frozenset({"Model"})


def _path(file_item: dict[str, Any]) -> str:
    return str(file_item.get("path") or file_item.get("new_path") or file_item.get("old_path") or "")


def _migrations_path(path: str) -> bool:
    return bool(_MIGRATIONS.search(path.replace("\\", "/")))


def _last_segment(text: str | None) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None
    value = text.strip()
    if "(" in value:
        value = value.split("(", 1)[0].strip()
    segment = value.replace("\\", "/").rsplit(".", 1)[-1].strip()
    return segment if _IDENTIFIER.fullmatch(segment) else None


def _expr_last_segment(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr if _IDENTIFIER.fullmatch(node.attr) else None
    return None


def _parse_module(segment: str) -> ast.AST | None:
    prepared = textwrap.dedent(segment).strip("\n")
    if not prepared.strip():
        return None
    try:
        return ast.parse(prepared)
    except SyntaxError:
        return None


def _parse_expr(segment: str) -> ast.AST | None:
    tree = _parse_module(segment)
    if tree is None or len(tree.body) != 1:
        return None
    statement = tree.body[0]
    if isinstance(statement, ast.Expr):
        return statement.value
    return None


def _summary_gaps(gaps: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[str]] = {}
    for gap in gaps:
        grouped.setdefault((gap["path"], gap["reason"]), []).append(gap["node_id"])
    return [
        {"path": path, "reason": reason, "node_ids": sorted(set(node_ids))}
        for (path, reason), node_ids in sorted(grouped.items())
    ]


def _finding(rule_id: str, message: str, evidence: dict[str, Any], impact_type: str) -> dict[str, Any]:
    rule = _RULES_BY_ID[rule_id]
    return {
        "rule_id": rule_id,
        "severity": rule["severity"],
        "confidence": "structural",
        "message": message,
        "impact_type": impact_type,
        "evidence": [evidence],
        "suggested_action": rule["suggested_action"],
    }


def _base_evidence(path: str, node: dict[str, Any], **extra: Any) -> dict[str, Any]:
    evidence = {
        "path": path,
        "node_id": node.get("node_id"),
        "node_kind": node.get("kind"),
        "lines": sorted(set(node.get("changed_lines") or [])),
        "qualified_name": node.get("qualified_name"),
        "start_line": node.get("start_line"),
        "end_line": node.get("end_line"),
        "source_segment": node.get("source_segment"),
    }
    evidence.update(extra)
    return evidence


def _nodes(file_item: dict[str, Any], *, side: str | None = None, kind: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for node in file_item.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        if side is not None and node.get("side") != side:
            continue
        if kind is not None and node.get("kind") != kind:
            continue
        out.append(node)
    return out



def _changed(node: dict[str, Any]) -> bool:
    return bool(node.get("changed_lines"))


def _class_header_untouched(klass: dict[str, Any]) -> bool:
    """True when the class statement line itself is outside changed_lines."""
    start = klass.get("start_line")
    if not isinstance(start, int):
        return False
    return start not in set(klass.get("changed_lines") or [])


def _decorator_name(expression: str) -> str | None:
    text = expression.strip()
    if text.startswith("@"):
        text = text[1:]
    return _last_segment(text.split("(", 1)[0])


def _file_has_permission_classes_assign(file_item: dict[str, Any]) -> bool:
    for node in _nodes(file_item, side="head", kind="field"):
        if str(node.get("name") or "") == "permission_classes":
            return True
    for node in _nodes(file_item, side="head", kind="function") + _nodes(file_item, side="head", kind="class"):
        segment = str(node.get("source_segment") or "")
        if re.search(r"\bpermission_classes\s*=", segment):
            return True
    return False


def _head_fully_visible(file_item: dict[str, Any]) -> bool:
    """True only when every head line is an added line.

    stage04 keeps only nodes that intersect changed lines (structure._map_nodes),
    and detectors never receive the head source. The head module node spans
    1..line_count, so its changed_lines covering that range means no unchanged
    head line, and therefore no invisible node, exists.
    """
    parse_status = file_item.get("parse_status") if isinstance(file_item.get("parse_status"), dict) else {}
    if parse_status.get("head") != "ok":
        return False
    for node in _nodes(file_item, side="head", kind="module"):
        end_line = node.get("end_line")
        changed = node.get("changed_lines")
        if not isinstance(end_line, int) or not isinstance(changed, list):
            return False
        return set(range(1, end_line + 1)) <= {line for line in changed if isinstance(line, int)}
    return False


def _collect_decorator_removed(file_item: dict[str, Any], enabled: set[str]) -> tuple[list, list, dict]:
    if DECORATOR_REMOVED_ID not in enabled:
        return [], [], {}
    path = _path(file_item)
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    examined = 0
    suppress = _file_has_permission_classes_assign(file_item)
    fully_visible = _head_fully_visible(file_item)
    head_owners = {
        str(node.get("qualified_name") or node.get("name") or "")
        for node in _nodes(file_item, side="head", kind="function") + _nodes(file_item, side="head", kind="class")
    }
    # An owner absent from head nodes may simply be unchanged (stage04 only keeps
    # changed nodes). Treat it as removed only when its base node was deleted
    # line for line.
    removed_owners: set[str] = set()
    for node in _nodes(file_item, side="base", kind="function") + _nodes(file_item, side="base", kind="class"):
        name = str(node.get("qualified_name") or node.get("name") or "")
        start, end = node.get("start_line"), node.get("end_line")
        changed = node.get("changed_lines")
        if (
            name not in head_owners
            and isinstance(start, int)
            and isinstance(end, int)
            and isinstance(changed, list)
            and set(range(start, end + 1)) <= set(changed)
        ):
            removed_owners.add(name)
    for node in _nodes(file_item, side="base", kind="decorator"):
        if not _changed(node):
            continue
        details = node.get("details") if isinstance(node.get("details"), dict) else {}
        expression = str(details.get("expression") or node.get("source_segment") or "").strip()
        owner = str(details.get("owner") or "")
        node_id = str(node.get("node_id") or "")
        if owner and owner in removed_owners:
            continue
        if bool(node.get("source_segment_truncated")):
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
            continue
        name = _decorator_name(expression)
        if name is None:
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
            continue
        if name not in _PERM_DECORATORS:
            examined += 1
            continue
        still_present = False
        for head in _nodes(file_item, side="head", kind="decorator"):
            head_details = head.get("details") if isinstance(head.get("details"), dict) else {}
            if str(head_details.get("owner") or "") != owner:
                continue
            if str(head_details.get("expression") or head.get("source_segment") or "").strip() == expression:
                still_present = True
                break
        if still_present:
            examined += 1
            continue
        if suppress:
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
            continue
        if not fully_visible:
            # An unchanged `permission_classes = ...` elsewhere in head would be
            # invisible, so the card's same-file suppression cannot be ruled out.
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
            continue
        examined += 1
        findings.append(_finding(
            DECORATOR_REMOVED_ID,
            f"所有者 {owner or 'unknown'} 移除装饰器 {expression}。此线索只表示声明消失，不表示请求已越权。",
            _base_evidence(
                path, node,
                impact_type="external_impact",
                owner=owner,
                decorator_expression=expression,
                decorator_name=name,
            ),
            "external_impact",
        ))
    return findings, gaps, {"examined": examined, "gaps": gaps}


def _is_objects_all_call(node: ast.AST) -> dict[str, Any]:
    current = node
    trailing: list[str] = []
    while isinstance(current, ast.Call):
        func = current.func
        if not isinstance(func, ast.Attribute):
            return {"status": "other"}
        trailing.append(func.attr)
        current = func.value
        if func.attr == "all":
            break
    else:
        return {"status": "other"}
    if not isinstance(current, ast.Attribute) or current.attr != "objects":
        return {"status": "other"}
    after_methods = list(reversed(trailing[:-1]))
    for method in after_methods:
        if method in {"filter", "exclude", "none"}:
            return {"status": "filtered"}
        if method not in _OBJECTS_ALL_TRAILING:
            return {"status": "framework", "method": method}
    return {"status": "objects_all"}


def _return_forms(segment: str, *, truncated: bool) -> dict[str, Any]:
    if truncated:
        return {"status": "unsupported"}
    tree = _parse_module(segment)
    if tree is None:
        return {"status": "unsupported"}
    returns: list[ast.AST] = []
    if len(tree.body) == 1 and isinstance(tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
        for child in tree.body[0].body:
            if isinstance(child, ast.Return) and child.value is not None:
                returns.append(child.value)
            else:
                for sub in ast.walk(child):
                    if isinstance(sub, ast.Return) and sub.value is not None:
                        returns.append(sub.value)
    else:
        for sub in ast.walk(tree):
            if isinstance(sub, ast.Return) and sub.value is not None:
                returns.append(sub.value)
    if not returns:
        return {"status": "unsupported"}
    forms = [_is_objects_all_call(item) for item in returns]
    if any(item["status"] == "framework" for item in forms):
        return {"status": "framework"}
    if any(item["status"] == "objects_all" for item in forms):
        return {"status": "objects_all"}
    if any(item["status"] == "filtered" for item in forms):
        return {"status": "filtered"}
    return {"status": "other"}


def _has_super_get_queryset(segment: str, *, truncated: bool) -> bool | None:
    if truncated:
        return None
    tree = _parse_module(segment)
    if tree is None:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "get_queryset":
            continue
        try:
            text = ast.unparse(func.value)
        except Exception:
            return None
        if text.startswith("super"):
            return True
    return False


def _class_viewset_status(klass: dict[str, Any]) -> dict[str, Any]:
    details = klass.get("details") if isinstance(klass.get("details"), dict) else {}
    bases = details.get("base_expressions") or details.get("bases") or []
    resolved = resolve_class_bases(list(bases) if isinstance(bases, list) else [])
    natives = set(resolved.get("native_or_mapped_bases") or [])
    if natives & _VIEWSET_NATIVE:
        return {"status": "applicable", "bases": natives}
    if resolved.get("unlisted_last_segments") or resolved.get("has_unreadable_base"):
        return {"status": "framework", "bases": natives}
    return {"status": "out"}


def _collect_queryset_bypass(file_item: dict[str, Any], enabled: set[str]) -> tuple[list, list, dict]:
    if QUERYSET_BYPASS_ID not in enabled:
        return [], [], {}
    path = _path(file_item)
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    examined = 0

    classes: dict[str, dict[str, Any]] = {}
    for side in ("base", "head"):
        for klass in _nodes(file_item, side=side, kind="class"):
            name = str(klass.get("qualified_name") or klass.get("name") or "")
            classes.setdefault(name, {})[side] = klass
    methods: dict[str, dict[str, Any]] = {}
    for side in ("base", "head"):
        for func in _nodes(file_item, side=side, kind="function"):
            qname = str(func.get("qualified_name") or "")
            if not qname.endswith(".get_queryset"):
                continue
            methods.setdefault(qname, {})[side] = func

    for qname, sides in methods.items():
        owner = qname.rsplit(".", 1)[0]
        head = sides.get("head")
        base = sides.get("base")
        if head is None or not _changed(head):
            continue
        klass = (classes.get(owner) or {}).get("head") or (classes.get(owner) or {}).get("base")
        if klass is None:
            gaps.append({"path": path, "node_id": str(head.get("node_id") or ""), "reason": _REASON_FRAMEWORK})
            continue
        status = _class_viewset_status(klass)
        node_id = str(head.get("node_id") or "")
        if status["status"] == "framework":
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
            continue
        if status["status"] != "applicable":
            continue
        head_form = _return_forms(
            str(head.get("source_segment") or ""),
            truncated=bool(head.get("source_segment_truncated")),
        )
        if head_form["status"] == "unsupported":
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
            continue
        if head_form["status"] == "framework":
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
            continue
        base_form = None
        base_status = "absent"
        if base is not None:
            base_form = _return_forms(
                str(base.get("source_segment") or ""),
                truncated=bool(base.get("source_segment_truncated")),
            )
            if base_form["status"] == "unsupported":
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
                continue
            if base_form["status"] == "framework":
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
                continue
            base_status = str(base_form.get("status"))
        super_removed = False
        if base is not None:
            base_super = _has_super_get_queryset(
                str(base.get("source_segment") or ""),
                truncated=bool(base.get("source_segment_truncated")),
            )
            head_super = _has_super_get_queryset(
                str(head.get("source_segment") or ""),
                truncated=bool(head.get("source_segment_truncated")),
            )
            if base_super is True and head_super is False:
                super_removed = True
            base_seg = str(base.get("source_segment") or "")
            head_seg = str(head.get("source_segment") or "")
            if "restrict_queryset" in base_seg and "restrict_queryset" not in head_seg:
                if head_form["status"] != "objects_all":
                    gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
                    continue
        if head_form["status"] != "objects_all":
            if super_removed:
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
                continue
            examined += 1
            continue
        if base_form is not None and base_form.get("status") == "objects_all":
            examined += 1
            continue
        examined += 1
        evidence_extra: dict[str, Any] = {
            "impact_type": "external_impact",
            "class_name": owner,
            "return_form": "objects_all",
            "base_method": base_status,
        }
        if super_removed:
            evidence_extra["super_removed"] = True
        findings.append(_finding(
            QUERYSET_BYPASS_ID,
            f"ViewSet {owner} 的 get_queryset 返回未过滤 objects.all。此线索不表示行已对外可见。",
            _base_evidence(path, head, **evidence_extra),
            "external_impact",
        ))
    return findings, gaps, {"examined": examined, "gaps": gaps}


def _signal_from_receiver_call(segment: str, *, truncated: bool) -> dict[str, Any]:
    if truncated:
        return {"status": "unsupported"}
    tree = _parse_expr(segment)
    if tree is None:
        return {"status": "unsupported"}
    if not isinstance(tree, ast.Call) or _expr_last_segment(tree.func) != "receiver":
        return {"status": "other"}
    if not tree.args:
        return {"status": "unsupported"}
    names: list[str] = []
    first = tree.args[0]
    candidates = first.elts if isinstance(first, (ast.List, ast.Tuple)) else [first]
    for item in candidates:
        name = _expr_last_segment(item)
        if name is None:
            return {"status": "unsupported"}
        names.append(name)
    if any(name in _SIGNAL_NAMES for name in names):
        return {"status": "closed", "signals": names}
    return {"status": "framework", "signals": names}


def _custom_signal_names(file_item: dict[str, Any]) -> set[str]:
    """Names bound to ``Signal(...)`` in head nodes of the same file."""
    names: set[str] = set()
    for node in _nodes(file_item, side="head"):
        if node.get("kind") not in {"field", "literal_binding"}:
            continue
        match = _CUSTOM_SIGNAL_BINDING.match(str(node.get("source_segment") or ""))
        if match:
            names.add(match.group(1))
    return names


def _collect_signal_leak(file_item: dict[str, Any], enabled: set[str]) -> tuple[list, list, dict]:
    if SIGNAL_LEAK_ID not in enabled:
        return [], [], {}
    path = _path(file_item)
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    examined = 0
    seen_receiver_segments: set[str] = set()
    custom_signals = _custom_signal_names(file_item)
    for node in _nodes(file_item, side="head", kind="call"):
        if not _changed(node):
            continue
        details = node.get("details") if isinstance(node.get("details"), dict) else {}
        callee = str(details.get("callee") or "")
        last = _last_segment(callee)
        node_id = str(node.get("node_id") or "")
        keyword_names = details.get("keyword_names")
        if not isinstance(keyword_names, list):
            keyword_names = []
        has_star_kwargs = any(item is None for item in keyword_names)
        kw_set = {str(item) for item in keyword_names if isinstance(item, str)}
        if last == "connect":
            if "." not in callee:
                # Bare connect(...) is not a signal registration surface on the card.
                continue
            receiver = callee.rsplit(".", 1)[0]
            signal_name = _last_segment(receiver)
            if signal_name is None:
                # Card section 6: an unreadable receiver is a known miss, not a gap.
                continue
            if signal_name not in _SIGNAL_NAMES:
                # Card: names outside the closed set (request_finished, task signals,
                # custom Signal()) are Unanalyzed with missing_framework_context.
                if (
                    signal_name in _OUT_OF_SET_SIGNALS
                    or signal_name in _TASK_SIGNALS
                    or signal_name in custom_signals
                    or kw_set & _SIGNAL_CONNECT_KEYWORDS
                ):
                    gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
                continue
            if has_star_kwargs:
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
                continue
            args_count = details.get("args_count")
            if not isinstance(args_count, int):
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
                continue
            if args_count >= 4:
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
                continue
            examined += 1
            if "dispatch_uid" in kw_set:
                continue
            findings.append(_finding(
                SIGNAL_LEAK_ID,
                f"信号 {signal_name}.connect 缺少 dispatch_uid。此线索不表示接收器已重复执行。",
                _base_evidence(
                    path, node,
                    impact_type="pr_intrinsic_risk",
                    signal_name=signal_name,
                    connect_form="connect",
                    keyword_names=sorted(kw_set),
                    args_count=args_count,
                ),
                "pr_intrinsic_risk",
            ))
            continue
        if last == "receiver":
            segment = str(node.get("source_segment") or "")
            classified = _signal_from_receiver_call(
                segment,
                truncated=bool(node.get("source_segment_truncated")),
            )
            if classified["status"] == "unsupported":
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
                continue
            if classified["status"] == "framework":
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
                continue
            if classified["status"] != "closed":
                examined += 1
                continue
            if has_star_kwargs:
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
                continue
            examined += 1
            seen_receiver_segments.add(segment)
            if "dispatch_uid" in kw_set:
                continue
            signal_name = next(name for name in classified["signals"] if name in _SIGNAL_NAMES)
            findings.append(_finding(
                SIGNAL_LEAK_ID,
                f"@receiver({signal_name}) 缺少 dispatch_uid。此线索不表示接收器已重复执行。",
                _base_evidence(
                    path, node,
                    impact_type="pr_intrinsic_risk",
                    signal_name=signal_name,
                    connect_form="receiver",
                    keyword_names=sorted(kw_set),
                ),
                "pr_intrinsic_risk",
            ))
    for node in _nodes(file_item, side="head", kind="decorator"):
        if not _changed(node):
            continue
        details = node.get("details") if isinstance(node.get("details"), dict) else {}
        expression = str(details.get("expression") or node.get("source_segment") or "")
        if _decorator_name(expression) != "receiver":
            continue
        if expression in seen_receiver_segments:
            continue
        node_id = str(node.get("node_id") or "")
        classified = _signal_from_receiver_call(expression, truncated=bool(node.get("source_segment_truncated")))
        if classified["status"] == "unsupported":
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
            continue
        if classified["status"] == "framework":
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
            continue
        if classified["status"] != "closed":
            continue
        examined += 1
        if "dispatch_uid" in expression:
            continue
        signal_name = next(name for name in classified["signals"] if name in _SIGNAL_NAMES)
        findings.append(_finding(
            SIGNAL_LEAK_ID,
            f"@receiver({signal_name}) 缺少 dispatch_uid。此线索不表示接收器已重复执行。",
            _base_evidence(
                path, node,
                impact_type="pr_intrinsic_risk",
                signal_name=signal_name,
                connect_form="receiver",
            ),
            "pr_intrinsic_risk",
        ))
    return findings, gaps, {"examined": examined, "gaps": gaps}


def _is_field_ctor_name(name: str | None) -> bool:
    if not name:
        return False
    return bool(_FIELD_CTOR.search(name)) or name in {"ForeignKey", "OneToOneField", "ManyToManyField"}


def _class_model_status(klass: dict[str, Any]) -> dict[str, Any]:
    details = klass.get("details") if isinstance(klass.get("details"), dict) else {}
    bases = details.get("base_expressions") or details.get("bases") or []
    resolved = resolve_class_bases(list(bases) if isinstance(bases, list) else [])
    natives = set(resolved.get("native_or_mapped_bases") or [])
    if natives & _MODEL_NATIVE:
        return {"status": "applicable"}
    if resolved.get("unlisted_last_segments") or resolved.get("has_unreadable_base"):
        return {"status": "framework"}
    return {"status": "out"}


def _field_ctor_segment(node: dict[str, Any]) -> str | None:
    segment = str(node.get("source_segment") or "")
    if "=" in segment:
        return segment.split("=", 1)[1].strip()
    return segment or None


def _collect_field_rename(file_item: dict[str, Any], enabled: set[str]) -> tuple[list, list, dict]:
    if FIELD_RENAME_ID not in enabled:
        return [], [], {}
    path = _path(file_item)
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    examined = 0
    if _migrations_path(path):
        return [], [], {}

    classes: dict[str, dict[str, Any]] = {}
    for side in ("base", "head"):
        for klass in _nodes(file_item, side=side, kind="class"):
            name = str(klass.get("qualified_name") or klass.get("name") or "")
            if name.endswith(".Meta"):
                continue
            classes.setdefault(name, {})[side] = klass

    for class_name, sides in classes.items():
        if "base" not in sides or "head" not in sides:
            continue
        status = _class_model_status(sides["head"])
        if status["status"] == "out":
            status = _class_model_status(sides["base"])
        node_id = str(sides["head"].get("node_id") or "")
        if status["status"] == "framework":
            if _changed(sides["head"]) or _changed(sides["base"]):
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
            continue
        if status["status"] != "applicable":
            continue

        def inventory(side: str) -> dict[str, dict[str, Any]]:
            out: dict[str, dict[str, Any]] = {}
            for node in _nodes(file_item, side=side, kind="field"):
                qname = str(node.get("qualified_name") or "")
                if not qname.startswith(class_name + "."):
                    continue
                details = node.get("details") if isinstance(node.get("details"), dict) else {}
                if details.get("meta_option"):
                    continue
                field_name = str(node.get("name") or "")
                ctor_text = _field_ctor_segment(node)
                ctor = _last_segment(ctor_text.split("(")[0] if ctor_text else None)
                if not _is_field_ctor_name(ctor):
                    continue
                keywords = details.get("value_keyword_names")
                if not isinstance(keywords, list):
                    keywords = None
                out[field_name] = {
                    "node": node,
                    "ctor": ctor,
                    "keywords": keywords,
                    "segment": str(node.get("source_segment") or ""),
                }
            return out

        base_fields = inventory("base")
        head_fields = inventory("head")
        removed = sorted(set(base_fields) - set(head_fields))
        added = sorted(set(head_fields) - set(base_fields))
        if not removed and not added:
            if any(_changed(item["node"]) for item in head_fields.values()):
                examined += 1
            continue
        if len(removed) != 1 or len(added) != 1:
            if any(_changed(base_fields[name]["node"]) for name in removed) or any(
                _changed(head_fields[name]["node"]) for name in added
            ):
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
            continue
        old_name, new_name = removed[0], added[0]
        old = base_fields[old_name]
        new = head_fields[new_name]
        if not (_changed(old["node"]) or _changed(new["node"])):
            continue
        if old["ctor"] != new["ctor"]:
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
            continue
        keywords = new["keywords"]
        if keywords is None:
            keywords = []
            for call in _nodes(file_item, side="head", kind="call"):
                if not _changed(call):
                    continue
                if _last_segment((call.get("details") or {}).get("callee")) == new["ctor"]:
                    kw = (call.get("details") or {}).get("keyword_names")
                    if isinstance(kw, list):
                        keywords = kw
                        break
        if any(item is None for item in (keywords or [])):
            gaps.append({"path": path, "node_id": str(new["node"].get("node_id") or ""), "reason": _REASON_DETAILS})
            continue
        kw_set = {str(item) for item in (keywords or []) if isinstance(item, str)}
        if "db_column" in new["segment"] or "db_column" in kw_set:
            examined += 1
            continue
        examined += 1
        findings.append(_finding(
            FIELD_RENAME_ID,
            f"模型 {class_name} 字段 {old_name} → {new_name} 且未见 db_column。此线索不表示列数据已丢失。",
            _base_evidence(
                path, new["node"],
                impact_type="external_impact",
                class_name=class_name,
                old_field=old_name,
                new_field=new_name,
                constructor_name=new["ctor"],
            ),
            "external_impact",
        ))
    return findings, gaps, {"examined": examined, "gaps": gaps}


def _serializer_status(klass: dict[str, Any]) -> dict[str, Any]:
    details = klass.get("details") if isinstance(klass.get("details"), dict) else {}
    bases = details.get("base_expressions") or details.get("bases") or []
    resolved = resolve_class_bases(list(bases) if isinstance(bases, list) else [])
    natives = set(resolved.get("native_or_mapped_bases") or [])
    if natives & _SERIALIZER_NATIVE:
        return {"status": "applicable", "bases": natives}
    if resolved.get("unlisted_last_segments") or resolved.get("has_unreadable_base"):
        return {"status": "framework"}
    return {"status": "out"}


def _required_true_no_default(segment: str, *, truncated: bool, keyword_names: list[Any] | None) -> dict[str, Any]:
    if truncated:
        return {"status": "unsupported"}
    if keyword_names is not None and any(item is None for item in keyword_names):
        return {"status": "unsupported"}
    kw = {str(item) for item in (keyword_names or []) if isinstance(item, str)}
    if "default" in kw or re.search(r"\bdefault\s*=", segment):
        return {"status": "optional"}
    if "required" not in kw and not re.search(r"\brequired\s*=", segment):
        return {"status": "omitted"}
    if re.search(r"required\s*=\s*True\b", segment):
        return {"status": "required"}
    if re.search(r"required\s*=\s*False\b", segment):
        return {"status": "optional"}
    return {"status": "unsupported"}


def _has_public_view_decorator(decorators: list[Any]) -> bool:
    for item in decorators or []:
        name = _decorator_name(str(item))
        if name in {"api_view", "action"}:
            return True
    return False


def _collect_param_added(file_item: dict[str, Any], enabled: set[str]) -> tuple[list, list, dict]:
    if PARAM_ADDED_ID not in enabled:
        return [], [], {}
    path = _path(file_item)
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    examined = 0

    base_classes = {
        str(node.get("qualified_name") or node.get("name") or ""): node
        for node in _nodes(file_item, side="base", kind="class")
    }
    head_classes = {
        str(node.get("qualified_name") or node.get("name") or ""): node
        for node in _nodes(file_item, side="head", kind="class")
    }
    base_fields = {
        str(node.get("qualified_name") or ""): node
        for node in _nodes(file_item, side="base", kind="field")
    }
    for node in _nodes(file_item, side="head", kind="field"):
        if not _changed(node):
            continue
        qname = str(node.get("qualified_name") or "")
        if "." not in qname:
            continue
        details = node.get("details") if isinstance(node.get("details"), dict) else {}
        if details.get("meta_option"):
            continue
        owner = qname.rsplit(".", 1)[0]
        head_klass = head_classes.get(owner)
        if head_klass is None:
            continue
        base_klass = base_classes.get(owner)
        if base_klass is None and not _class_header_untouched(head_klass):
            # Brand-new class (class header itself is on added lines).
            examined += 1
            continue
        status = _serializer_status(head_klass)
        node_id = str(node.get("node_id") or "")
        if status["status"] == "framework":
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
            continue
        if status["status"] != "applicable":
            continue
        if qname in base_fields:
            examined += 1
            continue
        segment = str(node.get("source_segment") or "")
        classified = _required_true_no_default(
            segment,
            truncated=bool(node.get("source_segment_truncated")),
            keyword_names=details.get("value_keyword_names") if isinstance(details.get("value_keyword_names"), list) else None,
        )
        if classified["status"] == "unsupported":
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
            continue
        if classified["status"] == "omitted":
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
            continue
        examined += 1
        if classified["status"] != "required":
            continue
        findings.append(_finding(
            PARAM_ADDED_ID,
            f"序列化器 {owner} 新增必填字段 {node.get('name')}。此线索不表示客户端已失败。",
            _base_evidence(
                path, node,
                impact_type="pr_intrinsic_risk",
                class_name=owner,
                parameter_name=node.get("name"),
            ),
            "pr_intrinsic_risk",
        ))

    base_funcs = {
        str(node.get("qualified_name") or node.get("name") or ""): node
        for node in _nodes(file_item, side="base", kind="function")
    }
    for node in _nodes(file_item, side="head", kind="function"):
        if not _changed(node):
            continue
        qname = str(node.get("qualified_name") or node.get("name") or "")
        if qname not in base_funcs:
            continue
        details = node.get("details") if isinstance(node.get("details"), dict) else {}
        decorators = details.get("decorators") or []
        if not _has_public_view_decorator(decorators):
            continue
        base_details = base_funcs[qname].get("details") if isinstance(base_funcs[qname].get("details"), dict) else {}
        base_params = {
            str(item.get("name")): item
            for item in (base_details.get("signature") or {}).get("parameters") or []
            if isinstance(item, dict)
        }
        head_params = {
            str(item.get("name")): item
            for item in (details.get("signature") or {}).get("parameters") or []
            if isinstance(item, dict)
        }
        for name, item in head_params.items():
            if name in base_params or name in {"self", "cls"}:
                continue
            examined += 1
            if item.get("has_default"):
                continue
            findings.append(_finding(
                PARAM_ADDED_ID,
                f"公有视图 {qname} 新增无默认参数 {name}。此线索不表示客户端已失败。",
                _base_evidence(
                    path, node,
                    impact_type="pr_intrinsic_risk",
                    function_name=qname,
                    parameter_name=name,
                ),
                "pr_intrinsic_risk",
            ))
    return findings, gaps, {"examined": examined, "gaps": gaps}


def _collect_param_removed(file_item: dict[str, Any], enabled: set[str]) -> tuple[list, list, dict]:
    if PARAM_REMOVED_ID not in enabled:
        return [], [], {}
    path = _path(file_item)
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    examined = 0

    base_classes = {
        str(node.get("qualified_name") or node.get("name") or ""): node
        for node in _nodes(file_item, side="base", kind="class")
    }
    head_classes = {
        str(node.get("qualified_name") or node.get("name") or ""): node
        for node in _nodes(file_item, side="head", kind="class")
    }
    head_fields = {
        str(node.get("qualified_name") or ""): node
        for node in _nodes(file_item, side="head", kind="field")
    }

    for node in _nodes(file_item, side="base", kind="field"):
        if not _changed(node):
            continue
        details = node.get("details") if isinstance(node.get("details"), dict) else {}
        qname = str(node.get("qualified_name") or "")
        node_id = str(node.get("node_id") or "")
        if details.get("meta_option") in {"fields", "exclude"}:
            continue
        if "." not in qname:
            continue
        owner = qname.rsplit(".", 1)[0]
        base_klass = base_classes.get(owner)
        head_klass = head_classes.get(owner)
        if base_klass is None:
            continue
        status = _serializer_status(base_klass)
        if status["status"] == "framework":
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
            continue
        if status["status"] != "applicable":
            continue
        if head_klass is None:
            if not _class_header_untouched(base_klass):
                # Class header deleted with the field — not a same-surface removal.
                examined += 1
                continue
        else:
            base_bases = (base_klass.get("details") or {}).get("base_expressions") or (base_klass.get("details") or {}).get("bases")
            head_bases = (head_klass.get("details") or {}).get("base_expressions") or (head_klass.get("details") or {}).get("bases")
            if list(base_bases or []) != list(head_bases or []):
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
                continue
        if qname in head_fields:
            examined += 1
            continue
        if bool(node.get("source_segment_truncated")):
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
            continue
        examined += 1
        findings.append(_finding(
            PARAM_REMOVED_ID,
            f"序列化器 {owner} 删除字段 {node.get('name')}。此线索不表示客户端已失败。",
            _base_evidence(
                path, node,
                impact_type="pr_intrinsic_risk",
                class_name=owner,
                parameter_name=node.get("name"),
            ),
            "pr_intrinsic_risk",
        ))

    for owner, head_klass in head_classes.items():
        if not str(owner).endswith(".Meta"):
            continue
        base_klass = base_classes.get(owner)
        if base_klass is None:
            continue
        parent = owner.rsplit(".", 1)[0]
        parent_base = base_classes.get(parent)
        parent_head = head_classes.get(parent)
        if parent_base is None or parent_head is None:
            continue
        status = _serializer_status(parent_head)
        if status["status"] == "framework":
            if _changed(head_klass) or _changed(parent_head):
                gaps.append({"path": path, "node_id": str(head_klass.get("node_id") or ""), "reason": _REASON_FRAMEWORK})
            continue
        if status["status"] != "applicable":
            continue
        base_meta_fields = {
            str(node.get("name") or ""): node
            for node in _nodes(file_item, side="base", kind="field")
            if str(node.get("qualified_name") or "").startswith(owner + ".")
        }
        head_meta_fields = {
            str(node.get("name") or ""): node
            for node in _nodes(file_item, side="head", kind="field")
            if str(node.get("qualified_name") or "").startswith(owner + ".")
        }
        for option in ("fields", "exclude"):
            base_node = base_meta_fields.get(option)
            head_node = head_meta_fields.get(option)
            if base_node is None and head_node is None:
                continue
            probe = head_node or base_node
            if probe is None or not (_changed(probe) or (base_node and _changed(base_node))):
                continue
            base_details = (base_node or {}).get("details") if isinstance((base_node or {}).get("details"), dict) else {}
            head_details = (head_node or {}).get("details") if isinstance((head_node or {}).get("details"), dict) else {}
            if base_node and base_details.get("meta_list_kind") == "all" and head_node and head_details.get("meta_list_kind") == "list":
                gaps.append({"path": path, "node_id": str(probe.get("node_id") or ""), "reason": _REASON_FRAMEWORK})
                continue
            if head_node and head_details.get("meta_list_kind") == "all" and base_node and base_details.get("meta_list_kind") == "list":
                gaps.append({"path": path, "node_id": str(probe.get("node_id") or ""), "reason": _REASON_FRAMEWORK})
                continue
            if (base_node and base_details.get("meta_list_readable") is False) or (
                head_node and head_details.get("meta_list_readable") is False
            ):
                gaps.append({"path": path, "node_id": str(probe.get("node_id") or ""), "reason": _REASON_DETAILS})
                continue
            base_members = set(base_details.get("meta_list_members") or []) if base_node else set()
            head_members = set(head_details.get("meta_list_members") or []) if head_node else set()
            if option == "fields":
                removed_names = sorted(base_members - head_members)
            else:
                removed_names = sorted(head_members - base_members)
            if not removed_names:
                examined += 1
                continue
            for name in removed_names:
                examined += 1
                findings.append(_finding(
                    PARAM_REMOVED_ID,
                    f"序列化器 {parent} 的 Meta.{option} 去掉 {name}。此线索不表示客户端已失败。",
                    _base_evidence(
                        path, probe,
                        impact_type="pr_intrinsic_risk",
                        class_name=parent,
                        parameter_name=name,
                        meta_option=option,
                    ),
                    "pr_intrinsic_risk",
                ))

    head_funcs = {
        str(node.get("qualified_name") or node.get("name") or ""): node
        for node in _nodes(file_item, side="head", kind="function")
    }
    for node in _nodes(file_item, side="base", kind="function"):
        qname = str(node.get("qualified_name") or node.get("name") or "")
        details = node.get("details") if isinstance(node.get("details"), dict) else {}
        if not _has_public_view_decorator(details.get("decorators") or []):
            continue
        head = head_funcs.get(qname)
        if head is None:
            continue
        if not (_changed(node) or _changed(head)):
            continue
        head_details = head.get("details") if isinstance(head.get("details"), dict) else {}
        base_params = {
            str(item.get("name"))
            for item in (details.get("signature") or {}).get("parameters") or []
            if isinstance(item, dict)
        }
        head_params = {
            str(item.get("name"))
            for item in (head_details.get("signature") or {}).get("parameters") or []
            if isinstance(item, dict)
        }
        for name in sorted(base_params - head_params):
            if name in {"self", "cls"}:
                continue
            examined += 1
            findings.append(_finding(
                PARAM_REMOVED_ID,
                f"公有视图 {qname} 删除参数 {name}。此线索不表示客户端已失败。",
                _base_evidence(
                    path, node,
                    impact_type="pr_intrinsic_risk",
                    function_name=qname,
                    parameter_name=name,
                ),
                "pr_intrinsic_risk",
            ))
    return findings, gaps, {"examined": examined, "gaps": gaps}


SECOND_BATCH_COLLECTORS: list[tuple[str, Any]] = [
    (DECORATOR_REMOVED_ID, _collect_decorator_removed),
    (QUERYSET_BYPASS_ID, _collect_queryset_bypass),
    (SIGNAL_LEAK_ID, _collect_signal_leak),
    (FIELD_RENAME_ID, _collect_field_rename),
    (PARAM_ADDED_ID, _collect_param_added),
    (PARAM_REMOVED_ID, _collect_param_removed),
]


def collect_second_batch_findings(
    stage04_record: dict[str, Any],
    enabled: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if not (SECOND_BATCH_RULE_IDS & enabled):
        return [], [], {}
    findings: list[dict[str, Any]] = []
    all_gaps: list[dict[str, str]] = []
    traces: dict[str, dict[str, Any]] = {
        rule_id: {"examined": 0, "gaps": []} for rule_id in SECOND_BATCH_RULE_IDS if rule_id in enabled
    }
    for file_item in stage04_record.get("files") or []:
        if not isinstance(file_item, dict):
            continue
        if file_item.get("parse_status", {}).get("head") == "failed":
            continue
        for rule_id, collector in SECOND_BATCH_COLLECTORS:
            if rule_id not in enabled:
                continue
            part_findings, part_gaps, part_trace = collector(file_item, enabled)
            findings.extend(part_findings)
            all_gaps.extend(part_gaps)
            if rule_id not in traces:
                continue
            traces[rule_id]["examined"] += int(part_trace.get("examined") or 0)
            for gap in part_gaps:
                if gap not in traces[rule_id]["gaps"]:
                    traces[rule_id]["gaps"].append(gap)
    findings.sort(
        key=lambda item: (
            item["evidence"][0].get("path") or "",
            item["evidence"][0].get("start_line") or 0,
            item["evidence"][0].get("node_id") or "",
            item["rule_id"],
        )
    )
    return findings, _summary_gaps(all_gaps), traces
