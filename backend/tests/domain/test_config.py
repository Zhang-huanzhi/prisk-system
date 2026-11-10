"""Unit tests for prisk.domain.config preset system and threshold injection."""

from __future__ import annotations

import unittest
from typing import Any

from prisk.domain.config import (
    CONFIG_SCHEMA_VERSION,
    DEFAULT_CONFIG,
    PRESET_BALANCED,
    PRESET_DAILY_REVIEW,
    PRESET_FRAMEWORK_UPGRADE,
    PRESET_LEGACY_BASELINE,
    PRESET_SECURITY_FOCUS,
    PRESETS,
    get_preset,
    list_presets,
    normalize_audit_config,
)
from prisk.domain.rules import RULE_CATALOG, evaluate_rules


def _make_stage04_record(files: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "stage04.v1",
        "status": "ok",
        "repo": "netbox",
        "pr_number": 9999,
        "base_sha": "0" * 40,
        "head_sha": "1" * 40,
        "files": files,
        "errors": [],
    }


class TestConfigPresets(unittest.TestCase):
    def test_presets_exist_and_cover_all_29_rules(self) -> None:
        expected_presets = {
            PRESET_BALANCED,
            PRESET_SECURITY_FOCUS,
            PRESET_FRAMEWORK_UPGRADE,
            PRESET_DAILY_REVIEW,
            PRESET_LEGACY_BASELINE,
        }
        self.assertEqual(set(PRESETS.keys()), expected_presets)
        all_catalog_ids = {item["rule_id"] for item in RULE_CATALOG}
        self.assertEqual(len(all_catalog_ids), 29)

        for name, preset in PRESETS.items():
            self.assertEqual(preset["preset"], name)
            self.assertTrue(preset["name"])
            self.assertTrue(preset["description"])
            self.assertEqual(set(preset["enabled_rules"]), all_catalog_ids)
            self.assertEqual(set(preset["rule_weights"].keys()), all_catalog_ids)
            for rule_id, weight in preset["rule_weights"].items():
                self.assertIsInstance(weight, int, f"{name}.{rule_id}")
                self.assertFalse(isinstance(weight, bool), f"{name}.{rule_id}")
                self.assertTrue(0 <= weight <= 5, f"{name}.{rule_id}={weight}")
            self.assertTrue(0 <= preset["test_collaboration_weight"] <= 5)
            self.assertIn("medium", preset["thresholds"])
            self.assertIn("high", preset["thresholds"])
            self.assertTrue(0 <= preset["thresholds"]["medium"] < preset["thresholds"]["high"] <= 100)

    def test_list_presets_metadata(self) -> None:
        items = list_presets()
        self.assertEqual(len(items), 5)
        names = {item["preset"] for item in items}
        self.assertIn(PRESET_BALANCED, names)
        self.assertIn(PRESET_SECURITY_FOCUS, names)
        for item in items:
            self.assertEqual(item["enabled_rule_count"], 29)
            self.assertIn("thresholds", item)
            self.assertIn("rule_thresholds", item)

    def test_get_preset_returns_deepcopy(self) -> None:
        p1 = get_preset(PRESET_BALANCED)
        p1["rule_weights"]["api.signature_changed"] = 99
        p2 = get_preset(PRESET_BALANCED)
        self.assertEqual(p2["rule_weights"]["api.signature_changed"], 2)

    def test_unknown_preset_raises_error(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_preset("nonexistent_preset")
        self.assertIn("未知预设", str(ctx.exception))

    def test_legacy_baseline_preserves_historical_10_points(self) -> None:
        cfg = normalize_audit_config(None)
        structural_pts = sum(
            weight for r_id, weight in cfg["rule_weights"].items()
            if r_id != "workflow.test_collaboration_gap"
        )
        self.assertEqual(structural_pts, 9)
        self.assertEqual(cfg["test_collaboration_weight"], 1)
        self.assertEqual(cfg["rule_weights"]["code.swallowed_exception"], 0)
        self.assertEqual(cfg["rule_weights"]["code.bare_exception"], 0)
        self.assertEqual(cfg["rule_weights"]["code.dynamic_execution"], 0)

    def test_normalize_audit_config_defaults_and_idempotence(self) -> None:
        normalized = normalize_audit_config(DEFAULT_CONFIG)
        self.assertEqual(normalized, DEFAULT_CONFIG)

    def test_preset_selection_and_weights_differentiation(self) -> None:
        sec = normalize_audit_config({"preset": PRESET_SECURITY_FOCUS})
        self.assertEqual(sec["preset"], PRESET_SECURITY_FOCUS)
        self.assertEqual(sec["schema_version"], CONFIG_SCHEMA_VERSION)
        # Security focus must heavily weight permissions & secrets
        self.assertEqual(sec["rule_weights"]["auth.drf_permission_policy_downgrade"], 5)
        self.assertEqual(sec["rule_weights"]["auth.drf_permission_decorator_removed"], 5)
        self.assertEqual(sec["rule_weights"]["code.hardcoded_secret"], 5)
        self.assertEqual(sec["rule_weights"]["data.django_raw_sql_execution"], 4)
        self.assertEqual(sec["rule_thresholds"]["code.hardcoded_secret"]["min_length"], 6)

        fw = normalize_audit_config({"preset": PRESET_FRAMEWORK_UPGRADE})
        self.assertEqual(fw["preset"], PRESET_FRAMEWORK_UPGRADE)
        self.assertEqual(fw["rule_weights"]["data.django_destructive_migration"], 5)
        self.assertEqual(fw["rule_weights"]["api.drf_viewset_action_changed"], 4)
        self.assertEqual(fw["rule_weights"]["data.django_field_rename_without_db_column"], 4)

        daily = normalize_audit_config({"preset": PRESET_DAILY_REVIEW})
        self.assertEqual(daily["preset"], PRESET_DAILY_REVIEW)
        self.assertEqual(daily["rule_weights"]["workflow.test_collaboration_gap"], 5)
        self.assertEqual(daily["rule_weights"]["code.deep_control_flow"], 4)
        self.assertEqual(daily["rule_thresholds"]["code.deep_control_flow"]["max_depth"], 3)

        bal = normalize_audit_config({"preset": PRESET_BALANCED})
        self.assertEqual(bal["preset"], PRESET_BALANCED)
        # All 29 rules have non-zero weight in balanced preset
        self.assertTrue(all(w > 0 for w in bal["rule_weights"].values()))

    def test_overrides_on_top_of_preset(self) -> None:
        custom = normalize_audit_config({
            "preset": PRESET_SECURITY_FOCUS,
            "rule_weights": {"code.hardcoded_secret": 2},
            "thresholds": {"medium": 20, "high": 50},
            "rule_thresholds": {"code.hardcoded_secret": {"min_length": 10}},
        })
        self.assertEqual(custom["preset"], PRESET_SECURITY_FOCUS)
        self.assertEqual(custom["rule_weights"]["code.hardcoded_secret"], 2)
        # Other security focus weights remain intact
        self.assertEqual(custom["rule_weights"]["auth.drf_permission_policy_downgrade"], 5)
        self.assertEqual(custom["thresholds"], {"medium": 20, "high": 50})
        self.assertEqual(custom["rule_thresholds"]["code.hardcoded_secret"]["min_length"], 10)

    def test_validation_rejects_invalid_weights_and_thresholds(self) -> None:
        with self.assertRaises(ValueError):
            normalize_audit_config({"rule_weights": {"api.signature_changed": 6}})
        with self.assertRaises(ValueError):
            normalize_audit_config({"rule_weights": {"api.signature_changed": -1}})
        with self.assertRaises(ValueError):
            normalize_audit_config({"rule_weights": {"unknown.rule": 2}})
        with self.assertRaises(ValueError):
            normalize_audit_config({"thresholds": {"medium": 70, "high": 50}})
        with self.assertRaises(ValueError):
            normalize_audit_config({"thresholds": {"medium": -5, "high": 50}})
        with self.assertRaises(ValueError):
            normalize_audit_config({"test_collaboration_weight": 10})

    def test_validation_rejects_invalid_rule_thresholds(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            normalize_audit_config({"rule_thresholds": {"code.deep_control_flow": {"max_depth": 1}}})
        self.assertIn("必须在 [2, 10] 范围内", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            normalize_audit_config({"rule_thresholds": {"code.deep_control_flow": {"max_depth": 15}}})
        self.assertIn("必须在 [2, 10] 范围内", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            normalize_audit_config({"rule_thresholds": {"code.hardcoded_secret": {"min_length": 2}}})
        self.assertIn("必须在 [4, 32] 范围内", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            normalize_audit_config({"rule_thresholds": {"code.deep_control_flow": {"unknown_param": 5}}})
        self.assertIn("不支持参数", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            normalize_audit_config({"rule_thresholds": {"unknown.rule": {"x": 1}}})
        self.assertIn("未知规则", str(ctx.exception))


class TestDynamicThresholdInjection(unittest.TestCase):
    def test_deep_control_flow_dynamic_threshold(self) -> None:
        # A control flow node with recorded nesting depth 3
        # With default threshold (4), it should NOT trigger a finding
        record = _make_stage04_record([{
            "path": "netbox/views.py",
            "role": "business",
            "is_python": True,
            "status": "modified",
            "nodes": [{
                "node_id": "flow-3",
                "kind": "control_flow",
                "side": "head",
                "start_line": 10,
                "end_line": 15,
                "changed_lines": [10, 11],
                "details": {
                    "control_kind": "if",
                    "nesting_depth": 3,
                },
            }],
            "structural_changes": [],
            "parse_status": {"head": "ok"},
            "errors": [],
        }])

        # 1. Default config (depth threshold = 4) -> No finding
        default_eval = evaluate_rules(record)
        findings_default = [f for f in default_eval["findings"] if f["rule_id"] == "code.deep_control_flow"]
        self.assertEqual(len(findings_default), 0)

        # 2. Config with max_depth=2 -> Finding triggered!
        custom_config = normalize_audit_config({
            "rule_thresholds": {"code.deep_control_flow": {"max_depth": 2}},
        })
        custom_eval = evaluate_rules(record, custom_config)
        findings_custom = [f for f in custom_eval["findings"] if f["rule_id"] == "code.deep_control_flow"]
        self.assertEqual(len(findings_custom), 1)
        evidence = findings_custom[0]["evidence"][0]
        self.assertEqual(evidence["nesting_depth"], 3)
        self.assertEqual(evidence["depth_threshold"], 2)
        self.assertIn("超过配置阈值 2", findings_custom[0]["message"])

    def test_hardcoded_secret_dynamic_threshold(self) -> None:
        # A literal binding with credential name and length 6
        # With default threshold (8), it should NOT trigger a finding
        record = _make_stage04_record([{
            "path": "netbox/secrets.py",
            "role": "business",
            "is_python": True,
            "status": "modified",
            "nodes": [{
                "node_id": "secret-1",
                "kind": "literal_binding",
                "side": "head",
                "start_line": 20,
                "end_line": 20,
                "changed_lines": [20],
                "details": {
                    "binding_name": "secret_key",
                    "binding_form": "name_assignment",
                    "literal_kind": "str",
                    "literal_length": 6,
                    "literal_text": "abc123",
                },
            }],
            "structural_changes": [],
            "parse_status": {"head": "ok"},
            "errors": [],
        }])

        # 1. Default config (min_length = 8) -> No finding
        default_eval = evaluate_rules(record)
        findings_default = [f for f in default_eval["findings"] if f["rule_id"] == "code.hardcoded_secret"]
        self.assertEqual(len(findings_default), 0)

        # 2. Security focus preset (min_length = 6) -> Finding triggered!
        sec_config = normalize_audit_config({"preset": PRESET_SECURITY_FOCUS})
        sec_eval = evaluate_rules(record, sec_config)
        findings_sec = [f for f in sec_eval["findings"] if f["rule_id"] == "code.hardcoded_secret"]
        self.assertEqual(len(findings_sec), 1)
        evidence = findings_sec[0]["evidence"][0]
        self.assertEqual(evidence["binding_name"], "secret_key")
        self.assertEqual(evidence["value_length"], 6)


if __name__ == "__main__":
    unittest.main()
