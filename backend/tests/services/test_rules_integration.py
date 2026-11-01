from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from prisk.domain.rules import evaluate_dataset
from tests.support import make_temp_dir


class RuleIntegrationTests(unittest.TestCase):
    def test_dataset_continues_after_error_and_reports_evidence(self) -> None:
        root = make_temp_dir("prisk-rules-")
        try:
            source = root / "input.jsonl"
            output = root / "output.jsonl"
            manifest_path = root / "manifest.json"
            records = [
                {
                    "status": "ok",
                    "schema_version": "stage04.v1",
                    "pr_number": 1,
                    "repo": "netbox-community/netbox",
                    "summary": {"business_changed": True, "test_changed": False},
                    "files": [{
                        "path": "netbox/dcim/api/views.py",
                        "role": "business",
                        "parse_status": {"file": "ok"},
                        "structural_changes": [{
                            "type": "signature_changed",
                            "kind": "function",
                            "node_id": "head:function:api:1",
                            "evidence_lines": [10],
                            "after": {"kind": "function", "node_id": "head:function:api:1", "qualified_name": "api", "changed_lines": [10]},
                        }],
                    }],
                },
                {"status": "error", "pr_number": 2, "errors": [{"code": "git_show_error"}]},
            ]
            source.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")
            manifest = evaluate_dataset(source, output, manifest_path)
            results = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(manifest["status_counts"], {"error": 1, "ok": 1})
        self.assertEqual(results[0]["summary"]["finding_count"], 1)
        self.assertEqual(results[1]["status"], "error")
        self.assertEqual(manifest["evidence_completeness"], 1.0)


if __name__ == "__main__":
    unittest.main()
