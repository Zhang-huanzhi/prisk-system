# 规则说明卡片：`data.django_raw_sql_execution`

> 本卡片同时服务于工程登记和毕业论文写作。没有证据的内容填写“待验证”，不要用推测替代结果。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `data.django_raw_sql_execution` |
| 规则名称 | Django 原生 SQL 执行 |
| 版本 | `v1` |
| 规则阵营 | `backend_contract` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

登记册 `lifecycle` 也是 `implemented`。013 按下面的闭集接入检测器和构造测试。这不是 `validated`。默认权重是 0，不改变默认可得权重。

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | Django 数据库 API 上、与新增行相交的调用。NetBox 的模型、查询和迁移是首要语境。路径不作为纳入或排除条件 |
| 依赖层级 | `framework`。阵营是后端契约；依赖的是 Django SQL API 的调用名，不是 SQL 字符串是否安全 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `High` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度仍是待验证的设计值，不是权重。

## 3. 为什么制定

### 观察到的工程问题

Django 应用里大多数查询走 ORM。直接执行 SQL 字符串时，参数是否分开传递、语句写在迁移里还是请求路径上，都会改变复核方式。

### 为什么值得检测

命中只标记「出现了原生 SQL 调用形态」。它不表示已经存在注入，也不表示迁移里的 SQL 一定不该出现。

### 现有规则为什么不能覆盖

`data.transaction_structure_changed` 把模型、迁移和事务调用上的结构变化合成一条粗线索。本规则只标记闭集里的原生 SQL 调用，而不是任何模型保存。[`data.django_destructive_migration`](../../breaking_impact/data.django_destructive_migration.md) 看 `DeleteModel` 和 `RemoveField`，不看 `cursor.execute`。

### 研究或工程价值

框架适配。011 拒绝在迁移路径政策缺失时默认纳入或默认忽略。路径写进证据。`migrations.RunSQL` 不在 Hit 闭集。

## 4. 检测定义

- **检测对象**：head AST 里与新增行相交的调用。接收者没有类型。
- **触发条件**：`direct_callee_name` 为 `RawSQL`，或 `callee` 的最后一段是 `execute`、`executemany` 或 `raw`。每个这样的调用一条 Finding。`report.execute(...)` 也会符合最后一段 `execute`。证据必须带上完整 `callee`，不能只写 `execute`。
- **触发特征**：`sql_callee`（`source` 为调用的属性最后一段或 `RawSQL` 直接名称；`value_type` 为 `string`；`operator` 为 `contains`；`threshold` 为 `RawSQL`、`execute`、`executemany`、`raw`；`required` 为 true）。`call_changed`（`source` 为与新增行相交；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true）。路径只作为证据，不作为通过或忽略条件。
- **不触发条件**：ORM 的 `filter`、`exclude`、`update`；字符串里出现 `SELECT` 但没有这些调用；未改动的历史 SQL。`extra`、`callproc` 和 `callee` 含有 `schema_editor` 不是不触发，而是 Unanalyzed。
- **输入**：同一文件的 head AST 和三点 Diff。检测器在 `backend/prisk/domain/django_raw_sql.py`，不读取 JSON 登记册。默认启用，默认权重是 0。
- **Finding**：规则 ID、完整 `callee`、路径、`pr_intrinsic_risk`、严重度 `High`。不截取 SQL 字符串来判断它是否安全。有直接名称时同时写出 `direct_callee_name`。
- **证据位置**：文件、调用切片、完整 `callee`、行号。
- **上下文切片**：该调用。不附带整段 SQL 作为必填栏。
- **影响类型**：数据访问形态。

`extra`、`callproc`，或 `callee` 文本包含 `schema_editor`：不命中。终态原因是 `missing_framework_context`。已有其他调用命中时，终态仍是 Hit，这条缺口留在 `summary.unanalyzed`。`callee` 为空，或切片被截断到不能确认最后一段：`unsupported_stage04_details`。别名 `run = cursor.execute` 之后的 `run(...)` 仍然漏报，不为此做数据流。限定名 `expressions.RawSQL` 的 `direct_callee_name` 不是 `RawSQL`，最后一段也不是闭集里的三个名字，因此不命中。

适用调用已经分类且没有上述缺口时是 NotFound。只有 SQL 字符串、没有相交调用时，是 `context_not_established`，不是 NotFound。迁移文件和视图文件使用同一闭集。

构造正例：`cursor.execute("SELECT id FROM dcim_device WHERE name = %s", [name])` 与新增行相交；`Device.objects.raw("SELECT * FROM dcim_device")`。构造反例：`Device.objects.filter(name=name)`；`note = "SELECT * FROM dcim_device"`。构造边界：`QuerySet.extra(...)` 记 Unanalyzed。

## 5. 理论与项目依据

- [Django：直接执行自定义 SQL](https://docs.djangoproject.com/en/stable/topics/db/sql/#executing-custom-sql-directly) 说明 `connection.cursor()` 与 `cursor.execute`。
- [Django：执行原生查询](https://docs.djangoproject.com/en/stable/topics/db/sql/#performing-raw-queries) 说明 `Manager.raw()` 和 `RawSQL`。
- [Django SQL 注入防护](https://docs.djangoproject.com/en/stable/topics/security/#sql-injection-protection) 要求把参数分开传递。该页不把每一次 `execute` 定义成漏洞。
- [QuerySet.extra](https://docs.djangoproject.com/en/stable/ref/models/querysets/#extra) 不在 Hit 闭集。以后若要纳入，需要另一次评审。
- NetBox 的模型和迁移出现在 [02 阶段调研](../../../versions/v1.0.0/02-PR采样&定风险场景/NetBox调研.md) 的数据与事务场景中。调研计数不是本规则的命中率。

## 6. 限制与反例

- 可能误报：参数化的管理 SQL、数据修复迁移和只读报表会命中。`report.execute` 的宽匹配也会命中。
- 可能漏报：别名、`getattr`、包在 helper 里的执行，以及 `expressions.RawSQL` 这种最后一段不是 `RawSQL` 的写法。
- Python 动态特性限制：调用名由变量给出时，最后一段确认不了。
- 规则不判断：不解析 SQL 方言，不连接数据库，不判断参数是否来自请求，不判断注入已经发生。
- 必须人工复核的上下文：调用位于迁移、管理命令还是请求处理，参数是序列还是拼进字符串，以及是否已有查询封装。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `empirical_required` |
| 验证方法 | 013 的构造样例检查新增行上的 `cursor.execute`、ORM `filter`、`QuerySet.extra` 的 Unanalyzed，以及迁移路径上的 `execute` 仍按同一闭集命中 |
| 数据集 | 013 构造样例。NetBox 实证集未圈定 |
| 判定依据 | 本卡片闭集。构造测试只说明检测器按闭集工作 |
| 指标 | 不报告 Precision、Recall 或注入是否发生 |
| 验收标准 | 闭集与 Unanalyzed 原因与本节一致，默认权重保持 0 |
| 未解决问题 | 迁移目录仍然没有纳入或排除政策。接收者没有类型。别名不做数据流 |
