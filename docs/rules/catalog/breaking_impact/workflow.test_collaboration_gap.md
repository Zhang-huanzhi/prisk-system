# 规则说明卡片：`workflow.test_collaboration_gap`

> 本卡片同时服务于工程登记和毕业论文写作。没有证据的内容填写“待验证”，不要用推测替代结果。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `workflow.test_collaboration_gap` |
| 规则名称 | 业务变更缺少测试协同 |
| 版本 | `v1` |
| 规则阵营 | `breaking_impact` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

登记册 `lifecycle` 也是 `implemented`。这表示 007 已接入检测器，并用构造样例检查过路径分类。它不是 `validated`。014 不改这个字段，也不改路径分类。

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | 使用仓库内默认路径分类的变更。生产代码后缀为 `.py`、`.pyi`、`.js`、`.jsx`、`.ts`、`.tsx`；其他路径在无法归类时未分析 |
| 依赖层级 | `process`。阵营是变更冲击；依赖的是路径分类和文件状态，不是 AST 节点 |
| 分析目标层 | `change_metadata`，`diff_delta` |
| 证据呈现形态 | `metric_value` |
| 严重度 | `Medium` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

设计值待验证，不是权重。纯删除不自动降低严重度。

## 3. 为什么制定

### 观察到的工程问题

生产代码变化有时需要同步维护测试。同一 PR 里只有生产路径变化、没有测试路径变化时，审查者需要核对测试是否仍充分。

### 为什么值得检测

此规则只观察同一 PR 的路径变化。单独维护测试的仓库、现有测试已覆盖或无需调整测试时也可能命中。提示不是缺陷结论。

### 现有规则为什么不能覆盖

[`workflow.large_change_scope`](workflow.large_change_scope.md) 讨论行数、文件数和模块数阈值，那些阈值还没有。本规则不使用行数阈值，也不把「没有测试文件变化」写成测试缺失已经证实。

### 研究或工程价值

过程协同类规则。文献支持生产代码与测试代码的共同演化是研究对象。文献不能把单个 PR 未改测试判成缺陷。

## 4. 检测定义

- **检测对象**：项目配置分类后的 PR 文件变化，包含新增、修改、重命名和删除。重命名须同时检查前后路径。比较单位是同一次变更里的文件路径分类，不是单个 AST 节点。
- **触发条件**：差异完整且路径分类规则可用，至少一个生产代码文件发生新增、修改或删除，且该 PR 没有任何测试文件发生新增、修改、删除或重命名。纯生产代码路径重命名默认不视作生产内容变化。
- **触发特征**：`production_files_changed`（`source` 为默认分类下有行数证据的生产代码内容变动文件数；`value_type` 为 `integer`；`operator` 为 `gte`；`threshold` 为 `1`；`required` 为 true）。`test_files_changed`（`source` 为测试路径上新增、修改、删除或重命名的文件数；`value_type` 为 `integer`；`operator` 为 `eq`；`threshold` 为 `0`；`required` 为 true）。`diff_complete`（`source` 为每条参与判断的文件都有状态，且生产代码内容判断所需的新增/删除行数可用；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true）。分类或统计不完整时不把 `diff_complete` 当成 true。
- **不触发条件**：没有生产代码变化，或至少一个测试文件发生变化。缺少完整 Diff、分类配置或无法判断时标记未分析，不当作未命中。
- **输入**：三点 Diff、分类规则、文件状态。检测器在 `backend/prisk/domain/test_collaboration.py`，由 `evaluate_rules` 调用。它不读取 JSON 登记册。
- **Finding**：生产路径、测试变化计数为 0、分类配置和统计范围，严重度 `Medium`，影响类型 `pr_intrinsic_risk`。额外记录 `production_additions` 和 `production_deletions`。生产代码新增行数为 0 且删除行数大于 0 时，`change_boundary` 为 `code_removal`，仍按上述条件提示，严重度不因此降低。
- **证据位置**：生产路径列表、测试变化计数、分类配置名。
- **上下文切片**：测试路径列表、外部测试来源及无法分类项。
- **影响类型**：过程协同。`breaking_impact` 是登记阵营，不表示已证实外部破坏。

默认路径策略 `default_source_and_test_directories` 固定在源码中：

- 测试：路径段 `test` 或 `tests`，或 Python 文件名 `test_*.py` / `*_test.py`（含 `.pyi`）。这与 stage03 的 `classify_path` 测试约定一致，因此覆盖 `backend/tests`。
- 非生产：`doc` / `docs`、`.md` / `.rst`、`migration` / `migrations`、`generated`、`static`，以及 `settings.py`、`configuration*.py` 和 `config` / `settings` / `configuration` 路径段。
- 生产：其余 `.py`、`.pyi`、`.js`、`.jsx`、`.ts`、`.tsx`。
- 其他路径为未知。

纯重命名或复制在新增行数和删除行数都为 0 时不是生产内容变化。测试路径上的重命名仍然算测试文件变化。没有文件状态、新增/删除行数或 `binary` 字段的 stage04 记录不进入文件变更通道。此时不产生 Finding，也不把历史协作分记上。摘要计数和文件列表不一致时，原因是 `diff_stats_unavailable`。路径无法分类时，原因是 `path_classification_unavailable`。规则未启用时，不因为未知路径写入未分析。

文件通道完整，且没有「生产内容变化并且没有测试路径变化」时，运行终态是 NotFound。分类或统计不完整是 Unanalyzed，不是 NotFound。

示例：修改 `src/order.py` 且没有任何测试文件变化，分类和行数都完整时触发；同一个 PR 同时修改 `src/order.py` 和 `tests/test_order.py` 时不触发。仅修改文档时不触发。

## 5. 理论与项目依据

- Zaidman, A., Van Rompaey, B., van Deursen, A., & Demeyer, S. (2011). *Studying the co-evolution of production and test code in open source and industrial developer test processes through repository mining*. Empirical Software Engineering, 16, 325–364. [DOI: 10.1007/s10664-010-9143-7](https://doi.org/10.1007/s10664-010-9143-7)。核对范围：Crossref 书目与 OpenAlex 摘要。不能据此断言单个 PR 未改测试就是缺陷。
- Wang, S., Wen, M., Liu, Y., Wang, Y., & Wu, R. (2021). *Understanding and Facilitating the Co-Evolution of Production and Test Code*. SANER. [DOI: 10.1109/SANER50967.2021.00033](https://doi.org/10.1109/SANER50967.2021.00033)。核对范围：书目与摘要。不能直接推广为 NetBox 的 PR 判定。
- Spadini, D., Aniche, M., Storey, M.-A., Bruntink, M., & Bacchelli, A. (2018). *When testing meets code review: why and how developers review tests*. ICSE. [DOI: 10.1145/3180155.3180192](https://doi.org/10.1145/3180155.3180192)。核对范围：书目与摘要。不用于证明「缺少测试是最常见审查顾虑」。

## 6. 限制与反例

- 可能误报：测试已覆盖、位于另一个仓库或后续 PR；文档、生成代码及配置被错误分成生产代码。
- 可能漏报：测试文件路径不匹配默认分类；纯删除被标成 `code_removal` 后仍提示，但审查者可能不需要补测。
- Python 动态特性限制：动态语言、生成文件和路径重命名可能影响分类。规则不执行测试。
- 规则不判断：测试质量、回归缺陷或因果关系。删除旧测试只代表测试文件发生变化，不证明处理充分。
- 必须人工复核的上下文：已有测试、CI、变更性质和后续测试计划。仅依据行数不能确认是死代码删除或功能下线。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `literature_inherited` |
| 验证方法 | 构造路径分类、纯删除、重命名、测试与生产混合、外部测试和不完整 Diff 样例。再对冻结 NetBox PR 按预先制定标准人工标注「提示是否准确」和「是否需要补测」 |
| 数据集 | 007 构造样例；NetBox 冻结 PR 的标注集未圈定 |
| 判定依据 | 人工标注。维护者评论中的补测请求只是弱线索，未标记不代表无需测试 |
| 指标 | 命中频次与 Precision。不预填。真实缺陷关联的三个月窗口和效果阈值均待论证 |
| 验收标准 | 构造样例按默认路径分类工作。这不是实证验收，也不是 `validated` |
| 未解决问题 | 纯删除是否另设规则待实证。外部测试仓库看不见。文献细节待核对全文 |
