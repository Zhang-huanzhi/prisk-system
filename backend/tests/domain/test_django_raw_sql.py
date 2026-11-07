"""Constructed cases for data.django_raw_sql_execution.

Hits are review clues. They are not injection findings, and the tests do not
treat SQL text as a safety signal.
"""

from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from prisk.domain.changes import parse_unified_diff, read_diff_text, read_name_status
from prisk.domain.rules import evaluate_rules
from prisk.domain.structure import extract_changed_structures, parse_python_source
from prisk.services.demo_service import collaboration_points, normalize_config, summed_rule_points
from tests.support import git, make_temp_dir


RULE_ID = "data.django_raw_sql_execution"
QUERY = "SELECT id FROM dcim_device WHERE name = %s"


def stage04_from_source(source: str, path: str) -> dict:
    parsed = parse_python_source(source, path, "head")
    nodes = []
    for node in parsed["nodes"]:
        if node["kind"] == "module":
            continue
        nodes.append({**node, "side": "head", "changed_lines": [node["start_line"]]})
    return {
        "schema_version": "stage04.v1",
        "status": "ok" if parsed["status"] == "ok" else "error",
        "repo": "example/example",
        "pr_number": 13,
        "files": [{
            "path": path,
            "role": "business",
            "parse_status": {
                "base": "absent",
                "head": parsed["status"],
                "file": "ok" if parsed["status"] == "ok" else "degraded",
            },
            "nodes": nodes,
            "structural_changes": [],
            "errors": [parsed["error"]] if parsed["error"] else [],
            "status": "modified",
            "additions": max(source.count("\n"), 1),
            "deletions": 0,
            "binary": False,
        }],
        "summary": {},
    }


def findings(result: dict) -> list[dict]:
    return [item for item in result["findings"] if item["rule_id"] == RULE_ID]


def outcome(result: dict) -> dict:
    return next(item for item in result["rule_outcomes"] if item["rule_id"] == RULE_ID)


def init_repo() -> tuple[Path, Path]:
    root = make_temp_dir("prisk-raw-sql-")
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Prisk Test")
    git(repo, "config", "user.email", "prisk@example.invalid")
    return root, repo


def commit(repo: Path, relative: str, source: str, message: str) -> str:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    git(repo, "add", relative)
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def evaluate_repo(repo: Path, base: str, head: str) -> dict:
    files = parse_unified_diff(read_diff_text(repo, base, head), read_name_status(repo, base, head))
    record = {
        "schema_version": "stage03.v1",
        "status": "ok",
        "repo": "example/example",
        "pr_number": 13,
        "base_sha": base,
        "head_sha": head,
        "files": files,
    }
    return evaluate_rules(extract_changed_structures(record, repo))


class DjangoRawSqlTests(unittest.TestCase):
    def test_cursor_execute_on_added_lines_hits_with_full_callee(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        view = "netbox/dcim/views.py"
        base = commit(
            repo,
            view,
            "def old(cursor):\n    cursor.execute('SELECT 1')\n\ndef listed(name):\n    return Device.objects.filter(name=name)\n",
            "base",
        )
        head = commit(
            repo,
            view,
            "def old(cursor):\n    cursor.execute('SELECT 1')\n\n"
            "def listed(name):\n    return Device.objects.filter(name=name)\n\n"
            "def added(cursor, name):\n"
            f"    cursor.execute(\"{QUERY}\", [name])\n",
            "add execute",
        )
        result = evaluate_repo(repo, base, head)
        matched = findings(result)
        self.assertEqual(len(matched), 1)
        evidence = matched[0]["evidence"][0]
        self.assertEqual(evidence["path"], view)
        self.assertEqual(evidence["callee"], "cursor.execute")
        self.assertNotEqual(evidence["callee"], "execute")
        self.assertNotIn(QUERY, matched[0]["message"])
        self.assertNotIn("sql", evidence)
        self.assertNotIn("sql_text", evidence)
        self.assertEqual(outcome(result)["state"], "Hit")
        self.assertIn("不表示已经存在注入", matched[0]["message"])

    def test_unchanged_execute_and_added_filter_are_not_found(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        view = "netbox/dcim/views.py"
        base = commit(
            repo,
            view,
            "def old(cursor):\n    cursor.execute('SELECT 1')\n",
            "base",
        )
        head = commit(
            repo,
            view,
            "def old(cursor):\n    cursor.execute('SELECT 1')\n\ndef listed(name):\n    return Device.objects.filter(name=name)\n",
            "add filter",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result), [])
        self.assertEqual(outcome(result)["state"], "NotFound")

    def test_orm_filter_exclude_and_update_are_not_found(self) -> None:
        source = (
            "def listed(name):\n"
            "    note = \"SELECT * FROM dcim_device\"\n"
            "    Device.objects.filter(name=name)\n"
            "    Device.objects.exclude(name=name)\n"
            "    Device.objects.update(name=name)\n"
        )
        result = evaluate_rules(stage04_from_source(source, "netbox/dcim/views.py"))
        self.assertEqual(findings(result), [])
        self.assertEqual(outcome(result)["state"], "NotFound")

    def test_sql_text_without_a_call_is_not_a_completed_miss(self) -> None:
        source = "note = \"SELECT * FROM dcim_device\"\n"
        result = evaluate_rules(stage04_from_source(source, "netbox/dcim/views.py"))
        self.assertEqual(findings(result), [])
        item = outcome(result)
        self.assertEqual(item["state"], "Unanalyzed")
        self.assertEqual(item["reasons"][0]["reason"], "context_not_established")

    def test_queryset_extra_callproc_and_schema_editor_are_unanalyzed(self) -> None:
        source = (
            "def boundary(qs, cursor, schema_editor):\n"
            "    qs.extra(where=[\"1=1\"])\n"
            "    cursor.callproc(\"refresh_device\", [])\n"
            "    schema_editor.execute(\"SELECT 1\")\n"
        )
        result = evaluate_rules(stage04_from_source(source, "netbox/dcim/views.py"))
        self.assertEqual(findings(result), [])
        item = outcome(result)
        self.assertEqual(item["state"], "Unanalyzed")
        self.assertEqual(item["reasons"][0]["reason"], "missing_framework_context")
        self.assertGreaterEqual(len(item["reasons"][0]["objects"]), 3)
        summary = [entry for entry in result["summary"]["unanalyzed"] if entry["reason"] == "missing_framework_context"]
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["path"], "netbox/dcim/views.py")
        self.assertGreaterEqual(len(summary[0]["node_ids"]), 3)

    def test_migration_execute_hits_with_the_same_closed_set(self) -> None:
        migration = (
            "def forwards(apps, schema_editor):\n"
            f"    cursor.execute(\"{QUERY}\", [])\n"
        )
        view = (
            "def added(cursor, name):\n"
            f"    cursor.execute(\"{QUERY}\", [name])\n"
        )
        migration_path = "netbox/dcim/migrations/0002_raw_sql.py"
        view_path = "netbox/dcim/views.py"
        record = stage04_from_source(migration, migration_path)
        view_record = stage04_from_source(view, view_path)
        record["files"].append(view_record["files"][0])
        result = evaluate_rules(record)
        matched = findings(result)
        self.assertEqual(
            sorted(item["evidence"][0]["path"] for item in matched),
            sorted([migration_path, view_path]),
        )
        self.assertTrue(all(item["evidence"][0]["callee"] == "cursor.execute" for item in matched))
        self.assertEqual(outcome(result)["state"], "Hit")

    def test_executemany_raw_and_direct_rawsql_each_hit_once(self) -> None:
        source = (
            "def write(cursor, rows):\n"
            "    cursor.executemany(\"INSERT INTO dcim_device VALUES (%s)\", rows)\n"
            "    Device.objects.raw(\"SELECT * FROM dcim_device\")\n"
            "    return RawSQL(\"SELECT 1\", [])\n"
        )
        result = evaluate_rules(stage04_from_source(source, "netbox/dcim/models.py"))
        matched = findings(result)
        self.assertEqual(
            sorted(item["evidence"][0]["callee"] for item in matched),
            ["Device.objects.raw", "RawSQL", "cursor.executemany"],
        )
        self.assertTrue(all(len(item["evidence"]) == 1 for item in matched))
        rawsql = next(item for item in matched if item["evidence"][0]["callee"] == "RawSQL")
        self.assertEqual(rawsql["evidence"][0]["direct_callee_name"], "RawSQL")
        self.assertEqual(outcome(result)["state"], "Hit")

    def test_runsql_alias_and_qualified_rawsql_do_not_hit(self) -> None:
        source = (
            "def change(cursor, migrations, expressions):\n"
            "    migrations.RunSQL(\"DELETE FROM dcim_device\")\n"
            "    run = cursor.execute\n"
            "    run(\"SELECT 1\")\n"
            "    return expressions.RawSQL(\"SELECT 1\", [])\n"
        )
        result = evaluate_rules(stage04_from_source(source, "netbox/dcim/migrations/0003_runsql.py"))
        self.assertEqual(findings(result), [])
        self.assertEqual(outcome(result)["state"], "NotFound")

    def test_report_execute_keeps_the_full_callee(self) -> None:
        source = "def publish(report):\n    report.execute(\"done\")\n"
        result = evaluate_rules(stage04_from_source(source, "netbox/core/reports.py"))
        matched = findings(result)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["evidence"][0]["callee"], "report.execute")
        self.assertIn("report.execute", matched[0]["message"])

    def test_empty_and_truncated_callees_are_unanalyzed(self) -> None:
        empty = {
            "kind": "call",
            "side": "head",
            "node_id": "head:call:empty:1",
            "changed_lines": [4],
            "start_line": 4,
            "end_line": 4,
            "details": {"callee": "", "direct_callee_name": None},
        }
        truncated = {
            "kind": "call",
            "side": "head",
            "node_id": "head:call:truncated:1",
            "changed_lines": [5],
            "start_line": 5,
            "end_line": 5,
            "source_segment": "cursor.exec",
            "source_segment_truncated": True,
            "details": {},
        }
        record = stage04_from_source("def listed(name):\n    return Device.objects.filter(name=name)\n", "netbox/dcim/views.py")
        record["files"][0]["nodes"].extend([empty, truncated])
        result = evaluate_rules(record)
        self.assertEqual(findings(result), [])
        item = outcome(result)
        self.assertEqual(item["state"], "Unanalyzed")
        self.assertEqual(item["reasons"][0]["reason"], "unsupported_stage04_details")
        node_ids = {obj["node_id"] for obj in item["reasons"][0]["objects"]}
        self.assertEqual(node_ids, {"head:call:empty:1", "head:call:truncated:1"})

    def test_execute_outside_added_lines_is_not_examined(self) -> None:
        source = (
            "def listed(name):\n"
            "    return Device.objects.filter(name=name)\n"
            "def old(cursor):\n"
            f"    cursor.execute(\"{QUERY}\", [name])\n"
        )
        record = stage04_from_source(source, "netbox/dcim/views.py")
        for node in record["files"][0]["nodes"]:
            callee = (node.get("details") or {}).get("callee") or ""
            if callee.endswith("execute"):
                node["changed_lines"] = []
        result = evaluate_rules(record)
        self.assertEqual(findings(result), [])
        self.assertEqual(outcome(result)["state"], "NotFound")

    def test_hit_does_not_raise_the_default_maximum(self) -> None:
        source = f"def added(cursor, name):\n    cursor.execute(\"{QUERY}\", [name])\n"
        result = evaluate_rules(stage04_from_source(source, "netbox/dcim/views.py"))
        self.assertEqual(outcome(result)["state"], "Hit")
        config = normalize_config(None)
        self.assertEqual(config["rule_weights"][RULE_ID], 0)
        found = {item["rule_id"] for item in result["findings"]}
        self.assertIn(RULE_ID, found)
        earned = summed_rule_points(found, config["rule_weights"])
        without = summed_rule_points(found - {RULE_ID}, config["rule_weights"])
        self.assertEqual(earned, without)
        maximum = summed_rule_points(config["enabled_rules"], config["rule_weights"])
        maximum += collaboration_points(config, True)[0]
        self.assertEqual(maximum, 10)

    def test_hit_keeps_framework_gap_visible_without_leaving_hit(self) -> None:
        source = (
            "def added(cursor, qs):\n"
            f"    cursor.execute(\"{QUERY}\", [])\n"
            "    qs.extra(where=[\"1=1\"])\n"
        )
        result = evaluate_rules(stage04_from_source(source, "netbox/dcim/views.py"))
        self.assertEqual(len(findings(result)), 1)
        self.assertEqual(outcome(result)["state"], "Hit")
        self.assertNotIn("reasons", outcome(result))
        reasons = {entry["reason"] for entry in result["summary"]["unanalyzed"]}
        self.assertIn("missing_framework_context", reasons)


if __name__ == "__main__":
    unittest.main()
