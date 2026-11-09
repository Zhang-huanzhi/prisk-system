---
task_id: "018"
target_version: "v1.1.0"
title: "v1.1 卡片门槛收口"
status: "Accepted"
branch: "docs/018-v11-card-gate"
date: "2026-11-07"
---

# 018：v1.1 卡片门槛收口

## 目标

在已合并的 `b9d793863c164a323f83015d618bfa39c79a2de5`（017）之上，写一份决策页，让所有者过目卡片之后能够收口或延后 v1.1.0 的**卡片门槛**（设计范围）。所有者已选择：过目卡片 + 写决策文档；**不**实现检测器。

所有者已接受本任务。状态为 Accepted。交付分支仍是 `docs/018-v11-card-gate`。评审记录是 [PR #18](https://github.com/Zhang-huanzhi/prisk-system/pull/18)。写下这条记录时该 PR 尚未合并。本提交只把任务状态改为 Accepted，填入决策页四个所有者终裁，并同步活动索引、v1.1 入口、分支规范和文档入口。不改规则卡片，不改登记册，不改任何 `rules[].lifecycle`，不实现检测器，不合并，不打 tag，不删除分支，也不开始 019。接受不表示 v1.1.0 已经完成。

决策页是 [v1.1 卡片门槛决策](../rules/v1.1-card-gate-decision.md)。014 的 [v1.1 卡片就绪核对](../rules/v1.1-card-readiness.md) 仍是历史核对范围；决策页才是门槛收口位。

## 编号核对

017 写明下一个未使用编号是 018，并且 018 不因 017 被接受而开始。开始时没有任务 018。分支、本文件和前言 `branch` 都是 `docs/018-v11-card-gate`。

## 范围

- 新建任务记录（本文件）；本提交将状态改为 Accepted。
- 新建决策页：当前计数（登记册 29；`implemented` 9 / `draft` 20；catalog 卡片 26；无卡片 3；运行时目录仍 14）、所有者过目清单、四个显式决策槽。所有者终裁已写入：
  - a) `yes with carve-outs`
  - b) 否：不宣布 v1.1.0，不建版本目录，不打 tag，直到另开发布任务
  - c) 残余检测器跟进进入 v1.2
  - d) 20 条 `draft` 在检测器与构造测试前按设计保持 `draft`
- 轻量同步活动索引、v1.1 入口、分支规范「下一个未使用编号」、文档入口。
- 可选：在就绪页加一句指向决策页的指针；就绪页正文仍描述 014 范围。

## 不做事项

- 不修改 `backend/prisk/`，不实现检测器，不把草稿放进 `RULE_CATALOG`，不改权重。
- 不改任何 `rules[].lifecycle`，不把 `draft` 写成 `registered` / `implemented` / `validated`。
- 不扩大 [已知框架基类映射](../rules/known-framework-bases.md) 之外的 NetBox Hit。
- 不建 ADR（本轮未发现阻塞决策页的矛盾）。
- 不建立 `docs/versions/v1.1/` 或 `docs/versions/v1.1.0/`，不宣布 v1.1.0 完成。
- 本提交只把任务改为 Accepted 并同步索引与决策终裁。不合并，不打 tag，不删除分支，不开始 019。
- 不改写 001–017 任务正文里「当时的句子」，只改索引与规范中需要反映 018 Accepted 的事实行。

## 技术方案

设计 / 实现 / 验证分开写：

1. **设计**：门槛是否够，由所有者在决策槽终裁；四个槽已按所有者决定填入。
2. **实现（本 PR）**：仅 Markdown。计数从起始 ref 的 `rule-registry.json` 与 `docs/rules/catalog/**/*.md`（排除 README）实读，不凭记忆。
3. **验证**：docs-only，见「实际验证」。不跑后端 unittest（未改 backend），不跑前端。

蓝图目标仍是目标规格，不等于本 PR 已实现检测器或版本冻结。

## 验收

- 前言 `status` 为 Accepted，`branch` 与 Git 分支同为 `docs/018-v11-card-gate`。
- 决策页四个所有者终裁已填。
- 活动索引 / v1.1 入口 / 分支规范 / 文档入口反映 018 Accepted，并写明 PR #18 写下时尚未合并、不宣布 v1.1.0、不开始 019。
- 无 `backend/prisk/` 变更，无 lifecycle 变更，无 `docs/versions/v1.1*`。

## 实际验证

仓库没有 GitHub Actions。本 PR 只改文档。

- `git diff --check`：提交前通过。
- 未改 `backend/`：不跑 `unittest`。
- 未改 `frontend/`：不跑 lint / typecheck / build。
- 计数复核（起始 ref）：登记册 29（`implemented` 9，`draft` 20）；catalog 规则卡片 26；无卡片 3；`gatekeeper` `true` 2 条；运行时目录文档仍写 14。
- 控制字符扫描：本提交涉及文件无意外 C0 控制符。

这些检查不是先导试点，也不是 Precision 或 Recall。

本状态提交只把任务改为 Accepted，填入所有者终裁，并同步活动索引、v1.1 入口、分支规范和文档入口。没有改卡片、登记册或任何 `rules[].lifecycle`。没有实现检测器，没有因此重跑后端 unittest，也没有跑前端 lint、typecheck 或 build。`git diff --check` 在这次提交前通过。PR #18 仍打开，不合并，不删除分支。

## 遗留（仍开放）

- 检测器后续：`bare_exception` 的 Exception 拆分、`Path.open`、映射表运行时、`Meta.fields`、`default=`、敏感配置方向、gatekeeper 评分读取，以及 016 六张草稿与 `workflow.large_change_scope` 阈值——默认归 v1.2，本任务不关闭。
- 接受不宣布 v1.1.0 完成，也不开始 019。
