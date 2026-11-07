---
task_id: "018"
target_version: "v1.1.0"
title: "v1.1 卡片门槛收口"
status: "In Progress"
branch: "docs/018-v11-card-gate"
date: "2026-11-07"
---

# 018：v1.1 卡片门槛收口

## 目标

在已合并的 `b9d793863c164a323f83015d618bfa39c79a2de5`（017）之上，写一份决策页，让所有者过目卡片之后能够收口或延后 v1.1.0 的**卡片门槛**（设计范围）。所有者已选择：过目卡片 + 写决策文档；**不**实现检测器。

本任务状态为 **In Progress**。交付分支是 `docs/018-v11-card-gate`。本提交不把任务写成 Accepted，不合并，不打 tag，不删除分支，不开始 019，不宣布 v1.1.0 完成，不改任何 `rules[].lifecycle`。

决策页是 [v1.1 卡片门槛决策](../rules/v1.1-card-gate-decision.md)。014 的 [v1.1 卡片就绪核对](../rules/v1.1-card-readiness.md) 仍是历史核对范围；本页才是门槛收口位。

## 编号核对

017 写明下一个未使用编号是 018，并且 018 不因 017 被接受而开始。开始时没有任务 018。分支、本文件和前言 `branch` 都是 `docs/018-v11-card-gate`。

## 范围

- 新建任务记录（本文件），状态 `In Progress`。
- 新建决策页：当前计数（登记册 29；`implemented` 9 / `draft` 20；catalog 卡片 26；无卡片 3；运行时目录仍 14）、所有者过目清单、四个显式决策槽（提案 + 所有者「待过目」）、诚实声明（本页不改 lifecycle；Accepted ≠ 版本冻结）。
- 轻量同步活动索引、v1.1 入口、分支规范「下一个未使用编号」、文档入口中关于 017 已合并 / 018 In Progress 的过时句子。
- 可选：在就绪页加一句指向决策页的指针；就绪页正文仍描述 014 范围。

## 不做事项

- 不修改 `backend/prisk/`，不实现检测器，不把草稿放进 `RULE_CATALOG`，不改权重。
- 不改任何 `rules[].lifecycle`，不把 `draft` 写成 `registered` / `implemented` / `validated`。
- 不扩大 [已知框架基类映射](../rules/known-framework-bases.md) 之外的 NetBox Hit。
- 不建 ADR（除非发现阻塞决策页的矛盾——本轮未发现，故不建）。
- 不建立 `docs/versions/v1.1/` 或 `docs/versions/v1.1.0/`，不宣布 v1.1.0 完成。
- 不把任务状态写成 Accepted，不合并，不打 tag，不删除分支，不开始 019。
- 不改写 001–017 任务正文里「当时的句子」，只改索引与规范中需要反映 018 的事实行。

## 技术方案

设计 / 实现 / 验证分开写：

1. **设计**：门槛是否够，由所有者过目后在决策槽终裁；本任务只提供提案与清单，不代填所有者决定。
2. **实现（本 PR）**：仅 Markdown。计数从起始 ref 的 `rule-registry.json` 与 `docs/rules/catalog/**/*.md`（排除 README）实读，不凭记忆。
3. **验证**：docs-only，见「实际验证」。不跑后端 unittest（未改 backend），不跑前端。

蓝图目标仍是目标规格，不等于本 PR 已实现检测器或版本冻结。

## 验收

- 前言 `status` 为 `In Progress`，`branch` 与 Git 分支同为 `docs/018-v11-card-gate`。
- 存在决策页，含计数、过目清单、四个决策槽（提案 + 待过目）、诚实声明。
- 活动索引 / v1.1 入口 / 分支规范 / 文档入口反映 018 In Progress，并修正「PR #17 尚未合并」这类相对 main 已过时的索引表述。
- 无 `backend/prisk/` 变更，无 lifecycle 变更，无 `docs/versions/v1.1*`。

## 实际验证

仓库没有 GitHub Actions。本 PR 只改文档。

- `git diff --check`：提交前通过。
- 未改 `backend/`：不跑 `unittest`。
- 未改 `frontend/`：不跑 lint / typecheck / build。
- 计数复核（起始 ref）：登记册 29（implemented 9，draft 20）；catalog 规则卡片 26；无卡片 3；gatekeeper `true` 2 条；运行时目录文档仍写 14。

这些检查不是先导试点，也不是 Precision 或 Recall。

## 遗留（仍开放）

- 所有者四个决策槽终裁仍为「待过目」。
- 检测器后续：`bare_exception` 的 Exception 拆分、`Path.open`、映射表运行时、`Meta.fields`、`default=`、敏感配置方向、gatekeeper 评分读取，以及 016 六张草稿与 large_change_scope 阈值——默认归 v1.2，本任务不关闭。
- 本任务保持 In Progress，直到所有者接受；接受也不等于 v1.1.0 冻结。
