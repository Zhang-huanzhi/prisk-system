# 规则说明卡片：`code.swallowed_exception`

> 本卡片同时服务于工程登记和毕业论文写作。没有证据的内容填写“待验证”，不要用推测替代结果。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.swallowed_exception` |
| 规则名称 | 静默吞异常模式 |
| 版本 | `v1` |
| 规则阵营 | `code_smell` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

登记册 `lifecycle` 也是 `implemented`。004 已接入检测器，并用构造样例检查过。这不是 `validated`。

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | Python 源文件及其 PR 差异中的 `ExceptHandler` |
| 依赖层级 | `language`。阵营是代码异味；依赖的是处理体是否只有 `pass`，不是捕获类型的宽窄 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `Medium` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

## 3. 为什么制定

### 观察到的工程问题

异常处理分支只有 `pass` 时，异常被捕获后没有该分支内的记录、恢复或重新抛出，可能掩盖故障并增加排查成本。

### 为什么值得检测

允许忽略异常也可能是有意设计。此规则只提示人工复核，不证明故障已经发生。

### 现有规则为什么不能覆盖

[`code.bare_exception`](code.bare_exception.md) 的设计合同看裸 `except:` 和 `BaseException`，不要求处理体为空。本规则看处理体。两者可以同时命中同一分支，Finding 必须分别说明原因。

### 研究或工程价值

文献继承。CWE 与 PEP 20 支持问题分类，不证明检测器的 Precision 或 Recall。

## 4. 检测定义

- **检测对象**：head 版本 Python AST 中的 `ExceptHandler`，包括普通和带异常类型的处理分支。
- **触发条件**：处理分支头或处理体与新增行相交，且处理体恰好只有一个 `Pass` 节点。当前仅按新增行定义。只移动代码或只删除代码不在本触发里。严重度 `Medium`。
- **触发特征**：`handler_body_is_single_pass`（`source` 为 head AST `ExceptHandler.body` 是否恰好一个 `Pass`；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true）。`handler_changed`（`source` 为该节点行范围与新增 Diff 行的交集；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true）。
- **不触发条件**：处理体含记录、恢复、重新抛出或其他语句；与新增行无交集。
- **输入**：head 源码、路径和三点 Diff 新增行。004 的 Finding 使用 stage04 节点切片。base 节点不存在或切片缺失时写入 `unavailable`。不复制 hunk 原文。
- **Finding**：规则 ID、路径、处理分支行范围、代码切片、`pr_intrinsic_risk`、严重度 `Medium`。
- **证据位置**：文件、处理分支行范围。
- **上下文切片**：该 `ExceptHandler`。前后对照不可得时明确标记，不伪造。
- **影响类型**：可维护性。

无法解析或无法定位差异时标记未分析，不视作已通过。产生 Finding 时运行终态是 Hit。适用处理分支已经看完、没有证据缺口、也没有解析失败时，终态是 NotFound。没有这种节点是 `context_not_established`。

触发：

```python
try:
    load()
except ValueError:
    pass
```

不触发：

```python
try:
    load()
except ValueError:
    logger.exception("load failed")
    raise
```

## 5. 理论与项目依据

- [CWE-390](https://cwe.mitre.org/data/definitions/390.html) 描述检测到错误条件却未采取行动。它不等同于本卡的 `except ...: pass` 语法检测器。
- [PEP 20](https://peps.python.org/pep-0020/) 写道：“Errors should never pass silently. Unless explicitly silenced.” 这是设计原则，不是经验性有效性结果。
- [try 语句](https://docs.python.org/3/reference/compound_stmts.html#the-try-statement) 与 [pass 语句](https://docs.python.org/3/reference/simple_stmts.html#the-pass-statement) 说明分支语义。
- Cabral, B., & Marques, P. (2007). *Exception Handling: A Field Study in Java and .NET*. ECOOP 2007, LNCS, pp. 151–175. [DOI: 10.1007/978-3-540-73589-2_8](https://doi.org/10.1007/978-3-540-73589-2_8)。卡片不断言「2009 年研究证明空 catch 最常见且最具破坏性」。
- [CWE-391](https://cwe.mitre.org/data/definitions/391.html) 当前标为 deprecated，不作为现行主依据。

## 6. 限制与反例

- 可能误报：有意忽略可恢复异常，处理体只有 `pass`。
- 可能漏报：处理体调用空函数、`contextlib.suppress`、动态生成的处理分支，或解析失败。
- Python 动态特性限制：处理体由 `exec` 填入时，AST 上看不到 `pass` 以外的动作，也可能看不到分支。
- 规则不判断：异常是否实际发生、故障严重度或业务正确性。
- 必须人工复核的上下文：异常来源、调用方及后续补偿逻辑。Python 异常组、重命名和只移动代码的处理仍待后续设计。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `literature_inherited` |
| 验证方法 | 迭代 004 的构造样例包括单个 `pass`、带日志或重新抛出、裸捕获与具名捕获、新增行、未改动行、语法错误和源码不可用 |
| 数据集 | 004 构造样例。实证数据集待确定 |
| 判定依据 | 本卡片。CWE/PEP 不证明检测器准确性 |
| 指标 | 不提供 Precision 或 Recall |
| 验收标准 | 构造样例按「恰好一个 Pass 且与新增行相交」命中。这不是实证验收 |
| 未解决问题 | 实证数据集和验收阈值仍待确定。只移动代码的前后匹配仍待设计 |
