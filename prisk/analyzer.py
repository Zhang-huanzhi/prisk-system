"""基于 Git diff 的最小后端变更风险分析器。"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any


HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,(?P<count>\d+))? @@")
DIFF_FILE_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")
AUTH_RE = re.compile(
    r"\b(?:require_owner|require_family_access|validate_csrf|permission|authorization|role|auth)\b",
    re.IGNORECASE,
)
INTERFACE_RE = re.compile(r"\b(?:def|async\s+def)\s+[A-Za-z_]\w*\s*\(|->\s*[A-Za-z_]\w*")
DATA_RE = re.compile(
    r"\b(?:Session|commit|rollback|transaction|select|insert|update|delete|repository|db)\b",
    re.IGNORECASE,
)


def analyze_repository(repo: Path, base: str, head: str) -> dict[str, Any]:
    """分析 repo 中 base..head 的累积差异。"""

    repo = repo.expanduser().resolve()
    diff = _read_diff(repo, base, head)
    files, added_lines, changed_paths = _parse_diff(diff)
    risks = _build_risks(added_lines, changed_paths)
    return {
        "schema_version": "0.1",
        "repository": str(repo),
        "base": base,
        "head": head,
        "summary": {
            "changed_files": len(files),
            "added_lines": len(added_lines),
            "risk_count": len(risks),
        },
        "changed_files": files,
        "risks": risks,
    }


def _read_diff(repo: Path, base: str, head: str) -> str:
    result = subprocess.run(
        ["git", "diff", "--find-renames", "--unified=0", f"{base}..{head}"],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode:
        detail = result.stderr.strip() or "无法读取 Git 差异"
        raise RuntimeError(detail)
    return result.stdout


def _parse_diff(diff: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    files: list[dict[str, Any]] = []
    added_lines: list[dict[str, Any]] = []
    changed_paths: set[str] = set()
    current_path: str | None = None
    next_line = 0

    for raw_line in diff.splitlines():
        file_match = DIFF_FILE_RE.match(raw_line)
        if file_match:
            current_path = file_match.group(2)
            changed_paths.add(current_path)
            files.append({"path": current_path, "change_type": "modified"})
            next_line = 0
            continue

        hunk_match = HUNK_RE.match(raw_line)
        if hunk_match:
            next_line = int(hunk_match.group("start"))
            continue

        if current_path is None or not raw_line.startswith(("+", "-", " ")):
            continue
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            added_lines.append({"path": current_path, "line": next_line, "content": raw_line[1:]})
            next_line += 1
        elif raw_line.startswith(" "):
            next_line += 1

    return files, added_lines, changed_paths


def _build_risks(
    added_lines: list[dict[str, Any]], changed_paths: set[str]
) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    backend_lines = [line for line in added_lines if _is_backend_code(line["path"])]
    test_changed = any(_is_test_path(path) for path in changed_paths)

    for line in backend_lines:
        content = line["content"]
        location = f"{line['path']}:{line['line']}"
        if AUTH_RE.search(content):
            risks.append(_risk("authorization", "high", location, "权限或认证相关代码发生变化", "复核不同角色的访问边界和未授权响应"))
        if INTERFACE_RE.search(content):
            risks.append(_risk("interface_contract", "medium", location, "方法签名或返回类型相关代码发生变化", "复核调用方、参数校验、返回结构和异常行为"))
        if DATA_RE.search(content):
            risks.append(_risk("data_transaction", "medium", location, "数据访问或事务相关代码发生变化", "复核事务边界、提交回滚路径和数据一致性"))

    if backend_lines and not test_changed:
        first = backend_lines[0]
        risks.append(_risk("testing_collaboration", "low", f"{first['path']}:{first['line']}", "后端代码发生变化，但本次差异未包含测试文件", "补充或复核覆盖正常、异常和权限边界的测试"))

    return _deduplicate(risks)


def _is_backend_code(path: str) -> bool:
    return path.startswith("backend/") and path.endswith(".py")


def _is_test_path(path: str) -> bool:
    normalized = path.lower()
    return "/test" in normalized or normalized.startswith("tests/") or normalized.endswith("_test.py")


def _risk(risk_type: str, severity: str, location: str, evidence: str, action: str) -> dict[str, Any]:
    return {
        "risk_type": risk_type,
        "severity": severity,
        "location": location,
        "evidence": [evidence],
        "suggested_action": action,
    }


def _deduplicate(risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []
    for risk in risks:
        key = (risk["risk_type"], risk["location"])
        if key not in seen:
            seen.add(key)
            result.append(risk)
    return result
