# 宽泛或裸异常捕获

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.bare_exception` |
| 版本 / 阵营 / 生命周期 | `v1` / `code_smell` / `implemented` |
| 负责人 | `Prisk-System` |
| 风险性质 / 依赖层级 | `pr_intrinsic` / `language` |
| 适用范围 | Python 源文件及其 PR 差异 |
| 分析目标层 / 证据形态 | `ast_syntax`, `diff_delta` / `code_slice`, `symbol_pair` |
| 严重度 / 一票抬升 | `Medium` / `false`，条件 `null` |

## 制定理由

裸捕获及捕获 `Exception`、`BaseException` 可能覆盖超出预期的异常，给故障定位和控制流带来困难。**裸 `except:` 等价于捕获 `BaseException`，会捕获 `KeyboardInterrupt` 和 `SystemExit`；`except Exception:` 不会捕获这两个异常**，不得混为同一后果。程序边界的统一记录及重新抛出也可能有意使用宽泛捕获，命中只要求复核，不证明缺陷。与静默吞异常规则不同，本规则检测捕获范围，不要求处理体为空。

## 检测定义

- 对象：head AST 中普通 `ExceptHandler`，其类型为空、直接名称 `Exception` 或 `BaseException`，包括异常元组中直接包含这些名称。
- 触发：处理分支头或处理体与新增 Diff 行相交且满足上述类型条件，生成复核 Finding；多个满足条件的类型属于同一分支时只生成一条。
- 不触发：仅捕获 `ValueError` 等具体类型；不与新增行相交；解析或定位失败时标记未分析。
- 特征：`handler_type`（head AST `ExceptHandler.type` 的直接名称集合，包含 `bare`、`Exception` 或 `BaseException`）；`handler_changed`（该节点行范围与新增行交集，布尔值，`eq true`）。名称直接匹配不保证解析为内置类型。
- 输入与证据：head Python 源码、文件路径、三点 Diff；Finding 包含规则 ID、行范围、捕获类型、代码切片与差异、`pr_intrinsic_risk`。前后对照缺失时明确标记。004 的原始 Finding 使用 stage04 节点切片和新增行号；base 节点不存在或切片缺失时写入 `before`/`after`/`source_status` 的 `unavailable` 及原因。stage05 输入不含 unified diff hunk 原文，因此不复制 hunk 文本。

触发：

```python
try:
    run()
except Exception:
    logger.exception("failed")
    raise
```

不触发：

```python
try:
    run()
except ValueError:
    recover()
```

## 依据

- **Python PEP 8: Style Guide for Python Code** ([PEP 8：异常处理](https://peps.python.org/pep-0008/#programming-recommendations)) 建议尽可能捕获具体异常，并明确说明裸 `except:` 会捕获 `SystemExit` 和 `KeyboardInterrupt`；若意图捕获程序错误，应使用 `except Exception:`。PEP 8 是规范性指导，不表示每次宽泛捕获均为缺陷。
- **MITRE CWE-396: Declaration of Catch for Generic Exception** ([CWE-396](https://cwe.mitre.org/data/definitions/396.html)) 说明捕获高层通用异常可能隐藏需要特殊处理的异常和诊断信息。该 CWE 描述通用弱点，不专指 Python，也不等同于裸 `except:`。
- [Python 语言参考：except 子句](https://docs.python.org/3/reference/compound_stmts.html#except-clause)与[内置异常层次](https://docs.python.org/3/library/exceptions.html#exception-hierarchy)界定匹配语义；`KeyboardInterrupt`、`SystemExit` 继承自 `BaseException` 而非 `Exception`。

## 限制与反例

进程边界记录后重新抛出等做法可能合理；名称被局部遮蔽会导致误报。别名、自定义异常继承、动态类型和解析失败可能漏报。裸捕获与 `Exception` 捕获后果不同，Finding 必须显示实际捕获形式。规则不判定异常被吞掉或业务受损，需人工核查处理体、异常类型来源和执行边界；异常组及 `except*` 的支持待设计。

## 014 登记字段

登记册和卡片表格的 `lifecycle` 都是 `implemented`。004 已接入检测器，并用构造样例检查过。这不是 `validated`。014 不改命中条件，也不改这个字段。

比较单位是 head 上与新增行相交的普通 `ExceptHandler`，类型为空，或直接名称是 `Exception` / `BaseException`。产生 Finding 时运行终态是 Hit。适用处理分支已经看完、没有本规则的证据缺口、也没有解析失败时，终态是 NotFound。没有这种节点是 `context_not_established`。这些终态不是另一个生命周期字段。

## 有效性计划

`literature_inherited`：迭代 004 已按本卡片检查裸捕获、`Exception`、`BaseException`、元组、嵌套元组、具体异常、名称遮蔽和新增行边界等构造样例。这些测试只证明检测器按定义工作，不提供 Precision 或 Recall。覆盖范围、实证数据集和验收阈值仍待确定。`except*` 仍待设计。

