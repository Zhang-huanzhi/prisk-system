---
task_id: "015"
target_version: "v1.1.0"
title: "大规模变更范围的严重度与风险性质"
status: "In Progress"
branch: "docs/015-large-change-scope-severity"
date: "2026-11-07"
---

# 015：大规模变更范围的严重度与风险性质

## 目标

在已合并的 014 之上，按工程负责人的临时裁决，把 `workflow.large_change_scope` 的规则卡片和 JSON 登记册对齐到严重度 `High`、风险性质 `pr_intrinsic`。

起始提交是 `9b40ce48af15c91de2dd730bcacf313f7622cccd`。卡片平时是设计依据。这次由所有者授权工程负责人现在选定严重度，两边一起改。后续算法阶段可以修订。这不是终局完成，也不表示 v1.1.0 已经完成。

状态保持 In Progress，留给工程负责人评审。本任务不写成 Accepted。

## 编号核对

014 已说明下一个未使用编号是 015，并且 015 不因 014 被接受而开始。开始时没有任务 015，也没有打开的竞争 PR。分支、本文件和前言 `branch` 都是 `docs/015-large-change-scope-severity`。

## 裁决

改前，以 `9b40ce48af15c91de2dd730bcacf313f7622cccd` 为准：

| 位置 | 字段 | 值 |
| --- | --- | --- |
| 卡片表格 | 严重度 | `Medium` |
| 卡片表格 | 风险性质 | `pr_intrinsic` |
| 卡片表格 | 生命周期 | `draft` |
| 登记册 `classification` | `severity` | `High` |
| 登记册 `classification` | `risk_nature` | `external_impact` |
| 登记册 `definition` | `impact_type` | `external_impact` |
| 登记册 | `lifecycle` | `draft` |

改后：

| 位置 | 字段 | 值 |
| --- | --- | --- |
| 卡片表格 | 严重度 | `High` |
| 卡片表格 | 风险性质 | `pr_intrinsic` |
| 卡片表格 | 生命周期 | `draft` |
| 登记册 `classification` | `severity` | `High` |
| 登记册 `classification` | `risk_nature` | `pr_intrinsic` |
| 登记册 `definition` | `impact_type` | `pr_intrinsic_risk` |
| 登记册 | `lifecycle` | `draft` |

理由：大规模变更的关注级别是 High。性质是该 PR 自身的变更规模冲击，不是对外部 API 的经验断言。严重度取登记册原有的 `High`，写回卡片。风险性质取卡片原有的 `pr_intrinsic`，写回登记册。`definition.impact_type` 不是分类标签；若留在 `external_impact`，同一条登记册会同时写成两种性质。015 把它改为 `pr_intrinsic_risk`，与其余 `pr_intrinsic` 条目相同。`definition` 的其余句子不改。

一票抬升仍是 `false`，条件仍是 `null`。阈值、模块映射和触发特征不改。

## 范围

- 改这一条规则的卡片严重度，以及登记册的 `classification.risk_nature` 和 `definition.impact_type`。
- `lifecycle` 保持 `draft`。
- 活动任务索引、v1.1 入口、分支规范里的下一编号、规则知识库、规则索引、责任矩阵、文档入口、就绪页和结构筛选页里把旧差异写成当前事实的句子，改为这次临时判断，并写明不是终局。

## 不做事项

- 不实现检测器，不修改 `backend/prisk/` 的规则语义，不开始 v1.2 批次。
- 不改其他规则的 `lifecycle` 或权重，不改这条规则的权重。登记册里这条没有权重字段。默认评分上限不改。
- 不把任何 `draft` 改成 `registered`、`implemented` 或 `validated`。
- 不指定 200 行、3 个模块或其他阈值，不补模块映射。
- 不标记 v1.1.0 完成，不建立 `docs/versions/v1.1/` 或 `docs/versions/v1.1.0/`，不合并，不打 tag。
- 不把本任务写成 Accepted。工程负责人评审前保持 In Progress。
- 不改 `docs/blueprint.md`，不改推进大纲正文，不改冻结的 v1.0.0。
- 不改 001–014 的任务结论。那些文件里「不覆盖这处差异」「014 不改」仍是当时的事实。

## 技术方案

卡片表格的严重度从 `Medium` 改为 `High`。风险性质单元格保持 `pr_intrinsic`。登记册只改 `workflow.large_change_scope` 的两个值：`classification.risk_nature` 和 `definition.impact_type`。`classification.severity` 本来就是 `High`，保持不动。

知识库说明要求分类标签与卡片同步。这次严重度先按临时裁决写入卡片，再让登记册的风险性质与卡片一致。`impact_type` 的改动只消除同一条记录里的外部影响标签，不改写制定理由、触发特征或验证义务。

## 兼容性

- 登记册仍不是运行时配置。运行时目录仍是 14 条。`evaluate_rules` 的命中条件不变。
- 这条规则仍没有检测器，仍不能产生 Finding。已保存 demo 的 Finding 和分数不重算。
- 其他规则的 `lifecycle` 和权重不改。`registered`、`validated`、`deprecated` 仍是空集。已实现名单仍是原先 9 条。

## 验收

- 前言 `status` 为 In Progress，`branch` 与 Git 分支同为 `docs/015-large-change-scope-severity`。
- 卡片与登记册的严重度都是 `High`，风险性质都是 `pr_intrinsic`，`lifecycle` 都是 `draft`。
- 登记册 `definition.impact_type` 是 `pr_intrinsic_risk`。
- 其他规则的 `lifecycle` 不变。运行时目录仍是 14 条。
- 就绪页、结构筛选页和规则知识库写明临时判断，以及后续算法阶段可以修订、不是终局。
- `docs/blueprint.md` 未被修改。v1.1.0 没有被写成已经完成。

## 实际验证

仓库没有 GitHub Actions。系统 Python 是 3.12.3，项目声明是 `requires-python >=3.12`。没有改前端，所以没有跑 lint、typecheck 或 build。没有改 `docs/blueprint.md` 和推进大纲。没有改 `backend/prisk/`。

在 `backend/` 下：

- `python3 -m unittest tests.services.test_rule_registry`：12 项全部通过，退出码 0。其中 `test_large_change_scope_classification_is_provisional_high_pr_intrinsic` 核对卡片表格与登记册的严重度、风险性质、`lifecycle` 和 `impact_type`，并核对就绪页、筛选页和知识库仍写明不是终局。同一文件仍核对卡片生命周期与登记册 `lifecycle` 一致，已实现名单不变，`registered` 为空。草稿仍是 14 条，已实现仍是 9 条。
- `python3 -m unittest discover -s tests -t .`：117 项全部通过，退出码 0。014 记录的是 116 项。多出的 1 项是上面这条分类核对。没有改 `backend/prisk/` 的规则语义。

没有改前端，所以没有跑 lint、typecheck 或 build。`git diff --check` 在提交前通过。本次新增和改写的活动 Markdown 相对链接已检查，没有断链。这些测试不是先导试点，也不是 Precision 或 Recall。

## 遗留风险

- 严重度和风险性质是临时判断。后续算法阶段可以修订。这不是终局，也不是实证结果。
- 阈值和模块映射仍未指定。行数和文件数仍然不能单独改写成 Hit。检测器没有开始。
- `definition.impact_type` 改为 `pr_intrinsic_risk` 只为和 `risk_nature` 一致。若评审只保留分类字段，可以单独收回这一处。
- 就绪页仍写明本表只核对生命周期，不声称全部分类元数据已经对齐。015 只处理这一条规则的上述字段。
- v1.1.0 没有冻结目录。本任务不代为宣布三条大纲已经完成。
- 本任务在工程负责人接受前保持 In Progress。
