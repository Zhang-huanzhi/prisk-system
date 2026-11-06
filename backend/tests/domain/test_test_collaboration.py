from __future__ import annotations

import json
import unittest

from prisk.domain.changes import load_records
from prisk.domain.rules import evaluate_rules
from prisk.domain.test_collaboration import COLLABORATION_RULE_ID, classify_collaboration_path
from prisk.paths import demo_data_root
from prisk.services.demo_service import DemoData


def _file(
    path: str,
    status: str = "modified",
    additions: int = 1,
    deletions: int = 0,
    *,
    old_path: str | None = None,
    new_path: str | None = None,
    binary: bool = False,
) -> dict:
    return {
        "path": new_path or old_path or path,
        "old_path": old_path if old_path is not None else (None if status == "added" else path),
        "new_path": new_path if new_path is not None else (None if status == "deleted" else path),
        "status": status,
        "additions": additions,
        "deletions": deletions,
        "binary": binary,
    }


def _record(files: list[dict], **summary: object) -> dict:
    return {
        "schema_version": "stage04.v1",
        "status": "ok",
        "repo": "example/example",
        "pr_number": 7,
        "files": files,
        "summary": summary,
    }


def _collaboration(result: dict) -> list[dict]:
    return [item for item in result["findings"] if item["rule_id"] == COLLABORATION_RULE_ID]


class PathClassTests(unittest.TestCase):
    def test_default_classes_cover_this_repo_and_demo_python(self) -> None:
        self.assertEqual(classify_collaboration_path("backend/tests/test_rules.py"), "test")
        self.assertEqual(classify_collaboration_path("backend/prisk/domain/rules.py"), "production")
        self.assertEqual(classify_collaboration_path("frontend/src/components/dashboard.tsx"), "production")
        self.assertEqual(classify_collaboration_path("netbox/dcim/models.py"), "production")
        self.assertEqual(classify_collaboration_path("netbox/dcim/tests/test_models.py"), "test")
        self.assertEqual(classify_collaboration_path("src/example.py"), "production")
        self.assertEqual(classify_collaboration_path("docs/architecture.md"), "non_production")
        self.assertEqual(classify_collaboration_path("netbox/dcim/migrations/0001_initial.py"), "non_production")
        self.assertEqual(classify_collaboration_path("netbox/netbox/settings.py"), "non_production")
        self.assertEqual(classify_collaboration_path("backend/prisk/generated/client.py"), "non_production")
        self.assertEqual(classify_collaboration_path("pyproject.toml"), "unknown")


class TestCollaborationRuleTests(unittest.TestCase):
    def test_production_without_test_change_hits(self) -> None:
        result = evaluate_rules(_record([
            _file("backend/prisk/domain/rules.py", additions=4, deletions=1),
            _file("docs/architecture.md", additions=2, deletions=0),
        ], files_changed=2, test_files=0, test_changed=False))
        findings = _collaboration(result)
        self.assertEqual(len(findings), 1)
        self.assertTrue(result["summary"]["test_collaboration"])
        self.assertEqual(findings[0]["evidence"][0]["path"], "backend/prisk/domain/rules.py")
        self.assertEqual(findings[0]["evidence"][0]["additions"], 4)
        self.assertEqual(findings[0]["test_files_changed"], 0)
        self.assertEqual(findings[0]["change_boundary"], "content_edit")
        self.assertEqual(findings[0]["impact_type"], "pr_intrinsic_risk")
        self.assertIn("不说明测试缺失、覆盖不足、回归、外部破坏或缺陷", findings[0]["message"])
        self.assertEqual(result["summary"]["unanalyzed"], [])

    def test_mixed_test_and_production_does_not_hit(self) -> None:
        result = evaluate_rules(_record([
            _file("backend/prisk/domain/rules.py", additions=2, deletions=0),
            _file("backend/tests/test_rules.py", additions=1, deletions=0),
        ]))
        self.assertEqual(_collaboration(result), [])
        self.assertFalse(result["summary"]["test_collaboration"])
        self.assertEqual(result["summary"]["unanalyzed"], [])

    def test_deletion_only_is_marked_and_still_reported(self) -> None:
        result = evaluate_rules(_record([
            _file("netbox/dcim/models.py", status="deleted", additions=0, deletions=8),
        ]))
        finding = _collaboration(result)[0]
        self.assertEqual(finding["change_boundary"], "code_removal")
        self.assertEqual(finding["production_additions"], 0)
        self.assertEqual(finding["production_deletions"], 8)
        self.assertEqual(finding["evidence"][0]["content_change"], "removed")
        self.assertIn("不能区分死代码删除和功能下线", finding["message"])

    def test_rename_only_is_not_content_change(self) -> None:
        result = evaluate_rules(_record([
            _file(
                "backend/prisk/old.py",
                status="renamed",
                additions=0,
                deletions=0,
                old_path="backend/prisk/old.py",
                new_path="backend/prisk/new.py",
            ),
        ]))
        self.assertEqual(_collaboration(result), [])
        self.assertFalse(result["summary"]["test_collaboration"])
        self.assertEqual(result["summary"]["unanalyzed"], [])

    def test_rename_with_content_and_test_rename_do_not_hit(self) -> None:
        result = evaluate_rules(_record([
            _file(
                "backend/prisk/old.py",
                status="renamed",
                additions=2,
                deletions=1,
                old_path="backend/prisk/old.py",
                new_path="backend/prisk/new.py",
            ),
            _file(
                "backend/tests/test_old.py",
                status="renamed",
                additions=0,
                deletions=0,
                old_path="backend/tests/test_old.py",
                new_path="backend/tests/test_new.py",
            ),
        ]))
        self.assertEqual(_collaboration(result), [])
        self.assertEqual(result["summary"]["unanalyzed"], [])

    def test_docs_only_does_not_hit(self) -> None:
        result = evaluate_rules(_record([
            _file("docs/architecture.md", additions=3, deletions=1),
            _file("README.md", additions=1, deletions=0),
        ]))
        self.assertEqual(_collaboration(result), [])
        self.assertFalse(result["summary"]["test_collaboration"])
        self.assertEqual(result["summary"]["unanalyzed"], [])

    def test_unknown_path_is_unanalyzed_and_not_a_hit(self) -> None:
        result = evaluate_rules(_record([
            _file("backend/prisk/domain/rules.py", additions=2, deletions=0),
            _file("pyproject.toml", additions=1, deletions=0),
        ]))
        self.assertEqual(_collaboration(result), [])
        self.assertFalse(result["summary"]["test_collaboration"])
        self.assertEqual(result["summary"]["unanalyzed"], [{
            "path": "pyproject.toml",
            "reason": "path_classification_unavailable",
        }])

    def test_missing_line_counts_and_binary_production_are_unanalyzed(self) -> None:
        missing = evaluate_rules(_record([{
            "path": "backend/prisk/domain/rules.py",
            "old_path": "backend/prisk/domain/rules.py",
            "new_path": "backend/prisk/domain/rules.py",
            "status": "modified",
        }]))
        binary = evaluate_rules(_record([
            _file("backend/prisk/domain/rules.py", additions=0, deletions=0, binary=True),
        ]))
        rename = evaluate_rules(_record([{
            "path": "backend/prisk/new.py",
            "old_path": "backend/prisk/old.py",
            "new_path": "backend/prisk/new.py",
            "status": "renamed",
        }]))
        for result in (missing, binary, rename):
            self.assertEqual(_collaboration(result), [])
            self.assertFalse(result["summary"]["test_collaboration"])
            self.assertEqual(result["summary"]["unanalyzed"][0]["reason"], "diff_stats_unavailable")

    def test_test_only_and_no_production_do_not_hit(self) -> None:
        test_only = evaluate_rules(_record([
            _file("backend/tests/test_rules.py", additions=2, deletions=0),
        ]))
        no_production = evaluate_rules(_record([
            _file("netbox/dcim/migrations/0001_initial.py", additions=4, deletions=0),
            _file("netbox/netbox/settings.py", status="modified", additions=1, deletions=1),
        ]))
        self.assertEqual(_collaboration(test_only), [])
        self.assertEqual(_collaboration(no_production), [])
        self.assertEqual(test_only["summary"]["unanalyzed"], [])
        self.assertEqual(no_production["summary"]["unanalyzed"], [])
        self.assertFalse(test_only["summary"]["test_collaboration"])
        self.assertFalse(no_production["summary"]["test_collaboration"])

    def test_disabled_rule_does_not_mark_unknown_paths_unanalyzed(self) -> None:
        result = evaluate_rules(
            _record([_file("pyproject.toml", additions=1, deletions=0)]),
            {"enabled_rules": ["api.signature_changed"]},
        )
        self.assertEqual(result["summary"]["unanalyzed"], [])
        self.assertFalse(result["summary"]["test_collaboration"])

    def test_tracked_demo_does_not_pass_or_change_stored_score(self) -> None:
        root = demo_data_root()
        stage03 = load_records(root / "stage03-change-objects.jsonl")[0]
        stage04 = load_records(root / "stage04-structure-objects.jsonl")[0]
        from_change = evaluate_rules(stage03)
        from_structure = evaluate_rules(stage04)
        self.assertEqual(_collaboration(from_change), [])
        self.assertFalse(from_change["summary"]["test_collaboration"])
        self.assertEqual(from_change["summary"]["unanalyzed"], [{
            "path": "",
            "reason": "diff_stats_unavailable",
        }])
        self.assertEqual(_collaboration(from_structure), [])
        self.assertFalse(from_structure["summary"]["test_collaboration"])
        self.assertEqual(from_structure["summary"]["unanalyzed"], [])
        report = DemoData(
            root / "stage03-change-objects.jsonl",
            root / "stage04-structure-objects.jsonl",
            root / "stage05-rule-results.jsonl",
        ).analyze(12)
        self.assertEqual(report["score_basis"]["maximum_points"], 10)
        self.assertEqual(report["score_basis"]["earned_points"], 3)
        self.assertEqual(report["score"], 30)
        self.assertEqual(
            [item["rule_id"] for item in report["findings"]],
            ["api.signature_changed"],
        )
        stored = json.loads((root / "stage05-rule-results.jsonl").read_text(encoding="utf-8"))
        self.assertTrue(stored["summary"]["test_collaboration"])
        self.assertNotIn(
            COLLABORATION_RULE_ID,
            [item["rule_id"] for item in stored["findings"]],
        )
        self.assertTrue((root / "stage03-change-objects.jsonl").is_file())


if __name__ == "__main__":
    unittest.main()
