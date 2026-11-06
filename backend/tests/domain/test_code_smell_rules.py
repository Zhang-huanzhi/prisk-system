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
        control_ids = sorted(node["node_id"] for node in record["files"][0]["nodes"] if node["kind"] == "control_flow")
        self.assertTrue(control_ids)
        self.assertEqual(result["summary"]["unanalyzed"], [{
            "path": "netbox/sample.py",
            "reason": "unsupported_stage04_details",
            "node_ids": control_ids,
        }])
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
        self.assertEqual(report["score_basis"]["configuration"]["rule_weights"]["code.unmanaged_open"], 0)
        self.assertEqual(report["score_basis"]["configuration"]["rule_weights"]["code.deep_control_flow"], 0)


OPEN_SAMPLE = """
import io
from pathlib import Path

def unmanaged(path):
    handle = open(path)
    text = open(path).read()
    return (open)(path)

def managed(path):
    with open(path) as handle:
        return handle.read()

def managed_bare(path):
    with open(path):
        return 1

async def managed_async(path):
    async with open(path):
        return 1

def attribute_calls(path):
    return Path(path).open(), io.open(path), path.open(), builtins.open(path)

def shadowed(path):
    open = custom_open
    return open(path)

def inner_open(path):
    with open(open(path).read()):
        return 1

def assigned_then_with(path):
    handle = open(path)
    with handle:
        return handle.read()

def closing_wrapper(path):
    return contextlib.closing(open(path))

def conditional_context(path, flag):
    with open(path) if flag else nullcontext():
        return 1

def dynamic_neighbor(source):
    return eval(source)
"""


DEEP_SAMPLE = """
def depth_five():
    if a:
        for b in items:
            while d:
                with e:
                    try:
                        touch()
                    except Error:
                        pass

def depth_four():
    if a:
        for b in items:
            while d:
                with e:
                    touch()

def elif_chain(a, b, c, d, e, f):
    if a:
        x()
    elif b:
        x()
    elif c:
        x()
    elif d:
        x()
    elif e:
        x()
    elif f:
        x()

def else_body_if():
    if a:
        for b in items:
            while d:
                with e:
                    log()
                    if ready:
                        touch()

def try_except_level():
    if a:
        for b in items:
            while d:
                try:
                    touch()
                except Error:
                    if ready:
                        flag()

def nested_function():
    if a:
        for b in items:
            while d:
                with e:
                    def inner():
                        if z:
                            touch()

def match_excluded(value):
    match value:
        case 1:
            if a:
                for b in items:
                    while d:
                        with e:
                            touch()

def comprehension(items):
    if a:
        for b in items:
            while d:
                with e:
                    values = [item for item in items if item]
                    return values

def ternary():
    if a:
        for b in items:
            while d:
                with e:
                    value = x if y else z
                    return value

async def async_counts():
    if a:
        async for b in items:
            while d:
                async with e:
                    try:
                        touch()
                    except Error:
                        pass
"""


def _legacy_node(kind: str, node_id: str, segment: str | None, details: dict, **extra) -> dict:
    node = {
        "kind": kind,
        "side": "head",
        "node_id": node_id,
        "changed_lines": [1],
        "start_line": 1,
        "end_line": 8,
        "details": details,
    }
    if segment is not None:
        node["source_segment"] = segment
    node.update(extra)
    return node


def _record_with(nodes: list[dict], path: str = "netbox/legacy.py") -> dict:
    return {
        "schema_version": "stage04.v1",
        "status": "ok",
        "pr_number": 5,
        "files": [{
            "path": path,
            "parse_status": {"head": "ok", "file": "ok"},
            "structural_changes": [],
            "errors": [],
            "nodes": nodes,
        }],
        "summary": {},
    }


class SecondBatchCodeSmellTests(unittest.TestCase):
    def test_open_positive_negative_and_boundary_patterns(self) -> None:
        result = evaluate_rules(stage04_from_source(OPEN_SAMPLE))
        opened = findings_for("code.unmanaged_open", result)
        self.assertEqual(len(opened), 8)
        self.assertTrue(all(item["confidence"] == "structural" for item in opened))
        self.assertTrue(all(item["evidence"][0]["callee_name"] == "open" for item in opened))
        self.assertTrue(all(item["evidence"][0]["used_as_with_context"] is False for item in opened))
        self.assertIn("不判断泄漏", opened[0]["message"])
        self.assertEqual(
            [item["evidence"][0]["callee_name"] for item in findings_for("code.dynamic_execution", result)],
            ["eval"],
        )
        parsed = parse_python_source(OPEN_SAMPLE, "netbox/sample.py", "head")
        managed = [
            node for node in parsed["nodes"]
            if node["kind"] == "call" and node["details"]["direct_callee_name"] == "open" and node["details"]["used_as_with_context"]
        ]
        self.assertGreaterEqual(len(managed), 4)
        self.assertEqual(result["summary"]["unanalyzed"], [])

    def test_recorded_depth_threshold_is_fixed_at_four(self) -> None:
        result = evaluate_rules(stage04_from_source(DEEP_SAMPLE))
        deep = findings_for("code.deep_control_flow", result)
        kinds = sorted(item["evidence"][0]["control_kind"] for item in deep)
        self.assertEqual(kinds, ["if", "if", "try", "try"])
        self.assertTrue(all(item["evidence"][0]["nesting_depth"] == 5 for item in deep))
        self.assertTrue(all(item["evidence"][0]["depth_threshold"] == 4 for item in deep))
        self.assertTrue(all(item["evidence"][0]["nesting_depth_basis"] == "recorded" for item in deep))
        self.assertIn("固定阈值 4", deep[0]["message"])
        self.assertNotIn("概率", deep[0]["message"])
        parsed = parse_python_source(DEEP_SAMPLE, "netbox/sample.py", "head")
        elifs = [
            node for node in parsed["nodes"]
            if node["kind"] == "control_flow" and node["details"].get("is_elif")
        ]
        self.assertGreaterEqual(len(elifs), 5)
        self.assertTrue(all(node["details"]["nesting_depth"] == 1 for node in elifs))

    def test_depth_four_elif_match_and_comprehension_do_not_trigger(self) -> None:
        result = evaluate_rules(stage04_from_source(DEEP_SAMPLE))
        deep_names = {item["evidence"][0]["qualified_name"] for item in findings_for("code.deep_control_flow", result)}
        self.assertTrue(all(not name.endswith("depth_four") for name in deep_names))
        self.assertTrue(all("elif_chain" not in name for name in deep_names))
        self.assertTrue(all("match_excluded" not in name for name in deep_names))
        self.assertTrue(all("comprehension" not in name for name in deep_names))
        self.assertTrue(all("ternary" not in name for name in deep_names))
        self.assertTrue(all("nested_function" not in name for name in deep_names))

    def test_legacy_open_without_with_flag_is_unanalyzed(self) -> None:
        record = _record_with([
            _legacy_node("call", "open-old", "open(path)", {"callee": "open"}),
            _legacy_node("call", "attr-old", "path.open()", {"callee": "path.open"}),
            _legacy_node("call", "eval-old", "eval(source)", {"callee": "eval"}),
        ])
        result = evaluate_rules(record)
        self.assertEqual(findings_for("code.unmanaged_open", result), [])
        self.assertEqual(
            [item["evidence"][0]["callee_name"] for item in findings_for("code.dynamic_execution", result)],
            ["eval"],
        )
        self.assertEqual(result["summary"]["unanalyzed"], [{
            "path": "netbox/legacy.py",
            "reason": "unsupported_stage04_details",
            "node_ids": ["open-old"],
        }])

    def test_recorded_open_context_flag_decides_the_finding(self) -> None:
        record = _record_with([
            _legacy_node("call", "bare", "open(path)", {"direct_callee_name": "open", "used_as_with_context": False}),
            _legacy_node("call", "managed", "open(path)", {"direct_callee_name": "open", "used_as_with_context": True}),
        ])
        result = evaluate_rules(record)
        self.assertEqual([item["evidence"][0]["node_id"] for item in findings_for("code.unmanaged_open", result)], ["bare"])
        self.assertEqual(result["summary"]["unanalyzed"], [])

    def test_legacy_control_segment_reports_only_a_conclusive_lower_bound(self) -> None:
        deep_segment = (
            "if a:\n"
            "    for b in items:\n"
            "        while d:\n"
            "            with e:\n"
            "                try:\n"
            "                    touch()\n"
            "                except Error:\n"
            "                    pass\n"
        )
        record = _record_with([
            _legacy_node("control_flow", "deep-slice", deep_segment, {}),
            _legacy_node("control_flow", "shallow-slice", "if ready:\n    touch()\n", {}),
            _legacy_node("control_flow", "depth-four", None, {"control_kind": "with", "nesting_depth": 4}),
            _legacy_node("control_flow", "depth-five", None, {"control_kind": "try", "nesting_depth": 5}),
        ])
        result = evaluate_rules(record)
        by_id = {item["evidence"][0]["node_id"]: item for item in findings_for("code.deep_control_flow", result)}
        self.assertEqual(set(by_id), {"deep-slice", "depth-five"})
        self.assertEqual(by_id["deep-slice"]["evidence"][0]["nesting_depth_basis"], "segment_lower_bound")
        self.assertEqual(by_id["depth-five"]["evidence"][0]["nesting_depth_basis"], "recorded")
        self.assertEqual(result["summary"]["unanalyzed"], [{
            "path": "netbox/legacy.py",
            "reason": "unsupported_stage04_details",
            "node_ids": ["shallow-slice"],
        }])

    def test_disabled_new_rules_do_not_mark_missing_fields_unanalyzed(self) -> None:
        record = _record_with([
            _legacy_node("call", "open-old", None, {}),
            _legacy_node("control_flow", "flow-old", None, {}),
        ])
        result = evaluate_rules(record, {"enabled_rules": ["code.swallowed_exception"]})
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["summary"]["unanalyzed"], [])

    def test_added_line_intersection_and_delete_only(self) -> None:
        root, repo = init_repo()
        try:
            base_source = "def f(path):\n    with open(path) as handle:\n        return handle.read()\n"
            base = commit(repo, "netbox/sample.py", base_source, "base")
            head = commit(
                repo,
                "netbox/sample.py",
                "def f(path):\n    handle = open(path)\n    with open(path) as managed:\n        return managed.read()\n",
                "head",
            )
            structure, result = evaluate_repo(repo, base, head)
            opened = findings_for("code.unmanaged_open", result)
            self.assertEqual(len(opened), 1)
            self.assertEqual(opened[0]["evidence"][0]["source_segment"], "open(path)")
            self.assertEqual(opened[0]["evidence"][0]["used_as_with_context"], False)
            self.assertNotIn("control_flow", {item["kind"] for item in structure["files"][0]["structural_changes"]})
            deleted = commit(repo, "netbox/sample.py", "def f(path):\n    return 1\n", "delete")
            _structure, deleted_result = evaluate_repo(repo, head, deleted)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(findings_for("code.unmanaged_open", deleted_result), [])
        self.assertEqual(findings_for("code.deep_control_flow", deleted_result), [])

    def test_deep_finding_follows_the_changed_node_only(self) -> None:
        root, repo = init_repo()
        deep = (
            "def depth_five():\n"
            "    if a:\n"
            "        for b in items:\n"
            "            while d:\n"
            "                with e:\n"
            "                    try:\n"
            "                        touch()\n"
            "                    except Error:\n"
            "                        pass\n"
            "\n"
            "def edited():\n"
            "    return 1\n"
        )
        try:
            base = commit(repo, "netbox/sample.py", deep, "base")
            inner = commit(repo, "netbox/sample.py", deep.replace("touch()", "touch()  # changed"), "inner")
            _structure, inner_result = evaluate_repo(repo, base, inner)
            outer = commit(repo, "netbox/sample.py", deep.replace("if a:", "if a:  # outer"), "outer")
            _structure, outer_result = evaluate_repo(repo, base, outer)
            sibling = commit(repo, "netbox/sample.py", deep.replace("return 1", "return 2"), "sibling")
            _structure, sibling_result = evaluate_repo(repo, base, sibling)
            removed = commit(repo, "netbox/sample.py", "def edited():\n    return 1\n", "removed")
            _structure, removed_result = evaluate_repo(repo, inner, removed)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        inner_findings = findings_for("code.deep_control_flow", inner_result)
        self.assertEqual(len(inner_findings), 1)
        self.assertEqual(inner_findings[0]["evidence"][0]["control_kind"], "try")
        self.assertEqual(inner_findings[0]["evidence"][0]["nesting_depth"], 5)
        self.assertEqual(findings_for("code.deep_control_flow", outer_result), [])
        self.assertEqual(findings_for("code.deep_control_flow", sibling_result), [])
        self.assertEqual(findings_for("code.deep_control_flow", removed_result), [])

    def test_branch_score_denominator_stays_ten_when_new_rules_match(self) -> None:
        root, repo = init_repo()
        try:
            commit(repo, "netbox/sample.py", "def edited():\n    return 1\n", "base")
            git(repo, "checkout", "-b", "feature")
            commit(
                repo,
                "netbox/sample.py",
                "def edited(path):\n"
                "    if a:\n"
                "        for b in items:\n"
                "            while d:\n"
                "                with e:\n"
                "                    try:\n"
                "                        handle = open(path)\n"
                "                        return handle\n"
                "                    finally:\n"
                "                        pass\n",
                "head",
            )
            report = analyze_branches(repo, "main", "feature")
        finally:
            shutil.rmtree(root, ignore_errors=True)
        ids = {item["rule_id"] for item in report["findings"]}
        self.assertIn("code.unmanaged_open", ids)
        self.assertIn("code.deep_control_flow", ids)
        self.assertIn("code", report["summary"]["domains"])
        self.assertEqual(report["score_basis"]["maximum_points"], 10)
        self.assertEqual(
            report["score_basis"]["earned_points"],
            report["score_basis"]["configuration"]["test_collaboration_weight"],
        )
        self.assertEqual(report["score_basis"]["configuration"]["rule_weights"]["code.unmanaged_open"], 0)
        self.assertEqual(report["score_basis"]["configuration"]["rule_weights"]["code.deep_control_flow"], 0)


SECRET_SAMPLE = r'''
password = "correct-horse"
note = "token=ak_live_0123456789"
db_password = "this-name-is-not-exact"
token = "short"
passwd = "changeme"
api_key = "PASSWORD"
secret = "your-secret"
access_key = "1234567"
private_key = "12345678"
client_secret = "sample"
auth_token = "sample-value"
Password = "correct-horse"
apikey = "ak_live_0123456789"

def login(token="tok_0123456789", other="short"):
    client.connect(client_secret="cs_0123456789")
    self.api_key = "ak_live_0123456789"

class Box:
    secret_key: str = "sk_live_0123456789"

def keyword_only(*, passwd="pw_0123456789"):
    return passwd

def no_default(token):
    return token

def annotation_only():
    password: str
    return password

def comparisons():
    return password == "correct-horse"

def joined():
    token = "0123" "456789"

def bytes_value():
    token = b"0123456789abcd"

def fstring_value():
    token = f"0123456789abcd"

def getenv_value():
    password = os.getenv("PASSWORD")

def name_value():
    password = SECRET_VALUE

def unpack():
    a, password = "x", "long-secret-value-xx"

def both_names():
    password = token = "correct-horse"

def placeholder_case():
    password = "ChAnGeMe"

def spaces():
    password = ""
    token = "        "

def subscript():
    data["password"] = "correct-horse"

def aug():
    password += "correct-horse"

def walrus():
    if (password := "correct-horse"):
        return password

def lambda_default():
    return lambda token="tok_0123456789": token

class ClassKeyword(password="correct-horse-extra"):
    pass

def attr_chain():
    obj.auth.secret_key = "sk_live_0123456789"

"""
password = "correct-horse-doc"
"""
# password = "correct-horse-comment"
'''


MUTABLE_SAMPLE = '''
global MODULE_ONLY
CACHE = {}
OTHER = []
REGISTRY = {1}
BUILT = list()
BUILT_DICT = dict()
BUILT_SET = set()
LIMIT = 3
PAIR = (1, 2)
NAME = OTHER
flags = None
text = "cache"
left = right = []
a, b = [], {}
if flag:
    LAZY = {}

class Registry:
    items = []
    global CACHE

def reset(value):
    global CACHE
    CACHE = value

def reset_many():
    global CACHE, OTHER

async def reset_async():
    global FLAGS

def local_only():
    items = []
    return items

def closure():
    nonlocal CACHE

def inplace():
    CACHE.append(1)

CONFIG: dict = {}

def defaults(items=[]):
    return items

def calls():
    cache = defaultdict(list)
    queue = deque()
    values = list(items)
    builtin = builtins.list()
    comp = [item for item in items]
    copied = list()

class Nested:
    data = set()

def outer():
    class Inner:
        items = []
    def inner():
        global NESTED

def drop():
    del CACHE
'''


class RemainingCodeSmellTests(unittest.TestCase):
    def test_secret_bindings_follow_the_card_name_length_and_placeholder_tables(self) -> None:
        result = evaluate_rules(stage04_from_source(SECRET_SAMPLE))
        secrets = findings_for("code.hardcoded_secret", result)
        observed = sorted(
            (item["evidence"][0]["binding_form"], item["evidence"][0]["binding_name"], item["evidence"][0]["qualified_name"])
            for item in secrets
        )
        self.assertEqual(
            observed,
            [
                ("attribute_assignment", "api_key", "login.api_key"),
                ("attribute_assignment", "secret_key", "attr_chain.secret_key"),
                ("keyword_argument", "client_secret", "login.client_secret"),
                ("name_assignment", "Password", "Password"),
                ("name_assignment", "apikey", "apikey"),
                ("name_assignment", "auth_token", "auth_token"),
                ("name_assignment", "password", "both_names.password"),
                ("name_assignment", "password", "password"),
                ("name_assignment", "private_key", "private_key"),
                ("name_assignment", "secret_key", "Box.secret_key"),
                ("name_assignment", "token", "both_names.token"),
                ("name_assignment", "token", "spaces.token"),
                ("parameter_default", "passwd", "keyword_only.passwd"),
                ("parameter_default", "token", "login.token"),
            ],
        )
        password = next(item for item in secrets if item["evidence"][0]["qualified_name"] == "password")
        self.assertEqual(password["confidence"], "structural")
        self.assertEqual(password["impact_type"], "pr_intrinsic_risk")
        self.assertEqual(password["evidence"][0]["value_length"], 13)
        self.assertEqual(password["evidence"][0]["value_preview"], "co…se")
        self.assertNotIn("literal_text", password["evidence"][0])
        self.assertNotIn("correct-horse", password["message"])
        self.assertIn("不表示秘密已经确认", password["message"])
        self.assertNotIn("漏洞已经", password["message"])
        self.assertIn("correct-horse", password["evidence"][0]["source_segment"])
        spaces = next(item for item in secrets if item["evidence"][0]["qualified_name"] == "spaces.token")
        self.assertEqual(spaces["evidence"][0]["value_length"], 8)
        self.assertEqual(spaces["evidence"][0]["value_preview"], "  …  ")
        self.assertEqual(result["summary"]["unanalyzed"], [])

    def test_mutable_state_reports_both_forms_and_skips_local_and_other_constructors(self) -> None:
        result = evaluate_rules(stage04_from_source(MUTABLE_SAMPLE))
        mutable = findings_for("code.global_mutable_state", result)
        observed = sorted(
            (
                item["evidence"][0]["mutable_state_form"],
                tuple(item["evidence"][0]["binding_targets"]),
                item["evidence"][0].get("value_kind"),
                item["evidence"][0]["qualified_name"],
            )
            for item in mutable
        )
        self.assertEqual(
            observed,
            [
                ("global_statement", ("CACHE",), None, "reset"),
                ("global_statement", ("CACHE", "OTHER"), None, "reset_many"),
                ("global_statement", ("FLAGS",), None, "reset_async"),
                ("global_statement", ("NESTED",), None, "outer.inner"),
                ("mutable_binding", ("BUILT",), "list_call", "<module>"),
                ("mutable_binding", ("BUILT_DICT",), "dict_call", "<module>"),
                ("mutable_binding", ("BUILT_SET",), "set_call", "<module>"),
                ("mutable_binding", ("CACHE",), "dict_display", "<module>"),
                ("mutable_binding", ("CONFIG",), "dict_display", "<module>"),
                ("mutable_binding", ("LAZY",), "dict_display", "<module>"),
                ("mutable_binding", ("OTHER",), "list_display", "<module>"),
                ("mutable_binding", ("REGISTRY",), "set_display", "<module>"),
                ("mutable_binding", ("data",), "set_call", "Nested"),
                ("mutable_binding", ("items",), "list_display", "Registry"),
                ("mutable_binding", ("items",), "list_display", "outer.Inner"),
                ("mutable_binding", ("left", "right"), "list_display", "<module>"),
            ],
        )
        self.assertTrue(all(item["confidence"] == "structural" for item in mutable))
        self.assertIn("不判断已经发生串扰", mutable[0]["message"])
        self.assertEqual(result["summary"]["unanalyzed"], [])
        parsed = parse_python_source(MUTABLE_SAMPLE, "netbox/sample.py", "head")
        self.assertNotIn("MODULE_ONLY", {node.get("name") for node in parsed["nodes"] if node["kind"] == "mutable_state"})
        reset = next(node for node in parsed["nodes"] if node["kind"] == "function" and node["name"] == "reset")
        self.assertTrue(reset["details"]["contains_global_statement"])
        local_only = next(node for node in parsed["nodes"] if node["kind"] == "function" and node["name"] == "local_only")
        self.assertFalse(local_only["details"]["contains_global_statement"])

    def test_new_nodes_do_not_enter_structural_changes(self) -> None:
        root, repo = init_repo()
        try:
            base = commit(repo, "netbox/sample.py", "def edited():\n    return 1\n", "base")
            head = commit(
                repo,
                "netbox/sample.py",
                "CACHE = {}\n\ndef edited(token=\"tok_0123456789\"):\n    global CACHE\n    return token\n",
                "head",
            )
            structure, result = evaluate_repo(repo, base, head)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        kinds = {item["kind"] for item in structure["files"][0]["structural_changes"]}
        self.assertTrue({"literal_binding", "mutable_state", "control_flow"}.isdisjoint(kinds))
        self.assertEqual(len(findings_for("code.hardcoded_secret", result)), 1)
        self.assertEqual(len(findings_for("code.global_mutable_state", result)), 2)
        self.assertEqual(result["summary"]["unanalyzed"], [])

    def test_added_lines_select_the_binding_and_delete_does_not_trigger(self) -> None:
        root, repo = init_repo()
        base_source = "password = \"correct-horse\"\nCACHE = {}\n\ndef edited():\n    return 1\n"
        try:
            base = commit(repo, "netbox/sample.py", base_source, "base")
            other = commit(repo, "netbox/sample.py", base_source.replace("return 1", "return 2"), "other")
            _structure, other_result = evaluate_repo(repo, base, other)
            secret_head = commit(
                repo,
                "netbox/sample.py",
                base_source.replace("correct-horse", "correct-horse-2"),
                "secret",
            )
            _structure, secret_result = evaluate_repo(repo, base, secret_head)
            removed = commit(repo, "netbox/sample.py", "def edited():\n    return 1\n", "removed")
            _structure, removed_result = evaluate_repo(repo, secret_head, removed)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(findings_for("code.hardcoded_secret", other_result), [])
        self.assertEqual(findings_for("code.global_mutable_state", other_result), [])
        secrets = findings_for("code.hardcoded_secret", secret_result)
        self.assertEqual(len(secrets), 1)
        self.assertEqual(secrets[0]["evidence"][0]["binding_name"], "password")
        self.assertEqual(findings_for("code.global_mutable_state", secret_result), [])
        self.assertEqual(findings_for("code.hardcoded_secret", removed_result), [])
        self.assertEqual(findings_for("code.global_mutable_state", removed_result), [])

    def test_legacy_field_and_call_slices_recover_or_stay_unanalyzed(self) -> None:
        record = _record_with([
            _legacy_node("field", "cache", "CACHE = {}\n", {"value_fingerprint": "abc"}),
            _legacy_node("field", "limit", "LIMIT = 3\n", {"value_fingerprint": "def"}),
            _legacy_node("field", "pair", "left = right = []\n", {"value_fingerprint": "ghi"}, start_line=3, end_line=3),
            _legacy_node("field", "pair-right", "left = right = []\n", {"value_fingerprint": "ghi"}, start_line=3, end_line=3),
            _legacy_node("field", "password", "password = \"correct-horse\"\n", {"value_fingerprint": "jkl"}, start_line=4, end_line=4),
            _legacy_node("field", "unknown", None, {"value_fingerprint": "mno"}, start_line=5, end_line=5),
            _legacy_node("call", "keyword", "connect(client_secret=\"cs_0123456789\")", {"callee": "connect", "keyword_names": ["client_secret"]}),
            _legacy_node("call", "plain", "open(path)", {"callee": "open", "keyword_names": []}),
        ])
        result = evaluate_rules(record)
        mutable = findings_for("code.global_mutable_state", result)
        self.assertEqual(
            sorted(tuple(item["evidence"][0]["binding_targets"]) for item in mutable),
            [("CACHE",), ("left", "right")],
        )
        secrets = findings_for("code.hardcoded_secret", result)
        self.assertEqual(
            sorted((item["evidence"][0]["binding_form"], item["evidence"][0]["binding_name"]) for item in secrets),
            [("keyword_argument", "client_secret"), ("name_assignment", "password")],
        )
        self.assertEqual(result["summary"]["unanalyzed"], [{
            "path": "netbox/legacy.py",
            "reason": "unsupported_stage04_details",
            "node_ids": ["plain", "unknown"],
        }])

    def test_legacy_function_slice_recovers_body_bindings_and_truncated_slice_is_unknown(self) -> None:
        segment = "def reset():\n    password = \"correct-horse\"\n    global CACHE\n"
        record = _record_with([
            _legacy_node("function", "reset", segment, {"signature": {"parameters": [], "returns": None}}, start_line=1, end_line=3, changed_lines=[2, 3]),
            _legacy_node("function", "truncated", "def long():\n    pass\n", {}, source_segment_truncated=True, start_line=10, end_line=12),
        ])
        result = evaluate_rules(record)
        self.assertEqual(
            [item["evidence"][0]["binding_name"] for item in findings_for("code.hardcoded_secret", result)],
            ["password"],
        )
        globals_ = findings_for("code.global_mutable_state", result)
        self.assertEqual([item["evidence"][0]["binding_targets"] for item in globals_], [["CACHE"]])
        self.assertEqual(globals_[0]["evidence"][0]["start_line"], 3)
        self.assertEqual(result["summary"]["unanalyzed"], [{
            "path": "netbox/legacy.py",
            "reason": "unsupported_stage04_details",
            "node_ids": ["truncated"],
        }])
        disabled = evaluate_rules(record, {"enabled_rules": ["code.swallowed_exception"]})
        self.assertEqual(disabled["findings"], [])
        self.assertEqual(disabled["summary"]["unanalyzed"], [])

    def test_branch_score_denominator_stays_ten_when_remaining_smells_match(self) -> None:
        root, repo = init_repo()
        try:
            commit(repo, "netbox/sample.py", "def edited():\n    return 1\n", "base")
            git(repo, "checkout", "-b", "feature")
            commit(
                repo,
                "netbox/sample.py",
                "CACHE = {}\n\ndef edited(password=\"correct-horse\"):\n    global CACHE\n    return password\n",
                "head",
            )
            report = analyze_branches(repo, "main", "feature")
        finally:
            shutil.rmtree(root, ignore_errors=True)
        ids = {item["rule_id"] for item in report["findings"]}
        self.assertIn("code.hardcoded_secret", ids)
        self.assertIn("code.global_mutable_state", ids)
        self.assertEqual(report["score_basis"]["maximum_points"], 10)
        self.assertEqual(report["score_basis"]["configuration"]["rule_weights"]["code.hardcoded_secret"], 0)
        self.assertEqual(report["score_basis"]["configuration"]["rule_weights"]["code.global_mutable_state"], 0)
        self.assertEqual(
            report["score_basis"]["earned_points"],
            report["score_basis"]["configuration"]["test_collaboration_weight"],
        )
