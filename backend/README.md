# Prisk-System Backend

本目录是独立的 Python 工作区：`prisk/` 是应用包（作用对应 EiheiZone 的 `app/`），保存 domain、services、adapters 和 cli；`tests/` 保存 Python 测试；`pyproject.toml` 与 `uv.lock` 管理 uv 环境。

`prisk/` 不是第二个项目目录，也不是第二个虚拟环境；它是 Python 的稳定导入根，因此正式入口使用 `python -m prisk.cli.<name>`。

从仓库根目录运行：

```powershell
uv sync --project backend --locked
uv run --project backend python -m prisk.cli.web_cli
uv run --project backend python -m unittest discover -s backend/tests -t backend
```
