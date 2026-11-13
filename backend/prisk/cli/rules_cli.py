"""阶段 05 的最小规则引擎命令。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..domain.config import PRESET_LEGACY_BASELINE, PRESETS, build_config_snapshot, normalize_audit_config
from ..domain.evaluation import load_config_payload
from ..domain.rules import evaluate_dataset, write_rule_catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="对 stage04.v1 结构对象运行当前规则目录")
    parser.add_argument("--input", required=True, type=Path, help="stage04-structure-objects.jsonl")
    parser.add_argument("--output", required=True, type=Path, help="stage05-rule-results.jsonl")
    parser.add_argument("--manifest", required=True, type=Path, help="stage05-manifest.json")
    parser.add_argument("--catalog", type=Path, help="可选的规则目录 JSON")
    parser.add_argument("--limit", type=int, help="优先选择 PR 179、19、226 进行试运行")
    parser.add_argument("--preset", choices=sorted(PRESETS), help="可选的命名配置预设")
    parser.add_argument("--config", type=Path, help="可选的审计配置覆盖 JSON 文件路径")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config_payload = load_config_payload(preset=args.preset, config_path=args.config)
        rule_config = (
            normalize_audit_config(config_payload, default_preset=PRESET_LEGACY_BASELINE)
            if config_payload is not None
            else None
        )
        manifest = evaluate_dataset(
            args.input,
            args.output,
            args.manifest,
            rule_config=rule_config,
            limit=args.limit,
        )
        if config_payload is not None:
            manifest["config_snapshot"] = build_config_snapshot(
                config_payload,
                default_preset=PRESET_LEGACY_BASELINE,
            )
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.catalog:
            write_rule_catalog(args.catalog)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"阶段 05 规则运行失败: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["status_counts"].get("error", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
