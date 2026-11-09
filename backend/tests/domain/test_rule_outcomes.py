"""Explicit Hit / NotFound / Unanalyzed outcomes for the runtime rules."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from prisk.domain.rules import RULE_CATALOG, evaluate_rules
from prisk.domain.structure import parse_python_source
from prisk.domain.test_collaboration import COLLABORATION_RULE_ID
from prisk.paths import demo_data_root
from prisk.services.demo_service import DemoData, collaboration_points, normalize_config, summed_rule_points


ZERO_HIT_SOURCE = """
def work(value):
    try:
        value.touch()
    except ValueError:
        raise
    return len(value)
"""

DETECTION_SOURCE = """
def view(payload):
    try:
        payload.load()
    except Exception:
        pass
    eval(payload.raw)
"""


def _states(result: dict) -> dict[str, str]:
    return {item["rule_id"]: item["state"] for item in result["rule_outcomes"]}


def _outcome(result: dict, rule_id: str) -> dict:
    return next(item for item in result["rule_outcomes"] if item["rule_id"] == rule_id)


def _parsed_file(source: str, path: str, changes: list[dict] | None = None) -> dict:
    parsed = parse_python_source(source, path, "head")
    nodes = []
    for node in parsed["nodes"]:
        if node["kind"] == "module":
            continue
        nodes.append({**node, "side": "head", "changed_lines": [node["start_line"]]})
    return {
        "path": path,
        "role": "test" if "/test" in f"/{path}" or path.split("/")[-1].startswith("test_") else "business",
        "parse_status": {
            "base": "absent",
            "head": parsed["status"],
            "file": "ok" if parsed["status"] == "ok" else "degraded",
        },
        "nodes": nodes,
        "structural_changes": [] if changes is None else changes,
        "errors": [parsed["error"]] if parsed["error"] else [],
        "status": "modified",
        "additions": 2,
        "deletions": 0,
        "binary": False,
    }


def _signature_change() -> dict:
    node = {
        "kind": "function",
        "node_id": "head:function:view:1",
        "name": "view",
        "qualified_name": "view",
        "changed_lines": [1],
        "details": {},
    }
    return {
        "type": "signature_changed",
        "kind": "function",
        "node_id": node["node_id"],
        "evidence_lines": [1],
        "after": node,
        "before": None,
    }


def _body_change() -> dict:
    change = _signature_change()
    change["type"] = "body_modified"
    return change


def _handler_change() -> dict:
    node = {
        "kind": "except_handler",
        "node_id": "head:except:view:1",
        "name": "Exception",
        "qualified_name": "view",
        "changed_lines": [4],
        "details": {"exception_type": "Exception"},
    }
    return {
        "type": "exception_handler_changed",
        "kind": "except_handler",
        "node_id": node["node_id"],
        "evidence_lines": [4],
        "after": node,
        "before": None,
    }


def _record(files: list[dict], **summary: object) -> dict:
    return {
        "schema_version": "stage04.v1",
        "status": "ok",
        "repo": "example/example",
        "pr_number": 9,
        "files": files,
        "summary": summary,
    }


class RuleOutcomeTests(unittest.TestCase):
    def assert_terminal_invariant(self, result: dict, enabled: list[str] | None = None) -> None:
        enabled_ids = enabled or [item["rule_id"] for item in RULE_CATALOG]
        outcomes = result["rule_outcomes"]
        self.assertEqual([item["rule_id"] for item in outcomes], enabled_ids)
        self.assertEqual(len(outcomes), len(set(enabled_ids)))
        finding_ids = {item["rule_id"] for item in result["findings"]}
        for item in outcomes:
            self.assertIn(item["state"], {"Hit", "NotFound", "Unanalyzed"})
            if item["state"] == "Hit":
                self.assertIn(item["rule_id"], finding_ids)
                self.assertNotIn("reasons", item)
            else:
                self.assertNotIn(item["rule_id"], finding_ids)
                if item["state"] == "Unanalyzed":
                    self.assertTrue(item["reasons"])
                    for reason in item["reasons"]:
                        self.assertIn("reason", reason)
                        self.assertIn("objects", reason)
                else:
                    self.assertNotIn("reasons", item)
        self.assertEqual(finding_ids, {item["rule_id"] for item in outcomes if item["state"] == "Hit"})

    def test_zero_hit_applicable_context_does_not_mark_every_rule_not_found(self) -> None:
        record = _record([
            _parsed_file(ZERO_HIT_SOURCE, "tests/test_work.py"),
            {
                "path": "netbox/dcim/api/views.py",
                "role": "business",
                "parse_status": {"head": "ok", "file": "ok"},
                "nodes": [],
                "structural_changes": [_body_change()],
                "errors": [],
                "status": "modified",
                "additions": 2,
                "deletions": 1,
                "binary": False,
            },
        ])
        result = evaluate_rules(record)
        self.assertEqual(result["schema_version"], "stage05.v2")
        self.assertEqual(result["findings"], [])
        self.assertFalse(result["summary"]["test_collaboration"])
        self.assert_terminal_invariant(result)
        states = _states(result)
        self.assertIn("NotFound", states.values())
        self.assertIn("Unanalyzed", states.values())
        self.assertNotEqual(list(states.values()), ["NotFound"] * len(states))
        for rule_id in (
            "code.swallowed_exception",
            "code.bare_exception",
            "code.dynamic_execution",
            "code.unmanaged_open",
            "code.deep_control_flow",
            "code.hardcoded_secret",
            "code.global_mutable_state",
            "api.signature_changed",
            "code.exception_structure_changed",
            "data.django_raw_sql_execution",
            COLLABORATION_RULE_ID,
        ):
            self.assertEqual(states[rule_id], "NotFound", rule_id)
        for rule_id in (
            "auth.permission_structure_changed",
            "data.transaction_structure_changed",
            "config.configuration_structure_changed",
        ):
            self.assertEqual(states[rule_id], "Unanalyzed", rule_id)
            self.assertEqual(_outcome(result, rule_id)["reasons"][0]["reason"], "missing_framework_context")
        config = normalize_config(None)
        maximum = summed_rule_points(config["enabled_rules"], config["rule_weights"])
        maximum += collaboration_points(config, False)[0]
        earned = summed_rule_points(set(), config["rule_weights"])
        self.assertEqual(maximum, 10)
        self.assertEqual(earned, 0)

    def test_actual_detection_is_hit_and_other_rules_stay_unanalyzed(self) -> None:
        production = _parsed_file(
            DETECTION_SOURCE,
            "netbox/dcim/api/views.py",
            [_signature_change(), _handler_change()],
        )
        result = evaluate_rules(_record([production]))
        self.assert_terminal_invariant(result)
        states = _states(result)
        for rule_id in (
            "api.signature_changed",
            "code.exception_structure_changed",
            "code.swallowed_exception",
            "code.bare_exception",
            "code.dynamic_execution",
            COLLABORATION_RULE_ID,
        ):
            self.assertEqual(states[rule_id], "Hit", rule_id)
        for rule_id in (
            "auth.permission_structure_changed",
            "data.transaction_structure_changed",
            "config.configuration_structure_changed",
        ):
            self.assertEqual(states[rule_id], "Unanalyzed", rule_id)
            self.assertEqual(_outcome(result, rule_id)["reasons"][0]["reason"], "missing_framework_context")
        self.assertNotIn("code.unmanaged_open", {item["rule_id"] for item in result["findings"]})
        for rule_id in (
            "code.unmanaged_open",
            "code.deep_control_flow",
            "code.hardcoded_secret",
            "code.global_mutable_state",
            "data.django_raw_sql_execution",
        ):
            self.assertEqual(states[rule_id], "NotFound", rule_id)
        config = normalize_config(None)
        found = {item["rule_id"] for item in result["findings"]}
        earned = summed_rule_points(found, config["rule_weights"])
        _maximum, collaboration_earned = collaboration_points(config, result["summary"]["test_collaboration"])
        self.assertEqual(config["rule_weights"]["code.swallowed_exception"], 0)
        self.assertEqual(config["rule_weights"]["code.dynamic_execution"], 0)
        self.assertEqual(earned, 2 + 1)
        self.assertEqual(collaboration_earned, 1)
        self.assertTrue(result["summary"]["test_collaboration"])
        maximum = summed_rule_points(config["enabled_rules"], config["rule_weights"]) + collaboration_points(config, True)[0]
        self.assertEqual(maximum, 10)

    def test_parse_failure_and_missing_details_stay_unanalyzed(self) -> None:
        degraded = evaluate_rules(_record([{
            "path": "netbox/bad.py",
            "role": "business",
            "parse_status": {"head": "failed", "file": "degraded"},
            "errors": [{"code": "syntax_error"}],
            "nodes": [],
            "structural_changes": [],
            "status": "modified",
            "additions": 1,
            "deletions": 0,
            "binary": False,
        }]))
        self.assert_terminal_invariant(degraded)
        self.assertEqual(degraded["summary"]["unanalyzed"], [{"path": "netbox/bad.py", "reason": "syntax_error"}])
        self.assertTrue(degraded["summary"]["parse_degraded"])
        states = _states(degraded)
        self.assertEqual(states[COLLABORATION_RULE_ID], "Hit")
        for rule_id in (
            "code.swallowed_exception",
            "code.bare_exception",
            "code.dynamic_execution",
            "code.unmanaged_open",
            "code.deep_control_flow",
            "code.hardcoded_secret",
            "code.global_mutable_state",
            "code.exception_structure_changed",
            "auth.permission_structure_changed",
            "data.transaction_structure_changed",
            "data.django_raw_sql_execution",
        ):
            self.assertEqual(states[rule_id], "Unanalyzed", rule_id)
            reasons = {item["reason"] for item in _outcome(degraded, rule_id)["reasons"]}
            self.assertIn("syntax_error", reasons)
        self.assertEqual(states["api.signature_changed"], "Unanalyzed")
        self.assertEqual(states["config.configuration_structure_changed"], "Unanalyzed")
        self.assertEqual(_outcome(degraded, "api.signature_changed")["reasons"][0]["reason"], "missing_framework_context")
        self.assertNotIn("NotFound", states.values())

        legacy = _parsed_file("def f():\n    try:\n        load()\n    except:\n        pass\n    eval('1')\n", "netbox/legacy.py")
        relevant = []
        for node in legacy["nodes"]:
            if node["kind"] in {"except_handler", "call"}:
                relevant.append(node["node_id"])
                node["details"] = {}
                node.pop("source_segment", None)
        missing = evaluate_rules(_record([legacy]))
        self.assert_terminal_invariant(missing)
        self.assertEqual(missing["summary"]["unanalyzed"][0]["reason"], "unsupported_stage04_details")
        for rule_id in ("code.swallowed_exception", "code.bare_exception", "code.dynamic_execution"):
            self.assertEqual(_states(missing)[rule_id], "Unanalyzed", rule_id)
            reasons = _outcome(missing, rule_id)["reasons"]
            self.assertEqual(reasons[0]["reason"], "unsupported_stage04_details")
            self.assertTrue(reasons[0]["objects"])
        self.assertNotEqual(_states(missing)["code.swallowed_exception"], "NotFound")

    def test_prior_stage_and_ast_only_channel_are_unanalyzed(self) -> None:
        excluded = evaluate_rules({"status": "excluded", "pr_number": 1})
        self.assertEqual(excluded["findings"], [])
        self.assertEqual(excluded["summary"]["unanalyzed"], [])
        self.assert_terminal_invariant(excluded)
        self.assertTrue(all(item["state"] == "Unanalyzed" for item in excluded["rule_outcomes"]))
        self.assertTrue(all(item["reasons"][0]["reason"] == "prior_stage_unavailable" for item in excluded["rule_outcomes"]))

        ast_only = _record([{"path": "netbox/core/models.py", "role": "business"}])
        result = evaluate_rules(ast_only)
        self.assertEqual(result["summary"]["unanalyzed"], [])
        self.assertFalse(result["summary"]["test_collaboration"])
        self.assertEqual(_states(result)[COLLABORATION_RULE_ID], "Unanalyzed")
        self.assertEqual(
            _outcome(result, COLLABORATION_RULE_ID)["reasons"][0]["reason"],
            "missing_file_change_channel",
        )
        self.assertNotIn("NotFound", _states(result).values())

    def test_disabled_rule_has_no_terminal_state(self) -> None:
        result = evaluate_rules(
            _record([_parsed_file(ZERO_HIT_SOURCE, "tests/test_work.py")]),
            {"enabled_rules": ["code.swallowed_exception"]},
        )
        self.assert_terminal_invariant(result, ["code.swallowed_exception"])
        self.assertEqual(result["summary"]["unanalyzed"], [])
        self.assertEqual(_states(result)["code.swallowed_exception"], "NotFound")

    def test_saved_demo_snapshot_does_not_invent_outcomes_or_change_score(self) -> None:
        root = demo_data_root()
        stage05 = root / "stage05-rule-results.jsonl"
        before = stage05.read_bytes()
        report = DemoData(
            root / "stage03-change-objects.jsonl",
            root / "stage04-structure-objects.jsonl",
            stage05,
        ).analyze(12)
        self.assertEqual(stage05.read_bytes(), before)
        stored = json.loads(before.decode("utf-8"))
        self.assertNotIn("rule_outcomes", stored)
        self.assertIsNone(report["rule_outcomes"])
        self.assertEqual(report["rule_outcome_availability"], "unavailable")
        self.assertEqual(report["score_basis"]["maximum_points"], 10)
        self.assertEqual(report["score_basis"]["earned_points"], 3)
        self.assertEqual(report["score"], 30)
        self.assertEqual([item["rule_id"] for item in report["findings"]], ["api.signature_changed"])
        self.assertEqual(report["score_basis"]["configuration"]["rule_weights"]["code.hardcoded_secret"], 0)
        self.assertEqual(report["score_basis"]["configuration"]["rule_weights"][COLLABORATION_RULE_ID], 1)
        blueprint = Path(__file__).resolve().parents[3] / "docs" / "blueprint.md"
        content = blueprint.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
        digest = hashlib.sha256(content).hexdigest()
        self.assertEqual(digest, "f0273030ec15fd0d8d87a767a37228b371d54a3f54b556f5e32c850f2454b817")


if __name__ == "__main__":
    unittest.main()
