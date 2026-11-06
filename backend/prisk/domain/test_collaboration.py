"""PR-level production/test collaboration hint.

The detector reads file-change records already produced from a three-dot
diff: status, additions, deletions, binary, and both paths of a rename.
It does not read the JSON rule registry, call external systems, or score
thresholds.

Path classes are one versioned default, not a per-project mapping:

- ``test``: a path segment named ``test`` or ``tests``, or a Python file
  named ``test_*.py`` / ``*_test.py`` (and the ``.pyi`` forms). This is the
  same test convention as ``classify_path`` and covers ``backend/tests``.
- ``non_production``: documentation (``.md``, ``.rst``, or a ``doc`` /
  ``docs`` segment), configuration (``settings.py``, ``configuration*.py``,
  or a ``config`` / ``settings`` / ``configuration`` segment), generated
  trees, migrations, and ``static``.
- ``production``: remaining ``.py``, ``.pyi``, ``.js``, ``.jsx``, ``.ts``,
  and ``.tsx`` files.
- ``unknown``: every other path.

A pure rename is not production content unless additions or deletions are
greater than zero. A test rename still counts as a test-file change.
Missing counts, a binary production file, or an unknown path are recorded
in ``summary.unanalyzed`` and do not hit. An empty finding list in that
case is not a pass. Records that carry only AST nodes, with no status and
no line counts, have no file-change channel; the rule does not hit and
does not award the historical collaboration point.
"""

from __future__ import annotations

from typing import Any


COLLABORATION_RULE_ID = "workflow.test_collaboration_gap"
PATH_POLICY_ID = "default_source_and_test_directories"

_TEST_SEGMENTS = frozenset({"test", "tests"})
_EXCLUDED_SEGMENTS = frozenset({
    "doc",
    "docs",
    "migration",
    "migrations",
    "generated",
    "static",
    "config",
    "configs",
    "configuration",
    "settings",
})
_DOC_SUFFIXES = (".md", ".rst")
_PRODUCTION_SUFFIXES = (".py", ".pyi", ".js", ".jsx", ".ts", ".tsx")
_CONTENT_STATUSES = frozenset({"added", "modified", "deleted"})
_RENAME_STATUSES = frozenset({"renamed", "copied"})
_TEST_CHANGE_STATUSES = _CONTENT_STATUSES | _RENAME_STATUSES
_DIFF_STATS_UNAVAILABLE = "diff_stats_unavailable"
_PATH_CLASS_UNAVAILABLE = "path_classification_unavailable"

_MESSAGE = (
    "同一变更中至少有一个生产代码文件发生了有行数证据的新增、修改或删除，"
    "且没有测试文件发生新增、修改、删除或重命名。"
    "这是复核提示，不说明测试缺失、覆盖不足、回归、外部破坏或缺陷。"
)
_REMOVAL_NOTE = (
    "这些生产代码变更的新增行数为 0，删除行数大于 0，记为 code_removal。"
    "行数不能区分死代码删除和功能下线。"
)


def _segments(path: str) -> list[str]:
    normalized = path.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return [part for part in normalized.strip("/").split("/") if part not in {"", "."}]


def classify_collaboration_path(path: str | None) -> str:
    """Return test, production, non_production, or unknown."""

    if not path or not str(path).strip():
        return "unknown"
    parts = _segments(str(path))
    if not parts:
        return "unknown"
    lowered = [part.casefold() for part in parts]
    if any(part in _TEST_SEGMENTS for part in lowered):
        return "test"
    filename = lowered[-1]
    if filename.startswith("test_") and (filename.endswith(".py") or filename.endswith(".pyi")):
        return "test"
    if filename.endswith("_test.py") or filename.endswith("_test.pyi"):
        return "test"
    directories = lowered[:-1]
    if any(part in _EXCLUDED_SEGMENTS for part in directories):
        return "non_production"
    if filename in _EXCLUDED_SEGMENTS:
        return "non_production"
    if filename == "settings.py" or (filename.startswith("configuration") and filename.endswith(".py")):
        return "non_production"
    if filename.endswith(_DOC_SUFFIXES):
        return "non_production"
    if filename.endswith(_PRODUCTION_SUFFIXES):
        return "production"
    return "unknown"


def _count(value: Any) -> int | None:
    if type(value) is not int or value < 0:
        return None
    return value


def _has_change_channel(file_item: dict[str, Any]) -> bool:
    return any(key in file_item for key in ("status", "additions", "deletions", "binary"))


def _display_path(file_item: dict[str, Any]) -> str:
    for key in ("new_path", "path", "old_path"):
        value = file_item.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _endpoint_paths(file_item: dict[str, Any]) -> tuple[list[str], bool]:
    status = file_item.get("status")
    old_path = file_item.get("old_path") if isinstance(file_item.get("old_path"), str) else None
    new_path = file_item.get("new_path") if isinstance(file_item.get("new_path"), str) else None
    lone_path = file_item.get("path") if isinstance(file_item.get("path"), str) else None
    if status == "added":
        old_path = None
    elif status == "deleted":
        new_path = None
    paths: list[str] = []
    for value in (old_path, new_path):
        if value and value not in paths:
            paths.append(value)
    if not paths and lone_path:
        paths.append(lone_path)
    rename_incomplete = status in _RENAME_STATUSES and (not old_path or not new_path)
    return paths, rename_incomplete


def _diff_lines(file_item: dict[str, Any]) -> list[int]:
    recorded = file_item.get("diff_lines")
    if isinstance(recorded, list) and all(type(item) is int for item in recorded):
        return sorted(set(recorded))
    values: set[int] = set()
    for hunk in file_item.get("hunks") or []:
        if not isinstance(hunk, dict):
            continue
        for line in hunk.get("lines") or []:
            if not isinstance(line, dict):
                continue
            if line.get("kind") == "add" and type(line.get("new_line")) is int:
                values.add(line["new_line"])
            elif line.get("kind") == "delete" and type(line.get("old_line")) is int:
                values.add(line["old_line"])
    return sorted(values)


def _gap(path: str, reason: str) -> dict[str, str]:
    return {"path": path, "reason": reason}


def _summary_claims_change(summary: dict[str, Any]) -> bool:
    if summary.get("business_changed") is True or summary.get("test_changed") is True:
        return True
    for key in ("files_changed", "business_files", "test_files"):
        value = summary.get(key)
        if type(value) is int and value > 0:
            return True
    return False


def _file_outcome(file_item: dict[str, Any]) -> dict[str, Any]:
    path = _display_path(file_item)
    paths, rename_incomplete = _endpoint_paths(file_item)
    if rename_incomplete or not paths:
        return {"gap": _gap(path, _PATH_CLASS_UNAVAILABLE if paths else _DIFF_STATS_UNAVAILABLE)}
    classes = [classify_collaboration_path(item) for item in paths]
    if "unknown" in classes:
        return {"gap": _gap(path, _PATH_CLASS_UNAVAILABLE)}
    if "test" in classes:
        path_class = "test"
    elif "production" in classes:
        path_class = "production"
    else:
        path_class = "non_production"

    status = file_item.get("status")
    binary = file_item.get("binary")
    if "binary" in file_item and not isinstance(binary, bool):
        return {"gap": _gap(path, _DIFF_STATS_UNAVAILABLE)}
    additions = _count(file_item.get("additions")) if "additions" in file_item else None
    deletions = _count(file_item.get("deletions")) if "deletions" in file_item else None
    counts_known = additions is not None and deletions is not None
    if not isinstance(status, str) or not status:
        return {"gap": _gap(path, _DIFF_STATS_UNAVAILABLE)}

    test_change = False
    production_content = False
    content_kind = None
    if path_class == "test":
        if status not in _TEST_CHANGE_STATUSES:
            return {"gap": _gap(path, _DIFF_STATS_UNAVAILABLE)}
        test_change = True
    elif path_class == "production":
        if binary is True or not counts_known:
            return {"gap": _gap(path, _DIFF_STATS_UNAVAILABLE)}
        assert additions is not None and deletions is not None
        changed_lines = additions + deletions
        if status in _CONTENT_STATUSES and changed_lines > 0:
            production_content = True
            if additions == 0 and deletions > 0:
                content_kind = "removed"
            elif status == "added":
                content_kind = "added"
            else:
                content_kind = "modified"
        elif status in _RENAME_STATUSES and changed_lines > 0:
            production_content = True
            content_kind = "removed" if additions == 0 and deletions > 0 else "modified"
        elif status not in _CONTENT_STATUSES | _RENAME_STATUSES:
            return {"gap": _gap(path, _DIFF_STATS_UNAVAILABLE)}
    return {
        "path": path,
        "old_path": file_item.get("old_path"),
        "new_path": file_item.get("new_path"),
        "status": status,
        "path_class": path_class,
        "additions": additions if counts_known else None,
        "deletions": deletions if counts_known else None,
        "test_change": test_change,
        "production_content": production_content,
        "content_kind": content_kind,
        "lines": _diff_lines(file_item),
    }


def _finding(production: list[dict[str, Any]], examined: list[dict[str, Any]]) -> dict[str, Any]:
    additions = sum(int(item["additions"] or 0) for item in production)
    deletions = sum(int(item["deletions"] or 0) for item in production)
    code_removal = additions == 0 and deletions > 0
    message = _MESSAGE + (_REMOVAL_NOTE if code_removal else "")
    evidence = []
    for item in production:
        evidence.append({
            "path": item["path"],
            "old_path": item.get("old_path"),
            "new_path": item.get("new_path"),
            "node_kind": "file",
            "structural_change_type": item["status"],
            "lines": item["lines"],
            "path_class": "production",
            "content_change": item["content_kind"],
            "additions": item["additions"],
            "deletions": item["deletions"],
        })
    return {
        "rule_id": COLLABORATION_RULE_ID,
        "severity": "medium",
        "confidence": "structural",
        "impact_type": "pr_intrinsic_risk",
        "message": message,
        "suggested_action": "复核这些生产代码路径是否仍有相应测试计划。本规则不判断已有测试是否足够。",
        "evidence": evidence,
        "path_policy": PATH_POLICY_ID,
        "production_files_changed": len(production),
        "test_files_changed": 0,
        "production_additions": additions,
        "production_deletions": deletions,
        "change_boundary": "code_removal" if code_removal else "content_edit",
        "classification_context": [
            {
                "path": item["path"],
                "path_class": item["path_class"],
                "status": item["status"],
                "test_change": item["test_change"],
                "production_content": item["production_content"],
            }
            for item in examined
        ],
    }


def _summary_gap(summary: dict[str, Any], examined: list[dict[str, Any]]) -> dict[str, str] | None:
    file_count = summary.get("files_changed")
    if type(file_count) is int and file_count != len(examined):
        return _gap("", _DIFF_STATS_UNAVAILABLE)
    test_files = summary.get("test_files")
    observed_tests = sum(item["path_class"] == "test" for item in examined)
    if type(test_files) is int and test_files != observed_tests:
        return _gap("", _DIFF_STATS_UNAVAILABLE)
    test_changed = summary.get("test_changed")
    observed_test_change = any(item["test_change"] for item in examined)
    if test_changed is True and not observed_test_change:
        return _gap("", _DIFF_STATS_UNAVAILABLE)
    if test_changed is False and observed_test_change:
        return _gap("", _DIFF_STATS_UNAVAILABLE)
    return None


def collect_test_collaboration(
    record: dict[str, Any],
    enabled: set[str],
) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    """Return one Finding, or unanalyzed gaps. Neither means the rule did not hit."""

    if COLLABORATION_RULE_ID not in enabled:
        return None, []
    files = [item for item in record.get("files") or [] if isinstance(item, dict)]
    summary = record.get("summary") if isinstance(record.get("summary"), dict) else {}
    channel = [item for item in files if _has_change_channel(item)]
    if not channel:
        if not files and _summary_claims_change(summary):
            return None, [_gap("", _DIFF_STATS_UNAVAILABLE)]
        if files and _summary_claims_change(summary):
            return None, [_gap(_display_path(item), _DIFF_STATS_UNAVAILABLE) for item in files]
        return None, []

    gaps: list[dict[str, str]] = []
    examined: list[dict[str, Any]] = []
    for item in files:
        if not _has_change_channel(item):
            gaps.append(_gap(_display_path(item), _DIFF_STATS_UNAVAILABLE))
            continue
        outcome = _file_outcome(item)
        gap = outcome.get("gap")
        if gap is not None:
            gaps.append(gap)
            continue
        examined.append(outcome)
    if gaps:
        return None, gaps
    summary_gap = _summary_gap(summary, examined)
    if summary_gap is not None:
        return None, [summary_gap]

    production = [item for item in examined if item["production_content"]]
    if not production or any(item["test_change"] for item in examined):
        return None, []
    production.sort(key=lambda item: item["path"])
    return _finding(production, examined), []


def collaboration_terminal(
    record: dict[str, Any],
    finding: dict[str, Any] | None,
    gaps: list[dict[str, str]],
) -> tuple[str, list[dict[str, Any]]]:
    """Return Hit, NotFound, or Unanalyzed for one completed collaboration call.

    An empty gap list is NotFound only after the file-change channel itself was
    present. AST-only records stay Unanalyzed and do not invent a pass.
    """
    if finding is not None:
        return "Hit", []
    if gaps:
        grouped: dict[str, list[dict[str, str]]] = {}
        for gap in gaps:
            grouped.setdefault(str(gap.get("reason") or "diff_stats_unavailable"), []).append(
                {"path": str(gap.get("path") or "")}
            )
        reasons = [
            {"reason": reason, "objects": objects}
            for reason, objects in sorted(grouped.items())
        ]
        return "Unanalyzed", reasons
    files = [item for item in record.get("files") or [] if isinstance(item, dict)]
    if not any(_has_change_channel(item) for item in files):
        objects = [{"path": _display_path(item)} for item in files if _display_path(item)]
        return "Unanalyzed", [{"reason": "missing_file_change_channel", "objects": objects}]
    return "NotFound", []
