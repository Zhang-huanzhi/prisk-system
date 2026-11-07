---
task_id: "012"
target_version: "v1.1.0"
title: "真实 PR 先导试点协议"
status: "Accepted"
branch: "docs/012-pilot-protocol"
date: "2026-11-07"
---

# 012：真实 PR 先导试点协议

## 目标

冻结一份只用于先导摸底的协议，并在公开的已合并 NetBox PR 上抽 10 到 20 条，记录现有研究规则是否出现、草稿表面能不能对上，以及一轮标注大概要多久。样本与未来 v1.4 正式评估集物理隔离。产出是实现优先级和样本量级。

用户已接受本任务。状态为 Accepted。分支、本文件和前言 `branch` 仍是 `docs/012-pilot-protocol`。评审记录是 [PR #12](https://github.com/Zhang-huanzhi/prisk-system/pull/12)。写下这条记录时该 PR 尚未合并。本提交不合并、不打 tag、不删除分支，也不启动 013。接受不表示实证结果。

推进大纲里的这条要求见 [开发推进大纲](../standards/development-roadmap.md)。This is a planning document and is not evidence of completion or implemented functionality.

## 依赖

- [011](011-rule-card-feasibility.md) 已接受。起始提交是 `7afba225b2e5a3af60a3d25fd77e0bf2fee59e25`。本任务不改 011 的卡片和筛选结论。
- [010](010-development-roadmap.md) 已接受。本任务不改大纲正文。
- 运行时仍是 13 条。研究候选仍是 20 条。011 的可行性计数仍是局部 Diff/AST 8、有界框架上下文 10、延后 2。

## 范围

- 新增本任务，并更新活动任务索引、v1.1 入口和任务与分支里的当前编号说明。
- 在 [docs/evaluation/pilot-v1.1/](../evaluation/pilot-v1.1/README.md) 写下协议、16 条 PR 的清单和人读表、筛查记录，以及给 013 的建议。
- 用现有 `analyze_branches` 在临时变更文件仓库上记录八条研究规则的终态。不改规则语义，不改权重。
- 对照草稿卡片做人工表面判断。Hit 不写成缺陷。

## 不做事项

- 不实现新检测器，不改 `backend/prisk/`、前端、测试、锁文件或权重。
- 不把 JSON 登记册接到运行时，不把 20 条候选说成 13 条运行时规则。
- 不计算 Precision、Recall，不声称经验有效性或 NetBox 生产效果。
- 不把试点 PR 写入 `docs/versions/`，不改写冻结调研结论，也不把冻结调研的 120 个编号收进本试点。
- 不改 `docs/blueprint.md`，不改 [开发推进大纲](../standards/development-roadmap.md) 的正文。
- 不启动 013，不合并，不打 tag，不删除分支。
- 不改 001–011 的状态、结论和前言 `branch`。

## 验收

- 本文件前言 `status` 为 Accepted，`branch` 与 Git 分支同为 `docs/012-pilot-protocol`。
- 协议写明抽样框、纳入排除、分层、身份字段、四种判断、耗时记法，以及试点编号永久排除出 v1.4。
- 清单中的 PR 为 10 到 20 条，每条都能在 GitHub 上对上编号和 URL，且不发明 PR。
- 每条有研究规则终态、可标注性、估计分钟、零命中和饱和旗标。草稿判断与运行时 Hit 分开。
- 试点目录标明仅试点。大补丁不入库。
- 新增和改写的活动 Markdown 相对链接能解析。`git diff --check` 通过。

## 实际验证

本变更只改文档和 `.gitignore`。没有运行后端 unittest，也没有运行前端 lint、typecheck 或 build。没有新增检测器。临时筛查脚本留在本机 `/tmp`，不入库。

- GitHub REST API 在 2026-11-07 取回 16 条已合并 PR 的编号、标题、URL、`merged_at` 和 merge commit。16 个编号与冻结调研 JSONL 的交集为空。
- 临时仓库上的文件数和增删行数与 GitHub PR 计数一致。运行入口是现有的 `analyze_branches`。权重未改，筛查不报告评分。
- `zero_hit` 为 9，`saturated_hit` 为 0。估计分钟合计 135。这些数字不是 Precision 或 Recall。
- 清单可解析，条数为 16。新增和改写的活动 Markdown 相对链接已检查。`git diff --check` 在提交前运行。

## 遗留风险 / Residual risks

下面这些限制写在任务正文里。它们不是 Precision、Recall，也不是经验有效性。任务状态是 Accepted，这些限制仍然成立。

1. 16 条是目的分层样本，不是随机样本。命中次数不能当成 NetBox 里的发生率。
2. 筛查比较的是合并提交和它的第一父提交，输入是临时检出的变更文件。这不是完整 NetBox 克隆，也不是相对 merge-base 的三点 diff。22473、19846、21941 落在 `feature`，不是 `main`。
3. 研究规则的 Hit 大多是 false-looking Hit：`code.global_mutable_state` 打在框架或测试要求的列表上。`zero_hit` 为 9，只表示八条研究规则里没有 Hit。它不表示这八条都已经 NotFound。23509 上八条都是 Unanalyzed。
4. 估计分钟是一个人一轮的估计，合计约 135。这一轮没有把五条历史结构规则的每条证据都标完。那些规则在测试文件上很吵。
5. 没有运行后端 unittest，也没有运行前端 lint、typecheck 或 build。本变更只有文档和 `.gitignore`。若把本次记录当成 CI 式证明，这是尚未补上的验证缺口。
6. [t013-priority.md](../evaluation/pilot-v1.1/t013-priority.md) 只是建议。它不授权开始 013，也不授权改卡片或权重。
