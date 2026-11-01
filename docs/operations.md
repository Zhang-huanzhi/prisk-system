# Prisk-System 本地运维手册

Prisk-System 是本地离线工具，不包含云端部署、数据库、账号或生产服务器运维。

## 初始化

```powershell
uv sync --project backend --locked
npm --prefix frontend ci
```

## 启动

API：

```powershell
uv run --project backend python -m prisk.cli.web_cli
```

API 默认读取仓库内 `backend/data/frozen-netbox/` 的运行时样本。该目录是从 v1.0 冻结产物提取后，在工作区独立保存并重新生成 stage05 的副本，不直接读取 `docs/versions/v1.0.0/` 或上一级 `Prisk-Note` 工作区。其他真实阶段产物仍通过 `--stage03`、`--stage04`、`--stage05` 显式传入。

前端：

```powershell
npm --prefix frontend run dev
```

生产构建检查后可使用 `npm --prefix frontend run start`。健康接口为 `http://127.0.0.1:8765/api/health`。

在 PyCharm 中选择 `Prisk Full Stack` 可同时启动后端 API 和前端开发服务器；也可以分别运行 `Prisk Backend API` 与 `Prisk Frontend Dev`。

## 检查与报告

```powershell
uv run --project backend python -m unittest discover -s backend/tests -t backend
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

阶段 CLI 的输入和输出路径由命令参数指定。生成产物写入用户明确指定的输出路径；不覆盖阶段 JSONL。仓库不保留大型实验数据或旧 MVP 的报告目录。

## 工作区保护

- 不对被分析仓库执行 checkout、fetch、merge、pull、reset 或其他状态修改；
- 不把工作区未提交改动纳入分支审计；
- `.venv`、`.uv-cache`、`frontend/node_modules`、`frontend/.next`、npm 缓存、`backend/tests/_tmp` 和 `backend/tests/_runtime` 不进入 Git；
- 不把本地凭证、完整实验仓库或 API 缓存复制进代码仓库；运行时冻结样本只保留已脱敏、可复核的必要产物；
- 恢复时重新克隆代码仓库、运行 `uv sync --project backend --locked` 和 `npm --prefix frontend ci`；真实阶段数据由调用方显式传入，不要求存在 Prisk note 工作区。
