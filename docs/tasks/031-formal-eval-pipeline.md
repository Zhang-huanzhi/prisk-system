---
task_id: "031"
target_version: "v1.4.0"
title: "v1.4.0 正式实证评估协议、物理隔离校验与批量评估基础设施"
status: "In Progress"
branch: "feat/031-formal-eval-pipeline"
date: "2026-11-13"
---

# Task 031: v1.4.0 正式实证评估协议、物理隔离校验与批量评估基础设施

## 1. 任务目标

- 面向 `v1.4.0`（规模型实证打靶与权重校准）确立可机器校验的正式实证评估协议与人工核验指南，构建从历史 `v1.0.0` / `v1.1.0` 样本集严格零重叠隔离的抽样、双提交临时仓库物化、29 规则三态批量聚合及多预设对比（`config.snapshot.v1`）基础设施；
- 为现有批处理 CLI（`dataset_cli`、`rules_cli`、`scoring_cli`）开放非 NetBox 仓库路径模式（`--path-mode generic` / `--repo-name`）和命名预设/配置覆盖参数（`--preset` / `--config`），同时严格保持默认 `legacy_baseline` 评分基线与 `rule-registry.json` 生命周期不变。

## 2. 背景与依据

- 阶段入口与推进路线：[`docs/tasks/v1.4-entry.md`](v1.4-entry.md)、[`docs/standards/development-roadmap.md`](../standards/development-roadmap.md)；
- 系统规格与现有基线：[`docs/blueprint.md`](../blueprint.md)、[`docs/architecture.md`](../architecture.md)；
- 历史隔离源数据：
  - `v1.0.0` 冻结调研集（`docs/versions/v1.0.0/02-PR采样&定风险场景/artifacts/netbox-survey.jsonl`：120 条 NetBox PR）；
  - `v1.1.0` 先导试点集（[`docs/evaluation/pilot-v1.1/manifest.json`](../evaluation/pilot-v1.1/manifest.json)：16 条 NetBox PR；两源去重合计 136 条，交叉重叠 0 条）。

## 3. 范围边界

### 包含

- `docs/evaluation/formal-v1.4/` 正式实证协议（`protocol.md`）、人工核验标注指南（`annotation-guide.md`）、目录索引（`README.md`）与机器生成/校验的永久排除清单（`exclusion-list.json`）；
- `prisk.domain.evaluation` 纯领域评估引擎（隔离校验、29 规则三态与 `Unanalyzed` 原因码汇总、`prisk.eval.annotation.v1` 精度与高噪候选统计、多预设对比与 Markdown 报告渲染，并收敛 `summed_rule_points` / `collaboration_points` 单一定义）；
- `prisk.services.evaluation_service` 实证服务编排与 `prisk.cli.eval_cli` CLI（`sync-exclusion`、`check-isolation`、`sample`、`aggregate`、`compare-presets`，含可注入 `gh_runner` 与 `materialize_two_commit_repo`）；
- `changes.py` / `structure.py` / `dataset_cli.py` 支持 `path_mode="generic"` 与 `repo_name` 覆盖，`rules_cli.py` / `scoring_cli.py` 支持 `--preset` 与 `--config`；
- 覆盖域模型与 CLI 的离线单元测试（`test_evaluation.py`、`test_eval_cli.py`）。

### 不包含

- 不在 Task 031 中直接联网采集或提交正式 PR 样本数据集与人工标注数据（留待 Task 032）；
- 不更改 `DEFAULT_CONFIG` / `legacy_baseline` 权重与 `rule-registry.json` 规则生命周期（24 `implemented` / 5 `draft` 保持不变，治理与权重校准留待 Task 033–034）；
- 不修改前端应用代码或自动执行 Git 提交/推送/合并/打标签。

## 4. 变更清单

- **文档与正式评估规范（`docs/`）**：
  - 新增 [`docs/evaluation/formal-v1.4/README.md`](../evaluation/formal-v1.4/README.md)
  - 新增 [`docs/evaluation/formal-v1.4/protocol.md`](../evaluation/formal-v1.4/protocol.md)
  - 新增 [`docs/evaluation/formal-v1.4/annotation-guide.md`](../evaluation/formal-v1.4/annotation-guide.md)
  - 新增 [`docs/evaluation/formal-v1.4/exclusion-list.json`](../evaluation/formal-v1.4/exclusion-list.json)
  - 新增 `docs/tasks/031-formal-eval-pipeline.md`，更新 [`docs/tasks/README.md`](README.md)、[`docs/tasks/v1.4-entry.md`](v1.4-entry.md)、[`docs/README.md`](../README.md) 与 [`docs/standards/document-structure.md`](../standards/document-structure.md)
- **后端领域、服务与 CLI（`backend/prisk/`）**：
  - 修改 `backend/prisk/domain/changes.py` 与 `backend/prisk/domain/structure.py`（增加 `path_mode` 与仓库名推断透传）
  - 新增 `backend/prisk/domain/evaluation.py`
  - 修改 `backend/prisk/services/demo_service.py`（复用 `prisk.domain.evaluation` 计分原语）
  - 新增 `backend/prisk/services/evaluation_service.py`
  - 修改 `backend/prisk/cli/dataset_cli.py`、`backend/prisk/cli/rules_cli.py`、`backend/prisk/cli/scoring_cli.py`
  - 新增 `backend/prisk/cli/eval_cli.py`
- **自动化测试（`backend/tests/`）**：
  - 新增 `backend/tests/domain/test_evaluation.py`
  - 新增 `backend/tests/cli/test_eval_cli.py`

## 5. 验证结果

- `backend/.venv/Scripts/python.exe -m prisk.cli.eval_cli sync-exclusion --check`（设置 `PYTHONPATH=backend`）：退出码 `0`，核验 [`docs/evaluation/formal-v1.4/exclusion-list.json`](../evaluation/formal-v1.4/exclusion-list.json) 与 `v1.0.0`（120 条）及 `v1.1.0`（16 条）源清单完全一致，合计 136 条去重 PR，`cross_source_overlap: {}`；
- `backend/.venv/Scripts/python.exe -m prisk.cli.eval_cli check-isolation`（设置 `PYTHONPATH=backend`）：退出码 `0`，输出 `ok: true`、`excluded_count: 136`；
- `backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend`（沙箱内执行）：共运行 `218` 项测试，其中 `214` 项通过，另 4 项均位于 `tests.web.test_web_branch_api.BranchApiTests` 因受限沙箱禁止绑定本地套接字报错（`PermissionError: [WinError 10013]`）；
- `backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests/web -t backend -v`（关闭沙箱隔离执行）：`Ran 4 tests in 9.597s`，`OK`；
- `npm --prefix frontend run lint`：退出码 `0`；
- `npm --prefix frontend run typecheck`：退出码 `0`；
- `git diff --check`：退出码 `0`。

## 6. 遗留风险与后续动作

- **Task 032（正式抽样与标注执行）**：在已认证 GitHub CLI 环境下运行 `eval_cli sample` 与 Stage 03–07 批处理流水线，固化 `track_a_random`、`track_b_targeted` 与 `external_control` 样本并按 `annotation-guide.md` 完成人工核验；
- **Task 033–034（治理与权重校准）**：基于正式实证汇总报告决策高噪规则收敛/`validated` 晋升与默认基线权重校准，同时维护与 `legacy_baseline` 回归基线的显式对比关系。
