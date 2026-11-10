"""prisk.domain.report_export: 可复现审查报告导出与配置快照封存渲染。"""

from __future__ import annotations

import json
from typing import Any

from .config import build_config_snapshot


_RISK_LABELS: dict[str, str] = {
    "high": "优先复核",
    "medium": "建议复核",
    "low": "常规",
}

_OUTCOME_LABELS: dict[str, str] = {
    "Hit": "命中",
    "NotFound": "未发现",
    "Unanalyzed": "无法分析",
}

_REASON_LABELS: dict[str, str] = {
    "path_classification_unavailable": "路径无法分类",
    "diff_stats_unavailable": "差异统计不完整",
    "unsupported_stage04_details": "结构细节不足",
    "syntax_error": "语法解析失败",
    "head_parse_failed": "头版本解析失败",
    "git_show_error": "源码无法读取",
    "missing_framework_context": "缺少该规则的框架或路径上下文",
    "context_not_established": "没有可完成判断的对象",
    "missing_file_change_channel": "没有文件变更通道",
    "prior_stage_unavailable": "前置阶段不可用",
}


def _outcome_note(outcome: dict[str, Any]) -> str:
    if outcome.get("state") != "Unanalyzed":
        return ""
    parts: list[str] = []
    for item in outcome.get("reasons") or []:
        reason_code = str(item.get("reason") or "")
        reason_text = _REASON_LABELS.get(reason_code, reason_code)
        objects = [
            f"{obj.get('path') or '本次变更'}:{obj.get('node_id')}"
            if obj.get("node_id")
            else str(obj.get("path") or "本次变更")
            for obj in (item.get("objects") or [])
        ]
        objects = [o for o in objects if o]
        shown = "、".join(objects[:3])
        extra = f" 等 {len(objects)} 个对象" if len(objects) > 3 else ""
        parts.append(f"{reason_text}{f'（{shown}{extra}）' if shown else ''}")
    return "；".join(parts)


def render_markdown_report(report: dict[str, Any]) -> str:
    """将阶段 07/08 审查报告渲染为固化完整运行配置快照的 Markdown 文本。"""
    score_basis = report.get("score_basis") or {}
    raw_config = score_basis.get("configuration")
    snapshot = report.get("config_snapshot") or build_config_snapshot(raw_config)
    summary = report.get("summary") or {}
    meta = report.get("snapshot_meta") or {}

    pr_number = report.get("pr_number")
    heading_target = (
        f"PR #{pr_number}"
        if pr_number
        else f"{report.get('base_ref', 'base')} → {report.get('head_ref', 'head')}"
    )
    risk_level = str(report.get("risk_level") or "low")
    risk_label = _RISK_LABELS.get(risk_level, risk_level)

    gatekeeper_lift = bool(score_basis.get("gatekeeper_lift"))
    gatekeeper_rules = sorted(
        set(score_basis.get("gatekeeper_finding_rule_ids") or [])
        | set(score_basis.get("gatekeeper_structural_rule_ids") or [])
    )
    gatekeeper_line = (
        f"已触发（强制抬升为优先复核，触发规则：{', '.join(gatekeeper_rules)}）"
        if gatekeeper_lift
        else "未触发"
    )

    outcomes_recorded = (
        report.get("rule_outcome_availability") == "recorded"
        and isinstance(report.get("rule_outcomes"), list)
    )
    outcome_by_rule: dict[str, dict[str, Any]] = {}
    if outcomes_recorded:
        for item in report.get("rule_outcomes") or []:
            if isinstance(item, dict) and item.get("rule_id"):
                outcome_by_rule[str(item["rule_id"])] = item

    lines: list[str] = [
        f"# {heading_target} 代码变更复核",
        "",
        f"- 标题：{report.get('title') or heading_target}",
        f"- 仓库：{report.get('repo') or '未知'}",
        f"- 作者：{report.get('author') or '未知'}",
        f"- 提交快照：base `{str(report.get('base_sha') or '')[:7] or '—'}` → head `{str(report.get('head_sha') or '')[:7] or '—'}`",
        f"- 复核优先级：{report.get('score', 0)}/100（{risk_label}，不是缺陷概率）",
        f"- 计分依据：{score_basis.get('earned_points', 0)} / {score_basis.get('maximum_points', 0)}（已得权重 / 可得权重）",
        f"- 一票抬升（Gatekeeper）：{gatekeeper_line}",
        f"- 变更规模：{summary.get('files_changed', 0)} 个文件，+{summary.get('additions', 0)} / -{summary.get('deletions', 0)}",
    ]
    if meta:
        lines.append(
            f"- 执行层级：`{meta.get('rerun_tier', 'full_run')}`（cache_hit={bool(meta.get('cache_hit'))}）"
        )

    # 运行配置快照（强制封存）
    thresholds = snapshot.get("thresholds") or {"medium": 30, "high": 65}
    rule_thresholds = snapshot.get("rule_thresholds") or {}
    deep_depth = (rule_thresholds.get("code.deep_control_flow") or {}).get("max_depth", 4)
    secret_len = (rule_thresholds.get("code.hardcoded_secret") or {}).get("min_length", 8)
    disabled_rules = snapshot.get("disabled_rules") or []

    lines.extend([
        "",
        "## 运行配置快照（可复现封存）",
        "",
        f"- 配置 Schema：`{snapshot.get('schema_version', 'config.snapshot.v1')}`",
        f"- 配置指纹（SHA-256）：`{snapshot.get('config_digest', '')}`",
        f"- 场景预设：`{snapshot.get('preset', 'legacy_baseline')}`（{snapshot.get('preset_name', '历史兼容基线')}，自定义覆盖：`{bool(snapshot.get('customized'))}`）",
        f"- 等级分段阈值：建议复核 `medium >= {thresholds.get('medium', 30)}`，优先复核 `high >= {thresholds.get('high', 65)}`",
        f"- 规则内部判定阈值：`code.deep_control_flow.max_depth = {deep_depth}`，`code.hardcoded_secret.min_length = {secret_len}`",
        f"- 测试协同配置：`enabled = {bool(snapshot.get('test_collaboration_enabled', True))}`，`weight = {snapshot.get('test_collaboration_weight', 1)}`",
        f"- 启用规则数：{snapshot.get('enabled_rule_count', len(snapshot.get('enabled_rules', [])))} / 29",
        f"- 已禁用规则：{', '.join(f'`{r}`' for r in disabled_rules) if disabled_rules else '无（全部 29 条规则均已启用）'}",
        "",
        "### 启用规则与权重明细",
        "",
        "| 规则 ID | 启发式权重 | 本次终态 |",
        "| :--- | :---: | :--- |",
    ])
    rule_weights = snapshot.get("rule_weights") or {}
    for rule_id in snapshot.get("enabled_rules") or []:
        weight = rule_weights.get(rule_id, 0)
        if outcomes_recorded and rule_id in outcome_by_rule:
            state_str = _OUTCOME_LABELS.get(str(outcome_by_rule[rule_id].get("state")), "未知")
        else:
            state_str = "终态未记录"
        lines.append(f"| `{rule_id}` | {weight} | {state_str} |")

    repro_payload = {
        "preset": snapshot.get("preset", "legacy_baseline"),
        "config_digest": snapshot.get("config_digest", ""),
        "enabled_rules": snapshot.get("enabled_rules", []),
        "rule_weights": rule_weights,
        "test_collaboration_enabled": snapshot.get("test_collaboration_enabled", True),
        "test_collaboration_weight": snapshot.get("test_collaboration_weight", 1),
        "thresholds": thresholds,
        "rule_thresholds": rule_thresholds,
    }
    lines.extend([
        "",
        "### 可复现配置载荷",
        "",
        "```json",
        json.dumps(repro_payload, ensure_ascii=False, indent=2),
        "```",
    ])

    # 规则终态
    lines.extend(["", "## 规则终态"])
    if outcomes_recorded:
        for outcome in report.get("rule_outcomes") or []:
            rule_id = outcome.get("rule_id")
            state = _OUTCOME_LABELS.get(str(outcome.get("state")), str(outcome.get("state")))
            note = _outcome_note(outcome)
            lines.append(f"- {rule_id}：{state}{f'。{note}' if note else ''}")
        lines.extend(["", "未发现不是安全结论。无法分析不是通过。"])
    else:
        lines.append("- 这次结果没有规则终态记录。没有 Finding 不能解释为未发现或已通过。")

    # 规则线索
    lines.extend(["", "## 规则线索"])
    for finding in report.get("findings") or []:
        lines.extend([
            "",
            f"### {finding.get('rule_id')}",
            f"- {finding.get('message')}",
            f"- 复核建议：{finding.get('suggested_action')}",
        ])
        for item in finding.get("evidence") or []:
            ev_lines = ",".join(str(x) for x in (item.get("lines") or []))
            qual = item.get("qualified_name") or item.get("node_id") or ""
            lines.append(
                f"- {item.get('path')}:{ev_lines} · {item.get('node_kind')} · {item.get('structural_change_type')} · {qual}"
            )

    # 说明
    lines.extend(["", "## 说明"])
    for item in report.get("limitations") or []:
        lines.append(f"- {item}")

    return "\n".join(lines)
