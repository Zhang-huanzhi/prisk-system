---
task_id: "016"
target_version: "v1.1.0"
title: "六张新的草稿规则卡片"
status: "Accepted"
branch: "docs/016-six-new-draft-cards"
date: "2026-11-07"
---

# 016：六张新的草稿规则卡片

## 目标

在已合并的 `2fe37e141b237a3ad62edd18378708a4223d51ee` 之上，按所有者要求新增六张规则说明卡片，并在 JSON 登记册里写入对应条目。六条都是 `draft`。本任务不实现检测器，不接入运行时目录，不宣布 v1.1.0 完成。

这六条是 011 那 20 条候选之外的新增候选，不是那 20 条的重写。011 的结构筛选仍是局部 Diff/AST 8、有界框架上下文 10、延后 2。

工程负责人已接受本任务。状态为 Accepted。交付分支仍是 `docs/016-six-new-draft-cards`。评审记录是 [PR #16](https://github.com/Zhang-huanzhi/prisk-system/pull/16)。写下这条记录时该 PR 尚未合并。本提交只把任务状态改为 Accepted，并同步活动索引、v1.1 入口和分支规范。不改六张卡片，不改登记册，不改任何 `rules[].lifecycle`，不扩大 NetBox 继承上的 Hit，不建 ADR，不实现检测器，不合并，不打 tag，不删除分支，也不开始 017。接受不表示 v1.1.0 已经完成。信号、查询集和 `assert` 的未决设计仍是遗留风险。严重度和风险性质仍是临时判断。

## 编号核对

015 写明下一个未使用编号是 016，并且 016 不因 015 被接受而开始。开始时没有任务 016。分支、本文件和前言 `branch` 都是 `docs/016-six-new-draft-cards`。六个规则 ID 在起始提交的登记册里都不存在，因此沿用所有者给出的 ID，没有另取名字。

## 范围

- 六张卡片，生命周期字段都是 `draft`：
  - `code.mutable_default_argument`
  - `code.assert_in_production`
  - `auth.django_csrf_exempt_added`
  - `auth.drf_queryset_scope_tighten_bypassed`
  - `data.django_signal_receiver_leak`
  - `data.django_field_rename_without_db_column`
- 登记册追加这六条。身份、阵营、生命周期和分类标签与卡片一致。
- `code.global_mutable_state` 的卡片和登记册 `coverage_gap` 改为指向新的默认参数卡片。那条规则的 `lifecycle` 仍是 `implemented`，命中条件不改。
- 权限降级、ViewSet 动作和破坏性迁移各加一句边界，避免和查询集、字段改名重复表达。这三张卡片的生命周期不改。
- 活动任务索引、v1.1 入口、分支规范、规则知识库、规则索引、责任矩阵、文档入口、架构说明、就绪页和结构筛选页写明：这是新增的 6 条，20 条候选的计数不重写。

## 不做事项

- 不实现检测器，不修改 `backend/prisk/` 的规则语义，不把六条放进 `RULE_CATALOG`。
- 不新增权重字段，不改默认可得权重。概念上的默认权重是 0，只写在卡片和说明里。
- 不把任何 `draft` 改成 `registered`、`implemented` 或 `validated`。文档写完不是升级条件。
- 不改 011 的 8 / 10 / 2，不把六条并进那张表。
- 不改 `code.dead_code_after_exit`、`auth.drf_object_permission_bypass`、`auth.django_permission_module_changed` 的生命周期，也不给这三条写卡片。
- 不把 `NetBoxModelViewSet`、`NetBoxModel` 或 `restrict_queryset` 写进 Hit 闭集，不建 ADR。
- 不运行 `makemigrations`，不下载真实 PR，不报告 Precision、Recall 或 NetBox 试点。
- 不改 `docs/blueprint.md`，不改推进大纲正文，不改冻结的 v1.0.0。
- 不标记 v1.1.0 完成，不建立 `docs/versions/v1.1/` 或 `docs/versions/v1.1.0/`，不合并，不打 tag。
- 本提交只把任务状态改为 Accepted，并同步活动索引、v1.1 入口和分支规范。不改卡片、登记册或任何 `rules[].lifecycle`。不扩大 NetBox 继承上的 Hit，不建 ADR，不实现检测器，不合并，不打 tag，不删除分支，不开始 017。不宣布 v1.1.0 完成。信号、查询集和 `assert` 的未决设计仍是遗留风险。

## 技术方案

卡片按规则说明卡片模板写。状态只使用模板和 schema 里已有的「生命周期」字段。六条都填 `draft`。

严重度和风险性质是工程负责人的临时判断，卡片写明不是终局。后续算法阶段可以修订。

| 规则 ID | 阵营 | 严重度 | 风险性质 | 依赖层级 |
| --- | --- | --- | --- | --- |
| `code.mutable_default_argument` | `code_smell` | `Medium` | `pr_intrinsic` | `language` |
| `code.assert_in_production` | `code_smell` | `Medium` | `pr_intrinsic` | `language` |
| `auth.django_csrf_exempt_added` | `backend_contract` | `High` | `external_impact` | `framework` |
| `auth.drf_queryset_scope_tighten_bypassed` | `backend_contract` | `High` | `external_impact` | `framework` |
| `data.django_signal_receiver_leak` | `backend_contract` | `Medium` | `pr_intrinsic` | `framework` |
| `data.django_field_rename_without_db_column` | `breaking_impact` | `High` | `external_impact` | `database` |

一票抬升都是 `false`，条件都是 `null`。

信号规则的 ID 使用 `data` 前缀，阵营记在 `backend_contract`。判定的是 `connect` 上有没有框架关键字，不是迁移操作。这是临时归类，可以改阵营，不改 ID。

结构备注写在筛选页末尾，使用 `same_file_ast_kind_missing` 与 `bounded_framework_context` 两个只属于这六条的标签。前者不并入 011 的 `local_diff_ast`，因为当前节点还没有默认值种类和 `Assert` 节点。

## 留给所有者的设计边界

- 查询集规则的设计 Hit 只覆盖四个直接基类上、返回未过滤 `objects.all()` 的 `get_queryset`。`NetBoxModelViewSet` 与 `restrict_queryset` 记 Unanalyzed。DRF 文档没有把「必须调用 `super()`」写成合同，所以单独去掉 `super()` 不记 Hit。若要把项目继承合同收进 Hit，需要写明的名单；当前 ADR 索引没有已发布条目。本任务不建 ADR。
- 字段改名同样只在直接基类最后一段为 `Model` 时设计 Hit。`NetBoxModel` 记 Unanalyzed。一对以上的字段名变化不猜测配对。本规则不证明自动检测器已经生成 `RemoveField` 加 `AddField`。
- 信号规则按所有者给出的「没有 `dispatch_uid`」记设计 Hit，但 Django 当前文档写明模块级函数按对象身份只登记一次。是否把 Hit 收窄到绑定方法，留待所有者决定。严重度因此暂为 `Medium`。
- `assert` 使用已有的 `default_source_and_test_directories`，不使用 stage03 里把 `netbox/` 记为 business 的分类，也不单列 auth 目录。严重度暂为 `Medium`，因为语句看不出它是不是权限检查。
- CSRF 豁免不排除测试路径。严重度暂为 `High`，不是一票抬升。

## 兼容性

- 运行时目录仍是 14 条。`evaluate_rules` 的命中条件不变。
- 登记册仍不是运行时配置。已保存 demo 的 Finding 和分数不重算。
- 除 `code.global_mutable_state` 的覆盖说明，以及三张卡片上的边界句子之外，既有规则的 `lifecycle` 不改。`registered`、`validated`、`deprecated` 仍是空集。已实现名单仍是原先 9 条。

## 验收

- 前言 `status` 为 Accepted，`branch` 与 Git 分支同为 `docs/016-six-new-draft-cards`。
- 六张卡片的生命周期与登记册 `lifecycle` 都是 `draft`，且值属于 schema 枚举。本提交不改这些字段。
- 六条不在 `RULE_CATALOG`。运行时目录仍是 14 条。
- 011 的 20 条计数仍是 8 / 10 / 2。就绪页仍保留「不是登记册里全部 23 条」这句 014 的范围说明。
- `docs/blueprint.md` 未被修改。v1.1.0 没有被写成已经完成。NetBox 继承上的 Hit 没有扩大，也没有新的 ADR。

## 实际验证

仓库没有 GitHub Actions。系统 Python 是 3.12.3，项目声明是 `requires-python >=3.12`。没有改前端，所以没有跑 lint、typecheck 或 build。没有改 `docs/blueprint.md` 和推进大纲。没有改 `backend/prisk/` 的规则语义。

在 `backend/` 下：

- `python3 -m unittest tests.services.test_rule_registry`：13 项全部通过，退出码 0。015 记录的是 12 项。多出的 1 项核对六张新卡片为 `draft`、不在运行时目录、20 条计数不重计，以及 `code.global_mutable_state` 仍是 `implemented`。
- `python3 -m unittest discover -s tests -t .`：118 项全部通过，退出码 0。015 记录的是 117 项。多出的 1 项就是上面这条。登记册现为 29 条：`code_smell` 10、`backend_contract` 13、`breaking_impact` 6。`draft` 20，`implemented` 9，`registered` 为空。

本次新增和改写的活动 Markdown 相对链接已检查，没有断链。`git diff --check` 在提交前通过。这些测试不是先导试点，也不是 Precision 或 Recall。

本状态提交只把任务改为 Accepted，并同步活动索引、v1.1 入口和分支规范里的任务状态。没有改卡片、登记册或任何 `rules[].lifecycle`。没有扩大 NetBox 继承上的 Hit，没有建 ADR，没有因此重跑后端 unittest，也没有跑前端 lint、typecheck 或 build。`git diff --check` 在这次提交前通过。

## 遗留风险

接受不关闭下面这些设计说明。本提交不改对应卡片，不扩大 Hit，也不建 ADR。

- 六条严重度和风险性质都是临时判断，不是终局，也不是实证。
- 查询集：`NetBoxModelViewSet` 与 `restrict_queryset` 仍是 Unanalyzed。单独去掉 `super().get_queryset()` 仍不是 Hit。项目继承名单仍没有，当前没有 ADR。
- 字段改名：`NetBoxModel` 仍是 Unanalyzed。接受不把项目模型基类写进 Hit。
- 信号：是否把缺少 `dispatch_uid` 的 Hit 收窄到绑定方法仍未决。Django 文档写明模块级函数按对象身份只登记一次。阵营仍是临时的 `backend_contract`。
- `assert`：严重度仍是 `Medium`。路径仍用 `default_source_and_test_directories`，不单列 auth 目录，也不改用 stage03 的 business 分类。语句本身看不出它是不是权限检查。
- 默认参数种类和 `Assert` 节点都还不是结构化字段。在那之前不能实现检测器而不把缺字段记成 Hit。
- v1.1.0 没有冻结目录。本任务不代为宣布大纲已经完成。接受不开始 017，也不开始检测器。
