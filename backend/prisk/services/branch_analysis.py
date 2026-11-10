"""Dynamic branch audit pipeline built on stages 03-07 primitives."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..domain.changes import build_change_object, classify_path
from .project_service import ProjectError
from ..domain.rules import evaluate_rules, rule_domain
from ..domain.structure import extract_changed_structures
from .demo_service import collaboration_points, normalize_config, summed_rule_points
from .analysis_cache import get_analysis_cache
from ..domain.gatekeeper import apply_gatekeeper_lift


def _resolve_ref(repo: Path, ref: str) -> str:
    import subprocess
    value = ref.strip()
    if not value or value.startswith("-"):
        raise ProjectError("invalid_ref", "分支 ref 不能为空")
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{value}^{{commit}}"],
        cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    if result.returncode:
        raise ProjectError("ref_not_found", f"找不到分支或提交: {value}")
    return result.stdout.strip()


def _score(
    rule_record: dict[str, Any],
    config: dict[str, Any],
    *,
    stage_record: dict[str, Any] | None = None,
) -> tuple[int, str, dict[str, Any]]:
    enabled = set(config["enabled_rules"])
    findings = [item for item in rule_record.get("findings", []) if item.get("rule_id") in enabled]
    matched = {item.get("rule_id") for item in findings}
    maximum = summed_rule_points(enabled, config["rule_weights"])
    earned = summed_rule_points(matched, config["rule_weights"])
    collaboration = bool(rule_record.get("summary", {}).get("test_collaboration"))
    collaboration_maximum, collaboration_earned = collaboration_points(config, collaboration)
    maximum += collaboration_maximum
    earned += collaboration_earned
    score = round(100 * earned / maximum) if maximum else 0
    level = "high" if score >= config["thresholds"]["high"] else "medium" if score >= config["thresholds"]["medium"] else "low"
    level, gatekeeper_basis = apply_gatekeeper_lift(
        risk_level=level,
        findings=findings,
        stage_record=stage_record or rule_record,
    )
    return score, level, {
        "earned_points": earned,
        "maximum_points": maximum,
        "matched_rule_ids": sorted(matched),
        "test_collaboration": collaboration,
        "configuration": config,
        **gatekeeper_basis,
    }


def analyze_branches(
    repo_path: Path,
    base_ref: str,
    head_ref: str,
    *,
    project: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    repo = repo_path.expanduser().resolve()
    base_sha = _resolve_ref(repo, base_ref)
    head_sha = _resolve_ref(repo, head_ref)
    if base_sha == head_sha:
        raise ProjectError("same_ref", "base 和 head 指向同一个提交")

    cache = get_analysis_cache()
    cache_key = f"{repo}:{base_sha}..{head_sha}"
    config_value = normalize_config(config)

    cached = None if refresh else cache.get(cache_key)
    diff_reused = False
    ast_reused = False
    rules_reused = False

    if cached is None:
        rerun_tier = "full_run"
        record = {
            "repo": project.get("name", repo.name) if project else repo.name,
            "pr_number": 0,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "source": {"base_ref": base_ref, "head_ref": head_ref},
        }
        change = build_change_object(record, repo)
        if change.get("status") != "ok":
            errors = change.get("errors", [])
            message = errors[0].get("message", "无法读取分支差异") if errors else "无法读取分支差异"
            raise ProjectError("diff_error", message)
        for file_item in change.get("files", []):
            path = str(file_item.get("new_path") or file_item.get("old_path") or "")
            role = classify_path(path)
            if role == "other" and file_item.get("is_python"):
                file_item["role"] = "business"
        counts = {role: sum(item.get("role") == role for item in change["files"]) for role in ("business", "test", "other")}
        change["summary"].update({
            "business_files": counts["business"], "test_files": counts["test"], "other_files": counts["other"],
            "business_changed": counts["business"] > 0, "test_changed": counts["test"] > 0,
            "test_cochanged": counts["business"] > 0 and counts["test"] > 0,
        })
        structure = extract_changed_structures(change, repo)
        rules = evaluate_rules(structure, config_value)
        cache.put(cache_key, change, structure, rules, config_value)
    else:
        diff_reused = True
        ast_reused = True
        change = cached.change
        structure = cached.structure

        rules_config_changed = (
            set(config_value.get("enabled_rules", [])) != set(cached.config.get("enabled_rules", []))
            or config_value.get("rule_thresholds") != cached.config.get("rule_thresholds")
        )

        if rules_config_changed:
            rerun_tier = "stage05_rules_rerun"
            cache.record_tier1()
            rules = evaluate_rules(structure, config_value)
            cache.update_rules(cache_key, rules, config_value)
        else:
            rerun_tier = "stage07_rescore_only"
            cache.record_tier2()
            rules_reused = True
            rules = cached.rule_record
    score, level, score_basis = _score(rules, config_value, stage_record=structure)
    nodes = {node.get("node_id"): node for item in structure.get("files", []) for node in item.get("nodes", []) if node.get("node_id")}
    findings = []
    for finding in rules.get("findings", []):
        evidence = []
        for item in finding.get("evidence", []):
            node = nodes.get(item.get("node_id"), {})
            node_source = node.get("source_segment")
            source_segment = node_source if node_source is not None else item.get("source_segment")
            evidence.append({
                **item,
                "source_segment": source_segment,
                "qualified_name": node.get("qualified_name") or item.get("qualified_name"),
                "node_start_line": node.get("start_line", item.get("start_line")),
                "node_end_line": node.get("end_line", item.get("end_line")),
            })
        findings.append({**finding, "evidence": evidence})
    snapshot_meta = {
        "cache_hit": cached is not None,
        "rerun_tier": rerun_tier,
        "diff_reused": diff_reused,
        "ast_reused": ast_reused,
        "rules_reused": rules_reused,
        "cache_key": cache_key,
    }
    return {
        "schema_version": "stage08.branch-report.v1",
        "status": "ok",
        "snapshot_meta": snapshot_meta,
        "project": project or {"name": repo.name, "path": str(repo)},
        "base_ref": base_ref,
        "head_ref": head_ref,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "merge_base_sha": change.get("merge_base_sha"),
        "diff_mode": "three_dot",
        "score": score,
        "risk_level": level,
        "score_basis": score_basis,
        "summary": {
            **change.get("summary", {}),
            "finding_count": len(findings),
            "domains": sorted({rule_domain(item["rule_id"]) for item in findings if item.get("rule_id")}),
            "scenes": sorted({item.get("scene") for item in findings if item.get("scene")}),
            "test_collaboration_gap": bool(rules.get("summary", {}).get("test_collaboration")),
            "unanalyzed": rules.get("summary", {}).get("unanalyzed", []),
            "parse_degraded": structure.get("summary", {}).get("files_degraded", 0) > 0,
            "structures": structure.get("summary", {}),
        },
        "files": [
            {
                **item,
                "path": item.get("new_path") or item.get("old_path"),
                "parse_status": next((s.get("parse_status", {}) for s in structure.get("files", []) if s.get("path") == (item.get("new_path") or item.get("old_path"))), {}),
                "parse_errors": next((s.get("errors", []) for s in structure.get("files", []) if s.get("path") == (item.get("new_path") or item.get("old_path"))), []),
            }
            for item in change.get("files", [])
        ],
        "findings": findings,
        "rule_outcomes": rules.get("rule_outcomes", []),
        "rule_outcome_availability": "recorded",
        "limitations": [
            "分支分析只读取已提交的 base/head 快照，不纳入未提交工作区。",
            "评分用于排列人工复核优先级，不是缺陷概率或安全结论。",
            "规则命中仅表示对应结构值得检查，需结合业务上下文人工确认。",
            "未发现只表示该规则已在适用上下文中完整执行；无法分析不是通过，也不表示代码安全。",
        ],
        "errors": [],
    }
