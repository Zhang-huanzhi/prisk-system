"""High-value draft detectors for tasks 021 and 022.

021 six rules plus 022 second batch land as Finding paths with Hit / NotFound / Unanalyzed terminals.
Hits are review clues. They do not prove CSRF exploits, anonymous writes,
dropped tables, or production misconfiguration. Lifecycle promotion happens
in the registry when constructive tests pass; default weight stays 0.
"""

from __future__ import annotations

import ast
import re
import textwrap
from typing import Any

from .framework_bases import resolve_class_bases
from .second_batch_detectors import SECOND_BATCH_RULES, SECOND_BATCH_RULE_IDS, collect_second_batch_findings
from .sensitive_settings import SENSITIVE_SETTING_NAMES, classify_sensitive_direction


CSRF_RULE_ID = "auth.django_csrf_exempt_added"
VIEWSET_RULE_ID = "api.drf_viewset_action_changed"
DESTRUCTIVE_RULE_ID = "data.django_destructive_migration"
PERMISSION_RULE_ID = "auth.drf_permission_policy_downgrade"
SENSITIVE_RULE_ID = "config.django_sensitive_settings_changed"
NON_NULL_RULE_ID = "data.django_non_null_constraint_tightened"

HIGH_VALUE_RULES: list[dict[str, str]] = [
    {
        "rule_id": CSRF_RULE_ID,
        "severity": "high",
        "trigger": "同一所有者上新增 csrf_exempt 或 method_decorator(csrf_exempt)，且与新增行相交",
        "evidence_type": "code_slice",
        "suggested_action": "复核豁免是否有意、方法是否改状态，以及是否还有其他来源校验。命中不表示跨站请求已发生。",
        "limitations": "只匹配闭集两种装饰器形态。别名与截断记 Unanalyzed。不判断中间件是否启用。",
    },
    {
        "rule_id": VIEWSET_RULE_ID,
        "severity": "high",
        "trigger": "闭集 ViewSet 基类上标准动作或 @action 的有无或 detail/methods 文本变化，且与 diff 行相交",
        "evidence_type": "code_slice",
        "suggested_action": "复核 router 是否登记该类，以及动作集合变化是否有意。命中不表示 URL 已变。",
        "limitations": "只看本文件基类最后一段与映射表。不沿跨文件继承。不读 router。",
    },
    {
        "rule_id": DESTRUCTIVE_RULE_ID,
        "severity": "critical",
        "trigger": "migrations 路径段文件中与新增行相交的 DeleteModel 或 RemoveField 调用",
        "evidence_type": "code_slice",
        "suggested_action": "复核迁移依赖、数据备份与是否另有数据迁移。命中不表示生产库已丢数据。",
        "limitations": "不解析 RunSQL/RunPython 字符串。不建迁移图。非 migrations 路径同名调用记 Unanalyzed。",
    },
    {
        "rule_id": PERMISSION_RULE_ID,
        "severity": "high",
        "trigger": "permission_classes 或 @permission_classes 在 head 为 AllowAny 或空列表/元组，且 base 不是同形态",
        "evidence_type": "code_slice",
        "suggested_action": "复核全局默认与继承来的权限，以及该视图是否挂在 URL 上。命中不表示请求已匿名可写。",
        "limitations": "不比较自定义权限类强弱。组合运算符与别名记 Unanalyzed。",
    },
    {
        "rule_id": SENSITIVE_RULE_ID,
        "severity": "high",
        "trigger": "七个部署检查清单设置名的模块级赋值呈不安全或放宽方向，且与 diff 行相交",
        "evidence_type": "code_slice",
        "suggested_action": "复核该文件是开发默认还是生产模块。收紧方向不生成 Finding。命中不表示密钥已泄露。",
        "limitations": "方向读自未截断切片。闭集外名字不进入本规则。下标赋值记 Unanalyzed。",
    },
    {
        "rule_id": NON_NULL_RULE_ID,
        "severity": "high",
        "trigger": "模型字段或迁移 AlterField/AddField 上 null 收紧且未见 default=，并与 diff 行相交",
        "evidence_type": "code_slice",
        "suggested_action": "复核 default= 是否覆盖已有行，以及后端差异。看见 default= 记 NotFound。命中不表示迁移已失败。",
        "limitations": "只看本文件。blank 不并入。截断或 **kwargs 记 Unanalyzed。",
    },
]

HIGH_VALUE_RULES = [*HIGH_VALUE_RULES, *SECOND_BATCH_RULES]
_RULES_BY_ID = {rule["rule_id"]: rule for rule in HIGH_VALUE_RULES}
HIGH_VALUE_RULE_IDS = frozenset(_RULES_BY_ID)

_REASON_DETAILS = "unsupported_stage04_details"
_REASON_FRAMEWORK = "missing_framework_context"
_MIGRATIONS = re.compile(r"(?:^|/)migrations(?:/|$)", re.I)
_DESTRUCTIVE = frozenset({"DeleteModel", "RemoveField"})
_RUN_OPS = frozenset({"RunSQL", "RunPython", "SeparateDatabaseAndState"})
_VIEWSET_NATIVE = frozenset({"ViewSet", "GenericViewSet", "ModelViewSet", "ReadOnlyModelViewSet"})
_STANDARD_ACTIONS = frozenset({"list", "create", "retrieve", "update", "partial_update", "destroy"})
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FIELD_SUFFIX = re.compile(r"(?:Field|ForeignKey|OneToOneField|ManyToManyField)$")


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


def _parse_expr(segment: str) -> ast.AST | None:
    prepared = textwrap.dedent(segment).strip()
    if not prepared:
        return None
    try:
        tree = ast.parse(prepared)
    except SyntaxError:
        return None
    if len(tree.body) != 1:
        return None
    statement = tree.body[0]
    if isinstance(statement, ast.Expr):
        return statement.value
    return None


def _parse_statement(segment: str) -> ast.AST | None:
    prepared = textwrap.dedent(segment).strip("\n")
    if not prepared.strip():
        return None
    try:
        tree = ast.parse(prepared)
    except SyntaxError:
        return None
    if len(tree.body) != 1:
        return None
    return tree.body[0]


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


# --- csrf_exempt -----------------------------------------------------------

def _csrf_closed_form(expression: str, *, truncated: bool) -> dict[str, Any]:
    if truncated:
        return {"status": "unsupported"}
    segment = expression.strip()
    last = _last_segment(segment)
    if last == "csrf_exempt" and "(" not in segment.split("csrf_exempt", 1)[0]:
        # bare name or attr ending in csrf_exempt, not a call wrapper other than the name itself
        if segment == "csrf_exempt" or segment.endswith(".csrf_exempt"):
            return {"status": "hit", "form": "csrf_exempt"}
    tree = _parse_expr(segment)
    if tree is None:
        # alias-like: identifier that is not csrf_exempt
        if last and last != "csrf_exempt" and "(" not in segment:
            return {"status": "framework", "form": "alias"}
        return {"status": "unsupported"}
    if isinstance(tree, (ast.Name, ast.Attribute)):
        if _expr_last_segment(tree) == "csrf_exempt":
            return {"status": "hit", "form": "csrf_exempt"}
        return {"status": "framework", "form": "alias"}
    if isinstance(tree, ast.Call) and _expr_last_segment(tree.func) == "method_decorator":
        candidates: list[ast.AST] = list(tree.args)
        for kw in tree.keywords:
            if kw.arg in {None, "decorator"}:
                candidates.append(kw.value)
        for candidate in candidates:
            if isinstance(candidate, (ast.List, ast.Tuple)):
                for element in candidate.elts:
                    if _expr_last_segment(element) == "csrf_exempt":
                        return {"status": "hit", "form": "method_decorator"}
            elif _expr_last_segment(candidate) == "csrf_exempt":
                return {"status": "hit", "form": "method_decorator"}
        return {"status": "examined"}
    return {"status": "examined"}


def _collect_csrf(file_item: dict[str, Any], enabled: set[str]) -> tuple[list, list, dict]:
    if CSRF_RULE_ID not in enabled:
        return [], [], {}
    path = _path(file_item)
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    examined = 0
    base_by_owner: dict[str, set[str]] = {}
    for node in _nodes(file_item, side="base", kind="decorator"):
        owner = str((node.get("details") or {}).get("owner") or "")
        expression = str((node.get("details") or {}).get("expression") or node.get("source_segment") or "").strip()
        if expression:
            base_by_owner.setdefault(owner, set()).add(expression)
    for node in _nodes(file_item, side="base", kind="function") + _nodes(file_item, side="base", kind="class"):
        owner = str(node.get("qualified_name") or node.get("name") or "")
        for expression in (node.get("details") or {}).get("decorators") or []:
            text = str(expression).strip()
            if text:
                base_by_owner.setdefault(owner, set()).add(text)

    # Explicit changed decorator nodes drive Hit / Unanalyzed.
    for node in _nodes(file_item, side="head", kind="decorator"):
        if not _changed(node):
            continue
        details = node.get("details") if isinstance(node.get("details"), dict) else {}
        expression = str(details.get("expression") or node.get("source_segment") or "").strip()
        owner = str(details.get("owner") or "")
        truncated = bool(node.get("source_segment_truncated"))
        classified = _csrf_closed_form(expression, truncated=truncated)
        node_id = str(node.get("node_id") or "")
        if classified["status"] == "hit":
            examined += 1
            if expression in base_by_owner.get(owner, set()):
                continue
            findings.append(_finding(
                CSRF_RULE_ID,
                f"所有者 {owner or 'unknown'} 新增装饰器 {expression}。此线索只要求复核 CSRF 中间件覆盖，不表示跨站请求已发生。",
                _base_evidence(
                    path, node,
                    impact_type="external_impact",
                    owner=owner,
                    decorator_expression=expression,
                    base_status="absent",
                    decorator_form=classified.get("form"),
                ),
                "external_impact",
            ))
        elif classified["status"] == "framework":
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
        elif classified["status"] == "unsupported":
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
        else:
            examined += 1

    # Body-only edits: function/class still carries decorator list → count as examined NotFound.
    for node in _nodes(file_item, side="head", kind="function") + _nodes(file_item, side="head", kind="class"):
        if not _changed(node):
            continue
        decorators = (node.get("details") or {}).get("decorators") or []
        if not decorators:
            continue
        for expression in decorators:
            classified = _csrf_closed_form(str(expression).strip(), truncated=False)
            if classified["status"] in {"hit", "examined"}:
                examined += 1
            elif classified["status"] == "framework":
                # unchanged alias on body edit is still framework context if newly introduced via details only
                pass
    return findings, gaps, {"examined": examined, "gaps": gaps}


# --- viewset actions -------------------------------------------------------

def _action_decorator_parts(expression: str, *, truncated: bool) -> dict[str, Any]:
    if truncated:
        return {"status": "unsupported"}
    tree = _parse_expr(expression)
    if tree is None:
        return {"status": "unsupported"}
    if not isinstance(tree, ast.Call) or _expr_last_segment(tree.func) != "action":
        return {"status": "examined"}
    detail = None
    methods = None
    for kw in tree.keywords:
        if kw.arg == "detail":
            try:
                detail = ast.unparse(kw.value)
            except Exception:
                return {"status": "unsupported"}
        if kw.arg == "methods":
            try:
                methods = ast.unparse(kw.value)
            except Exception:
                return {"status": "unsupported"}
    return {"status": "action", "detail": detail, "methods": methods}


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


def _collect_viewset(file_item: dict[str, Any], enabled: set[str]) -> tuple[list, list, dict]:
    if VIEWSET_RULE_ID not in enabled:
        return [], [], {}
    path = _path(file_item)
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    examined = 0

    def inventory(side: str) -> dict[str, dict[str, Any]]:
        classes: dict[str, dict[str, Any]] = {}
        for klass in _nodes(file_item, side=side, kind="class"):
            name = str(klass.get("qualified_name") or klass.get("name") or "")
            status = _class_viewset_status(klass)
            classes[name] = {
                "node": klass,
                "status": status,
                "actions": {},
                "extras": {},
            }
        for func in _nodes(file_item, side=side, kind="function"):
            qname = str(func.get("qualified_name") or "")
            if "." not in qname:
                continue
            owner, _, method = qname.rpartition(".")
            if owner not in classes:
                continue
            decorators = (func.get("details") or {}).get("decorators") or []
            action_expr = None
            for item in decorators:
                text = str(item)
                if "action" in text:
                    action_expr = text
                    break
            if method in _STANDARD_ACTIONS:
                classes[owner]["actions"][method] = func
            if action_expr is not None:
                classes[owner]["extras"][method] = {"node": func, "expression": action_expr}
        return classes

    base_classes = inventory("base")
    head_classes = inventory("head")
    names = sorted(set(base_classes) | set(head_classes))
    for name in names:
        head = head_classes.get(name)
        base = base_classes.get(name)
        probe = head or base
        if probe is None:
            continue
        status = probe["status"]["status"]
        node = probe["node"]
        node_id = str(node.get("node_id") or "")
        if status == "framework":
            if _changed(node) or any(_changed(f) for f in (probe["actions"].values())):
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
            continue
        if status != "applicable":
            continue
        head_actions = (head or {}).get("actions") or {}
        base_actions = (base or {}).get("actions") or {}
        head_extras = (head or {}).get("extras") or {}
        base_extras = (base or {}).get("extras") or {}
        # standard action presence
        for action_name in sorted(set(head_actions) | set(base_actions)):
            in_head = action_name in head_actions
            in_base = action_name in base_actions
            if in_head == in_base:
                if in_head and _changed(head_actions[action_name]):
                    examined += 1
                continue
            evidence_node = head_actions.get(action_name) or base_actions.get(action_name)
            if evidence_node is None or not _changed(evidence_node):
                # still count presence delta when class body changed
                if not (_changed(node) or (evidence_node and _changed(evidence_node))):
                    continue
            examined += 1
            delta = "added" if in_head and not in_base else "removed"
            findings.append(_finding(
                VIEWSET_RULE_ID,
                f"ViewSet {name} 标准动作 {action_name} {delta}。此线索只表示本文件动作集合变化，不表示 URL 已变。",
                _base_evidence(
                    path, evidence_node or node,
                    impact_type="pr_intrinsic_risk",
                    class_name=name,
                    action_name=action_name,
                    action_delta=delta,
                ),
                "pr_intrinsic_risk",
            ))
        for method in sorted(set(head_extras) | set(base_extras)):
            head_extra = head_extras.get(method)
            base_extra = base_extras.get(method)
            if head_extra and not base_extra:
                evidence_node = head_extra["node"]
                if not _changed(evidence_node):
                    continue
                examined += 1
                findings.append(_finding(
                    VIEWSET_RULE_ID,
                    f"ViewSet {name} 新增 @action 方法 {method}。此线索只表示本文件动作集合变化，不表示 URL 已变。",
                    _base_evidence(
                        path, evidence_node,
                        impact_type="pr_intrinsic_risk",
                        class_name=name,
                        action_name=method,
                        action_delta="added",
                        decorator_expression=head_extra["expression"],
                    ),
                    "pr_intrinsic_risk",
                ))
                continue
            if base_extra and not head_extra:
                evidence_node = base_extra["node"]
                if not _changed(evidence_node) and not _changed(node):
                    continue
                examined += 1
                findings.append(_finding(
                    VIEWSET_RULE_ID,
                    f"ViewSet {name} 删除 @action 方法 {method}。此线索只表示本文件动作集合变化，不表示 URL 已变。",
                    _base_evidence(
                        path, evidence_node or node,
                        impact_type="pr_intrinsic_risk",
                        class_name=name,
                        action_name=method,
                        action_delta="removed",
                    ),
                    "pr_intrinsic_risk",
                ))
                continue
            if head_extra and base_extra:
                head_parts = _action_decorator_parts(
                    head_extra["expression"],
                    truncated=bool(head_extra["node"].get("source_segment_truncated")),
                )
                base_parts = _action_decorator_parts(
                    base_extra["expression"],
                    truncated=bool(base_extra["node"].get("source_segment_truncated")),
                )
                if head_parts["status"] == "unsupported" or base_parts["status"] == "unsupported":
                    gaps.append({"path": path, "node_id": str(head_extra["node"].get("node_id") or ""), "reason": _REASON_DETAILS})
                    continue
                if head_parts.get("detail") != base_parts.get("detail") or head_parts.get("methods") != base_parts.get("methods"):
                    evidence_node = head_extra["node"]
                    if not _changed(evidence_node):
                        continue
                    examined += 1
                    findings.append(_finding(
                        VIEWSET_RULE_ID,
                        f"ViewSet {name} 的 @action {method} 的 detail/methods 文本变化。此线索只表示本文件动作声明变化。",
                        _base_evidence(
                            path, evidence_node,
                            impact_type="pr_intrinsic_risk",
                            class_name=name,
                            action_name=method,
                            action_delta="methods_or_detail_changed",
                            decorator_expression=head_extra["expression"],
                        ),
                        "pr_intrinsic_risk",
                    ))
                elif _changed(head_extra["node"]):
                    examined += 1
    return findings, gaps, {"examined": examined, "gaps": gaps}


# --- destructive migration -------------------------------------------------

def _collect_destructive(file_item: dict[str, Any], enabled: set[str]) -> tuple[list, list, dict]:
    if DESTRUCTIVE_RULE_ID not in enabled:
        return [], [], {}
    path = _path(file_item)
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    examined = 0
    in_migrations = _migrations_path(path)
    for node in _nodes(file_item, side="head", kind="call"):
        if not _changed(node):
            continue
        details = node.get("details") if isinstance(node.get("details"), dict) else {}
        segment = _last_segment(details.get("direct_callee_name") if details.get("direct_callee_name") else details.get("callee"))
        if segment is None:
            if details.get("callee") or details.get("direct_callee_name") or node.get("source_segment_truncated"):
                gaps.append({"path": path, "node_id": str(node.get("node_id") or ""), "reason": _REASON_DETAILS})
            continue
        if segment in _RUN_OPS:
            gaps.append({"path": path, "node_id": str(node.get("node_id") or ""), "reason": _REASON_FRAMEWORK})
            continue
        if segment in _DESTRUCTIVE:
            if not in_migrations:
                gaps.append({"path": path, "node_id": str(node.get("node_id") or ""), "reason": _REASON_FRAMEWORK})
                continue
            examined += 1
            findings.append(_finding(
                DESTRUCTIVE_RULE_ID,
                f"迁移调用 {segment}。此线索只标记破坏性迁移操作类名，不表示生产库已丢数据。",
                _base_evidence(
                    path, node,
                    impact_type="external_impact",
                    operation_name=segment,
                    callee=details.get("callee"),
                ),
                "external_impact",
            ))
        else:
            if in_migrations:
                examined += 1
    return findings, gaps, {"examined": examined, "gaps": gaps}


# --- permission downgrade --------------------------------------------------

def _permission_form(segment: str, *, truncated: bool) -> dict[str, Any]:
    if truncated:
        return {"status": "unsupported"}
    prepared = textwrap.dedent(segment).strip()
    if not prepared:
        return {"status": "unsupported"}
    # decorator form @permission_classes(...)
    expr = prepared[1:] if prepared.startswith("@") else prepared
    tree_stmt = _parse_statement(expr if "=" in expr else f"permission_classes = {expr}" if expr.startswith(("[", "(")) else expr)
    value = None
    if isinstance(tree_stmt, ast.Assign) and len(tree_stmt.targets) == 1:
        target = tree_stmt.targets[0]
        if isinstance(target, ast.Name) and target.id != "permission_classes":
            return {"status": "examined"}
        value = tree_stmt.value
    elif isinstance(tree_stmt, ast.AnnAssign) and isinstance(tree_stmt.target, ast.Name):
        if tree_stmt.target.id != "permission_classes":
            return {"status": "examined"}
        value = tree_stmt.value
    else:
        tree = _parse_expr(expr)
        if isinstance(tree, ast.Call) and _expr_last_segment(tree.func) == "permission_classes":
            if not tree.args:
                return {"status": "unsupported"}
            value = tree.args[0]
        elif isinstance(tree, (ast.List, ast.Tuple, ast.Name, ast.Attribute)):
            value = tree
        else:
            return {"status": "unsupported"}
    if value is None:
        return {"status": "unsupported"}
    if isinstance(value, (ast.List, ast.Tuple)) and not value.elts:
        return {"status": "downgrade", "form": "empty"}
    elements = value.elts if isinstance(value, (ast.List, ast.Tuple)) else [value]
    names: list[str] = []
    for element in elements:
        if isinstance(element, (ast.BitOr, ast.BitAnd, ast.UnaryOp)):
            return {"status": "framework"}
        name = _expr_last_segment(element)
        if name is None:
            return {"status": "unsupported"}
        names.append(name)
    if names == ["AllowAny"]:
        return {"status": "downgrade", "form": "AllowAny"}
    if any(name == "AllowAny" for name in names) and len(names) > 1:
        return {"status": "framework"}
    # unknown custom names are not AllowAny equivalents
    if names and all(name != "AllowAny" for name in names):
        # PublicRead etc. cannot be proven equal to AllowAny
        if any(name not in {"IsAuthenticated", "IsAdminUser", "IsAuthenticatedOrReadOnly", "DjangoModelPermissions", "DjangoObjectPermissions"} for name in names):
            # still not a downgrade form for this rule; examined unless it's a known non-AllowAny
            return {"status": "examined", "form": ",".join(names)}
        return {"status": "examined", "form": ",".join(names)}
    return {"status": "examined", "form": ",".join(names)}


def _collect_permission(file_item: dict[str, Any], enabled: set[str]) -> tuple[list, list, dict]:
    if PERMISSION_RULE_ID not in enabled:
        return [], [], {}
    path = _path(file_item)
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    examined = 0

    def forms(side: str) -> dict[str, dict[str, Any]]:
        found: dict[str, dict[str, Any]] = {}
        for node in _nodes(file_item, side=side, kind="field"):
            name = str(node.get("name") or "")
            if name != "permission_classes":
                continue
            qname = str(node.get("qualified_name") or name)
            found[qname] = {"node": node, "segment": str(node.get("source_segment") or "")}
        for node in _nodes(file_item, side=side, kind="decorator"):
            details = node.get("details") if isinstance(node.get("details"), dict) else {}
            expression = str(details.get("expression") or node.get("source_segment") or "")
            if _last_segment(expression.split("(", 1)[0]) != "permission_classes":
                continue
            owner = str(details.get("owner") or node.get("qualified_name") or "")
            found[f"decorator:{owner}"] = {"node": node, "segment": expression}
        return found

    base_forms = forms("base")
    head_forms = forms("head")
    for key, head in head_forms.items():
        node = head["node"]
        if not _changed(node):
            continue
        truncated = bool(node.get("source_segment_truncated"))
        head_form = _permission_form(head["segment"], truncated=truncated)
        node_id = str(node.get("node_id") or "")
        if head_form["status"] == "unsupported":
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
            continue
        if head_form["status"] == "framework":
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
            continue
        examined += 1
        if head_form["status"] != "downgrade":
            continue
        base = base_forms.get(key)
        base_status = "absent"
        if base is not None:
            base_form = _permission_form(base["segment"], truncated=bool(base["node"].get("source_segment_truncated")))
            if base_form["status"] == "unsupported":
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
                continue
            if base_form["status"] == "framework":
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
                continue
            if base_form.get("status") == "downgrade" and base_form.get("form") == head_form.get("form"):
                continue
            base_status = str(base_form.get("form") or base_form.get("status"))
        findings.append(_finding(
            PERMISSION_RULE_ID,
            f"permission_classes 变为 {head_form.get('form')}（base={base_status}）。此线索只表示显式降级声明，不表示请求已匿名可写。",
            _base_evidence(
                path, node,
                impact_type="external_impact",
                head_form=head_form.get("form"),
                base_form=base_status,
            ),
            "external_impact",
        ))
    return findings, gaps, {"examined": examined, "gaps": gaps}


# --- sensitive settings ----------------------------------------------------

def _module_level_field(node: dict[str, Any]) -> bool:
    details = node.get("details") if isinstance(node.get("details"), dict) else {}
    scope = details.get("scope")
    if scope == "<module>":
        return True
    qname = str(node.get("qualified_name") or node.get("name") or "")
    return qname.startswith("<module>.") or ("." not in qname)


def _paired_base_field(file_item: dict[str, Any], head: dict[str, Any]) -> dict[str, Any] | None:
    match_key = head.get("match_key")
    name = head.get("name")
    if match_key:
        for node in _nodes(file_item, side="base", kind="field"):
            if node.get("match_key") == match_key:
                return node
    for node in _nodes(file_item, side="base", kind="field"):
        if node.get("name") == name and _module_level_field(node):
            return node
    return None


def _collect_sensitive(file_item: dict[str, Any], enabled: set[str]) -> tuple[list, list, dict]:
    if SENSITIVE_RULE_ID not in enabled:
        return [], [], {}
    path = _path(file_item)
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    examined = 0
    seen_names: set[str] = set()
    for node in _nodes(file_item, side="head", kind="field"):
        if not _changed(node):
            continue
        if not _module_level_field(node):
            continue
        name = str(node.get("name") or "")
        if name not in SENSITIVE_SETTING_NAMES:
            continue
        seen_names.add(name)
        truncated = bool(node.get("source_segment_truncated"))
        base = _paired_base_field(file_item, node)
        direction = classify_sensitive_direction(
            name,
            base_segment=None if base is None else str(base.get("source_segment") or ""),
            head_segment=str(node.get("source_segment") or ""),
            truncated=truncated or bool(base and base.get("source_segment_truncated")),
        )
        node_id = str(node.get("node_id") or "")
        if direction["direction"] == "hit":
            examined += 1
            findings.append(_finding(
                SENSITIVE_RULE_ID,
                f"敏感设置 {name} 呈放宽或不安全方向。此线索只要求复核配置方向，不表示密钥已泄露。",
                _base_evidence(
                    path, node,
                    impact_type="pr_intrinsic_risk",
                    setting_name=name,
                    direction=direction.get("reason"),
                ),
                "pr_intrinsic_risk",
            ))
        elif direction["direction"] == "not_found":
            examined += 1
        else:
            gaps.append({"path": path, "node_id": node_id, "reason": str(direction.get("reason") or _REASON_DETAILS)})
    # removed sensitive assignment on base only
    for node in _nodes(file_item, side="base", kind="field"):
        if not _changed(node) or not _module_level_field(node):
            continue
        name = str(node.get("name") or "")
        if name not in SENSITIVE_SETTING_NAMES or name in seen_names:
            continue
        direction = classify_sensitive_direction(
            name,
            base_segment=str(node.get("source_segment") or ""),
            head_segment=None,
            truncated=bool(node.get("source_segment_truncated")),
        )
        if direction["direction"] == "hit":
            examined += 1
            findings.append(_finding(
                SENSITIVE_RULE_ID,
                f"敏感设置 {name} 被删除。此线索只要求复核配置方向。",
                _base_evidence(
                    path, node,
                    impact_type="pr_intrinsic_risk",
                    setting_name=name,
                    direction=direction.get("reason"),
                ),
                "pr_intrinsic_risk",
            ))
        elif direction["direction"] == "unanalyzed":
            gaps.append({"path": path, "node_id": str(node.get("node_id") or ""), "reason": str(direction.get("reason") or _REASON_DETAILS)})
    return findings, gaps, {"examined": examined, "gaps": gaps}


# --- non-null tighten ------------------------------------------------------

def _null_from_details(details: dict[str, Any]) -> Any:
    if "null_literal" in details:
        return details.get("null_literal")
    return None


def _has_default(details: dict[str, Any]) -> bool | None:
    if "has_default_keyword" in details:
        return bool(details.get("has_default_keyword"))
    return None


def _field_call_segment(node: dict[str, Any]) -> str:
    return str(node.get("source_segment") or "")


def _is_field_ctor(callee: str | None) -> bool:
    segment = _last_segment(callee)
    if segment is None:
        return False
    return bool(_FIELD_SUFFIX.search(segment)) or segment in {"ForeignKey", "OneToOneField", "ManyToManyField"}


def _null_state_from_segment(segment: str, *, truncated: bool, details: dict[str, Any]) -> dict[str, Any]:
    if truncated:
        return {"status": "unsupported"}
    has_default = _has_default(details)
    null_literal = _null_from_details(details)
    # Prefer structured fields when present; still require readable default presence.
    if has_default is None:
        # fall back to source text
        if "default=" in segment:
            has_default = True
        elif "**" in segment:
            return {"status": "unsupported"}
        else:
            has_default = False
    if null_literal == "unreadable":
        return {"status": "unsupported"}
    if null_literal is True:
        null_state = "true"
    elif null_literal is False:
        null_state = "false"
    elif "null=" not in segment:
        null_state = "absent"
    else:
        # present in text but structured value missing
        if re.search(r"null\s*=\s*True", segment):
            null_state = "true"
        elif re.search(r"null\s*=\s*False", segment):
            null_state = "false"
        else:
            return {"status": "unsupported"}
    return {"status": "ready", "null": null_state, "has_default": has_default}


def _collect_non_null(file_item: dict[str, Any], enabled: set[str]) -> tuple[list, list, dict]:
    if NON_NULL_RULE_ID not in enabled:
        return [], [], {}
    path = _path(file_item)
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    examined = 0
    in_migrations = _migrations_path(path)

    # model field assignments
    base_fields = {
        str(node.get("qualified_name") or node.get("name")): node
        for node in _nodes(file_item, side="base", kind="field")
        if "." in str(node.get("qualified_name") or "")
    }
    for node in _nodes(file_item, side="head", kind="field"):
        if not _changed(node):
            continue
        qname = str(node.get("qualified_name") or node.get("name") or "")
        if "." not in qname:
            continue
        details = node.get("details") if isinstance(node.get("details"), dict) else {}
        segment = _field_call_segment(node)
        # only field constructors
        if "Field" not in segment and "ForeignKey" not in segment and "OneToOne" not in segment and "ManyToMany" not in segment:
            continue
        head_state = _null_state_from_segment(segment, truncated=bool(node.get("source_segment_truncated")), details=details)
        node_id = str(node.get("node_id") or "")
        if head_state["status"] != "ready":
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
            continue
        base = base_fields.get(qname)
        if base is None:
            # new model field on possibly new model — CreateModel / new class body is NotFound
            examined += 1
            continue
        base_details = base.get("details") if isinstance(base.get("details"), dict) else {}
        base_state = _null_state_from_segment(
            str(base.get("source_segment") or ""),
            truncated=bool(base.get("source_segment_truncated")),
            details=base_details,
        )
        if base_state["status"] != "ready":
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
            continue
        examined += 1
        tightened = base_state["null"] == "true" and head_state["null"] in {"false", "absent"}
        if tightened and not head_state["has_default"]:
            findings.append(_finding(
                NON_NULL_RULE_ID,
                f"字段 {qname} 的 null 约束收紧且未见 default=。此线索不表示迁移已失败。",
                _base_evidence(
                    path, node,
                    impact_type="external_impact",
                    field_name=qname,
                    null_before=base_state["null"],
                    null_after=head_state["null"],
                ),
                "external_impact",
            ))

    # migration AlterField / AddField
    for node in _nodes(file_item, side="head", kind="call"):
        if not _changed(node):
            continue
        details = node.get("details") if isinstance(node.get("details"), dict) else {}
        segment_name = _last_segment(details.get("callee") or details.get("direct_callee_name"))
        if segment_name not in {"AlterField", "AddField"}:
            continue
        if not in_migrations:
            gaps.append({"path": path, "node_id": str(node.get("node_id") or ""), "reason": _REASON_FRAMEWORK})
            continue
        segment = str(node.get("source_segment") or "")
        truncated = bool(node.get("source_segment_truncated"))
        if truncated:
            gaps.append({"path": path, "node_id": str(node.get("node_id") or ""), "reason": _REASON_DETAILS})
            continue
        # field= kw expression: look for nested field ctor text
        has_default = "default=" in segment
        null_true = bool(re.search(r"null\s*=\s*True", segment))
        null_false = bool(re.search(r"null\s*=\s*False", segment))
        examined += 1
        if segment_name == "AddField":
            if not null_true and not has_default:
                findings.append(_finding(
                    NON_NULL_RULE_ID,
                    "迁移 AddField 未见 null=True 且未见 default=。此线索不表示迁移已失败。",
                    _base_evidence(path, node, impact_type="external_impact", operation_name="AddField"),
                    "external_impact",
                ))
            continue
        # AlterField: need base comparison when possible
        if null_false or (not null_true and "null=" in segment):
            if not has_default and (null_false or re.search(r"null\s*=\s*False", segment)):
                findings.append(_finding(
                    NON_NULL_RULE_ID,
                    "迁移 AlterField 呈现 null 收紧且未见 default=。此线索不表示迁移已失败。",
                    _base_evidence(path, node, impact_type="external_impact", operation_name="AlterField"),
                    "external_impact",
                ))
    return findings, gaps, {"examined": examined, "gaps": gaps}


_COLLECTORS = (
    _collect_csrf,
    _collect_viewset,
    _collect_destructive,
    _collect_permission,
    _collect_sensitive,
    _collect_non_null,
)


def collect_high_value_findings(
    stage04_record: dict[str, Any],
    enabled: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Return findings, merged summary gaps, and per-rule outcome traces."""
    if not (HIGH_VALUE_RULE_IDS & enabled):
        return [], [], {}
    findings: list[dict[str, Any]] = []
    all_gaps: list[dict[str, str]] = []
    traces: dict[str, dict[str, Any]] = {
        rule_id: {"examined": 0, "gaps": []} for rule_id in HIGH_VALUE_RULE_IDS if rule_id in enabled
    }
    for file_item in stage04_record.get("files") or []:
        if not isinstance(file_item, dict):
            continue
        if file_item.get("parse_status", {}).get("head") == "failed":
            continue
        for collector in _COLLECTORS:
            part_findings, part_gaps, part_trace = collector(file_item, enabled)
            findings.extend(part_findings)
            all_gaps.extend(part_gaps)
            if not part_trace:
                continue
            # map gaps back onto the rule that produced them by collector order
            rule_id = None
            if collector is _collect_csrf:
                rule_id = CSRF_RULE_ID
            elif collector is _collect_viewset:
                rule_id = VIEWSET_RULE_ID
            elif collector is _collect_destructive:
                rule_id = DESTRUCTIVE_RULE_ID
            elif collector is _collect_permission:
                rule_id = PERMISSION_RULE_ID
            elif collector is _collect_sensitive:
                rule_id = SENSITIVE_RULE_ID
            elif collector is _collect_non_null:
                rule_id = NON_NULL_RULE_ID
            if rule_id is None or rule_id not in traces:
                continue
            traces[rule_id]["examined"] += int(part_trace.get("examined") or 0)
            traces[rule_id]["gaps"].extend(part_trace.get("gaps") or [])
            # also record collector gaps into the rule trace when not already present
            for gap in part_gaps:
                if gap not in traces[rule_id]["gaps"]:
                    traces[rule_id]["gaps"].append(gap)
    second_findings, _second_gaps, second_traces = collect_second_batch_findings(stage04_record, enabled)
    findings.extend(second_findings)
    for rule_id, trace in second_traces.items():
        traces.setdefault(rule_id, {"examined": 0, "gaps": []})
        traces[rule_id]["examined"] += int(trace.get("examined") or 0)
        for gap in trace.get("gaps") or []:
            all_gaps.append(gap)
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
