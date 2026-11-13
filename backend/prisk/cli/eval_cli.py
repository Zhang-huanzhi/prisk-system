"""CLI entrypoint for v1.4 formal empirical evaluation, isolation checks, sampling, and preset comparison."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ..domain.config import PRESETS
from ..domain.evaluation import DEFAULT_TARGET_REPO, VALID_TRACKS
from ..services.evaluation_service import (
    GhRunner,
    check_isolation_files,
    load_exclusion_numbers,
    run_empirical_aggregation,
    run_preset_comparison,
    sample_github_prs,
    sync_exclusion_list,
)


def _parse_windows(raw_windows: list[str] | None) -> list[tuple[str, str]] | None:
    if not raw_windows:
        return None
    parsed: list[tuple[str, str]] = []
    for item in raw_windows:
        if ".." not in item:
            raise ValueError(f"时间窗口格式必须为 YYYY-MM-DD..YYYY-MM-DD: {item}")
        start, end = item.split("..", 1)
        if not start or not end:
            raise ValueError(f"时间窗口起止日期不能为空: {item}")
        parsed.append((start.strip(), end.strip()))
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prisk v1.4 正式实证评估与隔离校验工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync-exclusion", help="生成或校验 136 条历史 PR 永久排除清单")
    sync_parser.add_argument("--survey", type=Path, help="v1.0.0 netbox-survey.jsonl 路径")
    sync_parser.add_argument("--pilot-manifest", type=Path, help="v1.1.0 pilot manifest.json 路径")
    sync_parser.add_argument("--output", type=Path, help="输出 exclusion-list.json 路径")
    sync_parser.add_argument("--check", action="store_true", help="仅校验现存 exclusion-list.json 是否与源一致")

    iso_parser = subparsers.add_parser("check-isolation", help="校验候选数据集与永久排除清单零重叠")
    iso_parser.add_argument("datasets", nargs="*", type=Path, help="待校验的数据集 JSONL 或 manifest JSON")
    iso_parser.add_argument("--exclusion", type=Path, help="exclusion-list.json 路径")
    iso_parser.add_argument("--survey", type=Path, help="v1.0.0 netbox-survey.jsonl 路径")
    iso_parser.add_argument("--pilot-manifest", type=Path, help="v1.1.0 pilot manifest.json 路径")
    iso_parser.add_argument("--require-track", action="store_true", help="强制每条记录包含合法 track 字段")
    iso_parser.add_argument("--no-require-sha", action="store_true", help="跳过 SHA-1 40 位 hex 校验")

    sample_parser = subparsers.add_parser("sample", help="按双轨分层协议从 GitHub 抽取非重复且隔离的 PR 候选集")
    sample_parser.add_argument("--repo", default=DEFAULT_TARGET_REPO, help="目标 GitHub 仓库 owner/name")
    sample_parser.add_argument("--track", choices=sorted(VALID_TRACKS), default="track_a_random", help="抽样轨道")
    sample_parser.add_argument("--count", type=int, default=36, help="目标抽取 PR 数量")
    sample_parser.add_argument("--seed", type=int, default=20261113, help="确定性随机种子")
    sample_parser.add_argument("--window", action="append", help="时间窗口 YYYY-MM-DD..YYYY-MM-DD（可重复）")
    sample_parser.add_argument("--term", action="append", help="Track B 靶向检索词（可重复）")
    sample_parser.add_argument("--per-query-limit", type=int, default=30, help="每个查询分页上限")
    sample_parser.add_argument("--exclude-from", action="append", type=Path, help="额外排除数据集 JSONL/JSON（如已采集 Track A）")
    sample_parser.add_argument("--output", type=Path, help="输出候选集 JSONL 路径")
    sample_parser.add_argument("--manifest", type=Path, help="输出抽样清单 JSON 路径")
    sample_parser.add_argument("--dry-run", action="store_true", help="仅打印抽样摘要而不落盘文件")

    agg_parser = subparsers.add_parser("aggregate", help="汇总 29 规则三态分布、Unanalyzed 原因、人工标注精度与预设对比")
    agg_parser.add_argument("--stage05", required=True, type=Path, help="stage05 规则结果 JSONL")
    agg_parser.add_argument("--stage04", type=Path, help="可选 stage04 结构对象 JSONL")
    agg_parser.add_argument("--dataset", type=Path, help="可选抽样/数据集 JSONL（用于绑定 track 分轨）")
    agg_parser.add_argument("--annotations", type=Path, help="可选人工核验 annotations.jsonl")
    agg_parser.add_argument("--preset", action="append", choices=sorted(PRESETS), help="附带对比的预设名称（可重复）")
    agg_parser.add_argument("--config", action="append", type=Path, help="附带对比的自定义配置 JSON（可重复）")
    agg_parser.add_argument("--json-output", type=Path, help="输出 JSON 汇总报告路径")
    agg_parser.add_argument("--markdown-output", type=Path, help="输出 Markdown 汇总报告路径")

    cmp_parser = subparsers.add_parser("compare-presets", help="在同一 stage05 数据集上对比多套预设与自定义权重分布")
    cmp_parser.add_argument("--stage05", required=True, type=Path, help="stage05 规则结果 JSONL")
    cmp_parser.add_argument("--stage04", type=Path, help="可选 stage04 结构对象 JSONL")
    cmp_parser.add_argument("--preset", action="append", choices=sorted(PRESETS), help="对比预设名（默认全部 5 套）")
    cmp_parser.add_argument("--config", action="append", type=Path, help="对比自定义配置 JSON（可重复）")
    cmp_parser.add_argument("--json-output", type=Path, help="输出 JSON 对比报告路径")
    cmp_parser.add_argument("--markdown-output", type=Path, help="输出 Markdown 对比报告路径")

    return parser


def _handle_command(args: argparse.Namespace, *, gh_runner: GhRunner | None = None) -> tuple[int, dict[str, Any]]:
    if args.command == "sync-exclusion":
        payload = sync_exclusion_list(
            survey_path=args.survey,
            pilot_manifest_path=args.pilot_manifest,
            output_path=args.output,
            check_only=args.check,
        )
        return 0, payload

    if args.command == "check-isolation":
        if not args.datasets:
            exclusion = load_exclusion_numbers(
                survey_path=args.survey,
                pilot_manifest_path=args.pilot_manifest,
                exclusion_json_path=args.exclusion,
            )
            return 0, {
                "ok": True,
                "excluded_count": exclusion["count"],
                "excluded_by_repo": exclusion["excluded_by_repo"],
                "sources": exclusion["sources"],
                "datasets_checked": 0,
            }
        result = check_isolation_files(
            list(args.datasets),
            exclusion_json_path=args.exclusion,
            survey_path=args.survey,
            pilot_manifest_path=args.pilot_manifest,
            require_sha=not args.no_require_sha,
            require_track=args.require_track,
        )
        return (0 if result["ok"] else 1), result

    if args.command == "sample":
        output = None if args.dry_run else args.output
        manifest_path = None if args.dry_run else args.manifest
        result = sample_github_prs(
            repo=args.repo,
            track=args.track,
            target_count=args.count,
            seed=args.seed,
            windows=_parse_windows(args.window),
            query_terms=args.term,
            per_query_limit=args.per_query_limit,
            extra_exclude_paths=args.exclude_from,
            output_path=output,
            manifest_path=manifest_path,
            gh_runner=gh_runner,
        )
        summary = {k: v for k, v in result.items() if k != "records"}
        if args.dry_run:
            summary["dry_run"] = True
            summary["preview_pr_numbers"] = [item["pr_number"] for item in result["records"]]
        return 0, summary

    if args.command == "aggregate":
        report = run_empirical_aggregation(
            args.stage05,
            stage04_path=args.stage04,
            dataset_path=args.dataset,
            annotations_path=args.annotations,
            presets=args.preset,
            config_paths=args.config,
            json_output=args.json_output,
            markdown_output=args.markdown_output,
        )
        return 0, report

    if args.command == "compare-presets":
        comparison = run_preset_comparison(
            args.stage05,
            stage04_path=args.stage04,
            presets=args.preset,
            config_paths=args.config,
            json_output=args.json_output,
            markdown_output=args.markdown_output,
        )
        return 0, comparison

    raise ValueError(f"未知子命令: {args.command}")


def main(argv: list[str] | None = None, *, gh_runner: GhRunner | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        exit_code, payload = _handle_command(args, gh_runner=gh_runner)
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"评估命令执行失败: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
