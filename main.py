"""Prisk-System 的最小命令行入口。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prisk.analyzer import analyze_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="分析 Git 仓库两个提交之间的后端代码变更并生成风险报告。"
    )
    parser.add_argument("--repo", required=True, type=Path, help="实验仓库路径")
    parser.add_argument("--base", required=True, help="基础提交、分支或标签")
    parser.add_argument("--head", required=True, help="待分析提交、分支或标签")
    parser.add_argument("--output", type=Path, help="可选的 JSON 报告输出路径")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = analyze_repository(args.repo, args.base, args.head)
    content = json.dumps(report, ensure_ascii=False, indent=2)
    print(content)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content + "\n", encoding="utf-8")
        print(f"报告已写入: {args.output}")


if __name__ == "__main__":
    main()
