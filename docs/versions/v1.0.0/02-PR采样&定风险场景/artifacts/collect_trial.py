"""Saleor 试采样：抽取已合并 PR，写入 JSONL，并汇总场景表。"""

from __future__ import annotations

import argparse
import ast
import json
import os
import random
import re
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parent
REPO = ROOT / "repos" / "saleor"
CACHE = ROOT / "repos" / "api-cache"
JSONL_PATH = ROOT / "saleor-trial.jsonl"
TABLE_PATH = ROOT / "场景表.md"
SUMMARY_PATH = ROOT / "summary.json"
SELECTION_PATH = CACHE / "selection.json"

REPO_NAME = "saleor/saleor"
SEED = 20261028
TARGET = 40
POOL_PER_WINDOW = 36
WINDOWS = (
    ("2017-01-01", "2019-12-31"),
    ("2020-01-01", "2021-12-31"),
    ("2022-01-01", "2023-12-31"),
    ("2024-01-01", "2026-10-28"),
)
SCENE_ORDER = ("api", "auth", "data_transaction", "config_exception")
SCENE_TEXT = {
    "api": ("接口行为", "GraphQL、webhook 或 schema 文件变化"),
    "auth": ("认证与权限", "权限模块、认证模块，或权限判断代码变化"),
    "data_transaction": ("数据与事务", "模型、迁移、事务或回滚变化"),
    "config_exception": ("配置与异常", "设置文件、异常模块，或异常捕获变化"),
}
WEAK_SIGNALS = {"except_clause"}
DIFF_SIGNALS = {"permission_diff", "atomic_or_rollback", "except_clause"}
OTHER_SUFFIXES = {
    ".md",
    ".rst",
    ".txt",
    ".lock",
    ".po",
    ".pot",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".pdf",
    ".csv",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".css",
    ".scss",
    ".html",
    ".vue",
    ".map",
}
PRAISE_RE = re.compile(
    r"(?i)^(lgtm|looks good( to me)?|lg|thanks|thank you|approved|nice|great|\+1|ship it|👍|✅)[.!]?$"
)
PERMISSION_RE = re.compile(
    r"permission_required|one_of_permissions|check_permissions|Permissions\."
)
EXCEPT_RE = re.compile(r"^except\b")
ATOMIC_RE = re.compile(r"transaction\.atomic|\.rollback\(")


def run(args: list[str], cwd: Path | None = None, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        env=env,
    )


def gh_json(args: list[str], cache_name: str | None = None, retries: int = 5) -> object:
    if cache_name:
        path = CACHE / cache_name
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    last_error = ""
    for attempt in range(retries):
        result = run(["gh", *args], timeout=180)
        if result.returncode == 0 and result.stdout.strip():
            payload = json.loads(result.stdout)
            if cache_name:
                CACHE.mkdir(parents=True, exist_ok=True)
                (CACHE / cache_name).write_text(
                    json.dumps(payload, ensure_ascii=False),
                    encoding="utf-8",
                )
            return payload
        last_error = (result.stderr or result.stdout or "gh 调用失败").strip()
        if "rate limit" in last_error.lower() or result.returncode != 0:
            time.sleep(5 * (attempt + 1))
            continue
        break
    raise RuntimeError(last_error)


def is_sample_bot(login: str) -> bool:
    name = (login or "").lower()
    return "dependabot" in name or "renovate" in name


def is_machine(login: str) -> bool:
    name = (login or "").lower()
    if name.endswith("[bot]") or name.endswith("-bot"):
        return True
    tokens = ("dependabot", "renovate", "claassistant", "codecov", "github-actions")
    return any(token in name for token in tokens)


def window_label(start: str, end: str) -> str:
    return f"{start}..{end}"


def search_window(start: str, end: str, order: str) -> list[dict[str, object]]:
    query = quote(f"repo:{REPO_NAME} is:pr is:merged merged:{start}..{end}", safe="")
    path = f"search/issues?q={query}&per_page=100&sort=created&order={order}"
    payload = gh_json(
        ["api", path, "-H", "Accept: application/vnd.github+json"],
        cache_name=f"search-{start}-{end}-{order}.json",
    )
    if not isinstance(payload, dict):
        return []
    items = payload.get("items") or []
    found: list[dict[str, object]] = []
    for item in items:
        if not isinstance(item, dict) or "pull_request" not in item:
            continue
        user = item.get("user") or {}
        login = user.get("login", "") if isinstance(user, dict) else ""
        if is_sample_bot(str(login)):
            continue
        found.append(
            {
                "pr_number": int(item["number"]),
                "title": item.get("title") or "",
                "author": login,
                "sample_window": window_label(start, end),
            }
        )
    return found


def spread(items: list[dict[str, object]], count: int) -> list[dict[str, object]]:
    if len(items) <= count:
        return list(items)
    if count <= 1:
        return [items[0]]
    last = len(items) - 1
    return [items[round(i * last / (count - 1))] for i in range(count)]


def size_band(changed_files: int) -> str:
    if changed_files <= 5:
        return "small"
    if changed_files <= 20:
        return "medium"
    return "large"


def light_pull(number: int) -> dict[str, object]:
    payload = gh_json(
        [
            "api",
            f"repos/{REPO_NAME}/pulls/{number}",
            "-H",
            "Accept: application/vnd.github+json",
        ],
        cache_name=f"pull-{number}.json",
    )
    if not isinstance(payload, dict):
        raise RuntimeError(f"PR {number} 详情不是对象")
    user = payload.get("user") or {}
    login = user.get("login", "") if isinstance(user, dict) else ""
    return {
        "changed_files": int(payload.get("changed_files") or 0),
        "additions": int(payload.get("additions") or 0),
        "deletions": int(payload.get("deletions") or 0),
        "merged_at": payload.get("merged_at"),
        "author": login,
        "title": payload.get("title") or "",
        "url": payload.get("html_url") or f"https://github.com/{REPO_NAME}/pull/{number}",
        "base_sha": (payload.get("base") or {}).get("sha"),
        "head_sha": (payload.get("head") or {}).get("sha"),
    }


def build_pool() -> list[dict[str, object]]:
    pooled: list[dict[str, object]] = []
    seen: set[int] = set()
    for start, end in WINDOWS:
        merged: dict[int, dict[str, object]] = {}
        for order in ("asc", "desc"):
            for item in search_window(start, end, order):
                merged[int(item["pr_number"])] = item
        ordered = [merged[number] for number in sorted(merged)]
        for item in spread(ordered, POOL_PER_WINDOW):
            number = int(item["pr_number"])
            if number in seen:
                continue
            seen.add(number)
            try:
                detail = light_pull(number)
            except (RuntimeError, json.JSONDecodeError, KeyError) as error:
                print(f"skip {number}: {error}", flush=True)
                continue
            if is_sample_bot(str(detail["author"])):
                continue
            if not detail["merged_at"]:
                continue
            item.update(detail)
            item["size_band"] = size_band(int(detail["changed_files"]))
            pooled.append(item)
            time.sleep(0.15)
    return pooled


def select_sample(pool: list[dict[str, object]]) -> list[dict[str, object]]:
    cells: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for item in pool:
        cells[(str(item["sample_window"]), str(item["size_band"]))].append(item)
    rng = random.Random(SEED)
    for bucket in cells.values():
        rng.shuffle(bucket)
    keys = sorted(cells)
    selected: list[dict[str, object]] = []
    authors: set[str] = set()
    while len(selected) < TARGET:
        progressed = False
        for key in keys:
            bucket = cells[key]
            if not bucket:
                continue
            index = next((i for i, item in enumerate(bucket) if item["author"] not in authors), 0)
            chosen = bucket.pop(index)
            selected.append(chosen)
            authors.add(str(chosen["author"]))
            progressed = True
            if len(selected) >= TARGET:
                break
        if not progressed:
            break
    return selected


def load_selection(reselect: bool) -> list[dict[str, object]]:
    if SELECTION_PATH.exists() and not reselect:
        payload = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
        return list(payload["selected"])
    pool = build_pool()
    selected = select_sample(pool)
    CACHE.mkdir(parents=True, exist_ok=True)
    SELECTION_PATH.write_text(
        json.dumps(
            {
                "seed": SEED,
                "queried_at": datetime.now(timezone.utc).isoformat(),
                "windows": [window_label(start, end) for start, end in WINDOWS],
                "pool_count": len(pool),
                "selected": selected,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return selected


def git_ok(sha: str) -> bool:
    if not sha:
        return False
    result = run(["git", "cat-file", "-t", sha], cwd=REPO)
    return result.returncode == 0 and result.stdout.strip() == "commit"


def ensure_commit(sha: str, pr_number: int, kind: str) -> bool:
    if git_ok(sha):
        return True
    if kind == "head":
        run(["git", "fetch", "--no-tags", "origin", f"pull/{pr_number}/head"], cwd=REPO, timeout=180)
    else:
        run(["git", "fetch", "--no-tags", "origin", sha], cwd=REPO, timeout=180)
    return git_ok(sha)


def parse_name_status(text: str) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\t")
        status = parts[0]
        if status.startswith("R") or status.startswith("C"):
            path = parts[-1]
            change = "renamed" if status.startswith("R") else "added"
        elif status == "A":
            path = parts[-1]
            change = "added"
        elif status == "D":
            path = parts[-1]
            change = "deleted"
        elif status == "M" or status.startswith("T"):
            path = parts[-1]
            change = "modified"
        else:
            path = parts[-1]
            change = "modified"
        files.append({"path": path.replace("\\", "/"), "status": change})
    return files


def file_role(path: str) -> str:
    name = path.replace("\\", "/").lower()
    base = name.rsplit("/", 1)[-1]
    padded = f"/{name}"
    if "/tests/" in padded or "/test/" in padded or base.startswith("test_") or base.endswith("_test.py"):
        return "test"
    if (
        name.startswith("docs/")
        or name.startswith("templates/")
        or "/docs/" in padded
        or "/locale/" in padded
        or "/locales/" in padded
        or "/static/" in padded
        or "/templates/" in padded
    ):
        return "other"
    suffix = f".{base.rsplit('.', 1)[-1]}" if "." in base else ""
    if suffix in OTHER_SUFFIXES or base.endswith(".lock"):
        return "other"
    return "business"


def empty_scenes() -> dict[str, dict[str, object]]:
    return {
        key: {"hit": False, "where": [], "signals": [], "path_signals": {}}
        for key in SCENE_ORDER
    }


def add_signal(scenes: dict[str, dict[str, object]], scene: str, path: str, signal: str) -> None:
    bucket = scenes[scene]
    where = bucket["where"]
    signals = bucket["signals"]
    path_signals = bucket["path_signals"]
    assert isinstance(where, list)
    assert isinstance(signals, list)
    assert isinstance(path_signals, dict)
    if path not in where and len(where) < 40:
        where.append(path)
    if signal not in signals:
        signals.append(signal)
    current = path_signals.setdefault(path, [])
    if isinstance(current, list) and signal not in current:
        current.append(signal)
    bucket["hit"] = True


def tag_path(scenes: dict[str, dict[str, object]], path: str) -> None:
    lowered = path.lower()
    if "/graphql/" in f"/{lowered}" or lowered.endswith(".graphql"):
        signal = "graphql_file" if lowered.endswith(".graphql") else "graphql_path"
        add_signal(scenes, "api", path, signal)
    if "/webhook/" in f"/{lowered}":
        add_signal(scenes, "api", path, "webhook_path")
    if "/permission" in lowered or "permissions" in lowered or "/auth/" in f"/{lowered}" or "jwt" in lowered:
        signal = "permission_path" if "permission" in lowered else "auth_path"
        add_signal(scenes, "auth", path, signal)
    if "/migrations/" in f"/{lowered}":
        add_signal(scenes, "data_transaction", path, "migration_path")
    if lowered.endswith("/models.py") or lowered.endswith("/managers.py"):
        add_signal(scenes, "data_transaction", path, "model_path")
    if lowered.endswith("/settings.py") or "/settings/" in f"/{lowered}":
        add_signal(scenes, "config_exception", path, "settings_path")
    filename = lowered.rsplit("/", 1)[-1]
    if "exception" in filename:
        add_signal(scenes, "config_exception", path, "exception_path")


def scan_diff(scenes: dict[str, dict[str, object]], diff_text: str, roles: dict[str, str]) -> None:
    current: str | None = None
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            marker = " b/"
            current = line.rsplit(marker, 1)[-1].replace("\\", "/") if marker in line else None
            continue
        if current is None or roles.get(current) != "business":
            continue
        if not line.startswith(("+", "-")) or line.startswith(("+++", "---")):
            continue
        body = line[1:].strip()
        lowered = body.lower()
        if PERMISSION_RE.search(body):
            add_signal(scenes, "auth", current, "permission_diff")
        if "transaction.atomic" in lowered or ATOMIC_RE.search(lowered):
            add_signal(scenes, "data_transaction", current, "atomic_or_rollback")
        if EXCEPT_RE.match(body):
            add_signal(scenes, "config_exception", current, "except_clause")


def read_diff(base_sha: str, head_sha: str) -> tuple[bool, str]:
    result = run(
        [
            "git",
            "-c",
            "core.quotepath=false",
            "diff",
            "--no-color",
            "--find-renames",
            "-U0",
            f"{base_sha}...{head_sha}",
        ],
        cwd=REPO,
        timeout=180,
    )
    return result.returncode == 0, result.stdout


def commits_after(base_sha: str, head_sha: str) -> list[dict[str, object]]:
    result = run(
        [
            "git",
            "-c",
            "core.quotepath=false",
            "log",
            "--right-only",
            "--reverse",
            "--name-only",
            "--pretty=format:COMMIT%x09%cI%x09%s",
            f"{base_sha}...{head_sha}",
        ],
        cwd=REPO,
        timeout=180,
    )
    if result.returncode != 0:
        return []
    commits: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line in result.stdout.splitlines():
        if line.startswith("COMMIT\t"):
            _, when, subject = (line.split("\t", 2) + ["", ""])[:3]
            current = {"at": when, "subject": subject, "files": []}
            commits.append(current)
            continue
        if current is not None and line.strip():
            files = current["files"]
            assert isinstance(files, list)
            files.append(line.strip().replace("\\", "/"))
    return commits


def parse_python(head_sha: str, files: list[dict[str, str]]) -> dict[str, object]:
    targets = [
        item["path"]
        for item in files
        if item["path"].endswith(".py") and item["status"] != "deleted" and item["role"] in {"business", "test"}
    ]
    if not targets:
        return {
            "attempted": False,
            "ok": None,
            "failure_reason": None,
            "files_attempted": 0,
            "files_ok": 0,
        }
    ok_count = 0
    failures: list[str] = []
    for path in targets:
        shown = run(["git", "show", f"{head_sha}:{path}"], cwd=REPO)
        if shown.returncode != 0:
            failures.append(f"{path}: 目标版本读不到该文件")
            continue
        try:
            ast.parse(shown.stdout)
        except SyntaxError as error:
            failures.append(f"{path}: {error.msg}")
            continue
        ok_count += 1
    return {
        "attempted": True,
        "ok": ok_count == len(targets),
        "failure_reason": "; ".join(failures[:3]) or None,
        "files_attempted": len(targets),
        "files_ok": ok_count,
    }


def iso_after(left: str, right: str) -> bool:
    try:
        first = datetime.fromisoformat(left.replace("Z", "+00:00"))
        second = datetime.fromisoformat(right.replace("Z", "+00:00"))
    except ValueError:
        return False
    return second > first


def is_praise(body: str) -> bool:
    text = re.sub(r"\s+", " ", body or "").strip()
    if not text:
        return True
    return bool(PRAISE_RE.fullmatch(text))


def fetch_inline(number: int) -> list[dict[str, object]]:
    comments: list[dict[str, object]] = []
    page = 1
    while page <= 10:
        payload = gh_json(
            [
                "api",
                f"repos/{REPO_NAME}/pulls/{number}/comments?per_page=100&page={page}",
                "-H",
                "Accept: application/vnd.github+json",
            ],
            cache_name=f"inline-{number}-p{page}.json",
        )
        if not isinstance(payload, list) or not payload:
            break
        comments.extend(item for item in payload if isinstance(item, dict))
        if len(payload) < 100:
            break
        page += 1
    return comments


def fetch_checks(head_sha: str) -> str:
    if not head_sha:
        return "missing"
    payload = gh_json(
        [
            "api",
            f"repos/{REPO_NAME}/commits/{head_sha}/check-runs?per_page=100",
            "-H",
            "Accept: application/vnd.github+json",
        ],
        cache_name=f"checks-{head_sha}.json",
    )
    runs = payload.get("check_runs") if isinstance(payload, dict) else None
    conclusions = []
    if isinstance(runs, list):
        conclusions = [str(item.get("conclusion") or item.get("status") or "").lower() for item in runs if isinstance(item, dict)]
    if not conclusions:
        status = gh_json(
            [
                "api",
                f"repos/{REPO_NAME}/commits/{head_sha}/status",
                "-H",
                "Accept: application/vnd.github+json",
            ],
            cache_name=f"status-{head_sha}.json",
        )
        if isinstance(status, dict) and int(status.get("total_count") or 0) == 0:
            return "missing"
        state = str(status.get("state") or "").lower() if isinstance(status, dict) else ""
        if state in {"failure", "error"}:
            return "failure"
        if state == "pending":
            return "pending"
        if state == "success":
            return "success"
        return "missing"
    if any(item in {"failure", "failed", "error", "timed_out"} for item in conclusions):
        return "failure"
    if any(item in {"pending", "queued", "in_progress"} for item in conclusions):
        return "pending"
    if any(item == "success" for item in conclusions):
        return "success"
    return "missing"


def pr_view(number: int) -> dict[str, object]:
    payload = gh_json(
        [
            "pr",
            "view",
            str(number),
            "--repo",
            REPO_NAME,
            "--json",
            "number,title,author,mergedAt,additions,deletions,changedFiles,baseRefOid,headRefOid,url,files,reviews,comments,commits,body",
        ],
        cache_name=f"view-{number}.json",
    )
    if not isinstance(payload, dict):
        raise RuntimeError(f"PR {number} 视图不是对象")
    return payload


def author_login(view: dict[str, object], fallback: str) -> str:
    author = view.get("author")
    if isinstance(author, dict) and author.get("login"):
        return str(author["login"])
    return fallback


def evaluate(view: dict[str, object], inline: list[dict[str, object]], commit_rows: list[dict[str, object]], author: str) -> dict[str, object]:
    reviews = view.get("reviews") if isinstance(view.get("reviews"), list) else []
    changes_requested = any(isinstance(item, dict) and item.get("state") == "CHANGES_REQUESTED" for item in reviews)
    human_inline = []
    for item in inline:
        user = item.get("user") or {}
        login = user.get("login", "") if isinstance(user, dict) else ""
        if is_machine(str(login)) or login == author:
            continue
        human_inline.append(item)
    followup = False
    linked_request = False
    for item in human_inline:
        path = str(item.get("path") or "").replace("\\", "/")
        created = str(item.get("created_at") or "")
        if not path:
            continue
        later = [
            row
            for row in commit_rows
            if iso_after(created, str(row.get("at") or "")) and path in (row.get("files") or [])
        ]
        if later:
            followup = True
            if not is_praise(str(item.get("body") or "")):
                linked_request = True
    review_request = False
    for item in reviews:
        if not isinstance(item, dict):
            continue
        login = ""
        review_author = item.get("author")
        if isinstance(review_author, dict):
            login = str(review_author.get("login") or "")
        if is_machine(login) or login == author:
            continue
        if item.get("state") == "CHANGES_REQUESTED" or not is_praise(str(item.get("body") or "")):
            review_request = True
    if linked_request:
        label = "needs_attention"
    elif changes_requested or review_request or any(not is_praise(str(item.get("body") or "")) for item in human_inline):
        label = "uncertain"
    else:
        label = "not_flagged"
    post_merge_fix = direct_revert(str(view.get("title") or ""), commit_rows)
    return {
        "review_count": len(reviews),
        "inline_comment_count": len(human_inline),
        "changes_requested": changes_requested,
        "followup_after_comment": followup,
        "ci": "missing",
        "post_merge_fix": post_merge_fix,
        "label": label,
    }


def build_record(selected: dict[str, object]) -> dict[str, object]:
    number = int(selected["pr_number"])
    view = pr_view(number)
    author = author_login(view, str(selected.get("author") or ""))
    base_sha = str(view.get("baseRefOid") or selected.get("base_sha") or "")
    head_sha = str(view.get("headRefOid") or selected.get("head_sha") or "")
    base_ok = ensure_commit(base_sha, number, "base")
    head_ok = ensure_commit(head_sha, number, "head")
    diff_ok = False
    diff_text = ""
    files: list[dict[str, object]] = []
    if base_ok and head_ok:
        diff_ok, diff_text = read_diff(base_sha, head_sha)
        if diff_ok:
            name_status = run(
                [
                    "git",
                    "-c",
                    "core.quotepath=false",
                    "diff",
                    "--name-status",
                    "--find-renames",
                    f"{base_sha}...{head_sha}",
                ],
                cwd=REPO,
            )
            parsed = parse_name_status(name_status.stdout if name_status.returncode == 0 else "")
            line_counts: dict[str, dict[str, int]] = {}
            for item in view.get("files") or []:
                if isinstance(item, dict) and item.get("path"):
                    line_counts[str(item["path"])] = {
                        "additions": int(item.get("additions") or 0),
                        "deletions": int(item.get("deletions") or 0),
                    }
            for item in parsed:
                counts = line_counts.get(item["path"], {})
                files.append(
                    {
                        "path": item["path"],
                        "status": item["status"],
                        "role": file_role(item["path"]),
                        "additions": counts.get("additions"),
                        "deletions": counts.get("deletions"),
                    }
                )
    roles = {str(item["path"]): str(item["role"]) for item in files}
    scenes = empty_scenes()
    for item in files:
        if item["role"] == "business":
            tag_path(scenes, str(item["path"]))
    if diff_text:
        scan_diff(scenes, diff_text, roles)
    business_changed = any(item["role"] == "business" for item in files)
    test_changed = any(item["role"] == "test" for item in files)
    if not base_ok or not head_ok:
        exclusion = "unrecoverable"
    elif not diff_ok or not files:
        exclusion = "incomplete"
    elif not business_changed and not test_changed:
        exclusion = "docs_only"
    else:
        exclusion = None
    parse_info = (
        parse_python(head_sha, files)  # type: ignore[arg-type]
        if diff_ok and head_ok
        else {
            "attempted": False,
            "ok": None,
            "failure_reason": None,
            "files_attempted": 0,
            "files_ok": 0,
        }
    )
    commit_rows = commits_after(base_sha, head_sha) if base_ok and head_ok else []
    inline = fetch_inline(number)
    evaluation = evaluate(view, inline, commit_rows, author)
    evaluation["ci"] = fetch_checks(head_sha) if head_ok else "missing"
    return {
        "repo": REPO_NAME,
        "pr_number": number,
        "title": view.get("title") or selected.get("title") or "",
        "url": view.get("url") or selected.get("url"),
        "author": author,
        "merged_at": view.get("mergedAt") or selected.get("merged_at"),
        "base_sha": base_sha,
        "head_sha": head_sha,
        "sample_window": selected.get("sample_window"),
        "size_band": selected.get("size_band"),
        "availability": {
            "base_ok": base_ok,
            "head_ok": head_ok,
            "diff_ok": diff_ok and bool(files),
            "exclusion_reason": exclusion,
        },
        "change_facts": {
            "files_changed": len(files),
            "additions": view.get("additions", selected.get("additions")),
            "deletions": view.get("deletions", selected.get("deletions")),
            "files": [{key: item[key] for key in ("path", "status", "role")} for item in files],
            "business_changed": business_changed,
            "test_changed": test_changed,
            "test_cochanged": business_changed and test_changed,
            "scenes": scenes,
            "scene_source": "path_and_diff",
            "parse": parse_info,
        },
        "evaluation": evaluation,
    }


def direct_revert(title: str, commit_rows: list[dict[str, object]]) -> object:
    if re.search(r"(?i)^revert\b", title.strip()):
        return True
    for row in commit_rows:
        subject = str(row.get("subject") or "").strip()
        if re.search(r"(?i)^revert\b", subject):
            return True
    return "unknown"


def reclassify_record(record: dict[str, object]) -> dict[str, object]:
    facts = record["change_facts"]
    assert isinstance(facts, dict)
    files = facts.get("files") or []
    assert isinstance(files, list)
    for item in files:
        if isinstance(item, dict) and item.get("path"):
            item["role"] = file_role(str(item["path"]))
    scenes = empty_scenes()
    old_scenes = facts.get("scenes") or {}
    assert isinstance(old_scenes, dict)
    for item in files:
        if isinstance(item, dict) and item.get("role") == "business":
            tag_path(scenes, str(item["path"]))
    for scene, info in old_scenes.items():
        if scene not in scenes or not isinstance(info, dict):
            continue
        path_signals = info.get("path_signals") or {}
        if not isinstance(path_signals, dict):
            continue
        for path, signals in path_signals.items():
            if file_role(str(path)) != "business" or not isinstance(signals, list):
                continue
            for signal in signals:
                if signal in DIFF_SIGNALS:
                    add_signal(scenes, scene, str(path), str(signal))
    business_changed = any(isinstance(item, dict) and item.get("role") == "business" for item in files)
    test_changed = any(isinstance(item, dict) and item.get("role") == "test" for item in files)
    facts["files"] = files
    facts["business_changed"] = business_changed
    facts["test_changed"] = test_changed
    facts["test_cochanged"] = business_changed and test_changed
    facts["scenes"] = scenes
    availability = record["availability"]
    assert isinstance(availability, dict)
    if availability.get("diff_ok") and availability.get("exclusion_reason") in {None, "docs_only"}:
        availability["exclusion_reason"] = None if business_changed or test_changed else "docs_only"
    evaluation = record["evaluation"]
    assert isinstance(evaluation, dict)
    if evaluation.get("post_merge_fix") is True and not re.search(r"(?i)^revert\b", str(record.get("title") or "").strip()):
        evaluation["post_merge_fix"] = "unknown"
    return record


def analyzable(record: dict[str, object]) -> bool:
    availability = record["availability"]
    assert isinstance(availability, dict)
    return bool(availability.get("diff_ok")) and availability.get("exclusion_reason") is None


def diversity_key(path: str) -> str:
    parts = path.split("/")
    if len(parts) >= 3 and parts[0] == "saleor" and parts[1] == "graphql":
        return f"graphql/{parts[2]}"
    if len(parts) >= 2:
        return "/".join(parts[:2])
    return path


def scene_decision(records: list[dict[str, object]], scene: str) -> dict[str, object]:
    hits = []
    signal_counts: dict[str, int] = defaultdict(int)
    for record in records:
        facts = record["change_facts"]
        assert isinstance(facts, dict)
        scenes = facts["scenes"]
        assert isinstance(scenes, dict)
        info = scenes[scene]
        assert isinstance(info, dict)
        strong = [item for item in info.get("signals") or [] if item not in WEAK_SIGNALS]
        if not strong:
            continue
        hits.append(record)
        for signal in set(strong):
            signal_counts[str(signal)] += 1
    qualifying = sorted(signal for signal, count in signal_counts.items() if count >= 3)
    signals: set[str] = set()
    keys: set[str] = set()
    for record in hits:
        facts = record["change_facts"]
        assert isinstance(facts, dict)
        info = facts["scenes"][scene]
        assert isinstance(info, dict)
        path_signals = info.get("path_signals") or {}
        assert isinstance(path_signals, dict)
        for path, path_signal in path_signals.items():
            strong = [item for item in path_signal if item not in WEAK_SIGNALS and item in qualifying]
            signals.update(strong)
            if strong:
                keys.add(diversity_key(str(path)))
    attempted = []
    ok_count = 0
    for record in hits:
        facts = record["change_facts"]
        assert isinstance(facts, dict)
        parsed = facts["parse"]
        assert isinstance(parsed, dict)
        if parsed.get("attempted"):
            attempted.append(record)
            if parsed.get("ok"):
                ok_count += 1
    rate = (ok_count / len(attempted)) if attempted else None
    labels = defaultdict(int)
    for record in hits:
        evaluation = record["evaluation"]
        assert isinstance(evaluation, dict)
        labels[str(evaluation.get("label"))] += 1
    count = len(hits)
    parse_ok = rate is None or rate >= 0.8
    if count < 3:
        decision = "不纳入"
    elif count >= 8 and len(qualifying) >= 2 and parse_ok:
        decision = "纳入"
    else:
        decision = "案例"
    return {
        "count": count,
        "signals": sorted(signals),
        "signal_counts": dict(signal_counts),
        "qualifying_signals": qualifying,
        "diversity_keys": sorted(keys),
        "parse_rate": rate,
        "parse_attempted": len(attempted),
        "labels": dict(labels),
        "decision": decision,
    }


def write_outputs(records: list[dict[str, object]], selection_meta: dict[str, object]) -> dict[str, object]:
    ordered = sorted(records, key=lambda item: int(item["pr_number"]))
    JSONL_PATH.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in ordered),
        encoding="utf-8",
    )
    analyzable_records = [item for item in ordered if analyzable(item)]
    decisions = {scene: scene_decision(analyzable_records, scene) for scene in SCENE_ORDER}
    business_records = []
    for record in analyzable_records:
        facts = record["change_facts"]
        assert isinstance(facts, dict)
        if facts.get("business_changed"):
            business_records.append(record)
    cochanged = 0
    for record in business_records:
        facts = record["change_facts"]
        assert isinstance(facts, dict)
        if facts.get("test_cochanged"):
            cochanged += 1
    included = [scene for scene, info in decisions.items() if info["decision"] == "纳入"]
    exclusions = defaultdict(int)
    recovered = 0
    for record in ordered:
        availability = record["availability"]
        assert isinstance(availability, dict)
        if availability.get("base_ok") and availability.get("head_ok"):
            recovered += 1
        reason = availability.get("exclusion_reason")
        if reason:
            exclusions[str(reason)] += 1
    lock = len(analyzable_records) >= 20 and len(included) >= 2
    summary = {
        "queried_at": selection_meta.get("queried_at"),
        "seed": SEED,
        "windows": selection_meta.get("windows"),
        "selected_count": len(ordered),
        "author_count": len({str(item["author"]) for item in ordered}),
        "recovered_count": recovered,
        "analyzable_count": len(analyzable_records),
        "exclusions": dict(exclusions),
        "size_bands": dict(defaultdict(int, {band: sum(1 for item in ordered if item["size_band"] == band) for band in ("small", "medium", "large")})),
        "windows_selected": dict(defaultdict(int, {str(item["sample_window"]): sum(1 for row in ordered if row["sample_window"] == item["sample_window"]) for item in ordered})),
        "scenes": decisions,
        "business_changed": len(business_records),
        "test_cochanged": cochanged,
        "passes_sampling_gate": lock,
        "included_scenes": included,
        "parse_note": "语法检查使用 Python 标准库 ast.parse，解析的是目标版本上的 .py 文件。框架级结构对齐不在这一阶段。",
        "label_note": "needs_attention 表示审查者的非客套行内评论指向某个文件，且之后有提交改了该文件。只有评论、无法对应到后续文件时记为 uncertain。合并后修复只在 PR 标题或提交标题以 Revert 开头时记为 true，模板里的 revert option 不算。",
        "bot_rule": "抽样排除作者名包含 dependabot 或 renovate 的 PR。",
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_table(summary, len(analyzable_records))
    return summary


def percent(rate: float | None) -> str:
    if rate is None:
        return "没有可解析的 Python 文件"
    return f"{rate * 100:.0f}%"


def evidence_text(labels: dict[str, int]) -> str:
    return (
        f"需关注 {labels.get('needs_attention', 0)}，"
        f"未标记 {labels.get('not_flagged', 0)}，"
        f"不确定 {labels.get('uncertain', 0)}"
    )


def write_table(summary: dict[str, object], analyzable_count: int) -> None:
    scenes = summary["scenes"]
    assert isinstance(scenes, dict)
    lines = [
        globals().get("TABLE_HEADING", "# Saleor 试采样场景表"),
        "",
        (
            f"查询日期 {str(summary.get('queried_at') or '')[:10]}。"
            f"抽样 {globals().get('SAMPLE_LINE_COUNT', TARGET)} 条，可分析 PR {analyzable_count} 条。"
            "场景是否出现只统计可分析 PR。"
        ),
        "",
        "| 风险场景 | 可识别的客观变化 | 可分析 PR 数量 | 可获得的正负证据 | 解析成功率 | 是否纳入规则 |",
        "| --- | --- | ---: | --- | ---: | --- |",
    ]
    for key in SCENE_ORDER:
        title, change = SCENE_TEXT[key]
        info = scenes[key]
        assert isinstance(info, dict)
        labels = info["labels"]
        assert isinstance(labels, dict)
        lines.append(
            f"| {title} | {change} | {info['count']} | {evidence_text(labels)} | {percent(info['parse_rate'] if isinstance(info['parse_rate'], float) else None)} | {info['decision']} |"
        )
    business_changed = int(summary["business_changed"])
    cochanged = int(summary["test_cochanged"])
    lines.append(
        "| 测试协同 | 业务文件变化时测试文件是否一起变化 | "
        f"{business_changed} | 同步修改测试 {cochanged}，未同步 {business_changed - cochanged} |  | 不占规则名额 |"
    )
    lines.append("")
    lines.append("单独的 except 行不计入配置与异常。一种变化类型至少要出现在 3 条可分析 PR 里才算数；纳入还要求命中不少于 8 条，并且至少有两种这样的类型。解析成功率是这些 PR 里 Python 文件能够被 ast.parse 解析的比例。")
    lines.append("")
    TABLE_PATH.write_text("\n".join(lines), encoding="utf-8")


def self_test() -> None:
    assert file_role("saleor/graphql/order/schema.py") == "business"
    assert file_role("saleor/order/tests/test_order.py") == "test"
    assert file_role("README.md") == "other"
    assert file_role("poetry.lock") == "other"
    assert file_role("saleor/static/js/storefront.js") == "other"
    assert file_role("templates/base.html") == "other"
    scenes = empty_scenes()
    tag_path(scenes, "saleor/graphql/order/schema.py")
    tag_path(scenes, "saleor/permission/enums.py")
    tag_path(scenes, "saleor/order/models.py")
    tag_path(scenes, "saleor/order/migrations/0001_initial.py")
    tag_path(scenes, "saleor/settings.py")
    assert scenes["api"]["hit"] is True
    assert scenes["auth"]["hit"] is True
    assert "migration_path" in scenes["data_transaction"]["signals"]
    assert "model_path" in scenes["data_transaction"]["signals"]
    assert scenes["config_exception"]["hit"] is True
    scan_diff(
        scenes,
        "\n".join(
            [
                "diff --git a/saleor/order/actions.py b/saleor/order/actions.py",
                "--- a/saleor/order/actions.py",
                "+++ b/saleor/order/actions.py",
                "+with transaction.atomic():",
                "+except ValueError:",
                "+@permission_required",
            ]
        ),
        {"saleor/order/actions.py": "business"},
    )
    assert "atomic_or_rollback" in scenes["data_transaction"]["signals"]
    assert "except_clause" in scenes["config_exception"]["signals"]
    assert "permission_diff" in scenes["auth"]["signals"]
    print("self-test ok")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reselect", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--rebuild-summary", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.rebuild_summary:
        records = [
            reclassify_record(json.loads(line))
            for line in JSONL_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        meta = json.loads(SELECTION_PATH.read_text(encoding="utf-8")) if SELECTION_PATH.exists() else {}
        summary = write_outputs(records, meta)
        print(
            json.dumps(
                {
                    "analyzable": summary["analyzable_count"],
                    "passes_sampling_gate": summary["passes_sampling_gate"],
                    "included": summary["included_scenes"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        return
    if not (REPO / ".git").exists():
        raise SystemExit(f"缺少仓库：{REPO}")
    CACHE.mkdir(parents=True, exist_ok=True)
    selected = load_selection(args.reselect)
    print(f"selected {len(selected)}", flush=True)
    if len(selected) < 30:
        raise SystemExit(f"只抽到 {len(selected)} 条，少于 30")
    records = []
    for index, item in enumerate(selected, start=1):
        number = int(item["pr_number"])
        print(f"[{index}/{len(selected)}] {number}", flush=True)
        try:
            records.append(build_record(item))
        except (RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired, OSError) as error:
            records.append(
                {
                    "repo": REPO_NAME,
                    "pr_number": number,
                    "title": item.get("title") or "",
                    "url": item.get("url"),
                    "author": item.get("author") or "",
                    "merged_at": item.get("merged_at"),
                    "base_sha": item.get("base_sha") or "",
                    "head_sha": item.get("head_sha") or "",
                    "sample_window": item.get("sample_window"),
                    "size_band": item.get("size_band"),
                    "availability": {
                        "base_ok": False,
                        "head_ok": False,
                        "diff_ok": False,
                        "exclusion_reason": "incomplete",
                        "error": str(error),
                    },
                    "change_facts": {
                        "files_changed": 0,
                        "additions": item.get("additions"),
                        "deletions": item.get("deletions"),
                        "files": [],
                        "business_changed": False,
                        "test_changed": False,
                        "test_cochanged": False,
                        "scenes": empty_scenes(),
                        "scene_source": "path_and_diff",
                        "parse": {
                            "attempted": False,
                            "ok": None,
                            "failure_reason": None,
                            "files_attempted": 0,
                            "files_ok": 0,
                        },
                    },
                    "evaluation": {
                        "review_count": 0,
                        "inline_comment_count": 0,
                        "changes_requested": False,
                        "followup_after_comment": False,
                        "ci": "missing",
                        "post_merge_fix": "unknown",
                        "label": "uncertain",
                    },
                }
            )
    meta = {}
    if SELECTION_PATH.exists():
        meta = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    summary = write_outputs(records, meta)
    print(
        json.dumps(
            {
                "analyzable": summary["analyzable_count"],
                "passes_sampling_gate": summary["passes_sampling_gate"],
                "included": summary["included_scenes"],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
