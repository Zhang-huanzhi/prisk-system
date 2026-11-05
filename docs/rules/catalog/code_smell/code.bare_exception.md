# 宽泛或裸异常捕获

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.bare_exception` |
| 版本 / 阵营 / 生命周期 | `v1` / `code_smell` / `registered` |
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
- 特征：`handler_type`（待实现的 AST 类型名称集合，包含 `bare`、`Exception` 或 `BaseException`）；`handler_changed`（待实现的节点行范围与新增行交集，布尔值，`eq true`）。名称直接匹配不保证解析为内置类型。
- 输入与证据：head Python 源码、文件路径、三点 Diff；Finding 包含规则 ID、行范围、捕获类型、代码切片与差异、`pr_intrinsic_risk`。前后对照缺失时明确标记。

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

## 有效性计划

`literature_inherited`：后续构造裸捕获、`Exception`、`BaseException`、元组、具体异常、遮蔽、别名和差异边界样例，以卡片定义为判定依据检查命中与证据；覆盖 Python 版本及阈值待确定。当前未实现或验证。

