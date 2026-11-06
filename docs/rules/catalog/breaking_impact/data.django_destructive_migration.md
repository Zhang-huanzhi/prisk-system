# 破坏性数据库迁移风险

> 本卡片是设计记录。样例都是构造样例，不是某个已合并 PR 的复原。生命周期保持 `draft`：没有检测器，也没有运行终态。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `data.django_destructive_migration` |
| 规则名称 | 破坏性数据库迁移风险 |
| 版本 | `v1` |
| 规则阵营 | `breaking_impact` |
| 生命周期 | `draft` |
| 负责人 | `Prisk-System` |

登记阵营是 `breaking_impact`。这不表示已经证实外部数据丢失。

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `external_impact` |
| 适用范围 | 路径中含有 `migrations` 目录段的同一 Python 文件，且调用的是下面两个操作类 |
| 依赖层级 | `database`。阵营是变更冲击；依赖的是 Django 迁移操作的类名，不是数据库里的真实行数 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `Critical` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度是待验证的设计值。`Critical` 不表示一票抬升，当前评分权重也不因此变化。

## 3. 为什么制定

### 观察到的工程问题

迁移文件里出现删除模型或删除字段的操作。Django 写明 `DeleteModel` 会删表，`RemoveField` 反向执行时也无法找回已经丢失的数据。

### 为什么值得检测

这类操作和普通的 `AddField` 不是同一复核成本。审查者需要单独看到删除表和删除列，而不是只看到“迁移文件有改动”。

### 现有规则为什么不能覆盖

`data.transaction_structure_changed` 把模型、迁移和事务调用收成一条粗线索。`data.django_non_null_constraint_tightened` 只看非空收紧。`data.django_raw_sql_execution` 看原生 SQL 调用，不看迁移操作类名。

### 研究或工程价值

框架适配。操作类以 Django 迁移操作参考为准。不把每条 `RunSQL` 都定义成破坏性操作。

## 4. 检测定义

### 适用性

文件路径按段含有 `migrations`，调用名的最后一段是 `DeleteModel` 或 `RemoveField`，且该调用与新增行相交。路径判断只看本文件路径字符串，不读 Django 的迁移加载器。

### 检测边界

- [`DeleteModel`](https://docs.djangoproject.com/en/stable/ref/migration-operations/#django.db.migrations.operations.DeleteModel) 从项目历史删除模型，并从数据库删除其表。
- [`RemoveField`](https://docs.djangoproject.com/en/stable/ref/migration-operations/#django.db.migrations.operations.RemoveField) 删除字段。文档写明数据丢失不可逆；字段不可空且没有默认值时，反向操作也不可逆。

[`RunSQL`](https://docs.djangoproject.com/en/stable/ref/migration-operations/#django.db.migrations.operations.RunSQL) 与 [`RunPython`](https://docs.djangoproject.com/en/stable/ref/migration-operations/#django.db.migrations.operations.RunPython) 可以写任意 SQL 或 Python。文档示例包含插入数据，并不把这两个类定义成删除。见到它们时记 Unanalyzed，不记 Hit，也不记 NotFound。

`AlterField` 交给非空规则，不在这里重复。`RenameModel` 在文档中是重命名；自动检测器在同时改名又改字段时可能生成会丢数据的迁移，但那不是 `RenameModel` 类本身的定义。本规则不把 `RenameModel` 记成 Hit。

### 检测对象

迁移文件中与新增行相交的调用。

### 触发条件

适用路径上，调用的最后一段属性名是 `DeleteModel` 或 `RemoveField`。每个调用一条设计 Finding。

### 触发特征

- `operation_name`：`source` 为 `details.callee` 的最后一段，或 `direct_callee_name`；`value_type` 为 `string`；`operator` 为 `contains`；`threshold` 为 `DeleteModel`、`RemoveField`；`required` 为 true。
- `call_changed`：`source` 为调用与新增行的交集；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true。
- `migration_path`：`source` 为文件路径的目录段；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为路径含 `migrations`；`required` 为 true。

这些特征使用现有 call 节点和文件路径。不需要新的跨文件迁移图。

### 不触发条件

`AddField`、`CreateModel`、`RenameField`；操作出现在 `migrations` 以外的文件；历史迁移文件没有新增行。

### 输入

同一文件的 head AST、三点 Diff 和路径。不连接数据库，不展开 `dependencies` 指向的其他迁移。

### Finding

设计线索：规则 ID、操作名、文件和行、设计标签 `external_impact`。不证明生产库已经丢数据。本任务不生成 Finding。

### 证据位置

路径、调用切片、操作名、新增行号。

### 上下文切片

该操作调用。若同一列表里紧邻的操作能完整落在未截断切片中，可以一并展示；不读取其他迁移文件。

### 影响类型

数据保留。

### Unanalyzed

设计预期，不是运行结果。

- `RunSQL`、`RunPython`、`SeparateDatabaseAndState`，以及未列入的操作类：`missing_framework_context`。不解析 SQL 字符串来判断它是不是 `DROP`。
- 路径不含 `migrations`，但调用名相同：`missing_framework_context`。可能是测试里的构造，不记 Hit。
- `callee` 为空或切片截断到无法确认最后一段名字：`unsupported_stage04_details`。
- 迁移是否已经应用到某个环境、是否被 squash：未知。未知不改变本文件里的类名判断，也不被写成已部署结论。

### 构造样例

正例：`app/migrations/0004_drop_asset.py` 的新增行含有 `migrations.DeleteModel(name="Asset")` 或 `migrations.RemoveField(model_name="device", name="asset_tag")`。

反例：同一目录里只有 `migrations.AddField(...)`。另一个反例：`tests/test_migrations.py` 里调用了 `DeleteModel`，路径段不是 `migrations`。

边界：`migrations.RunSQL("DROP TABLE dcim_device")` 看起来像删除，但本规则不解析 SQL，记 Unanalyzed。

## 5. 理论与项目依据

- [迁移操作参考](https://docs.djangoproject.com/en/stable/ref/migration-operations/) 是本卡片的操作类来源。
- [`DeleteModel`](https://docs.djangoproject.com/en/stable/ref/migration-operations/#django.db.migrations.operations.DeleteModel) 与 [`RemoveField`](https://docs.djangoproject.com/en/stable/ref/migration-operations/#django.db.migrations.operations.RemoveField) 的语句已在检测边界引用。
- [`AlterField`](https://docs.djangoproject.com/en/stable/ref/migration-operations/#django.db.migrations.operations.AlterField) 说明它会修改 `null` 等字段属性。该变化属于非空规则的候选范围，不在本规则重复触发。
- NetBox 调研把模型和迁移列进数据场景。调研计数不是命中率。

## 6. 限制与反例

- 可能误报：删除的是尚未上线的模型，或迁移只存在于未执行的分支。类名仍然是删除操作。
- 可能漏报：用 `RunSQL` 删除表，或在 `RunPython` 里调用 `schema_editor`。
- Python 动态特性限制：操作列表由循环生成。
- 规则不判断：备份是否存在、反向迁移能否成功、行是否已经丢失。
- 必须人工复核的上下文：迁移依赖、是否还有数据迁移把行拷走，以及发布说明。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `empirical_required` |
| 验证方法 | 构造样例覆盖两个操作类、`AddField`、测试文件和 `RunSQL`。不连接数据库，不下载真实 PR |
| 数据集 | 未圈定 |
| 判定依据 | 将来的人工标注。官方文档只定义操作类，不证明本项目的误报率 |
| 指标 | 不预填 |
| 验收标准 | 待实现任务再写 |
| 未解决问题 | SQL 字符串不分类；迁移图不建；没有检测器 |
