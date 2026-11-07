# 活动任务

这里只放尚未随版本归档的任务：未完成的任务，以及已经接受、但目标版本还没有冻结进 `docs/versions/` 的任务。

v1.1.0 仍未归档，所以 001–012 留在本目录。013 的目标版本是 v1.2.0，任务仍是 In Progress，因此也留在本目录。不建立 `docs/versions/v1.1/`、`docs/versions/v1.1.0/` 或 `docs/versions/v1.2/`。v1.0.0 阶段 08 不是任务 008，也没有冻结的阶段 09 占用任务 009。010 开始前没有任务 010。011 开始前没有任务 011。012 开始前没有任务 012。013 开始前没有任务 013。

001–007 的前言都有 `branch`。下表引用原值，不把它们改写成现行分支形式。008 为 Accepted，其前言 `branch` 仍是 `docs/008-docs-structure-blueprint`。009 为 Accepted，其前言 `branch` 仍是 `feat/009-explicit-rule-outcomes`。010 为 Accepted，其前言 `branch` 仍是 `docs/010-development-roadmap`。011 为 Accepted，其前言 `branch` 仍是 `docs/011-rule-card-feasibility`。012 为 Accepted，其前言 `branch` 仍是 `docs/012-pilot-protocol`。013 为 In Progress，其前言 `branch` 是 `feat/013-django-raw-sql`。接受不把 008、009、010、011 或 012 移入 `docs/versions/`。013 在被接受之前也不移入。不建立 v1.2 冻结目录。规划文档是 [开发推进大纲](../standards/development-roadmap.md)。This is a planning document and is not evidence of completion or implemented functionality.

| 任务 | 状态 | 前言中的 `branch` | 记录 |
| --- | --- | --- | --- |
| 001 | Accepted | `main` | [规则分类体系重构与规则说明卡片规范](001-rule-taxonomy-and-card-template.md) |
| 002 | Accepted | `v1.1.0-002-rule-knowledge-base` | [建立规则知识库与首批规则卡片](002-rule-knowledge-base.md) |
| 003 | Accepted | `docs/rule-id-naming` | [规则 ID 命名迁移与四拆五解耦](003-rule-id-naming-and-five-rules.md) |
| 004 | Accepted | `feat/004-ast-detectors` | [AST 代码异味检测器](004-ast-code-smell-detectors.md) |
| 005 | Accepted | `feat/005-second-batch-code-smells` | [第二批代码异味与 Django 契约卡片](005-second-batch-code-smells.md) |
| 006 | Accepted | `feat/006-remaining-code-smells` | [剩余语言级代码异味](006-remaining-code-smells.md) |
| 007 | Accepted | `feat/007-test-collaboration` | [测试协同复核提示](007-test-collaboration.md) |
| 008 | Accepted | `docs/008-docs-structure-blueprint` | [文档信息架构与核心蓝图](008-docs-structure-blueprint.md) |
| 009 | Accepted | `feat/009-explicit-rule-outcomes` | [显式规则终态](009-explicit-rule-outcomes.md) |
| 010 | Accepted | `docs/010-development-roadmap` | [Add the Prisk-System development roadmap](010-development-roadmap.md) |
| 011 | Accepted | `docs/011-rule-card-feasibility` | [规则卡片与结构可行性](011-rule-card-feasibility.md) |
| 012 | Accepted | `docs/012-pilot-protocol` | [真实 PR 先导试点协议](012-pilot-protocol.md) |
| 013 | In Progress | `feat/013-django-raw-sql` | [Django 原生 SQL 执行](013-django-raw-sql.md) |

[v1.1 入口原文](v1.1-entry.md) 随文件迁出后保留。其中“写下这次索引更新时，该 PR 尚未合并”是当时的句子，008 不改写。

任务与分支的现行规则见 [任务与分支](../standards/branching-and-tasks.md)。目标系统规格见 [核心蓝图](../blueprint.md)。
