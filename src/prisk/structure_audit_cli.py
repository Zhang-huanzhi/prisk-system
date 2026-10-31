"""阶段 04 结构质量审计命令。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .dataset import load_records
from .structure_audit import audit_structure_records, write_audit_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="审计 stage04.v1 结构对象的路径、节点和行号一致性")
    parser.add_argument("--input", required=True, type=Path, help="stage04-structure-objects.jsonl")
    parser.add_argument("--stage03", required=True, type=Path, help="stage03-change-objects.jsonl")
    parser.add_argument("--survey", required=True, type=Path, help="02 阶段 NetBox survey JSONL")
    parser.add_argument("--output", required=True, type=Path, help="stage04-quality-report.json")
    parser.add_argument("--minimum-prs", type=int, default=12)
    parser.add_argument("--changes-per-pr", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        records = load_records(args.input)
        stage03_records = load_records(args.stage03)
        report = audit_structure_records(records, stage03_records, args.survey, args.minimum_prs, args.changes_per_pr)
        write_audit_report(report, args.output)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"阶段 04 质量审计失败: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["automatic_gate"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
