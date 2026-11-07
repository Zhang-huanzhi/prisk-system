# 未用 with 管理的 open

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.unmanaged_open` |
| 版本 / 阵营 / 生命周期 | `v1` / `code_smell` / `implemented` |
| 负责人 | `Prisk-System` |
| 风险性质 / 依赖层级 | `pr_intrinsic` / `language` |
| 适用范围 | Python 源文件及其 PR 差异 |
| 分析目标层 / 证据形态 | `ast_syntax`, `diff_delta` / `code_slice`, `symbol_pair` |
| 严重度 / 一票抬升 | `Medium` / `false`，条件 `null` |

## 制定理由

内置 `open` 返回的文件对象实现了上下文管理协议。直接写成 `with open(...)` 或 `async with open(...)` 时，退出代码块会走关闭路径。赋值、返回、传参或链式调用里的直接 `open` 仍可能由稍后的 `close`、`contextlib.closing` 或 `ExitStack` 关闭，所以命中只是复核线索，不表示资源已经泄漏。

`code.dynamic_execution` 只看直接名称 `eval` 和 `exec`。本规则沿用同一直接名称边界，避免把 `Path.open` 和 `io.open` 收进同一条规则。

## 检测定义

- 对象：head AST 中函数位置为直接名称 `open` 的 `Call`。`(open)(...)` 在 AST 里仍是 `Name`，算直接名称。
- 触发：该调用的行范围与新增 Diff 行相交，且这个 `Call` 不是某个 `with` 或 `async with` 项的 `context_expr`。每个这样的调用一条 Finding。
- 不触发：`with open(...)`、`with open(...) as f`、`async with open(...)`；`Path.open`、`path.open()`、`io.open`、`builtins.open` 等属性调用；别名 `opener = open` 之后的 `opener(...)`；字符串和注释里的 `open`；未改动调用；只删除调用。解析失败标记未分析，不视作通过。
- 明显局部模式只认“调用节点本身就是 `with` / `async with` 的上下文表达式”。`handle = open(path)` 后再 `with handle`、`contextlib.closing(open(path))`、`with open(path) if flag else nullcontext()` 都不算这个模式。条件表达式里的 `open` 不是 `context_expr` 本身。
- 特征：`direct_callee_name`（`Call.func` 为 `Name` 时的 id，`eq "open"`）；`used_as_with_context`（该 `Call` 是否正好是 `with` 或 `async with` 的 `context_expr`，布尔值，`eq false`）；`call_changed`（行范围与新增行相交，布尔值，`eq true`）。名称可能被遮蔽，仍按源码名字判断。
- 输入与证据：head Python 源码、路径、三点 Diff 新增行。Finding 含规则 ID、`callee_name`、`used_as_with_context: false`、行范围、代码切片和 `pr_intrinsic_risk`。切片缺失时 `source_status` 为 `unavailable`。005 之前的调用节点如果能确定直接名称是 `open`，但没有 `used_as_with_context`，调用切片本身看不出外层 `with`，该节点进入 `summary.unanalyzed`，原因是 `unsupported_stage04_details`。这不是通过。

触发：

```python
handle = open(path)
text = open(path).read()
return (open)(path)
```

不触发：

```python
with open(path) as handle:
    handle.read()
async with open(path):
    pass
Path(path).open()
io.open(path)
```

## 依据

- [PEP 343](https://peps.python.org/pep-0343/) 说明 `with` 用来保证上下文的进入和退出。它不证明每个未包在 `with` 里的 `open` 都会泄漏。
- [Python `with` 语句](https://docs.python.org/3/reference/compound_stmts.html#the-with-statement) 和 [内置 `open`](https://docs.python.org/3/library/functions.html#open) 描述本规则使用的语句和调用形式。
- [`pathlib.Path.open`](https://docs.python.org/3/library/pathlib.html#pathlib.Path.open) 是属性调用。本规则按 004 的直接名称风格排除它，并在测试里固定这条边界。
- [CWE-772 Missing Release of Resource after Effective Lifetime](https://cwe.mitre.org/data/definitions/772.html) 描述资源在有效期结束后未释放的问题类别。它不是本检测器的误报率证据。

## 限制与反例

手动 `close()`、`try/finally`、`contextlib.closing` 和 `ExitStack.enter_context` 会命中，需要人工看关闭路径。名称遮蔽成另一个 `open` 也会命中。`io.open`、`builtins.open`、赋值后再调用，以及反射得到的打开函数会漏报。规则不追踪变量，不执行代码，不判断描述符是否仍然打开。

## 014 登记字段

登记册和卡片表格的 `lifecycle` 都是 `implemented`。005 已接入检测器，并用构造样例检查过。这不是 `validated`。014 不改命中条件，也不改这个字段。

比较单位是 head 上与新增行相交、直接名称是 `open`、且不是 `with` / `async with` 上下文表达式的调用。产生 Finding 时运行终态是 Hit。适用调用已经分类、没有证据缺口、也没有解析失败时，终态是 NotFound。旧节点缺少 `used_as_with_context` 时是 `unsupported_stage04_details`，不是 NotFound。这些终态不是另一个生命周期字段。

## 有效性计划

`literature_inherited`：迭代 005 已按本卡片检查直接 `open`、`with` / `async with`、属性调用、遮蔽、内层 `open`、条件上下文、删除行和缺失 `used_as_with_context` 的旧节点。这些构造测试只证明检测器按定义工作。NetBox 人工标注、Precision 和 Recall 都还没有做，本卡片不填写这些结果。
