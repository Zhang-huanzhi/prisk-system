---
task_id: "032"
target_version: "v1.4.0"
title: "v1.4.0 有效性证明方案设计与定性决策矩阵"
status: "Accepted"
branch: "docs/032-v14-validation-strategy"
date: "2026-11-13"
---

# Task 032：v1.4.0 有效性证明方案设计与定性决策矩阵

## 1. 背景与目标

`v1.4.0` 阶段的核心目标是回应毕业论文实证环节关于“系统有效性如何获得可辩护证据支撑”的论证问题。前期评估初稿（Task 031）搭建了物理隔离校验与汇总框架，但在方法论、职责口径与架构对齐上存在三项偏差：
1. **被测系统口径滞后**：前期描述仍混合了 `v1.0.0` 离线批处理分步脚本（`dataset_cli` → `Stage 03–07`）叙事，未全面对接 [`v1.3.0` 里程碑](../versions/v1.3.0/README.md) 已经收敛的动态分支/PR 变更快照审查引擎（`analyze_branches`、`stage08.branch-report.v1`、非测试 Python 业务代码自动纳入、`AnalysisSnapshotCache` 三级重跑与 `config.snapshot.v1`）。
2. **验证手段同质化且面临 Author Bias 危机**：将全部运行时规则一刀切地绑定为“单一作者通读 PR Diff 逐条打标算人工精确率”，既脱离多阵营差异化论证逻辑，又会在缺乏外部资深双盲审稿团队时使论文主结论面临自测确认偏误（Author Bias）质疑。
3. **规则职责文档仍残留强制“人工标注”前缀**：既有 [`rule-responsibility-matrix.md`](../rules/rule-responsibility-matrix.md) 中 `backend_contract` 与 `breaking_impact` 仍将“人工标注”列为工程验证必选项，若不同步修订会与新的决策体系直接冲突。

为此，本任务作为 `v1.4.0` 纯研究设计与架构决策任务，围绕以下目标完成定案：
- **对齐最新系统与责任矩阵口径**：以 `v1.3.0` 动态审查主干为唯一被测对象，并同步修订 [`rule-responsibility-matrix.md`](../rules/rule-responsibility-matrix.md) 消除人工打标口径冲突；
- **梳理免专家自标精确率的验证路径（P1–P6）**：明确拆解各路径的能力边界，厘清 **P1 可公开检查的规格微基准** 与 **作者给真实 PR 主观打分** 的区别，同时如实界定 **P3/P4/P5 外部代理真值的噪声局限**；
- **完成多维定性决策矩阵（A–D）并沉淀 ADR**：记录所有者针对总路线、历史演示规则处置与单因子消融拆解、GitHub 外部代理启用范围及外部对照命题拆分（`G3a` 非 DRF 退避 vs `G3b` 真实 DRF 迁移）的四项最终裁决，固化为长期架构决策 [`ADR-0001`](../adr/0001-v14-validation-strategy.md)。

---

## 2. 范围与边界

### 做

- 新增方法论总纲与定性决策矩阵文档 [`docs/evaluation/formal-v1.4/validation-strategy.md`](../evaluation/formal-v1.4/validation-strategy.md)。
- 同步修订 [`docs/rules/rule-responsibility-matrix.md`](../rules/rule-responsibility-matrix.md)，移除 `backend_contract` 与 `breaking_impact` 中作为核心前置的“人工标注”要求，统一对齐为 P1 公开检查微基准 + P2 自动三态诊断（含 `G3a` / `G3b` 边界）+ P4（含随机行重叠机会基线）+ P5 + P3 外部代理证据链。
- 新增长期架构决策记录 [`docs/adr/0001-v14-validation-strategy.md`](../adr/0001-v14-validation-strategy.md) 并更新 [`docs/adr/README.md`](../adr/README.md) 索引，完整承接定性决策矩阵（A–D）、单因子消融拆解（`G0` / `G1` / `G2a` / `G2b`）以及外部双层对照命题（`G3a: saleor/saleor` 非 DRF 退避 + `G3b`: Task `033` 待选真实 DRF 仓库迁移）。
- 同步修正 `docs/evaluation/formal-v1.4/` 下 [`README.md`](../evaluation/formal-v1.4/README.md)、[`protocol.md`](../evaluation/formal-v1.4/protocol.md) 与 [`annotation-guide.md`](../evaluation/formal-v1.4/annotation-guide.md) 中的 `Stage 03–07`、`dataset_cli`、历史 5 条混算、“强制每 PR 单人手标”与 `Saleor` 非同栈误述。
- 将已合入 `main`（PR `#31`）的 [`031-formal-eval-pipeline.md`](031-formal-eval-pipeline.md) 状态更新为 `Accepted`，并在 [`docs/tasks/README.md`](README.md) 与 [`v1.4-entry.md`](v1.4-entry.md) 登记本任务并推进下一可用编号至 `033`。

### 不做

- 不在本任务中预设定量样本条数上限、随机抽样具体时间窗口、数值校准权重或精确率数值阈值。
- 不修改 `backend/`、`frontend/` 运行源码，不调整 [`rule-registry.json`](../../backend/data/rules/rule-registry.json) 规则生命周期、`DEFAULT_CONFIG`、`PRESETS` 数值或 [`exclusion-list.json`](../evaluation/formal-v1.4/exclusion-list.json)。
- 不在当前分支运行实际 GitHub PR 在线拉取，也不回写修改 `docs/versions/` 下已冻结历史版本归档。

---

## 3. 技术方案与契约设计

### 3.1 最新系统基准与“有效性”四层定性框架

在 [`validation-strategy.md`](../evaluation/formal-v1.4/validation-strategy.md) 第 1 节锚定最新 `v1.3.0` 被测系统形态（面向 Git `base...head` 变更快照的 `analyze_branches` 动态引擎，产出 `stage08.branch-report.v1`，内置 5 套配置预设、`config.snapshot.v1` + **SHA-256 十六进制摘要截断前 16 位 `config_digest`**、`RULE_PARAM_SCHEMAS` 内部参数以及 `AnalysisSnapshotCache` 三级缓存局部重跑能力）。

同时明确 Prisk 定位为**确定性静态风险初筛与复核优先级分诊系统**，不声称“命中 = 必然线上 Bug”或“分值 = 缺陷概率百分比”，将“证明有效性”拆解为四个待检验闭环命题：
1. **L1 检测器实现忠实性**：规则在 AST/Diff 语义层面忠实执行可公开检查的卡片正反定义与误报边界；
2. **L2 噪点收敛与覆盖诚实性**：真实仓大样本下高频规则噪点收敛情况，以及缺少上下文或基类时诚实落入 `Unanalyzed`（及明确原因码）；
3. **L3 系统级排序与 Gatekeeper 效度（待检验命题）**：**将要检验**高分及独立开启 `gatekeeper_lift` 抬升组是否优先对应第三方真实维护者审校阻力（含超越基于体积的随机行重叠机会基线的行级批注对齐）与已知高危案例，且在优先排序表现上是否优于纯修改行数规模基线及历史演示规则；
4. **L4 跨项目双层边界与配置可复现性**：
   - `L4-a`（非 DRF 退避与通用适用性）：在大型 Django + GraphQL-only 非 DRF 仓（`G3a: saleor/saleor`）上检验通用规则适用性，以及 DRF 专属规则遇到非 DRF 代码时诚实退避为 `Unanalyzed` 而不误报；
   - `L4-b`（真实 DRF 同栈契约迁移）与溯源：另行筛选真实采用 DRF 的外部仓库（`G3b`，仓名由 Task `033` 确立）专测 `backend_contract` 契约跨仓迁移性，并验证 `config.snapshot.v1` 复现一致性。

### 3.2 《规则责任矩阵》同步与阵营剔除边界

依据同步更新后的 [`rule-responsibility-matrix.md`](../rules/rule-responsibility-matrix.md)，严格划分运行时 **29 条规则 + 5 条未运行 `draft` 规则**的验证边界，不再将“人工标注”设为 `backend_contract` 与 `breaking_impact` 的工程前提：

| 规则类别 | 数量 | 规则范围与代表条目 | 论文与工程验证责任重点 | 在 v1.4 中的处置结论 |
| :--- | :---: | :--- | :--- | :--- |
| **`code_smell`**<br/>（文献继承类） | 9 条 | `swallowed_exception`、`bare_exception`、`dynamic_execution`、`hardcoded_secret`、`unmanaged_open`、`deep_control_flow`、`global_mutable_state`、`mutable_default_argument`、`assert_in_production` | 危害合理性引用 CWE / OWASP / PEP / Python 官方文档；工程重点用 **P1 可公开检查微基准** 证检测器忠实性 + **P2 大样本触发分布**（含 `G3a` 跨仓通用性）证参数（`max_depth`、`min_length`）治噪收敛。 | **纳入主评估与校准** |
| **`backend_contract`**<br/>（框架契约类） | 11 条 | `drf_public_parameter_added/removed`、`django_url_pattern_changed`、`drf_viewset_action_changed`、`drf_permission_decorator_removed`、`drf_permission_policy_downgrade`（GK）、`django_raw_sql_execution`、`django_sensitive_settings_changed`、`django_csrf_exempt_added`、`drf_queryset_scope_tighten_bypassed`、`django_signal_receiver_leak` | 阐明 Django/DRF 框架约束与语境；重点用 **P1 + P2（含 `G3a` 非 DRF 退避与 `G3b` 真实 DRF 迁移）+ P4 行内批注对齐（含随机行重叠机会基线）+ P5 社区案例** 验证真实存在性、语义忠实与退避诚实性。 | **纳入主评估与校准** |
| **`breaking_impact`**<br/>（变更冲击类） | 4 条 | `workflow.test_collaboration_gap`、`data.django_destructive_migration`（GK）、`data.django_non_null_constraint_tightened`、`data.django_field_rename_without_db_column` | 协同信号仅表“复核优先级需提升”，不直接断言外部破坏；重点依托 **P1 + P2 + P5 已知迁移故障/回滚 PR + P3 系统排序与 `G2b` 单独开启 `gatekeeper_lift` 消融** 检验捕获与抬升效应。 | **纳入主评估与校准** |
| **`historical_baseline`**<br/>（历史演示规则） | 5 条 | `api.signature_changed`、`auth.permission_structure_changed`、`data.transaction_structure_changed`、`config.configuration_structure_changed`、`code.exception_structure_changed` | 非研发成果主力规则，存在粗粒度历史包袱。 | **已裁决剔除**：不进入 `v1.4.0` 单规则有效性统计与新默认权重，仅保留 `legacy_baseline` 预设供消融 `G1` 对照与向后回归测试。 |
| **`draft`**<br/>（未激活草稿） | 5 条 | `code.dead_code_after_exit`、`auth.drf_object_permission_bypass`、`auth.django_permission_module_changed`、`data.django_transaction_boundary_changed`、`workflow.large_change_scope` | 运行时不启用。 | **严格排除**：不参与运行及命中分母计算。 |

### 3.3 验证路径全景（P1–P6）与四项最终定性选型决策（`ADR-0001`）

经多方案对比矩阵（详见 [`validation-strategy.md`](../evaluation/formal-v1.4/validation-strategy.md) 第 3–4 节及 [`ADR-0001`](../adr/0001-v14-validation-strategy.md) 第 2 节），**所有者与工程评审联合校准以下四项核心决策，并明确说明取舍边界与残余局限**：

| 决策项 | 可选备选集合 | 最终选定与校准结论 | 核心选择理由、边界区分与残余噪声说明 |
| :--- | :--- | :--- | :--- |
| **DEC-1：总体有效性证明路线** | - 方案 I（纯单人全量人工精读标注精确率）<br/>- 方案 II（纯 GitHub PR 元数据黑盒对比）<br/>- **方案 III（三层混合验证与外部代理体系）**<br/>- 方案 IV（方案 III + 窄域切片规范复核） | **选定「方案 III」**（`P1 可公开检查微基准 + P2 大样本自动诊断 + P3/P4(含随机基线) GitHub 评审与行级对齐 + P5 社区公开案例`） | 1. 方案 I 面临明显的“作者自研自判真实 PR”Author Bias 与单人审计过载问题；方案 II 将 24 规则全部黑盒化；<br/>2. 方案 III **明确放弃以单一作者给真实 PR 主观标注 `hit/fp` 精确率作为实证核心支柱**，将 [`annotation-guide.md`](../evaluation/formal-v1.4/annotation-guide.md) 降级为历史格式参考，并同步改写 [`rule-responsibility-matrix.md`](../rules/rule-responsibility-matrix.md)；<br/>3. **界定两种自构证据的区别**：P1 微基准夹具虽由开发者设计，但代码输入、规则契约与三态预期**可由任何评审者公开检查与复跑**，负责证实检测器实现忠实于规格，不应为避免自标真实 PR 而一并舍弃 P1；<br/>4. **诚实界定外部代理噪声**：本文档不宣称“消灭主观与噪声”，而明确标注 **P3/P4/P5 均属有噪声、非穷尽的外部代理真值（proxy）**，在论文构造效度与外部效度中正面披露。 |
| **DEC-2：历史 5 条演示规则处置与消融隔离** | - **选项 1：直接剔除出新版评估与权重体系（仅留 `legacy_baseline` 作 G1 消融参照），且 G2 内部拆分单因子对比**<br/>- 选项 2：与 24 条精细规则混算并继续赋予新校准权重 | **选定「选项 1」（直接剔除出 `v1.4` 有效性结论与新推荐权重主体，并执行单因子消融拆解）** | 这 5 条规则属于 `v1.0.0` 粗粒度占位演示规则，既无研究规则卡片也不属于三大研究阵营；剔除后可保持新旧研究规则的清晰边界，且只保留于 `legacy_baseline` 预设里承担 `G1` 消融；同时为避免多因子混杂归因，明确把 **`G1`（历史 5 条 vs 24 条）**、**`G2a`（相同规则与 Gatekeeper 开关下调整阈值与权重）** 与 **`G2b`（相同权重与阈值下单独开关 Gatekeeper）** 拆成三道独立实验。 |
| **DEC-3：GitHub 外部代理信号范围（P3/P4/P5）** | - **选项 1：完整启用 P3 + P4（配对随机行重叠基线）+ P5**<br/>- 选项 2：仅启用 PR 级阻力（P3）<br/>- 选项 3：局部人工标注替补 P5 | **选定「选项 1」（完整启用 P3 + P4 + P5）** | 仅有 PR 级审稿拒审/往返次数（P3）颗粒度过粗；叠加 **P4 行内评审批注文件/行号位置对齐** 后，可进一步检验告警落点与维护者注视焦点的空间重合度；**为防止“改动越多巧合重叠越高”，P4 强制引入按 PR 改行/hunk 体积归一化的随机行重叠机会基线（random line-overlap chance baseline）**；叠加 **P5 社区安全/回归标签及 `Revert`/`Fixes` 关联案例**，可为稀缺权限与迁移规则提供免作者自标的正例参照（仍承认其非穷尽属性）。 |
| **DEC-4：跨项目外部对照命题拆分（G3a vs G3b）** | - 选项 A（旧案）：单选 `saleor/saleor` 并笼统当作“未定制 Django/DRF 同栈对照”<br/>- **选项 B（校准定案）：拆分为 `G3a（saleor/saleor 非 DRF 退避）` + `G3b（真实 Django+DRF 同栈契约迁移，由 Task `033` 筛选）** | **保留 `saleor/saleor` 并明确拆分为双子命题：`G3a` + `G3b`** | `saleor/saleor` 官方定位为 **GraphQL-only** 电商引擎，主 API **并非 Django REST Framework（DRF）**，而 Prisk 11 条 `backend_contract` 规则主要围绕 ViewSet、`permission_classes`、Serializer 参数等 DRF 契约构建。若将 `saleor` 写成“Django/DRF 同栈对照”，会把“通用异味跨仓适用”与“DRF 契约迁移”混为一谈——在 `saleor` 上 DRF 规则大面积 `Unanalyzed` 只能证明非 DRF 下的**诚实退避与不乱误报**。故 **G3a（`saleor/saleor`）** 专责大型 Django（GraphQL-only、非 DRF / 非 NetBox 基类）退避与通用 `code_smell` 对照；另外立 **G3b**，由 Task `033` 另行筛选真正使用 DRF 的开源项目专门验证 DRF 契约规则迁移性。 |

### 3.4 单因子消融矩阵（G0–G3b）与论文章节（RQ1–RQ4）衔接

借助 `analyze_branches` 产出的 `stage08.branch-report.v1`、`config.snapshot.v1`（**SHA-256 十六进制摘要截断前 16 位 `config_digest`**）与 `AnalysisSnapshotCache` 三级缓存重跑，确定拆解单因子对照设计并直接对接毕业论文 `RQ1–RQ4`：
- **G0（纯变更规模基线 LOC / 文件数）**：消除改动体量混淆变量，服务 `RQ3`；
- **G1（`legacy_baseline` 预设：仅历史 5 条 vs 等效基础 24 条研究规则）**：独立检验淘汰历史演示规则并引入 24 精细规则的演进增益，服务 `RQ3`；
- **G2a（相同 24 规则且相同 Gatekeeper 状态：未收紧等权配置 vs 阈值收敛与场景校准权重）**：独立剥离 P2 参数降噪与权重校准的增量，服务 `RQ1` & `RQ3`；
- **G2b（相同 24 规则、相同阈值与权重：关闭 vs 开启 `gatekeeper_lift`）**：独立隔离一票抬升机制在稀缺高危场景下的净贡献，服务 `RQ2` & `RQ3`；
- **G3a（外部退避对照：`saleor/saleor` 大型 Django GraphQL-only 非 DRF 仓）**：检验通用规则跨仓适用性与非 DRF 环境下 DRF 规则 `Unanalyzed` 诚实退避边界，服务 `RQ1` & `RQ4`；
- **G3b（外部同栈迁移对照：Task `033` 筛选真实 Django + DRF 仓库）**：独立检验 `backend_contract`（11 条）DRF 契约规则在非 NetBox 真实 DRF 代码上的可迁移性，服务 `RQ4`。

### 3.5 前序工程入口兼容性说明（留待下一落地任务 Task `033` 执行）

Task 031 交付的 [`eval_cli.py`](../../backend/prisk/cli/eval_cli.py) 当前 `aggregate` / `compare-presets` 入口仍读取批处理 `--stage05` / `--stage04` JSONL；基于本任务及 `ADR-0001` 的最终决定，下一工程任务（`033`）将直接让评估聚合引擎接入 `analyze_branches` 产出的 `stage08.branch-report.v1` 报告对象，实现 P1 公开微基准、GitHub `P3/P4（含随机行重叠机会基线）/P5` 元数据采集、确立 **G3b** 真实 DRF 外部仓与定量定标，不再依赖 `v1.0.0` 分步 CLI 串联。

---

## 4. 交付物与改动清单

| 文件路径 | 变更类型 | 说明 |
| :--- | :---: | :--- |
| `docs/adr/0001-v14-validation-strategy.md` | 新增 | **ADR-0001**：固化定性决策矩阵 A–D、P1–P6 路径边界、单因子消融拆解（`G0`/`G1`/`G2a`/`G2b`）与外部对照分拆（`G3a`/`G3b`），`Status: Accepted` |
| `docs/adr/README.md` | 修改 | 登记并索引 `ADR-0001` |
| `docs/rules/rule-responsibility-matrix.md` | 修改 | 同步修订 `backend_contract` 与 `breaking_impact` 工程验证义务及术语定义，消除前置“人工标注”冲突，对齐 `ADR-0001`（P1 公开微基准 + P2 + P4 含随机基线 + P5 + P3 与 G3a/G3b 边界） |
| `docs/evaluation/formal-v1.4/validation-strategy.md` | 新增 | `v1.4.0` 有效性证明方法论总纲、三阵营分治、P1–P6 路径、矩阵 A–D、RQ1–RQ4 映射及第 6 节定案终裁记录 |
| `docs/evaluation/formal-v1.4/README.md` | 修改 | 将 `validation-strategy.md` 与 `ADR-0001` 设为实证决策入口，反映 `G2a`/`G2b` 与 `G3a`/`G3b` 最新口径 |
| `docs/evaluation/formal-v1.4/protocol.md` | 修改 | 清除 `Stage 03–07` / `dataset_cli` / “人工手标”旧前提，统一改接 `analyze_branches`，细化 `config_digest`（SHA-256 十六进制截断前 16 位）与 `G3a`/`G3b` 双层外部对照及 P4 随机基线说明 |
| `docs/evaluation/formal-v1.4/annotation-guide.md` | 修改 | 明确降级为可选历史格式参考，厘清 24 条研究规则与 5 条历史演示规则边界 |
| `docs/tasks/032-v14-validation-strategy.md` | 新增 | Task 032 完整设计、选型依据与四项校准后最终选择详细任务记录 |
| `docs/tasks/031-formal-eval-pipeline.md` | 修改 | 同步已合入 `main`（PR `#31`）的 Task 031 状态为 `Accepted` |
| `docs/tasks/README.md` | 修改 | 更新 031、032 为 `Accepted`，推进下一可用编号至 `033` |
| `docs/tasks/v1.4-entry.md` | 修改 | 同步阶段入口任务表及 Task 032 / `ADR-0001` 研究口径对齐注记 |

---

## 5. 验证与验收

### 自动化规范与基线检查

- **沙箱内全量后端单测**：在每次仅修改 `docs/` 且代码与规则配置未改动的最终文档收尾阶段，须执行 `backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend` 核验基线（注：受限沙箱环境可能拦截本地环回端口绑定测试，需结合非沙箱确认全部 218 项测试通过）。
- **隔离清单一致性校验**：`$env:PYTHONPATH="backend"; backend/.venv/Scripts/python.exe -m prisk.cli.eval_cli sync-exclusion --check`（校验 136 条排除 PR 无交叠、退出码 `0`）。
- **前端工程基线**：`npm --prefix frontend run lint` 与 `npm --prefix frontend run typecheck`（验证前端工程基线不受影响、退出码 `0`）。
- **Diff 与相对链接规范检查**：`git diff --check`（无空白或行尾污染、退出码 `0`）以及改动 Markdown 文档站内相对链接零断链校验。

### 评审与人工验收清单

- [x] 所有者已审阅方法论口径并确认脱离 `stage03`–`stage07` 旧路线叙事、采纳方案 III、剔除 5 条历史演示规则、完整启用 `P3+P4+P5` 并保留 `saleor/saleor` 外部对照；
- [x] 已按 Engineering Lead 评审意见完成 `ADR-0001` 与全套文档定稿修正：`saleor/saleor` 精准降格/分拆为 `G3a`（Django GraphQL-only 非 DRF 退避），增设 `G3b`（Task `033` 待选真 DRF 仓迁移）；同步更新 [`rule-responsibility-matrix.md`](../rules/rule-responsibility-matrix.md)；明确 `G2a`/`G2b` 单因子拆分、`P4` 随机行重叠机会基线、`P1` 公开可查性与 `P3/P4/P5` 代理噪声披露、`L3` 待检验表述及 `config_digest` SHA-256 截断前 16 位精确措辞。

---

## 6. 已知限制与残余风险

1. **定量规模、`G3b` 选仓与采样参数仍留待 Task `033` 落地**：本任务与 `ADR-0001` 只固化方法论与定性决策结构，具体 `track_a_random` / `track_b_targeted` / `G3a (saleor/saleor)` 抽样数目、时间窗设定、初始校准权重数值以及 **真实采用 Django + DRF 的 `G3b` 外部仓库筛选定案**均待下一工程执行任务（`033`）实测确立。
2. **前序工程评估入口与基线采集待实现**：`eval_cli aggregate` / `compare-presets` 须在 Task `033` 对接 `analyze_branches` 产出的 `stage08.branch-report.v1`（及 `AnalysisSnapshotCache`），并补齐 24 条规则 P1 可公开检查微基准、GitHub Reviews（P3）、Inline Review Comments 位置及基于变更体积的 **P4 随机行重叠机会基线**、Community Labels/Rework（P5）采集脚本。
3. **`legacy_baseline` 工程保留边界**：尽管 5 条历史演示规则已决定不参与 `v1.4.0` 单规则有效性统计与新默认校准权重，[`backend/prisk/domain/config.py`](../../backend/prisk/domain/config.py) 中的 `PRESET_LEGACY_BASELINE` 与 `DEFAULT_CONFIG` 在后续显式校准迁移前仍继续保留，以保障既有历史测试与 `G1` 消融对照组可执行性。
