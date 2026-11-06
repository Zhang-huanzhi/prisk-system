---
task_id: "010"
target_version: "v1.1.0"
title: "Add the Prisk-System development roadmap"
status: "In Progress"
branch: "docs/010-development-roadmap"
date: "2026-11-06"
---

# 010：Add the Prisk-System development roadmap

## 目标

把用户确认的开发推进大纲放入 [docs/roadmap.md](../roadmap.md)，并在 [文档入口](../README.md) 增加指向它的规划条目。`target_version` 只表示这条文档工作记在尚未归档的 v1.1.0 任务线上。它不表示 v1.1.0 至 v1.4.0 已经发布，也不表示大纲里的后续版本已经实现。

用户尚未接受本任务。状态保持 In Progress。Git 分支、本文件和前言 `branch` 都是 `docs/010-development-roadmap`。交付记录是 [PR #10](https://github.com/Zhang-huanzhi/prisk-system/pull/10)。写下这条记录时该 PR 尚未合并。本提交不合并、不打 tag，也不把任务移入 `docs/versions/`。

## 编号核对

开始改文件之前核对过 001–009：均为已有任务。008 与 009 已合并进 `main`。仓库里没有任务 010，也没有 `T010.yaml`。`docs/roadmap.md` 在该 `main` 上不存在，因此这次是新增，不是覆盖。v1.0.0 的阶段编号不是任务编号。

## 依赖

- [008](008-docs-structure-blueprint.md) 已合并，提交 `92b819a5e70d749b99520fda750c38004b5c4384`。文档入口、任务目录和分支规范以该结构为准。本任务不改蓝图原文。
- [009](009-explicit-rule-outcomes.md) 已合并，提交 `2beb40175a049be41bf5daf72b82350fa1330ded`。本分支从该 `main` 提交创建。本任务不修改 009 的记录、状态、终态实现或该提交。

已接受的 [核心蓝图](../blueprint.md) 仍是目标系统规格。本大纲不替换它，也不把它改写成另一份规格。009 已经为当前 13 条运行时规则在新鲜分析里记录 Hit / NotFound / Unanalyzed。大纲里的版本条目仍是计划；本任务不把任何一条写成已经交付的版本。

## 范围

- 将官方推进大纲原文写入 `docs/roadmap.md`，与附件逐字节相同。标题、加粗、编号、嵌套、范围写法、箭头 emoji、行内代码和语言都保持原文。
- 增加本任务记录。前言使用现行键：`task_id`、`target_version`、`title`、`status`、`branch`、`date`。`branch` 填写 `docs/010-development-roadmap`。`status` 为 In Progress。
- 在 `docs/README.md` 的分层表和入口增加指向 `roadmap.md` 的规划条目，并写明：This is a planning document and is not evidence of completion or implemented functionality.
- 在 `docs/tasks/README.md` 的活动任务索引加入 010。状态为 In Progress，前言分支为 `docs/010-development-roadmap`。索引沿用现有列，不新增所有者列。

## 交付

- `docs/roadmap.md`：官方推进大纲原文。
- `docs/README.md`：文档总入口中的规划条目，链到 `roadmap.md`。
- `docs/tasks/010-development-roadmap.md`：本任务记录。
- `docs/tasks/README.md`：活动任务索引中的 010。

## 不做事项

- 不修改 `backend/`、`frontend/`、锁文件、`docs/blueprint.md`、`docs/rules/` 或 `docs/schemas/`。
- 不把大纲中的 v1.1.0、v1.2.0、v1.3.0、v1.4.0 条目写成已经存在的功能或已经取得的成果。计划不是完成。
- 不改写已接受的蓝图，不把蓝图中的机器学习、权重调优、动态配置或实证验证回填成当前实现。
- 不把 009 已接受的终态记录改写成“v1.2.0 已经完成”，也不改 009 的任务文件。
- 不把 010 标为 Accepted。用户尚未接受。
- 不合并，不打 tag，不删除分支。
- 不建立 `docs/versions/v1.1/` 或 `docs/versions/v1.1.0/`。
- 不另写 `T010.yaml`，不另写第二份大纲。
- 不改 001–009 的结论、状态和前言 `branch`。
- 不修改 `docs/standards/`。因此 [任务与分支](../standards/branching-and-tasks.md) 里“下一个未使用的编号是 010”仍是 010 开始前的句子；活动索引以本目录 README 为准。`docs/standards/document-structure.md` 的目录表也尚未列入 `roadmap.md`。

## 验收

- Git 分支、文件 `docs/tasks/010-development-roadmap.md` 和前言 `branch` 都是 `docs/010-development-roadmap`。
- 前言含 `task_id`、`target_version`、`title`、`status`、`branch`、`date`。状态是 In Progress。标题是 `Add the Prisk-System development roadmap`。
- `docs/roadmap.md` 与官方原文逐字节相同。
- 原文结构仍在：一级标题；三个 `###` 小节（版本演进大纲、注意事项、核心风险）；版本条目的加粗；注意事项 1–5 与核心风险 1–3；两空格嵌套列表；范围写法 `20+`、`10~20`、`8~10`、`1~2` 和 `30`；箭头 emoji `➔`；行内代码 `` `Hit` ``、`` `NotFound` ``、`` `Unanalyzed` ``。
- `docs/README.md` 有指向 `roadmap.md` 的规划入口，并写明该文件是规划文档，不是完成证据，也不是已实现功能的证据。
- `docs/tasks/README.md` 列出 010，状态为 In Progress，分支为 `docs/010-development-roadmap`，没有把 010 写成 Accepted。
- 本变更新增或改写的相对链接指向现存路径。
- `git diff` 不改 `backend/`、`frontend/`、蓝图、规则、schema 或锁文件。

## 实际验证

下列检查在本工作区执行。本变更只改文档，不改运行时代码、测试或锁文件，因此没有运行后端 unittest，也没有运行前端 lint、typecheck 或 build。下面不把未运行的套件写成已通过。

- 官方附件与 `docs/roadmap.md` 逐字节相同。SHA-256 为 `1fe07a47f460354b2b0903e1a7e6a6fd1a1fa43c08f7aa93d16768484cdc216b`。文件 2694 字节，UTF-8，无 BOM，只有 LF。
- 标题仍是 `# Prisk-System 推进大纲`。三个小节标题仍是 `### 一、 版本演进大纲`、`### 二、 注意事项`、`### 三、 核心风险`。加粗版本条目仍是 v1.1.0、v1.2.0、v1.3.0、v1.4.0 四条。注意事项仍为 1–5，核心风险仍为 1–3。嵌套项仍以两个空格加 `*` 开始。`20+`、`10~20`、`8~10`、`1~2` 和 `30` 仍在。`➔` 仍只出现一次。行内代码仍是 `Hit`、`NotFound`、`Unanalyzed`。
- `docs/README.md` 的分层表列出 `roadmap.md`，入口用相对链接指向 `roadmap.md`。两处都有句子 “This is a planning document and is not evidence of completion or implemented functionality.”
- 前言六键与上面的验收一致。`docs/tasks/README.md` 的 010 行是 In Progress 和 `docs/010-development-roadmap`。001–009 的状态行未改成别的状态。
- 本任务文件、两份 README 里本次涉及的相对链接都能在仓库中解析。
- `git diff --check` 通过。变更文件只有 `docs/roadmap.md`、`docs/README.md`、`docs/tasks/README.md` 和 `docs/tasks/010-development-roadmap.md`。

## 遗留风险

- 大纲描述后续计划。阅读 `docs/roadmap.md` 不能当作这些版本已经交付。v1.2.0 的三态协议条目不是 009 已接受终态的完成声明，也不是新的已实现功能。
- 本任务未被接受。索引中的 In Progress 要保持到用户接受为止。
- `docs/standards/branching-and-tasks.md` 仍写着下一个未使用编号是 010。`docs/standards/document-structure.md` 的目录表尚未列入 `roadmap.md`。这两份规范不在本任务允许修改的文件里。
