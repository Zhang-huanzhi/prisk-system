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
        self.assertEqual(sum(rule["rule_family"] == "code_smell" for rule in rules), 9)
        self.assertEqual(sum(rule["rule_family"] == "backend_contract" for rule in rules), 10)
        self.assertEqual(sum(rule["rule_family"] == "breaking_impact" for rule in rules), 4)

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
            "data.django_raw_sql_execution",
        ]
        self.assertTrue(set(expected).isdisjoint(catalog_ids))
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


if __name__ == "__main__":
    unittest.main()
