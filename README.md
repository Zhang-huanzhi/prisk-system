# Prisk-System

Prisk-System 是一个本地 Git 分支代码审计工具。它读取已提交的 `base` 和 `head` 分支，以 `base...head` 三点 Diff 为基础，生成统一变更、Python AST 结构证据、规则结果和透明的人工复核优先级。

评分和规则命中用于帮助人工复核，不表示已经确认存在缺陷，也不代表缺陷概率。系统只读本地仓库，不执行 checkout、fetch、merge、pull 或其他会改变仓库状态的操作。

## 目录结构

```text
src/prisk/        正式 Python 包和模块化 CLI
src/prisk/legacy/  旧版 JSON/HTML 演示实现
apps/web/          Next.js 看板
tests/             Python 单元和集成测试
reports/           本地生成报告目录，不进入 Git
```

## 初始化开发环境

Python 需要 3.13 或更高版本，Node.js 用于看板开发。

```powershell
uv sync
npm --prefix apps/web install
```

Python 只使用标准库运行；前端依赖由 `apps/web/package-lock.json` 固定。

## 启动本地看板

先启动只读 API：

```powershell
uv run python -m prisk.web_cli
```

另开终端启动前端：

```powershell
npm --prefix apps/web run start
```

打开 <http://localhost:3000>，输入本地仓库路径，选择基准分支和目标分支后开始审计。开发模式可使用：

```powershell
npm --prefix apps/web run dev
```

## 测试与构建检查

```powershell
uv run python -m unittest discover -s tests -t .
npm --prefix apps/web run lint
npm --prefix apps/web run typecheck
npm --prefix apps/web run build
```

## 正式分支审计流程

分支审计的处理链路是：

```text
项目路径
→ 本地/远程跟踪分支
→ base/head
→ merge-base(base, head)
→ base...head Diff
→ 文件与 Hunk
→ AST 结构证据
→ 规则结果
→ 当前分支复核报告
```

API 服务提供：

```text
POST /api/projects/load
GET  /api/projects/<project_id>/branches
POST /api/branch-analysis
```

## 阶段数据 CLI

阶段 03：

```powershell
uv run python -m prisk.dataset_cli `
  --input "<netbox-survey.jsonl>" `
  --repo "<NetBox仓库>" `
  --output "<stage03-change-objects.jsonl>" `
  --manifest "<stage03-manifest.json>"
```

阶段 04：

```powershell
uv run python -m prisk.structure_cli `
  --input "<stage03-change-objects.jsonl>" `
  --repo "<NetBox仓库>" `
  --output "<stage04-structure-objects.jsonl>" `
  --manifest "<stage04-manifest.json>"
```

阶段 05 规则、阶段 04 审计和阶段 07 评分分别通过 `prisk.rules_cli`、`prisk.structure_audit_cli` 和 `prisk.scoring_cli` 运行。阶段产物保存在 Prisk 项目目录，不复制进本仓库。

## 兼容入口

根目录的 `main.py` 和 `run.py` 仅保留旧版命令兼容能力，并会提示使用正式入口：

```powershell
uv run python main.py --repo "<仓库>" --base main --head feature/example
uv run python run.py
```

新的本地项目审计应使用 `prisk.web_cli` 和 `apps/web` 看板。旧版实现位于 `src/prisk/legacy/`，不参与新的分支审计流水线。

## 当前边界

- 只分析本地已有的 Git 提交，不负责 clone 或 fetch；
- 不纳入未提交工作区改动；
- 规则是当前项目相关的最小结构信号，尚未完成独立标注集校准；
- 评分表示人工复核优先级，不是自动缺陷判定系统。
