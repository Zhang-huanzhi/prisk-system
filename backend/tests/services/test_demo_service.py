from __future__ import annotations

import unittest
import json
import shutil
from pathlib import Path

from prisk.services.demo_service import DEFAULT_CONFIG, DemoData, normalize_config
from tests.support import make_temp_dir


class DemoServiceTests(unittest.TestCase):
    def test_analyze_exposes_diff_hunks_and_rule_catalog_details(self) -> None:
        root = make_temp_dir("prisk-demo-")
        try:
            stage03 = root / "stage03.jsonl"
            stage04 = root / "stage04.jsonl"
            stage05 = root / "stage05.jsonl"
            stage03.write_text(json.dumps({
                "status": "ok", "pr_number": 12, "repo": "netbox-community/netbox",
                "source": {"title": "Diff demo"},
                "summary": {"files_changed": 1, "business_files": 1, "test_files": 0, "additions": 1, "deletions": 1, "business_changed": True},
                "files": [{
                    "new_path": "netbox/core/api/views.py", "old_path": "netbox/core/api/views.py",
                    "role": "business", "is_python": True, "additions": 1, "deletions": 1,
                    "hunks": [{"old_start": 4, "old_count": 1, "new_start": 4, "new_count": 1, "lines": [
                        {"kind": "delete", "old_line": 4, "new_line": None, "text": "old()"},
                        {"kind": "add", "old_line": None, "new_line": 4, "text": "new()"},
                    ]}],
                }],
            }) + "\n", encoding="utf-8")
            stage04.write_text(json.dumps({
                "status": "ok", "pr_number": 12, "files": [{
                    "path": "netbox/core/api/views.py", "parse_status": {"base": "ok", "head": "ok"}, "errors": [], "nodes": [],
                }],
            }) + "\n", encoding="utf-8")
            stage05.write_text(json.dumps({
                "status": "ok", "pr_number": 12, "summary": {"test_collaboration": True, "parse_degraded": False}, "findings": [],
            }) + "\n", encoding="utf-8")
            data = DemoData(stage03, stage04, stage05)
            report = data.analyze(12)
            catalog = data.catalog()
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(report["files"][0]["hunks"][0]["lines"][1]["kind"], "add")
        self.assertEqual(report["files"][0]["parse_status"]["head"], "ok")
        self.assertEqual(len(catalog), 10)
        self.assertTrue(all(item.get("rule_id") and item.get("applicable_scope") and "default_weight" in item for item in catalog))

    def test_config_is_deterministic_and_rejects_invalid_thresholds(self) -> None:
        self.assertEqual(normalize_config(DEFAULT_CONFIG), DEFAULT_CONFIG)
        with self.assertRaises(ValueError):
            normalize_config({"thresholds": {"medium": 80, "high": 60}})

    def test_config_rejects_unknown_rules_and_weights(self) -> None:
        with self.assertRaises(ValueError):
            normalize_config({"enabled_rules": ["unknown.rule"]})
        with self.assertRaises(ValueError):
            normalize_config({"rule_weights": {"auth.permission_structure_changed": 9}})

    def test_default_config_keeps_historical_score_denominator(self) -> None:
        normalized = normalize_config(None)
        self.assertEqual(len(normalized["enabled_rules"]), 10)
        self.assertEqual(normalized["rule_weights"]["code.swallowed_exception"], 0)
        self.assertEqual(normalized["rule_weights"]["code.bare_exception"], 0)
        self.assertEqual(normalized["rule_weights"]["code.dynamic_execution"], 0)
        self.assertEqual(normalized["rule_weights"]["code.unmanaged_open"], 0)
        self.assertEqual(normalized["rule_weights"]["code.deep_control_flow"], 0)
        self.assertEqual(sum(normalized["rule_weights"][rule_id] for rule_id in normalized["enabled_rules"]), 9)
        self.assertLess(normalized["thresholds"]["medium"], normalized["thresholds"]["high"])

    def test_scoring_is_rule_weighted_and_evidence_is_enriched(self) -> None:
        root = make_temp_dir("prisk-demo-")
        try:
            stage03 = root / "stage03.jsonl"
            stage04 = root / "stage04.jsonl"
            stage05 = root / "stage05.jsonl"
            stage03.write_text(json.dumps({
                "status": "ok", "pr_number": 9, "repo": "netbox-community/netbox",
                "source": {"title": "Demo PR", "author": "reviewer"},
                "summary": {"files_changed": 1, "business_files": 1, "test_files": 0, "additions": 2, "deletions": 1, "business_changed": True},
                "files": [{"new_path": "netbox/core/models.py", "old_path": "netbox/core/models.py", "role": "business", "is_python": True, "additions": 2, "deletions": 1}],
            }) + "\n", encoding="utf-8")
            stage04.write_text(json.dumps({
                "status": "ok", "pr_number": 9, "files": [{"path": "netbox/core/models.py", "nodes": [{"node_id": "head:call:atomic:1", "source_segment": "atomic()", "start_line": 12, "end_line": 12}]}],
            }) + "\n", encoding="utf-8")
            stage05.write_text(json.dumps({
                "status": "ok", "pr_number": 9, "summary": {"test_collaboration": True, "parse_degraded": False},
                "findings": [{"rule_id": "auth.permission_structure_changed", "severity": "high", "suggested_action": "复核权限边界", "evidence": [{"path": "netbox/core/models.py", "node_id": "head:call:atomic:1", "node_kind": "call", "structural_change_type": "call_touched", "lines": [12]}]}],
            }) + "\n", encoding="utf-8")
            data = DemoData(stage03, stage04, stage05)
            baseline = data.analyze(9)
            changed = data.analyze(9, {"rule_weights": {"auth.permission_structure_changed": 5}})
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(baseline["score"], 40)
        self.assertEqual(changed["score"], 50)
        self.assertEqual(baseline["findings"][0]["evidence"][0]["source_segment"], "atomic()")
        self.assertTrue(baseline["summary"]["test_collaboration_gap"])

    def test_enrichment_keeps_explicit_unavailable_evidence(self) -> None:
        root = make_temp_dir("prisk-demo-")
        try:
            stage03 = root / "stage03.jsonl"
            stage04 = root / "stage04.jsonl"
            stage05 = root / "stage05.jsonl"
            stage03.write_text(json.dumps({
                "status": "ok", "pr_number": 4, "repo": "example/example",
                "summary": {"files_changed": 1, "business_changed": True, "test_changed": True},
                "files": [],
            }) + "\n", encoding="utf-8")
            stage04.write_text(json.dumps({"status": "ok", "pr_number": 4, "files": [{"nodes": []}]}) + "\n", encoding="utf-8")
            stage05.write_text(json.dumps({
                "status": "ok", "pr_number": 4, "summary": {"test_collaboration": False, "parse_degraded": False},
                "findings": [{
                    "rule_id": "code.dynamic_execution",
                    "severity": "medium",
                    "message": "直接调用 eval。",
                    "suggested_action": "复核",
                    "evidence": [{
                        "path": "netbox/legacy.py",
                        "node_id": "missing-node",
                        "node_kind": "call",
                        "structural_change_type": "added_line_overlap",
                        "lines": [3],
                        "source_segment": None,
                        "source_status": "unavailable",
                        "before": {"status": "unavailable", "reason": "no_base_node", "source_segment": None},
                        "after": {"status": "unavailable", "reason": "source_missing", "source_segment": None},
                    }],
                }],
            }) + "\n", encoding="utf-8")
            report = DemoData(stage03, stage04, stage05).analyze(4)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        evidence = report["findings"][0]["evidence"][0]
        self.assertIsNone(evidence["source_segment"])
        self.assertEqual(evidence["source_status"], "unavailable")
        self.assertEqual(evidence["before"]["reason"], "no_base_node")
        self.assertEqual(evidence["after"]["reason"], "source_missing")


if __name__ == "__main__":
    unittest.main()
