# Prisk-System 工程协作规范

## 1. 仓库边界

- `Prisk-System/` 为独立 Git 仓库根目录。
- 上一级 `Prisk/` 笔记工作区以及同级目录不属于本仓库，不进行读写。
- `backend/` 为 Python 工作区，包含 `prisk/`、`tests/`、`pyproject.toml` 和 `uv.lock`。
- `frontend/` 为 Next.js 工作区。
- `docs/` 保存工程规范、技术蓝图、任务记录、规则资产与阶段归档。

## 2. 文档职责分工

- `docs/blueprint.md`：目标系统技术规格原文，定义系统原语与长远边界。
- `docs/architecture.md`：当前工程实现状态与链路说明。
- `docs/standards/`：开发流程、任务与分支规范、推进大纲与文档结构。
- `docs/rules/`：规则知识库中心，包含卡片模板（`rule-card-template.md`）、规则卡片与基类映射表。
- `docs/schemas/`：规则元数据 JSON Schema（`rule-metadata.schema.json`）。
- `docs/evaluation/`：实验与摸底资产（先导集与正式集物理隔离）。
- `docs/tasks/`：当前活动任务与阶段入口文档。
- `docs/versions/`：已冻结的阶段归档记录（如 `v1.0.0/`、`v1.1.0/`、`v1.2.0/`、`v1.3.0/`），冻结后不回写新行为。

## 3. 开发与任务工作流

- 任何变更均须对应一条任务记录，文件格式为 `docs/tasks/NNN-short-name.md`。
- 任务须包含 YAML 前言字段：`task_id`、`target_version`、`title`、`status`、`branch`、`date`。
- 分支与任务一对一绑定，命名形式为 `<type>/<三位任务编号>-<短英文名>`（类型限 `feat`, `fix`, `docs`, `refactor`, `chore`, `exp`）。
- 规则卡片编写须遵循 `docs/rules/rule-card-template.md` 标准结构，字段及枚举须与 `docs/schemas/rule-metadata.schema.json` 保持一致。
- 文档记录以事实陈述为主，避免跨任务嵌套递归的免责语句。
- 阶段里程碑收工时，已完成任务文档迁入 `docs/versions/<version>/tasks/`。

## 4. 本地环境与执行命令

- Python 环境仅使用 `backend/.venv`，不在仓库根目录创建虚拟环境。
- 本地执行优先使用 `backend/.venv/Scripts/python.exe`。
- 变更完成后须运行以下检查：

```powershell
backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend
npm --prefix frontend run lint
npm --prefix frontend run typecheck
git diff --check
```

## 5. 交付边界

- 不自动执行 `git commit`、`git push`、合并 PR 或创建 Git Tag。
- 提交、推送、合并与打标签均由用户在本地确认并执行。
