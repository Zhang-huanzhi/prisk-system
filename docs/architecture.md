# Prisk-System 架构

本文件描述当前系统的工程实现。目标系统规格见 [核心蓝图](blueprint.md)。

- **当前实现与目标边界**：蓝图中的机器学习、权重调优、动态配置和 NetBox 生产实证属于远期目标，非当前已落地功能。
- **运行时规则目录**：当前由代码静态维护 14 条规则（5 条历史结构规则、7 条代码异味、1 条测试协同、1 条 Django 原生 SQL）。研究登记册（29 条）与规则卡片（26 张）为设计与验证资产，未接入运行时配置。
- **三态执行**：新鲜分析为运行时全部 14 条规则记录显式终态（`Hit` / `NotFound` / `Unanalyzed`）。上下文不成立时不记 NotFound，已保存历史不补写终态。
- **已知合同差异（Carve-outs）**：`code.bare_exception` 检测器当前仍将 `except Exception` 包含在同一条 Finding 内（拆分留待 v1.2）；`code.unmanaged_open` 检测器当前仅检查直接名称 `open`（`Path.open` 扩展留待 v1.2）。

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

v1.1 的代码异味规则读取 head AST 中与新增行相交的节点，并进入同一 Finding 管道。已接入规则包含 `code.swallowed_exception`、`code.bare_exception`、`code.dynamic_execution`、`code.unmanaged_open`、`code.deep_control_flow`、`code.hardcoded_secret` 和 `code.global_mutable_state`。它们不替换既有五条结构规则，命中仅作为复核线索，不代表漏洞必然发生。`workflow.test_collaboration_gap` 依据三点 Diff 留下的文件状态和增删行数判定，证据不足时记入 `summary.unanalyzed`，默认权重为 1。`data.django_raw_sql_execution` 读取与新增行相交的调用节点（闭集为 `RawSQL` 直接名称，或 `callee` 尾段 `execute`、`executemany`、`raw`），默认权重为 0。

## 规则终态

新鲜的 `evaluate_rules` 在原有 Finding 之外写入 `rule_outcomes`。schema 为 `stage05.v2`。每个已启用规则恰好一条，状态只为 `Hit`、`NotFound` 或 `Unanalyzed`。

- `Hit`：现有检测器产出了该规则的 Finding。只有这个状态产生 Finding。命中不表示其余对象都已查完；`summary.unanalyzed` 仍保留解析或证据缺口。
- `NotFound`：该规则的上下文适用，并且该上下文已经完整执行，没有 Finding。零条 Finding 本身不是 NotFound。
- `Unanalyzed`：解析失败或降级、结构细节不足、缺少框架或路径上下文、没有可判断对象、没有文件变更通道，或前置阶段不是 `ok`。结果带 `reasons` 和 `objects`。它不加分，不是通过，也不是代码安全。

`api.signature_changed` 与 `config.configuration_structure_changed` 只在对应路径被结构扫描完整覆盖、且没有命中时记 NotFound。`auth.permission_structure_changed` 与 `data.transaction_structure_changed` 还要看到对应路径，或看到它们会检查的装饰器、调用；Python 解析不完整时不能记 NotFound。没有这些上下文时原因是 `missing_framework_context`。`code.exception_structure_changed` 只在全部 Python 文件的结构变更都已扫描、且没有异常处理变更时记 NotFound。代码异味只在实际检查过适用节点、并且没有该规则的缺口和解析失败时记 NotFound；没有该类节点是 `context_not_established`。`data.django_raw_sql_execution` 在至少一条相交调用已按闭集分类、且没有该规则的缺口和解析失败时记 NotFound。`extra`、`callproc` 和含 `schema_editor` 的调用是 `missing_framework_context`。空 `callee` 或无法确认最后一段是 `unsupported_stage04_details`。没有相交调用时是 `context_not_established`。`workflow.test_collaboration_gap` 在文件变更通道完整且没有生产代码缺测试特征时记 NotFound。只有 AST、没有文件变更通道时原因是 `missing_file_change_channel`，不额外写入 `summary.unanalyzed`。

已保存的 demo stage05 没有 `rule_outcomes`。演示 API 原样返回历史 Finding 和分数，`rule_outcome_availability` 为 `unavailable`，不把缺少 Finding 回填成 NotFound。分支分析是新鲜执行，终态为 `recorded`。评分仍只按 Finding 和原来的 `summary.test_collaboration` 计。默认权重不变，异味权重仍是 0，默认可得权重仍是 10。

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
