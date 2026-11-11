# 任务与分支

| 适用版本 | v1.x |
| --- | --- |
| 状态 | Active |
| 任务 | [030](../tasks/030-v13-milestone-closure.md) |
| 分支 | `docs/030-v13-milestone-closure` |

## 每个变更都有任务

任何变更，不论规模，都必须有一条任务记录。原先按规模豁免任务的例外废除，不为兼容旧习惯而保留。

同一目标下的后续提交和评审修复继续使用同一条任务、同一条分支，不另取任务编号。

任务编号是跨版本的永久身份：三位数字，已使用的编号不重编、不复用。版本目录不把编号从 001 重新开始。

- **001–018**：已全部评定为 Accepted，并已随 v1.1.0 里程碑归档移入 [docs/versions/v1.1.0/tasks/](../versions/v1.1.0/tasks/)。
- **019–024**：已全部评定为 Accepted，并已随 v1.2.0 里程碑归档移入 [docs/versions/v1.2.0/tasks/](../versions/v1.2.0/tasks/)。
- **025–029**：已全部评定为 Accepted，并已随 v1.3.0 里程碑归档移入 [docs/versions/v1.3.0/tasks/](../versions/v1.3.0/tasks/)。
- **030 及后续活动任务**：实时状态与**下一个未使用的任务编号**统一以 [活动任务工作区](../tasks/README.md) 及当前阶段入口（[v1.4 入口](../tasks/v1.4-entry.md)）为准（Task 030 占用后，下一个未使用编号为 **031**）。

任务状态只使用 `Proposed`、`In Progress`、`Accepted`。任务不使用 `Archived` 作为其内部状态值。没有明确验收时保持 `In Progress` 或 `Proposed`。

## 记录形式

任务记录基于标准模板 [`docs/tasks/_task-template.md`](../tasks/_task-template.md) 创建，以 Markdown 文件保存于 `docs/tasks/NNN-short-name.md`。

YAML 元数据写在文件开头的前言里：

- `task_id`：三位数字字符串（如 `"030"`）
- `target_version`：目标版本（如 `"v1.3.0"`）
- `title`：任务标题
- `status`：`Proposed` / `In Progress` / `Accepted`
- `branch`：承载该工作的 Git 分支名
- `date`：创建或更新日期

正文统一采用标准六节结构：

1. **背景与目标**：承接的阶段入口、前序遗留与核心目标；
2. **范围与边界**：纳入范围与不做事项（仅记录技术与产品边界，不写日常流程套话）；
3. **技术方案与契约设计**：核心实现机制（如三态判定契约、架构设计）及对既有 Schema、满分基线与历史快照的兼容性影响；
4. **交付物与改动清单**：分类改动文件列表及可选的「规则生命周期变更」表；
5. **验证与验收**：核心验收断言与实际执行的测试/检查结果；
6. **已知限制与残余风险**：静态分析边界、工程管线限制与后续演进事项。

任务编号、文件名前缀、前言中的 `branch` 与 Git 分支必须保持一对一严格一致。

## 分支形式

类型只使用 `feat`、`fix`、`docs`、`refactor`、`exp`、`chore`。

形式为 `<type>/<三位任务编号>-<短英文名>`。短英文名使用小写字母、数字和连字符。

## 归档规则

- 未完成或活动中的任务存放在 `docs/tasks/`。
- 阶段里程碑或版本收工归档时，将对应的任务文件迁入 `docs/versions/<version>/tasks/`，并在版本目录主 README 中提供完整任务索引表。
- 仓库当前已建立的归档目录包含 `docs/versions/v1.0.0/`、`docs/versions/v1.1.0/`、`docs/versions/v1.2.0/` 与 `docs/versions/v1.3.0/`。
