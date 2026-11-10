# 活动任务

本目录仅保留尚未随版本归档的活动任务：进行中的任务，以及尚未冻结进 `docs/versions/` 的任务。

- **已归档任务**：
  - v1.1.0 阶段的 18 条任务（Task 001 至 018）已随里程碑收工完整归档至 [docs/versions/v1.1.0/tasks/](../versions/v1.1.0/tasks/)。
- **下一阶段入口**：
  - [v1.2 入口文档](v1.2-entry.md)。
- **任务模板**：
  - [任务记录模板](_task-template.md)。它不是一条活动任务，不要把它当成编号记录，也不要改它的文件名为三位数字前缀。

## 如何新建任务

1. 在下面的活动任务表和当前阶段入口（现在是 [v1.2 入口](v1.2-entry.md)）里确认「下一个未使用的任务编号」。本任务占用 023 之后，下一个未使用编号为 **024**。已使用的编号不重编、不复用。
2. 复制 [`_task-template.md`](_task-template.md) 为 `docs/tasks/NNN-short-name.md`。`NNN` 是三位任务编号，`short-name` 与分支的短英文名一致，使用小写字母、数字和连字符。
3. 填写前言字段：`task_id`、`target_version`、`title`、`status`、`branch`、`date`。`status` 只使用 `Proposed`、`In Progress`、`Accepted`，见 [任务与分支](../standards/branching-and-tasks.md)。没有明确验收时保持 `Proposed` 或 `In Progress`。
4. 按同一规范建立 Git 分支。形式为 `<type>/<三位任务编号>-<短英文名>`。类型只使用 `feat`、`fix`、`docs`、`refactor`、`exp`、`chore`。实现切片常用 `feat/NNN-…`，文档迭代常用 `docs/NNN-…`。
5. 任务编号、文件名前缀、前言中的 `branch` 与 Git 分支必须一对一一致。同一目标下的后续提交和评审修复继续使用同一条任务、同一条分支，不另取编号。
6. 在本目录活动任务表和当前阶段入口中各登记一行。

## 任务文件写什么、不写什么

任务文件写本任务的目标、范围、不做事项、设计、实现、验证，必要时写生命周期增量，以及残余风险。结构化状态只写在前言的 `status` 字段和活动任务表的行里。

任务文件不要写流程或编排说明。不要增加「验收说明」一节，不要写所有者验收叙事，也不要写「PR 仍开，合并与删分支由 Engineering Lead 执行」以及同类的系统外状态。这些内容不属于任务记录。

## 当前活动任务表

| 任务 | 目标版本 | 状态 | 前言中的 `branch` | 记录 |
| :---: | :---: | :---: | :--- | :--- |
| 019 | v1.1.0 | Accepted | `docs/019-v11-milestone-closure` | [v1.1 阶段里程碑收工归档与文档对齐精简](019-v11-milestone-closure.md) |
| 020 | v1.2.0 | Accepted | `feat/020-residual-detector-alignment` | [残余检测器与合同对齐（v1.2 首切片）](020-residual-detector-alignment.md) |
| 021 | v1.2.0 | Accepted | `feat/021-high-value-draft-detectors` | [高价值草稿检测器批次（v1.2 第二切片）](021-high-value-draft-detectors.md) |
| 022 | v1.2.0 | Accepted | `feat/022-second-high-value-draft-detectors` | [第二批高价值草稿检测器（v1.2 第三切片）](022-second-high-value-draft-detectors.md) |
| 023 | v1.2.0 | In Progress | `docs/023-task-template` | [任务文件模板与用法说明](023-task-template.md) |

> 下一个未使用的任务编号为 **024**。任何新工作均需创建新编号任务并建立一对一分支。
