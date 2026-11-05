# 静默吞异常模式

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.swallowed_exception` |
| 版本 / 阵营 / 生命周期 | `v1` / `code_smell` / `implemented` |
| 负责人 | `Prisk-System` |
| 风险性质 / 依赖层级 | `pr_intrinsic` / `language` |
| 适用范围 | Python 源文件及其 PR 差异 |
| 分析目标层 / 证据形态 | `ast_syntax`, `diff_delta` / `code_slice`, `symbol_pair` |
| 严重度 / 一票抬升 | `Medium` / `false`，条件 `null` |

## 制定理由

异常处理分支只有 `pass` 时，异常被捕获后没有该分支内的记录、恢复或重新抛出，可能掩盖故障并增加排查成本。允许忽略异常也可能是有意设计，因此此规则只提示人工复核。宽泛捕获规则关注捕获范围，本规则关注处理体，两者可以同时命中同一分支，但 Finding 必须分别说明原因。

## 检测定义

- 对象：head 版本 Python AST 中的 `ExceptHandler`，包括普通和带异常类型的处理分支。
- 触发：处理分支头或处理体与新增行相交，且处理体恰好只有一个 `Pass` 节点。只移动代码或删除代码是否排除需后续通过可靠的前后匹配确定；当前仅按新增行定义。
- 不触发：处理体含记录、恢复、重新抛出或其他语句；与新增行无交集；无法解析或无法定位差异时标记未分析，不视作已通过。
- 特征：`handler_body_is_single_pass`，来源为 head AST `ExceptHandler.body` 是否恰好一个 `Pass`，布尔值，`eq true`；`handler_changed`，来源为该节点行范围与新增 Diff 行的交集，布尔值，`eq true`。
- 输入与证据：head 源码、路径和三点 Diff 新增行；Finding 包括规则 ID、路径、处理分支行范围、代码切片、差异及影响类型 `pr_intrinsic_risk`。前后对照不可得时明确标记，不伪造。004 的原始 Finding 使用 stage04 节点切片和新增行号；base 节点不存在或切片缺失时写入 `before`/`after`/`source_status` 的 `unavailable` 及原因。stage05 输入不含 unified diff hunk 原文，因此不复制 hunk 文本。

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

## 依据

- **MITRE CWE-390: Detection of Error Condition Without Action** ([CWE 条目](https://cwe.mitre.org/data/definitions/390.html)) 描述检测到错误条件却未采取行动，作为“静默吞异常”的缺陷分类依据。CWE 描述一般错误处理弱点，不等同于本卡的 `except ...: pass` 语法检测器。
- **Python PEP 20: The Zen of Python** ([PEP 20](https://peps.python.org/pep-0020/)) 明确写道：“Errors should never pass silently. Unless explicitly silenced.” 这是设计原则，不是经验性有效性结果。
- [Python 语言参考：try 语句](https://docs.python.org/3/reference/compound_stmts.html#the-try-statement)说明异常处理分支的执行语义；[pass 语句](https://docs.python.org/3/reference/simple_stmts.html#the-pass-statement)说明其不执行操作。
- Cabral, B., & Marques, P. (2007). *Exception Handling: A Field Study in Java and .NET*. ECOOP 2007, LNCS, pp. 151–175. [DOI: 10.1007/978-3-540-73589-2_8](https://doi.org/10.1007/978-3-540-73589-2_8)。可作为跨语言异常处理实践的田野研究背景；书目信息显示其为 ECOOP 2007 章节，并不支持“2009 年研究证明空 catch 最常见且最具破坏性”的说法，卡片不作该断言。
- **CWE-391: Unchecked Error Condition** 曾描述未检查错误条件，但 MITRE 当前条目标为 deprecated，故不作为本规则的现行主依据 ([CWE-391](https://cwe.mitre.org/data/definitions/391.html))。

## 限制与反例

有意忽略可恢复异常可能是合理处理；处理体调用空函数、`contextlib.suppress`、动态生成或解析失败均可能漏报。规则不判断异常是否实际发生、故障严重度或业务正确性；需人工查看异常来源、调用方及后续补偿逻辑。

## 有效性计划

`literature_inherited`：迭代 004 已按本卡片检查构造样例，包括单个 `pass`、带日志或重新抛出、裸捕获与具名捕获、新增行、未改动行、语法错误和源码不可用。CWE/PEP 支持问题分类和设计动机，不证明检测器准确性，也不提供 Precision 或 Recall。实证数据集和验收阈值仍待确定。Python 异常组、重命名和只移动代码的处理仍待后续设计。

