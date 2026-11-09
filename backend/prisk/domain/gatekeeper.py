"""Registry-backed one-vote gatekeeper lift for review scoring."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "rules" / "rule-registry.json"
_MIGRATIONS_SEGMENT = re.compile(r"(?:^|/)migrations(?:/|$)", re.I)
_DESTRUCTIVE_OPS = frozenset({"DeleteModel", "RemoveField"})
_ALLOW_ANY = re.compile(r"\bAllowAny\b")
_EMPTY_PERMISSION = re.compile(
    r"permission_classes\s*=\s*\[\s*\]|permission_classes\s*=\s*\(\s*\)|@permission_classes\(\s*\[\s*\]\s*\)|@permission_classes\(\s*\(\s*\)\s*\)"
)


@lru_cache(maxsize=1)
def load_rule_registry(path: str | None = None) -> dict[str, Any]:
    target = Path(path) if path else _REGISTRY_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def gatekeeper_rules(registry: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    data = registry or load_rule_registry()
    found: dict[str, dict[str, Any]] = {}
    for rule in data.get("rules", []):
        if not isinstance(rule, dict):
            continue
        classification = rule.get("classification") or {}
        if classification.get("gatekeeper") is True:
            found[str(rule.get("rule_id"))] = {
                "rule_id": rule.get("rule_id"),
                "gatekeeper": True,
                "gatekeeper_condition": classification.get("gatekeeper_condition"),
            }
    return found


def _callee_last_segment(details: dict[str, Any]) -> str | None:
    direct = details.get("direct_callee_name")
    if isinstance(direct, str) and direct.isidentifier():
        return direct
    callee = details.get("callee")
    if not isinstance(callee, str) or not callee.strip():
        return None
    text = callee.strip()
    if "(" in text:
        text = text.split("(", 1)[0].strip()
    segment = text.replace("\\", "/").rsplit(".", 1)[-1].strip()
    return segment if segment.isidentifier() else None


def _path_has_migrations(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return bool(_MIGRATIONS_SEGMENT.search(normalized))


def structural_gatekeeper_hits(stage04_or_report: dict[str, Any]) -> list[dict[str, str]]:
    """Score-side reads of DeleteModel/RemoveField and AllowAny downgrade forms."""
    hits: list[dict[str, str]] = []
    files = stage04_or_report.get("files") or []
    for file_item in files:
        if not isinstance(file_item, dict):
            continue
        path = str(file_item.get("path") or file_item.get("new_path") or file_item.get("old_path") or "")
        for node in file_item.get("nodes") or []:
            if not isinstance(node, dict) or node.get("side") not in {None, "head"}:
                continue
            if not node.get("changed_lines"):
                continue
            details = node.get("details") or {}
            if node.get("kind") == "call" and _path_has_migrations(path):
                segment = _callee_last_segment(details if isinstance(details, dict) else {})
                if segment in _DESTRUCTIVE_OPS:
                    hits.append({
                        "rule_id": "data.django_destructive_migration",
                        "path": path,
                        "node_id": str(node.get("node_id") or ""),
                        "operation": segment,
                    })
            segment_text = node.get("source_segment")
            if isinstance(segment_text, str) and (
                _ALLOW_ANY.search(segment_text) or _EMPTY_PERMISSION.search(segment_text)
            ):
                if "permission_classes" in segment_text or "@permission_classes" in segment_text:
                    hits.append({
                        "rule_id": "auth.drf_permission_policy_downgrade",
                        "path": path,
                        "node_id": str(node.get("node_id") or ""),
                        "operation": "AllowAny_or_empty",
                    })
    # Deduplicate by rule_id+path+node_id
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in hits:
        key = (item["rule_id"], item["path"], item["node_id"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def apply_gatekeeper_lift(
    *,
    risk_level: str,
    findings: list[dict[str, Any]],
    stage_record: dict[str, Any] | None = None,
    registry: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Force high risk when a gatekeeper registry rule or structural condition hits."""
    rules = gatekeeper_rules(registry)
    matched_finding_ids = sorted({
        str(item.get("rule_id"))
        for item in findings
        if isinstance(item, dict) and str(item.get("rule_id")) in rules
    })
    structural = structural_gatekeeper_hits(stage_record or {})
    structural_ids = sorted({item["rule_id"] for item in structural})
    lifted = bool(matched_finding_ids or structural_ids)
    basis = {
        "gatekeeper_lift": lifted,
        "gatekeeper_finding_rule_ids": matched_finding_ids,
        "gatekeeper_structural_rule_ids": structural_ids,
        "gatekeeper_structural_hits": structural,
        "registry_gatekeeper_rule_ids": sorted(rules),
    }
    if lifted:
        return "high", basis
    return risk_level, basis
