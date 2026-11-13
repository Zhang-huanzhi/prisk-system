"""Service orchestration for v1.4 formal evaluation isolation, sampling, repo materialization, and aggregation."""

from __future__ import annotations

import base64
import json
import random
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

from ..domain.config import PRESETS
from ..domain.evaluation import (
    DEFAULT_TARGET_REPO,
    EMPIRICAL_REPORT_SCHEMA_VERSION,
    VALID_TRACKS,
    build_exclusion_payload,
    compare_preset_runs,
    evaluate_annotations,
    load_config_payload,
    load_dataset_records,
    load_exclusion_numbers_from_sources,
    render_empirical_report_markdown,
    summarize_stage05_outcomes,
    verify_dataset_isolation,
)
from ..paths import project_root

GhRunner = Callable[[list[str]], Any]

DEFAULT_SAMPLE_WINDOWS: tuple[tuple[str, str], ...] = (
    ("2020-01-01", "2022-06-30"),
    ("2022-07-01", "2024-06-30"),
    ("2024-07-01", "2026-10-31"),
)

DEFAULT_TARGETED_TERMS: tuple[str, ...] = (
    "csrf_exempt",
    "permission",
    "migrations",
    "raw sql",
)

BOT_LOGINS = frozenset({
    "dependabot",
    "dependabot[bot]",
    "renovate",
    "renovate[bot]",
    "pre-commit-ci",
    "pre-commit-ci[bot]",
    "github-actions",
    "github-actions[bot]",
})


def default_survey_path() -> Path:
    """Return the frozen v1.0.0 NetBox survey JSONL path."""
    return project_root() / "docs" / "versions" / "v1.0.0" / "02-PR采样&定风险场景" / "artifacts" / "netbox-survey.jsonl"


def default_pilot_manifest_path() -> Path:
    """Return the frozen v1.1.0 pilot evaluation manifest path."""
    return project_root() / "docs" / "evaluation" / "pilot-v1.1" / "manifest.json"


def default_exclusion_list_path() -> Path:
    """Return the v1.4 permanent exclusion list JSON path."""
    return project_root() / "docs" / "evaluation" / "formal-v1.4" / "exclusion-list.json"


def _default_gh_executable() -> str:
    found = shutil.which("gh")
    if found:
        return found
    win_candidate = Path(r"C:\Program Files\GitHub CLI\gh.exe")
    if win_candidate.exists():
        return str(win_candidate)
    raise RuntimeError("未找到 gh CLI，请先安装并完成 GitHub CLI 认证。")


def default_gh_runner(args: list[str]) -> Any:
    """Invoke `gh` CLI and parse JSON stdout safely."""
    gh_exe = _default_gh_executable()
    completed = subprocess.run(
        [gh_exe, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or f"exit={completed.returncode}"
        raise RuntimeError(f"gh 命令执行失败 ({' '.join(args)}): {detail}")
    raw = completed.stdout.strip()
    if not raw:
        return {}
    return json.loads(raw)


def load_exclusion_numbers(
    *,
    survey_path: Path | None = None,
    pilot_manifest_path: Path | None = None,
    exclusion_json_path: Path | None = None,
    strict_sync: bool = True,
    default_repo: str = DEFAULT_TARGET_REPO,
) -> dict[str, Any]:
    """Load permanent exclusion PR numbers across v1.0 survey, v1.1 pilot manifest, and v1.4 exclusion JSON."""
    survey = survey_path or default_survey_path()
    pilot = pilot_manifest_path or default_pilot_manifest_path()
    exclusion_json = exclusion_json_path if exclusion_json_path is not None else default_exclusion_list_path()
    active_json = exclusion_json if strict_sync and exclusion_json.exists() else (
        exclusion_json if exclusion_json_path is not None else None
    )
    return load_exclusion_numbers_from_sources(
        survey_path=survey,
        pilot_manifest_path=pilot,
        exclusion_json_path=active_json,
        default_repo=default_repo,
    )


def sync_exclusion_list(
    *,
    survey_path: Path | None = None,
    pilot_manifest_path: Path | None = None,
    output_path: Path | None = None,
    check_only: bool = False,
    default_repo: str = DEFAULT_TARGET_REPO,
) -> dict[str, Any]:
    """Generate or verify docs/evaluation/formal-v1.4/exclusion-list.json against frozen historical sets."""
    survey = survey_path or default_survey_path()
    pilot = pilot_manifest_path or default_pilot_manifest_path()
    target = output_path or default_exclusion_list_path()
    payload = build_exclusion_payload(
        survey_path=survey,
        pilot_manifest_path=pilot,
        default_repo=default_repo,
    )
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if check_only:
        if not target.exists():
            raise ValueError(f"永久排除清单尚不存在: {target}")
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing != payload:
            raise ValueError(f"永久排除清单与 v1.0/v1.1 源清单不一致，请运行 sync-exclusion 更新: {target}")
        return payload

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    return payload


def check_isolation_files(
    dataset_paths: list[Path],
    *,
    exclusion_json_path: Path | None = None,
    survey_path: Path | None = None,
    pilot_manifest_path: Path | None = None,
    default_repo: str = DEFAULT_TARGET_REPO,
    require_sha: bool = True,
    require_track: bool = False,
) -> dict[str, Any]:
    """Validate one or more candidate dataset files against historical exclusions and against one another."""
    exclusion = load_exclusion_numbers(
        survey_path=survey_path,
        pilot_manifest_path=pilot_manifest_path,
        exclusion_json_path=exclusion_json_path,
        default_repo=default_repo,
    )
    excluded_by_repo = {
        repo: set(numbers)
        for repo, numbers in exclusion["excluded_by_repo"].items()
    }

    per_file: list[dict[str, Any]] = []
    combined_records: list[dict[str, Any]] = []
    for path in dataset_paths:
        records = load_dataset_records(path, default_repo=default_repo)
        combined_records.extend(records)
        result = verify_dataset_isolation(
            records,
            exclusion_by_repo=excluded_by_repo,
            default_repo=default_repo,
            require_sha=require_sha,
            require_track=require_track,
        )
        per_file.append({"path": str(path), **result})

    combined = verify_dataset_isolation(
        combined_records,
        exclusion_by_repo=excluded_by_repo,
        default_repo=default_repo,
        require_sha=require_sha,
        require_track=require_track,
    )
    return {
        "ok": all(item["ok"] for item in per_file) and combined["ok"],
        "excluded_count": exclusion["count"],
        "files": per_file,
        "combined": combined,
    }


def _is_bot_or_release_pr(pr: dict[str, Any]) -> str | None:
    title = str(pr.get("title") or "").strip()
    if title.lower().startswith("release "):
        return "release_pr"
    user = pr.get("user") or {}
    login = str(user.get("login") or "").strip().lower()
    user_type = str(user.get("type") or "").strip()
    if user_type == "Bot" or login in BOT_LOGINS or login.endswith("[bot]"):
        return "bot_author"
    return None


def _size_band(files_changed: int) -> str:
    if files_changed <= 5:
        return "small"
    if files_changed <= 20:
        return "medium"
    return "large"


def _stratified_select(
    candidates: list[dict[str, Any]],
    *,
    target_count: int,
    seed: int,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in candidates:
        buckets[(str(item.get("sample_window") or ""), str(item.get("size_band") or ""))].append(item)

    ordered_keys = sorted(buckets)
    for key in ordered_keys:
        buckets[key].sort(key=lambda row: int(row["pr_number"]))
        rng.shuffle(buckets[key])

    selected: list[dict[str, Any]] = []
    while len(selected) < target_count:
        progressed = False
        for key in ordered_keys:
            if len(selected) >= target_count:
                break
            bucket = buckets[key]
            if bucket:
                selected.append(bucket.pop(0))
                progressed = True
        if not progressed:
            break
    selected.sort(key=lambda row: int(row["pr_number"]))
    return selected


def sample_github_prs(
    *,
    repo: str = DEFAULT_TARGET_REPO,
    track: str = "track_a_random",
    target_count: int = 36,
    seed: int = 20261113,
    windows: list[tuple[str, str]] | None = None,
    query_terms: list[str] | None = None,
    per_query_limit: int = 30,
    extra_exclude_paths: list[Path] | None = None,
    output_path: Path | None = None,
    manifest_path: Path | None = None,
    gh_runner: GhRunner | None = None,
    survey_path: Path | None = None,
    pilot_manifest_path: Path | None = None,
    exclusion_json_path: Path | None = None,
) -> dict[str, Any]:
    """Sample merged Python-touching PRs from GitHub while strictly enforcing historical isolation."""
    if track not in VALID_TRACKS:
        raise ValueError(f"不支持的 track: {track}；可选值为 {sorted(VALID_TRACKS)}")
    if target_count < 1:
        raise ValueError("target_count 必须大于 0")

    runner = gh_runner or default_gh_runner
    exclusion = load_exclusion_numbers(
        survey_path=survey_path,
        pilot_manifest_path=pilot_manifest_path,
        exclusion_json_path=exclusion_json_path,
        default_repo=DEFAULT_TARGET_REPO,
    )
    excluded_numbers: set[int] = set(exclusion["excluded_by_repo"].get(repo, []))
    for extra_path in extra_exclude_paths or []:
        for row in load_dataset_records(extra_path, default_repo=repo):
            if (row.get("repo") or repo) == repo:
                num = row.get("pr_number") if isinstance(row.get("pr_number"), int) else row.get("number")
                if isinstance(num, int):
                    excluded_numbers.add(num)

    active_windows = windows or list(DEFAULT_SAMPLE_WINDOWS)
    if track == "track_b_targeted":
        terms = list(query_terms or DEFAULT_TARGETED_TERMS)
    else:
        terms = [""]

    seen_candidates: set[int] = set()
    candidates: list[dict[str, Any]] = []
    skip_counts: defaultdict[str, int] = defaultdict(int)

    for start_date, end_date in active_windows:
        window_label = f"{start_date}..{end_date}"
        for term in terms:
            query = f"repo:{repo} is:pr is:merged merged:{window_label}"
            if term:
                query = f"{query} {term}"
            encoded_query = quote(query, safe="")
            search_resp = runner([
                "api",
                f"search/issues?q={encoded_query}&sort=created&order=asc&per_page={per_query_limit}",
            ])
            items = search_resp.get("items", []) if isinstance(search_resp, dict) else []
            for issue in items:
                pr_number = issue.get("number")
                if not isinstance(pr_number, int) or pr_number <= 0:
                    continue
                if pr_number in excluded_numbers:
                    skip_counts["excluded_historical"] += 1
                    continue
                if pr_number in seen_candidates:
                    skip_counts["duplicate_candidate"] += 1
                    continue
                seen_candidates.add(pr_number)

                pr_detail = runner(["api", f"repos/{repo}/pulls/{pr_number}"])
                if not isinstance(pr_detail, dict):
                    skip_counts["invalid_pr_payload"] += 1
                    continue
                skip_reason = _is_bot_or_release_pr(pr_detail)
                if skip_reason:
                    skip_counts[skip_reason] += 1
                    continue

                base_sha = (pr_detail.get("base") or {}).get("sha")
                head_sha = (pr_detail.get("head") or {}).get("sha")
                merge_sha = pr_detail.get("merge_commit_sha")
                if not (base_sha and head_sha):
                    skip_counts["missing_sha"] += 1
                    continue

                files_resp = runner(["api", f"repos/{repo}/pulls/{pr_number}/files?per_page=100"])
                file_items = files_resp if isinstance(files_resp, list) else []
                py_files = [
                    f.get("filename")
                    for f in file_items
                    if isinstance(f, dict) and str(f.get("filename") or "").endswith(".py")
                ]
                if not py_files:
                    skip_counts["no_python_changes"] += 1
                    continue

                changed_files = int(pr_detail.get("changed_files") or len(file_items))
                candidates.append({
                    "repo": repo,
                    "pr_number": pr_number,
                    "track": track,
                    "title": pr_detail.get("title") or "",
                    "url": pr_detail.get("html_url") or f"https://github.com/{repo}/pull/{pr_number}",
                    "author": (pr_detail.get("user") or {}).get("login") or "",
                    "merged_at": pr_detail.get("merged_at"),
                    "sample_window": window_label,
                    "matched_term": term or None,
                    "base_sha": base_sha,
                    "head_sha": head_sha,
                    "merge_commit_sha": merge_sha,
                    "changed_files": changed_files,
                    "additions": int(pr_detail.get("additions") or 0),
                    "deletions": int(pr_detail.get("deletions") or 0),
                    "size_band": _size_band(changed_files),
                    "python_files": sorted(str(path) for path in py_files),
                })

    selected = _stratified_select(candidates, target_count=target_count, seed=seed)
    isolation = verify_dataset_isolation(
        selected,
        exclusion_by_repo=exclusion["excluded_by_repo"],
        default_repo=repo,
        require_sha=True,
        require_track=True,
        raise_on_error=True,
    )

    by_window: defaultdict[str, int] = defaultdict(int)
    by_size_band: defaultdict[str, int] = defaultdict(int)
    for row in selected:
        by_window[str(row["sample_window"])] += 1
        by_size_band[str(row["size_band"])] += 1

    manifest = {
        "schema_version": "prisk.eval.sample.v1",
        "repo": repo,
        "track": track,
        "seed": seed,
        "target_count": target_count,
        "selected_count": len(selected),
        "candidate_count": len(candidates),
        "windows": [f"{start}..{end}" for start, end in active_windows],
        "query_terms": terms if any(terms) else [],
        "skipped_counts": dict(sorted(skip_counts.items())),
        "by_window": dict(sorted(by_window.items())),
        "by_size_band": dict(sorted(by_size_band.items())),
        "isolation": isolation,
        "output_path": str(output_path) if output_path else None,
        "records": selected,
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lines = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in selected)
        output_path.write_text(lines, encoding="utf-8")
    if manifest_path is not None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_to_write = {k: v for k, v in manifest.items() if k != "records"}
        manifest_path.write_text(
            json.dumps(manifest_to_write, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return manifest


def _run_git(repo_dir: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_dir), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or f"exit={completed.returncode}"
        raise RuntimeError(f"git {' '.join(args)} 失败: {detail}")
    return completed.stdout


def _fetch_repo_file_bytes(
    runner: GhRunner,
    repo: str,
    file_path: str,
    ref: str,
) -> bytes:
    encoded_path = quote(file_path, safe="/")
    payload = runner(["api", f"repos/{repo}/contents/{encoded_path}?ref={quote(ref, safe='')}"])
    if not isinstance(payload, dict) or payload.get("encoding") != "base64" or "content" not in payload:
        raise RuntimeError(f"无法读取仓库文件 base64 内容: {repo}:{file_path}@{ref}")
    return base64.b64decode(str(payload["content"]).encode("ascii"))


def materialize_two_commit_repo(
    *,
    repo: str,
    pr_number: int,
    workspace_dir: Path,
    base_ref: str | None = None,
    head_ref: str | None = None,
    changed_files: list[dict[str, Any]] | None = None,
    file_fetcher: Callable[[str, str], bytes] | None = None,
    gh_runner: GhRunner | None = None,
) -> dict[str, Any]:
    """Create a disposable two-commit local git repo representing base^1 -> merge/head for a PR."""
    runner = gh_runner or default_gh_runner
    if changed_files is None or base_ref is None or head_ref is None:
        pr_detail = runner(["api", f"repos/{repo}/pulls/{pr_number}"])
        merge_sha = pr_detail.get("merge_commit_sha")
        if not merge_sha:
            raise ValueError(f"PR #{pr_number} 缺少 merge_commit_sha，无法物化双提交仓库")
        commit_detail = runner(["api", f"repos/{repo}/commits/{merge_sha}"])
        parents = commit_detail.get("parents") or []
        if not parents or not parents[0].get("sha"):
            raise ValueError(f"PR #{pr_number} merge_commit 缺少第一父提交")
        base_ref = base_ref or str(parents[0]["sha"])
        head_ref = head_ref or str(merge_sha)
        changed_files = changed_files or runner(["api", f"repos/{repo}/pulls/{pr_number}/files?per_page=100"])

    if file_fetcher is None:
        def _default_fetcher(path: str, ref: str) -> bytes:
            return _fetch_repo_file_bytes(runner, repo, path, ref)
        fetch_bytes = _default_fetcher
    else:
        fetch_bytes = file_fetcher

    repo_dir = workspace_dir / f"pr_{pr_number}"
    if repo_dir.exists():
        shutil.rmtree(repo_dir)
    repo_dir.mkdir(parents=True, exist_ok=True)

    _run_git(repo_dir, ["init"])
    _run_git(repo_dir, ["config", "user.name", "Prisk Eval"])
    _run_git(repo_dir, ["config", "user.email", "eval@prisk.local"])

    base_written = 0
    for item in changed_files:
        status = str(item.get("status") or "modified")
        if status == "added":
            continue
        base_path = str(item.get("previous_filename") or item.get("filename"))
        target = repo_dir / base_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(fetch_bytes(base_path, str(base_ref)))
        base_written += 1

    if base_written == 0:
        (repo_dir / ".prisk-base").write_text("empty base\n", encoding="utf-8")
    _run_git(repo_dir, ["add", "-A"])
    _run_git(repo_dir, ["commit", "-m", f"base for PR #{pr_number}"])
    local_base_sha = _run_git(repo_dir, ["rev-parse", "HEAD"]).strip()

    for item in changed_files:
        status = str(item.get("status") or "modified")
        filename = str(item.get("filename"))
        previous = item.get("previous_filename")
        if status == "renamed" and previous:
            old_target = repo_dir / str(previous)
            if old_target.exists():
                old_target.unlink()
        if status == "removed":
            old_target = repo_dir / filename
            if old_target.exists():
                old_target.unlink()
            continue
        new_target = repo_dir / filename
        new_target.parent.mkdir(parents=True, exist_ok=True)
        new_target.write_bytes(fetch_bytes(filename, str(head_ref)))

    _run_git(repo_dir, ["add", "-A"])
    _run_git(repo_dir, ["commit", "--allow-empty", "-m", f"head for PR #{pr_number}"])
    local_head_sha = _run_git(repo_dir, ["rev-parse", "HEAD"]).strip()

    numstat = _run_git(repo_dir, ["diff", "--numstat", "-M", local_base_sha, local_head_sha]).splitlines()
    diff_files = [line for line in numstat if line.strip()]
    return {
        "repo": repo,
        "pr_number": pr_number,
        "repo_dir": str(repo_dir),
        "remote_base_sha": base_ref,
        "remote_head_sha": head_ref,
        "base_sha": local_base_sha,
        "head_sha": local_head_sha,
        "expected_files": len(changed_files),
        "materialized_diff_files": len(diff_files),
    }


def _build_preset_specs(
    presets: list[str] | None,
    config_paths: list[Path] | None,
) -> list[tuple[str, dict[str, Any]]]:
    specs: list[tuple[str, dict[str, Any]]] = []
    if not presets and not config_paths:
        return [(name, {"preset": name}) for name in PRESETS]
    for name in presets or []:
        payload = load_config_payload(preset=name)
        assert payload is not None
        specs.append((name, payload))
    for path in config_paths or []:
        payload = load_config_payload(config_path=path)
        assert payload is not None
        specs.append((path.stem, payload))
    return specs


def run_empirical_aggregation(
    stage05_path: Path,
    *,
    stage04_path: Path | None = None,
    dataset_path: Path | None = None,
    annotations_path: Path | None = None,
    presets: list[str] | None = None,
    config_paths: list[Path] | None = None,
    json_output: Path | None = None,
    markdown_output: Path | None = None,
    default_repo: str = DEFAULT_TARGET_REPO,
) -> dict[str, Any]:
    """Aggregate stage05 tri-state rule outcomes, optional annotations, and optional preset comparisons."""
    stage05_records = load_dataset_records(stage05_path, default_repo=default_repo)
    stage04_records = (
        load_dataset_records(stage04_path, default_repo=default_repo)
        if stage04_path is not None
        else None
    )

    track_by_key: dict[tuple[str, int], str] = {}
    if dataset_path is not None:
        for row in load_dataset_records(dataset_path, default_repo=default_repo):
            pr_number = row.get("pr_number") if isinstance(row.get("pr_number"), int) else row.get("number")
            track = row.get("track")
            repo = str(row.get("repo") or default_repo)
            if isinstance(pr_number, int) and isinstance(track, str):
                track_by_key[(repo, pr_number)] = track

    outcomes = summarize_stage05_outcomes(
        stage05_records,
        stage04_records=stage04_records,
        track_by_key=track_by_key or None,
    )

    annotation_summary = None
    if annotations_path is not None:
        annotation_rows = load_dataset_records(annotations_path, default_repo=default_repo)
        annotation_summary = evaluate_annotations(annotation_rows, default_repo=default_repo)

    preset_comparison = None
    if presets or config_paths:
        specs = _build_preset_specs(presets, config_paths)
        preset_comparison = compare_preset_runs(
            stage05_records,
            specs,
            stage04_records=stage04_records,
        )

    report = {
        "schema_version": EMPIRICAL_REPORT_SCHEMA_VERSION,
        "input_paths": {
            "stage05": str(stage05_path),
            "stage04": str(stage04_path) if stage04_path else None,
            "dataset": str(dataset_path) if dataset_path else None,
            "annotations": str(annotations_path) if annotations_path else None,
        },
        "outcomes": outcomes,
        "annotations": annotation_summary,
        "preset_comparison": preset_comparison,
    }
    markdown = render_empirical_report_markdown(report)
    if json_output is not None:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if markdown_output is not None:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(markdown, encoding="utf-8")
    return report


def run_preset_comparison(
    stage05_path: Path,
    *,
    stage04_path: Path | None = None,
    presets: list[str] | None = None,
    config_paths: list[Path] | None = None,
    json_output: Path | None = None,
    markdown_output: Path | None = None,
    default_repo: str = DEFAULT_TARGET_REPO,
) -> dict[str, Any]:
    """Compare scoring distributions across preset/custom configs with config.snapshot.v1 digests."""
    stage05_records = load_dataset_records(stage05_path, default_repo=default_repo)
    stage04_records = (
        load_dataset_records(stage04_path, default_repo=default_repo)
        if stage04_path is not None
        else None
    )
    specs = _build_preset_specs(presets, config_paths)
    comparison = compare_preset_runs(
        stage05_records,
        specs,
        stage04_records=stage04_records,
    )
    if json_output is not None:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(
            json.dumps(comparison, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if markdown_output is not None:
        outcomes = summarize_stage05_outcomes(stage05_records, stage04_records=stage04_records)
        markdown = render_empirical_report_markdown({
            "outcomes": outcomes,
            "annotations": None,
            "preset_comparison": comparison,
        })
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(markdown, encoding="utf-8")
    return comparison
