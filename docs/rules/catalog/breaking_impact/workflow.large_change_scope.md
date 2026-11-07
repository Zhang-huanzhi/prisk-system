# 规则说明卡片：`workflow.large_change_scope`

> 本卡片同时服务于工程登记和毕业论文写作。没有证据的内容填写“待验证”，不要用推测替代结果。生命周期保持 `draft`：没有检测器。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `workflow.large_change_scope` |
| 规则名称 | 大规模变更范围 |
| 版本 | `v1` |
| 规则阵营 | `breaking_impact` |
| 生命周期 | `draft` |
| 负责人 | `Prisk-System` |

卡片与登记册的生命周期都是 `draft`。严重度与风险性质的现行值见下一节。后续算法阶段可以修订。这不是终局，也不表示 v1.1.0 已经完成。

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | 跨语言 PR。模块映射和排除规则由项目配置。阈值当前都未指定 |
| 依赖层级 | `process`。阵营是变更冲击；依赖的是 Diff 计数和项目模块映射，不是外部 API 合同 |
| 分析目标层 | `change_metadata`，`diff_delta` |
| 证据呈现形态 | `metric_value`，`code_slice` |
| 严重度 | `High` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度 `High` 与风险性质 `pr_intrinsic` 是 015 的临时判断，卡片和登记册使用同一对值。登记册 `definition.impact_type` 是 `pr_intrinsic_risk`。严重度仍是待验证的设计值，不是权重。一票抬升是 `false`，条件是 `null`。

## 3. 为什么制定

### 观察到的工程问题

一次审查要读的变更行、文件或模块很多时，理解和复核会更困难。计数可以提醒范围，计数不是实际影响半径、变更熵或缺陷概率。

### 为什么值得检测

大规模机械替换、自动生成代码和格式化会放大计数，也可能承载真实变更。审查者需要同时看到原始总计、过滤后计数和各类文件的贡献，而不是一个没有阈值的 Finding。

### 现有规则为什么不能覆盖

[`workflow.test_collaboration_gap`](workflow.test_collaboration_gap.md) 只看生产路径有没有伴随测试路径变化，不数模块，也不使用行数阈值。破坏性迁移等其他规则不因本规则的排除配置而关闭。

### 研究或工程价值

变更规模类的通用规则。文献支持把审查范围当作研究对象。文献不提供本项目的行数或模块阈值。

## 4. 检测定义

- **检测对象**：同一次三点 Diff 的行数、文件数和已分类文件所属模块数。比较单位是这一次 Diff，不是单个 AST 节点。
- **触发条件**：完整输入且相关项目阈值已配置时，`changed_lines >= lines_threshold`、`files_changed >= files_threshold`、`modules_changed >= modules_threshold` 任一成立则提示，并报告具体超限项。模块阈值仅在映射完整时参与。三个阈值和模块映射都还没有，因此现在不能产生 Hit，也不能把较小的 diff 记成 NotFound。
- **触发特征**：`changed_lines`（`source` 为新增行加删除行；`value_type` 为 `integer`；`operator` 为 `gte`；`threshold` 待确定；`required` 为 true）。`files_changed`（`source` 为去重后的文件数；`value_type` 为 `integer`；`operator` 为 `gte`；`threshold` 待确定；`required` 为 true）。`modules_changed`（`source` 为映射后的去重模块数；`value_type` 为 `integer`；`operator` 为 `gte`；`threshold` 待确定；`required` 为 true）。文件重命名计一次。二进制文件无行数时单独标明。
- **不触发条件**：可用指标均低于已配置阈值。阈值未配置、Diff 不完整或模块映射不可用时，该指标标记未评估；所有指标均未评估时规则标记未分析。自动生成文件、锁文件、`fixtures/`、`migrations/` 和纯重命名是否排除，由项目显式配置并记录，默认不排除。
- **输入**：完整 Diff、文件状态、模块映射和阈值配置。
- **Finding**：各计数、阈值、文件或模块清单、排除项与未评估项，严重度 `High`，影响类型 `pr_intrinsic_risk`。没有调用关系时不推断传播路径。阈值缺失时不生成 Finding。
- **证据位置**：计数、阈值和文件清单。
- **上下文切片**：贡献最大的文件路径及其行数。不附带整个 Diff。
- **影响类型**：该 PR 自身的变更规模。`breaking_impact` 是登记阵营，不表示已证实破坏。

示例：某项目明确配置文件阈值为 10，完整 Diff 命中 12 个计入文件时触发；同样配置下仅 2 个文件且其他可用指标均未超限时不触发。此数值只解释条件，不是推荐阈值，也不是 200 行或 3 个模块。

011 的结构可行性把本规则列为延后。详见 [结构可行性筛选](../../structural-feasibility.md)。

## 5. 理论与项目依据

- Hassan, A. E. (2009). *Predicting faults using the complexity of code changes*. ICSE. [DOI: 10.1109/ICSE.2009.5070510](https://doi.org/10.1109/ICSE.2009.5070510)。论文研究过程复杂度指标与故障预测。历史 Change Entropy 不等于单个 PR 的模块数或行数。核对范围：Crossref 书目与 OpenAlex 摘要。
- Sadowski, C., Söderberg, E., Church, L., Sipko, M., & Bacchelli, A. (2018). *Modern code review: a case study at Google*. ICSE-SEIP. [DOI: 10.1145/3183519.3183525](https://doi.org/10.1145/3183519.3183525)。摘要支持把审查过程作为研究场景，不能从摘要推出通用的 200 行阈值。核对范围：书目与摘要。

## 6. 限制与反例

- 可能误报：大规模机械替换、fixtures、格式化、迁移文件和生成文件可能由少数文件主导行数，并不必然反映业务逻辑复杂度。这些文件也可能承载真实风险。
- 可能漏报：小规模但影响核心调用的变更。模块数取决于项目映射。
- Python 动态特性限制：动态调用和跨仓库影响不在计数里。本规则不解析调用图。
- 规则不判断：真实爆炸半径、历史变更熵、缺陷、回滚或风险概率。
- 必须人工复核的上下文：变更性质、模块关系和部署上下文。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `empirical_required` |
| 验证方法 | 先构造行数、文件、模块、重命名、二进制、fixtures、迁移、排除项、未配置阈值和不完整 Diff 样例；再以冻结 NetBox PR 的人工标注报告计数分布、阈值敏感性和排序效果 |
| 数据集 | NetBox 冻结数据集仍待圈定到具体 PR |
| 判定依据 | 人工标注。维护者评论或标签只可作为待核实的弱线索，补测请求不能直接证明变更规模过大 |
| 指标 | 命中频次、阈值敏感性、人工复核排序相关性。不预填 |
| 验收标准 | 阈值和模块映射写明之前不能产生运行 Finding。`>=3` 模块、200 行和任何效果值均未确定 |
| 未解决问题 | 三个阈值和模块映射都没有。没有检测器。严重度 `High` 与风险性质 `pr_intrinsic` 是临时判断，后续算法阶段可以修订。这不是终局 |
