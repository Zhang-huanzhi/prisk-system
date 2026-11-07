# 全局可变状态

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.global_mutable_state` |
| 版本 / 阵营 / 生命周期 | `v1` / `code_smell` / `implemented` |
| 负责人 | `Prisk-System` |
| 风险性质 / 依赖层级 | `pr_intrinsic` / `language` |
| 适用范围 | Python 源文件及其 PR 差异 |
| 分析目标层 / 证据形态 | `ast_syntax`, `diff_delta` / `code_slice`, `symbol_pair` |
| 严重度 / 一票抬升 | `Medium` / `false`，条件 `null` |

## 制定理由

模块或类体里的列表、字典和集合会被导入该模块的调用方共享。函数里的 `global` 则明确表示要重新绑定模块级名字。两种写法都可能使一次请求或一次测试改到另一处的状态。共享容器也可能是有意的缓存，所以命中只要求复核，不表示已经发生串扰。

本规则不覆盖函数默认参数里的可变对象。那是另一类绑定，见 [`code.mutable_default_argument`](code.mutable_default_argument.md)。那张卡片的生命周期另行登记，本规则的检测范围和生命周期都不因此改变。迭代 006 按本卡片接入检测器。命中只要求复核，不表示已经发生串扰。

## 检测定义

- 对象一：函数或异步函数体内的 `global` 语句。类体和模块顶层没有合法的、需要单独报告的 `global` 用法；`nonlocal` 不是本对象。
- 对象二：模块体或类体中的赋值、带值注解赋值。值必须是列表、字典或集合显示，或者没有参数、没有关键字的直接名称调用 `list()`、`dict()`、`set()`。函数体内的同形赋值不触发。
- 触发：任一对象的节点行范围与新增行相交。一个节点一条 Finding。`global` 语句不要求随后赋的值是可变对象；它报告的是重新绑定这个事实。两条对象可以出现在同一次变更里，Finding 分开。
- 不触发：`nonlocal`；函数内的 `items = []`；模块级的整数、字符串、元组、`None` 和名字引用；`cache.append(...)` 这类就地修改而没有新的绑定语句；`collections.defaultdict`、`deque` 和其他构造调用；只删除绑定。头 AST 不可用时标记未分析，不视作通过。
- 特征：`mutable_state_form`（枚举 `global_statement` 或 `mutable_binding`，`contains` 这两个值之一）；`binding_changed`（节点行范围与新增行相交，布尔值，`eq true`）。两个形式满足一个即可，不要求同一个节点同时具备。
- 输入与证据：head Python AST 和三点 Diff 新增行。影响类型设计为 `pr_intrinsic_risk`。证据应带形式、名字列表或绑定目标，以及代码切片。
- 实现：新解析写入 `mutable_state`。`global` 只在最内层作用域是函数或异步函数时报告；模块顶层和类体里的 `global` 不报告。可变绑定的作用域是模块体或类体，包括模块级 `if` 中的赋值，以及函数里嵌套类的类体；函数体内的同形赋值不报告。这些节点不进入既有五条规则的 `structural_changes`。006 之前没有 `mutable_state` 时，field 用赋值切片判断值形态，完整函数切片用来恢复 `global` 和嵌套类里的容器。切片缺失、截断或无法判断时进入 `summary.unanalyzed`，原因是 `unsupported_stage04_details`。这不是通过。没有节点、也没有可判断切片，不能当成已经没有可变状态。

触发：

```python
CACHE = {}
class Registry:
    items = []

def reset(value):
    global CACHE
    CACHE = value
```

不触发：

```python
LIMIT = 3
PAIR = (1, 2)

def local_only():
    items = []
    return items

def closure():
    nonlocal CACHE
```

## 依据

- [Python `global` 语句](https://docs.python.org/3/reference/simple_stmts.html#the-global-statement) 说明该语句声明的名字绑定到模块全局作用域。
- [Python 数据模型中的可变对象](https://docs.python.org/3/reference/datamodel.html#objects-values-and-types) 说明列表、字典等对象的值可以被原地改变。模块级名字指向这种对象时，导入方看到的是同一个对象。
- 这两份语言文档支持“要复核共享绑定”的动机。它们不证明共享缓存一定错误，也不提供本项目的 Precision 或 Recall。

## 限制与反例

进程内缓存、插件注册表和测试夹具经常故意使用模块级字典，会命中。`CACHE = Cache()` 或 `DEFAULT = defaultdict(list)` 会漏报。导入后在另一个模块里修改对象也会漏报，因为本规则不跨文件跟踪名字。`global` 后只读不写仍会命中该语句。规则不检测数据竞争，不运行模块，不判断缓存是否线程安全。

人工复核应看绑定是否跨请求或跨测试共享、谁负责清空，以及这次变更是新增容器还是只新增 `global` 声明。

## 014 登记字段

登记册和卡片表格的 `lifecycle` 都是 `implemented`。006 已接入检测器，并用构造样例检查过。这不是 `validated`。014 不改命中条件，也不改这个字段。

比较单位是 head 上与新增行相交的函数内 `global`，或模块体、类体里的列表、字典、集合绑定。产生 Finding 时运行终态是 Hit。适用节点已经分类、没有证据缺口、也没有解析失败时，终态是 NotFound。没有这类节点是 `context_not_established`。切片不能判断时是 `unsupported_stage04_details`。这些终态不是另一个生命周期字段。命中仍不是串扰已经发生。

## 有效性计划

`literature_inherited`：迭代 006 已按本卡片检查两种形式、模块级 `if`、嵌套类、函数内列表、元组、`nonlocal`、`defaultdict`、带参数的 `list`、`builtins.list`、函数默认参数里的列表、只删除、新增行和旧切片。这些构造测试只证明检测器按定义工作。NetBox 上是否常见、是否造成串扰，留到实证迭代，现在不写结论。
