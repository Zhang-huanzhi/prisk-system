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

拟定调用集合还没有冻结，迁移目录是否排除也还没有项目配置。因此保持 `draft`，不写检测器。

- 拟定对象：head AST 里与新增行相交的调用。候选形态包括 `cursor.execute`、`cursor.executemany`、`cursor.callproc`、`connection.cursor`、`schema_editor.execute`、`QuerySet.raw`、`Manager.raw`、`RawSQL(...)` 和 `QuerySet.extra`。这些大多是属性调用，不能照搬 `code.dynamic_execution` 的“只认直接名称”。
- 拟定触发：调用的属性名或直接名称落在冻结后的名单里，且调用节点与新增行相交。每个调用一条 Finding，证据写出实际匹配到的名字，便于区分 `execute` 和 `extra`。
- 拟定不触发：ORM 的 `filter`、`exclude`、`update`；字符串里出现 `SELECT` 但没有这些调用；未改动的历史 SQL。迁移文件是否整目录排除，必须由显式路径配置决定。配置缺失时，迁移候选标记未评估，不能默认当成业务 SQL，也不能默认忽略。
- 拟定特征：`sql_callee`（调用的属性名或 `RawSQL` 直接名称，`contains` 冻结名单）；`call_changed`（与新增行相交，布尔值，`eq true`）；`path_policy`（迁移排除配置存在且已套用，枚举 `included` 或 `excluded`）。`path_policy` 未配置时不产生通过结论。
- 输入与证据：head AST、三点 Diff，以及尚未提供的路径策略。影响类型设计为 `pr_intrinsic_risk`。Finding 不截取 SQL 字符串来判断它是否安全。

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

- 属性调用名单是否包含 `extra`、`callproc` 和 `schema_editor.execute`。
- `*/migrations/*.py` 的排除或单独标记没有成为项目配置。排除迁移不能顺便关闭破坏性迁移等其他规则。
- 004 的直接名称风格覆盖不了 `cursor.execute`。新的属性链规则还没有写成可测试的 stage04 字段。

## 有效性计划

`empirical_required`：名单和迁移路径政策冻结后，再写构造正例、反例和未配置路径。NetBox 上的人工标注用来判断命中是否符合定义。Django 安全文档只提供动机。当前没有检测器，不报告 Precision、Recall 或注入是否发生。
