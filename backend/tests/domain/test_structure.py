from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

from prisk.domain.changes import parse_unified_diff, read_diff_text, read_name_status
from prisk.domain.structure import (
    build_structure_dataset,
    extract_changed_structures,
    parse_python_source,
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


class StructureUnitTests(unittest.TestCase):
    def test_extracts_required_node_kinds_and_details(self) -> None:
        source = """@class_decorator\nclass Example(Base):\n    field: int = make_value()\n\n    @method_decorator\n    def method(self, value: int = 1) -> str:\n        try:\n            return call(value)\n        except ValueError as error:\n            raise RuntimeError(error)\n"""
        parsed = parse_python_source(source, "netbox/example.py", "head")
        self.assertEqual(parsed["status"], "ok")
        kinds = {node["kind"] for node in parsed["nodes"]}
        self.assertTrue({"module", "class", "field", "function", "decorator", "call", "except_handler", "control_flow"} <= kinds)
        control = next(node for node in parsed["nodes"] if node["kind"] == "control_flow")
        self.assertEqual(control["details"]["control_kind"], "try")
        self.assertEqual(control["details"]["nesting_depth"], 1)
        calls = [node for node in parsed["nodes"] if node["kind"] == "call"]
        self.assertTrue(calls)
        self.assertTrue(all("used_as_with_context" in node["details"] for node in calls))
        function = next(node for node in parsed["nodes"] if node["kind"] == "function")
        self.assertEqual(function["details"]["signature"]["parameters"][1]["name"], "value")
        self.assertEqual(function["details"]["signature"]["returns"], "str")

    def test_syntax_error_has_location_and_no_nodes(self) -> None:
        parsed = parse_python_source("def broken(:\n    pass\n", "netbox/broken.py", "head")
        self.assertEqual(parsed["status"], "failed")
        self.assertEqual(parsed["error"]["code"], "syntax_error")
        self.assertIsNotNone(parsed["error"]["line"])
        self.assertEqual(parsed["nodes"], [])

    def test_node_ids_are_deterministic(self) -> None:
        source = "def f(value):\n    return value\n"
        first = parse_python_source(source, "netbox/example.py", "head")
        second = parse_python_source(source, "netbox/example.py", "head")
        self.assertEqual(first["nodes"], second["nodes"])


class StructureIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = make_temp_dir()
        self.repo = self.temp / "repo"
        self.repo.mkdir()
        run_git(self.repo, "init", "-b", "main")
        run_git(self.repo, "config", "user.name", "Prisk Test")
        run_git(self.repo, "config", "user.email", "prisk@example.invalid")
        (self.repo / "netbox").mkdir()
        (self.repo / "netbox" / "example.py").write_text(
            "class Example:\n    field = 1\n\n    def method(self, value):\n        return value\n",
            encoding="utf-8",
        )
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-m", "base")
        self.base = run_git(self.repo, "rev-parse", "HEAD")
        run_git(self.repo, "checkout", "-b", "feature")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp, ignore_errors=True)

    def _record(self, path: str = "netbox/example.py") -> dict:
        status_items = read_name_status(self.repo, self.base, self.head)
        diff_text = read_diff_text(self.repo, self.base, self.head)
        files = parse_unified_diff(diff_text, status_items)
        return {
            "schema_version": "stage03.v1",
            "status": "ok",
            "repo": "netbox-community/netbox",
            "pr_number": 19,
            "base_sha": self.base,
            "head_sha": self.head,
            "files": [item for item in files if item.get("new_path") == path or item.get("old_path") == path],
        }

    def test_maps_diff_to_structure_and_detects_signature(self) -> None:
        (self.repo / "netbox" / "example.py").write_text(
            "class Example:\n    field = 2\n\n    @decorator\n    def method(self, value, extra=1) -> int:\n        return call(value, extra)\n",
            encoding="utf-8",
        )
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-m", "feature")
        self.head = run_git(self.repo, "rev-parse", "HEAD")
        result = extract_changed_structures(self._record(), self.repo)
        self.assertEqual(result["status"], "ok")
        file_result = result["files"][0]
        self.assertEqual(file_result["parse_status"]["file"], "ok")
        self.assertTrue(file_result["nodes"])
        change_types = {item["type"] for item in file_result["structural_changes"]}
        self.assertIn("signature_changed", change_types)
        self.assertTrue(any(item["evidence_lines"] for item in file_result["structural_changes"]))

    def test_parse_failure_is_degraded_and_does_not_abort(self) -> None:
        (self.repo / "netbox" / "example.py").write_text(
            "def broken(:\n    pass\n",
            encoding="utf-8",
        )
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-m", "invalid")
        self.head = run_git(self.repo, "rev-parse", "HEAD")
        result = extract_changed_structures(self._record(), self.repo)
        file_result = result["files"][0]
        self.assertEqual(result["status"], "ok")
        self.assertEqual(file_result["parse_status"]["head"], "failed")
        self.assertEqual(file_result["parse_status"]["file"], "degraded")
        self.assertTrue(any(error["code"] == "syntax_error" for error in file_result["errors"]))

    def test_dataset_writes_manifest(self) -> None:
        (self.repo / "netbox" / "example.py").write_text(
            "class Example:\n    field = 2\n",
            encoding="utf-8",
        )
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-m", "feature")
        self.head = run_git(self.repo, "rev-parse", "HEAD")
        record = self._record()
        input_path = self.temp / "stage03.jsonl"
        output_path = self.temp / "stage04.jsonl"
        manifest_path = self.temp / "manifest.json"
        input_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        manifest = build_structure_dataset(input_path, self.repo, output_path, manifest_path)
        self.assertEqual(manifest["status_counts"], {"ok": 1})
        self.assertEqual(len(output_path.read_text(encoding="utf-8").splitlines()), 1)
        self.assertTrue(manifest_path.exists())


if __name__ == "__main__":
    unittest.main()
