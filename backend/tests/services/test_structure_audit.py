from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from prisk.services.structure_audit import audit_structure_records, select_audit_prs
from tests.support import make_temp_dir


def record(pr_number: int, files: list[dict]) -> dict:
    return {"pr_number": pr_number, "status": "ok", "files": files}


class StructureAuditTests(unittest.TestCase):
    def test_selects_three_prs_per_scene_and_fills_unique_total(self) -> None:
        stage04 = [record(number, []) for number in range(1, 20)]
        survey = Path("survey.jsonl")
        # Patch the scene lookup at its input boundary via a small temporary JSONL fixture.
        root = make_temp_dir("prisk-audit-")
        try:
            survey = root / "survey.jsonl"
            rows = []
            for number in range(1, 16):
                scene = (number - 1) // 3
                scene_name = ("api", "auth", "data_transaction", "config_exception", "api")[scene]
                rows.append({"pr_number": number, "change_facts": {"scenes": {scene_name: {"hit": True}}}})
            survey.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            selected = select_audit_prs(stage04, survey, 12)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertGreaterEqual(len(selected), 12)
        self.assertEqual(len(selected), len(set(selected)))

    def test_checks_paths_kinds_and_diff_lines_against_stage03(self) -> None:
        stage04 = [record(10, [{
            "path": "netbox/api/views.py",
            "role": "business",
            "is_python": True,
            "parse_status": {"file": "ok"},
            "nodes": [{"kind": "function", "match_key": "function:f", "qualified_name": "f", "changed_lines": [4]}],
            "structural_changes": [{"type": "signature_changed", "kind": "function", "evidence_lines": [4]}],
            "errors": [],
        }])]
        stage03 = [record(10, [{
            "new_path": "netbox/api/views.py",
            "old_path": "netbox/api/views.py",
            "hunks": [{"lines": [{"kind": "add", "new_line": 4, "old_line": None}]}],
        }])]
        root = make_temp_dir("prisk-audit-")
        try:
            survey = root / "survey.jsonl"
            survey.write_text('{"pr_number":10,"change_facts":{"scenes":{"api":{"hit":true}}}}\n', encoding="utf-8")
            report = audit_structure_records(stage04, stage03, survey, minimum_prs=1, changes_per_pr=1)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(report["metrics"]["file_path_accuracy"], 1.0)
        self.assertEqual(report["metrics"]["change_line_mapping_accuracy"], 1.0)
        self.assertEqual(len(report["manual_review_items"]), 1)


if __name__ == "__main__":
    unittest.main()
