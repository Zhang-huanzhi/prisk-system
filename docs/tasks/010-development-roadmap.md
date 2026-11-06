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

把官方开发推进大纲放在 [docs/standards/development-roadmap.md](../standards/development-roadmap.md)。[文档入口](../README.md)、[规范索引](../standards/README.md) 和 [活动任务](README.md) 直接链到这个路径。This is a planning document and is not evidence of completion or implemented functionality. `target_version` 只表示本任务记在尚未归档的 v1.1.0 任务线上。

状态保持 In Progress。用户尚未接受。分支、本文件和前言 `branch` 都是 `docs/010-development-roadmap`。交付记录是 [PR #10](https://github.com/Zhang-huanzhi/prisk-system/pull/10)。本提交不合并、不打 tag。

## 依赖

- [008](008-docs-structure-blueprint.md) 已合并：`92b819a5e70d749b99520fda750c38004b5c4384`。
- [009](009-explicit-rule-outcomes.md) 已合并：`2beb40175a049be41bf5daf72b82350fa1330ded`。本任务不修改 009。

## 范围

- 官方大纲字节保持 SHA-256 `1fe07a47f460354b2b0903e1a7e6a6fd1a1fa43c08f7aa93d16768484cdc216b`。不保留 `docs/roadmap.md`。
- 删除已跟踪的 `docs/iterations/`。活动文档去掉对该目录的现行链接，不另建转发目录。
- v1.0.0 冻结正文保持原句。阶段 04 结论不再链接缺失的全量 `stage04-structure-objects.jsonl`；文档级记录是 [stage04-manifest.json](../versions/v1.0.0/04-代码结构与变更表示/artifacts/stage04-manifest.json)。该 JSONL 不补造。
- [任务与分支](../standards/branching-and-tasks.md) 仍规定没有用户接受时不写成 Accepted。010 为 In Progress 之后，下一个未使用编号是 011。

## 不做事项

- 不修改 `docs/blueprint.md`、`docs/rules/`、运行时代码或锁文件。
- 不把大纲里的版本条目写成已实现功能。
- 不把 010 标为 Accepted，不合并，不打 tag，不删除本分支。
- 不改 001–009 的结论、状态和前言 `branch`。
- 不把全部历史链接说成已经通过。002 里有意保留的旧卡片路径不在本次清理范围。

## 验收

- 大纲文件与官方原文逐字节相同，路径是 `docs/standards/development-roadmap.md`。
- 三处索引直接链接该文件，并写明它是规划文档。
- 仓库中没有 `docs/roadmap.md`，也没有 `docs/iterations/`。
- 前言状态是 In Progress。

## 实际验证

本变更只改文档。没有运行后端 unittest，也没有运行前端 lint、typecheck 或 build。

- `docs/standards/development-roadmap.md` 的 SHA-256 是 `1fe07a47f460354b2b0903e1a7e6a6fd1a1fa43c08f7aa93d16768484cdc216b`。仓库里没有 `docs/roadmap.md`，也没有 `docs/iterations/`。
- 当前入口扫描了 `docs/README.md`、`docs/standards/` 下的规范与大纲、`docs/tasks/README.md`、本任务、`docs/versions/README.md`、`AGENTS.md`，以及阶段 04 结论。这些文件里的 91 条相对链接都能解析。
- 全库 `docs/**/*.md` 另有 5 条相对链接指向不存在的路径，都在 `docs/tasks/002-rule-knowledge-base.md` 的旧卡片路径。本次没有改那份记录，也不把全部历史链接记为通过。
- 全量 `stage04-structure-objects.jsonl` 仍不在仓库中。`stage04-manifest.json` 存在。
- `git diff --check` 在提交本记录前通过。
