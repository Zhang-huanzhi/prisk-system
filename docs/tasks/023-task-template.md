---
task_id: "023"
target_version: "v1.2.0"
title: "任务文档规范重构与历史活动任务对齐"
status: "Accepted"
branch: "docs/023-task-template"
date: "2026-11-10"
---

# 023：任务文档规范重构与历史活动任务对齐

## 1. 背景与目标

在推进 v1.2 阶段任务（Task 019–022）的过程中，既有任务文档暴露出三类明显问题：

1. **模板过于扁平空洞**：原 `_task-template.md` 仅提供单句占位符，缺乏针对 Prisk-System 核心工程要素（三态引擎 `Hit / NotFound / Unanalyzed` 判定契约、Stage03–08 数据 Schema 与历史快照兼容性、规则生命周期账本、静态分析有效性边界）的结构化引导。
2. **设计与实现混杂、可读性差**：部分检测器批次任务（如 021、022）在「范围/设计」中仅写两三行简略概述，却将复杂的 AST 边界逻辑堆砌在文件列表里，缺乏统一的规则判定契约表与分类交付物清单。
3. **流程套话与规范滞后**：任务正文中残留大量关于 Git 操作或角色编排的免责套话（如“PR 仍开、合并由某角色执行、不打 Tag、不开下一任务”），且 [`branching-and-tasks.md`](../standards/branching-and-tasks.md) 中的任务编号基线停留在 021，与实际进度脱节。

本任务旨在重构面向 Prisk-System 的标准化任务模板与写作指南，并将当前工作区内的全部活动任务（Task 019–022）及关联标准文档按新规范统一升级对齐。

## 2. 范围与边界

### 纳入范围

1. **重构标准任务模板 [`docs/tasks/_task-template.md`](_task-template.md)**：确立「1. 背景与目标、2. 范围与边界、3. 技术方案与契约设计、4. 交付物与改动清单、5. 验证与验收、6. 已知限制与残余风险」六节标准结构。
2. **重写活动任务工作区指南 [`docs/tasks/README.md`](README.md)**：明确任务文档的三重职责（工程实施契约、规则与三态引擎账本、阶段归档与论文素材），提供按任务类型（规则检测器 / 系统架构与工作台 / 实验评估与文档规范）的写作侧重矩阵与反模式说明。
3. **重构当前活动任务记录（Task 019–022）**：将 [`019`](019-v11-milestone-closure.md)、[`020`](020-residual-detector-alignment.md)、[`021`](021-high-value-draft-detectors.md)、[`022`](022-second-high-value-draft-detectors.md) 全部升级为六节标准结构，补齐规则三态契约总表、兼容性说明与分类交付物清单，剔除流程编排套话。
4. **同步标准规范文档**：更新 [`docs/standards/branching-and-tasks.md`](../standards/branching-and-tasks.md) 与 [`docs/standards/development-process.md`](../standards/development-process.md)，消除编号基线不一致问题。

### 不做事项（技术边界）

- 不改动 `backend/prisk/` 或 `frontend/` 下的运行时代码与业务逻辑。
- 不回写已冻结归档的 [`docs/versions/v1.0.0/`](../versions/v1.0.0/README.md) 与 [`docs/versions/v1.1.0/tasks/`](../versions/v1.1.0/README.md) 历史文档（遵循冻结文本原则）。
- 不修改 26 张规则卡片正文与 `rule-registry.json` 元数据。

## 3. 技术方案与契约设计

### 核心方案

将任务文档从“流水账备忘录”升级为契合 Prisk-System 研发与论文双重要求的结构化规格说明：

| 标准章节 | 核心设计意图 | 针对 Prisk-System 的结构化要素 |
| :--- | :--- | :--- |
| **1. 背景与目标** | 交代上下文承接关系与核心价值 | 关联阶段入口（如 `v1.2-entry.md`）、前序任务遗留项及本切片目标 |
| **2. 范围与边界** | 划清交付范围与技术排除项 | 拆分为「纳入范围」与「不做事项（技术边界）」，隔离日常流程噪音 |
| **3. 技术方案与契约设计** | 解耦“怎么设计”与“改了哪些文件” | 包含 **核心方案**（检测器任务采用三态契约表汇总 `Hit / NotFound / Unanalyzed`）与 **契约与兼容性**（Stage Schema、满分基线、Demo 快照兼容） |
| **4. 交付物与改动清单** | 便于代码审查与资产溯源 | 按「源码实现 / 规则与数据资产 / 测试与文档」分类，并内嵌可选的 **规则生命周期变更** 表 |
| **5. 验证与验收** | 区分功能断言与命令执行结果 | 拆分为「验收要点」（业务与契约断言）与「执行检查」（测试计数与命令结果） |
| **6. 已知限制与残余风险** | 沉淀后续任务输入与论文有效性分析素材 | 按「静态分析边界 / 工程管线限制 / 后续演进事项」分类记录客观限制 |

### 契约与兼容性

- **阶段 Schema 与接口**：纯文档与工程规范重构，不改变运行时代码、`stage03`–`stage08` Schema、CLI 或 HTTP API。
- **评分与权重基线**：运行时规则目录维持 26 条，登记册状态（`implemented: 21`, `draft: 8`）与默认满分基线（`maximum_points=10`）不变。
- **历史快照兼容**：已保存的 `backend/data/demo/` 与 `docs/versions/` 冻结资产保持不变。

## 4. 交付物与改动清单

### 改动文件

- **模板与工作区指南**：
  - [`docs/tasks/_task-template.md`](_task-template.md)：重构为六节标准结构，内嵌任务类型引导与契约兼容性、生命周期表格模板。
  - [`docs/tasks/README.md`](README.md)：补充任务文档定位、三类任务写作侧重表、反模式约束及活动任务索引。
  - [`docs/tasks/v1.2-entry.md`](v1.2-entry.md)：同步 Task 023 标题与下一个未使用编号（024）。
- **重构对齐的活动任务**：
  - [`docs/tasks/019-v11-milestone-closure.md`](019-v11-milestone-closure.md)：按六节模板补齐技术方案、契约兼容性、改动清单与残余风险。
  - [`docs/tasks/020-residual-detector-alignment.md`](020-residual-detector-alignment.md)：增加 7 项合同对齐与支撑机制总表，补齐契约兼容性与分类交付物。
  - [`docs/tasks/021-high-value-draft-detectors.md`](021-high-value-draft-detectors.md)：增加第一批 6 条规则的三态判定契约表与完整改动清单。
  - [`docs/tasks/022-second-high-value-draft-detectors.md`](022-second-high-value-draft-detectors.md)：增加第二批 6 条规则的三态判定契约表，提炼「关键边界设计说明」子节。
  - [`docs/tasks/023-task-template.md`](023-task-template.md)：本任务记录。
- **工程标准规范**：
  - [`docs/standards/branching-and-tasks.md`](../standards/branching-and-tasks.md)：对齐任务编号基线与六节正文结构说明，避免硬编码编号反复过期。
  - [`docs/standards/development-process.md`](../standards/development-process.md)：同步任务文档章节名称与模板引用。

## 5. 验证与验收

### 验收要点

- `_task-template.md`、`docs/tasks/README.md`、`branching-and-tasks.md` 与 `development-process.md` 章节定义、编号规则及相对链接完全一致。
- 当前全部活动任务（Task 019–023）统一遵循六节结构，技术细节（规则 ID、测试数量、生命周期变更）与代码库事实 100% 吻合，无流程编排套话残留。
- 后端与前端自动化检查全部通过。

### 执行检查

- **后端测试**：`backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend`（167 项测试全部通过）
- **前端检查**：`npm --prefix frontend run lint` 与 `npm --prefix frontend run typecheck`（通过）
- **格式检查**：`git diff --check`（无空白或格式错误）

## 6. 已知限制与残余风险

- **历史归档版本保持原貌**：已归档于 `docs/versions/v1.1.0/tasks/` 的 Task 001–018 受冻结文本原则约束，保留归档时的原始结构，不回溯套用新模板。
- **架构文档待随阶段收口同步**：[`docs/architecture.md`](../architecture.md) 中的运行时规则计数（仍描述 v1.1 收工时的 14 条基线）留待 v1.2 后续规则切片收口时一并更新。
