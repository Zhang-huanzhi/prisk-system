# 规则说明卡片：`data.django_non_null_constraint_tightened`

> 本卡片是设计记录。样例都是构造样例，不是某个已合并 PR 的复原。生命周期是 `implemented`（021 接入检测器与构造测试）；默认权重 0，不是 `validated`，也没有真实 PR 实证。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `data.django_non_null_constraint_tightened` |
| 规则名称 | 非空约束收紧 |
| 版本 | `v1` |
| 规则阵营 | `breaking_impact` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `external_impact` |
| 适用范围 | 同一文件里，模型字段调用或迁移 `AlterField` / `AddField` 上的 `null` 关键字 |
| 依赖层级 | `database`。阵营是变更冲击。`null` 影响数据库存储；`blank` 是另一件事 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `High` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度是待验证的设计值，不是权重。`external_impact` 不是已经测得的迁移失败。

## 3. 为什么制定

### 观察到的工程问题

已有字段从允许 `NULL` 变成不允许，或向已有模型新增一个不可空且没有默认值的字段。已有行可能没有值可填。写明了 `default=` 的新增或收紧不是这个缺口。

### 为什么值得检测

Django 写明 `null` 的默认值是 `False`，并且 `AlterField` 的 `preserve_default` 常用于把可空字段改成不可空时给已有行填值。这和删除整列不是同一条规则。

### 现有规则为什么不能覆盖

`data.django_destructive_migration` 只看 `DeleteModel` 和 `RemoveField`。`data.transaction_structure_changed` 不区分 `null=True` 与 `null=False`。

### 研究或工程价值

框架适配。不查询数据库里是否已有 `NULL`。

## 4. 检测定义

### 适用性

同一文件中的两类调用：

- 模型类体里的字段构造，调用名最后一段以 `Field` 结尾，或就是常见的关系字段调用；
- 迁移文件里属性名最后一段为 `AlterField` 或 `AddField` 的调用。

不跟随其他文件的抽象基类。

### 检测边界

[字段 `null`](https://docs.djangoproject.com/en/stable/ref/models/fields/#null)：`True` 时把空值存成 `NULL`，默认是 `False`。`blank` 只管表单校验，不并入本规则。

[`AlterField`](https://docs.djangoproject.com/en/stable/ref/migration-operations/#django.db.migrations.operations.AlterField) 会修改字段的 `null`。同页的 `AddField` 说明：向表添加不可空字段时，常用一次临时默认值填充已有行。设计 Hit 只描述「已有模型上非空，并且没有可见的默认值」：

- base 的同一字段调用含可读的 `null=True`，head 不再有 `null=True` 或写成 `null=False`，并且 head 的未截断切片里没有 `default=` 关键字；
- 迁移 `AlterField` 的字段表达式出现同样的 `null` 收紧，并且字段表达式没有 `default=`；
- 对已有模型的 `AddField`，字段表达式不是 `null=True`，并且没有 `default=`。不能只因为省略了 `null=True` 就 Hit。

看见 `default=` 时记 NotFound。Django 会用这个默认值填充已有行；`preserve_default=False` 只表示默认值不留在迁移后的字段状态里，执行迁移时仍用它填充已有行，所以仍然不是 Hit。

`null=True` 保持或被加上、只改 `blank`、`CreateModel` 或新建模型类体里的默认不可空字段、`RemoveField`，都是 NotFound，不是 Hit。

### 检测对象

上述调用里的 `null` 关键字，以及 `AddField` 的字段表达式。

### 触发条件

适用调用与新增行或删除行相交，且上一节的「非空且没有 `default=`」成立。`null=` 与 `default=` 都必须能从该调用的未截断源码读出有或没有。只知道 `keyword_names` 里有 `null` 还不够，因为当前节点不保存布尔值。读不出有没有 `default=` 时记 Unanalyzed，不记 Hit。

### 触发特征

- `null_keyword`：`source` 为调用源码中的 `null=` 右侧；`value_type` 为 `enum`；`operator` 为 `contains`；`threshold` 为 `true`、`false`、`absent`；`required` 为 true。
- `tightened`：`source` 为 base 与 head 的 `null_keyword` 比较，或已有模型上的 `AddField` 且 head 不是 `null=True`，并且同一未截断切片的关键字里没有 `default`；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true。
- `call_changed`：`source` 为调用与 diff 行的交集；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true。

这是有界输入：关键字布尔值的源码文本。它不是跨文件符号表。在检测器读到这个文本之前，不能把“出现了 `null` 这个关键字名”记成 Hit。

### 不触发条件

`null=True` 保持或被加上；同一收紧或 `AddField` 上能看见 `default=`；只改 `blank`、`help_text` 或 `verbose_name`；`CreateModel` 或新模型类体里的默认 `CharField()`；`RemoveField`。

### 输入

同一文件 base/head AST、未截断调用切片和三点 Diff。不连接数据库。

### Finding

设计线索：规则 ID、字段名、`null` 的前后值、`external_impact`。不证明迁移已经失败。021 生成运行时 Finding；默认权重 0。

### 证据位置

文件、模型或操作名、字段名、`null` 文本、行号。

### 上下文切片

该字段调用或该迁移操作。不展开历史迁移。

### 影响类型

数据约束。

### Unanalyzed

设计预期，不是运行结果。

- `null=` 的右侧不是常量 `True` 或 `False`，切片被截断，或 `default` / `null` 经 `**kwargs` 传入因而不能确认缺失：`unsupported_stage04_details`。不能把这种缺口记成 Hit。
- 字段定义在其他文件的抽象父类上，子类没有重写：`missing_framework_context`。
- 数据库里是否已有 `NULL`、所用后端是否把空字符串存成 `NULL`：未知。Oracle 的文档说明与此有关，本规则不查后端，也不因此记 Hit 或 NotFound。
- `RunSQL` 里的 `SET NOT NULL`：不解析 SQL，记 `missing_framework_context`。

### 构造样例

正例：base 为 `asset_tag = models.CharField(max_length=50, null=True)`，head 去掉 `null=True` 或写成 `null=False`，并且没有 `default=`。另一个正例：已有模型的迁移 `AddField` 使用 `models.CharField(max_length=50)`，既没有 `null=True` 也没有 `default=`。

反例：同一 `AddField` 写成 `models.CharField(max_length=50, default="")`，即使省略了 `null=True`，也是 NotFound。`null=True` 未改、只把 `blank=True` 改成 `blank=False`，是 NotFound。新建模型类里写 `name = models.CharField(max_length=50)`，是 NotFound。

边界：`AlterField` 的 `field=` 参数里字段构造跨了超过源码切片上限的行。截断后读不全 `null=`，记 Unanalyzed。

## 5. 理论与项目依据

- [Django 字段 `null`](https://docs.djangoproject.com/en/stable/ref/models/fields/#null) 说明默认 `False`，并区分数据库存储和表单。同页 [`blank`](https://docs.djangoproject.com/en/stable/ref/models/fields/#blank) 说明它只影响校验。
- [`AlterField`](https://docs.djangoproject.com/en/stable/ref/migration-operations/#django.db.migrations.operations.AlterField) 与同页 `AddField` 说明 `null` 变化和不可空新列对已有行的含义。
- 非空规则不引用 `data.django_destructive_migration` 的删除操作作为自己的正例。

## 6. 限制与反例

- 可能误报：字段尚未有数据，但源码上已经是非空且没有 `default=`。看见 `default=` 的填充不再记 Hit；默认值是否覆盖全部已有行，本规则不判断。
- 可能漏报：约束写在 `CheckConstraint` 或数据库触发器里。
- Python 动态特性限制：字段由循环和 `contribute_to_class` 生成。
- 规则不判断：迁移会不会在某个数据库失败、已有空字符串是否违反业务上的“非空”。
- 必须人工复核的上下文：`default=` 的值是否真能填充已有行、`preserve_default` 和后端差异。有 `default=` 时本规则已经是 NotFound，复核不再靠一条 High Hit。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `empirical_required` |
| 验证方法 | 构造样例覆盖 `null` 收紧、只改 `blank`、新模型和截断切片。不连接数据库 |
| 数据集 | 未圈定 |
| 判定依据 | 将来的人工标注 |
| 指标 | 不预填 |
| 验收标准 | 布尔关键字文本进入检测器之前不能当作已实现 |
| 未解决问题 | 当前 `literal_facts` 不保存布尔值，也021 已接入检测器。`default=` 必须从切片确认；确认不了则 Unanalyzed。父类字段不跨文件 |
