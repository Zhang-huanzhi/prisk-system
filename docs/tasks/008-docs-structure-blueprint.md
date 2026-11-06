---
task_id: "008"
target_version: "v1.1.0"
title: "文档信息架构与核心蓝图"
status: "In Progress"
branch: "docs/008-docs-structure-blueprint"
date: "2026-11-06"
---

# 008：文档信息架构与核心蓝图

## 目标

整理文档信息架构，并把用户确认的核心蓝图原文放入 `docs/blueprint.md`。`target_version` 只表示这条文档工作记在尚未归档的 v1.1.0 任务线上。它不表示 v1.1.0 已经实现蓝图。

## 编号核对

开始改文件之前，仓库里没有任务 008，也没有 `T008.yaml`。v1.0.0 的阶段 08 是「本地项目与分支审计」，不是任务编号。001–007 均为 Accepted。008 不与这些编号冲突，也不重用它们。

## 范围

- 用 `git mv` 把 `docs/iterations/v1.1/` 的 001–007 和当时的入口移到 `docs/tasks/`。
- 用 `git mv` 把 `docs/development-process.md` 移到 `docs/standards/development-process.md`，并按现行任务规则更新这份仍在使用的流程说明。
- 增加文档结构、任务与分支规范、版本索引、迭代路径对照、研究规则索引、schema 索引和资产状态。
- 把官方蓝图原文写入 `docs/blueprint.md`。文档入口直接链到该文件。
- 修正随移动而失效的相对链接。001–007 的结论、编号、状态和前言 `branch` 不改。

## 不做事项

- 不修改 `backend/` 或 `frontend/` 的源码和测试行为。
- 不把 008 写成 Accepted，不合并，不打 tag。
- 不重编号，不复用 001–007，不猜测并回填历史分支。
- 不建立 `docs/versions/v1.1/` 或 `docs/versions/v1.1.0/`。
- 不另写 `T008.yaml`，不另写第二份蓝图。
- 不把蓝图里的机器学习、权重调优、动态配置、NotFound 全量跟踪或 NetBox 实证验证写成当前实现。
- 不改写 v1.0.0 已有结论，不改写 002 里保留的旧路径引用。

## 当前基线

008 不改变运行时规则。编写本记录时，已接受实现的运行时目录有 13 条，其中包括 Accepted 007 的 `workflow.test_collaboration_gap`：

- `api.signature_changed`
- `auth.permission_structure_changed`
- `data.transaction_structure_changed`
- `config.configuration_structure_changed`
- `code.exception_structure_changed`
- `code.swallowed_exception`
- `code.bare_exception`
- `code.dynamic_execution`
- `code.unmanaged_open`
- `code.deep_control_flow`
- `code.hardcoded_secret`
- `code.global_mutable_state`
- `workflow.test_collaboration_gap`

这 13 条是当前目录事实，不是蓝图已经交付的证明。权重仍是已接受任务留下的工程默认值，不是按合格标注完成的调优。

## 验收

- Git 分支、文件 `docs/tasks/008-docs-structure-blueprint.md` 和前言 `branch` 都是 `docs/008-docs-structure-blueprint`。
- 不存在第二份 `T008.yaml`。
- [任务与分支](../standards/branching-and-tasks.md) 写明：任何规模的变更都要有任务；小改动豁免已废除且不保留；分支类型仅为 `feat`、`fix`、`docs`、`refactor`、`exp`、`chore`；形式与任务一对一；新任务必须填写 `branch`。
- 001–007 仍为 Accepted，编号和前言 `branch` 与移动前一致。
- `docs/blueprint.md` 与官方原文逐字节相同，含八个小节，以及流程代码块里 `base...head` 和 `上下文` 后面的空格。
- 文档入口直接链到 `docs/blueprint.md`。其他说明只引用该原文。
- 相对链接可解析。002 中有意保留的旧卡片路径，以及 v1.0.0 里原本指向缺失 stage04 JSONL 的链接，保持原目标。
- `git diff` 不改 `backend/` 与 `frontend/`。

## 实际验证

本任务仍是 In Progress。下列结果不构成接受。

- 官方原文与 `docs/blueprint.md` 逐字节相同。SHA-256 为 `f0273030ec15fd0d8d87a767a37228b371d54a3f54b556f5e32c850f2454b817`。文件含八个 `###` 小节。流程代码块保留 `base...head`、`上下文` 和 `规则` 行末空格。
- 机器学习定位句的原文是 `**规则引擎永远优先且独立，ML 属于可选、可独立关闭的辅助实验**。` 大模型条目的原文是 `仅用于对已有 Finding 和 Diff 切片进行辅助性的“变更意图推断”与“审查评语草拟”，不作为底层漏洞裁决器。`
- 没有 `docs/core-blueprint.md`，也没有 `T008.yaml`。
- 001–007 的前言与移动前一致，状态仍是 Accepted。008 的前言 `branch` 是 `docs/008-docs-structure-blueprint`。
- 从 `docs/README.md` 和根 README 能到达全部 `docs/**/*.md`。相对链接里，除 002 有意保留的五条旧卡片路径，以及 v1.0.0 阶段 04 结论里原本指向缺失 `stage04-structure-objects.jsonl` 的链接，其余都指向现存路径。
- `git diff` 不包含 `backend/` 或 `frontend/`。
- `git diff --check` 只报告 `docs/blueprint.md` 里上述三行行末空格。这三行属于官方原文，没有删掉。其余已暂存文档没有行末空白。
