# 规则说明卡片：`data.django_field_rename_without_db_column`

> 本卡片是设计记录。样例都是构造样例，不是某个已合并 PR 的复原。生命周期是 `implemented`（022 接入检测器与构造测试）；默认权重 0，不是 `validated`，也没有真实 PR 实证。严重度与风险性质是工程负责人的临时判断，不是终局。本规则不运行 `makemigrations`，也不证明迁移文件里已经出现 `RemoveField` 与 `AddField`。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `data.django_field_rename_without_db_column` |
| 规则名称 | 模型字段改名缺少 db_column |
| 版本 | `v1` |
| 规则阵营 | `breaking_impact` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

登记阵营是 `breaking_impact`。这不表示已经证实外部数据丢失。

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `external_impact` |
| 适用范围 | 同一非迁移 Python 文件中，直接基类最后一段为 `Model` 的类体字段 |
| 依赖层级 | `database`。阵营是变更冲击。依赖的是字段名与 `db_column` 的对应，不是某张表的行数 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `High` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度 `High` 是临时判断。`RemoveField` 本身仍由破坏性迁移规则以 `Critical` 表达。本规则看不到那条操作，所以不用 `Critical`，也不设一票抬升。后续算法阶段可以修订。

## 3. 为什么制定

### 观察到的工程问题

模型类里一个字段的 Python 名字换成了另一个名字，新的字段构造没有 `db_column`。

### 为什么值得检测

未设置 `db_column` 时，Django 用字段名作为数据库列名。`RenameField` 在未设置 `db_column` 时会连列名一起改。若自动检测器没有把去掉的名字和新增的名字配成重命名，就可能变成删除字段再新增字段。`RemoveField` 的数据丢失不可逆。审查者需要在模型源文件上看到这个配对，而不是只在迁移操作类上看到删除。

### 现有规则为什么不能覆盖

[`data.django_destructive_migration`](data.django_destructive_migration.md) 只看路径段含 `migrations` 的 `DeleteModel` 与 `RemoveField`。本规则不看迁移操作，也不在迁移文件里触发。[`data.django_non_null_constraint_tightened`](data.django_non_null_constraint_tightened.md) 只看 `null`。两条规则都不比较字段 Python 名字的一对一替换。

### 研究或工程价值

框架适配。配对条件收成「恰好一个名字消失、恰好一个名字出现、构造器最后一段相同、新调用没有 `db_column`」。多字段同时改动不猜测哪两个是一对。

## 4. 检测定义

### 比较单位

base 与 head 都存在的同一个类。类的直接基类最后一段必须是 `Model`，或按 [已知框架基类映射](../../known-framework-bases.md) 视为 `Model`（`NetBoxModel`）。比较的是该类体里字段赋值的名字集合，以及 head 上新名字那一次调用的关键字。

### 适用性

文件路径按段不含 `migrations`。类体里的赋值或带值注解，值是调用，调用名最后一段以 `Field` 结尾，或最后一段恰好是 `ForeignKey`。这与非空规则里的字段构造表面相同，不用于识别序列化器。`NetBoxModel` 按映射表视为 `Model`。未列入的项目基类不是 `Model`。不读父类文件。

字段节点保存名字和值指纹，不保存关键字名。同一次赋值上的调用节点保存 `keyword_names` 和 `callee`。配对要在同一条赋值里完成。对不上时不能只用指纹相同来声明 `db_column` 存在。

### 闭集

同时满足才是设计上的改名形态：

- base 有而 head 没有的字段名恰好一个；
- head 有而 base 没有的字段名恰好一个；
- 两次调用的最后一段相等，且都属于上面的字段构造表面；
- head 这次调用的 `keyword_names` 不含 `db_column`。

`db_column` 出现在关键字里就不是本规则的形态，不管字符串是否等于旧列名。写错列名不另设 Hit。

### 触发条件

比较单位满足闭集，且消失的赋值与删除行相交，或新赋值与新增行相交。一个类一条设计 Finding。证据写出旧名字、新名字和构造器最后一段。

全新的类只出现在 head 时，不把类体里的字段记成改名。只增加字段或只删除字段也不是这个闭集。

### 触发特征

- `model_base`：`source` 为类节点 `details.bases` 的最后一段；`value_type` 为 `string`；`operator` 为 `contains`；`threshold` 为 `Model`，或映射表中的 `NetBoxModel`；`required` 为 true。
- `renamed_pair`：`source` 为同一类字段名在 base/head 的差集；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为两侧差集大小都是 1；`required` 为 true。
- `constructor_name`：`source` 为两次调用的最后一段；`value_type` 为 `string`；`operator` 为 `eq`；`threshold` 为两侧相等且属于字段构造表面；`required` 为 true。
- `db_column`：`source` 为 head 调用的 `keyword_names`；`value_type` 为 `boolean`；`operator` 为 `missing`；`threshold` 为 `db_column`；`required` 为 true。
- `field_changed`：`source` 为旧赋值与删除行或新赋值与新增行的交集；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true。
- `migration_path`：`source` 为文件路径的目录段；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为路径不含 `migrations`；`required` 为 true。

### 不触发条件

新字段带有 `db_column`；差集不是恰好一个对一个；构造器最后一段不同；路径段含 `migrations`；类只出现在一侧；直接基类最后一段不是 `Model`，也不在映射表里。

### 输入

同一文件的 base/head AST、字段节点、字段构造调用和三点 Diff。不运行 `makemigrations`，不打开其他迁移文件。

### Finding

设计线索：规则 ID、类限定名、旧字段名、新字段名、构造器最后一段、设计标签 `external_impact`。不证明自动检测器已经发出 `RemoveField` 和 `AddField`，也不证明列上的数据已经丢失。022 生成运行时 Finding；默认权重 0。

### 证据位置

文件、类限定名、两处字段切片、`keyword_names`、行号。

### 上下文切片

旧赋值和新赋值。同一类里其他未改字段不需要整份列出。

### 影响类型

数据保留。列名是否跟着 Python 名字走，取决于有没有 `db_column`。

### 设计终态

设计预期，不是运行结果。

- Hit：直接基类是 `Model` 或映射表中的 `NetBoxModel`，恰好一对字段名替换，构造器最后一段相同，新调用没有 `db_column`，且改动与 diff 相交。
- NotFound：同一对名字之外的情况已经读完，新调用含有 `db_column`，或字段名集合没有这种一对一差集。只新增一个可空字段是 NotFound。
- Unanalyzed：直接基类不是 `Model`，也不在映射表里，原因是 `missing_framework_context`。差集大于一对，或构造器最后一段不同：字段名读得到，但没有写明的配对政策，不把它记成 NotFound，以免盖住可能丢列的改动。实现时若必须写入已有原因名，用 `missing_framework_context`，不用 `unsupported_stage04_details`。调用与字段赋值无法配对，或 `keyword_names` 含 `None`，原因是 `unsupported_stage04_details`。路径段含 `migrations` 的 `RemoveField` 不由本规则判终态，仍归破坏性迁移规则。这些都不记 Hit。

`NetBoxModel` 的身份只来自映射表的整段名字，不来自后缀，也没有 ADR。未列入的项目模型基类仍是 Unanalyzed。

### 构造样例

正例：base 为 `class Device(models.Model): asset_tag = models.CharField(max_length=50)`，head 把 `asset_tag` 换成 `tag = models.CharField(max_length=50)`，没有 `db_column`。

反例：head 为 `tag = models.CharField(max_length=50, db_column="asset_tag")`。另一个反例：同一类里同时改掉两个字段名，或 `CharField` 换成 `IntegerField`。`app/migrations/0005_rename.py` 里的 `migrations.RemoveField` 不由本规则触发。

正例补充：`class Device(NetBoxModel)` 上的同样一对改名，且新字段没有 `db_column`，按映射表记设计 Hit。无法分析：字段构造的关键字通过 `**options` 传入，读不到 `db_column` 是否存在。另一个无法分析的例子：`class Device(OrganizationalModel)`，该最后一段不在映射表里。

### 与现有规则的去重

迁移文件里的 `RemoveField` 仍只由 `data.django_destructive_migration` 记录。同一 PR 的另一个文件里若有 `RenameField`，本规则不跨文件把它当成已经配对，也不因此抑制模型侧的设计线索。`null` 收紧仍由非空规则记录。两条 Finding 可以同时存在于设计上，本任务都不生成。

## 5. 理论与项目依据

- [Django 字段 `db_column`](https://docs.djangoproject.com/en/stable/ref/models/fields/#db-column) 写明：这是该字段使用的数据库列名；若不给出，Django 使用字段名。
- 同页对 `ForeignKey` 写明 Django 会在字段名后加上 `_id` 作为列名，也可以用 `db_column` 明确指定。关系字段的改名仍用本卡片的同一闭集，不另判 `_id`。
- [`RenameField`](https://docs.djangoproject.com/en/stable/ref/migration-operations/#django.db.migrations.operations.RenameField) 写明它改变字段名，并且在未设置 `db_column` 时也改变列名。
- [`RemoveField`](https://docs.djangoproject.com/en/stable/ref/migration-operations/#django.db.migrations.operations.RemoveField) 写明数据丢失不可逆。该操作的命中条件仍在破坏性迁移卡片里。
- 这些句子说明列名和删除操作的文档含义。它们不证明某一次字段改名已经被自动检测器写成 `RemoveField` 加 `AddField`，也没有 NetBox 试点结果。

## 6. 限制与反例

- 可能误报：自动检测器会把这一对字段配成 `RenameField`，列上的数据可以保留。模型源文件仍然符合闭集，所以设计上仍是 Hit。复核要看生成的迁移，本规则不打开那个文件。
- 可能漏报：一次改动了两个以上字段；`db_column` 写在父类字段上；列名通过 `SeparateDatabaseAndState` 保留。
- Python 动态特性限制：字段由循环或 `contribute_to_class` 生成。
- 规则不判断：迁移是否已经应用到某个环境、旧列里有没有行、`db_column` 的字符串是否写对。
- 必须人工复核的上下文：生成的操作是 `RenameField` 还是 `RemoveField` 加 `AddField`，以及发布说明里有没有数据拷贝。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `empirical_required` |
| 验证方法 | 将来的构造样例覆盖一对改名、带 `db_column`、多字段、项目基类和迁移文件。不运行 `makemigrations`，不下载真实 PR |
| 数据集 | 未圈定 |
| 判定依据 | 将来的人工标注。官方文档不证明自动检测器在本项目数据上的配对结果 |
| 指标 | 不预填 |
| 验收标准 | 022 以构造样例验收。当前 022 已接入检测器 |
| 未解决问题 | `NetBoxModel` 已写入映射表；022 的检测器经 `resolve_class_bases` 按最后一段整段相等读取这张表。未列入的项目基类仍是 Unanalyzed。不跨文件读取 `RenameField`；022 已接入检测器；没有实证 |
