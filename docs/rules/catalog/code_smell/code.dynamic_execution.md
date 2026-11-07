# 规则说明卡片：`code.dynamic_execution`

> 本卡片同时服务于工程登记和毕业论文写作。没有证据的内容填写“待验证”，不要用推测替代结果。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.dynamic_execution` |
| 规则名称 | 动态代码执行调用 |
| 版本 | `v1` |
| 规则阵营 | `code_smell` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

登记册 `lifecycle` 也是 `implemented`。004 已接入检测器。这不是 `validated`。

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | Python 源文件及其 PR 差异中、函数位置为直接名称 `eval` 或 `exec` 的调用 |
| 依赖层级 | `language`。阵营是代码异味；依赖的是内置调用名，不是数据流是否不可信 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `Medium` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

## 3. 为什么制定

### 观察到的工程问题

`eval` 和 `exec` 可执行动态代码。处理不可信输入时需要看代码来源及后续使用。合法场景也可能使用这些调用。

### 为什么值得检测

本规则只报告直接调用以供复核。它不证明不可信数据可达、代码被执行或存在漏洞。

### 现有规则为什么不能覆盖

`compile` 只将源码编译为代码或 AST 对象，本身不执行代码，因此不纳入此规则。若要跟踪编译产物，应另立规则。`ast.literal_eval` 不是这两个直接名称。

### 研究或工程价值

文献与工具规则继承。CWE、OWASP 和 Bandit 提供可比动机，不是本项目检测器的有效性证明。

## 4. 检测定义

- **检测对象**：head AST 中函数位置为直接名称 `eval` 或 `exec` 的 `Call`。不包含 `compile`、属性调用、别名或字符串中的名字。
- **触发条件**：调用节点行范围与新增 Diff 行相交且名称匹配。每个调用一条 Finding，并标明 `eval` 或 `exec`。严重度 `Medium`。
- **触发特征**：`direct_callee_name`（`source` 为 head AST `Call.func` 为 `Name` 时的 id；`value_type` 为 `string`；`operator` 为 `contains`；`threshold` 为 `eval`、`exec`；`required` 为 true）。`call_changed`（`source` 为调用节点行范围与新增行交集；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true）。直接名称可能被遮蔽。
- **不触发条件**：`obj.eval()`、`ast.literal_eval()`、`compile(...)`、名称只在字符串或注释中出现、未改动的调用。
- **输入**：head Python 源码、路径、三点 Diff。切片缺失时标记 `unavailable`。不复制 hunk 原文。
- **Finding**：规则 ID、调用名称、行范围、代码切片、`pr_intrinsic_risk`、严重度 `Medium`。
- **证据位置**：文件、调用名称、行范围。
- **上下文切片**：该调用。不附带数据流。
- **影响类型**：可维护性与复核优先级。不是注入结论。

解析或定位失败时标记未分析。产生 Finding 时运行终态是 Hit。适用调用已经分类、没有证据缺口、也没有解析失败时，终态是 NotFound。没有这种调用是 `context_not_established`。

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

## 5. 理论与项目依据

- [CWE-95](https://cwe.mitre.org/data/definitions/95.html) 适用于攻击者可影响被动态求值的代码。它不意味着任何 `eval` / `exec` 调用本身就是注入漏洞。
- [OWASP A03:2021](https://owasp.org/Top10/A03_2021-Injection/) 提供注入风险的大类背景，不能单独支持本规则的触发条件。
- Bandit [B307](https://bandit.readthedocs.io/en/latest/blacklists/blacklist_calls.html) 针对 `eval`，[B102](https://bandit.readthedocs.io/en/latest/plugins/b102_exec_used.html) 针对 `exec`。这是可比依据，不是本项目有效性证明。
- [eval](https://docs.python.org/3/library/functions.html#eval)、[exec](https://docs.python.org/3/library/functions.html#exec) 与 [`compile`](https://docs.python.org/3/library/functions.html#compile) 描述调用语义。`compile` 单列排除。

## 6. 限制与反例

- 可能误报：可信固定输入、DSL 或模板引擎。名称被用户代码遮蔽成 `eval` 也会命中。
- 可能漏报：`builtins.eval`、别名、反射和间接调用。
- Python 动态特性限制：规则不追踪数据流，不解析 `Name` 的绑定目标。
- 规则不判断：输入是否可信，代码是否真正执行。
- 必须人工复核的上下文：数据来源、调用绑定及执行场景。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `literature_inherited` |
| 验证方法 | 迭代 004 的构造样例覆盖直接 `eval` / `exec`、`compile` 排除、`ast.literal_eval`、属性调用、别名、字符串、注释和新增行边界 |
| 数据集 | 004 构造样例。实证数据集待确定 |
| 判定依据 | 本卡片。测试不判断数据流 |
| 指标 | 不证明 Precision 或 Recall |
| 验收标准 | 构造样例按直接名称命中。这不是实证验收 |
| 未解决问题 | 实证数据集和验收标准仍待确定。属性调用继续排除 |
