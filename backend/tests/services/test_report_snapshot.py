"""Unit and integration tests for reproducible config snapshots and Markdown report export."""

from __future__ import annotations

import json
import re
import shutil
import unittest

from prisk.domain.config import (
    CONFIG_SNAPSHOT_SCHEMA_VERSION,
    PRESET_BALANCED,
    PRESET_DAILY_REVIEW,
    PRESET_FRAMEWORK_UPGRADE,
    PRESET_LEGACY_BASELINE,
    PRESET_SECURITY_FOCUS,
    build_config_snapshot,
    list_presets,
    normalize_audit_config,
)
from prisk.domain.report_export import render_markdown_report
from prisk.paths import demo_data_root
from prisk.services.analysis_cache import clear_analysis_cache
from prisk.services.branch_analysis import analyze_branches
from prisk.services.demo_service import DemoData
from prisk.services.project_service import inspect_project
from tests.support import git, make_temp_dir


class ConfigSnapshotUnitTests(unittest.TestCase):
    def test_default_snapshot_seals_all_29_rules_and_thresholds(self) -> None:
        snap = build_config_snapshot(None)
        self.assertEqual(snap["schema_version"], CONFIG_SNAPSHOT_SCHEMA_VERSION)
        self.assertEqual(snap["preset"], PRESET_LEGACY_BASELINE)
        self.assertEqual(snap["preset_name"], "历史兼容基线")
        self.assertFalse(snap["customized"])
        self.assertRegex(snap["config_digest"], r"^[0-9a-f]{16}$")
        self.assertEqual(snap["enabled_rule_count"], 29)
        self.assertEqual(snap["disabled_rule_count"], 0)
        self.assertEqual(len(snap["enabled_rules"]), 29)
        self.assertEqual(snap["disabled_rules"], [])
        self.assertEqual(snap["thresholds"], {"medium": 30, "high": 65})
        self.assertEqual(
            snap["rule_thresholds"],
            {
                "code.deep_control_flow": {"max_depth": 4},
                "code.hardcoded_secret": {"min_length": 8},
            },
        )

    def test_preset_snapshots_have_distinct_deterministic_digests(self) -> None:
        digests: set[str] = set()
        for preset_name in (
            PRESET_BALANCED,
            PRESET_SECURITY_FOCUS,
            PRESET_FRAMEWORK_UPGRADE,
            PRESET_DAILY_REVIEW,
            PRESET_LEGACY_BASELINE,
        ):
            s1 = build_config_snapshot({"preset": preset_name})
            s2 = build_config_snapshot({"preset": preset_name})
            self.assertEqual(s1["config_digest"], s2["config_digest"])
            self.assertFalse(s1["customized"])
            digests.add(s1["config_digest"])
        self.assertEqual(len(digests), 5)

    def test_customized_overrides_change_digest_and_track_disabled_rules(self) -> None:
        base_sec = build_config_snapshot({"preset": PRESET_SECURITY_FOCUS})
        custom_sec = build_config_snapshot({
            "preset": PRESET_SECURITY_FOCUS,
            "enabled_rules": ["code.hardcoded_secret", "auth.drf_permission_policy_downgrade"],
            "rule_weights": {"code.hardcoded_secret": 4},
            "thresholds": {"medium": 20, "high": 50},
            "rule_thresholds": {"code.hardcoded_secret": {"min_length": 10}},
        })
        self.assertTrue(custom_sec["customized"])
        self.assertNotEqual(base_sec["config_digest"], custom_sec["config_digest"])
        self.assertEqual(custom_sec["enabled_rule_count"], 2)
        self.assertEqual(custom_sec["disabled_rule_count"], 27)
        self.assertIn("api.signature_changed", custom_sec["disabled_rules"])
        self.assertEqual(custom_sec["rule_thresholds"]["code.hardcoded_secret"]["min_length"], 10)

    def test_list_presets_includes_full_weights_and_rules_for_workbench(self) -> None:
        presets = list_presets()
        self.assertEqual(len(presets), 5)
        for item in presets:
            self.assertEqual(len(item["enabled_rules"]), 29)
            self.assertEqual(len(item["rule_weights"]), 29)
            self.assertIn("test_collaboration_weight", item)
            self.assertIn("test_collaboration_enabled", item)
            self.assertIn("thresholds", item)
            self.assertIn("rule_thresholds", item)


class ReportExportReproducibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_analysis_cache()
        root = demo_data_root()
        self.demo = DemoData(
            root / "stage03-change-objects.jsonl",
            root / "stage04-structure-objects.jsonl",
            root / "stage05-rule-results.jsonl",
        )
        self.repo = make_temp_dir("prisk-report-snap-")
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test")
        (self.repo / "netbox").mkdir()
        (self.repo / "netbox" / "views.py").write_text("def handle():\n    return 1\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "base")
        git(self.repo, "checkout", "-b", "feature/audit")
        (self.repo / "netbox" / "views.py").write_text(
            "def handle(limit=10):\n"
            "    try:\n"
            "        return limit\n"
            "    except Exception:\n"
            "        pass\n",
            encoding="utf-8",
        )
        git(self.repo, "commit", "-am", "feature change")
        git(self.repo, "checkout", "main")
        self.project = inspect_project(self.repo)

    def tearDown(self) -> None:
        clear_analysis_cache()
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_demo_and_branch_reports_contain_config_snapshot_and_reproducible_markdown(self) -> None:
        pr_num = self.demo.pr_numbers()[0]
        pr_report = self.demo.analyze(pr_num, {"preset": PRESET_BALANCED})
        self.assertIn("config_snapshot", pr_report)
        self.assertEqual(pr_report["config_snapshot"]["preset"], PRESET_BALANCED)

        branch_cfg = {
            "preset": PRESET_DAILY_REVIEW,
            "rule_weights": {"code.swallowed_exception": 5},
            "thresholds": {"medium": 25, "high": 55},
            "rule_thresholds": {"code.deep_control_flow": {"max_depth": 3}},
        }
        branch_report = analyze_branches(
            self.repo,
            "main",
            "feature/audit",
            project=self.project,
            config=branch_cfg,
        )
        snap = branch_report["config_snapshot"]
        self.assertEqual(snap["preset"], PRESET_DAILY_REVIEW)
        self.assertTrue(snap["customized"])
        self.assertEqual(snap["rule_weights"]["code.swallowed_exception"], 5)
        self.assertEqual(snap["thresholds"], {"medium": 25, "high": 55})
        self.assertEqual(snap["rule_thresholds"]["code.deep_control_flow"]["max_depth"], 3)

        md = render_markdown_report(branch_report)
        self.assertIn("## 运行配置快照（可复现封存）", md)
        self.assertIn(snap["config_digest"], md)
        self.assertIn("`daily_review`", md)
        self.assertIn("`code.deep_control_flow.max_depth = 3`", md)
        self.assertIn("### 可复现配置载荷", md)

        # Extract embedded JSON payload from Markdown and verify exact reproducibility
        match = re.search(r"```json\n(\{.*?\})\n```", md, re.DOTALL)
        self.assertIsNotNone(match)
        extracted_cfg = json.loads(match.group(1))
        repro_report = analyze_branches(
            self.repo,
            "main",
            "feature/audit",
            project=self.project,
            config=extracted_cfg,
        )
        self.assertEqual(repro_report["score"], branch_report["score"])
        self.assertEqual(repro_report["risk_level"], branch_report["risk_level"])
        self.assertEqual(
            repro_report["config_snapshot"]["config_digest"],
            branch_report["config_snapshot"]["config_digest"],
        )


if __name__ == "__main__":
    unittest.main()
