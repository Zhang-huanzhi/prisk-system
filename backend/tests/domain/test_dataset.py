from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

from prisk.domain.changes import (
    build_change_object,
    build_from_jsonl,
    classify_path,
    load_records,
    parse_unified_diff,
    select_records,
)
from tests.support import make_temp_dir


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


class DatasetUnitTests(unittest.TestCase):
    def test_classify_path(self) -> None:
        self.assertEqual(classify_path("netbox/dcim/tests/test_models.py"), "test")
        self.assertEqual(classify_path("netbox/dcim/models.py"), "business")
        self.assertEqual(classify_path("docs/readme.md"), "other")

    def test_parse_add_delete_and_hunk_lines(self) -> None:
        diff = """diff --git a/netbox/dcim/models.py b/netbox/dcim/models.py
index 1111111..2222222 100644
--- a/netbox/dcim/models.py
+++ b/netbox/dcim/models.py
@@ -1,2 +1,3 @@
 keep
-old
+new
+added
"""
        files = parse_unified_diff(
            diff,
            [{"status": "modified", "old_path": "netbox/dcim/models.py", "new_path": "netbox/dcim/models.py"}],
        )
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["additions"], 2)
        self.assertEqual(files[0]["deletions"], 1)
        lines = files[0]["hunks"][0]["lines"]
        self.assertEqual(lines[0], {"kind": "context", "old_line": 1, "new_line": 1, "text": "keep"})
        self.assertEqual(lines[1]["old_line"], 2)
        self.assertEqual(lines[2]["new_line"], 2)

    def test_parse_rename_and_binary(self) -> None:
        diff = """diff --git a/netbox/a.py b/netbox/b.py
similarity index 100%
rename from netbox/a.py
rename to netbox/b.py
diff --git a/netbox/logo.png b/netbox/logo.png
Binary files a/netbox/logo.png and b/netbox/logo.png differ
"""
        files = parse_unified_diff(
            diff,
            [
                {"status": "renamed", "old_path": "netbox/a.py", "new_path": "netbox/b.py"},
                {"status": "modified", "old_path": "netbox/logo.png", "new_path": "netbox/logo.png"},
            ],
        )
        self.assertEqual(files[0]["status"], "renamed")
        self.assertEqual(files[0]["new_path"], "netbox/b.py")
        self.assertTrue(files[1]["binary"])

    def test_invalid_json_and_invalid_record_are_preserved(self) -> None:
        directory = make_temp_dir()
        try:
            path = directory / "input.jsonl"
            path.write_text("{bad json}\n[]\n", encoding="utf-8")
            records = load_records(path)
        finally:
            shutil.rmtree(directory, ignore_errors=True)
        self.assertEqual(records[0]["_input_error"]["code"], "invalid_json")
        self.assertEqual(records[1]["_input_error"]["code"], "record_not_object")

    def test_pilot_selection_uses_small_medium_large(self) -> None:
        records = []
        for pr_number, band in ((226, "large"), (19, "medium"), (179, "small"), (1000, "small")):
            records.append(
                {
                    "pr_number": pr_number,
                    "size_band": band,
                    "availability": {"diff_ok": True, "exclusion_reason": None},
                    "change_facts": {"business_changed": True},
                }
            )
        selected = select_records(records, 3)
        self.assertEqual([item["pr_number"] for item in selected], [179, 19, 226])


class DatasetIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = make_temp_dir()
        self.repo = self.temp / "repo"
        self.repo.mkdir()
        run_git(self.repo, "init", "-b", "main")
        run_git(self.repo, "config", "user.name", "Prisk Test")
        run_git(self.repo, "config", "user.email", "prisk@example.invalid")
        (self.repo / "netbox").mkdir()
        (self.repo / "netbox" / "models.py").write_text("class Model:\n    value = 1\n", encoding="utf-8")
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-m", "base")
        self.base = run_git(self.repo, "rev-parse", "HEAD")
        run_git(self.repo, "checkout", "-b", "feature")
        (self.repo / "netbox" / "models.py").write_text(
            "class Model:\n    value = 2\n    changed = True\n", encoding="utf-8"
        )
        (self.repo / "netbox" / "tests").mkdir()
        (self.repo / "netbox" / "tests" / "test_models.py").write_text(
            "def test_model():\n    assert True\n", encoding="utf-8"
        )
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-m", "feature")
        self.head = run_git(self.repo, "rev-parse", "HEAD")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_build_change_object_uses_three_dot_diff(self) -> None:
        record = {
            "repo": "netbox-community/netbox",
            "pr_number": 19,
            "title": "test",
            "base_sha": self.base,
            "head_sha": self.head,
            "availability": {"diff_ok": True, "exclusion_reason": None},
            "change_facts": {
                "files_changed": 2,
                "additions": 4,
                "deletions": 1,
                "business_changed": True,
                "test_changed": True,
                "test_cochanged": True,
            },
        }
        before = run_git(self.repo, "status", "--porcelain")
        result = build_change_object(record, self.repo)
        after = run_git(self.repo, "status", "--porcelain")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["diff_mode"], "three_dot")
        self.assertEqual(result["summary"]["files_changed"], 2)
        self.assertTrue(result["summary"]["test_cochanged"])
        self.assertEqual(before, after)
        self.assertTrue(result["validation"]["matches_source_change_facts"])

    def test_build_from_jsonl_writes_manifest_and_errors_do_not_abort(self) -> None:
        input_path = self.temp / "records.jsonl"
        output_path = self.temp / "out.jsonl"
        manifest_path = self.temp / "manifest.json"
        records = [
            {
                "repo": "netbox-community/netbox",
                "pr_number": 19,
                "base_sha": self.base,
                "head_sha": self.head,
                "availability": {"diff_ok": True, "exclusion_reason": None},
                "change_facts": {"business_changed": True},
            },
            {
                "repo": "netbox-community/netbox",
                "pr_number": 20,
                "base_sha": "0" * 40,
                "head_sha": self.head,
                "availability": {"diff_ok": True, "exclusion_reason": None},
                "change_facts": {"business_changed": True},
            },
        ]
        input_path.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")
        manifest = build_from_jsonl(input_path, self.repo, output_path, manifest_path)
        objects = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(manifest["status_counts"], {"error": 1, "ok": 1})
        self.assertEqual([item["status"] for item in objects], ["ok", "error"])
        self.assertTrue(manifest_path.exists())


if __name__ == "__main__":
    unittest.main()
