"""Stage 07 transparent scoring batch command."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from ..paths import demo_data_root
from ..services.demo_service import DemoData, build_scored_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="将 stage05 规则结果转换为 stage07 结构评分报告")
    root = demo_data_root()
    parser.add_argument("--stage03", type=Path, default=root / "stage03-change-objects.jsonl")
    parser.add_argument("--stage04", type=Path, default=root / "stage04-structure-objects.jsonl")
    parser.add_argument("--stage05", type=Path, default=root / "stage05-rule-results.jsonl")
    parser.add_argument("--output", required=True, type=Path, help="stage07-scored-reports.jsonl")
    parser.add_argument("--manifest", required=True, type=Path, help="stage07-manifest.json")
    parser.add_argument("--limit", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        data = DemoData(args.stage03, args.stage04, args.stage05)
        reports = build_scored_dataset(data)
        if args.limit is not None:
            if args.limit < 1:
                raise ValueError("limit 必须大于 0")
            reports = reports[: args.limit]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("".join(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n" for report in reports), encoding="utf-8")
        status_counts = Counter(report.get("status") for report in reports)
        level_counts = Counter(report.get("risk_level") for report in reports if report.get("status") == "ok")
        manifest = {
            "schema_version": "stage07.report.v1",
            "input_paths": [str(args.stage03), str(args.stage04), str(args.stage05)],
            "input_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in (args.stage03, args.stage04, args.stage05)},
            "input_records": len(reports),
            "status_counts": dict(sorted(status_counts.items())),
            "risk_level_counts": dict(sorted(level_counts.items())),
            "finding_count": sum(report["summary"]["finding_count"] for report in reports),
            "evidence_count": sum(
                len(finding.get("evidence", []))
                for report in reports
                for finding in report.get("findings", [])
            ),
            "scoring": "fixed transparent weights and thresholds; not calibrated defect probability",
            "output_path": str(args.output),
        }
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError) as exc:
        print(f"阶段 07 评分失败: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
