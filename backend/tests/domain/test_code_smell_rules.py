from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from prisk.domain.changes import parse_unified_diff, read_diff_text, read_name_status
from prisk.domain.rules import evaluate_rules
from prisk.services.branch_analysis import analyze_branches
from prisk.domain.structure import extract_changed_structures, parse_python_source
from tests.support import git, make_temp_dir


SAMPLE = """
def swallowed_value_error():
    try:
        load()
    except ValueError:
        pass

def swallowed_logged():
    try:
        load()
    except ValueError:
        logger.exception("load failed")
        raise

def double_pass():
    try:
        load()
    except ValueError:
        pass
        pass

def ellipsis_handler():
    try:
        load()
    except ValueError:
        ...

def bare_pass():
    try:
        run()
    except:
        pass

def bare_with_work():
    try:
        run()
    except:
        logger.exception("failed")

def except_exception():
    try:
        run()
    except Exception:
        logger.exception("failed")
        raise

def except_base():
    try:
        run()
    except BaseException:
        return None

def except_exception_as_name():
    try:
        run()
    except Exception as error:
        recover(error)

def specific_value_error():
    try:
        run()
    except ValueError:
        recover()

def tuple_exception():
    try:
        run()
    except (ValueError, Exception):
        recover()

def nested_tuple():
    try:
        run()
    except (OSError, (BaseException, ValueError)):
        recover()

def both_broad():
    try:
        run()
    except (Exception, BaseException):
        recover()

def tuple_specific():
    try:
        run()
    except (ValueError, OSError):
        recover()

def bool_op():
    try:
        run()
    except Exception or OSError:
        recover()

def nested_handlers():
    try:
        try:
            load()
        except ValueError:
            pass
    except Exception:
        logger.exception("outer")

def shadowed():
    Exception = ValueError
    try:
        run()
    except Exception:
        recover()

def attribute_exception():
    try:
        run()
    except builtins.Exception:
        recover()

def direct_calls(expression, source):
    result = eval(expression)
    exec(source)
    return (eval)(expression)

def excluded_calls(expression, source, obj, builtins):
    result = ast.literal_eval(expression)
    compiled = compile(source, "<string>", "exec")
    text = "eval(source)"
    # eval(source)
    obj.eval()
    run = eval
    run(source)
    return builtins.eval(source)

def grouped():
    try:
        run()
    except* Exception:
        pass
"""


def stage04_from_source(source: str, path: str = "netbox/sample.py") -> dict:
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
        "pr_number": 4,
        "files": [{
            "path": path,
            "role": "business",
            "parse_status": {"base": "absent", "head": parsed["status"], "file": "ok" if parsed["status"] == "ok" else "degraded"},
            "nodes": nodes,
            "structural_changes": [],
            "errors": [parsed["error"]] if parsed["error"] else [],
        }],
        "summary": {},
    }


def findings_for(rule_id: str, result: dict) -> list[dict]:
    return [item for item in result["findings"] if item["rule_id"] == rule_id]


def init_repo() -> tuple[Path, Path]:
    root = make_temp_dir("prisk-smell-")
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Prisk Test")
    git(repo, "config", "user.email", "prisk@example.invalid")
    (repo / "netbox").mkdir()
    return root, repo


def commit(repo: Path, relative: str, source: str, message: str) -> str:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    git(repo, "add", relative)
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def evaluate_repo(repo: Path, base: str, head: str) -> tuple[dict, dict]:
    files = parse_unified_diff(read_diff_text(repo, base, head), read_name_status(repo, base, head))
    record = {
        "schema_version": "stage03.v1",
        "status": "ok",
        "repo": "example/example",
        "pr_number": 4,
        "base_sha": base,
        "head_sha": head,
        "files": files,
    }
    structure = extract_changed_structures(record, repo)
    return structure, evaluate_rules(structure)


class CodeSmellRuleTests(unittest.TestCase):
    def test_node_details_distinguish_handlers_and_direct_calls(self) -> None:
        parsed = parse_python_source(SAMPLE, "netbox/sample.py", "head")
        self.assertEqual(parsed["status"], "ok")
        handlers = [node for node in parsed["nodes"] if node["kind"] == "except_handler"]
        bare = next(node for node in handlers if node["details"]["handler_type_names"] == ["bare"])
        self.assertTrue(bare["details"]["handler_body_is_single_pass"])
        self.assertTrue(bare["details"]["ordinary_handler"])
        grouped = next(node for node in handlers if node["details"]["ordinary_handler"] is False)
        self.assertEqual(grouped["details"]["handler_type_names"], ["Exception"])
        self.assertTrue(grouped["details"]["handler_body_is_single_pass"])
        calls = [node for node in parsed["nodes"] if node["kind"] == "call"]
        direct = {node["details"]["direct_callee_name"] for node in calls}
        self.assertIn("eval", direct)
        self.assertIn("exec", direct)
        self.assertIn("compile", direct)
        self.assertIn(None, direct)

    def test_positive_negative_nested_and_tuple_cases(self) -> None:
        result = evaluate_rules(stage04_from_source(SAMPLE))
        swallowed = findings_for("code.swallowed_exception", result)
        bare = findings_for("code.bare_exception", result)
        dynamic = findings_for("code.dynamic_execution", result)
        self.assertEqual(len(swallowed), 3)
        self.assertEqual(len(bare), 10)
        self.assertEqual(len(dynamic), 3)
        self.assertEqual(
            sorted(item["evidence"][0]["capture_form"] for item in bare),
            ["BaseException", "BaseException", "Exception", "Exception", "Exception", "Exception", "Exception", "Exception,BaseException", "bare", "bare"],
        )
        self.assertEqual(sorted(item["evidence"][0]["callee_name"] for item in dynamic), ["eval", "eval", "exec"])
        self.assertTrue(all(item["evidence"][0]["callee_name"] != "compile" for item in dynamic))
        self.assertTrue(all("literal_eval" not in item["message"] for item in dynamic))
        both = next(item for item in bare if item["evidence"][0]["capture_form"] == "Exception,BaseException")
        self.assertEqual(len(both["evidence"]), 1)
        self.assertIn("后果并不相同", both["message"])

    def test_bare_and_exception_messages_stay_distinct(self) -> None:
        result = evaluate_rules(stage04_from_source(SAMPLE))
        messages = {item["evidence"][0]["capture_form"]: item["message"] for item in findings_for("code.bare_exception", result)}
        self.assertIn("会捕获 KeyboardInterrupt", messages["bare"])
        self.assertIn("不会捕获 KeyboardInterrupt", messages["Exception"])
        self.assertIn("会捕获 KeyboardInterrupt", messages["BaseException"])
        self.assertNotEqual(messages["bare"], messages["Exception"])
        self.assertNotEqual(messages["Exception"], messages["BaseException"])
        swallowed = findings_for("code.swallowed_exception", result)[0]
        self.assertIn("只有 pass", swallowed["message"])
        self.assertNotEqual(swallowed["message"], messages["bare"])

    def test_same_handler_reports_swallowed_and_bare_separately(self) -> None:
        result = evaluate_rules(stage04_from_source(SAMPLE))
        by_node: dict[str, set[str]] = {}
        for item in result["findings"]:
            if item["rule_id"] in {"code.swallowed_exception", "code.bare_exception"}:
                by_node.setdefault(item["evidence"][0]["node_id"], set()).add(item["rule_id"])
        self.assertIn({"code.swallowed_exception", "code.bare_exception"}, by_node.values())

    def test_legacy_details_fall_back_to_source_segment(self) -> None:
        record = stage04_from_source("def f():\n    try:\n        load()\n    except:\n        pass\n    value = ast.literal_eval('1')\n    eval('1')\n")
        for node in record["files"][0]["nodes"]:
            segment = node.get("source_segment")
            if node["kind"] == "call" and isinstance(segment, str):
                callee = "eval" if segment.startswith("eval") else "ast.literal_eval" if "literal_eval" in segment else "load"
                node["details"] = {"callee": callee, "args_count": 1, "keyword_names": []}
            elif node["kind"] == "except_handler":
                node["details"] = {"exception_type": None, "bound_name": None}
            else:
                node["details"] = {}
        result = evaluate_rules(record)
        self.assertEqual(result["summary"]["unanalyzed"], [])
        self.assertEqual(len(findings_for("code.swallowed_exception", result)), 1)
        self.assertEqual([item["evidence"][0]["capture_form"] for item in findings_for("code.bare_exception", result)], ["bare"])
        self.assertEqual([item["evidence"][0]["callee_name"] for item in findings_for("code.dynamic_execution", result)], ["eval"])

    def test_legacy_nodes_without_details_or_source_are_unanalyzed(self) -> None:
        record = stage04_from_source("def f():\n    try:\n        load()\n    except:\n        pass\n    eval('1')\n")
        relevant = []
        for node in record["files"][0]["nodes"]:
            if node["kind"] in {"except_handler", "call"}:
                relevant.append(node["node_id"])
                node["details"] = {}
                node.pop("source_segment", None)
        result = evaluate_rules(record)
        self.assertEqual(findings_for("code.swallowed_exception", result), [])
        self.assertEqual(findings_for("code.bare_exception", result), [])
        self.assertEqual(findings_for("code.dynamic_execution", result), [])
        self.assertEqual(result["summary"]["unanalyzed"], [{
            "path": "netbox/sample.py",
            "reason": "unsupported_stage04_details",
            "node_ids": sorted(relevant),
        }])
        self.assertEqual(result["status"], "ok")

    def test_legacy_segment_preserves_tuple_and_skips_exception_group(self) -> None:
        def node(kind: str, node_id: str, segment: str, details: dict) -> dict:
            return {
                "kind": kind,
                "side": "head",
                "node_id": node_id,
                "changed_lines": [1],
                "start_line": 1,
                "end_line": 2,
                "source_segment": segment,
                "details": details,
            }
        record = {
            "schema_version": "stage04.v1",
            "status": "ok",
            "pr_number": 4,
            "files": [{
                "path": "netbox/legacy.py",
                "parse_status": {"head": "ok", "file": "ok"},
                "structural_changes": [],
                "errors": [],
                "nodes": [
                    node("except_handler", "tuple", "except (OSError, (BaseException, ValueError)):\n    recover()", {"exception_type": "(OSError, (BaseException, ValueError))"}),
                    node("except_handler", "group", "except* Exception:\n    pass", {"exception_type": "Exception"}),
                    node("call", "compile-call", "compile('1', '<string>', 'exec')", {"callee": "compile"}),
                ],
            }],
            "summary": {},
        }
        result = evaluate_rules(record)
        self.assertEqual(result["summary"]["unanalyzed"], [])
        self.assertEqual(findings_for("code.swallowed_exception", result), [])
        self.assertEqual(findings_for("code.dynamic_execution", result), [])
        bare = findings_for("code.bare_exception", result)
        self.assertEqual(len(bare), 1)
        self.assertEqual(bare[0]["evidence"][0]["capture_form"], "BaseException")
        self.assertEqual(bare[0]["evidence"][0]["node_id"], "tuple")

    def test_unevaluable_call_is_ignored_when_dynamic_rule_is_disabled(self) -> None:
        record = {
            "schema_version": "stage04.v1",
            "status": "ok",
            "pr_number": 4,
            "files": [{
                "path": "netbox/legacy.py",
                "parse_status": {"head": "ok", "file": "ok"},
                "nodes": [{
                    "kind": "call",
                    "side": "head",
                    "node_id": "old-call",
                    "changed_lines": [1],
                    "start_line": 1,
                    "end_line": 1,
                    "details": {},
                }],
                "structural_changes": [],
                "errors": [],
            }],
            "summary": {},
        }
        result = evaluate_rules(record, {"enabled_rules": ["code.swallowed_exception", "code.bare_exception"]})
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["summary"]["unanalyzed"], [])

    def test_disabled_rules_emit_nothing(self) -> None:
        result = evaluate_rules(stage04_from_source(SAMPLE), {"enabled_rules": ["code.exception_structure_changed"]})
        self.assertEqual(
            {item["rule_id"] for item in result["findings"]},
            set(),
        )

    def test_findings_are_review_signals(self) -> None:
        result = evaluate_rules(stage04_from_source(SAMPLE))
        for item in result["findings"]:
            self.assertEqual(item["confidence"], "structural")
            self.assertEqual(item["impact_type"], "pr_intrinsic_risk")
            self.assertNotIn("概率", item["message"])
            self.assertNotIn("precision", item["message"].lower())
            self.assertNotIn("recall", item["message"].lower())
            evidence = item["evidence"][0]
            self.assertTrue(evidence["path"])
            self.assertTrue(evidence["node_id"])
            self.assertTrue(evidence["lines"])
            self.assertNotIn("scene", item)
            self.assertEqual(evidence["source_status"], "available")
            self.assertTrue(evidence["source_segment"])
            self.assertEqual(evidence["after"]["status"], "available")
            self.assertEqual(evidence["after"]["source_segment"], evidence["source_segment"])
            self.assertEqual(evidence["before"], {"status": "unavailable", "reason": "no_base_node", "source_segment": None})
            self.assertIsNone(evidence["before"]["source_segment"])

    def test_pipeline_uses_added_lines_and_excludes_compile(self) -> None:
        root, repo = init_repo()
        try:
            base = commit(repo, "netbox/sample.py", "def edited():\n    return 1\n", "base")
            head = commit(
                repo,
                "netbox/sample.py",
                "def signals():\n"
                "    try:\n"
                "        load()\n"
                "    except ValueError:\n"
                "        pass\n"
                "    try:\n"
                "        run()\n"
                "    except Exception:\n"
                "        logger.exception('failed')\n"
                "        raise\n"
                "    value = eval('1')\n"
                "    other = compile('1', '<string>', 'eval')\n"
                "    literal = ast.literal_eval('1')\n",
                "head",
            )
            _structure, result = evaluate_repo(repo, base, head)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(len(findings_for("code.swallowed_exception", result)), 1)
        bare = findings_for("code.bare_exception", result)
        self.assertEqual([item["evidence"][0]["capture_form"] for item in bare], ["Exception"])
        dynamic = findings_for("code.dynamic_execution", result)
        self.assertEqual([item["evidence"][0]["callee_name"] for item in dynamic], ["eval"])
        raw = dynamic[0]["evidence"][0]
        self.assertEqual(raw["source_status"], "available")
        self.assertIn("eval", raw["source_segment"])
        self.assertEqual(raw["before"]["status"], "unavailable")
        self.assertEqual(raw["before"]["reason"], "no_base_node")
        self.assertIsNone(raw["before"]["source_segment"])
        self.assertEqual(result["summary"]["unanalyzed"], [])
        self.assertFalse(result["summary"]["parse_degraded"])

    def test_unchanged_handlers_and_calls_do_not_trigger(self) -> None:
        base_source = (
            "def kept():\n"
            "    try:\n"
            "        load()\n"
            "    except ValueError:\n"
            "        pass\n"
            "    value = eval('1')\n"
            "\n"
            "def edited():\n"
            "    return 1\n"
        )
        cases = {
            "other function": base_source.replace("return 1", "return 2"),
            "try line only": base_source.replace("    try:\n", "    try:  # touched\n", 1),
        }
        for name, head_source in cases.items():
            with self.subTest(name=name):
                root, repo = init_repo()
                try:
                    base = commit(repo, "netbox/sample.py", base_source, "base")
                    head = commit(repo, "netbox/sample.py", head_source, "head")
                    _structure, result = evaluate_repo(repo, base, head)
                finally:
                    shutil.rmtree(root, ignore_errors=True)
                smell_ids = {item["rule_id"] for item in result["findings"] if item["rule_id"].startswith("code.") and item["rule_id"] != "code.exception_structure_changed"}
                self.assertEqual(smell_ids, set(), name)

    def test_changed_handler_header_or_call_line_triggers_only_that_node(self) -> None:
        base_source = (
            "def kept():\n"
            "    try:\n"
            "        load()\n"
            "    except ValueError:\n"
            "        pass\n"
            "    value = eval('1')\n"
            "\n"
            "def edited():\n"
            "    return 1\n"
        )
        root, repo = init_repo()
        try:
            base = commit(repo, "netbox/sample.py", base_source, "base")
            header = commit(
                repo,
                "netbox/sample.py",
                base_source.replace("    except ValueError:\n", "    except ValueError:  # touched\n"),
                "header",
            )
            _structure, header_result = evaluate_repo(repo, base, header)
            call = commit(
                repo,
                "netbox/sample.py",
                base_source.replace("value = eval('1')", "value = eval('2')"),
                "call",
            )
            _structure, call_result = evaluate_repo(repo, base, call)
            body = commit(
                repo,
                "netbox/sample.py",
                base_source.replace("        pass\n", "        pass  # silenced\n"),
                "body",
            )
            _structure, body_result = evaluate_repo(repo, base, body)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual({item["rule_id"] for item in findings_for("code.swallowed_exception", header_result)}, {"code.swallowed_exception"})
        self.assertEqual(findings_for("code.bare_exception", header_result), [])
        self.assertEqual(findings_for("code.dynamic_execution", header_result), [])
        call_evidence = findings_for("code.dynamic_execution", call_result)[0]["evidence"][0]
        self.assertEqual(call_evidence["callee_name"], "eval")
        self.assertEqual(call_evidence["before"]["status"], "available")
        self.assertIn("eval('1')", call_evidence["before"]["source_segment"])
        self.assertEqual(call_evidence["after"]["status"], "available")
        self.assertIn("eval('2')", call_evidence["after"]["source_segment"])
        self.assertEqual(findings_for("code.swallowed_exception", call_result), [])
        self.assertEqual(len(findings_for("code.swallowed_exception", body_result)), 1)
        self.assertEqual(findings_for("code.bare_exception", body_result), [])
        self.assertEqual(findings_for("code.dynamic_execution", body_result), [])

    def test_deleted_smell_does_not_trigger(self) -> None:
        root, repo = init_repo()
        try:
            base = commit(
                repo,
                "netbox/sample.py",
                "def kept():\n    try:\n        load()\n    except:\n        pass\n    exec('1')\n",
                "base",
            )
            head = commit(repo, "netbox/sample.py", "def kept():\n    return 1\n", "delete")
            _structure, result = evaluate_repo(repo, base, head)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(findings_for("code.swallowed_exception", result), [])
        self.assertEqual(findings_for("code.bare_exception", result), [])
        self.assertEqual(findings_for("code.dynamic_execution", result), [])

    def test_syntax_error_is_unanalyzed_and_not_a_pass(self) -> None:
        root, repo = init_repo()
        try:
            base = commit(repo, "netbox/good.py", "def edited():\n    return 1\n", "base good")
            commit(repo, "netbox/bad.py", "def ok():\n    return 1\n", "base bad")
            base = git(repo, "rev-parse", "HEAD")
            commit(
                repo,
                "netbox/good.py",
                "def edited():\n    try:\n        load()\n    except ValueError:\n        pass\n",
                "good smell",
            )
            head = commit(repo, "netbox/bad.py", "def broken(:\n    pass\n", "bad syntax")
            structure, result = evaluate_repo(repo, base, head)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["summary"]["parse_degraded"])
        self.assertEqual(result["summary"]["unanalyzed"], [{"path": "netbox/bad.py", "reason": "syntax_error"}])
        self.assertEqual(len(findings_for("code.swallowed_exception", result)), 1)
        bad = next(item for item in structure["files"] if item["path"] == "netbox/bad.py")
        self.assertEqual(bad["parse_status"]["head"], "failed")
        self.assertEqual([node for node in bad["nodes"] if node.get("side") == "head"], [])
        self.assertTrue(all(item["evidence"][0]["path"] != "netbox/bad.py" for item in findings_for("code.swallowed_exception", result)))

    def test_unavailable_source_is_an_analysis_error(self) -> None:
        root, repo = init_repo()
        try:
            base = commit(repo, "netbox/sample.py", "def edited():\n    return 1\n", "base")
            record = {
                "schema_version": "stage03.v1",
                "status": "ok",
                "repo": "example/example",
                "pr_number": 4,
                "base_sha": base,
                "head_sha": base,
                "files": [{
                    "old_path": "netbox/missing.py",
                    "new_path": "netbox/missing.py",
                    "status": "modified",
                    "role": "business",
                    "is_python": True,
                    "hunks": [{"lines": [{"kind": "add", "old_line": None, "new_line": 1, "text": "eval('1')"}]}],
                }],
            }
            structure = extract_changed_structures(record, repo)
            result = evaluate_rules(structure)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(structure["status"], "error")
        self.assertTrue(any(error.get("code") == "git_show_error" for error in structure["errors"]))
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["findings"], [])
        self.assertNotEqual(result["status"], "ok")

    def test_test_role_python_file_is_analyzed(self) -> None:
        root, repo = init_repo()
        try:
            base = commit(repo, "netbox/tests/test_sample.py", "def test_ok():\n    return 1\n", "base")
            head = commit(
                repo,
                "netbox/tests/test_sample.py",
                "def test_ok():\n    try:\n        run()\n    except:\n        pass\n",
                "head",
            )
            _structure, result = evaluate_repo(repo, base, head)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        ids = {item["rule_id"] for item in result["findings"]}
        self.assertIn("code.swallowed_exception", ids)
        self.assertIn("code.bare_exception", ids)

    def test_branch_report_domains_cover_code_smells(self) -> None:
        root, repo = init_repo()
        try:
            commit(repo, "netbox/sample.py", "def edited():\n    return 1\n", "base")
            git(repo, "checkout", "-b", "feature")
            commit(
                repo,
                "netbox/sample.py",
                "def edited():\n    try:\n        load()\n    except:\n        pass\n",
                "head",
            )
            report = analyze_branches(repo, "main", "feature")
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertIn("code", report["summary"]["domains"])
        swallowed = next(item for item in report["findings"] if item["rule_id"] == "code.swallowed_exception")
        evidence = swallowed["evidence"][0]
        self.assertEqual(evidence["source_status"], "available")
        self.assertIn("pass", evidence["source_segment"])
        self.assertEqual(evidence["before"]["status"], "unavailable")
        self.assertEqual(evidence["before"]["reason"], "no_base_node")
        self.assertEqual(evidence["after"]["source_segment"], evidence["source_segment"])
        self.assertEqual(report["score_basis"]["maximum_points"], 10)
        self.assertEqual(report["score_basis"]["configuration"]["rule_weights"]["code.swallowed_exception"], 0)
