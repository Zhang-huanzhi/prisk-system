"""CLI and service integration tests for Task 031 formal evaluation toolchain."""

from __future__ import annotations

import base64
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from prisk.cli.dataset_cli import main as dataset_main
from prisk.cli.eval_cli import main as eval_main
from prisk.cli.rules_cli import main as rules_main
from prisk.cli.scoring_cli import main as scoring_main
from prisk.cli.structure_cli import main as structure_main
from prisk.services.evaluation_service import materialize_two_commit_repo


def _encode_b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _build_mock_gh(repo: str = "saleor/saleor") -> Any:
    """Create a deterministic in-memory GitHub REST response stub for `sample` & `materialize`."""
    sha_base = "1" * 40
    sha_head = "2" * 40
    sha_merge = "3" * 40

    pr_catalog: dict[int, dict[str, Any]] = {
        19: {
            "number": 19,
            "title": "Historical v1.0 excluded PR",
            "html_url": f"https://github.com/{repo}/pull/19",
            "user": {"login": "alice", "type": "User"},
            "merged_at": "2023-05-01T00:00:00Z",
            "base": {"sha": sha_base},
            "head": {"sha": sha_head},
            "merge_commit_sha": sha_merge,
            "changed_files": 2,
            "additions": 10,
            "deletions": 2,
            "files": [{"filename": "app/views.py", "status": "modified"}],
        },
        401: {
            "number": 401,
            "title": "chore(deps): bump django",
            "html_url": f"https://github.com/{repo}/pull/401",
            "user": {"login": "dependabot[bot]", "type": "Bot"},
            "merged_at": "2023-05-02T00:00:00Z",
            "base": {"sha": sha_base},
            "head": {"sha": sha_head},
            "merge_commit_sha": sha_merge,
            "changed_files": 1,
            "additions": 2,
            "deletions": 2,
            "files": [{"filename": "pyproject.toml", "status": "modified"}],
        },
        402: {
            "number": 402,
            "title": "Release v4.2.0",
            "html_url": f"https://github.com/{repo}/pull/402",
            "user": {"login": "maintainer", "type": "User"},
            "merged_at": "2023-05-03T00:00:00Z",
            "base": {"sha": sha_base},
            "head": {"sha": sha_head},
            "merge_commit_sha": sha_merge,
            "changed_files": 3,
            "additions": 5,
            "deletions": 1,
            "files": [{"filename": "app/version.py", "status": "modified"}],
        },
        403: {
            "number": 403,
            "title": "Update README docs",
            "html_url": f"https://github.com/{repo}/pull/403",
            "user": {"login": "bob", "type": "User"},
            "merged_at": "2023-05-04T00:00:00Z",
            "base": {"sha": sha_base},
            "head": {"sha": sha_head},
            "merge_commit_sha": sha_merge,
            "changed_files": 1,
            "additions": 8,
            "deletions": 1,
            "files": [{"filename": "README.md", "status": "modified"}],
        },
        404: {
            "number": 404,
            "title": "Update checkout endpoint",
            "html_url": f"https://github.com/{repo}/pull/404",
            "user": {"login": "carol", "type": "User"},
            "merged_at": "2023-05-05T00:00:00Z",
            "base": {"sha": sha_base},
            "head": {"sha": sha_head},
            "merge_commit_sha": sha_merge,
            "changed_files": 2,
            "additions": 12,
            "deletions": 4,
            "files": [
                {"filename": "saleor/checkout/views.py", "status": "modified"},
                {"filename": "saleor/legacy_mod.py", "status": "renamed", "previous_filename": "saleor/old_mod.py"},
            ],
        },
        405: {
            "number": 405,
            "title": "Add large inventory sync",
            "html_url": f"https://github.com/{repo}/pull/405",
            "user": {"login": "dave", "type": "User"},
            "merged_at": "2023-05-06T00:00:00Z",
            "base": {"sha": sha_base},
            "head": {"sha": sha_head},
            "merge_commit_sha": sha_merge,
            "changed_files": 25,
            "additions": 120,
            "deletions": 10,
            "files": [{"filename": "saleor/inventory/service.py", "status": "added"}],
        },
    }

    contents: dict[tuple[str, str], str] = {
        ("saleor/checkout/views.py", sha_base): _encode_b64("def checkout(request):\n    return 1\n"),
        ("saleor/checkout/views.py", sha_merge): _encode_b64(
            "def checkout(request, coupon=None):\n    try:\n        return int(coupon or 0)\n    except:\n        pass\n"
        ),
        ("saleor/old_mod.py", sha_base): _encode_b64("A = 1\nB = 2\nC = 3\nD = 4\nVALUE = 1\n"),
        ("saleor/legacy_mod.py", sha_merge): _encode_b64("A = 1\nB = 2\nC = 3\nD = 4\nVALUE = 2\n"),
    }

    def runner(args: list[str]) -> Any:
        endpoint = args[1] if len(args) > 1 and args[0] == "api" else args[0]
        if endpoint.startswith("search/issues?"):
            return {"items": [{"number": n} for n in sorted(pr_catalog)]}
        for num, detail in pr_catalog.items():
            if endpoint == f"repos/{repo}/pulls/{num}":
                return detail
            if endpoint.startswith(f"repos/{repo}/pulls/{num}/files"):
                return detail["files"]
            if endpoint == f"repos/{repo}/commits/{sha_merge}":
                return {"sha": sha_merge, "parents": [{"sha": sha_base}]}
        if f"repos/{repo}/contents/" in endpoint:
            path_part, ref_part = endpoint.split("contents/", 1)[1].split("?ref=", 1)
            encoded = contents.get((path_part, ref_part))
            if encoded is None:
                raise RuntimeError(f"missing content for {path_part}@{ref_part}")
            return {"encoding": "base64", "content": encoded}
        raise RuntimeError(f"unexpected gh api call: {endpoint}")

    return runner


def _run_cli(func: Any, argv: list[str], **kwargs: Any) -> tuple[int, str, str]:
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        code = func(argv, **kwargs)
    return code, stdout_buf.getvalue(), stderr_buf.getvalue()


class EvalCliTests(unittest.TestCase):
    def test_sync_exclusion_check_and_isolation_gate(self) -> None:
        code, stdout, stderr = _run_cli(eval_main, ["sync-exclusion", "--check"])
        self.assertEqual(code, 0, stderr)
        payload = json.loads(stdout)
        self.assertEqual(payload["count"], 136)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            overlap_file = tmp_path / "bad.jsonl"
            overlap_file.write_text(
                json.dumps({
                    "repo": "netbox-community/netbox",
                    "pr_number": 23175,
                    "track": "track_a_random",
                    "base_sha": "a" * 40,
                    "head_sha": "b" * 40,
                }) + "\n",
                encoding="utf-8",
            )
            bad_code, bad_stdout, _ = _run_cli(eval_main, ["check-isolation", str(overlap_file), "--require-track"])
            self.assertEqual(bad_code, 1)
            self.assertFalse(json.loads(bad_stdout)["ok"])

            clean_a = tmp_path / "track_a.jsonl"
            clean_b = tmp_path / "track_b.jsonl"
            clean_a.write_text(
                json.dumps({
                    "repo": "netbox-community/netbox",
                    "pr_number": 31001,
                    "track": "track_a_random",
                    "base_sha": "a" * 40,
                    "head_sha": "b" * 40,
                }) + "\n",
                encoding="utf-8",
            )
            clean_b.write_text(
                json.dumps({
                    "repo": "netbox-community/netbox",
                    "pr_number": 31001,
                    "track": "track_b_targeted",
                    "base_sha": "a" * 40,
                    "head_sha": "b" * 40,
                }) + "\n",
                encoding="utf-8",
            )
            ok_code, ok_stdout, _ = _run_cli(eval_main, ["check-isolation", str(clean_a), "--require-track"])
            self.assertEqual(ok_code, 0)
            self.assertTrue(json.loads(ok_stdout)["ok"])

            # Cross-file duplicate PR number between Track A and Track B must be rejected.
            dup_code, dup_stdout, _ = _run_cli(eval_main, ["check-isolation", str(clean_a), str(clean_b), "--require-track"])
            self.assertEqual(dup_code, 1)
            self.assertFalse(json.loads(dup_stdout)["ok"])

    def test_sample_dry_run_and_write_with_mock_gh_and_exclude_from(self) -> None:
        stub = _build_mock_gh("netbox-community/netbox")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out_jsonl = tmp_path / "track_a.jsonl"
            out_manifest = tmp_path / "track_a_manifest.json"
            dry_code, dry_out, dry_err = _run_cli(
                eval_main,
                [
                    "sample",
                    "--repo", "netbox-community/netbox",
                    "--track", "track_a_random",
                    "--count", "2",
                    "--window", "2023-01-01..2023-12-31",
                    "--dry-run",
                    "--output", str(out_jsonl),
                ],
                gh_runner=stub,
            )
            self.assertEqual(dry_code, 0, dry_err)
            dry_payload = json.loads(dry_out)
            self.assertTrue(dry_payload["dry_run"])
            self.assertEqual(dry_payload["preview_pr_numbers"], [404, 405])
            self.assertFalse(out_jsonl.exists())

            write_code, write_out, write_err = _run_cli(
                eval_main,
                [
                    "sample",
                    "--repo", "netbox-community/netbox",
                    "--track", "track_a_random",
                    "--count", "1",
                    "--window", "2023-01-01..2023-12-31",
                    "--output", str(out_jsonl),
                    "--manifest", str(out_manifest),
                ],
                gh_runner=stub,
            )
            self.assertEqual(write_code, 0, write_err)
            manifest = json.loads(out_manifest.read_text(encoding="utf-8"))
            self.assertEqual(manifest["selected_count"], 1)
            self.assertTrue(manifest["isolation"]["ok"])
            first_selected = json.loads(out_jsonl.read_text(encoding="utf-8").strip())["pr_number"]

            # Track B excluding Track A picks the remaining eligible PR without overlap.
            track_b_jsonl = tmp_path / "track_b.jsonl"
            b_code, _, b_err = _run_cli(
                eval_main,
                [
                    "sample",
                    "--repo", "netbox-community/netbox",
                    "--track", "track_b_targeted",
                    "--term", "checkout",
                    "--count", "2",
                    "--window", "2023-01-01..2023-12-31",
                    "--exclude-from", str(out_jsonl),
                    "--output", str(track_b_jsonl),
                ],
                gh_runner=stub,
            )
            self.assertEqual(b_code, 0, b_err)
            b_numbers = [json.loads(line)["pr_number"] for line in track_b_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertNotIn(first_selected, b_numbers)
            self.assertEqual(len(b_numbers), 1)

    def test_materialize_two_commit_and_end_to_end_pipeline_with_preset_and_aggregation(self) -> None:
        stub = _build_mock_gh("saleor/saleor")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mat = materialize_two_commit_repo(
                repo="saleor/saleor",
                pr_number=404,
                workspace_dir=tmp_path / "repos",
                gh_runner=stub,
            )
            self.assertEqual(mat["expected_files"], 2)
            self.assertEqual(mat["materialized_diff_files"], 2)

            repo_dir = Path(mat["repo_dir"])
            dataset_jsonl = tmp_path / "dataset.jsonl"
            dataset_jsonl.write_text(
                json.dumps({
                    "repo": "saleor/saleor",
                    "pr_number": 404,
                    "track": "external_control",
                    "title": "Update checkout endpoint",
                    "base_sha": mat["base_sha"],
                    "head_sha": mat["head_sha"],
                }) + "\n",
                encoding="utf-8",
            )

            s3_jsonl = tmp_path / "stage03.jsonl"
            s3_manifest = tmp_path / "stage03_manifest.json"
            s4_jsonl = tmp_path / "stage04.jsonl"
            s4_manifest = tmp_path / "stage04_manifest.json"
            s5_jsonl = tmp_path / "stage05.jsonl"
            s5_manifest = tmp_path / "stage05_manifest.json"
            s7_jsonl = tmp_path / "stage07.jsonl"
            s7_manifest = tmp_path / "stage07_manifest.json"

            c3, _, e3 = _run_cli(
                dataset_main,
                [
                    "--input", str(dataset_jsonl),
                    "--repo", str(repo_dir),
                    "--output", str(s3_jsonl),
                    "--manifest", str(s3_manifest),
                    "--path-mode", "generic",
                    "--repo-name", "saleor/saleor",
                ],
            )
            self.assertEqual(c3, 0, e3)
            self.assertEqual(json.loads(s3_manifest.read_text(encoding="utf-8"))["path_mode"], "generic")

            c4, _, e4 = _run_cli(
                structure_main,
                ["--input", str(s3_jsonl), "--repo", str(repo_dir), "--output", str(s4_jsonl), "--manifest", str(s4_manifest)],
            )
            self.assertEqual(c4, 0, e4)

            c5, _, e5 = _run_cli(
                rules_main,
                ["--input", str(s4_jsonl), "--output", str(s5_jsonl), "--manifest", str(s5_manifest), "--preset", "balanced"],
            )
            self.assertEqual(c5, 0, e5)
            m5 = json.loads(s5_manifest.read_text(encoding="utf-8"))
            self.assertEqual(m5["config_snapshot"]["preset"], "balanced")

            c7, _, e7 = _run_cli(
                scoring_main,
                [
                    "--stage03", str(s3_jsonl),
                    "--stage04", str(s4_jsonl),
                    "--stage05", str(s5_jsonl),
                    "--output", str(s7_jsonl),
                    "--manifest", str(s7_manifest),
                    "--preset", "balanced",
                ],
            )
            self.assertEqual(c7, 0, e7)
            m7 = json.loads(s7_manifest.read_text(encoding="utf-8"))
            self.assertEqual(m7["config_snapshot"]["preset"], "balanced")
            report_row = json.loads(s7_jsonl.read_text(encoding="utf-8").strip())
            self.assertEqual(report_row["score_basis"]["configuration"]["preset"], "balanced")

            annotations_jsonl = tmp_path / "annotations.jsonl"
            annotations_jsonl.write_text(
                json.dumps({
                    "schema_version": "prisk.eval.annotation.v1",
                    "repo": "saleor/saleor",
                    "pr_number": 404,
                    "track": "external_control",
                    "review_minutes": 5.5,
                    "finding_judgments": [
                        {"rule_id": "code.bare_exception", "judgment": "hit"},
                    ],
                }) + "\n",
                encoding="utf-8",
            )
            agg_json = tmp_path / "report.json"
            agg_md = tmp_path / "report.md"
            ca, _, ea = _run_cli(
                eval_main,
                [
                    "aggregate",
                    "--stage05", str(s5_jsonl),
                    "--stage04", str(s4_jsonl),
                    "--dataset", str(dataset_jsonl),
                    "--annotations", str(annotations_jsonl),
                    "--preset", "legacy_baseline",
                    "--preset", "balanced",
                    "--json-output", str(agg_json),
                    "--markdown-output", str(agg_md),
                ],
            )
            self.assertEqual(ca, 0, ea)
            agg_data = json.loads(agg_json.read_text(encoding="utf-8"))
            self.assertIn("external_control", agg_data["outcomes"]["by_track"])
            self.assertEqual(agg_data["annotations"]["finding_totals"]["empirical_precision"], 1.0)
            self.assertEqual(len(agg_data["preset_comparison"]["runs"]), 2)
            self.assertIn("code.bare_exception", agg_md.read_text(encoding="utf-8"))

            cmp_json = tmp_path / "compare.json"
            cc, _, ec = _run_cli(
                eval_main,
                ["compare-presets", "--stage05", str(s5_jsonl), "--stage04", str(s4_jsonl), "--json-output", str(cmp_json)],
            )
            self.assertEqual(cc, 0, ec)
            self.assertEqual(len(json.loads(cmp_json.read_text(encoding="utf-8"))["runs"]), 5)


if __name__ == "__main__":
    unittest.main()
