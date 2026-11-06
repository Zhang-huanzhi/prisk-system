# 业务变更缺少测试协同

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `workflow.test_collaboration_gap` |
| 版本 / 阵营 / 生命周期 | `v1` / `breaking_impact` / `implemented` |
| 负责人 | `Prisk-System` |
| 风险性质 / 依赖层级 | `pr_intrinsic` / `process` |
| 适用范围 | 使用仓库内默认路径分类的变更。生产代码后缀为 `.py`、`.pyi`、`.js`、`.jsx`、`.ts`、`.tsx`；其他路径在无法归类时未分析 |
| 分析目标层 / 证据形态 | `change_metadata`, `diff_delta` / `metric_value` |
| 严重度 / 一票抬升 | `Medium` / `false`，条件 `null`；设计值待验证 |

## 制定理由

生产代码变化有时需要同步维护测试，审查时可提示核对测试是否仍充分。此规则只观察同一 PR 的路径变化，不能从没有测试文件变化推断测试缺失、协同滞后或存在缺陷。单独维护测试的仓库、现有测试已覆盖或无需调整测试时也可能命中；`breaking_impact` 是登记阵营，不表示已证实外部破坏。

## 检测定义

- 检测对象：项目配置分类后的 PR 文件变化，包含新增、修改、重命名和删除；重命名须同时检查前后路径。
- 触发：差异完整且路径分类规则可用，至少一个生产代码文件发生新增、修改或删除，且该 PR 没有任何测试文件发生新增、修改、删除或重命名。纯生产代码路径重命名默认不视作生产内容变化；需根据 Diff 判断。
- 不触发：没有生产代码变化，或至少一个测试文件发生变化。缺少完整 Diff、分类配置或无法判断时标记未分析，不当作未命中。
- 特征：`production_files_changed`（默认分类下有行数证据的生产代码内容变动文件数，integer，`gte 1`）；`test_files_changed`（测试路径上新增、修改、删除或重命名的文件数，integer，`eq 0`）；`diff_complete`（每条参与判断的文件都有状态，且生产代码内容判断所需的新增/删除行数可用，boolean，`eq true`）。分类或统计不完整时不把 `diff_complete` 当成 true。
- 纯删除边界：额外记录 `production_additions` 和 `production_deletions`。生产代码新增行数为 0 且删除行数大于 0 时标记 `code_removal`，仍按上述条件提示，但单独展示供人工复核；是否调整严重度或另设规则待实证，不自动降低严重度。仅依据行数不能确认是死代码删除或功能下线；二进制或统计不完整时标记未知。
- 输入与输出：三点 Diff、分类规则、文件状态；Finding 给出生产路径、测试变化计数为 0、分类配置和统计范围，供审查者人工检查测试计划。测试路径列表、外部测试来源及无法分类项作为上下文展示。

示例：修改 `src/order.py` 且没有任何测试文件变化，分类和行数都完整时触发；同一个 PR 同时修改 `src/order.py` 和 `tests/test_order.py` 时不触发。仅修改文档时不触发。Diff 行数缺失、生产代码为二进制，或路径无法分类时不触发，并写入 `summary.unanalyzed`。

## 当前实现

检测器在 `backend/prisk/domain/test_collaboration.py`，由 `evaluate_rules` 调用。它不读取 JSON 登记册。默认路径策略 `default_source_and_test_directories` 固定在源码中：

- 测试：路径段 `test` 或 `tests`，或 Python 文件名 `test_*.py` / `*_test.py`（含 `.pyi`）。这与 stage03 的 `classify_path` 测试约定一致，因此覆盖 `backend/tests`。
- 非生产：`doc` / `docs`、`.md` / `.rst`、`migration` / `migrations`、`generated`、`static`，以及 `settings.py`、`configuration*.py` 和 `config` / `settings` / `configuration` 路径段。
- 生产：其余 `.py`、`.pyi`、`.js`、`.jsx`、`.ts`、`.tsx`。
- 其他路径为未知。

纯重命名或复制在新增行数和删除行数都为 0 时不是生产内容变化。测试路径上的重命名仍然算测试文件变化。生产代码新增行数为 0 且删除行数大于 0 时，Finding 的 `change_boundary` 为 `code_removal`，严重度不因此降低。

没有文件状态、新增/删除行数或 `binary` 字段的 stage04 记录不进入这条规则的文件变更通道。此时不产生 Finding，也不把历史协作分记上；这不是已复核通过。已保存的 demo stage05 不重算。摘要计数和文件列表不一致时，原因是 `diff_stats_unavailable`。路径无法分类时，原因是 `path_classification_unavailable`。规则未启用时，不因为未知路径写入未分析。

## 理论与项目依据

- Zaidman, A., Van Rompaey, B., van Deursen, A., & Demeyer, S. (2011). *Studying the co-evolution of production and test code in open source and industrial developer test processes through repository mining*. Empirical Software Engineering, 16, 325–364. [DOI: 10.1007/s10664-010-9143-7](https://doi.org/10.1007/s10664-010-9143-7)。论文使用版本历史、规模与覆盖信息分析共同演化，并识别同步和分阶段模式；不能据此断言单个 PR 未改测试就是缺陷。核对范围：Crossref 书目与 OpenAlex 摘要；完整论文细节待核对。
- Wang, S., Wen, M., Liu, Y., Wang, Y., & Wu, R. (2021). *Understanding and Facilitating the Co-Evolution of Production and Test Code*. SANER. [DOI: 10.1109/SANER50967.2021.00033](https://doi.org/10.1109/SANER50967.2021.00033)。摘要研究 Java 项目中测试更新及其影响因素，支持“是否需要更新测试依赖具体上下文”；不能直接推广为 NetBox 的 PR 判定。核对范围：书目与摘要。
- Spadini, D., Aniche, M., Storey, M.-A., Bruntink, M., & Bacchelli, A. (2018). *When testing meets code review: why and how developers review tests*. ICSE. [DOI: 10.1145/3180155.3180192](https://doi.org/10.1145/3180155.3180192)。摘要研究测试代码如何被审查及其障碍，可支持测试审查的重要性；不用于证明“缺少测试是最常见审查顾虑”。核对范围：书目与摘要。

## 限制与反例

测试可能已覆盖、位于另一个仓库或后续 PR；文档、生成代码及配置分类错误可导致误报或漏报。纯删除可能是功能下线、删除死代码或其他重构，即使没有测试变更也未必需要补测；删除旧测试也只代表测试文件发生变化，不证明处理充分。测试文件变动不保证测试覆盖当前行为；动态语言、生成文件和路径重命名可能影响分类。规则不判断测试质量、回归缺陷或因果关系，需人工查看已有测试、CI、变更性质和后续测试计划。

## 有效性计划

`literature_inherited` 表示问题背景有文献依据；本项目的实现和判定方式仍须验证。先构造路径分类、纯删除含无旧测试和删除旧测试、重命名、测试与生产混合、外部测试和不完整 Diff 样例，验证条件及证据；再对冻结 NetBox PR 按预先制定标准人工标注“提示是否准确”和“是否需要补测”，分别报告命中频次与 Precision，并比较纯删除子集。探索将维护者评论中的补测请求和仓库原生标签作为弱标注线索，与人工标注交叉核对；先确认标签实际存在、评论作者与请求语义，并避免把机器人、引用或合并后产生的信息误当审查时证据。未标记不代表无需测试，弱标注并非真值，需报告覆盖率和分歧。真实缺陷关联分析只有在可靠的引入提交关联、观察窗口及混杂因素控制可行时才进行；三个月窗口和效果阈值均待论证，不预填结果。

