"""Django raw-SQL call shape.

The hit set is the closed list from task 011, not the wider draft list from
task 005. A hit marks a call shape for review. It is not an injection
finding, and the SQL text is not read to decide safety.

Hit, for a head call whose lines already intersect added diff lines:

- ``direct_callee_name`` is ``RawSQL``, or
- the last segment of ``callee`` is ``execute``, ``executemany``, or ``raw``.

``extra``, ``callproc``, and any callee containing ``schema_editor`` are
``missing_framework_context``. An empty callee, or a slice truncated so the
last segment cannot be confirmed, is ``unsupported_stage04_details``.
``migrations.RunSQL`` is outside the hit set. There is no migration-path
policy: the same names apply in migration files and view files, and the path
is evidence only. Aliases such as ``run = cursor.execute`` are not followed.
"""

from __future__ import annotations

import ast
import re
import textwrap
from typing import Any


RAW_SQL_RULE_ID = "data.django_raw_sql_execution"
RAW_SQL_RULE: dict[str, str] = {
    "rule_id": RAW_SQL_RULE_ID,
    "severity": "high",
    "trigger": "新增行与调用相交，且直接名称是 RawSQL，或 callee 最后一段是 execute、executemany、raw",
    "evidence_type": "code_slice",
    "suggested_action": "复核调用位于迁移、管理命令还是请求处理，以及参数是序列还是拼进字符串。命中不是注入已经发生。",
    "limitations": "只标记闭集中的调用形态。不解析 SQL，不判断参数是否安全，不跟随别名。extra、callproc 和 schema_editor 记为无法分析。路径不作为纳入或排除条件。",
}

_HIT_SEGMENTS = frozenset({"execute", "executemany", "raw"})
_DIRECT_HIT = "RawSQL"
_FRAMEWORK_SEGMENTS = frozenset({"extra", "callproc"})
_SCHEMA_EDITOR = "schema_editor"
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_REASON_DETAILS = "unsupported_stage04_details"
_REASON_FRAMEWORK = "missing_framework_context"

def _message(callee: str) -> str:
    return (
        f"调用 {callee}。"
        "此线索只标记原生 SQL 调用形态，供人工复核，不表示已经存在注入，也不表示这条语句不该出现。"
        "证据保留完整调用名和路径，不截取 SQL 字符串来判断它是否安全。"
    )


def _segments(callee: str) -> list[str]:
    return [part.strip() for part in callee.split(".") if part.strip()]


def _last_segment(callee: str) -> str | None:
    parts = _segments(callee)
    if not parts:
        return None
    last = parts[-1]
    if _IDENTIFIER.fullmatch(last):
        return last
    return None


def _ready(callee: str, direct_name: str | None) -> dict[str, Any]:
    return {
        "status": "ready",
        "callee": callee,
        "direct_name": direct_name,
        "last_segment": _last_segment(callee),
    }


def _unsupported() -> dict[str, Any]:
    return {"status": "unsupported", "callee": None, "direct_name": None, "last_segment": None}


def _recover_from_segment(segment: str) -> dict[str, Any] | None:
    """Read one complete call slice when the node has no callee field.

    A slice with zero calls, or with more than one, does not identify the
    node's last segment. Nested calls stay unsupported rather than guessed.
    """
    try:
        tree = ast.parse(textwrap.dedent(segment).strip())
    except SyntaxError:
        return None
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    if len(calls) != 1:
        return None
    func = calls[0].func
    try:
        callee = ast.unparse(func)
    except (AttributeError, ValueError):
        return None
    if not isinstance(callee, str) or not callee.strip() or _last_segment(callee) is None:
        return None
    direct = func.id if isinstance(func, ast.Name) else None
    return _ready(callee.strip(), direct)


def _resolve_call(node: dict[str, Any]) -> dict[str, Any]:
    details = node.get("details") if isinstance(node.get("details"), dict) else {}
    has_callee = "callee" in details
    has_direct = "direct_callee_name" in details
    callee = details.get("callee") if has_callee else None
    direct = details.get("direct_callee_name") if has_direct else None
    if has_direct and direct is not None and not isinstance(direct, str):
        return _unsupported()
    if has_callee:
        # An empty or unsegmentable callee is not completed by another field.
        if not isinstance(callee, str) or not callee.strip() or _last_segment(callee) is None:
            return _unsupported()
        direct_name = direct if isinstance(direct, str) and direct.strip() else None
        return _ready(callee.strip(), direct_name)
    if isinstance(direct, str) and _IDENTIFIER.fullmatch(direct.strip()):
        name = direct.strip()
        return _ready(name, name)
    if node.get("source_segment_truncated"):
        return _unsupported()
    segment = node.get("source_segment")
    if isinstance(segment, str) and segment.strip():
        recovered = _recover_from_segment(segment)
        if recovered is not None:
            return recovered
    return _unsupported()


def _contains_schema_editor(callee: str) -> bool:
    return _SCHEMA_EDITOR in callee


def _classification(resolved: dict[str, Any]) -> str:
    if resolved["status"] != "ready":
        return "unsupported"
    callee = str(resolved["callee"])
    last = resolved["last_segment"]
    if _contains_schema_editor(callee) or last in _FRAMEWORK_SEGMENTS:
        return "framework"
    if resolved["direct_name"] == _DIRECT_HIT or last in _HIT_SEGMENTS:
        return "hit"
    return "examined"


def _change_type(file_item: dict[str, Any], node_id: str | None) -> str:
    for change in file_item.get("structural_changes") or []:
        if not isinstance(change, dict):
            continue
        after = change.get("after") or {}
        if node_id and (change.get("node_id") == node_id or after.get("node_id") == node_id):
            return str(change.get("type") or "added_line_overlap")
    return "added_line_overlap"


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
        if not isinstance(change, dict):
            continue
        after = change.get("after") or {}
        if node_id and (change.get("node_id") == node_id or after.get("node_id") == node_id):
            before = change.get("before")
            return before if isinstance(before, dict) else None
    match_key = node.get("match_key")
    if not match_key:
        return None
    for candidate in file_item.get("nodes") or []:
        if isinstance(candidate, dict) and candidate.get("side") == "base" and candidate.get("match_key") == match_key:
            return candidate
    return None


def _evidence(path: str, file_item: dict[str, Any], node: dict[str, Any], resolved: dict[str, Any]) -> dict[str, Any]:
    after = _slice_record(node, missing_reason="source_missing")
    before = _slice_record(_paired_before(file_item, node), missing_reason="no_base_node")
    evidence: dict[str, Any] = {
        "path": path,
        "node_id": node.get("node_id"),
        "node_kind": node.get("kind"),
        "structural_change_type": _change_type(file_item, node.get("node_id")),
        "lines": sorted(set(node.get("changed_lines") or [])),
        "qualified_name": node.get("qualified_name"),
        "start_line": node.get("start_line"),
        "end_line": node.get("end_line"),
        "impact_type": "pr_intrinsic_risk",
        "callee": resolved["callee"],
        "source_segment": after["source_segment"],
        "source_status": after["status"],
        "before": before,
        "after": after,
    }
    if isinstance(resolved.get("direct_name"), str):
        evidence["direct_callee_name"] = resolved["direct_name"]
    return evidence


def _finding(path: str, file_item: dict[str, Any], node: dict[str, Any], resolved: dict[str, Any]) -> dict[str, Any]:
    callee = str(resolved["callee"])
    return {
        "rule_id": RAW_SQL_RULE_ID,
        "severity": RAW_SQL_RULE["severity"],
        "confidence": "structural",
        "message": _message(callee),
        "impact_type": "pr_intrinsic_risk",
        "evidence": [_evidence(path, file_item, node, resolved)],
        "suggested_action": RAW_SQL_RULE["suggested_action"],
    }


def _changed_head_calls(file_item: dict[str, Any]) -> list[dict[str, Any]]:
    """Head calls that already intersect added lines.

    Stage 04 stores that intersection on ``changed_lines``. This is the same
    filter the code-smell detectors use. Nodes that do not intersect are absent
    or have an empty line list, and are not examined.
    """
    if file_item.get("parse_status", {}).get("head") == "failed":
        return []
    calls: list[dict[str, Any]] = []
    for node in file_item.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        if node.get("side") == "head" and node.get("kind") == "call" and node.get("changed_lines"):
            calls.append(node)
    return calls


def _summary_gaps(gaps: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[str]] = {}
    for gap in gaps:
        grouped.setdefault((gap["path"], gap["reason"]), []).append(gap["node_id"])
    return [
        {"path": path, "reason": reason, "node_ids": sorted(set(node_ids))}
        for (path, reason), node_ids in sorted(grouped.items())
    ]


def collect_django_raw_sql(
    stage04_record: dict[str, Any],
    enabled: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Return findings, summary gaps, and the outcome trace.

    One finding per matching call. Framework-boundary calls and unreadable
    callees are gaps, not hits and not completed misses.
    """
    if RAW_SQL_RULE_ID not in enabled:
        return [], [], {}
    findings: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    examined = 0
    for file_item in stage04_record.get("files") or []:
        if not isinstance(file_item, dict):
            continue
        path = str(file_item.get("path") or file_item.get("new_path") or file_item.get("old_path") or "")
        for node in _changed_head_calls(file_item):
            resolved = _resolve_call(node)
            kind = _classification(resolved)
            node_id = str(node.get("node_id") or "")
            if kind == "hit":
                examined += 1
                findings.append(_finding(path, file_item, node, resolved))
            elif kind == "examined":
                examined += 1
            elif kind == "framework":
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_FRAMEWORK})
            else:
                gaps.append({"path": path, "node_id": node_id, "reason": _REASON_DETAILS})
    findings.sort(
        key=lambda item: (
            item["evidence"][0].get("path") or "",
            item["evidence"][0].get("start_line") or 0,
            item["evidence"][0].get("node_id") or "",
        )
    )
    return findings, _summary_gaps(gaps), {"examined": examined, "gaps": gaps}
