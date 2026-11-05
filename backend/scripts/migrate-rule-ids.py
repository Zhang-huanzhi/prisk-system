"""One-time migration for the v1.1.0-003 rule ID and domain contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


RULE_ID_MAP = {
    "smell.swallowed_exception": "code.swallowed_exception",
    "smell.bare_exception": "code.bare_exception",
    "smell.dynamic_execution": "code.dynamic_execution",
    "smell.hardcoded_secret": "code.hardcoded_secret",
    "smell.unmanaged_open": "code.unmanaged_open",
    "smell.dead_code_after_exit": "code.dead_code_after_exit",
    "smell.deep_control_flow": "code.deep_control_flow",
    "smell.global_mutable_state": "code.global_mutable_state",
    "smell.test_collaboration_gap": "workflow.test_collaboration_gap",
    "contract.drf_public_parameter_added": "api.drf_public_parameter_added",
    "contract.drf_public_parameter_removed": "api.drf_public_parameter_removed",
    "contract.django_url_pattern_changed": "api.django_url_pattern_changed",
    "contract.drf_viewset_action_changed": "api.drf_viewset_action_changed",
    "contract.drf_permission_decorator_removed": "auth.drf_permission_decorator_removed",
    "contract.drf_permission_policy_downgrade": "auth.drf_permission_policy_downgrade",
    "contract.drf_object_permission_bypass": "auth.drf_object_permission_bypass",
    "contract.django_permission_module_changed": "auth.django_permission_module_changed",
    "impact.django_destructive_migration": "data.django_destructive_migration",
    "impact.django_non_null_constraint_tightened": "data.django_non_null_constraint_tightened",
    "contract.django_raw_sql_execution": "data.django_raw_sql_execution",
    "impact.django_transaction_boundary_changed": "data.django_transaction_boundary_changed",
    "contract.django_sensitive_settings_changed": "config.django_sensitive_settings_changed",
    "impact.large_change_scope": "workflow.large_change_scope",
    "interface.signature_changed": "api.signature_changed",
    "auth.permission_structure_changed": "auth.permission_structure_changed",
    "data.transaction_structure_changed": "data.transaction_structure_changed",
}

_CONFIG_PATH = re.compile(r"/(?:settings?(?:/|\.py$)|configuration[^/]*\.py$)", re.I)


def migrate_text(value: str) -> str:
    for old, new in RULE_ID_MAP.items():
        value = value.replace(old, new)
    return value


def migrate_registry(source: Path, target: Path) -> None:
    document = json.loads(source.read_text(encoding="utf-8-sig"))
    for rule in document.get("rules", []):
        old_id = rule.get("rule_id")
        if old_id in RULE_ID_MAP:
            rule["rule_id"] = RULE_ID_MAP[old_id]
        definition = rule.get("definition", {})
        if isinstance(definition.get("finding"), str):
            definition["finding"] = migrate_text(definition["finding"])
    target.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def migrate_finding(finding: dict[str, Any]) -> list[dict[str, Any]]:
    old_id = finding.get("rule_id")
    if old_id != "config.exception_structure_changed":
        migrated = {key: value for key, value in finding.items() if key != "scene"}
        migrated["rule_id"] = RULE_ID_MAP.get(old_id, old_id)
        return [migrated]

    config_evidence = [item for item in finding.get("evidence", []) if _CONFIG_PATH.search(str(item.get("path") or ""))]
    code_evidence = [item for item in finding.get("evidence", []) if item.get("node_kind") == "except_handler"]
    results = []
    for rule_id, evidence in (
        ("config.configuration_structure_changed", config_evidence),
        ("code.exception_structure_changed", code_evidence),
    ):
        if evidence:
            migrated = {key: value for key, value in finding.items() if key not in {"scene", "evidence", "rule_id"}}
            migrated.update({"rule_id": rule_id, "evidence": evidence})
            results.append(migrated)
    return results


def migrate_jsonl(source: Path, target: Path) -> None:
    output = []
    for line in source.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        record["schema_version"] = "stage05.v2"
        findings = [finding for item in record.get("findings", []) for finding in migrate_finding(item)]
        record["findings"] = findings
        summary = record.setdefault("summary", {})
        summary.pop("scenes", None)
        summary["domains"] = sorted({item["rule_id"].split(".", 1)[0] for item in findings})
        output.append(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
    target.write_text("\n".join(output) + ("\n" if output else ""), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--jsonl", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if bool(args.registry) == bool(args.jsonl):
        parser.error("exactly one of --registry or --jsonl is required")
    if args.registry:
        migrate_registry(args.registry, args.output)
    else:
        migrate_jsonl(args.jsonl, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
