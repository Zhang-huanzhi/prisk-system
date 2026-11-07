# 规则说明卡片：`code.bare_exception`

> 本卡片同时服务于工程登记和毕业论文写作。没有证据的内容填写“待验证”，不要用推测替代结果。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.bare_exception` |
| 规则名称 | 宽泛或裸异常捕获 |
| 版本 | `v1` |
| 规则阵营 | `code_smell` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

登记册 `lifecycle` 也是 `implemented`。这表示检测器已经接入并用构造样例检查过，不是 `validated`。017 改的是卡片合同。检测器还没有按新合同拆开，见第 7 节。

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | Python 源文件及其 PR 差异中的普通 `ExceptHandler` |
| 依赖层级 | `language`。阵营是代码异味；依赖的是 Python 异常层次，不是框架权限类 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `Medium` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

## 3. 为什么制定

### 观察到的工程问题

裸 `except:` 会捕获 `SystemExit` 和 `KeyboardInterrupt`。显式 `except BaseException:` 覆盖同一层。变更里出现这两种写法时，故障和控制流的边界需要单独看。

### 为什么值得检测

PEP 8 把裸 `except:` 写成过宽的捕获，并写明若意图是捕获程序错误，应使用 `except Exception:`。这两种写法的后果不同，不能共用一条 Hit。命中只要求复核，不证明缺陷。程序边界的统一记录及重新抛出也可能有意使用裸捕获。

### 现有规则为什么不能覆盖

[`code.swallowed_exception`](code.swallowed_exception.md) 看处理体是不是只有 `pass`，不看捕获范围。两条规则可以同时命中同一分支，Finding 必须分别说明原因。本规则不要求处理体为空。

### 研究或工程价值

文献继承的语言级规则。017 按 PEP 8 把 `except Exception:` 移出本规则的 Hit。不为它新建规则 ID。

## 4. 检测定义

- **检测对象**：head AST 中普通 `ExceptHandler`。类型为空（裸 `except:`），或直接名称是 `BaseException`，包括异常元组中直接包含 `BaseException`。
- **触发条件**：处理分支头或处理体与新增 Diff 行相交，且满足上述类型。多个满足条件的类型属于同一分支时只生成一条。严重度是 `Medium`。
- **触发特征**：`handler_type`（`source` 为 head AST `ExceptHandler.type` 的直接名称集合；`value_type` 为 `string`；`operator` 为 `contains`；`threshold` 为 `bare`、`BaseException`；`required` 为 true）。`handler_changed`（`source` 为该节点行范围与新增行的交集；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true）。名称直接匹配不保证解析为内置类型。
- **不触发条件**：`except Exception:`，包括元组里只有 `Exception` 的写法；仅捕获 `ValueError` 等具体类型；不与新增行相交。`except Exception:` 不是本规则的 Hit，也不是较低严重度的第二条 Finding。
- **输入**：head Python 源码、文件路径、三点 Diff 新增行。
- **Finding**：规则 ID、行范围、捕获形式、代码切片、`pr_intrinsic_risk`、严重度 `Medium`。Finding 必须显示实际捕获形式是裸捕获还是 `BaseException`。前后对照缺失时标记 `unavailable`，不复制 hunk 原文。
- **证据位置**：文件、节点行范围、捕获形式。
- **上下文切片**：该 `ExceptHandler`。
- **影响类型**：可维护性。

解析或定位失败时标记未分析，不视作通过。适用处理分支已经看完、没有本规则的证据缺口、也没有解析失败时，终态是 NotFound。没有这种节点是 `context_not_established`。这些终态不是另一个生命周期字段。

设计上的触发：

```python
try:
    run()
except:
    logger.exception("failed")
    raise
```

设计上的不触发：

```python
try:
    run()
except Exception:
    logger.exception("failed")
    raise

try:
    run()
except ValueError:
    recover()
```

运行时差异：`backend/prisk/domain/code_smells.py` 的 `BROAD_HANDLER_NAMES` 仍是 `bare`、`Exception`、`BaseException`。当前检测器仍会为 `except Exception:` 生成 `code.bare_exception` Finding。017 不改这段 Python。卡片合同与检测器不一致，直到后续任务把 `Exception` 移出该元组并改构造测试。

## 5. 理论与项目依据

- [PEP 8：异常处理](https://peps.python.org/pep-0008/#programming-recommendations) 建议尽可能捕获具体异常，并写明裸 `except:` 会捕获 `SystemExit` 和 `KeyboardInterrupt`；若意图捕获程序错误，应使用 `except Exception:`。PEP 8 不表示每次裸捕获都是缺陷。
- [CWE-396](https://cwe.mitre.org/data/definitions/396.html) 说明捕获高层通用异常可能隐藏诊断信息。该 CWE 不专指 Python，也不把 `except Exception:` 定义成与裸 `except:` 相同。
- [except 子句](https://docs.python.org/3/reference/compound_stmts.html#except-clause) 与 [异常层次](https://docs.python.org/3/library/exceptions.html#exception-hierarchy) 说明 `KeyboardInterrupt` 和 `SystemExit` 继承自 `BaseException`，不继承自 `Exception`。

## 6. 限制与反例

- 可能误报：进程边界有意使用裸捕获，记录后重新抛出。名称被局部遮蔽成另一个 `BaseException` 也会命中。
- 可能漏报：别名、自定义异常继承、动态类型和解析失败。`except Exception:` 按本卡片是不触发，不是漏报。
- Python 动态特性限制：异常类型由变量给出时，直接名称集合为空，不能把它记成裸捕获。
- 规则不判断：异常是否被吞掉、业务是否受损、处理体是否为空。
- 必须人工复核的上下文：处理体、异常类型是否被遮蔽、该分支是不是进程边界。异常组及 `except*` 的支持待设计。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `literature_inherited` |
| 验证方法 | 迭代 004 的构造样例覆盖了裸捕获、`Exception`、`BaseException`、元组和具体异常。那些测试证明的是当时的检测器。017 之后要以本卡片重写样例：`except Exception:` 不得再作为本规则的正例 |
| 数据集 | 迭代 004 构造样例；项目实证数据集待确定 |
| 判定依据 | 本卡片的设计合同。运行时行为在检测器跟上之前不是这张合同的 Ground Truth |
| 指标 | 构造样例通过率、证据完整率。不预填 Precision 或 Recall |
| 验收标准 | 检测器只对裸 `except:` 和 `BaseException` 产生本规则 Finding，并且构造测试按这个合同通过。当前还没有做到 |
| 未解决问题 | 运行时仍把 `except Exception:` 与裸 `except:` 放在同一条 Finding 里。`except*` 仍待设计。实证数据范围待补齐。生命周期保持 `implemented`，不把这个差异写成 `validated` |
