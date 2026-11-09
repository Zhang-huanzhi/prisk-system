# 规则说明卡片：`code.unmanaged_open`

> 本卡片同时服务于工程登记和毕业论文写作。没有证据的内容填写“待验证”，不要用推测替代结果。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.unmanaged_open` |
| 规则名称 | 未用 with 管理的 open |
| 版本 | `v1` |
| 规则阵营 | `code_smell` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

登记册 `lifecycle` 也是 `implemented`。这表示检测器已经接入，不是 `validated`。017 扩大了设计上的调用形态。检测器尚未覆盖 `Path.open`，见第 7 节。

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | Python 源文件及其 PR 差异中的 `open` 调用，包括直接名称和 `pathlib.Path` 上的属性 `open` |
| 依赖层级 | `language`。阵营是代码异味；依赖的是上下文管理协议，不是 Django 文件 API |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `Medium` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

## 3. 为什么制定

### 观察到的工程问题

`open` 返回的文件对象实现了上下文管理协议。调用没有作为 `with` 或 `async with` 的上下文表达式时，关闭路径要靠稍后的 `close`、`contextlib.closing` 或 `ExitStack`。`Path.open` 返回的是同一类文件对象。

### 为什么值得检测

直接写成 `with open(...)` 或 `with Path(...).open(...)` 时，退出代码块会走关闭路径。命中只是复核线索，不表示资源已经泄漏。把 `Path.open` 机械排除会漏掉同一类未托管打开。

### 现有规则为什么不能覆盖

`code.dynamic_execution` 只看直接名称 `eval` 和 `exec`。本规则不把 `io.open`、`builtins.open` 或其他属性上的 `open` 收进 Hit；那些不是 `pathlib.Path` 的打开形式。

### 研究或工程价值

语言级资源关闭复核。017 把 `Path.open` 纳入与内置 `open` 相同的「未作为 with 上下文」判定。

## 4. 检测定义

- **检测对象**：head AST 中的 `Call`。要么函数位置是直接名称 `open`（`(open)(...)` 在 AST 里仍是 `Name`，算直接名称）；要么函数位置是属性，属性名是 `open`，并且接收者是调用、该调用的最后一段是 `Path`（`Path(...)` 或 `pathlib.Path(...)`）。
- **触发条件**：该调用的行范围与新增 Diff 行相交，且这个 `Call` 不是某个 `with` 或 `async with` 项的 `context_expr`。每个这样的调用一条 Finding。严重度 `Medium`。
- **触发特征**：`direct_callee_name`（`source` 为直接名称 `open`，或属性名 `open` 且接收者最后一段为 `Path`；`value_type` 为 `string`；`operator` 为 `eq`；`threshold` 为 `open`；`required` 为 true）。`used_as_with_context`（`source` 为该 `Call` 是否正好是 `with` 或 `async with` 的 `context_expr`；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `false`；`required` 为 true）。`call_changed`（`source` 为行范围与新增行相交；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true）。
- **不触发条件**：`with open(...)`、`with Path(...).open(...) as handle`、`async with open(...)`；`io.open`、`builtins.open`；接收者最后一段不是 `Path` 的其他属性 `open`（例如名字 `path.open()`，接收者不是 `Path(...)` 调用）；别名 `opener = open` 之后的 `opener(...)`；字符串和注释里的 `open`；未改动调用；只删除调用。
- **输入**：head Python 源码、路径、三点 Diff 新增行。
- **Finding**：规则 ID、调用形态、`used_as_with_context: false`、行范围、代码切片、`pr_intrinsic_risk`、严重度 `Medium`。切片缺失时 `source_status` 为 `unavailable`。
- **证据位置**：文件、调用节点、行范围。
- **上下文切片**：该调用。`handle = open(path)` 后再 `with handle`、`contextlib.closing(open(path))`、条件表达式里的 `open` 都不是 `context_expr` 本身。
- **影响类型**：可维护性。资源是否仍然打开不在本规则内。

接收者是名字而不是 `Path(...)` 调用时，不能证明它是 pathlib 的 Path。这种 `path.open()` 记 `missing_framework_context`，不记 Hit，也不把它当成已经检查过的 NotFound。旧节点能确定直接名称是 `open` 但没有 `used_as_with_context` 时，进入 `summary.unanalyzed`，原因是 `unsupported_stage04_details`。解析失败标记未分析，不视作通过。

设计上的触发：

```python
handle = open(path)
text = Path(path).open().read()
return pathlib.Path(path).open()
return (open)(path)
```

设计上的不触发：

```python
with open(path) as handle:
    handle.read()
with Path(path).open() as handle:
    handle.read()
io.open(path)
```

运行时对齐（Task 020）：检测器覆盖直接名称 open 与接收者为 Path(...) / pathlib.Path(...) 调用的属性 open。with Path(...).open() 不触发；名字形式 path.open() 记 missing_framework_context。

适用调用已经按本卡片分类、没有证据缺口、也没有解析失败时，终态是 NotFound。这些终态不是另一个生命周期字段。

## 5. 理论与项目依据

- [PEP 343](https://peps.python.org/pep-0343/) 说明 `with` 用来保证上下文的进入和退出。它不证明每个未包在 `with` 里的 `open` 都会泄漏。
- [Python `with` 语句](https://docs.python.org/3/reference/compound_stmts.html#the-with-statement)、[内置 `open`](https://docs.python.org/3/library/functions.html#open) 和 [`pathlib.Path.open`](https://docs.python.org/3/library/pathlib.html#pathlib.Path.open) 描述本规则的两种调用。`Path.open` 打开文件并返回文件对象，关闭理由与内置 `open` 相同。
- [CWE-772](https://cwe.mitre.org/data/definitions/772.html) 描述资源在有效期结束后未释放。它不是本检测器的误报率证据。

## 6. 限制与反例

- 可能误报：手动 `close()`、`try/finally`、`contextlib.closing` 和 `ExitStack.enter_context` 会命中。被遮蔽的直接名称 `open` 也会命中。
- 可能漏报：`io.open`、`builtins.open`、先赋值再调用，以及接收者不是 `Path(...)` 调用的属性 `open`。运行时目前还会漏掉设计上已经纳入的 `Path.open`。
- Python 动态特性限制：直接名称可能被局部名字遮蔽。规则不解析绑定目标，也不证明一个名字的值是 Path 实例。
- 规则不判断：文件描述符是否仍然打开，也不判断泄漏已经发生。
- 必须人工复核的上下文：关闭路径、调用绑定，以及该调用是不是 `with` 的上下文表达式。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `literature_inherited` |
| 验证方法 | 迭代 005 构造样例已由 Task 020 补齐 Path(...).open(...) 及其 with 形式 |
| 数据集 | 迭代 005 构造样例；NetBox 实证数据集待确定 |
| 判定依据 | 本卡片的设计合同；Task 020 后 Path.open 运行时与合同一致 |
| 指标 | 构造样例通过率、证据完整率。不预填 Precision、Recall 或泄漏结论 |
| 验收标准 | 未作为 with 上下文的直接 open 和 Path(...).open(...) 都产生 Finding，with 形式不产生。Task 020 已做到 |
| 未解决问题 | 名字形式的 path.open() 仍是 Unanalyzed，因为没有类型。实证数据范围待补齐 |
