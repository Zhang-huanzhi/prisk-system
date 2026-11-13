# v1.4.0 正式实证评估资产说明 (`docs/evaluation/formal-v1.4/`)

本目录承载 `v1.4.0`（规模型实证打靶与权重校准）正式评估协议、永久隔离清单、人工核验指南及后续正式样本/汇总产物。本目录与 `v1.0.0` 调研集及 [`pilot-v1.1/`](../pilot-v1.1/README.md) 先导试点保持物理隔离。

## 目录内容

| 文件 | 用途 | 状态 |
| :--- | :--- | :---: |
| [`protocol.md`](protocol.md) | 正式实证评估协议：抽样框、136 条隔离边界、Track A/B 与外部对照分轨口径、两类仓库物化模式 | 已冻结口径（Task 031） |
| [`annotation-guide.md`](annotation-guide.md) | 人工核验标注指南：四值判断词表、`prisk.eval.annotation.v1` 格式、29 条规则逐条核验边界与耗时记录 | 已冻结口径（Task 031） |
| [`exclusion-list.json`](exclusion-list.json) | 机器可读的永久排除清单：合并导出 `v1.0.0`（120 条）与 `v1.1.0`（16 条）共 136 个 NetBox PR 编号及源 SHA-256 指纹 | 已同步生成（Task 031） |

## 常用 CLI 命令

所有命令在仓库根目录通过 `backend/.venv/Scripts/python.exe`（设置 `PYTHONPATH=backend`）运行：

```powershell
$env:PYTHONPATH = "backend"

# 1. 校验 exclusion-list.json 与 v1.0.0/v1.1.0 源清单严格同步（136 条，交叉重叠 0）
backend/.venv/Scripts/python.exe -m prisk.cli.eval_cli sync-exclusion --check

# 2. 校验任意正式数据集 JSONL / 清单与永久排除清单零重叠、无重复且含合法 SHA
backend/.venv/Scripts/python.exe -m prisk.cli.eval_cli check-isolation path/to/formal-track-a.jsonl --require-track

# 3. 聚合 stage05 三态分布、Unanalyzed 原因、人工标注 Precision 与多预设对比
backend/.venv/Scripts/python.exe -m prisk.cli.eval_cli aggregate `
  --stage05 path/to/stage05-rule-results.jsonl `
  --stage04 path/to/stage04-structure-objects.jsonl `
  --dataset path/to/formal-dataset.jsonl `
  --annotations path/to/annotations.jsonl `
  --preset legacy_baseline --preset balanced --preset security_focus `
  --json-output path/to/empirical-report.json `
  --markdown-output path/to/empirical-report.md
```

> 注：联网从 GitHub 采集正式 PR 样本（`eval_cli sample`）与完成人工核验标注属于后续实证执行任务，不在 Task 031 中直接提交真实正式数据集产物。
