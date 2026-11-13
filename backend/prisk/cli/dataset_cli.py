"""阶段 03 的 JSONL 数据集构建命令。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..domain.changes import VALID_PATH_MODES, build_from_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="将冻结 PR JSONL 转换为统一变更对象 JSONL")
    parser.add_argument("--input", required=True, type=Path, help="冻结的 PR JSONL")
    parser.add_argument("--repo", required=True, type=Path, help="本地 Git 仓库")
    parser.add_argument("--output", required=True, type=Path, help="统一变更对象 JSONL")
    parser.add_argument("--manifest", type=Path, help="可选的批处理清单 JSON")
    parser.add_argument("--limit", type=int, help="限制处理记录数；3 表示按小、中、大改动各选一条")
    parser.add_argument(
        "--path-mode",
        choices=sorted(VALID_PATH_MODES),
        default="netbox",
        help="路径角色判定模式：netbox（默认）或 generic（通用外部 Django/DRF 仓库）",
    )
    parser.add_argument("--repo-name", help="可选覆盖清单中记录的仓库名（如 saleor/saleor）")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = build_from_jsonl(
            args.input,
            args.repo,
            args.output,
            args.manifest,
            args.limit,
            path_mode=args.path_mode,
            repo_name=args.repo_name,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"阶段 03 数据构建失败: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["status_counts"].get("error", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
