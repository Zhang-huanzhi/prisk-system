---
task_id: "023"
target_version: "v1.2.0"
title: "任务文件模板与用法说明"
status: "In Progress"
branch: "docs/023-task-template"
date: "2026-11-10"
---

# 023：任务文件模板与用法说明

## 目标

为 `docs/tasks/` 提供可复用的任务记录模板，并在目录 README 中写明如何复制模板、如何选取下一个未使用编号、分支如何命名，以及任务文件应写什么、不应写什么。本任务是 v1.2 阶段内的文档簿记，不宣布 v1.2.0 完成。

## 范围

- 新增任务模板 `docs/tasks/_task-template.md`。文件名不以三位任务编号开头，避免被当成活动任务。
- 更新 `docs/tasks/README.md`：补充复制模板、编号、分支命名，以及任务文件与流程编排文字的边界。本任务占用 023 后，下一个未使用编号是 024。
- 新增本任务记录 `docs/tasks/023-task-template.md`，并在 `docs/tasks/README.md` 与 `docs/tasks/v1.2-entry.md` 的活动表中登记。
- 删除活动任务中已有的「验收说明」流程段落；当前需要删除的是 020 与 021。022 本来就没有该节。

## 不做事项

- 不改检测器或其他运行时代码，不跑与文档无关的测试套件。
- 不建立 `docs/versions/v1.2*`，不打 Tag。
- 不开 024，不发明产品检测器任务。
- 不把流程编排文字写进模板或本任务记录。

## 设计

- 模板前言字段与现行任务记录一致：`task_id`、`target_version`、`title`、`status`、`branch`、`date`。
- 正文标题与现行密切片任务一致：目标、范围、不做事项、设计、实现、验证、可选的生命周期增量、残余风险。生命周期增量标为可选，避免无生命周期改动的任务去编造规则 ID。
- 模板只放占位说明，不放虚构规则或未发生的事实。
- 模板故意不含「验收说明」或任何流程编排段落。结构化状态只出现在前言的 `status` 字段，以及活动任务表的行里。
- 分支类型与形式以 [任务与分支](../standards/branching-and-tasks.md) 为准：`<type>/<三位任务编号>-<短英文名>`，类型为 `feat`、`fix`、`docs`、`refactor`、`exp`、`chore`。

## 实现

- `docs/tasks/_task-template.md`：新增模板。
- `docs/tasks/023-task-template.md`：按模板填写本任务事实。
- `docs/tasks/README.md`：补充用法，并把 023 登记进活动表；「下一个未使用的任务编号」改为 024。
- `docs/tasks/v1.2-entry.md`：活动表增加 023，下一个未使用编号改为 024。
- `docs/tasks/020-residual-detector-alignment.md`、`docs/tasks/021-high-value-draft-detectors.md`：只删除「验收说明」一节，不改技术正文。

## 验证

- 文档任务，不跑后端 `unittest`。
- `git diff --check`：无错误。
- 对改动文件做控制字符扫描：除换行与制表符外无其他 ASCII 控制字符。

## 残余风险

- [任务与分支](../standards/branching-and-tasks.md) 里「下一个未使用的任务编号」仍写 021，与本目录 README 在本任务之后应为 024 的说法不一致。本任务不改那份规范正文。
- 部分既有任务的「不做事项」里仍可能出现合并或分支安排的句子；本任务只删除独立的「验收说明」一节，不改写那些历史条目。
- 019 的「验证与验收」是检查结果节，不是「验收说明」，因此保留。
