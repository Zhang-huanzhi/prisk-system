# 任务与分支

| 适用版本 | v1.x |
| --- | --- |
| 状态 | Active |
| 任务 | [008](../tasks/008-docs-structure-blueprint.md) |
| 分支 | `docs/008-docs-structure-blueprint` |

## 每个变更都有任务

任何变更，不论规模，都必须有一条任务记录。原先开发流程把任务记录限定在“功能或工程改造”。该范围限制废除。按规模豁免任务的例外废除，并且不为兼容旧习惯而保留。

同一目标下的后续提交和评审修复继续使用同一条任务、同一条分支，不另取任务编号。

任务编号是跨版本的永久身份：三位数字，已使用的编号不重编、不复用。版本目录不把编号从 001 重新开始。009 已用于显式规则终态，状态为 Accepted。010 用于开发推进大纲，状态为 Accepted。011 用于规则卡片与结构可行性，状态为 Accepted。012 用于真实 PR 先导试点协议，状态为 Accepted。013 用于 Django 原生 SQL 执行检测，状态为 Accepted。014 用于 v1.1 规则卡片就绪核对，状态为 Accepted。015 用于 `workflow.large_change_scope` 的严重度与风险性质临时对齐，状态为 Accepted。015 不因 014 被接受而自动开始；它只因所有者授权工程负责人做这次临时判断而开始。016 用于六张新的草稿规则卡片，状态为 In Progress。016 不因 015 被接受而开始；它因所有者要求新增这六张卡片而开始。015 的接受不表示 v1.1.0 已经完成，也不开始检测器或 v1.2 批次。严重度和风险性质仍是临时判断，后续算法阶段可以修订，不是终局。016 同样不表示 v1.1.0 已经完成。下一个未使用的编号是 017。017 尚未开始。017 不因 016 打开而开始。

状态只使用 Proposed、In Progress、Accepted。任务不使用 Archived。没有用户接受时，任务保持 In Progress 或 Proposed，不写成 Accepted。

## 记录形式

001–007 的任务记录是 Markdown，YAML 写在文件开头的前言里。仓库没有独立的任务 `.yaml` 文件，也没有另一份任务 schema 文件。

这些前言已经使用的键是：

- `task_id`
- `target_version`
- `title`
- `status`
- `branch`
- `date`

关联 Git 分支的字段采用已经存在的 `branch`。从 008 起，新任务的 `branch` 必须填写。任务编号、文件名前缀、前言中的 `branch` 和承载该工作的 Git 分支必须是同一条任务。

不为同一任务再写一份 `T008.yaml`。第二份记录若与前言或分支不一致，就视为任务、YAML 和分支不一致。

008 的对应关系：

| 项 | 值 |
| --- | --- |
| 文件 | `docs/tasks/008-docs-structure-blueprint.md` |
| `task_id` | `008` |
| 前言 `branch` | `docs/008-docs-structure-blueprint` |
| Git 分支 | `docs/008-docs-structure-blueprint` |

## 分支形式

类型只使用 `feat`、`fix`、`docs`、`refactor`、`exp`、`chore`。

形式是 `<type>/<三位任务编号>-<短英文名>`。短英文名使用小写字母、数字和连字符。一条任务对应一条这样的分支。

008 使用 `docs/008-docs-structure-blueprint`。

## 历史记录

编辑 008 之前核过 001–007：每条前言都有 `branch`，没有缺少该字段的任务记录。这些值保持原样，不按新形式回填：

| 任务 | 状态 | 前言中的 `branch` |
| --- | --- | --- |
| 001 | Accepted | `main` |
| 002 | Accepted | `v1.1.0-002-rule-knowledge-base` |
| 003 | Accepted | `docs/rule-id-naming` |
| 004 | Accepted | `feat/004-ast-detectors` |
| 005 | Accepted | `feat/005-second-batch-code-smells` |
| 006 | Accepted | `feat/006-remaining-code-smells` |
| 007 | Accepted | `feat/007-test-collaboration` |

若以后发现更早的记录没有 `branch`，把它视为历史记录，不凭猜测补充分支名。新形式只约束 008 以及其后的新任务。

## 归档

任务变为 Accepted，还不等于它所在版本已经归档。v1.1.0 尚未冻结，001–007 因此留在 `docs/tasks/`。版本发布归档时才写入对应的 `docs/versions/`。当前不建立 `docs/versions/v1.1/` 或 `docs/versions/v1.1.0/`。

v1.0.0 阶段 08「本地项目与分支审计」不是任务 008。008 开始前仓库里没有任务编号 008。
