"""Read-only discovery of local Git projects and their branches."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any


class ProjectError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=path, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    if result.returncode:
        raise ProjectError("git_error", (result.stderr or result.stdout or "Git 命令失败").strip())
    return result.stdout.strip()


def project_id(path: Path) -> str:
    resolved = str(path.expanduser().resolve())
    return hashlib.sha256(resolved.casefold().encode("utf-8")).hexdigest()[:16]


def inspect_project(value: str | Path) -> dict[str, Any]:
    raw_path = Path(value).expanduser()
    if not raw_path.exists() or not raw_path.is_dir():
        raise ProjectError("invalid_path", "项目路径不存在或不是文件夹")
    path = raw_path.resolve()
    try:
        inside = _git(path, "rev-parse", "--is-inside-work-tree")
    except ProjectError as exc:
        raise ProjectError("not_git_repository", "指定目录不是 Git 工作树") from exc
    if inside != "true":
        raise ProjectError("not_git_repository", "指定目录不是 Git 工作树")
    top_level = Path(_git(path, "rev-parse", "--show-toplevel")).resolve()
    if top_level != path:
        raise ProjectError("not_git_repository", "请提供 Git 工作树根目录")

    branches_output = _git(
        path, "for-each-ref",
        "--format=%(refname:short)%09%(refname)%09%(objectname)%09%(subject)%09%(committerdate:iso-strict)",
        "refs/heads", "refs/remotes",
    )
    branches: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in branches_output.splitlines():
        fields = line.split("\t", 4)
        if len(fields) < 5:
            continue
        ref, full_ref, sha, subject, committed_at = fields
        if ref.endswith("/HEAD") or ref in seen:
            continue
        seen.add(ref)
        branches.append({
            "ref": ref,
            "kind": "local" if full_ref.startswith("refs/heads/") else "remote",
            "sha": sha,
            "short_sha": sha[:7],
            "subject": subject,
            "committed_at": committed_at,
        })
    branches.sort(key=lambda item: (item["kind"] != "local", item["ref"].casefold()))
    if not branches:
        raise ProjectError("no_branches", "仓库没有可分析的本地或远程跟踪分支")

    try:
        symbolic_default = _git(path, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    except ProjectError:
        symbolic_default = ""
    default_branch = symbolic_default if any(item["ref"] == symbolic_default for item in branches) else ""
    if not default_branch:
        default_branch = next((name for name in ("main", "master") if any(item["ref"] == name for item in branches)), "")
    if not default_branch:
        current = _git(path, "branch", "--show-current")
        default_branch = current if any(item["ref"] == current for item in branches) else branches[0]["ref"]
    try:
        current_head = _git(path, "rev-parse", "HEAD")
        current_branch = _git(path, "branch", "--show-current")
    except ProjectError:
        current_head = ""
        current_branch = ""
    if not current_branch and current_head:
        current_branch = next((item["ref"] for item in branches if item["sha"] == current_head and item["kind"] == "local"), "")

    return {
        "project_id": project_id(path),
        "name": path.name,
        "path": str(path),
        "default_branch": default_branch,
        "current_head": current_head,
        "current_branch": current_branch,
        "branches": branches,
    }


class ProjectRegistry:
    def __init__(self) -> None:
        self._projects: dict[str, dict[str, Any]] = {}

    def load(self, path: str | Path) -> dict[str, Any]:
        project = inspect_project(path)
        self._projects[project["project_id"]] = project
        return project

    def get(self, key: str) -> dict[str, Any]:
        project = self._projects.get(key)
        if project is None:
            raise ProjectError("project_not_loaded", "项目未加载或服务已重启，请重新加载项目")
        return project

    def refresh(self, key: str) -> dict[str, Any]:
        project = self.get(key)
        refreshed = self.load(project["path"])
        return refreshed
