# Prisk-System 架构

本文件描述当前实现。目标系统写在 [核心蓝图](blueprint.md)。蓝图是目标规格；其中的机器学习、权重调优、动态配置、NotFound 全量跟踪和 NetBox 实证验证都不是本文件已经落地的行为。

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

v1.1 的代码异味规则读取 head AST 中与新增行相交的节点，并进入同一 Finding 管道。004 接入 `code.swallowed_exception`、`code.bare_exception` 和 `code.dynamic_execution`。005 在同一管道接入 `code.unmanaged_open` 和 `code.deep_control_flow`。006 在同一管道接入 `code.hardcoded_secret` 和 `code.global_mutable_state`。它们不替换既有五条结构规则，也不表示秘密、漏洞或可变状态串扰已经发生。007 的 `workflow.test_collaboration_gap` 不读 AST，只读三点 Diff 留下的文件状态和新增/删除行数，并使用源码中的默认路径分类。证据不足时写入既有的 `summary.unanalyzed`。它的默认权重仍是原来的测试协同权重 1，不另加一分，默认可得权重仍是 10。JSON 登记册仍不是运行时配置。

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
- 数据：stage03.v1 至 stage08.branch-report.v1；教师演示 API 与评分 CLI 的当前默认输入是已跟踪的 `backend/data/demo/`。`frozen_sample_data_root()` 仍指向可选的 `backend/data/frozen-netbox/` 提取样本，供以后的验证迭代显式传入，不是启动依赖。
- 旧 MVP 脚本、HTML 展示 demo、根目录兼容模块和报告目录已移除。

## 前端

`frontend/` 使用 Next.js、React、TypeScript 和 Tailwind CSS。前端通过 rewrite 访问本地 API，不自行读取 Git 或阶段 JSONL。页面的分析单位是一次冻结 PR 或一次本地项目 base/head 分支审查。
