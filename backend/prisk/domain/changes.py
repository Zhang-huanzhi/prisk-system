"""PR 数据基础设施：将冻结的 PR 记录转换为统一变更对象。"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "stage03.v1"
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)
SIZE_ORDER = ("small", "medium", "large")
REQUIRED_FIELDS = ("repo", "pr_number", "base_sha", "head_sha")


class DatasetError(RuntimeError):
    """表示 Git 或数据输入无法满足阶段 03 的要求。"""


def _run_git(repo: Path, args: list[str], *, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=text,
        encoding="utf-8" if text else None,
        errors="replace" if text else None,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "Git 命令失败").strip()
        raise DatasetError(detail)
    return result.stdout


def verify_commit(repo: Path, sha: str) -> None:
    if not SHA_RE.fullmatch(sha):
        raise DatasetError(f"提交 SHA 格式无效: {sha!r}")
    _run_git(repo, ["cat-file", "-e", f"{sha}^{{commit}}"])


def resolve_merge_base(repo: Path, base_sha: str, head_sha: str) -> str:
    output = _run_git(repo, ["merge-base", base_sha, head_sha])
    merge_base = str(output).strip()
    if not SHA_RE.fullmatch(merge_base):
        raise DatasetError("无法解析 base/head 的 merge-base")
    return merge_base


def read_diff_text(repo: Path, base_sha: str, head_sha: str) -> str:
    output = _run_git(
        repo,
        [
            "-c",
            "core.quotepath=false",
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--no-color",
            "--find-renames",
            "--find-copies",
            "-U0",
            f"{base_sha}...{head_sha}",
        ],
    )
    return str(output)


def _decode_path(value: bytes) -> str:
    return value.decode("utf-8", errors="replace").replace("\\", "/")


def read_name_status(repo: Path, base_sha: str, head_sha: str) -> list[dict[str, str | None]]:
    raw = _run_git(
        repo,
        [
            "-c",
            "core.quotepath=false",
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--find-renames",
            "--find-copies",
            "--name-status",
            "-z",
            f"{base_sha}...{head_sha}",
        ],
        text=False,
    )
    parts = bytes(raw).split(b"\0")
    items: list[dict[str, str | None]] = []
    index = 0
    while index < len(parts):
        token = parts[index]
        index += 1
        if not token:
            continue
        decoded = _decode_path(token)
        if "\t" in decoded:
            status, path = decoded.split("\t", 1)
        else:
            status = decoded
            if index >= len(parts):
                raise DatasetError("Git name-status 输出不完整")
            path = _decode_path(parts[index])
            index += 1
        kind = status[:1]
        if kind in {"R", "C"}:
            if index >= len(parts):
                raise DatasetError("Git 重命名状态缺少旧路径")
            old_path = path
            new_path = _decode_path(parts[index])
            index += 1
            items.append(
                {
                    "status": "renamed" if kind == "R" else "copied",
                    "old_path": old_path,
                    "new_path": new_path,
                }
            )
        else:
            items.append(
                {
                    "status": {
                        "A": "added",
                        "D": "deleted",
                        "M": "modified",
                        "T": "type_changed",
                        "U": "unmerged",
                    }.get(kind, "modified"),
                    "old_path": path if kind != "A" else None,
                    "new_path": path if kind != "D" else None,
                }
            )
    return items


def _strip_diff_path(value: str, prefix: str) -> str | None:
    value = value.strip()
    if value == "/dev/null":
        return None
    if value.startswith('"') and value.endswith('"'):
        try:
            value = bytes(value[1:-1], "utf-8").decode("unicode_escape")
        except UnicodeDecodeError:
            value = value[1:-1]
    if value.startswith(prefix):
        value = value[len(prefix) :]
    if "\t" in value:
        value = value.split("\t", 1)[0]
    return value.replace("\\", "/")


def _diff_header_paths(line: str) -> tuple[str | None, str | None]:
    try:
        tokens = shlex.split(line)
    except ValueError:
        tokens = line.split()
    if len(tokens) < 4:
        return None, None
    return _strip_diff_path(tokens[2], "a/"), _strip_diff_path(tokens[3], "b/")


def _hunk_counts(match: re.Match[str]) -> tuple[int, int, int, int]:
    old_start = int(match.group("old_start"))
    old_count = int(match.group("old_count") or "1")
    new_start = int(match.group("new_start"))
    new_count = int(match.group("new_count") or "1")
    return old_start, old_count, new_start, new_count


def classify_path(path: str | None) -> str:
    """按 02 阶段的 NetBox 规则将路径分类为 test/business/other。"""

    normalized = (path or "").replace("\\", "/").lower()
    base = normalized.rsplit("/", 1)[-1]
    padded = f"/{normalized}"
    if (
        "/tests/" in padded
        or "/test/" in padded
        or base.startswith("test_")
        or base.endswith("_test.py")
    ):
        return "test"
    if normalized.startswith("netbox/") and normalized.endswith(".py") and "/static/" not in padded:
        return "business"
    return "other"


def _status_for_paths(
    status_items: Iterable[dict[str, str | None]],
    old_path: str | None,
    new_path: str | None,
) -> dict[str, str | None] | None:
    for item in status_items:
        if item.get("new_path") == new_path or item.get("old_path") == old_path:
            return item
    return None


def parse_unified_diff(
    diff_text: str,
    status_items: Iterable[dict[str, str | None]] = (),
) -> list[dict[str, Any]]:
    """解析 Git unified diff，保留文件、Hunk 和行级变更。"""

    statuses = list(status_items)
    files: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_hunk: dict[str, Any] | None = None
    old_line = 0
    new_line = 0

    def finalize() -> None:
        nonlocal current, current_hunk
        if current is None:
            return
        additions = 0
        deletions = 0
        for hunk in current["hunks"]:
            for item in hunk["lines"]:
                if item["kind"] == "add":
                    additions += 1
                elif item["kind"] == "delete":
                    deletions += 1
        current["additions"] = additions
        current["deletions"] = deletions
        files.append(current)
        current = None
        current_hunk = None

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("diff --git "):
            finalize()
            header_old, header_new = _diff_header_paths(raw_line)
            status_item = _status_for_paths(statuses, header_old, header_new) or {}
            old_path = status_item.get("old_path") or header_old
            new_path = status_item.get("new_path") or header_new
            role = classify_path(str(new_path or old_path or ""))
            current = {
                "old_path": old_path,
                "new_path": new_path,
                "status": status_item.get("status") or "modified",
                "role": role,
                "is_python": str(new_path or old_path or "").lower().endswith(".py"),
                "additions": 0,
                "deletions": 0,
                "binary": False,
                "hunks": [],
            }
            current_hunk = None
            continue

        if current is None:
            continue
        if raw_line.startswith("rename from "):
            current["old_path"] = raw_line[len("rename from ") :].replace("\\", "/")
            continue
        if raw_line.startswith("rename to "):
            current["new_path"] = raw_line[len("rename to ") :].replace("\\", "/")
            current["role"] = classify_path(current["new_path"] or current["old_path"])
            current["is_python"] = str(current["new_path"] or current["old_path"] or "").lower().endswith(".py")
            continue
        if raw_line.startswith("Binary files ") or raw_line.startswith("GIT binary patch"):
            current["binary"] = True
            continue
        if raw_line.startswith("--- ") and current_hunk is None:
            path = _strip_diff_path(raw_line[4:], "a/")
            current["old_path"] = path
            continue
        if raw_line.startswith("+++ ") and current_hunk is None:
            path = _strip_diff_path(raw_line[4:], "b/")
            current["new_path"] = path
            if path is not None:
                current["role"] = classify_path(path)
                current["is_python"] = path.lower().endswith(".py")
            continue

        hunk_match = HUNK_RE.match(raw_line)
        if hunk_match:
            old_start, old_count, new_start, new_count = _hunk_counts(hunk_match)
            old_line = old_start
            new_line = new_start
            current_hunk = {
                "old_start": old_start,
                "old_count": old_count,
                "new_start": new_start,
                "new_count": new_count,
                "lines": [],
            }
            current["hunks"].append(current_hunk)
            continue

        if current_hunk is None or raw_line.startswith("\\ No newline"):
            continue
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            current_hunk["lines"].append(
                {"kind": "add", "old_line": None, "new_line": new_line, "text": raw_line[1:]}
            )
            new_line += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            current_hunk["lines"].append(
                {"kind": "delete", "old_line": old_line, "new_line": None, "text": raw_line[1:]}
            )
            old_line += 1
        elif raw_line.startswith(" "):
            current_hunk["lines"].append(
                {"kind": "context", "old_line": old_line, "new_line": new_line, "text": raw_line[1:]}
            )
            old_line += 1
            new_line += 1

    finalize()

    known = {(item.get("old_path"), item.get("new_path")) for item in files}
    for status_item in statuses:
        key = (status_item.get("old_path"), status_item.get("new_path"))
        if key in known:
            continue
        path = status_item.get("new_path") or status_item.get("old_path")
        role = classify_path(path)
        files.append(
            {
                "old_path": status_item.get("old_path"),
                "new_path": status_item.get("new_path"),
                "status": status_item.get("status") or "modified",
                "role": role,
                "is_python": str(path or "").lower().endswith(".py"),
                "additions": 0,
                "deletions": 0,
                "binary": False,
                "hunks": [],
            }
        )

    canonical: dict[tuple[str, str | None, str | None], dict[str, Any]] = {}
    for item in files:
        status_item = _status_for_paths(statuses, item.get("old_path"), item.get("new_path"))
        status = str(item.get("status") or (status_item or {}).get("status") or "modified")
        item["status"] = status
        if status == "added":
            item["old_path"] = None
        elif status == "deleted":
            item["new_path"] = None
        item["role"] = classify_path(item.get("new_path") or item.get("old_path"))
        item["is_python"] = str(item.get("new_path") or item.get("old_path") or "").lower().endswith(".py")
        key = (status, item.get("old_path"), item.get("new_path"))
        previous = canonical.get(key)
        if previous is None or len(item.get("hunks", [])) > len(previous.get("hunks", [])):
            canonical[key] = item

    return sorted(canonical.values(), key=lambda item: (item.get("new_path") or item.get("old_path") or ""))


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            records.append(
                {
                    "_input_line": line_number,
                    "_input_error": {"code": "invalid_json", "message": str(exc)},
                }
            )
            continue
        if not isinstance(value, dict):
            records.append(
                {
                    "_input_line": line_number,
                    "_input_error": {"code": "record_not_object", "message": "JSONL 记录必须是对象"},
                }
            )
            continue
        record = dict(value)
        record["_input_line"] = line_number
        records.append(record)
    return records


def _source(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: record.get(key)
        for key in ("pr_number", "title", "url", "author", "merged_at", "sample_window", "size_band")
        if key in record
    }


def _error_object(record: dict[str, Any], errors: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "error",
        "repo": record.get("repo"),
        "pr_number": record.get("pr_number"),
        "source": _source(record),
        "errors": errors,
    }


def _validation(record: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    facts = record.get("change_facts")
    if not isinstance(facts, dict):
        return {"source_change_facts_present": False, "matches_source_change_facts": None}
    fields = {
        "files_changed": "files_changed",
        "additions": "additions",
        "deletions": "deletions",
        "business_changed": "business_changed",
        "test_changed": "test_changed",
        "test_cochanged": "test_cochanged",
    }
    matches = {
        source_key: facts.get(source_key) == summary.get(summary_key)
        for source_key, summary_key in fields.items()
        if source_key in facts
    }
    return {
        "source_change_facts_present": True,
        "matches_source_change_facts": all(matches.values()) if matches else None,
        "field_matches": matches,
    }


def build_change_object(record: dict[str, Any], repo_path: Path) -> dict[str, Any]:
    if "_input_error" in record:
        return _error_object(record, [record["_input_error"]])

    errors: list[dict[str, str]] = []
    for field in REQUIRED_FIELDS:
        if field not in record or record.get(field) in (None, ""):
            errors.append({"code": "missing_field", "message": f"缺少字段: {field}"})
    for field in ("base_sha", "head_sha"):
        if field in record and record.get(field) and not SHA_RE.fullmatch(str(record[field])):
            errors.append({"code": "invalid_sha", "message": f"{field} 不是 40 位提交 SHA"})
    if errors:
        return _error_object(record, errors)

    availability = record.get("availability")
    if isinstance(availability, dict):
        exclusion_reason = availability.get("exclusion_reason")
        if exclusion_reason or availability.get("diff_ok") is False:
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "excluded",
                "repo": record.get("repo"),
                "pr_number": record.get("pr_number"),
                "source": _source(record),
                "exclusion_reason": exclusion_reason or "unavailable",
                "errors": [],
            }

    base_sha = str(record["base_sha"])
    head_sha = str(record["head_sha"])
    try:
        verify_commit(repo_path, base_sha)
        verify_commit(repo_path, head_sha)
        merge_base = resolve_merge_base(repo_path, base_sha, head_sha)
        status_items = read_name_status(repo_path, base_sha, head_sha)
        diff_text = read_diff_text(repo_path, base_sha, head_sha)
        files = parse_unified_diff(diff_text, status_items)
    except DatasetError as exc:
        return _error_object(
            record,
            [{"code": "git_error", "message": str(exc)}],
        )

    business_files = sum(item["role"] == "business" for item in files)
    test_files = sum(item["role"] == "test" for item in files)
    other_files = sum(item["role"] == "other" for item in files)
    additions = sum(int(item["additions"]) for item in files)
    deletions = sum(int(item["deletions"]) for item in files)
    business_changed = business_files > 0
    test_changed = test_files > 0
    summary = {
        "files_changed": len(files),
        "business_files": business_files,
        "test_files": test_files,
        "other_files": other_files,
        "additions": additions,
        "deletions": deletions,
        "business_changed": business_changed,
        "test_changed": test_changed,
        "test_cochanged": business_changed and test_changed,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "repo": record.get("repo"),
        "pr_number": record.get("pr_number"),
        "base_sha": base_sha,
        "head_sha": head_sha,
        "merge_base_sha": merge_base,
        "diff_mode": "three_dot",
        "source": _source(record),
        "files": files,
        "summary": summary,
        "validation": _validation(record, summary),
        "errors": [],
    }


def select_records(records: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    if limit is None:
        return records
    if limit < 1:
        raise ValueError("limit 必须大于 0")
    candidates = [
        record
        for record in records
        if "_input_error" not in record
        and isinstance(record.get("availability"), dict)
        and record["availability"].get("diff_ok")
        and not record["availability"].get("exclusion_reason")
        and isinstance(record.get("change_facts"), dict)
        and record["change_facts"].get("business_changed")
    ]
    candidates.sort(key=lambda item: int(item.get("pr_number") or 0))
    selected: list[dict[str, Any]] = []
    for band in SIZE_ORDER:
        for candidate in candidates:
            if candidate.get("size_band") == band and candidate not in selected:
                selected.append(candidate)
                break
        if len(selected) >= limit:
            return selected[:limit]
    for candidate in candidates:
        if candidate not in selected:
            selected.append(candidate)
        if len(selected) >= limit:
            break
    return selected[:limit]


def write_jsonl(objects: Iterable[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for item in objects:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def build_from_jsonl(
    input_path: Path,
    repo_path: Path,
    output_path: Path,
    manifest_path: Path | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    records = load_records(input_path)
    selected = select_records(records, limit)
    objects = [build_change_object(record, repo_path) for record in selected]
    write_jsonl(objects, output_path)

    counts = Counter(item["status"] for item in objects)
    validation_mismatches = [
        item["pr_number"]
        for item in objects
        if item.get("status") == "ok"
        and item.get("validation", {}).get("matches_source_change_facts") is False
    ]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "input_path": str(input_path),
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "repo": "netbox-community/netbox",
        "selection_limit": limit,
        "input_records": len(records),
        "selected_records": len(selected),
        "status_counts": dict(sorted(counts.items())),
        "validation_mismatch_count": len(validation_mismatches),
        "validation_mismatch_pr_numbers": validation_mismatches,
        "selected_pr_numbers": [item.get("pr_number") for item in selected if item.get("pr_number") is not None],
        "pilot_pr_numbers": [179, 19, 226] if limit == 3 else [],
        "output_path": str(output_path),
    }
    if manifest_path is not None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest
