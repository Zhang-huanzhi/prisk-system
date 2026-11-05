# Prisk-System 架构

## 运行链路

```text
本地项目路径 + base/head
→ Git 三点 Diff
→ 统一变更对象
→ Python AST 结构证据
→ 结构规则
→ 透明复核评分
→ 标准库 HTTP API / Next.js 看板
```

分析只读取已提交快照，不执行 checkout、fetch、merge、pull，不纳入未提交工作区。

v1.1 的 `code.swallowed_exception`、`code.bare_exception` 和 `code.dynamic_execution` 读取 head AST 中与新增行相交的节点，并进入同一 Finding 管道。它们不替换既有五条结构规则。JSON 登记册仍不是运行时配置。

## Python 分层

```text
backend/prisk/domain/    变更、AST、规则和评分逻辑
backend/prisk/services/  数据集、结构、审计、项目和分支分析用例编排
backend/prisk/adapters/  Git、JSONL、HTTP 和外部文件访问边界
backend/prisk/cli/       正式命令实现
```

分层迁移属于 v1.1 活动工作，当前实现已经收敛到 domain、services、adapters、cli 四层；新增实现进入对应分层。旧 MVP 演示、HTML demo、根目录兼容转发模块和报告输出目录已经移除。

## 稳定契约

- CLI：`python -m prisk.cli.web_cli`、`dataset_cli`、`structure_cli`、`structure_audit_cli`、`rules_cli`、`scoring_cli`；
- API：冻结样本 `/api/health`、`/api/dataset`、`/api/pr/<number>`、`/api/analyze`，本地项目 `/api/projects/load`、`/api/projects/<id>/branches`、`/api/branch-analysis`；
- 数据：stage03.v1 至 stage08.branch-report.v1；
- 旧 MVP 脚本、HTML 展示 demo、根目录兼容模块和报告目录已移除。

## 前端

`frontend/` 使用 Next.js、React、TypeScript 和 Tailwind CSS。前端通过 rewrite 访问本地 API，不自行读取 Git 或阶段 JSONL。页面的分析单位是一次冻结 PR 或一次本地项目 base/head 分支审查。
