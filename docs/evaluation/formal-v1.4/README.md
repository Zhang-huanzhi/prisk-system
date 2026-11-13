# v1.4.0 正式实证评估资产说明 (`docs/evaluation/formal-v1.4/`)

本目录承载 `v1.4.0`（规模型实证打靶与权重校准）正式评估协议、永久隔离清单、人工核验指南及后续正式样本/汇总产物。本目录与 `v1.0.0` 调研集及 [`pilot-v1.1/`](../pilot-v1.1/README.md) 先导试点保持物理隔离。

## 目录内容

| 文件 | 用途 | 状态 |
| :--- | :--- | :---: |
| [`validation-strategy.md`](validation-strategy.md) | `v1.4.0` 有效性证明方法论与定性决策矩阵：最新 `v1.3.0` 被测口径、三阵营分治义务（同步至规则责任矩阵）、六条验证路径、四张定性矩阵（含 `G2a`/`G2b` 与 `G3a`/`G3b` 拆分）与所有者终裁记录 | 已定案并固化至 [`ADR-0001`](../../adr/0001-v14-validation-strategy.md)（Task 032） |
| [`ADR-0001`](../../adr/0001-v14-validation-strategy.md) | 长期架构决策记录：固化方案 III、剔除 5 条历史演示规则、启用 P3+P4（含随机行重叠机会基线）+P5、拆分 `G2a`/`G2b`，以及拆分外部对照 `G3a`（`saleor/saleor` 非 DRF 退避）+ `G3b`（Task `033` 待选真实 DRF 迁移） | `Accepted`（Task 032） |
| [`protocol.md`](protocol.md) | 正式实证评估基础协议：抽样框、136 条隔离边界、Track A/B 与外部对照分轨口径、`analyze_branches` 物化接入规范（具体证明路线服从 `validation-strategy.md`） | 口径已对齐（Task 032） |
| [`annotation-guide.md`](annotation-guide.md) | 可选辅助指南：四值核验词表、`prisk.eval.annotation.v1` 格式与切片核对参考（已降级为可选工具，非全量必需支柱） | 已降级为可选参考（Task 032） |
| [`exclusion-list.json`](exclusion-list.json) | 机器可读的永久排除清单：合并导出 `v1.0.0`（120 条）与 `v1.1.0`（16 条）共 136 个 NetBox PR 编号及源 SHA-256 指纹 | 已同步生成（Task 031） |

## 常用 CLI 命令

所有命令在仓库根目录通过 `backend/.venv/Scripts/python.exe`（设置 `PYTHONPATH=backend`）运行：

```powershell
$env:PYTHONPATH = "backend"

# 1. 校验 exclusion-list.json 与 v1.0.0/v1.1.0 源清单严格同步（136 条，交叉重叠 0）
backend/.venv/Scripts/python.exe -m prisk.cli.eval_cli sync-exclusion --check

# 2. 校验任意正式数据集 JSONL / 清单与永久排除清单零重叠、无重复且含合法 SHA
backend/.venv/Scripts/python.exe -m prisk.cli.eval_cli check-isolation path/to/formal-track-a.jsonl --require-track

# 3. Task 031 过渡聚合入口示例（待按 validation-strategy.md 选定方案适配对齐 stage08.branch-report.v1）
backend/.venv/Scripts/python.exe -m prisk.cli.eval_cli aggregate `
  --stage05 path/to/stage05-rule-results.jsonl `
  --stage04 path/to/stage04-structure-objects.jsonl `
  --dataset path/to/formal-dataset.jsonl `
  --annotations path/to/annotations.jsonl `
  --preset legacy_baseline --preset balanced --preset security_focus `
  --json-output path/to/empirical-report.json `
  --markdown-output path/to/empirical-report.md
```

> 注：Task 032 已完成方法论定案并由 [`ADR-0001`](../../adr/0001-v14-validation-strategy.md) 与更新后的[`规则责任矩阵`](../../rules/rule-responsibility-matrix.md)锁定「方案 III + 剔除历史 5 条演示规则 + 完整启用 P3/P4（配对随机行重叠机会基线）/P5 + 外部双轨 `G3a`（`saleor/saleor` 非 DRF 退避）/`G3b`（真 DRF 迁移，仓名待选）」；具体工程接口改造（将 `eval_cli aggregate` / `compare-presets` 对齐至 `analyze_branches` 的 `stage08.branch-report.v1` 并增加 `P1/P3/P4/P5` 支撑）、`G3b` 选仓与正式采样将在下一落地任务（Task `033`）中开展。
