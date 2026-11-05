import subprocess
import shutil
import unittest
from pathlib import Path

from prisk.services.branch_analysis import analyze_branches
from prisk.services.project_service import ProjectError, inspect_project
from tests.support import git, make_temp_dir


class BranchAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.repo = make_temp_dir("prisk-branch-")
        git(self.repo, "init")
        git(self.repo, "checkout", "-b", "main")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test")
        (self.repo / "netbox").mkdir()
        (self.repo / "netbox" / "models.py").write_text("class Device:\n    name = 'old'\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "base")
        git(self.repo, "checkout", "-b", "feature/example")
        (self.repo / "netbox" / "models.py").write_text("class Device:\n    name = 'new'\n    enabled = True\n", encoding="utf-8")
        git(self.repo, "commit", "-am", "feature")
        git(self.repo, "checkout", "main")
        self.project = inspect_project(self.repo)

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_three_dot_branch_report_contains_diff_and_structure(self):
        report = analyze_branches(self.repo, "main", "feature/example", project=self.project)
        self.assertEqual(report["schema_version"], "stage08.branch-report.v1")
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["diff_mode"], "three_dot")
        self.assertEqual(report["base_ref"], "main")
        self.assertTrue(report["merge_base_sha"])
        self.assertEqual(report["files"][0]["path"], "netbox/models.py")
        self.assertTrue(report["files"][0]["hunks"])
        self.assertIsInstance(report["summary"]["domains"], list)
        self.assertTrue(report["summary"]["structures"]["nodes"] >= 1)

    def test_uncommitted_changes_are_not_included(self):
        (self.repo / "netbox" / "models.py").write_text("uncommitted\n", encoding="utf-8")
        first = analyze_branches(self.repo, "main", "feature/example", project=self.project)
        second = analyze_branches(self.repo, "main", "feature/example", project=self.project)
        self.assertEqual(first["files"], second["files"])

    def test_same_ref_is_rejected(self):
        with self.assertRaises(ProjectError) as error:
            analyze_branches(self.repo, "main", "main", project=self.project)
        self.assertEqual(error.exception.code, "same_ref")

    def test_unknown_ref_has_clear_error_code(self):
        with self.assertRaises(ProjectError) as error:
            analyze_branches(self.repo, "main", "missing/branch", project=self.project)
        self.assertEqual(error.exception.code, "ref_not_found")

