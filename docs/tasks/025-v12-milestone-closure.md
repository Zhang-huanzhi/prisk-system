---
task_id: "025"
target_version: "v1.2.0"
title: "v1.2 阶段里程碑收工归档与文档对齐"
status: "Accepted"
branch: "docs/025-v12-milestone-closure"
date: "2026-11-10"
---

# 025：v1.2 阶段里程碑收工归档与文档对齐

## 1. 背景与目标

在已完成的 Task 020–024 基础上，Prisk-System v1.2.0 阶段（核心规则实现与三态引擎能力闭环）的全部工程与规则目标已圆满达成：
- Task 020 解决了 7 项残余检测器与合同对齐问题（含 `code.bare_exception` 拆分、`Path.open` 扩展、已知框架基类映射、`Meta.fields` 常量解析、`default=`/`null=` 提取、敏感配置方向判定与 Gatekeeper 一票抬升）；
- Task 021、022、024 分三批实现了 15 条高价值草稿规则的三态检测器与构造测试，知识库 26 张卡片中 24 张单文件/Diff 本地 AST 可行卡片全部晋升为 `implemented`，运行时规则扩充至 29 条；
- Task 023 建立了标准化任务模板 `_task-template.md` 并完成历史活动任务对齐。

本任务定位为内部阶段里程碑收工归档（Stage Closure），旨在：
1. 建立 `docs/versions/v1.2.0/` 冻结归档，迁入 Task 019–024 任务记录；
2. 清理 `docs/architecture.md`、`docs/rules/README.md` 与规范文档中的历史残留陈述；
3. 建立面向下一阶段的 `docs/tasks/v1.3-entry.md`，平滑交接至 v1.3.0 动态交互工作台演进。

## 2. 范围与边界

### 纳入范围

1. **v1.2.0 阶段资产冻结归档**：建立 `docs/versions/v1.2.0/`，创建 `README.md`、`00-baseline-summary.md`，将 `docs/tasks/v1.2-entry.md` 更新为总结并归档为 `v1.2-entry.md`，迁入 `tasks/019..024`。
2. **活动任务工作区与 v1.3 入口建立**：创建 `docs/tasks/v1.3-entry.md`，更新 `docs/tasks/README.md`，登记活动任务 Task 025，下一个未使用编号更新为 026。
3. **架构与知识库文档对齐**：更新 `docs/architecture.md`（清除已过时的 v1.1 残余说明，准确记录 29 条规则与 Gatekeeper 机制）、`docs/README.md`、`docs/rules/README.md`、`docs/rules/structural-feasibility.md`、`docs/rules/v1.1-card-readiness.md`、`docs/rules/rule-responsibility-matrix.md`。
4. **工程协作规范同步**：更新 `docs/standards/document-structure.md`、`branching-and-tasks.md` 与根目录 `AGENTS.md`。

### 不做事项（技术边界）

- 不改动 `backend/prisk/` 下的运行时检测器、评分逻辑、CLI 或 API 实现。
- 不改动 `backend/data/rules/rule-registry.json` 或 `docs/rules/catalog/` 中 26 张规则卡片的正文与生命周期状态（保持 24 `implemented` / 5 `draft`）。
- 保持 2 张延后草稿卡片（`data.django_transaction_boundary_changed` 与 `workflow.large_change_scope`）的 `draft` 状态不变。
- 不修改 `docs/blueprint.md` 规格原文。

## 3. 技术方案与契约设计

### 核心方案

- **阶段归档隔离**：按照 `document-structure.md` 的冻结文本原则，将 v1.2.0 阶段完成的任务（019–024）整体迁入 `docs/versions/v1.2.0/tasks/`，活动工作区 `docs/tasks/` 仅保留当前收工任务 025 及标准模板。
- **Task 019 衔接性归档**：Task 019 虽为 v1.1.0 的收尾任务，但作为 v1.2.0 活动前夜的衔接记录，一并归入 `v1.2.0/tasks/`，确保编号 001–024 全部有序归档。
- **测试断言严格兼容**：维护 `backend/tests/services/test_rule_registry.py` 对 `docs/rules/README.md`、`structural-feasibility.md` 与 `v1.1-card-readiness.md` 的断言锚点语句，确保所有测试无感通过。

### 契约与兼容性

- **阶段 Schema 与接口**：纯文档与归档任务，不涉及 `stage03`–`stage08` Schema、CLI 或 HTTP API 变更。
- **评分与权重基线**：运行时规则目录维持 29 条，默认权重均为 0，默认满分基线 `maximum_points=10` 不变。
- **历史快照兼容**：`backend/data/demo/`、`docs/versions/v1.0.0/` 与 `docs/versions/v1.1.0/` 冻结资产保持零篡改。

## 4. 交付物与改动清单

### 改动文件

- **阶段冻结归档**：
  - 新增 [`docs/versions/v1.2.0/README.md`](../versions/v1.2.0/README.md)、[`00-baseline-summary.md`](../versions/v1.2.0/00-baseline-summary.md)、[`v1.2-entry.md`](../versions/v1.2.0/v1.2-entry.md)；
  - 迁入归档任务 [`docs/versions/v1.2.0/tasks/019..024`](../versions/v1.2.0/tasks/)；
  - 更新 [`docs/versions/README.md`](../versions/README.md)。
- **活动任务工作区**：
  - 新增 [`docs/tasks/025-v12-milestone-closure.md`](025-v12-milestone-closure.md)（本文件）；
  - 新增 [`docs/tasks/v1.3-entry.md`](v1.3-entry.md)；
  - 更新 [`docs/tasks/README.md`](README.md)。
- **架构、规则与标准规范**：
  - 更新 [`docs/architecture.md`](../architecture.md)、[`docs/README.md`](../README.md)；
  - 更新 [`docs/rules/README.md`](../rules/README.md)、[`docs/rules/structural-feasibility.md`](../rules/structural-feasibility.md)、[`docs/rules/v1.1-card-readiness.md`](../rules/v1.1-card-readiness.md)、[`docs/rules/rule-responsibility-matrix.md`](../rules/rule-responsibility-matrix.md)；
  - 更新 [`docs/standards/document-structure.md`](../standards/document-structure.md)、[`docs/standards/branching-and-tasks.md`](../standards/branching-and-tasks.md)；
  - 更新根目录 [`AGENTS.md`](../../AGENTS.md)。

## 5. 验证与验收

### 验收要点

- `docs/versions/v1.2.0/` 包含完整的 `README.md`、`00-baseline-summary.md`、`v1.2-entry.md` 及 Task 019–024 任务文件。
- `docs/tasks/README.md` 与 `v1.3-entry.md` 准确标识下一个未使用编号为 026。
- `docs/architecture.md` 准确表述 29 条规则与 Gatekeeper 机制，无过时未决表述。
- 后端 186 项单元测试、前端 Lint 与 TypeCheck、Git diff check 全部一次性通过。

### 执行检查

- **后端测试**：`backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend`（186 项单元与集成测试全部通过，耗时 134.354s，OK）
- **前端检查**：
  - `npm --prefix frontend run lint`（ESLint 零错误、零警告通过）
  - `npm --prefix frontend run typecheck`（TypeScript 零错误通过）
- **格式检查**：`git diff --check`（无空白字符或格式错误通过）

## 6. 已知限制与残余风险

- **2 张延后草稿卡片**：`data.django_transaction_boundary_changed`（语句级包含关系）与 `workflow.large_change_scope`（项目动态阈值与模块映射）仍保持 `draft`，待后续全仓分析或动态工作台阶段演进。
- **实证验证义务**：已落地的 24 条三态检测器已通过单测构造测试验证工程正确性，面向开源仓库大规模 PR 的实证有效性评测（`validated`）与权重校准按大纲统一安排在 v1.4 阶段。
