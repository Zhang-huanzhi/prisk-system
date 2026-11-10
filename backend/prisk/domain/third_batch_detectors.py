"""Third high-value draft detector batch for task 024.

Three rules land as Finding paths with Hit / NotFound / Unanalyzed terminals:
- api.django_url_pattern_changed (backend_contract)
- code.assert_in_production (code_smell)
- code.mutable_default_argument (code_smell)

Hits are review clues. Lifecycle promotion happens in the registry when
constructive tests pass; default weight stays 0.
"""

from __future__ import annotations

import ast
import re
from typing import Any

from .test_collaboration import classify_collaboration_path


URL_PATTERN_ID = "api.django_url_pattern_changed"
ASSERT_PROD_ID = "code.assert_in_production"
MUTABLE_DEFAULT_ID = "code.mutable_default_argument"

THIRD_BATCH_RULES: list[dict[str, str]] = [
    {
        "rule_id": URL_PATTERN_ID,
        "severity": "medium",
        "trigger": "同一文件 Django URL 路由（path/re_path/register）的 route、view 或 name 发生变更，或新增/删除路由声明与变更行相交",
        "evidence_type": "code_slice",
        "suggested_action": "复核路由变更是否影响外部 API 契约或客户端路径，确认是否需要重定向或发布说明。命中不表示线上路由已 404。",
        "limitations": "仅分析同一文件内路由字面量；include()/url() 与动态构造路由记 Unanalyzed；不跟随跨文件 URLconf 分发。",
    },
    {
        "rule_id": ASSERT_PROD_ID,
        "severity": "medium",
        "trigger": "路径分类为生产代码（production）的 Python 文件中，与新增行相交的 assert 语句",
        "evidence_type": "code_slice",
        "suggested_action": "复核该 assert 是否承担业务或权限校验，生产环境优化模式（python -O）下会被跳过。命中不表示优化已开启。",
        "limitations": "仅基于 default_source_and_test_directories 路径策略；非生产/测试路径不触发；未知路径记 Unanalyzed。",
    },
    {
        "rule_id": MUTABLE_DEFAULT_ID,
        "severity": "medium",
        "trigger": "函数、异步函数或 lambda 的默认参数值为可变容器（list/dict/set 显示或无参调用），且与新增行相交",
        "evidence_type": "code_slice",
        "suggested_action": "复核默认参数是否在函数调用间共享状态并引发串扰，建议使用 None 作为默认值并在函数体内初始化。命中不表示已发生串扰。",
        "limitations": "仅覆盖闭集容器种类（list_display, dict_display, set_display, list_call, dict_call, set_call）；闭集外或不可读表达式不触发或记 Unanalyzed。",
    },
]

_RULES_BY_ID = {rule["rule_id"]: rule for rule in THIRD_BATCH_RULES}
THIRD_BATCH_RULE_IDS = frozenset(_RULES_BY_ID)

_REASON_DETAILS = "unsupported_stage04_details"
_REASON_FRAMEWORK = "missing_framework_context"
_REASON_PATH = "path_classification_unavailable"

MUTABLE_VALUE_KINDS = frozenset({
    "list_display",
    "dict_display",
    "set_display",
    "list_call",
    "dict_call",
    "set_call",
})

_SUPPORTED_ROUTING_CALLEES = frozenset({"path", "re_path", "register"})


def _path(file_item: dict[str, Any]) -> str:
    return str(file_item.get("path") or file_item.get("new_path") or file_item.get("old_path") or "")


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


def _summary_gaps(gaps: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[str]] = {}
    for gap in gaps:
        node_id = str(gap.get("node_id") or "")
        node_ids = grouped.setdefault((gap["path"], gap["reason"]), [])
        if node_id:
            node_ids.append(node_id)
    return [
        {"path": path, "reason": reason, "node_ids": sorted(set(node_ids))}
        for (path, reason), node_ids in sorted(grouped.items())
    ]


def _changed(node: dict[str, Any]) -> bool:
    return bool(node.get("changed_lines"))


# ==============================================================================
# 1. api.django_url_pattern_changed
# ==============================================================================

def _collect_url_pattern(
    file_item: dict[str, Any],
    enabled: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:
    if URL_PATTERN_ID not in enabled:
        return [], [], {"examined": 0, "gaps": []}

    path = _path(file_item)
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    examined = 0

    base_call_nodes = [
        node for node in _nodes(file_item, side="base", kind="call")
        if (node.get("details") or {}).get("routing_call") is not None
    ]
    head_call_nodes = [
        node for node in _nodes(file_item, side="head", kind="call")
        if (node.get("details") or {}).get("routing_call") is not None
    ]

    all_routing_nodes = base_call_nodes + head_call_nodes
    if not all_routing_nodes:
        return [], [], {"examined": 0, "gaps": []}

    # Inspect all changed calls for unsupported callees (url, include) or unreadable expressions
    for node in all_routing_nodes:
        if not _changed(node):
            continue
        r_info = (node.get("details") or {}).get("routing_call") or {}
        callee = r_info.get("callee_name")
        node_id = str(node.get("node_id") or "")
        if callee in {"url", "include"}:
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
            continue
        if r_info.get("has_unpacking") or r_info.get("route_status") == "unreadable" or r_info.get("view_status") == "unreadable" or r_info.get("name_status") == "unreadable":
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
            continue

    if gaps:
        return [], gaps, {"examined": examined, "gaps": gaps}

    # Filter to supported routing calls: path, re_path, register
    base_supported = [
        n for n in base_call_nodes
        if ((n.get("details") or {}).get("routing_call") or {}).get("callee_name") in _SUPPORTED_ROUTING_CALLEES
    ]
    head_supported = [
        n for n in head_call_nodes
        if ((n.get("details") or {}).get("routing_call") or {}).get("callee_name") in _SUPPORTED_ROUTING_CALLEES
    ]

    if not base_supported and not head_supported:
        return [], [], {"examined": 0, "gaps": []}

    # Check for unchanged include() views: if view is include_call and unchanged, that's fine;
    # but if an include() call view is changed without route text change, we cannot inspect target cross-file.
    for n in head_supported:
        if not _changed(n):
            continue
        r_info = (n.get("details") or {}).get("routing_call") or {}
        if r_info.get("view_status") == "include_call":
            # If the route text itself didn't change relative to a paired base node, we report missing_framework_context
            matched_base = None
            for b in base_supported:
                b_info = (b.get("details") or {}).get("routing_call") or {}
                if b_info.get("route_text") == r_info.get("route_text"):
                    matched_base = b
                    break
            if matched_base is not None:
                # route didn't change, but view is include() target
                gaps.append({"path": path, "node_id": str(n.get("node_id") or ""), "reason": _REASON_FRAMEWORK})

    if gaps:
        return [], gaps, {"examined": examined, "gaps": gaps}

    # Match base and head routing calls:
    # 1. Match by (name_text) if name_text is present on both
    # 2. Match by (route_text) if route_text is present on both
    # 3. Match by (view_text) if view_text is present on both
    # 4. If lengths match, match by index
    matched_pairs: list[tuple[dict[str, Any] | None, dict[str, Any] | None]] = []
    unmatched_base = list(base_supported)
    unmatched_head = list(head_supported)

    def extract_routing(n: dict[str, Any] | None) -> dict[str, Any]:
        if n is None:
            return {}
        return (n.get("details") or {}).get("routing_call") or {}

    # Pass 1: match by non-empty name_text
    b_idx = 0
    while b_idx < len(unmatched_base):
        b = unmatched_base[b_idx]
        b_name = extract_routing(b).get("name_text")
        if b_name:
            h_match = next((h for h in unmatched_head if extract_routing(h).get("name_text") == b_name), None)
            if h_match is not None:
                matched_pairs.append((b, h_match))
                unmatched_base.pop(b_idx)
                unmatched_head.remove(h_match)
                continue
        b_idx += 1

    # Pass 2: match by non-empty route_text
    b_idx = 0
    while b_idx < len(unmatched_base):
        b = unmatched_base[b_idx]
        b_route = extract_routing(b).get("route_text")
        if b_route is not None:
            h_match = next((h for h in unmatched_head if extract_routing(h).get("route_text") == b_route), None)
            if h_match is not None:
                matched_pairs.append((b, h_match))
                unmatched_base.pop(b_idx)
                unmatched_head.remove(h_match)
                continue
        b_idx += 1

    # Pass 3: match by non-empty view_text
    b_idx = 0
    while b_idx < len(unmatched_base):
        b = unmatched_base[b_idx]
        b_view = extract_routing(b).get("view_text")
        if b_view:
            h_match = next((h for h in unmatched_head if extract_routing(h).get("view_text") == b_view), None)
            if h_match is not None:
                matched_pairs.append((b, h_match))
                unmatched_base.pop(b_idx)
                unmatched_head.remove(h_match)
                continue
        b_idx += 1

    # Pass 4: if single pair remains and same callee, pair them (in-place modification of both route & view)
    if len(unmatched_base) == 1 and len(unmatched_head) == 1:
        if extract_routing(unmatched_base[0]).get("callee_name") == extract_routing(unmatched_head[0]).get("callee_name"):
            matched_pairs.append((unmatched_base.pop(0), unmatched_head.pop(0)))

    # Remaining unmatched are deletions / additions
    for b in unmatched_base:
        matched_pairs.append((b, None))
    for h in unmatched_head:
        matched_pairs.append((None, h))

    for base_node, head_node in matched_pairs:
        # Check if either side changed
        is_changed = (base_node is not None and _changed(base_node)) or (head_node is not None and _changed(head_node))
        if not is_changed:
            examined += 1
            continue

        b_info = extract_routing(base_node)
        h_info = extract_routing(head_node)

        # Deletion
        if head_node is None and base_node is not None:
            examined += 1
            b_route = b_info.get("route_text")
            b_name = b_info.get("name_text")
            ident = b_route or b_name or "pattern"
            findings.append(_finding(
                URL_PATTERN_ID,
                f"删除路由声明 '{ident}'。此线索不表示线上路由已 404。",
                _base_evidence(
                    path, base_node,
                    impact_type="pr_intrinsic_risk",
                    callee=b_info.get("callee_name"),
                    old_route=b_route,
                    new_route=None,
                    old_view=b_info.get("view_text"),
                    new_view=None,
                    old_name=b_name,
                    new_name=None,
                    change_kind="route_removed",
                ),
                "pr_intrinsic_risk",
            ))
            continue

        # Addition
        if base_node is None and head_node is not None:
            examined += 1
            h_route = h_info.get("route_text")
            h_name = h_info.get("name_text")
            ident = h_route or h_name or "pattern"
            findings.append(_finding(
                URL_PATTERN_ID,
                f"新增路由声明 '{ident}'。此线索不表示线上路由已 404。",
                _base_evidence(
                    path, head_node,
                    impact_type="pr_intrinsic_risk",
                    callee=h_info.get("callee_name"),
                    old_route=None,
                    new_route=h_route,
                    old_view=None,
                    new_view=h_info.get("view_text"),
                    old_name=None,
                    new_name=h_name,
                    change_kind="route_added",
                ),
                "pr_intrinsic_risk",
            ))
            continue

        # Paired modification
        assert base_node is not None and head_node is not None
        examined += 1
        b_route = b_info.get("route_text")
        h_route = h_info.get("route_text")
        b_view = b_info.get("view_text")
        h_view = h_info.get("view_text")
        b_name = b_info.get("name_text")
        h_name = h_info.get("name_text")

        route_diff = b_route != h_route
        view_diff = b_view != h_view
        name_diff = b_name != h_name

        if not (route_diff or view_diff or name_diff):
            # Only formatting/whitespace changed
            continue

        ident = h_route or h_name or b_route or b_name or "pattern"
        if route_diff:
            msg = f"路由声明 '{ident}' 路径变更 ('{b_route}' → '{h_route}')。此线索不表示线上路由已 404。"
            change_kind = "route_changed"
        elif view_diff:
            msg = f"路由声明 '{ident}' 视图变更 ('{b_view}' → '{h_view}')。此线索不表示线上路由已 404。"
            change_kind = "view_changed"
        else:
            msg = f"路由声明 '{ident}' 名称变更 ('{b_name}' → '{h_name}')。此线索不表示线上路由已 404。"
            change_kind = "name_changed"

        findings.append(_finding(
            URL_PATTERN_ID,
            msg,
            _base_evidence(
                path, head_node,
                impact_type="pr_intrinsic_risk",
                callee=h_info.get("callee_name"),
                old_route=b_route,
                new_route=h_route,
                old_view=b_view,
                new_view=h_view,
                old_name=b_name,
                new_name=h_name,
                change_kind=change_kind,
            ),
            "pr_intrinsic_risk",
        ))

    return findings, gaps, {"examined": examined, "gaps": gaps}


# ==============================================================================
# 2. code.assert_in_production
# ==============================================================================

def _collect_assert_in_production(
    file_item: dict[str, Any],
    enabled: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:
    if ASSERT_PROD_ID not in enabled:
        return [], [], {"examined": 0, "gaps": []}

    path = _path(file_item)
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    examined = 0

    assert_nodes = _nodes(file_item, side="head", kind="assert_statement")
    if not assert_nodes:
        return [], [], {"examined": 0, "gaps": []}

    path_class = classify_collaboration_path(path)

    for node in assert_nodes:
        if not _changed(node):
            examined += 1
            continue

        if path_class == "unknown":
            gaps.append({"path": path, "node_id": str(node.get("node_id") or ""), "reason": _REASON_PATH})
            continue

        if path_class != "production":
            # Test or non_production paths (migrations, settings, docs) do not trigger
            examined += 1
            continue

        examined += 1
        details = node.get("details") if isinstance(node.get("details"), dict) else {}
        test_expr = details.get("test_expression")
        msg_expr = details.get("msg_expression")
        findings.append(_finding(
            ASSERT_PROD_ID,
            f"生产代码路径 {path} 中新增 assert 语句。在 python -O 优化模式下将被跳过。此线索不表示优化已开启。",
            _base_evidence(
                path, node,
                impact_type="pr_intrinsic_risk",
                path_class="production",
                test_expression=test_expr,
                msg_expression=msg_expr,
            ),
            "pr_intrinsic_risk",
        ))

    return findings, gaps, {"examined": examined, "gaps": gaps}


# ==============================================================================
# 3. code.mutable_default_argument
# ==============================================================================

def _collect_mutable_default(
    file_item: dict[str, Any],
    enabled: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:
    if MUTABLE_DEFAULT_ID not in enabled:
        return [], [], {"examined": 0, "gaps": []}

    path = _path(file_item)
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    examined = 0

    # Collect head nodes that can define parameter defaults: function, async_function, lambda_defaults
    candidate_nodes = [
        node for node in _nodes(file_item, side="head")
        if node.get("kind") in {"function", "async_function", "lambda_defaults"}
    ]

    if not candidate_nodes:
        return [], [], {"examined": 0, "gaps": []}

    # Aggregate all changed lines in head
    head_changed_lines: set[int] = set()
    for n in _nodes(file_item, side="head"):
        head_changed_lines.update(n.get("changed_lines") or [])

    for node in candidate_nodes:
        details = node.get("details") if isinstance(node.get("details"), dict) else {}
        param_defaults = details.get("parameter_defaults")
        node_id = str(node.get("node_id") or "")

        if node.get("source_segment_truncated") and _changed(node):
            gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
            continue

        if not isinstance(param_defaults, list):
            continue

        qname = str(node.get("qualified_name") or node.get("name") or "<lambda>")
        is_lambda = node.get("kind") == "lambda_defaults"

        for item in param_defaults:
            if not isinstance(item, dict):
                continue
            default_kind = item.get("default_kind")
            start_line = item.get("start_line")
            end_line = item.get("end_line")
            param_name = str(item.get("name") or "")

            if start_line is None or end_line is None:
                continue

            default_span = set(range(int(start_line), int(end_line) + 1))
            if not (default_span & head_changed_lines):
                # Default expression did not intersect added lines
                continue

            examined += 1

            if default_kind not in MUTABLE_VALUE_KINDS:
                # Non-mutable default (e.g. None, int, str, tuple, or non_mutable)
                continue

            # Mutable default hit!
            prefix = "Lambda 表达式" if is_lambda else f"函数 {qname}"
            findings.append(_finding(
                MUTABLE_DEFAULT_ID,
                f"{prefix} 参数 {param_name} 使用可变对象 ({default_kind}) 作为默认值。此线索不表示已发生串扰。",
                _base_evidence(
                    path, node,
                    impact_type="pr_intrinsic_risk",
                    function_name=qname,
                    parameter_name=param_name,
                    default_kind=default_kind,
                    default_expr=item.get("default_expr"),
                    default_start_line=start_line,
                    default_end_line=end_line,
                ),
                "pr_intrinsic_risk",
            ))

    return findings, gaps, {"examined": examined, "gaps": gaps}


THIRD_BATCH_COLLECTORS: list[tuple[str, Any]] = [
    (URL_PATTERN_ID, _collect_url_pattern),
    (ASSERT_PROD_ID, _collect_assert_in_production),
    (MUTABLE_DEFAULT_ID, _collect_mutable_default),
]


def collect_third_batch_findings(
    stage04_record: dict[str, Any],
    enabled: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if not (THIRD_BATCH_RULE_IDS & enabled):
        return [], [], {}
    findings: list[dict[str, Any]] = []
    all_gaps: list[dict[str, str]] = []
    traces: dict[str, dict[str, Any]] = {
        rule_id: {"examined": 0, "gaps": []} for rule_id in THIRD_BATCH_RULE_IDS if rule_id in enabled
    }
    for file_item in stage04_record.get("files") or []:
        if not isinstance(file_item, dict):
            continue
        if file_item.get("parse_status", {}).get("head") == "failed":
            continue
        for rule_id, collector in THIRD_BATCH_COLLECTORS:
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
