import subprocess
import shutil
import unittest
from pathlib import Path

from prisk.services.project_service import ProjectError, inspect_project
from tests.support import git, make_temp_dir


class ProjectServiceTests(unittest.TestCase):
    def setUp(self):
        self.repo = make_temp_dir("prisk-project-")
        git(self.repo, "init")
        git(self.repo, "checkout", "-b", "main")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test")
        (self.repo / "README.md").write_text("base\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "base")
        git(self.repo, "checkout", "-b", "feature/example")
        (self.repo / "README.md").write_text("feature\n", encoding="utf-8")
        git(self.repo, "commit", "-am", "feature")
        git(self.repo, "checkout", "main")

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_inspects_project_and_local_branches(self):
        project = inspect_project(self.repo)
        self.assertEqual(project["name"], self.repo.name)
        self.assertEqual(project["default_branch"], "main")
        self.assertEqual({item["ref"] for item in project["branches"]}, {"main", "feature/example"})
        self.assertTrue(all(item["short_sha"] for item in project["branches"]))

    def test_rejects_non_git_path(self):
        folder = make_temp_dir("prisk-plain-")
        try:
            with self.assertRaises(ProjectError) as error:
                inspect_project(folder)
            self.assertEqual(error.exception.code, "not_git_repository")
        finally:
            shutil.rmtree(folder, ignore_errors=True)

