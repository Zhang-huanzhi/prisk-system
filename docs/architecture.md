# Prisk-System 架构

本文件描述当前系统的工程实现。目标系统规格见 [核心蓝图](blueprint.md)。

- **当前实现与目标边界**：蓝图中的机器学习、大规模实证权重校准属于后续目标；当前已落地 29 条局部 AST/Diff 三态规则、5 套运行时配置预设、三级快照局部重跑缓存与可复现配置快照报告导出。
- **运行时规则目录**：当前维护 29 条规则（5 条历史结构规则、9 条代码异味、11 条 Django/DRF 契约、4 条变更冲击）。研究登记册（29 条，24 implemented / 5 draft）与规则卡片（26 张，24 implemented / 2 draft）均已全面对齐。
- **三态执行**：新鲜分析为运行时全部 29 条规则记录显式终态（`Hit` / `NotFound` / `Unanalyzed`）。上下文不成立时不记 NotFound，已保存历史不补写终态。
- **延后设计项（Deferred Drafts）**：知识库中剩余 2 张草稿卡片按原设计保持 `draft`：`data.django_transaction_boundary_changed`（依赖语句级 `atomic` 包含关系）与 `workflow.large_change_scope`（依赖项目级阈值与模块映射政策）。

## 运行链路

```text
本地项目路径 + base/head
→ Git 三点 Diff（Stage03）
→ Python AST 结构证据（Stage04）
→ 三级快照缓存与局部重跑判定（Tier 0 全量 / Tier 1 重算规则 / Tier 2 仅重算评分）
→ 29 条三态结构规则评估（Stage05，支持动态阈值注入）
→ 透明复核评分 + Gatekeeper 一票抬升（Stage07/08）
→ 固化运行配置快照（config.snapshot.v1 + SHA-256 指纹）
→ 标准库 HTTP API / Next.js 交互工作台 / Markdown & JSON 报告导出
```

分析只读取已提交快照，不执行 checkout、fetch、merge、pull，不纳入未提交工作区。

代码异味与框架契约检测器读取 head AST 中与新增行相交的节点（或在路由、视图动作、迁移与字段中配对 base/head 结构），并统一进入 Finding 管道。已接入规则包含 9 条语言异味（含吞异常、裸异常、动态执行、硬编码秘密、未管理 open、深层控制流、全局可变状态、生产 assert、可变默认参数）、11 条后端契约（含 DRF 增删参数、ViewSet 动作变更、路由变更、权限装饰器删除、权限策略降级、原生 SQL、敏感配置、CSRF 豁免、QuerySet 绕过、信号泄漏等）与 4 条变更冲击（含破坏性迁移、非空约束收紧、字段改名无 db_column、测试协同缺失）。它们不替换既有五条历史结构规则，命中仅作为复核线索，不代表缺陷必然发生。`workflow.test_collaboration_gap` 依据三点 Diff 留下的文件状态和增删行数判定，证据不足时记入 `summary.unanalyzed`。

## 运行时配置预设与快照局部重跑

- **运行时配置解耦（`prisk/domain/config.py`）**：
  - 支持 5 套场景化预设：`balanced`（均衡基线）、`security_focus`（安全加固审查）、`framework_upgrade`（框架与迁移升级）、`daily_review`（日常代码合规）与 `legacy_baseline`（历史兼容基线，保持 10 分分母不变）。
  - 支持细粒度覆盖 `enabled_rules`、`rule_weights`（0–5）、`thresholds`（`medium` / `high`）及规则内部判定参数 `rule_thresholds`（`code.deep_control_flow.max_depth` 与 `code.hardcoded_secret.min_length`）。
- **三级快照局部重跑缓存（`prisk/services/analysis_cache.py`）**：
  - 按 `f"{repo}:{base_sha}..{head_sha}"` 线程安全缓存 Stage03 Diff 与 Stage04 AST 结构对象；
  - `full_run`（Tier 0）：首次分析或 `refresh=True` 时全量执行；
  - `stage05_rules_rerun`（Tier 1）：规则开关或 `rule_thresholds` 变更时复用 Diff/AST，仅重跑 Stage05 规则与 Stage07 评分；
  - `stage07_rescore_only`（Tier 2）：仅规则权重或风险分段阈值变更时复用 Diff/AST/Rules，毫秒级重算评分。
- **审查报告配置快照固化（`prisk/domain/report_export.py`）**：
  - 每次分析报告均注入 `config_snapshot`（`config.snapshot.v1`），封存预设名称、是否自定义覆盖、16 位确定性 SHA-256 指纹 `config_digest`、启用/禁用规则名单、29 条规则权重及双重阈值；
  - 导出的 Markdown 与 JSON 报告强制包含完整配置快照与可复现配置载荷块，确保任何一次审查评分均可追溯、可复现。

## 规则终态

新鲜的 `evaluate_rules` 在原有 Finding 之外写入 `rule_outcomes`。schema 为 `stage05.v2`。每个已启用规则恰好一条，状态只为 `Hit`、`NotFound` 或 `Unanalyzed`。

- `Hit`：现有检测器产出了该规则的 Finding。只有这个状态产生 Finding。命中不表示其余对象都已查完；`summary.unanalyzed` 仍保留解析或证据缺口。
- `NotFound`：该规则的上下文适用，并且该上下文已经完整执行，没有 Finding。零条 Finding 本身不是 NotFound。
- `Unanalyzed`：解析失败或降级、结构细节不足、缺少框架或路径上下文、没有可判断对象、没有文件变更通道，或前置阶段不是 `ok`。结果带 `reasons` 和 `objects`。它不加分，不是通过，也不是代码安全。

`api.signature_changed` 与 `config.configuration_structure_changed` 只在对应路径被结构扫描完整覆盖、且没有命中时记 NotFound。`auth.permission_structure_changed` 与 `data.transaction_structure_changed` 还要看到对应路径，或看到它们会检查的装饰器、调用；Python 解析不完整时不能记 NotFound。没有这些上下文时原因是 `missing_framework_context`。`code.exception_structure_changed` 只在全部 Python 文件的结构变更都已扫描、且没有异常处理变更时记 NotFound。代码异味只在实际检查过适用节点、并且没有该规则的缺口和解析失败时记 NotFound；没有该类节点是 `context_not_established`。`data.django_raw_sql_execution` 在至少一条相交调用已按闭集分类、且没有该规则的缺口和解析失败时记 NotFound。高价值检测器（如 Django URL 变更、ViewSet 动作变更、DRF 参数增删、破坏性迁移等）遵循相同的“上下文不成立时不记 NotFound”原则。`workflow.test_collaboration_gap` 在文件变更通道完整且没有生产代码缺测试特征时记 NotFound。只有 AST、没有文件变更通道时原因是 `missing_file_change_channel`，不额外写入 `summary.unanalyzed`。

## 评分与一票抬升（Gatekeeper）

评分链路（`prisk/domain/gatekeeper.py`、`demo_service.py` 与 `branch_analysis.py`）依据 Finding 计算人工复核优先级分数（0–100），分级为 `low`、`medium`、`high`。
同时联动读取规则登记册 `gatekeeper=true` 元数据：当触发高危特征（`migrations` 路径下的 `DeleteModel` / `RemoveField` 破坏性操作，或 `permission_classes` 设为 `AllowAny` / 空列表容器的权限降级）时，无论当前综合得分是否达到高风险阈值，系统均通过 `apply_gatekeeper_lift` 将 `risk_level` 强制抬升为 `"high"`，并在评分结果中保留 `gatekeeper_lift=True` 与结构命中证据。

已保存的 demo stage05 没有 `rule_outcomes`。演示 API 原样返回历史 Finding 和分数，`rule_outcome_availability` 为 `unavailable`，不把缺少 Finding 回填成 NotFound。分支分析是新鲜执行，终态为 `recorded`。默认兼容基线（`legacy_baseline`）下新增规则权重仍是 0，PR #12 默认可得权重仍是 10。

## Python 分层

```text
backend/prisk/domain/    变更、AST、规则、检测器、配置模型、报告导出与 Gatekeeper 逻辑
backend/prisk/services/  数据集、结构审计、分析快照缓存、项目和分支分析用例编排
backend/prisk/adapters/  Git、JSONL、HTTP 和外部文件访问边界
backend/prisk/cli/       正式命令实现
```

分层收敛于 domain、services、adapters、cli 四层；新增实现进入对应分层。旧 MVP 演示、HTML demo、根目录兼容转发模块和报告输出目录已经移除。

## 稳定契约

- CLI：`python -m prisk.cli.web_cli`、`dataset_cli`、`structure_cli`、`structure_audit_cli`、`rules_cli`、`scoring_cli`；
- API：冻结样本 `/api/health`、`/api/dataset`、`/api/pr/<number>`、`/api/analyze`，配置与缓存 `/api/config/presets`、`/api/cache/stats`，本地项目 `/api/projects/load`、`/api/projects/<id>/branches`、`/api/branch-analysis`；
- 数据：stage03.v1 至 stage08.branch-report.v1，配置快照 `config.snapshot.v1`；教师演示 API 与评分 CLI 的当前默认输入是已跟踪的 `backend/data/demo/`。`frozen_sample_data_root()` 仍指向可选的 `backend/data/frozen-netbox/` 提取样本，供以后的验证迭代显式传入，不是启动依赖。

## 前端

`frontend/` 使用 Next.js、React、TypeScript 和 Tailwind CSS。前端通过 rewrite 访问本地 API，不自行读取 Git 或阶段 JSONL。页面的分析单位是一次冻结 PR 或一次本地项目 base/head 分支审查，支持 29 条规则三态检视、5 套场景预设切换、规则内部阈值调节、局部重跑层级展示与固化配置快照的 Markdown/JSON 报告导出。
