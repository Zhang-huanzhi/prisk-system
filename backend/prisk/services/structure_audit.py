"""阶段 04 结构对象的可复核质量审计。"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from ..domain.changes import load_records


ALLOWED_NODE_KINDS = {
    "module",
    "class",
    "function",
    "async_function",
    "decorator",
    "field",
    "call",
    "except_handler",
}
ALLOWED_CHANGE_TYPES = {
    "node_added",
    "node_removed",
    "function_touched",
    "signature_changed",
    "class_touched",
    "decorator_added",
    "decorator_removed",
    "field_added",
    "field_removed",
    "field_modified",
    "call_touched",
    "exception_handler_changed",
}
SCENES = ("api", "auth", "data_transaction", "config_exception")


def _scene_candidates(survey_path: Path) -> dict[int, set[str]]:
    result: dict[int, set[str]] = {}
    for record in load_records(survey_path):
        number = record.get("pr_number")
        scenes = record.get("change_facts", {}).get("scenes", {})
        if not isinstance(number, int) or not isinstance(scenes, dict):
            continue
        result[number] = {
            scene for scene in SCENES if isinstance(scenes.get(scene), dict) and scenes[scene].get("hit")
        }
    return result


def select_audit_prs(stage04_records: list[dict[str, Any]], survey_path: Path, minimum: int = 12) -> list[int]:
    scenes_by_pr = _scene_candidates(survey_path)
    records_by_pr = {
        int(record["pr_number"]): record
        for record in stage04_records
        if record.get("status") == "ok" and record.get("pr_number") is not None
    }
    selected: list[int] = []
    for scene in SCENES:
        candidates = sorted(number for number, scenes in scenes_by_pr.items() if scene in scenes and number in records_by_pr)
        selected.extend(number for number in candidates[:3] if number not in selected)
    for record in sorted(records_by_pr.values(), key=lambda item: int(item.get("pr_number") or 0)):
        number = int(record["pr_number"])
        if number not in selected and len(selected) < minimum:
            selected.append(number)
    return selected


def _changed_lines(file_item: dict[str, Any]) -> set[int]:
    lines: set[int] = set()
    for hunk in file_item.get("hunks", []):
        for line in hunk.get("lines", []):
            for key in ("old_line", "new_line"):
                if line.get(key) is not None:
                    lines.add(int(line[key]))
    return lines


def _node_key(node: dict[str, Any]) -> tuple[Any, ...]:
    return (
        node.get("side"),
        node.get("kind"),
        node.get("match_key"),
        tuple(node.get("changed_lines", [])),
    )


def _change_key(change: dict[str, Any]) -> tuple[Any, ...]:
    return (
        change.get("type"),
        change.get("kind"),
        change.get("match_key"),
        tuple(change.get("evidence_lines", [])),
    )


def audit_structure_records(
    stage04_records: list[dict[str, Any]],
    stage03_records: list[dict[str, Any]],
    survey_path: Path,
    minimum_prs: int = 12,
    changes_per_pr: int = 5,
) -> dict[str, Any]:
    selected_prs = select_audit_prs(stage04_records, survey_path, minimum_prs)
    selected_set = set(selected_prs)
    selected_records = [record for record in stage04_records if record.get("pr_number") in selected_set]
    stage03_by_pr = {
        int(record["pr_number"]): record
        for record in stage03_records
        if record.get("status") == "ok" and record.get("pr_number") is not None
    }

    totals = Counter()
    duplicate_keys: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []
    degraded_errors = 0
    for record in selected_records:
        source_record = stage03_by_pr.get(int(record["pr_number"]), {})
        source_files = {}
        for item in source_record.get("files", []):
            for source_path in (item.get("new_path"), item.get("old_path")):
                if source_path:
                    source_files[source_path] = item
        changes_seen = 0
        for file_item in record.get("files", []):
            path = file_item.get("path") or file_item.get("new_path") or file_item.get("old_path") or ""
            if file_item.get("role") not in {"business", "test"} or not path.lower().endswith(".py"):
                continue
            totals["python_files"] += 1
            source_file = source_files.get(path)
            if source_file is not None:
                totals["file_path_checks"] += 1
            else:
                totals["file_path_failures"] += 1
            file_lines = _changed_lines(source_file) if source_file is not None else set()
            parse_status = file_item.get("parse_status", {})
            if parse_status.get("base") in {"ok", "absent"} and parse_status.get("head") in {"ok", "absent"}:
                totals["parsed_files"] += 1
            elif "failed" in parse_status.values():
                totals["degraded_files"] += 1
                errors = [error for error in file_item.get("errors", []) if error.get("code") in {"syntax_error", "git_show_error"}]
                degraded_errors += sum(1 for error in errors if error.get("line") and error.get("column"))
                totals["degraded_error_records"] += len(errors)
            nodes = file_item.get("nodes", [])
            node_keys = Counter(_node_key(node) for node in nodes)
            for key, count in node_keys.items():
                if count > 1:
                    totals["duplicate_nodes"] += count - 1
                    duplicate_keys.append({"pr_number": record.get("pr_number"), "path": file_item.get("path"), "key": key, "count": count})
            for node in nodes:
                totals["nodes"] += 1
                if node.get("kind") in ALLOWED_NODE_KINDS:
                    totals["valid_node_kind"] += 1
                if node.get("kind") in ALLOWED_NODE_KINDS and node.get("qualified_name"):
                    totals["qualified_node"] += 1
                if node.get("qualified_name"):
                    totals["qualified_name"] += 1
                node_lines = set(node.get("changed_lines", []))
                if node_lines and node_lines & file_lines:
                    totals["node_line_mapping"] += 1
                else:
                    totals["node_line_mapping_failed"] += 1
            for change in file_item.get("structural_changes", []):
                totals["structural_changes"] += 1
                totals["call_touched_changes"] += change.get("type") == "call_touched"
                duplicate_change_key = (record.get("pr_number"), path, _change_key(change))
                totals[f"change:{duplicate_change_key!r}"] += 1
                allowed_pair = {
                    "signature_changed": {"function", "async_function"},
                    "function_touched": {"function", "async_function"},
                    "class_touched": {"class"},
                    "decorator_added": {"decorator"},
                    "decorator_removed": {"decorator"},
                    "field_added": {"field"},
                    "field_removed": {"field"},
                    "field_modified": {"field"},
                    "call_touched": {"call"},
                    "exception_handler_changed": {"except_handler"},
                    "node_added": ALLOWED_NODE_KINDS - {"module"},
                    "node_removed": ALLOWED_NODE_KINDS - {"module"},
                }
                if change.get("type") in ALLOWED_CHANGE_TYPES and change.get("kind") in allowed_pair.get(change.get("type"), set()):
                    totals["valid_change_type"] += 1
                if set(change.get("evidence_lines", [])) & file_lines:
                    totals["change_line_mapping"] += 1
                else:
                    totals["change_line_mapping_failed"] += 1
                if change.get("kind") == "call":
                    totals["call_changes"] += 1
                if changes_seen < changes_per_pr:
                    review_items.append({
                        "pr_number": record.get("pr_number"),
                        "path": file_item.get("path"),
                        "change": change,
                        "manual_checks": ["确认文件路径", "确认节点类型", "确认行号和限定名", "确认变化类型"],
                    })
                    changes_seen += 1

    def ratio(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator, 4) if denominator else None

    metrics = {
        "python_files": totals["python_files"],
        "parsed_files": totals["parsed_files"],
        "degraded_files": totals["degraded_files"],
        "degraded_errors_with_location": degraded_errors,
        "degraded_errors_missing_location": totals["degraded_error_records"] - degraded_errors,
        "nodes": totals["nodes"],
        "structural_changes": totals["structural_changes"],
        "file_path_accuracy": ratio(totals["file_path_checks"], totals["file_path_checks"] + totals["file_path_failures"]),
        "node_kind_accuracy": ratio(totals["valid_node_kind"], totals["nodes"]),
        "qualified_name_coverage": ratio(totals["qualified_node"], totals["nodes"]),
        "node_line_mapping_accuracy": ratio(totals["node_line_mapping"], totals["nodes"]),
        "change_type_accuracy": ratio(totals["valid_change_type"], totals["structural_changes"]),
        "change_line_mapping_accuracy": ratio(totals["change_line_mapping"], totals["structural_changes"]),
        "duplicate_node_rate": ratio(totals["duplicate_nodes"], totals["nodes"]),
        "duplicate_structural_change_rate": ratio(
            sum(max(0, count - 1) for key, count in totals.items() if isinstance(key, str) and key.startswith("change:")),
            totals["structural_changes"],
        ),
        "call_touched_ratio": ratio(totals["call_touched_changes"], totals["structural_changes"]),
        "call_change_ratio": ratio(totals["call_changes"], totals["structural_changes"]),
    }
    automatic_pass = all(
        value is None or value >= (0.85 if key == "node_kind_accuracy" else 0.90)
        for key, value in metrics.items()
        if key in {"file_path_accuracy", "node_kind_accuracy", "node_line_mapping_accuracy", "change_type_accuracy", "change_line_mapping_accuracy"}
    ) and (metrics["duplicate_node_rate"] or 0) <= 0.10
    return {
        "schema_version": "stage04-quality.v1",
        "audit_method": "automatic_consistency_checks_with_manual_review_queue",
        "selected_pr_numbers": selected_prs,
        "selected_record_count": len(selected_records),
        "minimum_prs": minimum_prs,
        "changes_per_pr_reviewed": changes_per_pr,
        "metrics": metrics,
        "automatic_gate": {
            "pass": automatic_pass,
            "thresholds": {
                "node_kind_accuracy": 0.85,
                "file_path_accuracy": 0.90,
                "node_line_mapping_accuracy": 0.90,
                "change_type_accuracy": 0.90,
                "change_line_mapping_accuracy": 0.90,
                "duplicate_node_rate_max": 0.10,
            },
        },
        "manual_review_required": True,
        "manual_review_items": review_items,
        "duplicate_examples": duplicate_keys[:50],
        "limitations": [
            "路径、节点类型和行号映射指标是与 stage03.v1 对照的一致性指标，不等同于人工语义准确率。",
            "结构变化数量不是规则质量指标，需结合证据完整性解释。",
        ],
    }


def write_audit_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
