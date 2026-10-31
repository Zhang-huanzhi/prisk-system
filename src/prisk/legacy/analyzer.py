"""基于 Git diff 的最小后端变更风险分析器。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..dataset import parse_unified_diff, read_diff_text


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


def main() -> None:
    """兼容旧版 main.py 的命令行入口。"""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="分析 Git 仓库两个提交之间的后端代码变更并生成风险报告。")
    parser.add_argument("--repo", required=True, type=Path, help="实验仓库路径")
    parser.add_argument("--base", required=True, help="基础提交、分支或标签")
    parser.add_argument("--head", required=True, help="待分析提交、分支或标签")
    parser.add_argument("--output", type=Path, help="可选的 JSON 报告输出路径")
    args = parser.parse_args()
    print("警告：main.py 是兼容入口，正式分支审计请使用 python -m prisk.web_cli。")
    report = analyze_repository(args.repo, args.base, args.head)
    content = json.dumps(report, ensure_ascii=False, indent=2)
    print(content)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content + "\n", encoding="utf-8")
        print(f"报告已写入: {args.output}")


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
    try:
        return read_diff_text(repo, base, head)
    except RuntimeError:
        raise


def _parse_diff(diff: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    parsed_files = parse_unified_diff(diff)
    files: list[dict[str, Any]] = [
        {
            "path": item["new_path"] or item["old_path"],
            "change_type": item["status"],
        }
        for item in parsed_files
    ]
    added_lines: list[dict[str, Any]] = []
    changed_paths: set[str] = {
        str(item["new_path"] or item["old_path"])
        for item in parsed_files
        if item["new_path"] or item["old_path"]
    }
    for item in parsed_files:
        path = item["new_path"] or item["old_path"]
        if not path:
            continue
        for hunk in item["hunks"]:
            for line in hunk["lines"]:
                if line["kind"] == "add":
                    added_lines.append(
                        {"path": path, "line": line["new_line"], "content": line["text"]}
                    )

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
