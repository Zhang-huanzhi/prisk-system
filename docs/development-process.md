# Prisk-System 开发流程

| 适用版本 | v1.x.x |
| --- | --- |
| 状态 | Active |
| 更新时间 | 2026-11-01 |

## 迭代生命周期

每个功能或工程改造使用 `docs/iterations/v1.x/NNN-short-name.md`。状态依次为 Proposed、In Progress、Accepted、Archived。迭代文档必须记录目标、范围、不做事项、技术方案、兼容性、验收、实际测试和遗留风险。

v1.1 及后续迭代完成后，按目标版本归档到对应的 `docs/versions/v1.x.x/`；补丁版本只记录修复、依赖或文档变化。已发布版本目录冻结后不回写新行为。

## 分支与提交

从最新 `main` 创建一条与迭代对应的 `feat/`、`fix/` 或 `docs/` 短期分支。代码、测试和受影响文档在同一分支完成。允许查看 status、diff 和 log；提交、推送、PR、合并和 tag 需要用户明确授权。

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

公开 API、CLI、阶段 schema、分析输出或模块边界发生变化时，必须在迭代文档中记录兼容性；影响多个模块或长期演进的选择另建 ADR。

## 文件生命周期

- `backend/prisk/`、`backend/tests/`、`frontend/src/`：受版本控制的源码；
- `docs/versions/v1.x.x/`：验收后的冻结版本记录；若发现历史事实错误，先记录审查依据，再由维护者修正文档并保留变更记录；
- `docs/iterations/v1.x/`：当前活动版本的工作计划、实施记录和测试事实；
- `docs/adr/`：长期有效的架构决策；
- `.venv/`、缓存、`node_modules/`、`.next/` 和测试临时目录：本地生成内容，不纳入 Git。

文件迁移时同步更新 README 和相对链接。冻结版本只保留经筛选、脱敏且可复核的必要阶段产物；完整实验仓库、API 缓存和本机秘密不迁入代码仓库。

## 版本发布

版本 README 只写实际完成和验证的事实。所有检查通过并完成发布提交后，才允许在该提交创建 `v1.x.x` tag。当前工程化整理本身不自动创建 tag。
