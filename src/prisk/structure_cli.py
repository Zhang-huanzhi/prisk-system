"""阶段 04 的结构对象构建命令。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .structure import build_structure_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="将 stage03.v1 PR 对象转换为 stage04.v1 结构对象")
    parser.add_argument("--input", required=True, type=Path, help="stage03-change-objects.jsonl")
    parser.add_argument("--repo", required=True, type=Path, help="NetBox 本地 Git 仓库")
    parser.add_argument("--output", required=True, type=Path, help="stage04-structure-objects.jsonl")
    parser.add_argument("--manifest", type=Path, help="stage04-manifest.json")
    parser.add_argument("--limit", type=int, help="限制处理记录数；3 表示优先选择 179、19、226")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = build_structure_dataset(args.input, args.repo, args.output, args.manifest, args.limit)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"阶段 04 结构构建失败: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["status_counts"].get("error", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
