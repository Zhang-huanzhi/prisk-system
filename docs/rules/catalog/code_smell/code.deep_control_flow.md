# 规则说明卡片：`code.deep_control_flow`

> 本卡片同时服务于工程登记和毕业论文写作。没有证据的内容填写“待验证”，不要用推测替代结果。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.deep_control_flow` |
| 规则名称 | 深层控制流嵌套 |
| 版本 | `v1` |
| 规则阵营 | `code_smell` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

登记册 `lifecycle` 也是 `implemented`。005 已接入检测器。这不是 `validated`。深度阈值 4 是卡片常量，014 不改它。

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | Python 源文件及其 PR 差异中的控制流语句节点 |
| 依赖层级 | `language`。阵营是代码异味；依赖的是语句嵌套深度，不是圈复杂度公式 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`metric_value` |
| 严重度 | `Medium` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

## 3. 为什么制定

### 观察到的工程问题

多层 `if`、循环、`with` 和 `try` 叠在一起时，读者要同时记住更多分支。

### 为什么值得检测

这是可维护性复核线索，不是缺陷结论，也不是圈复杂度。阈值写死在本卡片上，检测器不读取运行时配置。

### 现有规则为什么不能覆盖

Pylint R1702 的默认上限属于 Pylint 配置，不自动成为本卡片的阈值。两边计入的块也不要求一致。本规则不把控制流节点送进既有五条粗粒度结构规则的 `structural_changes`。

### 研究或工程价值

语言级可维护性规则。不把某个历史缺陷样本说成深度 5 的后果。

## 4. 检测定义

- **检测对象**：head AST 中的控制流语句节点。种类只包括 `if`、`for`、`async for`、`while`、`with`、`async with`、`try` 和 `try*`（`try_star`）。
- **触发条件**：该节点的行范围与新增行相交，且 `nesting_depth > 4`。深度 4 不触发，深度 5 触发。每个超限节点一条 Finding。外层节点自己的深度不超过 4 时，即使行范围盖住了内层改动，也不触发。严重度 `Medium`。
- **触发特征**：`nesting_depth`（`source` 为当前函数、类或模块内的整数深度；`value_type` 为 `integer`；`operator` 为 `gt`；`threshold` 为 `4`；`required` 为 true）。`control_flow_changed`（`source` 为节点行范围与新增行相交；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true）。阈值 `4` 是卡片常量 `CONTROL_FLOW_DEPTH_THRESHOLD`。
- **不触发条件**：深度小于等于 4；只改外层条件行而较深节点没有碰上新增行；未改动的深层块；只删除深层块。不计入：三元 `IfExp`、`assert`、布尔运算、`match` / `case`、推导式里的 `for` / `if`、函数嵌套本身。`match` 里面的 `if` 仍按 `if` 计数，但 `match` 不加深度。
- **输入**：head 源码、路径、三点 Diff 新增行。
- **Finding**：`control_kind`、`nesting_depth`、`depth_threshold: 4`、`nesting_depth_basis`、行范围、切片、`pr_intrinsic_risk`、严重度 `Medium`。
- **证据位置**：文件、控制流节点、深度。
- **上下文切片**：超限节点。进入函数、异步函数或类时深度归零。语句自身使深度加一。`else`、`elif` 的后续分支、`finally` 和 `except` 处理器不再额外加一层。`elif` 按 CPython 的写法与所属 `if` 共用深度。AST 无法区分「单独的 else-if」和 `elif`。
- **影响类型**：可维护性。

旧节点已有整数 `nesting_depth` 和合法 `control_kind` 时直接使用。没有这些字段时，只在未截断切片本身的深度已经大于 4 时，把该深度当作下界并报告，`nesting_depth_basis` 为 `segment_lower_bound`。切片更浅、无法解析或被截断时，原因是 `unsupported_stage04_details`。005 之前没有 `control_flow` 节点；没有这种节点不等于已经证明深度不超过 4。

产生 Finding 时运行终态是 Hit。适用节点已经看完、没有证据缺口、也没有解析失败时，终态是 NotFound。没有控制流节点是 `context_not_established`。

触发的形状是函数内深度 5：`if` / `for` / `while` / `with` / `try` 逐层嵌套且内层与新增行相交。深度 4 的同样链条不触发。`elif` 链不因分支数量加深度。

## 5. 理论与项目依据

- [Python 复合语句](https://docs.python.org/3/reference/compound_stmts.html) 列出 `if`、`for`、`while`、`with` 和 `try` 的语句边界。深度按这些语句的 AST 形状计算。
- [Pylint R1702](https://pylint.readthedocs.io/en/latest/user_guide/messages/refactor/too-many-nested-blocks.html) 把过深嵌套当作可维护性提示。它的默认上限不是本卡片阈值。
- 本规则不引用圈复杂度公式。

## 6. 限制与反例

- 可能误报：状态机、解析器和生成代码可以在深度 5 以上仍然清楚。
- 可能漏报：长 `elif` 链不会加深度。`else: if` 在 AST 中与 `elif` 相同，也会少算一层。`match` 很深时，只有其中的 `if`、循环、`with`、`try` 继续累加。
- Python 动态特性限制：`exec` 生成的分支没有语句节点。切片截断时只能使用下界或记未分析。
- 规则不判断：不计算 McCabe 复杂度，不判断分支是否可达，不把命中写成缺陷。
- 必须人工复核的上下文：超限节点的 `control_kind` 和深度，以及新增行是落在深层语句上还是只碰到外层条件。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `literature_inherited` |
| 验证方法 | 迭代 005 的构造样例检查深度 5、深度 4、`elif`、`else` 体内的 `if`、`try` 不把 `except` 再算一层、函数重置、`match`、推导式、三元表达式、只改外层行、未改动深层块和删除 |
| 数据集 | 005 构造样例。阈值 4 没有用 NetBox 校准 |
| 判定依据 | 本卡片的深度定义 |
| 指标 | Precision、Recall 和「多深才影响缺陷」都还没有结果，不能填写 |
| 验收标准 | 构造样例按 `nesting_depth > 4` 命中。这不是实证验收 |
| 未解决问题 | 阈值未用真实 PR 校准。`match` 本身不加深度 |
