# Prisk-System 文档

本目录保存代码仓库的工程文档，以及构成 v1.0.0 冻结证据的经筛选研究样本和阶段产物。个人开题材料、完整 NetBox/Saleor 实验克隆、API 缓存、本机秘密和临时文件不进入本仓库。

## 必读

开发者和 AI 在改动本系统前阅读 [核心蓝图](blueprint.md)。该文件是目标系统规格的原文。它不把机器学习、权重调优、动态配置或 NetBox 实证验证登记为当前实现。009 起，新鲜分析会为运行时目录中的每条已启用规则记录 Hit / NotFound / Unanalyzed。013 起该目录为 14 条，其中包括 `data.django_raw_sql_execution`。上下文不成立时不记 NotFound，已保存历史快照也不补写终态。命中不是注入已经发生。当前实现见 [架构说明](architecture.md)，活动任务见 [活动任务](tasks/README.md)。

## 文档分层

| 路径 | 职责 | 生命周期 |
| --- | --- | --- |
| `blueprint.md` | 目标系统规格原文 | 目标；不是当前实现 |
| `standards/development-roadmap.md` | 开发推进规划。This is a planning document and is not evidence of completion or implemented functionality. | 规划；不是完成证据，也不是已实现功能 |
| `standards/` | 文档结构、任务与分支、开发流程 | 持续更新 |
| `tasks/` | 未完成，或已接受但尚未随版本归档的任务 | 活动 |
| `evaluation/pilot-v1.1/` | 012 的先导试点。仅试点，不是正式实证 | 活动；排除出 v1.4 |
| `versions/v1.0.0/` | v1.0.0 阶段档案、冻结范围和任务索引 | Frozen |
| `rules/` | 研究规则卡片、索引和卡片框架 | 研究产物；不是代码登记册 |
| `schemas/` | 研究元数据 schema | 文档契约 |
| `assets/` | 研究资产；状态见该目录说明 | 当前无已跟踪资产 |
| `architecture.md` | 当前实现 | 随实现更新 |
| `operations.md` | 本地运行与检查 | 持续更新 |
| `adr/` | 长期架构决策 | 按需新增 |

生命周期规则：源码和测试进入 Git；versions 保存冻结阶段事实及必要的可复核产物；tasks 保存尚未随版本归档的任务。本机依赖、上游仓库克隆、API 响应缓存和临时文件不进入 Git。冻结目录不收录个人材料，样本中的贡献者身份字段应脱敏。

## 入口

- [核心蓝图](blueprint.md)
- [推进大纲](standards/development-roadmap.md)。This is a planning document and is not evidence of completion or implemented functionality.
- [架构说明](architecture.md)
- [运维手册](operations.md)
- [文档结构](standards/document-structure.md)
- [任务与分支](standards/branching-and-tasks.md)
- [开发流程](standards/development-process.md)
- [规范索引](standards/README.md)
- [活动任务](tasks/README.md)
- [v1.1 先导试点](evaluation/pilot-v1.1/README.md)。仅试点，不是 Precision、Recall 或 v1.4 正式评估集
- [版本索引](versions/README.md)
- [v1.0.0 基线](versions/v1.0.0/README.md)
- [研究规则索引](rules/index.md)
- [Schema](schemas/README.md)
- [研究资产](assets/README.md)
- [ADR 索引](adr/README.md)
- [根 README](../README.md)
