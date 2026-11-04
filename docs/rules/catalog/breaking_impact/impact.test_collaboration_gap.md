# 业务变更缺少测试协同

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `impact.test_collaboration_gap` |
| 版本 / 阵营 / 生命周期 | `v1` / `breaking_impact` / `draft` |
| 负责人 | `Prisk-System` |
| 风险性质 / 依赖层级 | `pr_intrinsic` / `process` |
| 适用范围 | 跨语言 PR；项目需提供生产代码与测试路径的分类配置 |
| 分析目标层 / 证据形态 | `change_metadata`, `diff_delta` / `metric_value`, `code_slice` |
| 严重度 / 一票抬升 | `Medium` / `false`，条件 `null`；设计值待验证 |

## 制定理由

生产代码变化有时需要同步维护测试，审查时可提示核对测试是否仍充分。此规则只观察同一 PR 的路径变化，不能从没有测试文件变化推断测试缺失、协同滞后或存在缺陷。单独维护测试的仓库、现有测试已覆盖或无需调整测试时也可能命中；`breaking_impact` 是登记阵营，不表示已证实外部破坏。

## 检测定义

- 检测对象：项目配置分类后的 PR 文件变化，包含新增、修改、重命名和删除；重命名须同时检查前后路径。
- 触发：差异完整且路径分类规则可用，至少一个生产代码文件发生新增、修改或删除，且该 PR 没有任何测试文件发生新增、修改、删除或重命名。纯生产代码路径重命名默认不视作生产内容变化；需根据 Diff 判断。
- 不触发：没有生产代码变化，或至少一个测试文件发生变化。缺少完整 Diff、分类配置或无法判断时标记未分析，不当作未命中。
- 特征（拟定，均非现有运行能力）：`production_files_changed`（按项目分类的生产代码内容变动文件数，integer，`gte 1`）；`test_files_changed`（按项目分类的测试变动文件数，integer，`eq 0`）；`diff_complete`（Diff 是否完整，boolean，`eq true`）。
- 纯删除边界：额外记录 `production_additions` 和 `production_deletions`。生产代码新增行数为 0 且删除行数大于 0 时标记 `code_removal`，仍按上述条件提示，但单独展示供人工复核；是否调整严重度或另设规则待实证，不自动降低严重度。仅依据行数不能确认是死代码删除或功能下线；二进制或统计不完整时标记未知。
- 输入与输出：三点 Diff、分类规则、文件状态；Finding 给出生产路径、测试变化计数为 0、分类配置和统计范围，供审查者人工检查测试计划。测试路径列表、外部测试来源及无法分类项作为上下文展示。

示例：修改 `src/order.py` 且没有任何测试文件变化，分类配置和 Diff 完整时触发；同一个 PR 同时修改 `src/order.py` 和 `tests/test_order.py` 时不触发。仅修改文档或 Diff 不完整时不触发，但后者需标记未分析。

## 理论与项目依据

- Zaidman, A., Van Rompaey, B., van Deursen, A., & Demeyer, S. (2011). *Studying the co-evolution of production and test code in open source and industrial developer test processes through repository mining*. Empirical Software Engineering, 16, 325–364. [DOI: 10.1007/s10664-010-9143-7](https://doi.org/10.1007/s10664-010-9143-7)。论文使用版本历史、规模与覆盖信息分析共同演化，并识别同步和分阶段模式；不能据此断言单个 PR 未改测试就是缺陷。核对范围：Crossref 书目与 OpenAlex 摘要；完整论文细节待核对。
- Wang, S., Wen, M., Liu, Y., Wang, Y., & Wu, R. (2021). *Understanding and Facilitating the Co-Evolution of Production and Test Code*. SANER. [DOI: 10.1109/SANER50967.2021.00033](https://doi.org/10.1109/SANER50967.2021.00033)。摘要研究 Java 项目中测试更新及其影响因素，支持“是否需要更新测试依赖具体上下文”；不能直接推广为 NetBox 的 PR 判定。核对范围：书目与摘要。
- Spadini, D., Aniche, M., Storey, M.-A., Bruntink, M., & Bacchelli, A. (2018). *When testing meets code review: why and how developers review tests*. ICSE. [DOI: 10.1145/3180155.3180192](https://doi.org/10.1145/3180155.3180192)。摘要研究测试代码如何被审查及其障碍，可支持测试审查的重要性；不用于证明“缺少测试是最常见审查顾虑”。核对范围：书目与摘要。

## 限制与反例

测试可能已覆盖、位于另一个仓库或后续 PR；文档、生成代码及配置分类错误可导致误报或漏报。纯删除可能是功能下线、删除死代码或其他重构，即使没有测试变更也未必需要补测；删除旧测试也只代表测试文件发生变化，不证明处理充分。测试文件变动不保证测试覆盖当前行为；动态语言、生成文件和路径重命名可能影响分类。规则不判断测试质量、回归缺陷或因果关系，需人工查看已有测试、CI、变更性质和后续测试计划。

## 有效性计划

`literature_inherited` 表示问题背景有文献依据；本项目的实现和判定方式仍须验证。先构造路径分类、纯删除含无旧测试和删除旧测试、重命名、测试与生产混合、外部测试和不完整 Diff 样例，验证条件及证据；再对冻结 NetBox PR 按预先制定标准人工标注“提示是否准确”和“是否需要补测”，分别报告命中频次与 Precision，并比较纯删除子集。探索将维护者评论中的补测请求和仓库原生标签作为弱标注线索，与人工标注交叉核对；先确认标签实际存在、评论作者与请求语义，并避免把机器人、引用或合并后产生的信息误当审查时证据。未标记不代表无需测试，弱标注并非真值，需报告覆盖率和分歧。真实缺陷关联分析只有在可靠的引入提交关联、观察窗口及混杂因素控制可行时才进行；三个月窗口和效果阈值均待论证，不预填结果。
