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

    def test_registered_rules_have_linked_matching_cards(self) -> None:
        index = (KNOWLEDGE_BASE / "README.md").read_text(encoding="utf-8")
        entries = [rule for rule in self.registry["rules"] if rule["lifecycle"] == "registered"]
        self.assertTrue(entries)
        for rule in entries:
            rule_id = rule["rule_id"]
            pattern = rf"\[`{re.escape(rule_id)}`\]\(([^)]+)\) · `registered`"
            match = re.search(pattern, index)
            self.assertIsNotNone(match, rule_id)
            path = KNOWLEDGE_BASE / match.group(1)
            self.assertTrue(path.is_file(), rule_id)
            content = path.read_text(encoding="utf-8")
            self.assertIn(f"`{rule_id}`", content)
            self.assertIn(f"`{rule['version']}` / `{rule['rule_family']}` / `registered`", content)
            for key in ("risk_nature", "dependency_level", "severity"):
                self.assertIn(f"`{rule['classification'][key]}`", content)


if __name__ == "__main__":
    unittest.main()
