# 活动任务工作区

本目录保存当前阶段尚未随里程碑冻结归档的活动任务记录、阶段入口文档与任务记录模板。

- **当前阶段入口**：[v1.3 下一阶段入口](v1.3-entry.md)
- **标准任务模板**：[`_task-template.md`](_task-template.md)（模板文件以 `_` 开头，不占用三位任务编号）
- **历史归档任务**：
  - v1.1.0 阶段的 Task 001–018 已归档至 [`docs/versions/v1.1.0/tasks/`](../versions/v1.1.0/tasks/)
  - v1.2.0 阶段的 Task 019–024 已归档至 [`docs/versions/v1.2.0/tasks/`](../versions/v1.2.0/tasks/)

---

## 1. 任务文档在项目中的定位

在 Prisk-System 中，每条任务文档（`docs/tasks/NNN-short-name.md`）同时承担三项职责：

1. **工程实施契约**：明确本次分支变更解决什么问题、技术边界在哪里、采用什么方案、改动了哪些文件、如何通过自动化验证。
2. **规则与三态引擎演进账本**：清晰记录规则生命周期（`draft → registered → implemented → validated`）、三态判定边界（`Hit / NotFound / Unanalyzed`）、阶段数据契约（`stage03`–`stage08`）及评分权重基线的变化。
3. **阶段归档与论文素材**：在里程碑收工时直接迁入 `docs/versions/<version>/tasks/`，为后续架构追溯与毕业论文（尤其是设计依据、实验设计与有效性威胁分析）提供结构化事实记录。

---

## 2. 新建与维护流程

1. **确认编号**：在下方「当前活动任务表」及阶段入口文档中确认下一个未使用的三位任务编号（当前为 **028**）。任务编号跨版本全局唯一，不重编、不复用。
2. **复制模板**：复制 [`_task-template.md`](_task-template.md) 为 `docs/tasks/NNN-short-name.md`，并按 [`branching-and-tasks.md`](../standards/branching-and-tasks.md) 创建同名一对一分支 `<type>/NNN-short-name`（`<type>` 限 `feat`、`fix`、`docs`、`refactor`、`exp`、`chore`）。
3. **填写前言与正文**：
   - YAML 前言必填 `task_id`、`target_version`、`title`、`status`（`Proposed` / `In Progress` / `Accepted`）、`branch`、`date`。
   - 任务启动时填写 `1. 背景与目标`、`2. 范围与边界`、`3. 技术方案与契约设计`；实施与验证完成后补齐 `4. 交付物与改动清单`、`5. 验证与验收` 与 `6. 已知限制与残余风险`。
4. **登记索引**：在本文件「当前活动任务表」与当前阶段入口（[`v1.3-entry.md`](v1.3-entry.md)）中同步登记。同一任务目标下的后续提交与评审修复均复用同一编号与分支。

---

## 3. 不同类型任务的写作侧重

所有任务统一采用 [`_task-template.md`](_task-template.md) 的六节结构，并根据任务性质在 **第 3 节（技术方案与契约设计）** 与 **第 4 节（交付物与改动清单）** 中有所侧重：

| 任务类型 | 典型分支前缀 | 第 3 节（方案与契约）写作重点 | 第 4 节（交付物）写作重点 |
| :--- | :---: | :--- | :--- |
| **规则与检测器落地**<br>（如 020、021、022、024） | `feat/` | 用表格或结构化条目写明每条规则的 AST/Diff 触发闭集、`Hit / NotFound / Unanalyzed` 三态边界及缺口原因码；说明运行时规则总数、默认权重与 Gatekeeper 影响。 | 列出检测器模块、规则登记册（`rule-registry.json`）、同步的规则卡片，并保留 **「规则生命周期变更」** 表格。 |
| **系统架构与工作台演进**<br>（如 009、后续 v1.3 任务） | `feat/` / `refactor/` | 说明模块分层职责、API/CLI 接口契约、`stage03`–`stage08` Schema 演进，以及对已保存 `backend/data/demo/` 历史快照的向后兼容性。 | 按后端（domain/services/adapters/cli）、前端组件与测试套件分类列出改动清单；不涉及规则晋升时删去生命周期表。 |
| **实验评估与文档规范**<br>（如 012、019、023、025） | `exp/` / `docs/` | 说明先导/实证抽样协议与数据集隔离原则，或说明文档架构重构、卡片模板升级与跨文档一致性对齐规则。 | 列出新增/重构的文档资产路径、归档迁移映射或校验脚本；不涉及规则状态变更时删去生命周期表。 |

### 写作规范与反模式

- **只写技术与研究事实**：正文聚焦代码、规则契约、数据 Schema 与验证数据。
- **剔除流程与编排套话**：`不做事项` 仅记录技术与业务排除项（如“不追踪跨文件继承”、“不解析 `RunSQL` 字符串”），**不写**“不合并 PR、不删分支、不打 Tag、不开下一任务、由某角色执行合并”等日常协作或流程编排语句。
- **不单设「验收说明」流程节**：任务状态仅通过 YAML 前言的 `status` 字段与活动任务表体现，不在正文末尾追加审批叙事段落。

---

## 4. 当前活动任务表

| 任务 | 目标版本 | 状态 | 分支 (`branch`) | 任务记录 |
| :---: | :---: | :---: | :--- | :--- |
| 025 | v1.2.0 | Accepted | `docs/025-v12-milestone-closure` | [v1.2 阶段里程碑收工归档与文档对齐](025-v12-milestone-closure.md) |
| 026 | v1.3.0 | Accepted | `feat/026-runtime-config-presets` | [运行时配置解耦与场景预设体系](026-runtime-config-presets.md) |
| 027 | v1.3.0 | Accepted | `feat/027-snapshot-partial-rerun` | [快照局部重跑与分析缓存](027-snapshot-partial-rerun.md) |

> 下一个未使用的任务编号为 **028**。任何新变更均须基于 [`_task-template.md`](_task-template.md) 创建新编号任务并建立一对一分支。
