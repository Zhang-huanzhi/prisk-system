"""阶段 05 的最小规则引擎命令。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .rules import evaluate_dataset, write_rule_catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="对 stage04.v1 结构对象运行四类最小规则")
    parser.add_argument("--input", required=True, type=Path, help="stage04-structure-objects.jsonl")
    parser.add_argument("--output", required=True, type=Path, help="stage05-rule-results.jsonl")
    parser.add_argument("--manifest", required=True, type=Path, help="stage05-manifest.json")
    parser.add_argument("--catalog", type=Path, help="可选的规则目录 JSON")
    parser.add_argument("--limit", type=int, help="优先选择 PR 179、19、226 进行试运行")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = evaluate_dataset(args.input, args.output, args.manifest, limit=args.limit)
        if args.catalog:
            write_rule_catalog(args.catalog)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"阶段 05 规则运行失败: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["status_counts"].get("error", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
