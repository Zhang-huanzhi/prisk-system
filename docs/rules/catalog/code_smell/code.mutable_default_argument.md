# 规则说明卡片：`code.mutable_default_argument`

> 本卡片同时服务于工程登记和毕业论文写作。样例都是构造样例，不是某个已合并 PR 的复原。生命周期是 `implemented`（024 接入检测器与构造测试）；默认权重 0，不是 `validated`，也没有真实 PR 实证。严重度与风险性质是工程负责人的临时判断，不是终局。登记册没有权重字段；概念上的默认权重是 0，本任务不接入评分。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.mutable_default_argument` |
| 规则名称 | 函数默认参数中的可变对象 |
| 版本 | `v1` |
| 规则阵营 | `code_smell` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | 同一 Python 文件中，函数、异步函数或 lambda 的默认参数表达式 |
| 依赖层级 | `language`。阵营是代码异味；依赖的是 Python 函数定义时求值默认值，不是框架名单 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `Medium` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度 `Medium` 与 [`code.global_mutable_state`](code.global_mutable_state.md) 的设计值对齐。这是临时判断，后续算法阶段可以修订。`Medium` 不是权重，也不是一票抬升。

## 3. 为什么制定

### 观察到的工程问题

函数默认值在定义时只求值一次。默认值若是列表、字典或集合，后续调用会共享同一个对象。

### 为什么值得检测

一次调用里的 `append` 或写键会留在下一次调用看到的默认对象上。审查者需要单独看到这个绑定，而不是把它当成普通参数。

### 现有规则为什么不能覆盖

[`code.global_mutable_state`](code.global_mutable_state.md) 只覆盖函数内的 `global`，以及模块体、类体里的可变容器。该卡片写明函数默认参数里的可变对象是另一类绑定。006 的检测器按那张卡片工作，不把默认参数记成它的 Finding。本规则不改那条规则的生命周期，也不扩大它的命中条件。

### 研究或工程价值

语言文档中的已知写法。闭集与全局可变状态里的容器形态对齐：列表、字典、集合显示，以及无参数、无关键字的直接名称 `list()`、`dict()`、`set()`。不把这次对齐写成已经测过的误报率。

## 4. 检测定义

### 比较单位

一个函数、异步函数或 lambda 上的一个参数。位置参数、仅位置参数和仅关键字参数各自比较。比较的是该参数的默认值表达式，不是函数体里的赋值。

### 适用性

`FunctionDef.args.defaults`、`AsyncFunctionDef.args.defaults`、`Lambda.args.defaults`，以及对应的 `kw_defaults`。默认值节点必须能读出种类。当前 stage04 的函数签名只保存 `has_default`。参数默认值的 `literal_binding` 对列表、字典和集合记为 `literal_kind: non_literal`，不保存容器种类。只看到 `has_default` 为真，不能记 Hit。

### 闭集

默认值表达式属于下面之一：

- `ast.List`、`ast.Dict`、`ast.Set` 显示，空与非空都算；
- 直接名称调用 `list`、`dict` 或 `set`，且没有位置参数、没有关键字。

元组、`None`、数字、字符串、名字、属性、带参数的 `list(...)`、`collections.defaultdict`、列表推导和集合推导都不在闭集里。

### 触发条件

比较单位上的默认值属于闭集，且该默认值表达式的行范围与新增行相交。一个参数一条设计 Finding。同一函数上的多个闭集默认值分开记录。

### 触发特征

- `default_kind`：`source` 为该参数默认值表达式的 AST 种类；`value_type` 为 `enum`；`operator` 为 `contains`；`threshold` 为 `list_display`、`dict_display`、`set_display`、`list_call`、`dict_call`、`set_call`；`required` 为 true。
- `parameter_name`：`source` 为参数名；lambda 没有名字时用参数序号；`value_type` 为 `string`；`operator` 为 `present`；`required` 为 true。
- `default_changed`：`source` 为默认值表达式与新增行的交集；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true。

两个特征都要成立。`has_default` 不是 `default_kind`。

### 不触发条件

闭集之外的默认值；函数体内的 `items = []`；模块级或类级容器，那是 `code.global_mutable_state`；默认值没有与新增行相交；只有注解、没有默认值。

### 输入

同一文件的 head Python AST 和三点 Diff 新增行。不运行函数，不跨文件跟踪默认值后来被谁修改。

### Finding

设计线索：规则 ID、限定名、参数名、`default_kind`、设计标签 `pr_intrinsic_risk`。不证明已经发生串扰。024 接入检测器并生成 Finding。

### 证据位置

文件、函数或 lambda 的限定名、参数名、默认值切片、新增行号。

### 上下文切片

该参数所在的函数签名。签名超过未截断切片时，只保留这个默认值表达式；截断到无法确认种类则进入下面的 Unanalyzed。

### 影响类型

可维护性。共享的是这个默认对象，不是模块全局名字。

### 设计终态

设计预期，不是运行结果。本规则缺的是默认值种类。

- Hit：默认值种类属于闭集，且与新增行相交。
- NotFound：这次变更里的函数签名已经解析，每个默认值的种类都读到了，且没有闭集默认值与新增行相交。没有默认值也是 NotFound，前提是签名已解析。
- Unanalyzed：签名只有 `has_default`、默认值切片被截断、或种类无法区分列表与名字。原因是 `unsupported_stage04_details`。这时不能记 Hit，也不能记 NotFound。解析失败同样不是通过。

### 构造样例

正例：新增行含有 `def collect(item, bucket=[]):` 或 `def remember(key, cache={}):`。另一个正例：`def values(items=list()):`。仅关键字 `def build(*, rows=set()):` 同样落在闭集。

反例：`def collect(item, bucket=None):` 以及函数体内的 `bucket = []`。另一个反例：`def pair(item, bucket=(1, 2)):`。模块级 `CACHE = {}` 不由本规则触发。

无法分析：函数签名长到默认值表达式被截断，只能看见 `has_default`。不把 `has_default` 记成 Hit。

### 与现有规则的去重

`code.global_mutable_state` 继续负责 `global` 和模块级、类级容器。两条规则可以在同一次变更里各有设计线索，Finding 不合并。函数体内的局部列表两条都不触发。

## 5. 理论与项目依据

- [Python 教程：默认参数值](https://docs.python.org/3/tutorial/controlflow.html#default-argument-values) 写明默认值只求值一次，并用列表作为可变默认值的例子。随后的 `None` 写法是文档给出的替代，不是本规则的 Hit。
- 同页说明这与列表、字典以及多数类的实例有关。闭集没有因此扩大到任意调用。
- 这些句子说明规则思想有语言文档依据。它们不证明本项目的 Precision 或 Recall，也没有 NetBox 试点结果。

## 6. 限制与反例

- 可能误报：有意共享的默认缓存、注册表或递归辅助列表仍会落在闭集里。命中只要求复核。
- 可能漏报：`defaultdict(list)`、自定义容器、列表推导，以及在别的模块里改这个默认对象。
- Python 动态特性限制：默认值由调用构造，或函数由 `exec` 生成。直接名称被局部名字遮住时，`list()` 仍会按闭集记录，不证明它是内建 `list`。
- 规则不判断：对象是否跨请求共享、是否线程安全、调用方是否每次都传入实参。
- 必须人工复核的上下文：谁清空这个对象，以及这次变更是新增默认值还是只改了函数体。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `literature_inherited` |
| 验证方法 | 将来的构造样例覆盖五种闭集形态、`None`、元组、函数体列表、截断签名和未改动的旧默认值。不下载真实 PR |
| 数据集 | 未圈定 |
| 判定依据 | 语言文档只说明求值时机。Ground Truth 要等实现任务的构造样例，不能把文档当成已测得的误报率 |
| 指标 | 不预填 |
| 验收标准 | 默认值种类进入结构化字段并且构造测试按本卡片工作之前，不能写成 `implemented`。文档写完也不是 `registered` |
| 未解决问题 | 当前节点没有默认值种类；推导式未纳入闭集；没有检测器，没有实证 |
