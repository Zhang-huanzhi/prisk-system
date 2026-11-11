---
task_id: "030"
target_version: "v1.3.0"
title: "v1.3 阶段里程碑收工归档与文档对齐"
status: "Accepted"
branch: "docs/030-v13-milestone-closure"
date: "2026-11-11"
---

# 030：v1.3 阶段里程碑收工归档与文档对齐

## 1. 背景与目标

在已完成并合并至 `main` 的 Task 026–029 基础上，Prisk-System v1.3.0 阶段（动态交互工作台与报告）的全部工程与交互重构目标已完整达成：
- Task 026 实现了运行时配置解耦、5 套标准化场景预设（`balanced`、`security_focus`、`framework_upgrade`、`daily_review`、`legacy_baseline`）与规则内部判定阈值动态下发；
- Task 027 建立了线程安全 LRU 快照缓存与三级局部重跑判定机制（`full_run` Tier 0 / `stage05_rules_rerun` Tier 1 / `stage07_rescore_only` Tier 2），提供毫秒级重算与 `snapshot_meta` 诊断元数据；
- Task 028 确立了可复现配置快照契约 `config.snapshot.v1` 与 16 位确定性 SHA-256 指纹 `config_digest`，打通 Markdown/JSON 报告固化配置快照与可复现载荷导出闭环，并在前端全面对齐 29 条规则与 Gatekeeper 提示；
- Task 029 借鉴 GitHub PR "Files changed"（Primer Design System）范式完成前端工作台深度重构，落地防溢出布局、左侧常驻 29 条规则目录与卡片抽屉、紧凑双层 PR 头部，以及「Sticky 层级目录树 + 连续 Diff 卡片流 + `Viewed` 已审阅跟踪 + 证据行高亮定位」审查视图。

本任务定位为内部阶段里程碑收工归档（Stage Closure），旨在：
1. 建立 `docs/versions/v1.3.0/` 冻结归档，迁入 Task 025–029 任务记录；
2. 清理并对齐全仓架构文档与工程规范，准确反映 v1.3 阶段产物；
3. 建立面向下一阶段的 `docs/tasks/v1.4-entry.md`，交接至 v1.4.0 规模型实证打靶与权重校准。

## 2. 范围与边界

### 纳入范围

1. **v1.3.0 阶段资产冻结归档**：建立 `docs/versions/v1.3.0/`，创建 `README.md`、`00-baseline-summary.md`，将 `docs/tasks/v1.3-entry.md` 更新为总结并归档为 `v1.3-entry.md`，迁入 `tasks/025..029`。
2. **活动任务工作区与 v1.4 入口建立**：创建 `docs/tasks/v1.4-entry.md`，更新 `docs/tasks/README.md`，登记活动任务 Task 030，下一个未使用编号更新为 031。
3. **架构与工程规范文档对齐**：更新 `docs/architecture.md`（补齐 GitHub Primer 审查工作区架构事实）、`docs/README.md`、`docs/versions/README.md`、`docs/standards/document-structure.md`、`docs/standards/branching-and-tasks.md` 与根目录 `AGENTS.md`。

### 不做事项（技术边界）

- 不改动 `backend/prisk/` 下的运行时检测器、评分逻辑、缓存模型、导出引擎或 API 实现。
- 不改动 `backend/data/rules/rule-registry.json` 或 `docs/rules/catalog/` 中 26 张规则卡片的正文与生命周期状态（保持 24 `implemented` / 5 `draft`）。
- 保持 2 张延后草稿卡片（`data.django_transaction_boundary_changed` 与 `workflow.large_change_scope`）的 `draft` 状态不变。
- 不修改 `docs/blueprint.md` 规格原文。

## 3. 技术方案与契约设计

### 核心方案

- **阶段归档隔离**：按照 `document-structure.md` 的冻结文本原则，将 v1.3.0 阶段完成的任务（025–029）整体迁入 `docs/versions/v1.3.0/tasks/`，活动工作区 `docs/tasks/` 仅保留当前收工任务 030 及标准模板。
- **Task 025 衔接性归档**：Task 025 虽为 v1.2.0 的收尾任务，但作为 v1.3.0 活动前夜的衔接记录，一并归入 `v1.3.0/tasks/`，确保编号 001–029 全部有序归档。
- **测试断言严格兼容**：维护 `backend/tests/services/test_rule_registry.py` 及全套 209 项单元与集成测试，确保所有测试无感通过。

### 契约与兼容性

- **阶段 Schema 与接口**：纯文档与归档任务，不涉及 `stage03`–`stage08` Schema、`config.snapshot.v1`、CLI 或 HTTP API 变更。
- **评分与权重基线**：运行时规则目录维持 29 条，默认兼容预设（`legacy_baseline`）满分基线 `maximum_points=10` 不变。
- **历史快照兼容**：`backend/data/demo/`、`docs/versions/v1.0.0/`、`docs/versions/v1.1.0/` 与 `docs/versions/v1.2.0/` 冻结资产保持零篡改。

## 4. 交付物与改动清单

### 改动文件

- **阶段冻结归档**：
  - 新增 [`docs/versions/v1.3.0/README.md`](../versions/v1.3.0/README.md)、[`00-baseline-summary.md`](../versions/v1.3.0/00-baseline-summary.md)、[`v1.3-entry.md`](../versions/v1.3.0/v1.3-entry.md)；
  - 迁入归档任务 [`docs/versions/v1.3.0/tasks/025..029`](../versions/v1.3.0/tasks/)；
  - 更新 [`docs/versions/README.md`](../versions/README.md)。
- **活动任务工作区**：
  - 新增 [`docs/tasks/030-v13-milestone-closure.md`](030-v13-milestone-closure.md)（本文件）；
  - 新增 [`docs/tasks/v1.4-entry.md`](v1.4-entry.md)；
  - 更新 [`docs/tasks/README.md`](README.md)。
- **架构、标准与协作规范**：
  - 更新 [`docs/architecture.md`](../architecture.md)、[`docs/README.md`](../README.md)；
  - 更新 [`docs/standards/document-structure.md`](../standards/document-structure.md)、[`docs/standards/branching-and-tasks.md`](../standards/branching-and-tasks.md)；
  - 更新根目录 [`AGENTS.md`](../../AGENTS.md)。

## 5. 验证与验收

### 验收要点

- `docs/versions/v1.3.0/` 包含完整的 `README.md`、`00-baseline-summary.md`、`v1.3-entry.md` 及 Task 025–029 任务文件。
- `docs/tasks/README.md` 与 `v1.4-entry.md` 准确标识下一个未使用编号为 031。
- `docs/architecture.md` 准确表述 GitHub Primer 前端审查工作台事实。
- 后端 209 项单元测试、前端 Lint 与 TypeCheck、Git diff check 全部一次性通过。

### 执行检查

- **后端测试**：`backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend`（通过全部 209 项测试，0 失败 0 错误）
- **前端检查**：
  - `npm --prefix frontend run lint`（ESLint 零错误、零警告通过）
  - `npm --prefix frontend run typecheck`（TypeScript 零错误通过）
- **格式检查**：`git diff --check`（无空白字符或格式错误通过）

## 6. 已知限制与残余风险

- **2 张延后草稿卡片**：`data.django_transaction_boundary_changed`（语句级包含关系）与 `workflow.large_change_scope`（项目动态阈值与模块映射）仍保持 `draft`，待后续全仓分析或外部输入支持。
- **实证打靶与权重校准义务**：已落地的 24 条三态检测器与 5 套场景预设权重已通过构造测试与功能验证，面向开源仓库大规模 PR 的正式实证有效性评测（`validated`）与默认基线权重校准按大纲统一安排在 v1.4.0 阶段。
