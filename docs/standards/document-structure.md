# 文档结构

| 适用版本 | v1.x |
| --- | --- |
| 状态 | Active |
| 任务 | [030](../tasks/030-v13-milestone-closure.md) |
| 分支 | `docs/030-v13-milestone-closure` |

## 目录分工

| 路径 | 职责 |
| --- | --- |
| `docs/README.md` | 文档总入口与全景索引 |
| `docs/blueprint.md` | 目标系统规格原文（基准规格） |
| `docs/architecture.md` | 当前工程实现与链路说明 |
| `docs/operations.md` | 当前本地运维与测试指引 |
| `docs/standards/` | 文档、任务、分支、开发流程及推进大纲 |
| `docs/tasks/` | 活动中的任务与下一阶段入口 |
| `docs/evaluation/pilot-v1.1/` | 真实 PR 先导试点协议与 16 条样本摸底（永久排除出 v1.4 正式集） |
| `docs/evaluation/formal-v1.4/` | `v1.4.0` 正式实证评估协议、人工标注指南与 136 条永久排除清单 |
| `docs/versions/` | 已冻结归档的阶段版本（`v1.0.0/`, `v1.1.0/`, `v1.2.0/`, `v1.3.0/`） |
| `docs/rules/` | 研究规则卡片、规则索引与责任矩阵 |
| `docs/schemas/` | 研究元数据 JSON Schema |
| `docs/assets/` | 研究资产目录 |
| `docs/adr/` | 架构决策记录 |

## 版本目录规范

- 只为已经完成并冻结归档的阶段里程碑建立 `docs/versions/<version>/`。
- 仓库现有归档目录：
  - `docs/versions/v1.0.0/`：阶段 01–08 的调研与工程基线产物；
  - `docs/versions/v1.1.0/`：规则知识库全集、结构可行性筛选、真实 PR 先导协议及 Task 001–018 归档任务；
  - `docs/versions/v1.2.0/`：核心规则实现、三态引擎闭环、任务模板规范及 Task 019–024 归档任务；
  - `docs/versions/v1.3.0/`：动态交互工作台、快照局部重跑、可复现审查报告固化、GitHub Primer 审查视图重构及 Task 025–029 归档任务。
- 对应阶段收工归档后，已完成的任务记录迁入对应的 `docs/versions/<version>/tasks/`，活动工作区 `docs/tasks/` 仅保留当前活动任务与下一阶段入口。

## 冻结文本原则

- 已归档目录中的历史阶段记录保持原貌，不因后续演进而频繁改写历史结论。
- 当前系统功能以 `docs/architecture.md` 与主干代码为准。
