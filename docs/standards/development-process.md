# Prisk-System 开发流程

| 适用版本 | v1.x.x |
| --- | --- |
| 状态 | Active |
| 更新时间 | 2026-11-06 |
| 任务 | [008](../tasks/008-docs-structure-blueprint.md) |

## 迭代生命周期

每个变更，不论规模，都使用一条任务记录：`docs/tasks/NNN-short-name.md`。不存在可以不建任务的小改动例外。按规模豁免任务的做法已经废除，并且不为兼容旧习惯而保留。任务编号、状态、YAML 前言和分支形式以 [任务与分支](branching-and-tasks.md) 为准。

状态只使用 Proposed、In Progress、Accepted。任务不使用 Archived。任务文档记录目标、范围、不做事项、技术方案、兼容性、验收、实际测试和遗留风险。

同一目标的后续提交和评审修复继续使用同一条任务和同一条分支。

v1.1 及后续任务在对应版本发布时写入 `docs/versions/v1.x.x/`。补丁版本只记录修复、依赖或文档变化。已发布版本目录冻结后不回写新行为。版本目录的发布记录不是任务状态。

目标系统的规格原文是 [核心蓝图](../blueprint.md)。实现、测试和验收记录没有写明的能力，不回填成已经完成的功能。

## 分支与提交

从最新 `main` 创建一条与任务一对一的短期分支。类型和形式见 [任务与分支](branching-and-tasks.md)。代码、测试和受影响文档在同一分支完成。允许查看 status、diff 和 log；提交、推送、PR、合并和 tag 需要用户明确授权。

## 检查门槛

```powershell
uv sync --project backend --locked
uv run --project backend python -m unittest discover -s backend/tests -t backend
npm --prefix frontend ci
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
git diff --check
```

公开 API、CLI、阶段 schema、分析输出或模块边界发生变化时，必须在任务文档中记录兼容性；影响多个模块或长期演进的选择另建 ADR。

## 文件生命周期

- `backend/prisk/`、`backend/tests/`、`frontend/src/`：受版本控制的源码；
- `docs/versions/v1.x.x/`：验收后的冻结版本记录；若发现历史事实错误，先记录审查依据，再由维护者修正文档并保留变更记录；
- `docs/tasks/`：未完成，或已接受但尚未随版本归档的任务；
- `docs/standards/`：文档结构、任务与分支、开发流程和推进大纲；
- `docs/blueprint.md`：目标系统规格原文；
- `docs/adr/`：长期有效的架构决策；
- `.venv/`、缓存、`node_modules/`、`.next/` 和测试临时目录：本地生成内容，不纳入 Git。

文件迁移时同步更新 README 和相对链接。冻结版本只保留经筛选、脱敏且可复核的必要阶段产物；完整实验仓库、API 缓存和本机秘密不迁入代码仓库。

## 版本发布

版本 README 只写实际完成和验证的事实。所有检查通过并完成发布提交后，才允许在该提交创建 `v1.x.x` tag。008 的文档结构调整不创建 tag。
