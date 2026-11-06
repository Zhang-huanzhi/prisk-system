# Django 原生 SQL 执行

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `data.django_raw_sql_execution` |
| 版本 / 阵营 / 生命周期 | `v1` / `backend_contract` / `draft` |
| 负责人 | `Prisk-System` |
| 风险性质 / 依赖层级 | `pr_intrinsic` / `framework` |
| 适用范围 | Django 数据库 API；NetBox 的模型、查询和迁移是首要语境 |
| 分析目标层 / 证据形态 | `ast_syntax`, `diff_delta` / `code_slice`, `symbol_pair` |
| 严重度 / 一票抬升 | `High` / `false`，条件 `null`；严重度仍是待验证的设计值 |

## 制定理由

Django 应用里大多数查询走 ORM。直接执行 SQL 字符串时，参数是否分开传递、语句是写在迁移里还是请求路径上，都会改变复核方式。命中只标记“出现了原生 SQL 调用形态”，不表示已经存在注入，也不表示迁移里的 SQL 一定不该出现。

`data.transaction_structure_changed` 把模型、迁移和事务调用上的结构变化合成一条粗线索。本规则如果实现，应只标记原生 SQL 调用，而不是任何模型保存。

## 检测定义

005 的拟定合同如下。与后面的「011 补强」冲突时，以 011 补强为准。调用闭集和路径政策当时都未冻结，因此保持 `draft`，不写检测器。

- 拟定对象：head AST 里与新增行相交的调用。候选形态包括 `cursor.execute`、`cursor.executemany`、`cursor.callproc`、`connection.cursor`、`schema_editor.execute`、`QuerySet.raw`、`Manager.raw`、`RawSQL(...)` 和 `QuerySet.extra`。这些大多是属性调用，不能照搬 `code.dynamic_execution` 的“只认直接名称”。
- 拟定触发：调用的属性名或直接名称落在冻结后的名单里，且调用节点与新增行相交。每个调用一条 Finding，证据写出实际匹配到的名字，便于区分 `execute` 和 `extra`。
- 拟定不触发：ORM 的 `filter`、`exclude`、`update`；字符串里出现 `SELECT` 但没有这些调用；未改动的历史 SQL。
- 拟定特征：`sql_callee`（调用的属性名或 `RawSQL` 直接名称，`contains` 下面「011 补强」的闭集）；`call_changed`（与新增行相交，布尔值，`eq true`）。路径只作为证据，不作为通过或忽略条件。
- 输入与证据：同一文件的 head AST 和三点 Diff。影响类型设计为 `pr_intrinsic_risk`。Finding 不截取 SQL 字符串来判断它是否安全。

示例：

```python
with connection.cursor() as cursor:
    cursor.execute("SELECT id FROM dcim_device WHERE name = %s", [name])
Device.objects.raw("SELECT * FROM dcim_device")
```

不作为本规则触发的例子：

```python
Device.objects.filter(name=name)
note = "SELECT * FROM dcim_device"
```

## 011 补强

005 要求迁移路径政策缺失时既不默认纳入、也不默认忽略。011 保持这个拒绝：不新增路径政策，不把 `migrations` 记成安全，也不把业务文件记成更危险。路径写进证据，供人工看调用落在迁移、命令还是视图附近。政策仍未设定，所以不能把“没有政策”写成 NotFound 或写成排除。

设计上的 Hit 闭集只包括调用节点已经能提供的名字：

- `direct_callee_name` 为 `RawSQL`；
- `callee` 的最后一段是 `execute`、`executemany` 或 `raw`。

这三项覆盖文档中的 [`cursor.execute`](https://docs.djangoproject.com/en/stable/topics/db/sql/#executing-custom-sql-directly)、`executemany` 的同一游标接口、[`Manager.raw()`](https://docs.djangoproject.com/en/stable/topics/db/sql/#performing-raw-queries) 和 [`RawSQL`](https://docs.djangoproject.com/en/stable/ref/models/expressions/#django.db.models.expressions.RawSQL)。接收者没有类型。`report.execute(...)` 也会符合最后一段 `execute`。这是已知的宽匹配，证据必须带上完整 `callee`，不能只写 `execute`。

`extra`、`callproc` 和 `schema_editor.execute` 不在闭集里。[`QuerySet.extra`](https://docs.djangoproject.com/en/stable/ref/models/querysets/#extra) 与游标执行不是同一接口；[`callproc`](https://docs.djangoproject.com/en/stable/topics/db/sql/#calling-stored-procedures) 是存储过程。见到最后一段是 `extra`、`callproc`，或 `callee` 含有 `schema_editor` 时，记 Unanalyzed，原因是 `missing_framework_context`，不是 Hit，也不是 NotFound。

`callee` 为空或调用切片被截断到不能确认最后一段时，记 `unsupported_stage04_details`。别名 `run = cursor.execute` 之后的 `run(...)` 仍然漏报，不为此做数据流。

构造正例：`cursor.execute("SELECT id FROM dcim_device WHERE name = %s", [name])` 与新增行相交。构造反例：`Device.objects.filter(name=name)`。构造边界：`QuerySet.extra(...)` 记 Unanalyzed。迁移文件里的 `cursor.execute` 与视图文件里的同形调用使用同一闭集，路径留在证据里。

这些边界写清之后，卡片仍是 `draft`。闭集还没有构造测试，接收者也还没有收窄，因此不写成 `registered`。

## 依据

- [Django：直接执行自定义 SQL](https://docs.djangoproject.com/en/stable/topics/db/sql/#executing-custom-sql-directly) 说明 `connection.cursor()` 与 `cursor.execute`。
- [Django：执行原生查询](https://docs.djangoproject.com/en/stable/topics/db/sql/#performing-raw-queries) 说明 `Manager.raw()` 和 `RawSQL`。
- [Django SQL 注入防护](https://docs.djangoproject.com/en/stable/topics/security/#sql-injection-protection) 要求把参数分开传递，并指出查询由开发者自己拼接时需要额外小心。该页不把每一次 `execute` 定义成漏洞。
- [QuerySet.extra](https://docs.djangoproject.com/en/stable/ref/models/querysets/#extra) 已被 Django 标为可能被后续版本弃用的接口。它是否与 `cursor.execute` 放在同一条规则里，本卡片尚未冻结。
- NetBox 的模型和迁移出现在 [02 阶段调研](../../../versions/v1.0.0/02-PR采样&定风险场景/NetBox调研.md) 的数据与事务场景中。调研计数不是本规则的命中率。

## 限制与反例

参数化的管理 SQL、数据修复迁移和只读报表会命中，需要人工看语句和调用场景。别名 `run = cursor.execute` 之后的 `run(...)`、通过 `getattr` 调用，以及包在 helper 里的执行会漏报。`extra()` 的风险和 `cursor.execute` 不一样，合并报告可能过宽。规则不解析 SQL 方言，不连接数据库，不判断参数是否来自请求。

人工复核应看调用位于迁移、管理命令还是请求处理，参数是序列还是拼进字符串，以及是否已有查询封装。

## 未冻结、因此保持 draft 的部分

- `extra`、`callproc` 和 `schema_editor.execute` 明确不在 Hit 闭集，见到时 Unanalyzed。以后若要纳入，需要另一次评审。
- 迁移目录仍然没有纳入或排除政策。011 不发明该政策，也不让它阻断上面的名字闭集。排除迁移不能顺便关闭破坏性迁移等其他规则。
- `callee` 已经在 call 节点上。缺的是按闭集读取它的检测器和构造测试，不是一张跨文件调用图。

## 有效性计划

`empirical_required`：名单和迁移路径政策冻结后，再写构造正例、反例和未配置路径。NetBox 上的人工标注用来判断命中是否符合定义。Django 安全文档只提供动机。当前没有检测器，不报告 Precision、Recall 或注入是否发生。
