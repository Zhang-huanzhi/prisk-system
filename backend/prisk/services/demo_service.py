"""Teacher-demo data API and transparent priority scoring for stages 06/07."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from ..domain.changes import load_records
from ..domain.rules import RULE_CATALOG, rule_domain
from ..domain.test_collaboration import COLLABORATION_RULE_ID
from ..domain.gatekeeper import apply_gatekeeper_lift


DEFAULT_CONFIG: dict[str, Any] = {
    "enabled_rules": [rule["rule_id"] for rule in RULE_CATALOG],
    "rule_weights": {
        "api.signature_changed": 2,
        "auth.permission_structure_changed": 3,
        "data.transaction_structure_changed": 2,
        "config.configuration_structure_changed": 1,
        "code.exception_structure_changed": 1,
        "code.swallowed_exception": 0,
        "code.bare_exception": 0,
        "code.dynamic_execution": 0,
        "code.unmanaged_open": 0,
        "code.deep_control_flow": 0,
        "code.hardcoded_secret": 0,
        "code.global_mutable_state": 0,
        "data.django_raw_sql_execution": 0,
        "auth.django_csrf_exempt_added": 0,
        "api.drf_viewset_action_changed": 0,
        "data.django_destructive_migration": 0,
        "auth.drf_permission_policy_downgrade": 0,
        "config.django_sensitive_settings_changed": 0,
        "data.django_non_null_constraint_tightened": 0,
        "auth.drf_permission_decorator_removed": 0,
        "auth.drf_queryset_scope_tighten_bypassed": 0,
        "data.django_signal_receiver_leak": 0,
        "data.django_field_rename_without_db_column": 0,
        "api.drf_public_parameter_added": 0,
        "api.drf_public_parameter_removed": 0,
        COLLABORATION_RULE_ID: 1,
    },
    "test_collaboration_weight": 1,
    "test_collaboration_enabled": True,
    "thresholds": {"medium": 30, "high": 65},
}

RULE_SCOPES = {
    "api.signature_changed": "API、serializer、view、viewset 和 URL 相关 Python 文件",
    "auth.permission_structure_changed": "权限、认证路径，以及权限装饰器和权限调用节点",
    "data.transaction_structure_changed": "model、migration、manager，以及事务和数据库调用节点",
    "config.configuration_structure_changed": "settings 和 configuration 文件",
    "code.exception_structure_changed": "异常处理节点",
    "code.swallowed_exception": "Python 异常处理分支的处理体只有 pass",
    "code.bare_exception": "Python 裸 except，或直接名称 BaseException（不含 except Exception）",
    "code.dynamic_execution": "Python 直接名称 eval 或 exec 调用，不含 compile",
    "code.unmanaged_open": "Python 直接名称 open 或 Path(...).open，且不是 with / async with 的上下文表达式",
    "code.deep_control_flow": "Python if、for、while、with、try 的嵌套深度大于固定阈值 4",
    "code.hardcoded_secret": "Python 凭据名字上长度不少于 8 且不在占位符表中的 str 字面量",
    "code.global_mutable_state": "Python 函数体内的 global，或模块与类体中的列表、字典、集合绑定",
    "data.django_raw_sql_execution": "与新增行相交的 RawSQL 直接名称，或 callee 最后一段为 execute、executemany、raw。路径只作证据",
    "auth.django_csrf_exempt_added": "同一所有者上新增的 csrf_exempt 或 method_decorator(csrf_exempt)",
    "api.drf_viewset_action_changed": "闭集 ViewSet 上标准动作或 @action 的有无 / detail / methods 变化",
    "data.django_destructive_migration": "migrations 路径上与新增行相交的 DeleteModel 或 RemoveField",
    "auth.drf_permission_policy_downgrade": "permission_classes 或 @permission_classes 显式 AllowAny 或空列表/元组",
    "config.django_sensitive_settings_changed": "七个部署检查清单设置名的模块级赋值呈放宽或不安全方向",
    "data.django_non_null_constraint_tightened": "模型字段或迁移 AlterField/AddField 上 null 收紧且未见 default=",
    "auth.drf_permission_decorator_removed": "同一所有者上闭集权限装饰器被移除，且同文件无 permission_classes 赋值",
    "auth.drf_queryset_scope_tighten_bypassed": "闭集 ViewSet 上 get_queryset 返回未过滤 objects.all",
    "data.django_signal_receiver_leak": "闭集信号的 connect/@receiver 缺少 dispatch_uid",
    "data.django_field_rename_without_db_column": "非 migrations 路径上 Model 字段一对一改名且无 db_column",
    "api.drf_public_parameter_added": "已有 Serializer 或 @api_view/@action 表面新增必填参数",
    "api.drf_public_parameter_removed": "已有 Serializer 或 @api_view/@action 表面删除参数/字段",
    COLLABORATION_RULE_ID: "默认路径分类下的生产代码内容变更，且同一变更没有测试文件变更",
}


class DemoData:
    def __init__(self, stage03_path: Path, stage04_path: Path, stage05_path: Path) -> None:
        self.stage03_path = stage03_path
        self.stage04_path = stage04_path
        self.stage05_path = stage05_path
        self.stage03 = {record.get("pr_number"): record for record in load_records(stage03_path)}
        self.stage04 = {record.get("pr_number"): record for record in load_records(stage04_path)}
        self.stage05 = {record.get("pr_number"): record for record in load_records(stage05_path)}

    def pr_numbers(self) -> list[int]:
        return sorted(number for number in self.stage05 if isinstance(number, int))

    def analyze(
        self,
        pr_number: int,
        config: dict[str, Any] | None = None,
        *,
        include_diff: bool = True,
    ) -> dict[str, Any]:
        rule_record = self.stage05.get(pr_number)
        if rule_record is None:
            raise KeyError(f"PR #{pr_number} 不存在")
        stage03 = self.stage03.get(pr_number, {})
        stage04 = self.stage04.get(pr_number, {})
        config_value = normalize_config(config)
        findings = rule_record.get("findings", [])
        enabled = set(config_value["enabled_rules"])
        selected = [finding for finding in findings if finding.get("rule_id") in enabled]
        found_rule_ids = {finding.get("rule_id") for finding in selected}
        max_points = summed_rule_points(enabled, config_value["rule_weights"])
        earned = summed_rule_points(found_rule_ids, config_value["rule_weights"])
        collaboration = bool(rule_record.get("summary", {}).get("test_collaboration"))
        collaboration_maximum, collaboration_earned = collaboration_points(config_value, collaboration)
        max_points += collaboration_maximum
        earned += collaboration_earned
        score = round(100 * earned / max_points) if max_points else 0
        thresholds = config_value["thresholds"]
        level = "high" if score >= thresholds["high"] else "medium" if score >= thresholds["medium"] else "low"
        level, gatekeeper_basis = apply_gatekeeper_lift(
            risk_level=level,
            findings=selected,
            stage_record=stage04 if isinstance(stage04, dict) else {},
        )

        nodes = {
            node.get("node_id"): node
            for file_item in stage04.get("files", [])
            for node in file_item.get("nodes", [])
            if node.get("node_id")
        }
        enriched_findings = []
        for finding in selected:
            evidence = []
            for item in finding.get("evidence", []):
                node = nodes.get(item.get("node_id"), {})
                node_source = node.get("source_segment")
                evidence.append({
                    **item,
                    "source_segment": node_source if node_source is not None else item.get("source_segment"),
                    "node_start_line": node.get("start_line", item.get("start_line")),
                    "node_end_line": node.get("end_line", item.get("end_line")),
                })
            enriched_findings.append({**finding, "evidence": evidence})

        summary = stage03.get("summary", {})
        files = stage03.get("files", [])
        structure_files = {
            item.get("path") or item.get("new_path") or item.get("old_path"): item
            for item in stage04.get("files", [])
        }
        domains = sorted({rule_domain(item["rule_id"]) for item in enriched_findings})
        stored_outcomes = rule_record.get("rule_outcomes")
        if isinstance(stored_outcomes, list):
            rule_outcomes = [
                item for item in stored_outcomes
                if isinstance(item, dict) and item.get("rule_id") in enabled
            ]
            outcome_availability = "recorded"
        else:
            rule_outcomes = None
            outcome_availability = "unavailable"
        return {
            "schema_version": "stage07.report.v2",
            "status": rule_record.get("status", "error"),
            "repo": stage03.get("repo", rule_record.get("repo")),
            "pr_number": pr_number,
            "title": stage03.get("source", {}).get("title") or f"Pull Request #{pr_number}",
            "author": stage03.get("source", {}).get("author"),
            "url": stage03.get("source", {}).get("url"),
            "merged_at": stage03.get("source", {}).get("merged_at"),
            "base_sha": stage03.get("base_sha"),
            "head_sha": stage03.get("head_sha"),
            "score": score,
            "risk_level": level,
            "score_label": "复核优先级（结构评分）",
            "score_basis": {
                "earned_points": earned,
                "maximum_points": max_points,
                "matched_rule_ids": sorted(found_rule_ids),
                "test_collaboration": collaboration,
                "configuration": config_value,
                **gatekeeper_basis,
            },
            "summary": {
                "finding_count": len(enriched_findings),
                "domains": domains,
                "files_changed": summary.get("files_changed", len(files)),
                "business_files": summary.get("business_files", 0),
                "test_files": summary.get("test_files", 0),
                "additions": summary.get("additions", 0),
                "deletions": summary.get("deletions", 0),
                "business_changed": summary.get("business_changed", False),
                "test_changed": summary.get("test_changed", False),
                "test_cochanged": summary.get("test_cochanged", False),
                "test_collaboration_gap": collaboration,
                "parse_degraded": rule_record.get("summary", {}).get("parse_degraded", False),
                "unanalyzed": rule_record.get("summary", {}).get("unanalyzed", []),
            },
            "files": [
                {
                    "path": item.get("new_path") or item.get("old_path"),
                    "old_path": item.get("old_path"),
                    "new_path": item.get("new_path"),
                    "status": item.get("status"),
                    "role": item.get("role"),
                    "is_python": item.get("is_python", False),
                    "additions": item.get("additions", 0),
                    "deletions": item.get("deletions", 0),
                    "binary": item.get("binary", False),
                    "hunks": item.get("hunks", []) if include_diff else [],
                    "parse_status": structure_files.get(
                        item.get("new_path") or item.get("old_path"), {}
                    ).get("parse_status", {}),
                    "parse_errors": structure_files.get(
                        item.get("new_path") or item.get("old_path"), {}
                    ).get("errors", []),
                }
                for item in files
            ],
            "findings": enriched_findings,
            "rule_outcomes": rule_outcomes,
            "rule_outcome_availability": outcome_availability,
            "limitations": [
                "分数用于排列人工复核优先级，不是缺陷概率或安全结论。",
                "当前权重和阈值是可调演示参数，尚未通过独立标注集校准。",
                "规则命中仅表示对应结构值得检查，需结合业务上下文人工确认。",
                "未发现只表示该规则已在适用上下文中完整执行；无法分析不是通过，也不表示代码安全。历史快照没有终态时，不能把缺少 Finding 当成未发现。",
            ],
        }

    def catalog(self) -> list[dict[str, Any]]:
        return [
            {
                **rule,
                "applicable_scope": RULE_SCOPES.get(rule["rule_id"], ""),
                "default_weight": DEFAULT_CONFIG["rule_weights"].get(rule["rule_id"], 0),
                "enabled_by_default": rule["rule_id"] in DEFAULT_CONFIG["enabled_rules"],
            }
            for rule in RULE_CATALOG
        ]

    def dataset(self) -> dict[str, Any]:
        analyses = [self.analyze(number, include_diff=False) for number in self.pr_numbers()]
        level_counts = Counter(item["risk_level"] for item in analyses if item["status"] == "ok")
        hit_count = sum(item["summary"]["finding_count"] > 0 for item in analyses if item["status"] == "ok")
        return {
            "schema_version": "stage06.dataset.v2",
            "counts": {
                "records": len(analyses),
                "analyzable": sum(item["status"] == "ok" for item in analyses),
                "excluded": sum(item["status"] == "excluded" for item in analyses),
                "with_findings": hit_count,
                "without_findings": sum(item["status"] == "ok" and item["summary"]["finding_count"] == 0 for item in analyses),
                "levels": dict(level_counts),
            },
            "rules": self.catalog(),
            "prs": [
                {
                    "pr_number": item["pr_number"],
                    "title": item["title"],
                    "author": item.get("author"),
                    "url": item.get("url"),
                    "status": item["status"],
                    "score": item["score"],
                    "risk_level": item["risk_level"],
                    "finding_count": item["summary"]["finding_count"],
                    "domains": item["summary"]["domains"],
                    "additions": item["summary"]["additions"],
                    "deletions": item["summary"]["deletions"],
                }
                for item in analyses
            ],
        }


def normalize_config(config: dict[str, Any] | None) -> dict[str, Any]:
    supplied = config or {}
    rule_ids = {item["rule_id"] for item in RULE_CATALOG}
    enabled_rules = supplied.get("enabled_rules", DEFAULT_CONFIG["enabled_rules"])
    if not isinstance(enabled_rules, list) or any(rule_id not in rule_ids for rule_id in enabled_rules):
        raise ValueError("enabled_rules 包含未知规则")
    weights = {**DEFAULT_CONFIG["rule_weights"], **supplied.get("rule_weights", {})}
    if any(rule_id not in rule_ids for rule_id in weights):
        raise ValueError("rule_weights 包含未知规则")
    if any(not isinstance(value, int) or not 0 <= value <= 5 for value in weights.values()):
        raise ValueError("规则权重必须是 0 到 5 的整数")
    supplied_weights = supplied.get("rule_weights") or {}
    if (
        COLLABORATION_RULE_ID in supplied_weights
        and "test_collaboration_weight" not in supplied
    ):
        collaboration_weight = supplied_weights[COLLABORATION_RULE_ID]
    else:
        collaboration_weight = supplied.get("test_collaboration_weight", DEFAULT_CONFIG["test_collaboration_weight"])
    if type(collaboration_weight) is not int or not 0 <= collaboration_weight <= 5:
        raise ValueError("测试协同权重必须是 0 到 5 的整数")
    weights[COLLABORATION_RULE_ID] = collaboration_weight
    thresholds = {**DEFAULT_CONFIG["thresholds"], **supplied.get("thresholds", {})}
    medium, high = thresholds.get("medium"), thresholds.get("high")
    if not isinstance(medium, int) or not isinstance(high, int) or not 0 <= medium < high <= 100:
        raise ValueError("风险阈值需满足 0 ≤ medium < high ≤ 100")
    return {
        "enabled_rules": list(dict.fromkeys(enabled_rules)),
        "rule_weights": weights,
        "test_collaboration_weight": collaboration_weight,
        "test_collaboration_enabled": bool(supplied.get("test_collaboration_enabled", True)),
        "thresholds": thresholds,
    }


def summed_rule_points(rule_ids: set[str] | list[str], weights: dict[str, int]) -> int:
    """Sum catalog weights except the collaboration rule, whose point is separate."""
    return sum(weights[rule_id] for rule_id in rule_ids if rule_id != COLLABORATION_RULE_ID)


def collaboration_points(config: dict[str, Any], matched: bool) -> tuple[int, int]:
    """Return the historical collaboration maximum and earned points, added once."""
    if not config.get("test_collaboration_enabled"):
        return 0, 0
    weight = config["test_collaboration_weight"]
    return weight, weight if matched else 0


def write_json_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_scored_dataset(data: DemoData, config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Build deterministic stage07 reports without changing source-stage artifacts."""
    return [data.analyze(number, config) for number in data.pr_numbers()]
