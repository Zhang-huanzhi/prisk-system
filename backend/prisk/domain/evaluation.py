"""Pure domain helpers for v1.4 formal dataset isolation, outcome aggregation, annotation grading, and preset comparison."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ..paths import project_root
from .changes import SHA_RE
from .config import (
    DEFAULT_CONFIG,
    PRESET_LEGACY_BASELINE,
    build_config_snapshot,
    normalize_audit_config,
)
from .gatekeeper import apply_gatekeeper_lift, load_rule_registry
from .rules import RULE_CATALOG, evaluate_rules, rule_domain
from .test_collaboration import COLLABORATION_RULE_ID

DEFAULT_TARGET_REPO = "netbox-community/netbox"
EXCLUSION_SCHEMA_VERSION = "prisk.eval.exclusion.v1"
ANNOTATION_SCHEMA_VERSION = "prisk.eval.annotation.v1"
EMPIRICAL_REPORT_SCHEMA_VERSION = "prisk.eval.report.v1"
PRESET_COMPARISON_SCHEMA_VERSION = "prisk.eval.preset_comparison.v1"

VALID_TRACKS = frozenset({"track_a_random", "track_b_targeted", "external_control"})
VALID_JUDGMENTS = frozenset({"hit", "false_looking_hit", "unanalyzed", "not_applicable"})
OUTCOME_STATES = ("Hit", "NotFound", "Unanalyzed")
HISTORICAL_RULE_FAMILY = "historical_baseline"


def summed_rule_points(rule_ids: set[str] | list[str], weights: dict[str, int]) -> int:
    """Sum catalog weights except the collaboration rule, whose point is separate."""
    return sum(weights[rule_id] for rule_id in rule_ids if rule_id != COLLABORATION_RULE_ID)


def collaboration_points(config: dict[str, Any], matched: bool) -> tuple[int, int]:
    """Return the historical collaboration maximum and earned points, added once."""
    if not config.get("test_collaboration_enabled"):
        return 0, 0
    weight = config["test_collaboration_weight"]
    return weight, weight if matched else 0


def normalized_file_sha256(path: Path) -> str:
    """Return deterministic LF-normalized UTF-8 SHA-256 checksum for text artifacts."""
    content = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def _portable_source_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(project_root().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def load_config_payload(
    *,
    preset: str | None = None,
    config_path: Path | None = None,
) -> dict[str, Any] | None:
    """Load and validate an explicit preset/config override payload without mutating legacy defaults."""
    if preset is None and config_path is None:
        return None
    payload: dict[str, Any] = {}
    if config_path is not None:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"配置文件必须是 JSON 对象: {config_path}")
        payload.update(raw)
    if preset is not None:
        payload["preset"] = preset
    normalize_audit_config(payload, default_preset=PRESET_LEGACY_BASELINE)
    return payload


def _extract_pr_number(record: dict[str, Any]) -> int | None:
    value = record.get("pr_number")
    if value is None:
        value = record.get("number")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _extract_repo(record: dict[str, Any], default_repo: str = DEFAULT_TARGET_REPO) -> str:
    repo = record.get("repo")
    if isinstance(repo, str) and repo.strip():
        return repo.strip()
    return default_repo


def load_dataset_records(path: Path, *, default_repo: str = DEFAULT_TARGET_REPO) -> list[dict[str, Any]]:
    """Load PR records from JSONL or manifest JSON (`records` / `selected` / `pull_requests` / `prs`)."""
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if not stripped:
        return []
    if path.suffix.lower() == ".json":
        payload = json.loads(stripped)
        if isinstance(payload, list):
            items = payload
            manifest_repo = default_repo
        elif isinstance(payload, dict):
            manifest_repo = payload.get("repo") or default_repo
            for key in ("records", "selected", "pull_requests", "prs"):
                candidate = payload.get(key)
                if isinstance(candidate, list):
                    items = candidate
                    break
            else:
                raise ValueError(f"JSON 清单缺少 PR 记录列表字段: {path}")
        else:
            raise ValueError(f"不支持的 JSON 清单格式: {path}")
        records: list[dict[str, Any]] = []
        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"{path} 第 {idx} 条记录必须是对象")
            record = dict(item)
            if not record.get("repo"):
                record["repo"] = manifest_repo
            records.append(record)
        return records

    records = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        item = json.loads(line_stripped)
        if not isinstance(item, dict):
            raise ValueError(f"{path}:{line_no} 必须是 JSON 对象")
        record = dict(item)
        if not record.get("repo"):
            record["repo"] = default_repo
        records.append(record)
    return records


def _load_pilot_exclusion_numbers(
    pilot_manifest_path: Path,
    default_repo: str = DEFAULT_TARGET_REPO,
) -> dict[str, set[int]]:
    payload = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"先导清单必须是 JSON 对象: {pilot_manifest_path}")
    manifest_repo = str(payload.get("repo") or default_repo).strip()
    by_repo: dict[str, set[int]] = defaultdict(set)

    records = load_dataset_records(pilot_manifest_path, default_repo=manifest_repo)
    for item in records:
        pr_number = _extract_pr_number(item)
        if pr_number is None:
            raise ValueError(f"先导清单存在非法 PR 编号: {item}")
        by_repo[_extract_repo(item, manifest_repo)].add(pr_number)

    declared = payload.get("exclusion_from_formal_v1_4", {}).get("numbers")
    if isinstance(declared, list):
        declared_set = {int(n) for n in declared}
        if declared_set != by_repo.get(manifest_repo, set()):
            raise ValueError(
                f"先导清单 exclusion_from_formal_v1_4.numbers 与 pull_requests 不一致: {pilot_manifest_path}"
            )
    return by_repo


def _load_exclusion_json(
    exclusion_json_path: Path,
    default_repo: str = DEFAULT_TARGET_REPO,
) -> dict[str, set[int]]:
    payload = json.loads(exclusion_json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"排除清单必须是 JSON 对象: {exclusion_json_path}")
    by_repo: dict[str, set[int]] = defaultdict(set)
    raw_by_repo = payload.get("excluded_by_repo")
    if isinstance(raw_by_repo, dict):
        for repo, numbers in raw_by_repo.items():
            if isinstance(numbers, list):
                by_repo[str(repo)].update(int(n) for n in numbers)
    raw_numbers = payload.get("excluded_pr_numbers")
    if isinstance(raw_numbers, list):
        target_repo = str(payload.get("repo") or default_repo).strip()
        by_repo[target_repo].update(int(n) for n in raw_numbers)
    return by_repo


def load_exclusion_numbers_from_sources(
    *,
    survey_path: Path | None = None,
    pilot_manifest_path: Path | None = None,
    exclusion_json_path: Path | None = None,
    default_repo: str = DEFAULT_TARGET_REPO,
) -> dict[str, Any]:
    """Load and cross-check permanent exclusion PR numbers across frozen v1.0/v1.1/v1.4 artifacts."""
    by_repo: dict[str, set[int]] = defaultdict(set)
    sources: list[dict[str, Any]] = []

    if survey_path is not None:
        survey_records = load_dataset_records(survey_path, default_repo=default_repo)
        survey_by_repo: dict[str, set[int]] = defaultdict(set)
        for item in survey_records:
            pr_number = _extract_pr_number(item)
            if pr_number is None:
                raise ValueError(f"调研集存在非法 PR 编号: {item}")
            repo = _extract_repo(item, default_repo)
            survey_by_repo[repo].add(pr_number)
            by_repo[repo].add(pr_number)
        sources.append({
            "name": "v1.0_survey",
            "path": _portable_source_path(survey_path),
            "sha256": normalized_file_sha256(survey_path),
            "count": sum(len(v) for v in survey_by_repo.values()),
        })

    if pilot_manifest_path is not None:
        pilot_by_repo = _load_pilot_exclusion_numbers(pilot_manifest_path, default_repo)
        for repo, numbers in pilot_by_repo.items():
            by_repo[repo].update(numbers)
        sources.append({
            "name": "v1.1_pilot",
            "path": _portable_source_path(pilot_manifest_path),
            "sha256": normalized_file_sha256(pilot_manifest_path),
            "count": sum(len(v) for v in pilot_by_repo.values()),
        })

    if exclusion_json_path is not None:
        json_by_repo = _load_exclusion_json(exclusion_json_path, default_repo)
        if (survey_path is not None or pilot_manifest_path is not None) and dict(json_by_repo) != dict(by_repo):
            missing = {
                repo: sorted(by_repo[repo] - json_by_repo.get(repo, set()))
                for repo in by_repo
                if by_repo[repo] - json_by_repo.get(repo, set())
            }
            extra = {
                repo: sorted(json_by_repo[repo] - by_repo.get(repo, set()))
                for repo in json_by_repo
                if json_by_repo[repo] - by_repo.get(repo, set())
            }
            raise ValueError(
                f"exclusion-list.json 与 v1.0/v1.1 源清单不一致 (missing={missing}, extra={extra})"
            )
        for repo, numbers in json_by_repo.items():
            by_repo[repo].update(numbers)

    sorted_by_repo = {repo: sorted(numbers) for repo, numbers in sorted(by_repo.items())}
    primary_numbers = sorted_by_repo.get(default_repo, [])
    return {
        "schema_version": EXCLUSION_SCHEMA_VERSION,
        "repo": default_repo,
        "count": sum(len(v) for v in sorted_by_repo.values()),
        "excluded_pr_numbers": primary_numbers,
        "excluded_by_repo": sorted_by_repo,
        "sources": sources,
    }


def build_exclusion_payload(
    *,
    survey_path: Path,
    pilot_manifest_path: Path,
    default_repo: str = DEFAULT_TARGET_REPO,
) -> dict[str, Any]:
    """Build deterministic exclusion-list.json payload from v1.0 survey and v1.1 pilot sources."""
    survey_records = load_dataset_records(survey_path, default_repo=default_repo)
    survey_numbers: dict[str, set[int]] = defaultdict(set)
    for item in survey_records:
        pr_number = _extract_pr_number(item)
        if pr_number is None:
            raise ValueError(f"调研集存在非法 PR 编号: {item}")
        survey_numbers[_extract_repo(item, default_repo)].add(pr_number)

    pilot_numbers = _load_pilot_exclusion_numbers(pilot_manifest_path, default_repo)
    cross_overlap = {
        repo: sorted(survey_numbers.get(repo, set()) & pilot_numbers.get(repo, set()))
        for repo in sorted(set(survey_numbers) | set(pilot_numbers))
        if survey_numbers.get(repo, set()) & pilot_numbers.get(repo, set())
    }
    combined = load_exclusion_numbers_from_sources(
        survey_path=survey_path,
        pilot_manifest_path=pilot_manifest_path,
        default_repo=default_repo,
    )
    combined["cross_source_overlap"] = cross_overlap
    return combined


def verify_dataset_isolation(
    records_or_path: list[dict[str, Any]] | Path,
    *,
    exclusion_numbers: set[int] | list[int] | None = None,
    exclusion_by_repo: dict[str, set[int] | list[int]] | None = None,
    default_repo: str = DEFAULT_TARGET_REPO,
    require_sha: bool = True,
    require_track: bool = False,
    raise_on_error: bool = False,
) -> dict[str, Any]:
    """Verify zero overlap against historical exclusion sets plus internal dataset integrity."""
    records = (
        load_dataset_records(records_or_path, default_repo=default_repo)
        if isinstance(records_or_path, Path)
        else list(records_or_path)
    )
    excluded_map: dict[str, set[int]] = defaultdict(set)
    if exclusion_numbers is not None:
        excluded_map[default_repo].update(int(n) for n in exclusion_numbers)
    if exclusion_by_repo is not None:
        for repo, numbers in exclusion_by_repo.items():
            excluded_map[str(repo)].update(int(n) for n in numbers)

    seen: set[tuple[str, int]] = set()
    duplicates: list[dict[str, Any]] = []
    overlaps: list[dict[str, Any]] = []
    invalid_records: list[dict[str, Any]] = []
    track_counts: Counter[str] = Counter()
    repos: set[str] = set()

    for idx, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            invalid_records.append({"index": idx, "reason": "record_not_object"})
            continue
        repo = _extract_repo(record, default_repo)
        repos.add(repo)
        pr_number = _extract_pr_number(record)
        if pr_number is None:
            invalid_records.append({"index": idx, "repo": repo, "reason": "invalid_pr_number"})
            continue

        key = (repo, pr_number)
        if key in seen:
            duplicates.append({"repo": repo, "pr_number": pr_number})
        seen.add(key)

        if pr_number in excluded_map.get(repo, set()):
            overlaps.append({"repo": repo, "pr_number": pr_number})

        if require_sha:
            base_sha = record.get("base_sha")
            head_sha = record.get("head_sha")
            merge_sha = record.get("merge_commit_sha")
            has_pair = isinstance(base_sha, str) and SHA_RE.fullmatch(base_sha) and isinstance(head_sha, str) and SHA_RE.fullmatch(head_sha)
            has_merge = isinstance(merge_sha, str) and SHA_RE.fullmatch(merge_sha)
            if not (has_pair or has_merge):
                invalid_records.append({
                    "index": idx,
                    "repo": repo,
                    "pr_number": pr_number,
                    "reason": "missing_or_invalid_sha",
                })

        track = record.get("track")
        if track is not None:
            if not isinstance(track, str) or track not in VALID_TRACKS:
                invalid_records.append({
                    "index": idx,
                    "repo": repo,
                    "pr_number": pr_number,
                    "reason": f"invalid_track:{track}",
                })
            else:
                track_counts[track] += 1
        elif require_track:
            invalid_records.append({
                "index": idx,
                "repo": repo,
                "pr_number": pr_number,
                "reason": "missing_track",
            })

    ok = not (duplicates or overlaps or invalid_records)
    summary = {
        "ok": ok,
        "total_records": len(records),
        "unique_records": len(seen),
        "repos": sorted(repos),
        "by_track": dict(sorted(track_counts.items())),
        "duplicate_prs": duplicates,
        "overlap_prs": overlaps,
        "invalid_records": invalid_records,
    }
    if raise_on_error and not ok:
        raise ValueError(
            "正式集隔离校验失败: "
            f"overlaps={len(overlaps)}, duplicates={len(duplicates)}, invalid={len(invalid_records)}"
        )
    return summary


def score_stage05_record(
    stage05_record: dict[str, Any],
    config: dict[str, Any] | None = None,
    *,
    stage04_record: dict[str, Any] | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score a single stage05 rule result deterministically with normalized config and gatekeeper rules."""
    config_value = normalize_audit_config(config, default_preset=PRESET_LEGACY_BASELINE)
    rule_record = stage05_record
    if config and ("rule_thresholds" in config) and stage04_record:
        rule_record = evaluate_rules(stage04_record, config_value)

    status = str(rule_record.get("status") or "unknown")
    pr_number = _extract_pr_number(rule_record)
    repo = _extract_repo(rule_record)
    if status != "ok":
        return {
            "repo": repo,
            "pr_number": pr_number,
            "status": status,
            "score": None,
            "risk_level": "unanalyzed",
            "finding_count": 0,
            "found_rule_ids": [],
            "gatekeeper_applied": False,
        }

    enabled = set(config_value["enabled_rules"])
    selected = [
        finding
        for finding in rule_record.get("findings", [])
        if isinstance(finding, dict) and finding.get("rule_id") in enabled
    ]
    found_rule_ids = sorted({str(finding.get("rule_id")) for finding in selected if finding.get("rule_id")})
    max_points = summed_rule_points(enabled, config_value["rule_weights"])
    earned = summed_rule_points(found_rule_ids, config_value["rule_weights"])
    collaboration = bool(rule_record.get("summary", {}).get("test_collaboration"))
    collab_max, collab_earned = collaboration_points(config_value, collaboration)
    max_points += collab_max
    earned += collab_earned

    score = round(100 * earned / max_points) if max_points else 0
    thresholds = config_value["thresholds"]
    level = "high" if score >= thresholds["high"] else "medium" if score >= thresholds["medium"] else "low"
    level, gatekeeper_basis = apply_gatekeeper_lift(
        risk_level=level,
        findings=selected,
        stage_record=stage04_record or {},
        registry=registry,
    )
    return {
        "repo": repo,
        "pr_number": pr_number,
        "status": status,
        "score": score,
        "risk_level": level,
        "finding_count": len(selected),
        "found_rule_ids": found_rule_ids,
        "gatekeeper_applied": bool(gatekeeper_basis.get("gatekeeper_lift")),
    }


def _record_key(record: dict[str, Any], default_repo: str = DEFAULT_TARGET_REPO) -> tuple[str, int | None]:
    return (_extract_repo(record, default_repo), _extract_pr_number(record))


def _summarize_rule_slice(
    records: list[dict[str, Any]],
    *,
    stage04_by_key: dict[tuple[str, int | None], dict[str, Any]],
    registry: dict[str, Any],
) -> dict[str, Any]:
    registry_by_id = {
        str(item["rule_id"]): item
        for item in registry.get("rules", [])
        if isinstance(item, dict) and item.get("rule_id")
    }
    catalog_ids = [item["rule_id"] for item in RULE_CATALOG]
    seen_extra: set[str] = set()
    for record in records:
        for finding in record.get("findings", []):
            if isinstance(finding, dict) and finding.get("rule_id"):
                seen_extra.add(str(finding["rule_id"]))
        for outcome in record.get("rule_outcomes") or []:
            if isinstance(outcome, dict) and outcome.get("rule_id"):
                seen_extra.add(str(outcome["rule_id"]))
    all_rule_ids = catalog_ids + sorted(seen_extra - set(catalog_ids))

    status_counts: Counter[str] = Counter()
    ok_prs = 0
    outcomes_available_prs = 0
    outcomes_unavailable_prs = 0
    zero_hit_ok_prs = 0
    gatekeeper_lift_prs = 0
    finding_counts: Counter[str] = Counter()
    hit_prs: Counter[str] = Counter()
    not_found_prs: Counter[str] = Counter()
    unanalyzed_prs: Counter[str] = Counter()
    unavailable_prs: Counter[str] = Counter()
    rule_reasons: dict[str, Counter[str]] = defaultdict(Counter)
    global_reasons: Counter[str] = Counter()

    for record in records:
        status = str(record.get("status") or "unknown")
        status_counts[status] += 1
        findings = [item for item in record.get("findings", []) if isinstance(item, dict)]
        for finding in findings:
            rule_id = finding.get("rule_id")
            if rule_id:
                finding_counts[str(rule_id)] += 1

        if status == "ok":
            ok_prs += 1
            if not findings:
                zero_hit_ok_prs += 1
            stage04 = stage04_by_key.get(_record_key(record), {})
            _, gatekeeper_basis = apply_gatekeeper_lift(
                risk_level="low",
                findings=findings,
                stage_record=stage04,
                registry=registry,
            )
            if gatekeeper_basis.get("gatekeeper_lift"):
                gatekeeper_lift_prs += 1

        outcomes = record.get("rule_outcomes")
        if not isinstance(outcomes, list):
            outcomes_unavailable_prs += 1
            for rule_id in all_rule_ids:
                unavailable_prs[rule_id] += 1
            continue

        outcomes_available_prs += 1
        outcome_map = {
            str(item["rule_id"]): item
            for item in outcomes
            if isinstance(item, dict) and item.get("rule_id")
        }
        for rule_id in all_rule_ids:
            outcome = outcome_map.get(rule_id)
            if outcome is None:
                unavailable_prs[rule_id] += 1
                continue
            state = outcome.get("state")
            if state == "Hit":
                hit_prs[rule_id] += 1
            elif state == "NotFound":
                not_found_prs[rule_id] += 1
            elif state == "Unanalyzed":
                unanalyzed_prs[rule_id] += 1
                reasons_seen = {
                    str(item.get("reason") or "unknown")
                    for item in outcome.get("reasons", [])
                    if isinstance(item, dict)
                }
                for reason in sorted(reasons_seen or {"unknown"}):
                    rule_reasons[rule_id][reason] += 1
                    global_reasons[reason] += 1
            else:
                unavailable_prs[rule_id] += 1

    per_rule: list[dict[str, Any]] = []
    for rule_id in all_rule_ids:
        reg_item = registry_by_id.get(rule_id)
        applicable = hit_prs[rule_id] + not_found_prs[rule_id]
        family = str(reg_item.get("rule_family")) if reg_item else rule_domain(rule_id)
        lifecycle = str(reg_item.get("lifecycle")) if reg_item else HISTORICAL_RULE_FAMILY
        per_rule.append({
            "rule_id": rule_id,
            "rule_family": family,
            "registry_lifecycle": lifecycle,
            "default_weight": DEFAULT_CONFIG["rule_weights"].get(rule_id, 0),
            "hit_prs": hit_prs[rule_id],
            "not_found_prs": not_found_prs[rule_id],
            "unanalyzed_prs": unanalyzed_prs[rule_id],
            "unavailable_prs": unavailable_prs[rule_id],
            "finding_count": finding_counts[rule_id],
            "applicable_prs": applicable,
            "coverage_rate": round(applicable / ok_prs, 4) if ok_prs else None,
            "hit_rate_over_ok": round(hit_prs[rule_id] / ok_prs, 4) if ok_prs else None,
            "hit_rate_over_applicable": round(hit_prs[rule_id] / applicable, 4) if applicable else None,
            "unanalyzed_reasons": dict(sorted(rule_reasons[rule_id].items())),
        })

    return {
        "total_prs": len(records),
        "ok_prs": ok_prs,
        "non_ok_prs": len(records) - ok_prs,
        "status_counts": dict(sorted(status_counts.items())),
        "outcomes_available_prs": outcomes_available_prs,
        "outcomes_unavailable_prs": outcomes_unavailable_prs,
        "zero_hit_ok_prs": zero_hit_ok_prs,
        "gatekeeper_lift_prs": gatekeeper_lift_prs,
        "total_findings": sum(finding_counts.values()),
        "unanalyzed_reason_counts": dict(sorted(global_reasons.items())),
        "per_rule": per_rule,
    }


def summarize_stage05_outcomes(
    stage05_records: list[dict[str, Any]],
    *,
    stage04_records: list[dict[str, Any]] | None = None,
    track_by_key: dict[tuple[str, int], str] | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate 29-rule Hit/NotFound/Unanalyzed distributions, reasons, and track slices."""
    loaded_registry = registry if registry is not None else load_rule_registry()
    stage04_by_key = {
        _record_key(record): record
        for record in (stage04_records or [])
        if isinstance(record, dict)
    }

    overall = _summarize_rule_slice(
        stage05_records,
        stage04_by_key=stage04_by_key,
        registry=loaded_registry,
    )

    by_track_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in stage05_records:
        repo = _extract_repo(record)
        pr_number = _extract_pr_number(record)
        track = record.get("track")
        if track is None and track_by_key is not None and pr_number is not None:
            track = track_by_key.get((repo, pr_number))
        if isinstance(track, str) and track in VALID_TRACKS:
            by_track_records[track].append(record)

    overall["by_track"] = {
        track: _summarize_rule_slice(
            items,
            stage04_by_key=stage04_by_key,
            registry=loaded_registry,
        )
        for track, items in sorted(by_track_records.items())
    }
    return overall


def validate_annotation_records(
    annotations: list[dict[str, Any]],
    *,
    default_repo: str = DEFAULT_TARGET_REPO,
) -> list[dict[str, Any]]:
    """Validate manual verification annotation records against prisk.eval.annotation.v1."""
    normalized: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, int]] = set()
    for idx, item in enumerate(annotations, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"标注第 {idx} 行必须是 JSON 对象")
        schema_version = item.get("schema_version")
        if schema_version is not None and schema_version != ANNOTATION_SCHEMA_VERSION:
            raise ValueError(f"标注第 {idx} 行 schema_version 非法: {schema_version}")
        repo = _extract_repo(item, default_repo)
        pr_number = _extract_pr_number(item)
        if pr_number is None:
            raise ValueError(f"标注第 {idx} 行 pr_number 非法: {item.get('pr_number')}")
        key = (repo, pr_number)
        if key in seen_keys:
            raise ValueError(f"标注中存在重复 PR: {repo}#{pr_number}")
        seen_keys.add(key)

        track = item.get("track")
        if not isinstance(track, str) or track not in VALID_TRACKS:
            raise ValueError(f"标注 {repo}#{pr_number} 缺少或非法 track: {track}")

        review_minutes = item.get("review_minutes")
        if isinstance(review_minutes, bool) or not isinstance(review_minutes, (int, float)) or review_minutes < 0:
            raise ValueError(f"标注 {repo}#{pr_number} review_minutes 必须为非负数: {review_minutes}")

        judgments_raw = item.get("finding_judgments")
        if not isinstance(judgments_raw, list):
            raise ValueError(f"标注 {repo}#{pr_number} finding_judgments 必须是列表")
        judgments: list[dict[str, Any]] = []
        for j_idx, entry in enumerate(judgments_raw, start=1):
            if not isinstance(entry, dict):
                raise ValueError(f"标注 {repo}#{pr_number} 第 {j_idx} 条 judgment 必须是对象")
            rule_id = entry.get("rule_id")
            judgment = entry.get("judgment")
            if not isinstance(rule_id, str) or not rule_id.strip():
                raise ValueError(f"标注 {repo}#{pr_number} 第 {j_idx} 条缺少 rule_id")
            if not isinstance(judgment, str) or judgment not in VALID_JUDGMENTS:
                raise ValueError(
                    f"标注 {repo}#{pr_number} 第 {j_idx} 条 judgment 非法: {judgment}"
                )
            judgments.append({
                "rule_id": rule_id.strip(),
                "judgment": judgment,
                "path": entry.get("path"),
                "start_line": entry.get("start_line"),
                "end_line": entry.get("end_line"),
                "reason_note": entry.get("reason_note"),
                "noise_pattern": entry.get("noise_pattern"),
            })
        normalized.append({
            "schema_version": ANNOTATION_SCHEMA_VERSION,
            "repo": repo,
            "pr_number": pr_number,
            "track": track,
            "review_minutes": float(review_minutes),
            "finding_judgments": judgments,
        })
    return normalized


def _summarize_annotation_slice(
    records: list[dict[str, Any]],
    *,
    min_noise_samples: int,
    noise_precision_threshold: float,
) -> dict[str, Any]:
    durations = [float(item["review_minutes"]) for item in records]
    totals: Counter[str] = Counter()
    rule_judgments: dict[str, Counter[str]] = defaultdict(Counter)
    rule_prs_hit: dict[str, set[tuple[str, int]]] = defaultdict(set)
    rule_prs_fp: dict[str, set[tuple[str, int]]] = defaultdict(set)
    noise_patterns: dict[str, Counter[str]] = defaultdict(Counter)

    for item in records:
        pr_key = (item["repo"], item["pr_number"])
        for entry in item["finding_judgments"]:
            rule_id = entry["rule_id"]
            judgment = entry["judgment"]
            totals[judgment] += 1
            rule_judgments[rule_id][judgment] += 1
            if judgment == "hit":
                rule_prs_hit[rule_id].add(pr_key)
            elif judgment == "false_looking_hit":
                rule_prs_fp[rule_id].add(pr_key)
                if entry.get("noise_pattern"):
                    noise_patterns[rule_id][str(entry["noise_pattern"])] += 1

    total_tp = totals["hit"]
    total_fp = totals["false_looking_hit"]
    denom = total_tp + total_fp

    per_rule: list[dict[str, Any]] = []
    high_noise_candidates: list[dict[str, Any]] = []
    for rule_id in sorted(rule_judgments):
        counts = rule_judgments[rule_id]
        tp = counts["hit"]
        fp = counts["false_looking_hit"]
        rule_denom = tp + fp
        precision = round(tp / rule_denom, 4) if rule_denom else None
        noise_rate = round(fp / rule_denom, 4) if rule_denom else None
        is_high_noise = (
            rule_denom >= min_noise_samples
            and precision is not None
            and precision < noise_precision_threshold
        )
        row = {
            "rule_id": rule_id,
            "tp_hit": tp,
            "fp_noise": fp,
            "unanalyzed_judgments": counts["unanalyzed"],
            "not_applicable_judgments": counts["not_applicable"],
            "empirical_precision": precision,
            "noise_rate": noise_rate,
            "pr_tp_count": len(rule_prs_hit[rule_id]),
            "pr_fp_only_count": len(rule_prs_fp[rule_id] - rule_prs_hit[rule_id]),
            "high_noise_candidate": is_high_noise,
            "noise_patterns": dict(sorted(noise_patterns[rule_id].items())),
        }
        per_rule.append(row)
        if is_high_noise:
            high_noise_candidates.append(row)

    return {
        "annotated_prs": len(records),
        "review_minutes": {
            "total": round(sum(durations), 2),
            "mean": round(statistics.mean(durations), 2) if durations else None,
            "median": round(statistics.median(durations), 2) if durations else None,
            "min": round(min(durations), 2) if durations else None,
            "max": round(max(durations), 2) if durations else None,
        },
        "finding_totals": {
            "hit": total_tp,
            "false_looking_hit": total_fp,
            "unanalyzed": totals["unanalyzed"],
            "not_applicable": totals["not_applicable"],
            "empirical_precision": round(total_tp / denom, 4) if denom else None,
            "noise_rate": round(total_fp / denom, 4) if denom else None,
        },
        "high_noise_candidates": high_noise_candidates,
        "per_rule": per_rule,
    }


def evaluate_annotations(
    annotations: list[dict[str, Any]],
    *,
    default_repo: str = DEFAULT_TARGET_REPO,
    min_noise_samples: int = 3,
    noise_precision_threshold: float = 0.5,
) -> dict[str, Any]:
    """Compute per-rule precision, noise rates, high-noise candidates, and review effort across annotations."""
    normalized = validate_annotation_records(annotations, default_repo=default_repo)
    overall = _summarize_annotation_slice(
        normalized,
        min_noise_samples=min_noise_samples,
        noise_precision_threshold=noise_precision_threshold,
    )
    by_track_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in normalized:
        by_track_records[item["track"]].append(item)
    overall["by_track"] = {
        track: _summarize_annotation_slice(
            items,
            min_noise_samples=min_noise_samples,
            noise_precision_threshold=noise_precision_threshold,
        )
        for track, items in sorted(by_track_records.items())
    }
    return overall


def _percentile(sorted_values: list[int], q: float) -> float | None:
    if not sorted_values:
        return None
    idx = min(len(sorted_values) - 1, max(0, math.ceil(q * len(sorted_values)) - 1))
    return float(sorted_values[idx])


def compare_preset_runs(
    stage05_records: list[dict[str, Any]],
    config_specs: list[tuple[str, dict[str, Any]]],
    *,
    stage04_records: list[dict[str, Any]] | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score the same stage05 dataset across multiple preset/custom configs with snapshot provenance."""
    loaded_registry = registry if registry is not None else load_rule_registry()
    stage04_by_key = {
        _record_key(record): record
        for record in (stage04_records or [])
        if isinstance(record, dict)
    }

    runs: list[dict[str, Any]] = []
    for label, raw_config in config_specs:
        normalized = normalize_audit_config(raw_config, default_preset=PRESET_LEGACY_BASELINE)
        snapshot = build_config_snapshot(raw_config or normalized, default_preset=PRESET_LEGACY_BASELINE)
        scored = [
            score_stage05_record(
                record,
                raw_config,
                stage04_record=stage04_by_key.get(_record_key(record)),
                registry=loaded_registry,
            )
            for record in stage05_records
        ]
        ok_items = [item for item in scored if item["status"] == "ok" and item["score"] is not None]
        scores = sorted(int(item["score"]) for item in ok_items)
        levels = Counter(item["risk_level"] for item in ok_items)
        total_findings = sum(int(item["finding_count"]) for item in ok_items)
        runs.append({
            "label": label,
            "preset": snapshot["preset"],
            "config_digest": snapshot["config_digest"],
            "config_snapshot": snapshot,
            "total_prs": len(scored),
            "ok_prs": len(ok_items),
            "mean_score": round(statistics.mean(scores), 2) if scores else None,
            "median_score": round(statistics.median(scores), 2) if scores else None,
            "p90_score": _percentile(scores, 0.90),
            "min_score": min(scores) if scores else None,
            "max_score": max(scores) if scores else None,
            "risk_level_counts": {level: levels.get(level, 0) for level in ("low", "medium", "high")},
            "gatekeeper_lift_prs": sum(1 for item in ok_items if item["gatekeeper_applied"]),
            "zero_finding_prs": sum(1 for item in ok_items if item["finding_count"] == 0),
            "mean_findings_per_pr": round(total_findings / len(ok_items), 2) if ok_items else None,
        })

    return {
        "schema_version": PRESET_COMPARISON_SCHEMA_VERSION,
        "dataset_prs": len(stage05_records),
        "runs": runs,
    }


def _fmt_rate(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:.1f}%"


def render_empirical_report_markdown(report: dict[str, Any]) -> str:
    """Render an empirical aggregation report and optional annotations/presets into Markdown tables."""
    outcomes = report["outcomes"]
    lines = [
        "# Prisk v1.4 实证评估汇总报告",
        "",
        "## 1. 数据集概览",
        "",
        f"- 总 PR 数：`{outcomes['total_prs']}`（`status == \"ok\"`：`{outcomes['ok_prs']}`，非 ok：`{outcomes['non_ok_prs']}`）",
        f"- 含完整 `rule_outcomes`：`{outcomes['outcomes_available_prs']}`；缺失回退：`{outcomes['outcomes_unavailable_prs']}`",
        f"- 零命中（`ok` 且 `findings == 0`）PR 数：`{outcomes['zero_hit_ok_prs']}`",
        f"- Gatekeeper 抬升触发 PR 数：`{outcomes['gatekeeper_lift_prs']}`",
        f"- 总 Findings 数：`{outcomes['total_findings']}`",
        "",
    ]

    if outcomes.get("unanalyzed_reason_counts"):
        lines.extend([
            "## 2. Unanalyzed 原因分布",
            "",
            "| Reason | 规则×PR 次数 |",
            "| :--- | :---: |",
        ])
        for reason, count in outcomes["unanalyzed_reason_counts"].items():
            lines.append(f"| `{reason}` | {count} |")
        lines.append("")

    lines.extend([
        "## 3. 29 条规则三态命中与覆盖分布",
        "",
        "| Rule ID | 族 (`family`) | 生命周期 | 默认权重 | Hit PR | NotFound PR | Unanalyzed PR | 适用覆盖率 | 命中率 (`ok`) | 命中率 (`applicable`) | Findings |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ])
    for row in outcomes["per_rule"]:
        lines.append(
            f"| `{row['rule_id']}` | `{row['rule_family']}` | `{row['registry_lifecycle']}` | "
            f"{row['default_weight']} | {row['hit_prs']} | {row['not_found_prs']} | "
            f"{row['unanalyzed_prs']} | {_fmt_rate(row['coverage_rate'])} | "
            f"{_fmt_rate(row['hit_rate_over_ok'])} | {_fmt_rate(row['hit_rate_over_applicable'])} | {row['finding_count']} |"
        )
    lines.append("")

    annotations = report.get("annotations")
    if annotations:
        effort = annotations["review_minutes"]
        totals = annotations["finding_totals"]
        lines.extend([
            "## 4. 人工核验标注精度与耗时",
            "",
            f"- 已核验 PR 数：`{annotations['annotated_prs']}`，总耗时：`{effort['total']} min`（均值 `{effort['mean']} min`，中位数 `{effort['median']} min`）",
            f"- Findings 核验：`hit={totals['hit']}`，`false_looking_hit={totals['false_looking_hit']}`，综合 Precision：`{_fmt_rate(totals['empirical_precision'])}`",
            "",
            "| Rule ID | Hit (TP) | Noise (FP) | Unanalyzed | Not Applicable | Empirical Precision | 高噪候选 |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ])
        for row in annotations["per_rule"]:
            flag = "YES" if row["high_noise_candidate"] else "no"
            lines.append(
                f"| `{row['rule_id']}` | {row['tp_hit']} | {row['fp_noise']} | "
                f"{row['unanalyzed_judgments']} | {row['not_applicable_judgments']} | "
                f"{_fmt_rate(row['empirical_precision'])} | {flag} |"
            )
        lines.append("")

    preset_comparison = report.get("preset_comparison")
    if preset_comparison and preset_comparison.get("runs"):
        lines.extend([
            "## 5. 多配置预设对比（含 `config.snapshot.v1` 指纹）",
            "",
            "| Label | Preset | Digest (`config_digest`) | OK PRs | Mean | Median | P90 | Low / Med / High | Gatekeeper Lift |",
            "| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ])
        for run in preset_comparison["runs"]:
            lv = run["risk_level_counts"]
            lines.append(
                f"| `{run['label']}` | `{run['preset']}` | `{run['config_digest'][:12]}` | "
                f"{run['ok_prs']} | {run['mean_score']} | {run['median_score']} | {run['p90_score']} | "
                f"{lv['low']} / {lv['medium']} / {lv['high']} | {run['gatekeeper_lift_prs']} |"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
