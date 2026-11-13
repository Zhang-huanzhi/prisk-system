# ADR-0001：v1.4.0 实证有效性证明路线、规则阵营边界与外部对照策略

| 属性 | 内容 |
| :--- | :--- |
| **编号** | ADR-0001 |
| **状态** | `Accepted` |
| **决策日期** | 2026-11-13 |
| **关联任务** | [Task 032：v1.4.0 有效性证明方案设计与定性决策矩阵](../tasks/032-v14-validation-strategy.md)（分支 `docs/032-v14-validation-strategy`） |
| **关联规范** | [`validation-strategy.md`](../evaluation/formal-v1.4/validation-strategy.md)、[`protocol.md`](../evaluation/formal-v1.4/protocol.md)、[`rule-responsibility-matrix.md`](../rules/rule-responsibility-matrix.md) |
| **影响范围** | `analyze_branches` 审查报告输出（`stage08.branch-report.v1`）、`eval_cli` 后续聚合适配、24 条研究规则 vs 5 条历史演示规则边界、`netbox-community/netbox` 主仓库、非 DRF 退避对照仓 `saleor/saleor`（G3a）与真实 DRF 迁移对照仓（G3b，待 Task `033` 筛选） |

---

## 1. 背景与问题驱动（Context）

截至 `v1.3.0` 归档，Prisk-System 已从 `v1.0.0` 早期基于 NetBox 固定目录前缀和分步批处理脚本（`dataset_cli` → `Stage 03–07`）的演示原型，演进为面向任意 Git `base...head` 变更快照的**动态变更风险审查与决策支持引擎**（`analyze_branches`）：

1. **工程基准变化**：最新主干引擎自动将所有非测试 `.py` 文件纳入业务分析，通过三态规则引擎（`Hit / NotFound / Unanalyzed` + 原因码与代码切片）、`gatekeeper_lift` 一票抬升、`config.snapshot.v1`（含 SHA-256 十六进制摘要截断前 16 位 `config_digest`）及 `AnalysisSnapshotCache` 三级局部重跑完成一体化审查并输出 `stage08.branch-report.v1`。
2. **规则体系分化**：按 [`rule-responsibility-matrix.md`](../rules/rule-responsibility-matrix.md) 与 [`rule-registry.json`](../../backend/data/rules/rule-registry.json)，运行时共 29 条规则并非均等实体——其中 **24 条 `implemented` 精细研究规则**分布在 `code_smell`（9 条）、`backend_contract`（11 条）与 `breaking_impact`（4 条）三大阵营，各自背负不同的学术与工程验证责任；另有 **5 条 `historical_baseline` 历史演示规则**（`api.signature_changed`、`auth.permission_structure_changed`、`data.transaction_structure_changed`、`config.configuration_structure_changed`、`code.exception_structure_changed`）仅用于历史回归兼容，以及 **5 条未激活 `draft` 规则**不参与运行时执行。
3. **单一作者评估可信度局限（Author Bias）**：研究工作处于单人研发与评估语境，无法雇佣多名资深第三方工程师开展双盲全量 Diff 人工审计；若继续把“作者本人精读真实 PR Diff 并主观判 `hit`/`fp` 算精确率”作为实证核心支柱，不仅与三大阵营责任分化相抵触，也会在答辩环节面临“自研自判”偏误质疑与过高人工工时门槛。
4. **外部项目技术栈区分**：先前拟议的外部仓 **`saleor/saleor`** 官方定位为 **Django + GraphQL-only** 电商引擎，并非 Django REST Framework（DRF）项目；而 Prisk 11 条 `backend_contract` 规则大部分依赖 DRF 接口与权限契约（如 `ViewSet`、`permission_classes`、Serializer 参数）。若把 `saleor/saleor` 笼统称为“DRF 同栈对照仓”，会把两件不同的命题混为一谈——DRF 规则在非 DRF 仓落入 `Unanalyzed` 只能检验“诚实退避”，不能检验 DRF 契约规则在异仓 DRF 架构上的跨项目可迁移性。

因此，必须在进入正式样本采集与权重调优实现前，通过长期架构决策（ADR）一次性锁定：**`v1.4.0` 要检验的有效性命题边界、历史规则剔除范围、免于依赖作者全量自标的证据组合路线（承认外部代理信号存在噪声）、独立拆分的单因子消融对照，以及严格分离“非 DRF 退避对照（`saleor/saleor`）”与“真实 DRF 迁移对照（待选）”的双层外部检验设计**。

---

## 2. 定性决策矩阵与备选方案评估（Decision Matrices & Options Considered）

### 2.1 六条可选验证路径的机理定位（P1–P6）

| 路径 | 核心机制 | 能够客观提供什么检验依据 | 固有盲区、噪声属性与本次决策处置 |
| :--- | :--- | :--- | :--- |
| **P1：公开可审查的受控结构微基准** | 面向 24 条 `implemented` 规则构造正例、合法反例、注释/字符串遮蔽及解析退化代码差异片段，接入 `analyze_branches` 自动化跑测。 | 检验 **检测器代码实现是否忠实于规则卡片规格定义**（L1 准确性）。**注**：P1 夹具虽由开发者设计，但其输入与预期边界完全公开、可由任何评审者独立核查并重跑，**与“作者对真实复杂 PR 主观打精确率分”有本质区别**。 | 无法反映真实复杂项目中的触发密度与背景噪点分布。<br/>**结论：核心采纳（公开可审查夹具，不因此弃用）**。 |
| **P2：大样本自动化三态与 AST 聚类诊断** | 对隔离真实 PR 快照批跑 `analyze_branches`，统计全量规则的 `Hit / NotFound / Unanalyzed` 分布及原因码，按 AST 形态/路径聚合并借助 `AnalysisSnapshotCache` 观测 `rule_thresholds` 收敛前后变化。 | 客观测量高噪饱和情况、稀缺规则出现频次及 `Unanalyzed` 退避边界（L2），无需人工主观测评词名/写法对错。 | 仅反映触发分布与结构聚类，不能直接判定单次 Hit 是否对应真实审查聚焦。<br/>**结论：核心采纳**。 |
| **P3：GitHub 第三方历史评审阻力代理信号** | 抽取原仓维护者当年留下的 `CHANGES_REQUESTED`、Review 往返轮次与评论密度；严格隔离未来审查记录，仅用 PR 代码快照运行 Prisk，对照风险分/等级的分组差异。 | 以**原仓库维护团队当年工程注意力投入**作为独立外部代理真值（proxy），用于**检验**系统排序相对纯规模基线及历史基线是否更具审查区分力（L3 待检验命题）。 | **属于有噪声的代理真值**：PR 被打回可能源于需求争议或风格意见，且人类审稿人也会漏看部分静态风险。<br/>**结论：核心采纳（严守代理信号边界）**。 |
| **P4：GitHub 行内评审批注位置对齐（含随机基线对照）** | 将原仓人类维护者在 Review 中发表的 Inline Review Comments（文件 + Diff hunk / 附近行窗口）与 Prisk Finding 证据坐标作空间交集匹配，**并强制相对于“按同文件/Hunk 改动体积均匀抽样的随机行重叠期望（chance baseline）”作对比检验**。 | 在局部代码行级粒度检验 Prisk 定位是否**高于随机重合巧合概率**地接近人类审稿焦点，弥补 PR 级粗粒度代理信号盲区。 | 不同仓行内评论习惯有差异；引入随机行重叠基线可防止“只因改动大/评论多造成的虚假对齐”。<br/>**结论：完整启用（强制配合随机机会基线）**。 |
| **P5：社区公开风险标签与合入后返工追踪** | 采集带有仓库维护者共识印记（`security`、`bug`、`regression`、`breaking change`、`migration`）或后续触发 `Revert` / `Fixes #...` 的原 PR 引入快照，与常规 PR 对照。 | 为 `backend_contract` 与 `breaking_impact` 等低频高危规则（含 `gatekeeper_lift`）提供**第三方真实正例对照集**（L3 待检验命题）。 | **呈非穷尽性代理特征**：未被打标或未立即回滚的 PR 并不等同于零缺陷负例。<br/>**结论：完整启用（仅作正例参考，不假定未打标为绝对负例）**。 |
| **P6：单人全量人工核验真实 PR vs 窄域规范切片检查** | 由作者通读真实 PR Diff 按四值词表打分（重标注），或仅对 P2 异常聚合做切片人工核对。 | 在无独立双盲第三方专家审阅组的情况下，全量自标精确率难以令评委区分真实准度与作者偏袒（Author Bias）。 | **结论：不纳入方案 III 主证明路线**（`annotation-guide.md` 降级为历史/可选格式参考；注意这**不否定 P1 公开夹具检查**）。 |

### 2.2 矩阵 A：总体实证路线组合定性对比矩阵

| 评估维度 | 方案 I：单人全量人工核验路线 | 方案 II：纯 GitHub PR 级代理黑盒对比 | **方案 III（最终选定）：三层客观混合与外部代理体系**<br/>`P1 公开微基准 + P2 自动三态诊断 + P3/P4(含随机基线) + P5 社区案例` | 方案 IV：方案 III + 窄域切片辅助人工复核 |
| :--- | :--- | :--- | :--- | :--- |
| **证明链分工** | 作者通读真实 Diff 标 `hit / fp` 算精确率。 | 弃用单规则检视，仅算总分与 `changes_requested` 相关性。 | **规则规格忠实度靠可公开审查的 P1，大样本噪点与覆盖诚实性靠 P2，系统排序与局部定位对齐靠第三方历史代理 P3/P4/P5。** | 方案 III 上额外对少量 P2 异常切片附加机械规范复核清单。 |
| **规避单人自标偏误（Author Bias）** | **弱**：作者自研自判真实 PR 精确率，无双盲交叉检验支撑。 | **强（系统层）/ 极弱（规则层）**：无法解释 24 条 AST 检测器实现是否忠实。 | **较强（非“零主观”）**：规避了作者给真实 PR 主观打“对/错”的确认偏误；同时坦承 **P3/P4/P5 代理真值存在固有噪声，P1 夹具依赖公开可审查性保障公信力**。 | **较强（须严控 P6 仅作诊断）**：仍存在审稿人追问局部切片一致性的风险。 |
| **个人业务审计能力依赖** | **极高**：复杂跨模块开源 Diff 极易误判。 | **低**：统计由程序与公开元数据驱动。 | **低**：P1 基于明确语言/框架语法规格；P2–P5 基于静态统计与仓库历史事件。 | **中低**：需人工判读极少量异常切片。 |
| **与《规则责任矩阵》贴合度** | **差**：对三大阵营一刀切。 | **差**：把不同责任阵营压扁为黑盒总分。 | **高**：文献类重 P1+P2；框架契约与变更冲击类重 P1+P2+P4+P5+跨仓边界；系统优先级检验靠 P3/P4/P5。 | **高**。 |
| **工程实施重点** | **差（工时高压）**。 | **良**。 | 增量投入集中于完善 P1 公开夹具、`eval_cli` 对接 `stage08.branch-report.v1`、抓取 P3/P4/P5 元数据与实现随机行重叠基线。 | 与方案 III 相近，略增局部复核清单整理。 |
| **ADR 裁决结果** | **否决** | **否决** | **采纳（最终选择）** | **暂不采纳**（坚持不引入真实 PR 人工打分支柱；同步保留 P1 公开微基准） |

### 2.3 矩阵 B：三大规则阵营 × 验证路径 × 检验目标矩阵

| 评估对象 | 规则数量与名单范围 | 将要检验的研究命题与工程任务 | 选定验证路径 | 外部参照与控制基线 | 明确不主张的边界 |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **`code_smell`**<br/>（文献继承类） | **9 条 `implemented`**<br/>(`swallowed_exception`、`bare_exception`、`dynamic_execution`、`hardcoded_secret`、`unmanaged_open`、`deep_control_flow`、`global_mutable_state`、`mutable_default_argument`、`assert_in_production`) | 1. 检验 AST/Diff 检测器是否严格符合公开可审查的正反边界微基准；<br/>2. 检验真实大样本下的触发分布与 `rule_thresholds` 收紧前后降噪幅度；<br/>3. 在非 NetBox 仓验证通用 Python 规则跨仓适用性。 | **P1 + P2（含 G3a `saleor`） + P4（辅助）** | - 危害文献依据：CWE / OWASP / PEP / Python 官方文档；<br/>- 实现检验：P1 公开微基准集 + P2 大样本触发聚类。 | 不单独声称任一编码异味必然导致线上事故或 PR 被拒。 |
| **`backend_contract`**<br/>（框架契约类） | **11 条 `implemented`**<br/>(`drf_public_parameter_added/removed`、`django_url_pattern_changed`、`drf_viewset_action_changed`、`drf_permission_decorator_removed`、`drf_permission_policy_downgrade`[GK]、`django_raw_sql_execution`、`django_sensitive_settings_changed`、`django_csrf_exempt_added`、`drf_queryset_scope_tighten_bypassed`、`django_signal_receiver_leak`) | 1. 检验规则在 NetBox 真实演化中的存在性与触发结构；<br/>2. **G3a（`saleor/saleor`，Django GraphQL-only 非 DRF 仓）**：检验 DRF 专属规则在非 DRF 仓是否**诚实退避为 `Unanalyzed` 或不误报**（不作为 DRF 迁移性证明）；<br/>3. **G3b（待 Task `033` 筛选的真实 DRF 项目）**：检验 DRF 契约规则在另一个 DRF 项目上的跨仓迁移与命中能力；<br/>4. 检验关键发现与行内批注焦点及社区风险案例的对齐倾向。 | **P1 + P2（G3a + G3b 分列） + P4 + P5** | - 契约规范：Django/DRF 官方文档与 P1 契约正反夹具；<br/>- 现实代理：维护者行内批注（相对随机行重叠基线）、社区标签/返工案例。 | 不宣称纯静态匹配可穷尽动态中间件或运行时权限绕过。 |
| **`breaking_impact`**<br/>（变更冲击类） | **4 条 `implemented`**<br/>(`test_collaboration_gap`、`django_destructive_migration`[GK]、`django_non_null_constraint_tightened`、`django_field_rename_without_db_column`) | 1. 检验高危迁移在社区已知破坏/回滚样本中的捕获情况与 `gatekeeper_lift` 独立开启增益；<br/>2. 检验协同缺失与破坏冲击信号在不同配置权重下的排序区分变化。 | **P1 + P2 + P5 + P3（系统层）** | - 破坏参照：带迁移故障、`Revert`、`breaking` 印记的真实 PR；<br/>- 排序对照：P3 评审阻力与 G2a/G2b 消融组。 | 不将 `workflow.test_collaboration_gap` 直接等同于“代码必有 Bug”。 |
| **系统综合排序与 Gatekeeper** | 以上 **24 条研究规则**（**剔除 5 条历史演示规则及 5 条 `draft` 规则**） | **核心待检验命题（L3）**：检验综合分诊等级与 `gatekeeper_lift` 是否相较纯变更规模基线（G0）及历史基线（G1），更常把审查注意力优先引导向客观阻力更高、行内讨论更集中及含已知风险返工的 PR。 | **P3 + P4（含随机基线） + P5 + 多配置单刀消融** | 原仓维护者的 `changes_requested`、Review 轮次、归一化行内批注重合度及社区返工标签。 | 不替代 CI/测试或人类维护者终审合入；分值不是 Bug 概率预测，代理指标噪声将诚实报告。 |

### 2.4 矩阵 C：单因子消融对照与双层外部仓矩阵（G0–G3b）

依托 `analyze_branches` 的 `config.snapshot.v1`（`config_digest`）及 `AnalysisSnapshotCache` 三级缓存局部重跑机制，**每个实验组严格只变动单个被测因子**，禁止多因子打包混淆归因：

| 对照实验组 | 单一变动因子与设计实质 | 严格控制不变量 | 要独立回答的科学问题 |
| :--- | :--- | :--- | :--- |
| **G0：纯变更规模基线** | 仅按 PR 新增+删除代码行（LOC）或变更非测试 Python 文件数排序。 | 相同真实 PR 快照与 P3/P4/P5 外部代理指标。 | **剥离规模混淆**：检验系统分诊效果是否仅仅等价于“改动越多分越高”。 |
| **G1：`legacy_baseline` 历史规则基线** | 仅计分历史 5 条演示规则（+1 分协同），24 条精细规则权重置 0。 | 相同 PR 快照与缓存 AST/Diff（仅切配置快照）。 | **独立隔离历史规则剥离与精细规则演进效应**：对比 `v1.4` 24 规则体系与 `v1.0` 5 条演示规则的分辨能力跃升。 |
| **G2a：参数阈值与场景权重调优消融** | 在同样仅用 24 规则且保持同一 Gatekeeper 开关的前提下，比较未收紧初始阈值/等权配置 vs 经 P2 收紧 `rule_thresholds` 及场景权重校准配置。 | 相同的 24 规则集、相同 Gatekeeper 状态与相同 PR 快照（固化各自 `config_digest`）。 | **独立剥离参数治噪与权重校准的增量贡献**（不与历史规则剥离或 Gatekeeper 混算）。 |
| **G2b：Gatekeeper 开关单刀消融** | 在**完全相同的 24 规则权重与内部参数阈值**下，**仅单独对比开启 vs 关闭 `gatekeeper_lift`**（`data.django_destructive_migration` 与 `auth.drf_permission_policy_downgrade` 一票抬升）。 | 相同的 24 规则权重、`rule_thresholds` 与 PR 快照（仅切换 Gatekeeper 机制开关）。 | **独立验证 `gatekeeper_lift` 机制的净贡献**：观测在低分值小体积 PR 中拦截高危变更的单独增量效果。 |
| **G3a：非 DRF / 非 NetBox 退避对照（`saleor/saleor`）** | 选定大型开源 **Django + GraphQL-only** 项目 **`saleor/saleor`**（主 API 非 DRF），零定制适配接入 `analyze_branches`。 | 相同系统代码、相同通用非测试 `.py` 业务分类与相同预设。 | **严守命题边界**：1) 检验通用 Python 异味（`code_smell`）与 Django 层信号在大型异仓的适用性；2) 检验 DRF 专属规则在非 DRF 环境下是否**诚实退避为 `Unanalyzed` 而不误触发**（不夸大为 DRF 迁移验证）。 |
| **G3b：真实 Django + DRF 同栈迁移对照（待 Task `033` 选定）** | 在 Task `033` 经依赖与代码模式筛查后，另选真正广泛使用 **DRF**（`ViewSet`/`APIView`/`Serializer`/`permission_classes`）的独立开源项目接入 `analyze_branches`（若涉及未列入映射的自定义基类，同步观察其 `Unanalyzed` 边界）。 | 相同系统代码与通用业务文件分类策略。 | **专门检验 DRF 框架契约跨仓可迁移性**：与 G3a 解耦，正面检验 11 条 `backend_contract` 规则在 NetBox 之外真实 DRF 代码上的命中与语义契约表现。 |

### 2.5 矩阵 D：Threats to Validity 预置学术应对策略

| 威胁类型 | 论文预置克制应对边界 |
| :--- | :--- |
| **构造效度（Construct Validity）** | 1. 明确系统定位为“确定性静态变更风险初筛与复核优先级分诊”，非“线上缺陷概率预测”；<br/>2. **坦承代理真值噪声**：`CHANGES_REQUESTED`、Review 轮次、Inline Review Comments 与社区 `bug`/`security` 标签均为不完全且有噪声的工程代理信号（proxy），存在人类审稿疏漏与非安全性争议噪音；`P4` 强制对照同规模改动下的**随机行重叠机会基线**以过滤偶然重合，社区未打标样本绝不当作零缺陷绝对负例。 |
| **内部效度（Internal Validity）** | 1. **不以单作者真实 PR 主观打分当核心支柱**，规避“作者自证自高”的确认偏误；<br/>2. `P1` 微基准夹具虽系按规格构造，但正反边界源码与预期结局全部公开透明、接受任何人检查和独立重跑，用于证明实现忠实性而非冒充真实仓库自然精准率；<br/>3. 通过 `G1`、`G2a`、`G2b` 各自单因子切分消融，避免多变量混绑导致无法归因。 |
| **外部效度（External Validity）** | 1. 研究对象明确限定于 Python 后端与 Django/DRF 生态；<br/>2. **拒绝用 `saleor/saleor` 冒充 DRF 同栈迁移证明**：将 **`saleor/saleor`（G3a）严格界定为“大型 Django / GraphQL-only 非 DRF 退避与通用规则检验仓”**，而将 DRF 契约规则跨仓迁移性交由 **G3b（真实使用 DRF 的独立对照仓）** 独立检验。 |
| **可靠性（Reliability）** | 通过 `exclusion-list.json`（136 条历史 NetBox PR 零交叠）与 `eval_cli check-isolation` 杜绝调研集/先导集数据泄露；通过 `config.snapshot.v1` 固化每个运行配置及 **SHA-256 十六进制摘要截断前 16 位 `config_digest`**，保证跨配置对照完全可追溯复现。 |

---

## 3. 正式裁决结论（Decision）

经所有者与工程审阅在 Task 032 共同定案，**正式确立以下四项长期实证与工程边界裁决**：

1. **【D1】总体实证路线选择「方案 III」（三层客观混合与外部代理体系）**：
   - 确立 **`P1 公开可审查微基准 + P2 大样本自动化三态与 AST 聚类诊断 + P3/P4（强制带随机行重叠机会基线）+ P5 社区公开风险标签与返工案例`** 作为 `v1.4.0` 实证框架；同时同步更新 [`rule-responsibility-matrix.md`](../rules/rule-responsibility-matrix.md)，使之不再要求以人工标注为 `backend_contract`/`breaking_impact` 的前提真值。
   - 不以单一作者给真实复杂 PR 逐条主观标 `hit`/`fp` 作为核心精度真值支柱（[`annotation-guide.md`](../evaluation/formal-v1.4/annotation-guide.md) 保留为历史/可选格式参考）；同时保留公开可审、可重跑的 P1 夹具检验规格忠实度，并在论文中诚实界定代理真值噪声。
2. **【D2】直接剔除 5 条历史演示规则出新版评估与默认权重体系，并严格拆解 G2a / G2b 单因子消融**：
   - 5 条 `historical_baseline` 规则不纳入 `v1.4.0` 规则阵营统计、单规则有效性结论或新版推荐权重主体；`legacy_baseline` 预设仅保留用于 `G1` 系统基线消融与历史回归测试；5 条 `draft` 规则继续排除。
   - **G2a（参数治噪与场景权重）** 与 **G2b（Gatekeeper 开关单刀消融）** 拆开执行，不与历史规则剥离混捆。
3. **【D3】完整启用 GitHub 行内批注位置对齐（P4，带随机行重叠机会基线）与社区风险案例追踪（P5）**：
   - 后续采样同步提取 P3（PR 级评审阻力）、P4（Inline Review Comments 位置及同改动体积随机行重叠基线）与 P5（社区风险标签与 `Revert`/`Fixes` 关联案例）。
4. **【D4】外部对照分层为 G3a（`saleor/saleor` 非 DRF 退避与通用规则检验）与 G3b（待 Task `033` 选定的真实 DRF 同栈迁移检验）**：
   - **G3a**：正式确认选用 **`saleor/saleor`** 作为大型 **Django + GraphQL-only（非 DRF / 非 NetBox 定制基类）** 对照仓，检验通用 Python 规则跨仓运行及 DRF 规则在非 DRF 环境下的诚实 `Unanalyzed`/无误报退避表现，**不再错误描述为 DRF 同栈对照**。
   - **G3b**：授权在后续工程 Task `033` 另行筛选真正使用 **Django + DRF** 的独立开源对照项目，专门检验 `backend_contract` 契约规则跨仓迁移能力。

---

## 4. 后果与工程影响（Consequences）

### 4.1 架构与数据契约影响
- **脱离旧批处理路径**：`v1.4.0` 正式实证评估不再以 `v1.0.0` `dataset_cli` → `Stage 03–07` 为主运行路径；Task `033` 须在工程侧将 `eval_cli aggregate` / `compare-presets` 适配为直接消费 `analyze_branches` 产出的 `stage08.branch-report.v1` 报告对象（及 `AnalysisSnapshotCache`），并落地 P1 微基准、P3/P4（含随机行重叠机会基线）/P5 采集及 `G2a`/`G2b`/`G3a`/`G3b` 对照支持。
- **隔离与筛选门禁**：`netbox-community/netbox` 仍须严格经 [`exclusion-list.json`](../evaluation/formal-v1.4/exclusion-list.json) 排除 136 条历史 PR；`G3a`（`saleor/saleor`）与 `G3b`（待选真实 DRF 仓）按同等 bot 与发布过滤条件采样，且统计严格分列不混算。

### 4.2 权重校准与配置演进约束
- 在后续权重校准产出推荐预设的任务中，**推荐新配置应仅以 24 条 `implemented` 研究规则为主体，剔除 5 条 `historical_baseline` 演示规则**；`PRESET_LEGACY_BASELINE` 仅在历史兼容回归和 `G1` 消融组中显式调用。

### 4.3 残余边界
- 本 ADR 确立**定性方法论、证据结构、单因子消融拆解与双层外部仓定位**；具体抽样数量、时间窗口、GitHub API 限流细节、G3b 真实 DRF 仓库最终提名与校准权重参数值均留待 Task `033` 及后续实证任务确立，本决策记录不提前虚构任何未实测数值。
