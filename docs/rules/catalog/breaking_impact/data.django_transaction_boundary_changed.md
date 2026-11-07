# 事务与并发边界变化

> 本卡片是设计记录。样例都是构造样例，不是某个已合并 PR 的复原。生命周期保持 `draft`。当前局部 Diff/AST 不能建立“哪些语句还在事务里”，因此本任务不把它列为下一步检测器候选。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `data.django_transaction_boundary_changed` |
| 规则名称 | 事务与并发边界变化 |
| 版本 | `v1` |
| 规则阵营 | `breaking_impact` |
| 生命周期 | `draft` |
| 负责人 | `Prisk-System` |

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `external_impact` |
| 适用范围 | 设计上关心同一函数里，语句相对于 `atomic` 块或 `select_for_update` 的位置。当前节点没有这个位置关系 |
| 依赖层级 | `database`。阵营是变更冲击。依赖 Django 事务语义，而不是“文件里出现了 atomic 这几个字母” |
| 分析目标层 | `ast_syntax`，`diff_delta`。若要做成本规则所写的边界，还缺一层语句包含关系；本任务不新增这层 |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `High` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度是待验证的设计值，不是权重。

## 3. 为什么制定

### 观察到的工程问题

保存、更新或加锁的代码，可能从 `transaction.atomic` 块内移到块外，或不再使用 `select_for_update`。默认自动提交下，块外的每一条查询会单独提交。

### 为什么值得检测

事务块决定失败时哪些写入会一起回滚。只报告“某次调用的文本变了”看不到语句是否还在块内。

### 现有规则为什么不能覆盖

`data.transaction_structure_changed` 已经会在模型、迁移或事务相关调用发生变化时给出粗线索。把“出现了 `atomic`”再报一遍，不会比那条运行时规则多说明边界。`data.django_raw_sql_execution` 看的是原生 SQL 形态。

### 研究或工程价值

框架适配。本卡片把缺的证据写清楚，避免以后用全局调用图来补一个本文件就能表达、但当前节点没保存的包含关系。

## 4. 检测定义

### 适用性

设计上的适用对象是同一个函数体内的：

- `@transaction.atomic` 或 `with transaction.atomic()`；
- 查询上的 `select_for_update()`。

[`atomic`](https://docs.djangoproject.com/en/stable/topics/db/transactions/#django.db.transaction.atomic) 可作为装饰器或上下文管理器。文档同时说明 Django 默认自动提交，除非当前已有事务。[`select_for_update`](https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-for-update) 是查询集上的加锁方法。`ATOMIC_REQUESTS` 写在设置里，不在本规则的函数体范围内。

### 检测边界

要称为“边界变化”，至少要能指出同一条语句在 base 与 head 是否位于某个 `atomic` 块内部。当前 stage04 做不到：

- call 的 `match_key` 是函数限定名加调用文本，不记录父语句；
- `with` 会记成控制流节点，但控制流节点不进入粗粒度 `structural_changes`，也没有“这个 call 属于哪个 with”的字段；
- `used_as_with_context` 只标记作为 `with` 上下文表达式的那个调用本身，不标记块里的其他语句；
- 装饰器表达式能看出 `@transaction.atomic` 还在不在，但看不出函数体里哪几行因此进入事务。

因此本任务不把“`atomic` 调用被加上或删掉”定义成 Hit。那会和已有的粗粒度事务规则重叠，而且仍然没有边界。

### 检测对象

若以后增加包含关系，对象应是同一函数内、与 diff 相交的写入或 `select_for_update` 调用，以及包围它的 `atomic`。在该字段不存在时，没有可触发对象。

### 触发条件

本卡片不给出当前可以执行的 Hit 条件。包含关系字段不存在时，不允许用调用名出现与否代替。

### 触发特征

下面是以后才可能使用的特征，现在都缺 `source`：

- `enclosing_atomic`：语句是否位于同一函数的 `atomic` 块内；`value_type` 为 `boolean`；`operator` 为 `changed`；`required` 为 true。当前没有这个字段。
- `select_for_update_present`：同一查询链上是否有 `select_for_update`；`value_type` 为 `boolean`；`operator` 为 `changed`；`required` 为 false。调用文本里出现这个属性名，也还不能说明它锁的是哪一次查询的同一行集合。

### 不触发条件

在包含关系可以被读取之前，本规则不触发。不要把缺少字段解释成“边界没有变化”。

### 输入

现在的输入只有同一文件的 call、decorator 和 control_flow 节点。它们不够。不分析其他文件里的事务包装函数，也不读取 `ATOMIC_REQUESTS`。

### Finding

没有当前 Finding。不设计一条“见到 atomic 就报告”的替代 Finding。

### 证据位置

将来应是语句行号和包围它的 `atomic` 行号。现在这两项不能配对。

### 上下文切片

复核时需要函数里相关语句和包围它的 `with` 或装饰器。只切出 `atomic()` 一行并不能复核边界。

### 影响类型

数据一致性与并发。设计标签是 `external_impact`，不是已测得的竞态。

### Unanalyzed

这条规则在当前局部节点上的设计预期全部是 Unanalyzed，不是 NotFound。

- 语句相对 `atomic` 的移动：`missing_framework_context`。缺的是包含关系，不是项目政策文本。
- 事务包在另一个函数或另一个文件的 helper 里：同样 Unanalyzed。不内联 helper，不做跨文件调用图。
- `@transaction.atomic` 装饰器单独增减：仍 Unanalyzed。装饰器可见，被它覆盖的语句集合不可见。
- `select_for_update` 的调用文本增减：Unanalyzed。锁的行集合和事务边界都没有结构化证据。
- 这些预期不会写入 009 的运行时 `rule_outcomes`。009 只覆盖现有 13 条运行时规则。

### 构造样例

下面说明本规则想区分、但当前不能判定的差异。它们不是检测器正例。

想区分的变化：base 中 `with transaction.atomic():` 包住 `device.save()`，head 把 `device.save()` 移到块外。调用文本仍是 `device.save`，现有 `match_key` 可以对上同一次调用，但没有字段说明它是否还在块内。

不应当成边界已经证明的变化：文件里新增一行 `transaction.atomic` 的导入。导入不是边界。

反例方向：`device.save()` 的参数文本变了，但两边都写在同一个 `atomic` 块里。这不是本规则要的边界变化；当前节点同样不能证明“仍在块内”。

### 014 比较单位

`lifecycle` 仍是 `draft`。包含关系还不是节点字段，没有可执行的 Hit，不写成 `registered`。

比较单位本应是同一条语句是否仍在同一个 `atomic` 块内。现在做不到这一对比较。设计预期全部是 Unanalyzed，不能把「文件里没有 `atomic`」记成 NotFound。上文「009 只覆盖现有 13 条」写于 011。013 起运行时目录是 14 条。本规则仍不在运行时目录里，所以上面的预期仍不是 `rule_outcomes`。

## 5. 理论与项目依据

- [Django 事务](https://docs.djangoproject.com/en/stable/topics/db/transactions/#django.db.transaction.atomic) 说明默认自动提交、`atomic` 装饰器和上下文管理器，以及嵌套块仍可能被外层回滚。
- 同页说明 `ATOMIC_REQUESTS` 包住的是视图函数本身，中间件在事务外。本规则不读设置来推断每个视图都在事务里。
- [`QuerySet.select_for_update`](https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-for-update) 是加锁查询的文档入口。本卡片不从该页摘出尚未在这里逐段引用的数据库差异表。
- 粗粒度运行时规则 `data.transaction_structure_changed` 仍是现有的事务复核线索。本卡片不替换它。

## 6. 限制与反例

- 可能误报：若将来只报告 `atomic` 出现，会把合法的事务拆分和无关导入都算进来。所以当前不报告。
- 可能漏报：helper 函数内部的事务、跨文件混入、数据库触发器。
- Python 动态特性限制：`atomic` 由别名或 `getattr` 调用。即便以后有包含关系，别名仍然要 Unanalyzed。
- 规则不判断：隔离级别、死锁、丢失更新是否已经发生。
- 必须人工复核的上下文：函数全文、外层视图是否启用 `ATOMIC_REQUESTS`、查询是否在事务提交之后才发出。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `empirical_required` |
| 验证方法 | 在包含关系成为显式字段之前，不写检测器测试。构造样例只用于说明为何现在不能判定 |
| 数据集 | 未圈定。不下载真实 PR |
| 判定依据 | 没有可执行定义，就没有 Ground Truth 结果 |
| 指标 | 不预填 |
| 验收标准 | 本任务的验收是把“不能由当前节点判定”写清楚，而不是交付 Hit |
| 未解决问题 | 语句与 `atomic` 的包含关系；helper 不内联；与现有粗粒度规则的分工已说明，但不实现第二条事务规则 |
