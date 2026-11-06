---
task_id: "011"
target_version: "v1.1.0"
title: "规则卡片与结构可行性"
status: "Accepted"
branch: "docs/011-rule-card-feasibility"
date: "2026-11-06"
---

# 011：规则卡片与结构可行性

## 目标

把知识库里的 20 条候选都写成可复核的设计卡片，并给出一次结构可行性筛选。筛选只回答：以当前同一文件的 Diff/AST，这条候选能不能定义局部 Hit；若不能，缺的是一份有界框架上下文，还是跨文件关系或尚未指定的项目政策。

本任务不实现检测器，不改权重，不把任何卡片写成 `registered` 或 `validated`，也不产生 Hit / NotFound / Unanalyzed 的运行结果。009 的终态机器仍只覆盖当前 13 条运行时规则。

用户已接受本任务。状态为 Accepted。分支、本文件和前言 `branch` 仍是 `docs/011-rule-card-feasibility`。交付记录是 [PR #11](https://github.com/Zhang-huanzhi/prisk-system/pull/11)。本提交不合并、不打 tag、不删除分支，也不启动 012。接受不表示实证结果，也不把卡片生命周期改成 `validated`。

## 依赖

- [010](010-development-roadmap.md) 已合并：`257d32a153416b1e6f53ba996d9b92b2b16dd3f0`。本任务从该提交开始。
- [009](009-explicit-rule-outcomes.md) 已接受。本任务不修改 009，也不把设计预期写进 `rule_outcomes`。

## 范围

- 为八个当时没有卡片的候选按卡片模板写设计说明：`api.drf_public_parameter_removed`、`api.django_url_pattern_changed`、`api.drf_viewset_action_changed`、`auth.drf_permission_policy_downgrade`、`config.django_sensitive_settings_changed`、`data.django_destructive_migration`、`data.django_non_null_constraint_tightened`、`data.django_transaction_boundary_changed`。
- 补强 005 的三张草稿：`api.drf_public_parameter_added`、`auth.drf_permission_decorator_removed`、`data.django_raw_sql_execution`。适用面收在同一文件；路由、父类和设置模块不在场时写明 Unanalyzed。
- 新增 [结构可行性筛选](../rules/structural-feasibility.md)，覆盖全部 20 条候选，并保留三条登记册排除项及原因。
- 更新活动任务索引、v1.1 入口、规则索引和登记册中这八条原先的占位定义。身份字段与卡片一致，生命周期保持 `draft`。

起始提交上 `docs/rules/catalog/` 有 12 张卡片：七条代码异味、三张后端契约草稿、两张变更冲击。20 条候选里没有卡片的是上面八个 ID。本任务之后，20 条候选各有一张卡片。

## 不做事项

- 不实现检测器，不修改 `backend/prisk/`、前端、测试、锁文件、已保存快照或权重。
- 不把 JSON 登记册改成运行时配置，也不把研究候选 20 条说成运行时 13 条。
- 不下载真实 PR 补丁，不做命中、标注难度、Precision 或 Recall 试点。
- 不启动 012，不合并，不打 tag，不删除分支。
- 本提交只把状态改为 Accepted。不改卡片、登记册或运行时代码。
- 不改 001–010 的状态、结论和前言 `branch`。
- 不改 `docs/blueprint.md` 和 `docs/standards/development-roadmap.md`。
- 不清理 002 里有意留下的旧卡片路径，不改冻结版本文档。
- 不给 `code.dead_code_after_exit`、`auth.drf_object_permission_bypass`、`auth.django_permission_module_changed` 写卡片，也不把这三条登记册里的占位依据改写成已经核实的引用。
- 不覆盖 `workflow.large_change_scope` 登记册里与卡片不一致的严重度和风险性质。卡片仍是设计依据；这处差异留在筛选页说明。
- 不把 `data.django_raw_sql_execution` 的登记册名称从「绕过 ORM 的原生 SQL」改成卡片标题。ID 与 `draft` 已经一致。

## 生命周期

`draft` 表示定义或验证方案仍未接到检测器。`registered` 表示卡片已登记且检测器未接入。这十一张新写或补强的卡片都还有未接入的切片读取、闭集或包含关系，也没有构造测试。因此保持 `draft`，不写成 `registered`。登记册里 `registered` 集合仍为空。

## 验收

- 20 条候选各有一张卡片。八张新卡片写明适用性、检测边界、构造正例/反例/边界、证据、Unanalyzed、验证计划和可打开的官方文档链接。
- 三张旧草稿仍是 `draft`，并写明同一文件之外的路由或框架信息不作为隐藏前提。
- 筛选页的三类计数与页末清单一致，且不是把二十条收成同一类。
- 新卡片的 ID、名称、阵营和 `draft` 与登记册一致。已实现规则的登记册条目未被改写。
- 活动文档里新增或改写的相对链接都能解析。本任务不把 002 的历史坏链算进本次通过范围。

## 实际验证

本变更只改文档和登记册 JSON。没有运行后端 unittest，也没有运行前端 lint、typecheck 或 build。登记册不是运行时配置。现有一致性测试仍期待 `registered` 为空、三条旧草稿为 `draft`、已实现名单不变。本任务没有改测试，也没有改写那份测试。

- 登记册按 `docs/schemas/rule-metadata.schema.json` 检查通过。仍是 23 条：`code_smell` 8、`backend_contract` 10、`breaking_impact` 5。`registered` 为空。八条 `implemented` 的 ID 与顺序未变。相对 `257d32a153416b1e6f53ba996d9b92b2b16dd3f0`，登记册只改了八条原先的占位候选。
- `docs/rules/catalog/` 下规则卡片 20 张，对应 20 条候选。筛选页清单为局部 Diff/AST 8、有界框架上下文 10、延后 2，另有 3 条排除。
- 本次新增和改写的活动 Markdown 里，相对链接都能解析。这些文件里新引用的 Django 与 DRF 文档锚点已对照页面 `id`。`git diff --check` 通过。
- 002 的历史坏链不在本次检查的通过范围里。三条排除项登记册里的占位依据句子仍保留。

本状态提交只把任务改为 Accepted，并同步活动索引。没有改卡片、登记册或运行时代码。没有运行后端 unittest，也没有运行前端 lint、typecheck 或 build。`git diff --check` 在提交前通过。
