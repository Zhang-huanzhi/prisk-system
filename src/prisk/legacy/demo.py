"""直接运行 EiheiZone 演示分析。

在 PyCharm 中打开本文件，点击右上角运行按钮即可。
"""

from __future__ import annotations

import json
import html
import webbrowser
from pathlib import Path

from .analyzer import analyze_repository


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_REPO = PROJECT_ROOT.parent / "EiheiZone-experience"
REPORT_PATH = PROJECT_ROOT / "reports" / "eiheizone-demo.json"
HTML_REPORT_PATH = PROJECT_ROOT / "reports" / "eiheizone-demo.html"
BASE_REF = "main"
HEAD_REF = "prisk-risk-demo"


def main() -> None:
    print("警告：run.py 是兼容入口，正式分支审计请使用本地看板。")
    if not EXPERIMENT_REPO.is_dir():
        raise FileNotFoundError(f"找不到实验仓库: {EXPERIMENT_REPO}")

    report = analyze_repository(EXPERIMENT_REPO, BASE_REF, HEAD_REF)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    HTML_REPORT_PATH.write_text(_render_html(report), encoding="utf-8")

    summary = report["summary"]
    print("Prisk-System 风险分析演示")
    print(f"实验项目: {EXPERIMENT_REPO.name}")
    print(f"比较范围: {BASE_REF}..{HEAD_REF}")
    print(f"变更文件: {summary['changed_files']} 个")
    print(f"新增行数: {summary['added_lines']} 行")
    print(f"风险数量: {summary['risk_count']} 个")
    print("\n风险列表:")
    for index, risk in enumerate(report["risks"], start=1):
        print(f"{index}. [{risk['severity']}] {risk['risk_type']}")
        print(f"   位置: {risk['location']}")
        print(f"   依据: {risk['evidence'][0]}")
        print(f"   建议: {risk['suggested_action']}")
    print(f"\n报告已保存: {REPORT_PATH}")
    print(f"网页报告已保存: {HTML_REPORT_PATH}")
    webbrowser.open(HTML_REPORT_PATH.as_uri())


def _render_html(report: dict) -> str:
    summary = report["summary"]
    risk_items = []
    for risk in report["risks"]:
        risk_items.append(
            "<article class='risk'>"
            f"<div class='risk-title'><strong>{html.escape(risk['risk_type'])}</strong>"
            f"<span class='severity {html.escape(risk['severity'])}'>{html.escape(risk['severity'])}</span></div>"
            f"<p><b>位置：</b>{html.escape(risk['location'])}</p>"
            f"<p><b>触发依据：</b>{html.escape(risk['evidence'][0])}</p>"
            f"<p><b>复核建议：</b>{html.escape(risk['suggested_action'])}</p>"
            "</article>"
        )
    risks_html = "\n".join(risk_items) or "<p>未发现规则命中。</p>"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Prisk-System 风险分析报告</title>
  <style>
    :root {{ color-scheme: light; font-family: system-ui, sans-serif; }}
    body {{ max-width: 900px; margin: 40px auto; padding: 0 20px; color: #17202a; background: #f5f7fa; }}
    header, .summary, .risk {{ background: white; border: 1px solid #d9e0e7; border-radius: 8px; padding: 20px; margin-bottom: 16px; }}
    h1 {{ margin-top: 0; }}
    .meta {{ color: #5b6773; }}
    .summary {{ display: flex; gap: 28px; flex-wrap: wrap; }}
    .metric strong {{ display: block; font-size: 1.6rem; }}
    .risk-title {{ display: flex; justify-content: space-between; gap: 16px; align-items: center; }}
    .severity {{ border-radius: 999px; padding: 4px 10px; font-size: .85rem; font-weight: 700; }}
    .high {{ color: #8b1e1e; background: #fde4e4; }}
    .medium {{ color: #805500; background: #fff1c7; }}
    .low {{ color: #155b3a; background: #dff5e9; }}
    p {{ line-height: 1.55; }}
    code {{ background: #eef1f4; padding: 2px 5px; border-radius: 4px; }}
  </style>
</head>
<body>
  <header>
    <h1>Prisk-System 风险分析报告</h1>
    <p class="meta">实验项目：<code>{html.escape(Path(report['repository']).name)}</code></p>
    <p class="meta">比较范围：<code>{html.escape(report['base'])}..{html.escape(report['head'])}</code></p>
  </header>
  <section class="summary">
    <div class="metric"><strong>{summary['changed_files']}</strong>变更文件</div>
    <div class="metric"><strong>{summary['added_lines']}</strong>新增行数</div>
    <div class="metric"><strong>{summary['risk_count']}</strong>风险提示</div>
  </section>
  <section>
    <h2>风险列表</h2>
    {risks_html}
  </section>
</body>
</html>
"""


if __name__ == "__main__":
    main()
