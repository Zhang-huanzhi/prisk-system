"""阶段 05：基于 stage04.v1 的最小结构规则引擎。"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .changes import load_records, write_jsonl
from .code_smells import CODE_SMELL_RULES, collect_code_smell_findings
from .django_raw_sql import RAW_SQL_RULE, RAW_SQL_RULE_ID, collect_django_raw_sql
from .high_value_detectors import HIGH_VALUE_RULE_IDS, HIGH_VALUE_RULES, collect_high_value_findings
from .test_collaboration import COLLABORATION_RULE_ID, collaboration_terminal, collect_test_collaboration


RULE_SCHEMA_VERSION = "stage05.v2"
RULE_DOMAINS = frozenset({"api", "auth", "data", "config", "code", "workflow"})
_RULE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
RULE_CATALOG = [
    {
        "rule_id": "api.signature_changed",
        "severity": "medium",
        "trigger": "API、serializer、view 或 URL Python 文件出现 signature_changed",
        "evidence_type": "structural_change",
        "suggested_action": "复核参数、返回结构、调用方和异常行为",
        "limitations": "只表示接口相关结构变化，不判断兼容性或真实缺陷",
    },
    {
        "rule_id": "auth.permission_structure_changed",
        "severity": "high",
        "trigger": "权限/认证路径、权限装饰器或权限调用节点发生变化",
        "evidence_type": "structural_change",
        "suggested_action": "复核不同角色的访问边界和未授权响应",
        "limitations": "不推断实际授权结果",
    },
    {
        "rule_id": "data.transaction_structure_changed",
        "severity": "medium",
        "trigger": "model、migration 或事务/数据库调用节点发生变化",
        "evidence_type": "structural_change",
        "suggested_action": "复核事务边界、提交回滚路径和数据一致性",
        "limitations": "不执行数据库或运行时事务验证",
    },
    {
        "rule_id": "config.configuration_structure_changed",
        "severity": "medium",
        "trigger": "settings 或 configuration 文件发生结构变化",
        "evidence_type": "structural_change",
        "suggested_action": "复核默认配置、环境覆盖和部署行为",
        "limitations": "不判断部署环境中的实际配置值，也不覆盖异常处理逻辑",
    },
    {
        "rule_id": "code.exception_structure_changed",
        "severity": "medium",
        "trigger": "异常处理节点发生结构变化",
        "evidence_type": "structural_change",
        "suggested_action": "复核异常分支、错误响应和调用方处理",
        "limitations": "不判断运行时异常传播或实际错误响应",
    },
    *CODE_SMELL_RULES,
    RAW_SQL_RULE,
    *HIGH_VALUE_RULES,
    {
        "rule_id": COLLABORATION_RULE_ID,
        "severity": "medium",
        "trigger": "生产代码有行数证据的新增、修改或删除，且没有测试文件新增、修改、删除或重命名",
        "evidence_type": "metric_value",
        "suggested_action": "复核这些生产代码路径是否仍有相应测试计划。本规则不判断已有测试是否足够。",
        "limitations": "只比较默认路径分类下的文件变更。纯重命名不是生产内容变化。统计或分类不完整时进入未分析，不表示通过，也不说明测试缺失、回归或缺陷。",
    },
]

_INTERFACE_PATH = re.compile(r"/(?:api|graphql)/|(?:serializers?|viewsets?|views?|urls?)\.py$", re.I)
_AUTH_PATH = re.compile(r"/(?:users?|auth|authentication|permissions?)/|(?:permission|authentication)\.py$", re.I)
_DATA_PATH = re.compile(r"/(?:migrations?)/|(?:models?|managers?)\.py$", re.I)
_CONFIG_PATH = re.compile(r"/(?:settings?(?:/|\.py$)|configuration[^/]*\.py$)", re.I)
_AUTH_TEXT = re.compile(r"permission|authorization|authentication|has_perm|restrict_queryset|owner|role|auth", re.I)
_DATA_TEXT = re.compile(r"transaction|atomic|commit|rollback|select|insert|update|delete|save|bulk|query", re.I)


def _normalized_path(path: str | None) -> str:
    value = (path or "").replace("\\", "/")
    return f"/{value.lstrip('/')}"


def _node_for_change(change: dict[str, Any]) -> dict[str, Any]:
    return change.get("after") or change.get("before") or {}


def _evidence(path: str, change: dict[str, Any]) -> dict[str, Any]:
    node = _node_for_change(change)
    return {
        "path": path,
        "node_id": change.get("node_id") or node.get("node_id"),
        "node_kind": change.get("kind") or node.get("kind"),
        "structural_change_type": change.get("type"),
        "lines": sorted(set(change.get("evidence_lines", []))),
        "qualified_name": node.get("qualified_name"),
    }


def _finding(rule: dict[str, Any], path: str, changes: list[dict[str, Any]]) -> dict[str, Any]:
    evidence = [_evidence(path, change) for change in changes]
    return {
        "rule_id": rule["rule_id"],
        "severity": rule["severity"],
        "confidence": "structural",
        "message": rule["trigger"],
        "evidence": evidence,
        "suggested_action": rule["suggested_action"],
    }


def _match_rule(rule_id: str, path: str, file_item: dict[str, Any], change: dict[str, Any]) -> bool:
    normalized = _normalized_path(path)
    kind = str(change.get("kind") or "")
    change_type = str(change.get("type") or "")
    node = _node_for_change(change)
    details = node.get("details", {})
    text = " ".join(
        str(value)
        for value in (
            node.get("name"),
            node.get("qualified_name"),
            details.get("callee"),
            details.get("expression"),
            details.get("exception_type"),
        )
        if value is not None
    )
    if rule_id == "api.signature_changed":
        return change_type == "signature_changed" and bool(_INTERFACE_PATH.search(normalized))
    if rule_id == "auth.permission_structure_changed":
        return bool(_AUTH_PATH.search(normalized) or (kind == "decorator" and _AUTH_TEXT.search(text)) or (kind == "call" and _AUTH_TEXT.search(text)))
    if rule_id == "data.transaction_structure_changed":
        return bool(_DATA_PATH.search(normalized) or (kind == "call" and _DATA_TEXT.search(text)))
    if rule_id == "config.configuration_structure_changed":
        return bool(_CONFIG_PATH.search(normalized))
    if rule_id == "code.exception_structure_changed":
        return kind == "except_handler"
    return False


def rule_domain(rule_id: str) -> str:
    """Return the UI and aggregation domain encoded in a two-part rule ID."""
    return rule_id.split(".", 1)[0]


def validate_rule_catalog() -> None:
    ids = [rule["rule_id"] for rule in RULE_CATALOG]
    if len(ids) != len(set(ids)):
        raise ValueError("规则 ID 必须全局唯一")
    invalid = [rule_id for rule_id in ids if not _RULE_ID_PATTERN.fullmatch(rule_id)]
    if invalid:
        raise ValueError(f"规则 ID 必须是两段 snake_case: {invalid}")
    invalid_domains = [rule_id for rule_id in ids if rule_domain(rule_id) not in RULE_DOMAINS]
    if invalid_domains:
        raise ValueError(f"规则 domain 不在允许集合中: {invalid_domains}")


validate_rule_catalog()


def _merge_unanalyzed(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fold later gaps into the first entry with the same path and reason.

    A call the code-smell pass cannot read is also unreadable for the raw-SQL
    rule. Keep one summary row, and add only node ids the first row lacked.
    """
    merged: list[dict[str, Any]] = []
    index: dict[tuple[str, str], int] = {}
    for entry in entries:
        path = str(entry.get("path") or "")
        reason = str(entry.get("reason") or "")
        key = (path, reason)
        if key not in index:
            copied = dict(entry)
            node_ids = copied.get("node_ids")
            if isinstance(node_ids, list):
                copied["node_ids"] = list(node_ids)
            index[key] = len(merged)
            merged.append(copied)
            continue
        extra_ids = entry.get("node_ids")
        if not isinstance(extra_ids, list):
            continue
        current = merged[index[key]]
        existing = current.get("node_ids")
        if not isinstance(existing, list):
            current["node_ids"] = list(extra_ids)
            continue
        added = False
        for node_id in extra_ids:
            if node_id not in existing:
                existing.append(node_id)
                added = True
        if added:
            current["node_ids"] = sorted(existing)
    return merged


def _unanalyzed_files(record: dict[str, Any]) -> list[dict[str, str]]:
    """Head AST 不可用时记录未分析文件。空 Finding 在这种情况下不是通过。"""
    entries: list[dict[str, str]] = []
    for file_item in record.get("files", []):
        if file_item.get("parse_status", {}).get("head") != "failed":
            continue
        reason = "head_parse_failed"
        for error in file_item.get("errors", []):
            code = error.get("code")
            if code:
                reason = str(code)
                break
        path = str(file_item.get("path") or file_item.get("new_path") or file_item.get("old_path") or "")
        entries.append({"path": path, "reason": reason})
    return entries


def _testing_collaboration(finding: dict[str, Any] | None) -> bool:
    """The historical score flag is true only when this rule emits a Finding."""
    return finding is not None


_TERMINAL_HIT = "Hit"
_TERMINAL_NOT_FOUND = "NotFound"
_TERMINAL_UNANALYZED = "Unanalyzed"
_REASON_FRAMEWORK = "missing_framework_context"
_REASON_CONTEXT = "context_not_established"
_REASON_PRIOR = "prior_stage_unavailable"
_REASON_DETAILS = "unsupported_stage04_details"
_SMELL_RULE_IDS = frozenset(rule["rule_id"] for rule in CODE_SMELL_RULES)
_PATH_RULES = {
    "api.signature_changed": _INTERFACE_PATH,
    "config.configuration_structure_changed": _CONFIG_PATH,
}


def _record_path(file_item: dict[str, Any]) -> str:
    return str(file_item.get("path") or file_item.get("new_path") or file_item.get("old_path") or "")


def _head_state(file_item: dict[str, Any]) -> str | None:
    status = file_item.get("parse_status")
    if not isinstance(status, dict):
        return None
    head = status.get("head")
    return str(head) if isinstance(head, str) else None


def _is_python_file(file_item: dict[str, Any]) -> bool:
    path = _record_path(file_item).lower()
    if path.endswith((".py", ".pyi")) or file_item.get("is_python") is True:
        return True
    return _head_state(file_item) in {"ok", "failed"}


def _structurally_scanned(file_item: dict[str, Any]) -> bool:
    if not isinstance(file_item.get("structural_changes"), list):
        return False
    return _head_state(file_item) not in {"failed", "skipped"}


def _parse_reason(file_item: dict[str, Any]) -> str:
    for error in file_item.get("errors") or []:
        if isinstance(error, dict) and error.get("code"):
            return str(error["code"])
    if _head_state(file_item) == "failed":
        return "head_parse_failed"
    return _REASON_CONTEXT


def _object(path: str, node_id: str | None = None) -> dict[str, str]:
    item = {"path": path}
    if node_id:
        item["node_id"] = node_id
    return item


def _dedupe_objects(objects: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, str]] = []
    for item in objects:
        key = (item.get("path", ""), item.get("node_id", ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    unique.sort(key=lambda item: (item.get("path", ""), item.get("node_id", "")))
    return unique


def _reasons_from_pairs(pairs: list[tuple[str, dict[str, str]]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for reason, obj in pairs:
        grouped.setdefault(reason, []).append(obj)
    return [
        {"reason": reason, "objects": _dedupe_objects(objects)}
        for reason, objects in sorted(grouped.items())
    ]


def _terminal(rule_id: str, state: str, reasons: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"rule_id": rule_id, "state": state}
    if state == _TERMINAL_UNANALYZED:
        item["reasons"] = reasons or [{"reason": _REASON_CONTEXT, "objects": []}]
    return item


def _blocking_reasons(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pairs = [
        (_parse_reason(file_item), _object(_record_path(file_item)))
        for file_item in files
        if not _structurally_scanned(file_item)
    ]
    return _reasons_from_pairs(pairs)


def _path_scoped_terminal(rule_id: str, files: list[dict[str, Any]], pattern: re.Pattern[str]) -> dict[str, Any]:
    in_scope = [item for item in files if pattern.search(_normalized_path(_record_path(item)))]
    if not in_scope:
        return _terminal(rule_id, _TERMINAL_UNANALYZED, [{"reason": _REASON_FRAMEWORK, "objects": []}])
    blocking = _blocking_reasons(in_scope)
    if blocking:
        return _terminal(rule_id, _TERMINAL_UNANALYZED, blocking)
    return _terminal(rule_id, _TERMINAL_NOT_FOUND)


def _kind_terminal(
    rule_id: str,
    files: list[dict[str, Any]],
    *,
    path_pattern: re.Pattern[str],
    kinds: frozenset[str],
) -> dict[str, Any]:
    """Auth and data rules inspect a path scope plus selected node kinds.

    A failed or missing Python structural scan can hide those kinds, so it
    stays Unanalyzed. A diff with neither the path nor those kinds has no
    framework context and is not NotFound.
    """
    blocking = _blocking_reasons([item for item in files if _is_python_file(item)])
    if blocking:
        return _terminal(rule_id, _TERMINAL_UNANALYZED, blocking)
    scoped = [item for item in files if path_pattern.search(_normalized_path(_record_path(item)))]
    saw_kind = False
    for item in files:
        changes = item.get("structural_changes")
        if not isinstance(changes, list):
            continue
        for change in changes:
            if isinstance(change, dict) and str(change.get("kind") or "") in kinds:
                saw_kind = True
                break
    if any(not _structurally_scanned(item) for item in scoped):
        return _terminal(rule_id, _TERMINAL_UNANALYZED, _blocking_reasons(scoped))
    if scoped or saw_kind:
        return _terminal(rule_id, _TERMINAL_NOT_FOUND)
    return _terminal(rule_id, _TERMINAL_UNANALYZED, [{"reason": _REASON_FRAMEWORK, "objects": []}])


def _exception_terminal(files: list[dict[str, Any]]) -> dict[str, Any]:
    python_files = [item for item in files if _is_python_file(item)]
    if not python_files:
        return _terminal(
            "code.exception_structure_changed",
            _TERMINAL_UNANALYZED,
            [{"reason": _REASON_CONTEXT, "objects": []}],
        )
    blocking = _blocking_reasons(python_files)
    if blocking:
        return _terminal("code.exception_structure_changed", _TERMINAL_UNANALYZED, blocking)
    return _terminal("code.exception_structure_changed", _TERMINAL_NOT_FOUND)


def _raw_sql_terminal(
    trace: dict[str, Any],
    parse_failures: list[dict[str, Any]],
) -> dict[str, Any]:
    """NotFound only after at least one call was fully classified.

    Framework-boundary calls and unreadable callees block NotFound. A file
    with no intersecting call stays ``context_not_established``. Parse failures
    stay Unanalyzed, including when some other call was examined.
    """
    info = trace or {"examined": 0, "gaps": []}
    pairs: list[tuple[str, dict[str, str]]] = []
    for gap in info.get("gaps") or []:
        if not isinstance(gap, dict):
            continue
        node_id = str(gap.get("node_id") or "") or None
        pairs.append((str(gap.get("reason") or _REASON_DETAILS), _object(str(gap.get("path") or ""), node_id)))
    for failure in parse_failures:
        pairs.append((
            str(failure.get("reason") or "head_parse_failed"),
            _object(str(failure.get("path") or "")),
        ))
    reasons = _reasons_from_pairs(pairs)
    if reasons:
        return _terminal(RAW_SQL_RULE_ID, _TERMINAL_UNANALYZED, reasons)
    if int(info.get("examined") or 0) > 0:
        return _terminal(RAW_SQL_RULE_ID, _TERMINAL_NOT_FOUND)
    return _terminal(RAW_SQL_RULE_ID, _TERMINAL_UNANALYZED, [{"reason": _REASON_CONTEXT, "objects": []}])



def _high_value_terminal(
    rule_id: str,
    trace: dict[str, dict[str, Any]],
    parse_failures: list[dict[str, Any]],
) -> dict[str, Any]:
    """Preserve collector gap reasons (framework vs details)."""
    info = trace.get(rule_id) or {"examined": 0, "gaps": []}
    pairs: list[tuple[str, dict[str, str]]] = []
    for gap in info.get("gaps") or []:
        if not isinstance(gap, dict):
            continue
        node_id = str(gap.get("node_id") or "") or None
        reason = str(gap.get("reason") or _REASON_DETAILS)
        pairs.append((reason, _object(str(gap.get("path") or ""), node_id)))
    for failure in parse_failures:
        pairs.append((
            str(failure.get("reason") or "head_parse_failed"),
            _object(str(failure.get("path") or "")),
        ))
    reasons = _reasons_from_pairs(pairs)
    if reasons:
        return _terminal(rule_id, _TERMINAL_UNANALYZED, reasons)
    if int(info.get("examined") or 0) > 0:
        return _terminal(rule_id, _TERMINAL_NOT_FOUND)
    return _terminal(rule_id, _TERMINAL_UNANALYZED, [{"reason": _REASON_CONTEXT, "objects": []}])

def _smell_terminal(
    rule_id: str,
    trace: dict[str, dict[str, Any]],
    parse_failures: list[dict[str, Any]],
) -> dict[str, Any]:
    info = trace.get(rule_id) or {"examined": 0, "gaps": []}
    pairs: list[tuple[str, dict[str, str]]] = []
    for gap in info.get("gaps") or []:
        if not isinstance(gap, dict):
            continue
        node_id = str(gap.get("node_id") or "") or None
        pairs.append((_REASON_DETAILS, _object(str(gap.get("path") or ""), node_id)))
    for failure in parse_failures:
        pairs.append((
            str(failure.get("reason") or "head_parse_failed"),
            _object(str(failure.get("path") or "")),
        ))
    reasons = _reasons_from_pairs(pairs)
    if reasons:
        return _terminal(rule_id, _TERMINAL_UNANALYZED, reasons)
    if int(info.get("examined") or 0) > 0:
        return _terminal(rule_id, _TERMINAL_NOT_FOUND)
    return _terminal(rule_id, _TERMINAL_UNANALYZED, [{"reason": _REASON_CONTEXT, "objects": []}])


def _unavailable_outcomes(enabled: set[str]) -> list[dict[str, Any]]:
    return [
        _terminal(rule["rule_id"], _TERMINAL_UNANALYZED, [{"reason": _REASON_PRIOR, "objects": []}])
        for rule in RULE_CATALOG
        if rule["rule_id"] in enabled
    ]


def _rule_outcomes(
    record: dict[str, Any],
    enabled: set[str],
    findings: list[dict[str, Any]],
    smell_trace: dict[str, dict[str, Any]],
    raw_sql_trace: dict[str, Any],
    high_value_trace: dict[str, dict[str, Any]],
    collaboration_finding: dict[str, Any] | None,
    collaboration_gaps: list[dict[str, str]],
    parse_failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """One terminal state per enabled rule. Hit is exactly the rules with findings."""
    finding_ids = {item.get("rule_id") for item in findings}
    files = [item for item in record.get("files") or [] if isinstance(item, dict)]
    outcomes: list[dict[str, Any]] = []
    for rule in RULE_CATALOG:
        rule_id = rule["rule_id"]
        if rule_id not in enabled:
            continue
        if rule_id in finding_ids:
            outcomes.append(_terminal(rule_id, _TERMINAL_HIT))
            continue
        if rule_id in _PATH_RULES:
            outcomes.append(_path_scoped_terminal(rule_id, files, _PATH_RULES[rule_id]))
        elif rule_id == "auth.permission_structure_changed":
            outcomes.append(_kind_terminal(
                rule_id, files, path_pattern=_AUTH_PATH, kinds=frozenset({"decorator", "call"}),
            ))
        elif rule_id == "data.transaction_structure_changed":
            outcomes.append(_kind_terminal(
                rule_id, files, path_pattern=_DATA_PATH, kinds=frozenset({"call"}),
            ))
        elif rule_id == "code.exception_structure_changed":
            outcomes.append(_exception_terminal(files))
        elif rule_id in _SMELL_RULE_IDS:
            outcomes.append(_smell_terminal(rule_id, smell_trace, parse_failures))
        elif rule_id == RAW_SQL_RULE_ID:
            outcomes.append(_raw_sql_terminal(raw_sql_trace, parse_failures))
        elif rule_id in HIGH_VALUE_RULE_IDS:
            outcomes.append(_high_value_terminal(rule_id, high_value_trace, parse_failures))
        elif rule_id == COLLABORATION_RULE_ID:
            state, reasons = collaboration_terminal(record, collaboration_finding, collaboration_gaps)
            outcomes.append(_terminal(rule_id, state, reasons))
        else:
            outcomes.append(_terminal(rule_id, _TERMINAL_UNANALYZED, [{"reason": _REASON_CONTEXT, "objects": []}]))
    return outcomes


def evaluate_rules(stage04_record: dict[str, Any], rule_config: dict[str, Any] | None = None) -> dict[str, Any]:
    status = stage04_record.get("status")
    config_dict = rule_config or {}
    enabled = set(config_dict.get("enabled_rules", [item["rule_id"] for item in RULE_CATALOG]))
    rule_thresholds = config_dict.get("rule_thresholds", {})
    if status == "excluded":
        return {
            "schema_version": RULE_SCHEMA_VERSION,
            "status": "excluded",
            "repo": stage04_record.get("repo"),
            "pr_number": stage04_record.get("pr_number"),
            "findings": [],
            "rule_outcomes": _unavailable_outcomes(enabled),
            "summary": {"finding_count": 0, "domains": [], "test_collaboration": False, "parse_degraded": False, "unanalyzed": []},
            "errors": [],
        }
    if status != "ok":
        return {
            "schema_version": RULE_SCHEMA_VERSION,
            "status": "error",
            "repo": stage04_record.get("repo"),
            "pr_number": stage04_record.get("pr_number"),
            "findings": [],
            "rule_outcomes": _unavailable_outcomes(enabled),
            "summary": {"finding_count": 0, "domains": [], "test_collaboration": False, "parse_degraded": False, "unanalyzed": []},
            "errors": stage04_record.get("errors", []),
        }

    findings: list[dict[str, Any]] = []
    for rule in RULE_CATALOG:
        if rule["rule_id"] not in enabled:
            continue
        matched_by_path: dict[str, list[dict[str, Any]]] = {}
        for file_item in stage04_record.get("files", []):
            path = str(file_item.get("path") or file_item.get("new_path") or file_item.get("old_path") or "")
            for change in file_item.get("structural_changes", []):
                if _match_rule(rule["rule_id"], path, file_item, change):
                    matched_by_path.setdefault(path, []).append(change)
        for path, changes in sorted(matched_by_path.items()):
            findings.append(_finding(rule, path, changes))
    smell_findings, smell_gaps, smell_trace = collect_code_smell_findings(stage04_record, enabled, rule_thresholds=rule_thresholds)
    findings.extend(smell_findings)
    raw_sql_findings, raw_sql_gaps, raw_sql_trace = collect_django_raw_sql(stage04_record, enabled)
    findings.extend(raw_sql_findings)
    high_value_findings, high_value_gaps, high_value_trace = collect_high_value_findings(stage04_record, enabled)
    findings.extend(high_value_findings)
    collaboration_finding, collaboration_gaps = collect_test_collaboration(stage04_record, enabled)
    if collaboration_finding is not None:
        findings.append(collaboration_finding)

    degraded = any(
        "failed" in file_item.get("parse_status", {}).values()
        for file_item in stage04_record.get("files", [])
    )
    domains = sorted({rule_domain(item["rule_id"]) for item in findings})
    parse_failures = _unanalyzed_files(stage04_record)
    return {
        "schema_version": RULE_SCHEMA_VERSION,
        "status": "ok",
        "repo": stage04_record.get("repo"),
        "pr_number": stage04_record.get("pr_number"),
        "base_sha": stage04_record.get("base_sha"),
        "head_sha": stage04_record.get("head_sha"),
        "findings": findings,
        "rule_outcomes": _rule_outcomes(
            stage04_record,
            enabled,
            findings,
            smell_trace,
            raw_sql_trace,
            high_value_trace,
            collaboration_finding,
            collaboration_gaps,
            parse_failures,
        ),
        "summary": {
            "finding_count": len(findings),
            "domains": domains,
            "test_collaboration": _testing_collaboration(collaboration_finding),
            "parse_degraded": degraded,
            "unanalyzed": _merge_unanalyzed([*parse_failures, *smell_gaps, *raw_sql_gaps, *high_value_gaps, *collaboration_gaps]),
        },
        "errors": [],
    }


def evaluate_dataset(
    input_path: Path,
    output_path: Path,
    manifest_path: Path | None = None,
    rule_config: dict[str, Any] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    records = load_records(input_path)
    if limit is not None:
        if limit < 1:
            raise ValueError("limit 必须大于 0")
        by_pr = {record.get("pr_number"): record for record in records if record.get("pr_number") is not None}
        pilot = [by_pr[number] for number in (179, 19, 226) if number in by_pr]
        selected = pilot[:limit]
        for record in records:
            if len(selected) >= limit:
                break
            if record not in selected:
                selected.append(record)
        records = selected
    results = [evaluate_rules(record, rule_config) for record in records]
    write_jsonl(results, output_path)
    status_counts = Counter(item["status"] for item in results)
    finding_count = sum(item["summary"]["finding_count"] for item in results)
    evidence_count = sum(
        len(finding.get("evidence", []))
        for item in results
        for finding in item.get("findings", [])
    )
    complete_evidence = sum(
        1
        for item in results
        for finding in item.get("findings", [])
        for evidence in finding.get("evidence", [])
        if evidence.get("path") and evidence.get("node_id") and evidence.get("lines")
    )
    per_rule: dict[str, dict[str, int]] = {}
    for item in results:
        for finding in item.get("findings", []):
            counts = per_rule.setdefault(finding["rule_id"], {"evidence": 0, "usable_evidence": 0})
            counts["evidence"] += len(finding.get("evidence", []))
            counts["usable_evidence"] += sum(
                bool(evidence.get("path") and evidence.get("node_id") and evidence.get("lines"))
                for evidence in finding.get("evidence", [])
            )
    manifest = {
        "schema_version": RULE_SCHEMA_VERSION,
        "input_path": str(input_path),
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "input_records": len(records),
        "status_counts": dict(sorted(status_counts.items())),
        "finding_count": finding_count,
        "evidence_count": evidence_count,
        "evidence_completeness": round(complete_evidence / evidence_count, 4) if evidence_count else None,
        "rule_evidence_usability": {
            rule_id: {
                **counts,
                "ratio": round(counts["usable_evidence"] / counts["evidence"], 4) if counts["evidence"] else None,
            }
            for rule_id, counts in sorted(per_rule.items())
        },
        "degraded_pr_count": sum(item["summary"].get("parse_degraded", False) for item in results),
        "output_path": str(output_path),
    }
    if manifest_path is not None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def write_rule_catalog(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": RULE_SCHEMA_VERSION, "rules": RULE_CATALOG}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
