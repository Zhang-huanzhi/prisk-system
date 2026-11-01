# Prisk-System 工程协作规范

## 仓库边界

- `Prisk-System/` 是独立 Git 仓库根目录。
- 上一级 `Prisk/` 是笔记工作区；`Prisk-Note/`、`EiheiZone-experience/` 和其他相邻目录不属于本仓库。
- `backend/` 是唯一 Python 工作区，包含 `prisk/`、`tests/`、`pyproject.toml` 和 `uv.lock`。
- `frontend/` 是独立的 Next.js 工作区。
- `docs/` 保存当前工程文档、ADR、迭代记录和冻结版本记录。

## 本地环境

- Python 虚拟环境只使用 `backend/.venv`。
- 不在仓库根目录创建第二个 `.venv`。
- 使用 `uv sync --project backend --locked` 安装后端依赖，或直接使用 `backend/.venv/Scripts/python.exe`。
- `frontend/node_modules`、`.next`、缓存、覆盖率和测试临时产物只保留在本机，不进入 Git。

## 常用检查

从仓库根目录运行：

```powershell
uv run --project backend python -m unittest discover -s backend/tests -t backend
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

## 修改原则

- 代码、测试和当前文档保持 `backend/`、`frontend/`、`docs/` 的边界。
- 冻结版本文档中的历史路径只用于记录基线，不作为当前入口。
- 不修改上一级笔记工作区，不复制阶段数据、实验仓库、凭证或本地秘密。
- 不自动提交、推送、合并或创建版本标签。

## 版本发布边界

- 当前工作区按待发布的 v1.0.0 基线维护；发布后新增工作进入 `docs/iterations/`，不回写 `docs/versions/v1.0.0/`。
- 发布前必须完成后端测试、前端 lint/typecheck/build、`git diff --check` 和敏感信息检查；提交、推送和创建 tag 由用户执行。
