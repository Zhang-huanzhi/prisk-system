"""阶段 05：基于 stage04.v1 的最小结构规则引擎。"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .dataset import load_records, write_jsonl


RULE_SCHEMA_VERSION = "stage05.v1"
RULE_CATALOG = [
    {
        "rule_id": "interface.signature_changed",
        "scene": "interface",
        "severity": "medium",
        "trigger": "API、serializer、view 或 URL Python 文件出现 signature_changed",
        "evidence_type": "structural_change",
        "suggested_action": "复核参数、返回结构、调用方和异常行为",
        "limitations": "只表示接口相关结构变化，不判断兼容性或真实缺陷",
    },
    {
        "rule_id": "auth.permission_structure_changed",
        "scene": "auth",
        "severity": "high",
        "trigger": "权限/认证路径、权限装饰器或权限调用节点发生变化",
        "evidence_type": "structural_change",
        "suggested_action": "复核不同角色的访问边界和未授权响应",
        "limitations": "不推断实际授权结果",
    },
    {
        "rule_id": "data.transaction_structure_changed",
        "scene": "data_transaction",
        "severity": "medium",
        "trigger": "model、migration 或事务/数据库调用节点发生变化",
        "evidence_type": "structural_change",
        "suggested_action": "复核事务边界、提交回滚路径和数据一致性",
        "limitations": "不执行数据库或运行时事务验证",
    },
    {
        "rule_id": "config.exception_structure_changed",
        "scene": "config_exception",
        "severity": "medium",
        "trigger": "settings、configuration 文件或异常处理节点发生变化",
        "evidence_type": "structural_change",
        "suggested_action": "复核默认配置、异常分支和错误响应",
        "limitations": "不判断部署环境中的实际配置值",
    },
]

_INTERFACE_PATH = re.compile(r"/(?:api|graphql)/|(?:serializers?|viewsets?|views?|urls?)\.py$", re.I)
_AUTH_PATH = re.compile(r"/(?:users?|auth|authentication|permissions?)/|(?:permission|authentication)\.py$", re.I)
_DATA_PATH = re.compile(r"/(?:migrations?)/|(?:models?|managers?)\.py$", re.I)
_CONFIG_PATH = re.compile(r"/(?:settings?(?:/|\.py$)|configuration[^/]*\.py$|exceptions?\.py$)", re.I)
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
        "scene": rule["scene"],
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
    if rule_id == "interface.signature_changed":
        return change_type == "signature_changed" and bool(_INTERFACE_PATH.search(normalized))
    if rule_id == "auth.permission_structure_changed":
        return bool(_AUTH_PATH.search(normalized) or (kind == "decorator" and _AUTH_TEXT.search(text)) or (kind == "call" and _AUTH_TEXT.search(text)))
    if rule_id == "data.transaction_structure_changed":
        return bool(_DATA_PATH.search(normalized) or (kind == "call" and _DATA_TEXT.search(text)))
    if rule_id == "config.exception_structure_changed":
        return bool(_CONFIG_PATH.search(normalized) or kind == "except_handler")
    return False


def _testing_collaboration(record: dict[str, Any]) -> bool:
    summary = record.get("summary", {})
    if "business_changed" in summary or "test_changed" in summary:
        return bool(summary.get("business_changed") and not summary.get("test_changed"))
    business_changed = any(file_item.get("role") == "business" for file_item in record.get("files", []))
    test_changed = any(file_item.get("role") == "test" for file_item in record.get("files", []))
    return bool(business_changed and not test_changed)


def evaluate_rules(stage04_record: dict[str, Any], rule_config: dict[str, Any] | None = None) -> dict[str, Any]:
    status = stage04_record.get("status")
    if status == "excluded":
        return {
            "schema_version": RULE_SCHEMA_VERSION,
            "status": "excluded",
            "repo": stage04_record.get("repo"),
            "pr_number": stage04_record.get("pr_number"),
            "findings": [],
            "summary": {"finding_count": 0, "scenes": [], "test_collaboration": False, "parse_degraded": False},
            "errors": [],
        }
    if status != "ok":
        return {
            "schema_version": RULE_SCHEMA_VERSION,
            "status": "error",
            "repo": stage04_record.get("repo"),
            "pr_number": stage04_record.get("pr_number"),
            "findings": [],
            "summary": {"finding_count": 0, "scenes": [], "test_collaboration": False, "parse_degraded": False},
            "errors": stage04_record.get("errors", []),
        }

    enabled = set((rule_config or {}).get("enabled_rules", [item["rule_id"] for item in RULE_CATALOG]))
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

    degraded = any(
        "failed" in file_item.get("parse_status", {}).values()
        for file_item in stage04_record.get("files", [])
    )
    scenes = sorted({item["scene"] for item in findings})
    return {
        "schema_version": RULE_SCHEMA_VERSION,
        "status": "ok",
        "repo": stage04_record.get("repo"),
        "pr_number": stage04_record.get("pr_number"),
        "base_sha": stage04_record.get("base_sha"),
        "head_sha": stage04_record.get("head_sha"),
        "findings": findings,
        "summary": {
            "finding_count": len(findings),
            "scenes": scenes,
            "test_collaboration": _testing_collaboration(stage04_record),
            "parse_degraded": degraded,
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
