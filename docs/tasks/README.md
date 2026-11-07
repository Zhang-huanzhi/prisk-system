# 活动任务

这里只放尚未随版本归档的任务：未完成的任务，以及已经接受、但目标版本还没有冻结进 `docs/versions/` 的任务。

v1.1.0 仍未归档，所以 001–012 留在本目录。013 的目标版本是 v1.2.0，状态为 Accepted，因此也留在本目录。014 的目标版本是 v1.1.0，状态为 Accepted，因此也留在本目录。015 的目标版本是 v1.1.0，状态为 Accepted，因此也留在本目录。016 的目标版本是 v1.1.0，状态为 Accepted，因此也留在本目录。017 的目标版本是 v1.1.0，状态为 Accepted，因此也留在本目录。018 的目标版本是 v1.1.0，状态为 In Progress，因此也留在本目录。接受不表示 v1.1.0 已经完成。016 的接受也不表示 v1.1.0 已经完成。017 的接受同样不表示 v1.1.0 已经完成。018 的进行也不表示 v1.1.0 已经完成。不建立 `docs/versions/v1.1/`、`docs/versions/v1.1.0/` 或 `docs/versions/v1.2/`。v1.0.0 阶段 08 不是任务 008，也没有冻结的阶段 09 占用任务 009。010 开始前没有任务 010。011 开始前没有任务 011。012 开始前没有任务 012。013 开始前没有任务 013。014 开始前没有任务 014。015 开始前没有任务 015。016 开始前没有任务 016。017 开始前没有任务 017。018 开始前没有任务 018。014 不宣布 v1.1.0 完成。015 的接受也不宣布 v1.1.0 完成，不开始检测器。015 正文里「也不开始 016」是当时的句子。016 因所有者要求新增六张草稿卡片而开始，不因 015 被接受而开始。016 现为 Accepted。接受不把六条规则的 `lifecycle` 改离 `draft`，不扩大 NetBox 继承上的 Hit，不建 ADR，不开始检测器，也不开始 017。这句话里的「也不开始 017」是当时的句子。017 因所有者要求修正卡片语义并统一模板而开始，不因 016 被接受而开始。017 现为 Accepted。分支仍是 `docs/017-card-content-format`。评审记录是 [PR #17](https://github.com/Zhang-huanzhi/prisk-system/pull/17)。该 PR 已合并进 main（`b9d7938`）。017 正文与当时索引里「写下这次索引更新时，该 PR 尚未合并」「也不开始 018」是当时的句子，本段不改写那些历史措辞的含义：017 的接受本身并不开始 018。018 因工程负责人下达卡片门槛收口 brief 而开始，不因 017 被接受而自动开始。018 现为 In Progress，目标版本 v1.1.0，分支 `docs/018-v11-card-gate`，决策页是 [v1.1 卡片门槛决策](../rules/v1.1-card-gate-decision.md)。018 不改任何 `lifecycle`，不实现检测器，不宣布 v1.1.0 完成，不开始 019。裸 `except`、`Path.open` 和其他检测器后续任务仍开放。严重度和风险性质仍是临时判断，不是终局。信号、查询集和 `assert` 的未决设计仍是遗留风险。

001–007 的前言都有 `branch`。下表引用原值，不把它们改写成现行分支形式。008 为 Accepted，其前言 `branch` 仍是 `docs/008-docs-structure-blueprint`。009 为 Accepted，其前言 `branch` 仍是 `feat/009-explicit-rule-outcomes`。010 为 Accepted，其前言 `branch` 仍是 `docs/010-development-roadmap`。011 为 Accepted，其前言 `branch` 仍是 `docs/011-rule-card-feasibility`。012 为 Accepted，其前言 `branch` 仍是 `docs/012-pilot-protocol`。013 为 Accepted，其前言 `branch` 仍是 `feat/013-django-raw-sql`。014 为 Accepted，其前言 `branch` 仍是 `feat/014-rule-card-readiness`。015 为 Accepted，其前言 `branch` 仍是 `docs/015-large-change-scope-severity`。016 为 Accepted，其前言 `branch` 仍是 `docs/016-six-new-draft-cards`。017 为 Accepted，其前言 `branch` 仍是 `docs/017-card-content-format`。018 为 In Progress，其前言 `branch` 是 `docs/018-v11-card-gate`。接受不把 008、009、010、011、012、013、014、015、016、017 或 018 移入 `docs/versions/`。不建立 v1.2 冻结目录。规划文档是 [开发推进大纲](../standards/development-roadmap.md)。This is a planning document and is not evidence of completion or implemented functionality.

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
| 013 | Accepted | `feat/013-django-raw-sql` | [Django 原生 SQL 执行](013-django-raw-sql.md) |
| 014 | Accepted | `feat/014-rule-card-readiness` | [v1.1 规则卡片就绪核对](014-rule-card-readiness.md) |
| 015 | Accepted | `docs/015-large-change-scope-severity` | [大规模变更范围的严重度与风险性质](015-large-change-scope-severity.md) |
| 016 | Accepted | `docs/016-six-new-draft-cards` | [六张新的草稿规则卡片](016-six-new-draft-cards.md) |
| 017 | Accepted | `docs/017-card-content-format` | [规则卡片内容与模板格式](017-card-content-format.md) |
| 018 | In Progress | `docs/018-v11-card-gate` | [v1.1 卡片门槛收口](018-v11-card-gate.md) |

[v1.1 入口原文](v1.1-entry.md) 随文件迁出后保留。其中“写下这次索引更新时，该 PR 尚未合并”是当时的句子，008 不改写。

任务与分支的现行规则见 [任务与分支](../standards/branching-and-tasks.md)。目标系统规格见 [核心蓝图](../blueprint.md)。
