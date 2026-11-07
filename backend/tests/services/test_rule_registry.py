from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / "backend" / "data" / "rules" / "rule-registry.json"
SCHEMA_PATH = ROOT / "docs" / "schemas" / "rule-metadata.schema.json"
KNOWLEDGE_BASE = ROOT / "docs" / "rules"


class RuleRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))

    def test_registry_has_expected_families(self) -> None:
        self.assertEqual(self.registry["schema_version"], "rule-registry.v1")
        rules = self.registry["rules"]
        self.assertEqual(len(rules), 23)
        self.assertEqual(
            {rule["rule_family"] for rule in rules},
            {"code_smell", "backend_contract", "breaking_impact"},
        )
        self.assertEqual(sum(rule["rule_family"] == "code_smell" for rule in rules), 8)
        self.assertEqual(sum(rule["rule_family"] == "backend_contract" for rule in rules), 10)
        self.assertEqual(sum(rule["rule_family"] == "breaking_impact" for rule in rules), 5)

    def test_every_rule_contains_paper_ready_sections(self) -> None:
        required = {
            "rule_id", "name", "version", "rule_family", "lifecycle", "owner",
            "classification", "rationale", "definition", "basis", "limitations",
            "validation_obligation",
        }
        classification = {
            "risk_nature", "dependency_level", "applicability", "target_layer",
            "evidence_type", "severity", "gatekeeper",
        }
        for rule in self.registry["rules"]:
            self.assertRegex(rule["rule_id"], r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
            self.assertIn(rule["rule_id"].split(".", 1)[0], {"api", "auth", "data", "config", "code", "workflow"})
            self.assertTrue(required.issubset(rule), rule["rule_id"])
            self.assertTrue(classification.issubset(rule["classification"]), rule["rule_id"])
            self.assertIn(rule["classification"]["severity"], {"Critical", "High", "Medium", "Low"})
            self.assertIn(rule["classification"]["risk_nature"], {"pr_intrinsic", "external_impact"})
            self.assertIn(rule["classification"]["dependency_level"], {"language", "framework", "database", "process"})
            self.assertIn("gatekeeper_condition", rule["classification"])
            self.assertTrue(all(isinstance(feature, dict) for feature in rule["definition"]["trigger_features"]))
            self.assertIn(
                rule["validation_obligation"]["level"],
                {"literature_inherited", "empirical_required", "implementation_only"},
            )

    def test_schema_declares_the_same_top_level_contract(self) -> None:
        self.assertEqual(self.schema["properties"]["schema_version"]["const"], "rule-registry.v1")
        self.assertEqual(self.schema["properties"]["rules"]["type"], "array")
        rule_required = set(self.schema["$defs"]["rule"]["required"])
        self.assertIn("validation_obligation", rule_required)
        self.assertIn("limitations", rule_required)
        self.assertIn("trigger_features", self.schema["$defs"]["rule"]["properties"]["definition"]["required"])
        self.assertEqual(
            self.schema["$defs"]["rule"]["properties"]["rule_family"]["enum"],
            ["code_smell", "backend_contract", "breaking_impact"],
        )

    def test_registered_and_implemented_rules_have_linked_matching_cards(self) -> None:
        index = (KNOWLEDGE_BASE / "README.md").read_text(encoding="utf-8")
        implemented = [rule["rule_id"] for rule in self.registry["rules"] if rule["lifecycle"] == "implemented"]
        self.assertEqual(
            implemented,
            [
                "code.swallowed_exception",
                "code.bare_exception",
                "code.dynamic_execution",
                "code.hardcoded_secret",
                "code.unmanaged_open",
                "code.deep_control_flow",
                "code.global_mutable_state",
                "workflow.test_collaboration_gap",
                "data.django_raw_sql_execution",
            ],
        )
        registered = [rule["rule_id"] for rule in self.registry["rules"] if rule["lifecycle"] == "registered"]
        self.assertEqual(registered, [])

    def test_draft_backend_contract_cards_are_linked_and_not_runtime_rules(self) -> None:
        from prisk.domain.rules import RULE_CATALOG

        index = (KNOWLEDGE_BASE / "README.md").read_text(encoding="utf-8")
        catalog_ids = {item["rule_id"] for item in RULE_CATALOG}
        expected = [
            "api.drf_public_parameter_added",
            "auth.drf_permission_decorator_removed",
        ]
        self.assertTrue(set(expected).isdisjoint(catalog_ids))
        self.assertIn("data.django_raw_sql_execution", catalog_ids)
        self.assertTrue({"code.hardcoded_secret", "code.global_mutable_state"} <= catalog_ids)
        for rule_id in expected:
            rule = next(item for item in self.registry["rules"] if item["rule_id"] == rule_id)
            self.assertEqual(rule["lifecycle"], "draft")
            match = re.search(rf"\[`{re.escape(rule_id)}`\]\(([^)]+)\) · `draft`", index)
            self.assertIsNotNone(match, rule_id)
            content = (KNOWLEDGE_BASE / match.group(1)).read_text(encoding="utf-8")
            self.assertIn(f"`{rule['version']}` / `{rule['rule_family']}` / `draft`", content)
            for key in ("risk_nature", "dependency_level", "severity"):
                self.assertIn(f"`{rule['classification'][key]}`", content)
        for lifecycle in ("registered", "implemented"):
            entries = [rule for rule in self.registry["rules"] if rule["lifecycle"] == lifecycle]
            for rule in entries:
                rule_id = rule["rule_id"]
                pattern = rf"\[`{re.escape(rule_id)}`\]\(([^)]+)\) · `{lifecycle}`"
                match = re.search(pattern, index)
                self.assertIsNotNone(match, rule_id)
                path = KNOWLEDGE_BASE / match.group(1)
                self.assertTrue(path.is_file(), rule_id)
                content = path.read_text(encoding="utf-8")
                self.assertIn(f"`{rule_id}`", content)
                self.assertIn(f"`{rule['version']}` / `{rule['rule_family']}` / `{lifecycle}`", content)
                for key in ("risk_nature", "dependency_level", "severity"):
                    self.assertIn(f"`{rule['classification'][key]}`", content)


def _lifecycle_tokens(text: str) -> set[str]:
    row = re.findall(r"^\|\s*生命周期\s*\|\s*`([a-z]+)`\s*\|", text, re.MULTILINE)
    combined = re.findall(r"`v\d+`\s*/\s*`[a-z_]+`\s*/\s*`([a-z]+)`", text)
    return set(row + combined)


class LifecycleFieldConsistencyTests(unittest.TestCase):
    """Card tables and the registry share schema lifecycle. No second status field."""

    def setUp(self) -> None:
        self.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))
        self.allowed = set(self.schema["$defs"]["rule"]["properties"]["lifecycle"]["enum"])

    def test_schema_lifecycle_enum_is_unchanged(self) -> None:
        self.assertEqual(
            self.schema["$defs"]["rule"]["properties"]["lifecycle"]["enum"],
            ["draft", "registered", "implemented", "validated", "deprecated"],
        )

    def test_every_card_lifecycle_matches_registry_and_stays_in_enum(self) -> None:
        by_id = {rule["rule_id"]: rule for rule in self.registry["rules"]}
        seen: set[str] = set()
        card_root = KNOWLEDGE_BASE / "catalog"
        for path in card_root.rglob("*.md"):
            if path.name == "README.md":
                continue
            text = path.read_text(encoding="utf-8")
            match = re.search(r"^\|\s*规则 ID\s*\|\s*`([^`]+)`\s*\|", text, re.MULTILINE)
            self.assertIsNotNone(match, path)
            rule_id = match.group(1)
            self.assertIn(rule_id, by_id, path)
            tokens = _lifecycle_tokens(text)
            self.assertEqual(tokens, {by_id[rule_id]["lifecycle"]}, path)
            self.assertTrue(tokens <= self.allowed, path)
            seen.add(rule_id)
        self.assertEqual(
            seen,
            {rule_id for rule_id, rule in by_id.items() if rule["lifecycle"] != "draft"}
            | {
                "api.drf_public_parameter_added",
                "api.drf_public_parameter_removed",
                "api.django_url_pattern_changed",
                "api.drf_viewset_action_changed",
                "auth.drf_permission_decorator_removed",
                "auth.drf_permission_policy_downgrade",
                "config.django_sensitive_settings_changed",
                "data.django_destructive_migration",
                "data.django_non_null_constraint_tightened",
                "data.django_transaction_boundary_changed",
                "workflow.large_change_scope",
            },
        )

    def test_excluded_drafts_have_no_card_and_no_promoted_lifecycle(self) -> None:
        excluded = {
            "code.dead_code_after_exit",
            "auth.drf_object_permission_bypass",
            "auth.django_permission_module_changed",
        }
        by_id = {rule["rule_id"]: rule for rule in self.registry["rules"]}
        for rule_id in excluded:
            self.assertEqual(by_id[rule_id]["lifecycle"], "draft")
        counts = {name: 0 for name in self.allowed}
        for rule in self.registry["rules"]:
            self.assertIn(rule["lifecycle"], self.allowed)
            counts[rule["lifecycle"]] += 1
        self.assertEqual(counts["draft"], 14)
        self.assertEqual(counts["implemented"], 9)
        self.assertEqual(counts["registered"], 0)
        self.assertEqual(counts["validated"], 0)
        self.assertEqual(counts["deprecated"], 0)
        for path in (KNOWLEDGE_BASE / "catalog").rglob("*.md"):
            if path.name == "README.md":
                continue
            text = path.read_text(encoding="utf-8")
            for rule_id in excluded:
                self.assertNotIn(f"| 规则 ID | `{rule_id}` |", text)

    def test_knowledge_base_badges_use_registry_lifecycle(self) -> None:
        index = (KNOWLEDGE_BASE / "README.md").read_text(encoding="utf-8")
        for rule in self.registry["rules"]:
            rule_id = rule["rule_id"]
            lifecycle = rule["lifecycle"]
            badge = re.search(rf"\[`{re.escape(rule_id)}`\]\(([^)]+)\) · `([a-z]+)`", index)
            if badge is None:
                continue
            self.assertEqual(badge.group(2), lifecycle, rule_id)
            content = (KNOWLEDGE_BASE / badge.group(1)).read_text(encoding="utf-8")
            self.assertEqual(_lifecycle_tokens(content), {lifecycle}, rule_id)


if __name__ == "__main__":
    unittest.main()
