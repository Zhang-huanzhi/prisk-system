# 规则说明卡片：`code.global_mutable_state`

> 本卡片同时服务于工程登记和毕业论文写作。没有证据的内容填写“待验证”，不要用推测替代结果。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.global_mutable_state` |
| 规则名称 | 全局可变状态 |
| 版本 | `v1` |
| 规则阵营 | `code_smell` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

登记册 `lifecycle` 也是 `implemented`。006 已接入检测器。这不是 `validated`。命中仍不是串扰已经发生。

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | Python 源文件及其 PR 差异中的模块或类体绑定，以及函数内的 `global` 语句 |
| 依赖层级 | `language`。阵营是代码异味；依赖的是绑定作用域，不是函数默认参数 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `Medium` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

## 3. 为什么制定

### 观察到的工程问题

模块或类体里的列表、字典和集合会被导入该模块的调用方共享。函数里的 `global` 则明确表示要重新绑定模块级名字。两种写法都可能使一次请求或一次测试改到另一处的状态。

### 为什么值得检测

共享容器也可能是有意的缓存。命中只要求复核，不表示已经发生串扰。

### 现有规则为什么不能覆盖

本规则不覆盖函数默认参数里的可变对象。那是另一类绑定，见 [`code.mutable_default_argument`](code.mutable_default_argument.md)。那张卡片的生命周期另行登记，本规则的检测范围和生命周期都不因此改变。

### 研究或工程价值

语言级共享绑定复核。语言文档支持动机，不证明共享缓存一定错误。

## 4. 检测定义

- **检测对象**：函数或异步函数体内的 `global` 语句；以及模块体或类体中的赋值、带值注解赋值。值必须是列表、字典或集合显示，或者没有参数、没有关键字的直接名称调用 `list()`、`dict()`、`set()`。
- **触发条件**：任一对象的节点行范围与新增行相交。一个节点一条 Finding。`global` 语句不要求随后赋的值是可变对象。两条对象可以出现在同一次变更里，Finding 分开。严重度 `Medium`。
- **触发特征**：`mutable_state_form`（`source` 为枚举 `global_statement` 或 `mutable_binding`；`value_type` 为 `enum`；`operator` 为 `contains`；`threshold` 为这两个值；`required` 为 true）。`binding_changed`（`source` 为节点行范围与新增行相交；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true）。两个形式满足一个即可。
- **不触发条件**：`nonlocal`；函数内的 `items = []`；模块级的整数、字符串、元组、`None` 和名字引用；`cache.append(...)` 这类就地修改而没有新的绑定语句；`collections.defaultdict`、`deque` 和其他构造调用；只删除绑定。类体和模块顶层的 `global` 不报告。
- **输入**：head Python AST 和三点 Diff 新增行。新解析写入 `mutable_state`。这些节点不进入既有五条规则的 `structural_changes`。
- **Finding**：形式、名字列表或绑定目标、代码切片、`pr_intrinsic_risk`、严重度 `Medium`。
- **证据位置**：文件、绑定目标或 `global` 名字、行范围。
- **上下文切片**：该语句。可变绑定的作用域包括模块级 `if` 中的赋值，以及函数里嵌套类的类体。
- **影响类型**：可维护性。不是数据竞争结论。

006 之前没有 `mutable_state` 时，field 用赋值切片判断值形态，完整函数切片用来恢复 `global` 和嵌套类里的容器。切片缺失、截断或无法判断时，原因是 `unsupported_stage04_details`。没有节点、也没有可判断切片，不能当成已经没有可变状态。头 AST 不可用时标记未分析，不视作通过。

产生 Finding 时运行终态是 Hit。适用节点已经分类、没有证据缺口、也没有解析失败时，终态是 NotFound。没有这类节点是 `context_not_established`。

触发：`CACHE = {}`；类体 `items = []`；函数内 `global CACHE`。

不触发：`LIMIT = 3`；`PAIR = (1, 2)`；函数内 `items = []`；`nonlocal CACHE`。

## 5. 理论与项目依据

- [Python `global` 语句](https://docs.python.org/3/reference/simple_stmts.html#the-global-statement) 说明该语句声明的名字绑定到模块全局作用域。
- [数据模型中的对象](https://docs.python.org/3/reference/datamodel.html#objects-values-and-types) 说明列表、字典等对象的值可以被原地改变。
- 这两份语言文档不提供本项目的 Precision 或 Recall。

## 6. 限制与反例

- 可能误报：进程内缓存、插件注册表和测试夹具故意使用模块级字典。`global` 后只读不写仍会命中该语句。
- 可能漏报：`CACHE = Cache()` 或 `DEFAULT = defaultdict(list)`。导入后在另一个模块里修改对象也会漏报。
- Python 动态特性限制：本规则不跨文件跟踪名字，不运行模块。
- 规则不判断：不检测数据竞争，不判断缓存是否线程安全。
- 必须人工复核的上下文：绑定是否跨请求或跨测试共享、谁负责清空，以及这次变更是新增容器还是只新增 `global` 声明。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `literature_inherited` |
| 验证方法 | 迭代 006 的构造样例检查两种形式、模块级 `if`、嵌套类、函数内列表、元组、`nonlocal`、`defaultdict`、带参数的 `list`、函数默认参数里的列表、只删除和旧切片 |
| 数据集 | 006 构造样例 |
| 判定依据 | 本卡片的两种对象 |
| 指标 | 不填写 NetBox 上是否常见或是否造成串扰 |
| 验收标准 | 构造样例按两种形式命中。函数默认参数的列表留给 `code.mutable_default_argument` |
| 未解决问题 | 实证迭代尚未开始。默认参数卡片是另一条 `draft`，不改变本规则的 `implemented` |
