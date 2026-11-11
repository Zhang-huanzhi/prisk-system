# Prisk-System 文档

本目录保存代码仓库的工程规范、设计蓝图、任务演进和阶段冻结档案。个人开题材料、完整实验克隆、API 缓存、本机秘密和临时文件不进入本仓库。

## 必读

开发者和 AI 在改动本系统前请先阅读 [核心蓝图](blueprint.md)。该文件是目标系统规格的原语定义。

- **目标与实现边界**：蓝图中的机器学习、权重调优、动态配置或 NetBox 生产实证属于远期目标，非当前已落地功能。当前具体实现以 [架构说明](architecture.md) 为准。
- **三态执行与评分**：新鲜分析为运行时 29 条规则记录显式终态（`Hit / NotFound / Unanalyzed`）。命中 Finding 代表检测到特征，是人工复核优先级线索，不等于断定代码缺陷。
- **阶段状态**：
  - `v1.0.0`：阶段基线档案保存在 [versions/v1.0.0/](versions/v1.0.0/README.md)。
  - `v1.1.0`：规则知识库里程碑（含 26 张卡片、结构可行性筛选、真实 PR 先导摸底协议、所有者门槛收口决策）已归档于 [versions/v1.1.0/](versions/v1.1.0/README.md)。
  - `v1.2.0`：核心规则实现与三态引擎能力闭环（含残余合同对齐、24 张卡片三态检测器落地、Gatekeeper 机制与标准任务模板）已归档于 [versions/v1.2.0/](versions/v1.2.0/README.md)。
  - `v1.3.0`：动态交互工作台、快照局部重跑与可复现审查报告（含配置解耦、5 套场景预设、三级快照缓存、`config.snapshot.v1` 固化与 GitHub Primer 审查视图重构）已归档于 [versions/v1.3.0/](versions/v1.3.0/README.md)。
  - 当前活动工作区见 [活动任务](tasks/README.md)。

## 文档分层

| 路径 | 职责 | 生命周期 |
| --- | --- | --- |
| `blueprint.md` | 目标系统规格原文 | 目标；不是当前实现 |
| `standards/development-roadmap.md` | 开发推进规划（非完成证据，非已实现功能） | 规划指导 |
| `standards/` | 文档结构、任务与分支、开发流程 | 持续更新 |
| `tasks/` | 未完成，或已接受但尚未随版本归档的任务 | 活动 |
| `evaluation/pilot-v1.1/` | 真实 PR 先导试点记录（仅摸底试点，永久排除出 v1.4 正式集） | 冻结研究资产 |
| `versions/` | 各阶段里程碑冻结档案（v1.0.0, v1.1.0, v1.2.0, v1.3.0） | Frozen |
| `rules/` | 研究规则卡片、索引和卡片框架 | 研究产物；非运行时代码登记册 |
| `schemas/` | 研究元数据 schema | 文档契约 |
| `assets/` | 研究资产（当前无额外已跟踪资产） | 按需更新 |
| `architecture.md` | 当前工程实现说明 | 随实现更新 |
| `operations.md` | 本地运维与检查指南 | 持续更新 |
| `adr/` | 长期架构决策记录 | 按需新增 |

## 核心入口

- [核心蓝图](blueprint.md)
- [推进大纲](standards/development-roadmap.md)
- [架构说明](architecture.md)
- [运维手册](operations.md)
- [开发流程](standards/development-process.md)
- [任务与分支规范](standards/branching-and-tasks.md)
- [活动任务](tasks/README.md)
- [版本索引](versions/README.md)
- [研究规则索引](rules/index.md)
- [规则说明卡片模板](rules/rule-card-template.md)
- [已知框架基类映射](rules/known-framework-bases.md)
- [v1.1 卡片门槛决策](rules/v1.1-card-gate-decision.md)
- [根 README](../README.md)
