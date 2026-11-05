# 动态代码执行调用

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.dynamic_execution` |
| 版本 / 阵营 / 生命周期 | `v1` / `code_smell` / `registered` |
| 负责人 | `Prisk-System` |
| 风险性质 / 依赖层级 | `pr_intrinsic` / `language` |
| 适用范围 | Python 源文件及其 PR 差异 |
| 分析目标层 / 证据形态 | `ast_syntax`, `diff_delta` / `code_slice`, `symbol_pair` |
| 严重度 / 一票抬升 | `Medium` / `false`，条件 `null` |

## 制定理由

`eval` 和 `exec` 可执行动态代码；处理不可信输入时需关注代码来源及后续使用，但合法场景也可能使用这些调用。本规则只报告直接调用以供复核，不证明不可信数据可达、代码被执行或存在漏洞。`compile` 只将源码编译为代码或 AST 对象，本身不执行代码，因此不纳入此规则；如有需要，应另立编译产物流向分析。

## 检测定义

- 对象：head AST 中函数位置为直接名称 `eval` 或 `exec` 的 `Call` 节点；不包含 `compile`、属性调用、别名或字符串中的名字。
- 触发：调用节点行范围与新增 Diff 行相交且名称匹配；每个调用生成一条复核 Finding，并标明 `eval` 或 `exec`。
- 不触发：`obj.eval()`、`ast.literal_eval()`、名称只在字符串或注释中出现、未改动的调用。解析或定位失败时标记未分析。
- 特征：`direct_callee_name`（待实现的 `Call.func.id`，属于 `eval` 或 `exec`）；`call_changed`（待实现的调用节点行范围与新增行交集，布尔值，`eq true`）。直接名称可能被遮蔽。
- 输入与证据：head Python 源码、路径、三点 Diff；Finding 包含规则 ID、调用名称、行范围、代码切片及差异、`pr_intrinsic_risk`。前后对照缺失时明确标记。

触发：

```python
result = eval(expression)
exec(source)
```

不触发：

```python
result = ast.literal_eval(expression)
text = "eval(source)"
```

## 依据

- **MITRE CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code ('Eval Injection')** ([CWE-95](https://cwe.mitre.org/data/definitions/95.html)) 适用于攻击者可影响被动态求值代码指令的场景；它不意味着任何 `eval`/`exec` 调用本身就是注入漏洞。
- **OWASP Top 10:2021 A03 Injection** ([A03:2021](https://owasp.org/Top10/A03_2021-Injection/)) 提供注入风险的大类背景，不是 Python `eval`/`exec` 静态规则定义，也不能单独支持本规则的触发条件。
- **Bandit** 是 Python 安全检查工具，其规则 [B307](https://bandit.readthedocs.io/en/latest/blacklists/blacklist_calls.html) 针对 `eval` 并建议考虑 `ast.literal_eval`；[B102](https://bandit.readthedocs.io/en/latest/plugins/b102_exec_used.html) 针对 `exec`。这是成熟工具规则的可比依据，不是本项目检测器有效性证明。
- [Python 内置函数 eval](https://docs.python.org/3/library/functions.html#eval) 和 [exec](https://docs.python.org/3/library/functions.html#exec) 描述调用语义；[`compile`](https://docs.python.org/3/library/functions.html#compile) 单列说明其仅编译源码。

## 限制与反例

可信固定输入、DSL 或模板引擎等合法场景可能命中；名称被用户代码遮蔽也会误报。`builtins.eval`、别名、反射、间接调用或解析失败可能漏报。规则不追踪数据流、不判断输入可信度或代码是否真正执行；人工应复核数据来源、调用绑定及执行场景。

## 有效性计划

`literature_inherited`：后续以 `eval`/`exec` 直接调用、可信与不可信来源仅作为人工语义差异、`compile` 排除、遮蔽、别名、属性调用、注释字符串和新增行边界构造样例；以卡片定义为判定依据，检查 Finding 及位置。CWE/OWASP/Bandit 支持动机和可比规则，不证明本项目检测器准确性。数据集和验收标准待确定，目前没有实现或验证结果。

