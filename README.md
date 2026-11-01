# Prisk-System

Prisk-System 是一个本地 Git 分支代码审计工具。它读取已提交的 `base` 和 `head` 分支，以 `base...head` 三点 Diff 为基础，生成统一变更、Python AST 结构证据、规则结果和透明的人工复核优先级。

评分和规则命中用于帮助人工复核，不表示已经确认存在缺陷，也不代表缺陷概率。系统只读本地仓库，不执行 checkout、fetch、merge、pull 或其他会改变仓库状态的操作。

## 当前版本

当前工作区准备作为 v1.0.0 基线发布。代码、测试、运行时样本和冻结文档共同构成这一版本；发布后新增功能、修复和工程改造进入 `docs/iterations/`，不回写 `docs/versions/v1.0.0/`。冻结版本、架构、运维和 ADR 入口见 `docs/`。

## 目录结构

```text
Prisk-System/
├─ backend/                 Python 工作区
│  ├─ prisk/
│  │  ├─ domain/            Diff、AST、规则等分析逻辑
│  │  ├─ services/          数据集、项目和分支审计流程
│  │  ├─ adapters/          Git、JSONL、HTTP 接口边界
│  │  └─ cli/               正式命令实现
│  ├─ tests/                Python 单元与集成测试
│  └─ pyproject.toml        Python 依赖和包配置
├─ frontend/                Next.js 看板及 npm 配置
├─ docs/                    生命周期文档、ADR、版本和迭代记录
└─ AGENTS.md                协作与工程边界
```

## 初始化开发环境

Python 需要 3.13 或更高版本，Node.js 用于看板开发。

Python 只保留一个项目虚拟环境：`backend/.venv`。根目录不创建 `.venv`；使用 `uv --project backend` 时，uv 会自动使用或创建后端环境。

```powershell
uv sync --project backend --locked
npm --prefix frontend ci
```

Python 只使用标准库运行；前端依赖由 `frontend/package-lock.json` 固定。

## 启动本地看板

先启动只读 API：

```powershell
uv run --project backend python -m prisk.cli.web_cli
```

另开终端启动前端：

```powershell
npm --prefix frontend run start
```

打开 <http://localhost:3000>，可以加载冻结 NetBox 样本，或输入本地仓库路径后选择基准分支和目标分支开始审计。开发模式可使用：

```powershell
npm --prefix frontend run dev
```

## 测试与构建检查

```powershell
uv run --project backend python -m unittest discover -s backend/tests -t backend
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
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
uv run --project backend python -m prisk.cli.dataset_cli `
  --input "<netbox-survey.jsonl>" `
  --repo "<NetBox仓库>" `
  --output "<stage03-change-objects.jsonl>" `
  --manifest "<stage03-manifest.json>"
```

阶段 04：

```powershell
uv run --project backend python -m prisk.cli.structure_cli `
  --input "<stage03-change-objects.jsonl>" `
  --repo "<NetBox仓库>" `
  --output "<stage04-structure-objects.jsonl>" `
  --manifest "<stage04-manifest.json>"
```

阶段 05 规则、阶段 04 审计和阶段 07 评分分别通过 `prisk.cli.rules_cli`、`prisk.cli.structure_audit_cli` 和 `prisk.cli.scoring_cli` 运行。教师演示 API 默认使用 `backend/data/frozen-netbox/` 中从 v1.0 归档提取的运行时样本，不读取冻结文档目录或上一级笔记工作区；`backend/data/demo/` 仍保留最小开发数据。

## 正式入口

本地项目审计使用 `prisk.cli.web_cli` 和 `frontend/` 看板。旧 MVP 脚本、HTML demo、报告目录和兼容代码已移除。

## 当前边界

- 只分析本地已有的 Git 提交，不负责 clone 或 fetch；
- 不纳入未提交工作区改动；
- 规则是当前项目相关的最小结构信号，尚未完成独立标注集校准；
- 评分表示人工复核优先级，不是自动缺陷判定系统。
