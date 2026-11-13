"""Domain tests for Task 031 formal evaluation isolation, tri-state aggregation, annotations, and presets."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from prisk.domain.changes import build_from_jsonl, classify_path
from prisk.domain.config import PRESET_LEGACY_BASELINE
from prisk.domain.evaluation import (
    ANNOTATION_SCHEMA_VERSION,
    build_exclusion_payload,
    compare_preset_runs,
    evaluate_annotations,
    load_config_payload,
    load_exclusion_numbers_from_sources,
    render_empirical_report_markdown,
    score_stage05_record,
    summarize_stage05_outcomes,
    validate_annotation_records,
    verify_dataset_isolation,
)
from prisk.domain.rules import RULE_CATALOG, evaluate_rules
from prisk.domain.structure import build_structure_dataset, parse_python_source
from prisk.services.evaluation_service import (
    default_exclusion_list_path,
    default_pilot_manifest_path,
    default_survey_path,
)

DETECTION_SOURCE = """
def unsafe_handler(payload):
    try:
        payload.run()
    except:
        pass
"""

ZERO_HIT_SOURCE = """
def safe_helper(value):
    return len(value)
"""


def _git(repo_dir: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_dir), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return completed.stdout.strip()


def _parsed_file(source: str, path: str) -> dict:
    parsed = parse_python_source(source, path, "head")
    nodes = [
        {**node, "side": "head", "changed_lines": [node["start_line"]]}
        for node in parsed["nodes"]
        if node["kind"] != "module"
    ]
    return {
        "path": path,
        "role": classify_path(path, path_mode="generic"),
        "parse_status": {
            "base": "absent",
            "head": parsed["status"],
            "file": "ok" if parsed["status"] == "ok" else "degraded",
        },
        "nodes": nodes,
        "structural_changes": [],
        "errors": [parsed["error"]] if parsed["error"] else [],
        "status": "modified",
        "additions": 3,
        "deletions": 1,
        "binary": False,
    }


def _stage04_record(pr_number: int, files: list[dict], *, status: str = "ok", repo: str = "netbox-community/netbox") -> dict:
    return {
        "schema_version": "stage04.v1",
        "status": status,
        "repo": repo,
        "pr_number": pr_number,
        "files": files,
        "summary": {},
    }


class EvaluationDomainTests(unittest.TestCase):
    def test_real_exclusion_sources_contain_136_distinct_prs_and_match_artifact(self) -> None:
        summary = load_exclusion_numbers_from_sources(
            survey_path=default_survey_path(),
            pilot_manifest_path=default_pilot_manifest_path(),
            exclusion_json_path=default_exclusion_list_path(),
        )
        self.assertEqual(summary["count"], 136)
        self.assertEqual(len(summary["excluded_pr_numbers"]), 136)
        self.assertIn(19, summary["excluded_pr_numbers"])
        self.assertIn(23513, summary["excluded_pr_numbers"])
        self.assertIn(23175, summary["excluded_pr_numbers"])
        self.assertIn(23631, summary["excluded_pr_numbers"])

        built = build_exclusion_payload(
            survey_path=default_survey_path(),
            pilot_manifest_path=default_pilot_manifest_path(),
        )
        self.assertEqual(built["cross_source_overlap"], {})

    def test_verify_dataset_isolation_rejects_overlap_duplicate_bad_sha_and_bad_track(self) -> None:
        exclusion = load_exclusion_numbers_from_sources(
            exclusion_json_path=default_exclusion_list_path(),
        )["excluded_by_repo"]
        sha_a = "a" * 40
        sha_b = "b" * 40

        bad_records = [
            {"repo": "netbox-community/netbox", "pr_number": 19, "base_sha": sha_a, "head_sha": sha_b, "track": "track_a_random"},
            {"repo": "netbox-community/netbox", "pr_number": 23175, "base_sha": sha_a, "head_sha": sha_b, "track": "track_a_random"},
            {"repo": "netbox-community/netbox", "pr_number": 30001, "base_sha": sha_a, "head_sha": sha_b, "track": "track_a_random"},
            {"repo": "netbox-community/netbox", "pr_number": 30001, "base_sha": "bad", "head_sha": sha_b, "track": "unknown_track"},
            {"repo": "saleor/saleor", "pr_number": 19, "base_sha": sha_a, "head_sha": sha_b, "track": "external_control"},
        ]
        result = verify_dataset_isolation(
            bad_records,
            exclusion_by_repo=exclusion,
            require_sha=True,
            require_track=True,
        )
        self.assertFalse(result["ok"])
        self.assertEqual([item["pr_number"] for item in result["overlap_prs"]], [19, 23175])
        self.assertEqual(result["duplicate_prs"], [{"repo": "netbox-community/netbox", "pr_number": 30001}])
        reasons = {item["reason"] for item in result["invalid_records"]}
        self.assertIn("missing_or_invalid_sha", reasons)
        self.assertIn("invalid_track:unknown_track", reasons)

        with self.assertRaises(ValueError):
            verify_dataset_isolation(bad_records, exclusion_by_repo=exclusion, raise_on_error=True)

        clean_records = [
            {"repo": "netbox-community/netbox", "pr_number": 30002, "base_sha": sha_a, "head_sha": sha_b, "track": "track_a_random"},
            {"repo": "saleor/saleor", "pr_number": 19, "base_sha": sha_a, "head_sha": sha_b, "track": "external_control"},
        ]
        ok_result = verify_dataset_isolation(
            clean_records,
            exclusion_by_repo=exclusion,
            require_sha=True,
            require_track=True,
            raise_on_error=True,
        )
        self.assertTrue(ok_result["ok"])
        self.assertEqual(ok_result["by_track"], {"external_control": 1, "track_a_random": 1})

    def test_summarize_stage05_outcomes_and_gatekeeper_and_track_split(self) -> None:
        migration_src = "from django.db import migrations\nclass Migration(migrations.Migration):\n    operations = [migrations.DeleteModel(name='OldDevice')]\n"
        stage04_hit = _stage04_record(30010, [
            _parsed_file(DETECTION_SOURCE, "netbox/dcim/views.py"),
            _parsed_file(migration_src, "netbox/dcim/migrations/0009_cleanup.py"),
        ])
        stage04_zero = _stage04_record(30011, [_parsed_file(ZERO_HIT_SOURCE, "tests/test_helper.py")])
        stage04_bad = _stage04_record(30012, [_parsed_file("def broken(:\n", "netbox/dcim/bad.py")])
        stage04_excluded = _stage04_record(30013, [], status="excluded")

        r_hit = evaluate_rules(stage04_hit)
        r_hit["track"] = "track_b_targeted"
        r_zero = evaluate_rules(stage04_zero)
        r_zero["track"] = "track_a_random"
        r_bad = evaluate_rules(stage04_bad)
        r_bad["track"] = "track_a_random"
        r_excl = evaluate_rules(stage04_excluded)
        r_excl["track"] = "track_a_random"
        r_legacy = {
            "schema_version": "stage05.v2",
            "status": "ok",
            "repo": "netbox-community/netbox",
            "pr_number": 30014,
            "track": "track_a_random",
            "summary": {"test_collaboration": False},
            "findings": [{"rule_id": "api.signature_changed", "severity": "medium", "evidence": []}],
        }

        summary = summarize_stage05_outcomes(
            [r_hit, r_zero, r_bad, r_excl, r_legacy],
            stage04_records=[stage04_hit, stage04_zero, stage04_bad, stage04_excluded],
        )
        self.assertEqual(summary["total_prs"], 5)
        self.assertEqual(summary["ok_prs"], 4)
        self.assertEqual(summary["non_ok_prs"], 1)
        self.assertEqual(summary["outcomes_available_prs"], 4)
        self.assertEqual(summary["outcomes_unavailable_prs"], 1)
        self.assertEqual(summary["zero_hit_ok_prs"], 1)
        self.assertEqual(summary["gatekeeper_lift_prs"], 1)
        self.assertEqual(len(summary["per_rule"]), len(RULE_CATALOG))

        by_id = {row["rule_id"]: row for row in summary["per_rule"]}
        self.assertEqual(by_id["api.signature_changed"]["registry_lifecycle"], "historical_baseline")
        self.assertEqual(by_id["code.bare_exception"]["registry_lifecycle"], "implemented")
        self.assertEqual(by_id["code.bare_exception"]["hit_prs"], 1)
        self.assertEqual(by_id["data.django_destructive_migration"]["hit_prs"], 1)
        self.assertEqual(by_id["workflow.test_collaboration_gap"]["hit_prs"], 2)
        self.assertIn("syntax_error", summary["unanalyzed_reason_counts"])
        self.assertIn("prior_stage_unavailable", summary["unanalyzed_reason_counts"])
        self.assertEqual(sorted(summary["by_track"]), ["track_a_random", "track_b_targeted"])
        self.assertEqual(summary["by_track"]["track_b_targeted"]["gatekeeper_lift_prs"], 1)
        self.assertEqual(summary["by_track"]["track_a_random"]["gatekeeper_lift_prs"], 0)

    def test_evaluate_annotations_and_high_noise_detection(self) -> None:
        annotations = [
            {
                "schema_version": ANNOTATION_SCHEMA_VERSION,
                "repo": "netbox-community/netbox",
                "pr_number": 30101,
                "track": "track_a_random",
                "review_minutes": 6.0,
                "finding_judgments": [
                    {"rule_id": "code.global_mutable_state", "judgment": "false_looking_hit", "noise_pattern": "const_map"},
                    {"rule_id": "workflow.test_collaboration_gap", "judgment": "hit"},
                ],
            },
            {
                "schema_version": ANNOTATION_SCHEMA_VERSION,
                "repo": "netbox-community/netbox",
                "pr_number": 30102,
                "track": "track_a_random",
                "review_minutes": 8.0,
                "finding_judgments": [
                    {"rule_id": "code.global_mutable_state", "judgment": "false_looking_hit", "noise_pattern": "const_map"},
                    {"rule_id": "workflow.test_collaboration_gap", "judgment": "hit"},
                ],
            },
            {
                "schema_version": ANNOTATION_SCHEMA_VERSION,
                "repo": "netbox-community/netbox",
                "pr_number": 30103,
                "track": "track_b_targeted",
                "review_minutes": 10.0,
                "finding_judgments": [
                    {"rule_id": "code.global_mutable_state", "judgment": "false_looking_hit", "noise_pattern": "const_tuple"},
                    {"rule_id": "code.global_mutable_state", "judgment": "hit"},
                    {"rule_id": "workflow.test_collaboration_gap", "judgment": "hit"},
                    {"rule_id": "api.signature_changed", "judgment": "unanalyzed"},
                ],
            },
        ]
        report = evaluate_annotations(annotations)
        self.assertEqual(report["annotated_prs"], 3)
        self.assertEqual(report["review_minutes"], {"total": 24.0, "mean": 8.0, "median": 8.0, "min": 6.0, "max": 10.0})
        self.assertEqual(report["finding_totals"]["hit"], 4)
        self.assertEqual(report["finding_totals"]["false_looking_hit"], 3)
        self.assertAlmostEqual(report["finding_totals"]["empirical_precision"], round(4 / 7, 4))
        self.assertEqual([item["rule_id"] for item in report["high_noise_candidates"]], ["code.global_mutable_state"])
        self.assertEqual(sorted(report["by_track"]), ["track_a_random", "track_b_targeted"])

        with self.assertRaises(ValueError):
            validate_annotation_records([
                {**annotations[0], "finding_judgments": [{"rule_id": "x", "judgment": "invalid_state"}]},
            ])

    def test_compare_preset_runs_and_markdown_rendering(self) -> None:
        stage05 = [
            {
                "schema_version": "stage05.v2",
                "status": "ok",
                "repo": "netbox-community/netbox",
                "pr_number": 30201,
                "summary": {"test_collaboration": True},
                "findings": [
                    {"rule_id": "api.signature_changed", "severity": "medium", "evidence": []},
                    {"rule_id": "auth.drf_permission_policy_downgrade", "severity": "high", "evidence": []},
                ],
                "rule_outcomes": [],
            },
            {
                "schema_version": "stage05.v2",
                "status": "ok",
                "repo": "netbox-community/netbox",
                "pr_number": 30202,
                "summary": {"test_collaboration": False},
                "findings": [],
                "rule_outcomes": [],
            },
        ]
        legacy_score = score_stage05_record(stage05[0], {"preset": PRESET_LEGACY_BASELINE})
        self.assertEqual(legacy_score["risk_level"], "high")
        self.assertTrue(legacy_score["gatekeeper_applied"])

        custom_cfg = {"preset": "balanced", "rule_weights": {"api.signature_changed": 5}}
        comparison = compare_preset_runs(
            stage05,
            [
                ("legacy_baseline", {"preset": "legacy_baseline"}),
                ("balanced", {"preset": "balanced"}),
                ("custom_api", custom_cfg),
            ],
        )
        self.assertEqual(len(comparison["runs"]), 3)
        for run in comparison["runs"]:
            self.assertEqual(run["config_snapshot"]["schema_version"], "config.snapshot.v1")
            self.assertEqual(len(run["config_digest"]), 16)
            self.assertEqual(run["gatekeeper_lift_prs"], 1)

        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "custom.json"
            cfg_path.write_text(json.dumps({"rule_weights": {"api.signature_changed": 5}}), encoding="utf-8")
            loaded = load_config_payload(preset="balanced", config_path=cfg_path)
            self.assertEqual(loaded, {"preset": "balanced", "rule_weights": {"api.signature_changed": 5}})

        outcomes = summarize_stage05_outcomes(stage05)
        md = render_empirical_report_markdown({
            "outcomes": outcomes,
            "annotations": None,
            "preset_comparison": comparison,
        })
        self.assertIn("29 条规则三态命中与覆盖分布", md)
        self.assertIn("多配置预设对比", md)

    def test_generic_path_mode_enables_ast_extraction_for_non_netbox_repos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo_dir = tmp_path / "saleor_repo"
            repo_dir.mkdir()
            _git(repo_dir, "init")
            _git(repo_dir, "config", "user.name", "Prisk Test")
            _git(repo_dir, "config", "user.email", "test@prisk.local")

            order_view = repo_dir / "saleor" / "order" / "views.py"
            order_view.parent.mkdir(parents=True, exist_ok=True)
            order_view.write_text("def checkout(request):\n    return True\n", encoding="utf-8")
            _git(repo_dir, "add", "-A")
            _git(repo_dir, "commit", "-m", "base")
            base_sha = _git(repo_dir, "rev-parse", "HEAD")

            order_view.write_text("def checkout(request, coupon=None):\n    return coupon is not None\n", encoding="utf-8")
            _git(repo_dir, "add", "-A")
            _git(repo_dir, "commit", "-m", "head")
            head_sha = _git(repo_dir, "rev-parse", "HEAD")

            input_jsonl = tmp_path / "prs.jsonl"
            input_jsonl.write_text(
                json.dumps({
                    "repo": "saleor/saleor",
                    "pr_number": 9001,
                    "title": "Add coupon parameter",
                    "base_sha": base_sha,
                    "head_sha": head_sha,
                }) + "\n",
                encoding="utf-8",
            )

            netbox_s3 = tmp_path / "s3_netbox.jsonl"
            generic_s3 = tmp_path / "s3_generic.jsonl"
            generic_manifest = tmp_path / "s3_generic_manifest.json"
            m_netbox = build_from_jsonl(input_jsonl, repo_dir, netbox_s3)
            m_generic = build_from_jsonl(
                input_jsonl,
                repo_dir,
                generic_s3,
                generic_manifest,
                path_mode="generic",
                repo_name="saleor/saleor",
            )
            self.assertEqual(m_netbox["path_mode"], "netbox")
            self.assertEqual(m_generic["path_mode"], "generic")
            self.assertEqual(m_generic["repo"], "saleor/saleor")

            netbox_record = json.loads(netbox_s3.read_text(encoding="utf-8").strip())
            generic_record = json.loads(generic_s3.read_text(encoding="utf-8").strip())
            self.assertEqual(netbox_record["files"][0]["role"], "other")
            self.assertEqual(generic_record["files"][0]["role"], "business")

            s4_generic = tmp_path / "s4_generic.jsonl"
            s4_manifest = tmp_path / "s4_generic_manifest.json"
            struct_manifest = build_structure_dataset(generic_s3, repo_dir, s4_generic, s4_manifest)
            self.assertEqual(struct_manifest["repo"], "saleor/saleor")
            s4_rec = json.loads(s4_generic.read_text(encoding="utf-8").strip())
            self.assertEqual(s4_rec["files"][0]["parse_status"]["head"], "ok")


if __name__ == "__main__":
    unittest.main()
