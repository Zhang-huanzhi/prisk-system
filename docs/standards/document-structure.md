# 文档结构

| 适用版本 | v1.x |
| --- | --- |
| 状态 | Active |
| 任务 | [008](../tasks/008-docs-structure-blueprint.md) |
| 分支 | `docs/008-docs-structure-blueprint` |

## 目录

| 路径 | 职责 |
| --- | --- |
| `docs/README.md` | 文档总入口。开发者和 AI 从这里进入 [核心蓝图](../blueprint.md) |
| `docs/blueprint.md` | 目标系统规格原文 |
| `docs/architecture.md` | 当前实现 |
| `docs/operations.md` | 当前本地运维 |
| `docs/standards/` | 文档、任务、分支和开发流程规范 |
| `docs/standards/development-roadmap.md` | 开发推进规划。This is a planning document and is not evidence of completion or implemented functionality. |
| `docs/tasks/` | 未完成，或已接受但尚未随版本归档的任务 |
| `docs/evaluation/pilot-v1.1/` | 012 的先导试点。仅试点，不是 v1.4 正式评估集 |
| `docs/versions/v1.0.0/` | 已冻结的 v1.0.0 阶段档案 |
| `docs/versions/README.md` | 各版本的范围、冻结状态和任务索引 |
| `docs/rules/` | 研究规则卡片和索引 |
| `docs/schemas/` | 研究元数据 schema |
| `docs/assets/` | 研究资产；当前状态写在该目录 README |
| `docs/adr/` | 架构决策。当前没有已发布条目 |

`docs/blueprint.md` 定义目标系统。当前实现以 `docs/architecture.md` 和已接受任务的记录为准。蓝图中的机器学习、权重调优、动态配置和 NetBox 实证验证不是已经落地的能力。009 起，新鲜分析为运行时目录中的每条已启用规则记录终态。013 起该目录为 14 条，其中包括 `data.django_raw_sql_execution`。014 没有扩大这份目录。015 也不扩大这份目录，不宣布 v1.1.0 完成，也不开始检测器。016 只增加六张草稿卡片和登记册条目，不扩大这份目录，不宣布 v1.1.0 完成。017 只改规则卡片和登记册文字，不扩大这份目录，也不宣布 v1.1.0 完成。不能成立的上下文不记 NotFound，已保存历史也不补写。该规则默认权重是 0，命中不是注入已经发生。

## 版本目录

只为已经冻结归档的版本建立 `docs/versions/<version>/`。仓库里现有的版本目录只有 `v1.0.0`。v1.1.0 的入口状态仍是进行中，因此不建立 `docs/versions/v1.1/` 或 `docs/versions/v1.1.0/`。

已接受的 001–007 还没有随版本发布归档，所以留在 `docs/tasks/`。v1.0.0 的阶段 01–08 是阶段档案，不是 T00X 任务。阶段 08 不占用任务编号 008。

## 冻结文本

`docs/versions/v1.0.0/` 里的历史结论保持原句。正文里的 `docs/iterations/` 是冻结当时的路径。当前任务在 [活动任务](../tasks/README.md)。
