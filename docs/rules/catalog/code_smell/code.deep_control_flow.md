# 深层控制流嵌套

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.deep_control_flow` |
| 版本 / 阵营 / 生命周期 | `v1` / `code_smell` / `implemented` |
| 负责人 | `Prisk-System` |
| 风险性质 / 依赖层级 | `pr_intrinsic` / `language` |
| 适用范围 | Python 源文件及其 PR 差异 |
| 分析目标层 / 证据形态 | `ast_syntax`, `diff_delta` / `code_slice`, `metric_value` |
| 严重度 / 一票抬升 | `Medium` / `false`，条件 `null` |

## 制定理由

多层 `if`、循环、`with` 和 `try` 叠在一起时，读者要同时记住更多分支。这是可维护性复核线索，不是缺陷结论，也不是圈复杂度。阈值写死在本卡片上，检测器不读取运行时配置，也不把 Pylint 的配置当作本项目阈值。

## 检测定义

- 对象：head AST 中的控制流语句节点，种类只包括 `if`、`for`、`async for`、`while`、`with`、`async with`、`try` 和 `try*`（`try_star`）。
- 深度：进入函数、异步函数或类时深度归零。语句自身使深度加一，再计入其体内的语句。`else`、`elif` 的后续分支、`finally` 和 `except` 处理器不再额外加一层。`elif` 按 CPython 的写法是外层 `if` 的 `orelse` 里唯一的 `If`，因此与所属 `if` 共用深度。手写的 `else` 里如果还有别的语句，其后的 `if` 会加一层；AST 无法区分“单独的 else-if”和 `elif`。
- 触发：该控制流节点的行范围与新增行相交，且 `nesting_depth > 4`。深度 4 不触发，深度 5 触发。每个超限节点一条 Finding。外层节点只要自己的深度不超过 4，即使行范围盖住了内层改动，也不触发。
- 不触发：深度小于等于 4；只改外层条件行而较深节点的行范围没有碰上新增行；未改动的深层块；只删除深层块。不计入：三元 `IfExp`、`assert`、布尔运算、`match` / `case`、推导式里的 `for` / `if`、函数嵌套本身。`match` 里面的 `if` 仍按 `if` 计数，但 `match` 不加深度。
- 特征：`nesting_depth`（当前函数、类或模块内的整数深度，`gt 4`）；`control_flow_changed`（节点行范围与新增行相交，布尔值，`eq true`）。阈值 `4` 是卡片常量 `CONTROL_FLOW_DEPTH_THRESHOLD`，不是登记册运行配置。
- 输入与证据：head 源码、路径、三点 Diff 新增行。Finding 含 `control_kind`、`nesting_depth`、`depth_threshold: 4`、`nesting_depth_basis`、行范围、切片和 `pr_intrinsic_risk`。控制流节点不进入既有五条粗粒度结构规则的 `structural_changes`，避免 `models.py` 里新出现的 `if` 被当成数据或事务结构变化。
- 旧节点：已有整数 `nesting_depth` 和合法 `control_kind` 时直接使用。没有这些字段时，只在未截断切片本身的深度已经大于 4 时，把该深度当作下界并报告，`nesting_depth_basis` 为 `segment_lower_bound`。切片更浅、无法解析或被截断时，节点进入 `summary.unanalyzed`，原因是 `unsupported_stage04_details`。005 之前的 stage04 没有 `control_flow` 节点；没有这种节点不等于已经证明深度不超过 4，重新解析后才能评估。

触发：

```python
def depth_five():
    if a:
        for b in items:
            while d:
                with e:
                    try:
                        touch()
                    except Error:
                        pass
```

不触发：

```python
def depth_four():
    if a:
        for b in items:
            while d:
                with e:
                    touch()

def elif_chain():
    if a:
        x()
    elif b:
        x()
```

## 依据

- [Python 复合语句](https://docs.python.org/3/reference/compound_stmts.html) 列出 `if`、`for`、`while`、`with` 和 `try` 的语句边界。本规则的深度按这些语句的 AST 形状计算。
- [Pylint R1702 too-many-nested-blocks](https://pylint.readthedocs.io/en/latest/user_guide/messages/refactor/too-many-nested-blocks.html) 把过深的嵌套块当作可维护性提示。它的默认上限属于 Pylint 配置，不自动成为本卡片的阈值；两边计入的块也不要求一致。
- 本规则不引用圈复杂度公式，也不把某个历史缺陷样本说成深度 5 的后果。

## 限制与反例

状态机、解析器和生成代码可以在深度 5 以上仍然清楚。长 `elif` 链不会加深度，真正难读的平铺分支可能漏报。`else: if` 在 AST 中与 `elif` 相同，也会少算一层。`match` 很深时，只有其中的 `if` / 循环 / `with` / `try` 继续累加。规则不计算 McCabe 复杂度，不判断分支是否可达，不把命中写成缺陷。

人工复核时应看超限节点的切片、它的 `control_kind` 和深度，以及这次新增行是落在深层语句上还是只碰到外层条件。

## 有效性计划

`literature_inherited`：迭代 005 已用构造样例检查深度 5、深度 4、`elif`、`else` 体内的 `if`、`try` 不把 `except` 再算一层、函数重置、`match`、推导式、三元表达式、只改外层行、未改动深层块和删除。阈值 4 没有用 NetBox 校准。Precision、Recall 和“多深才影响缺陷”都还没有结果，不能在本卡片里填写。
