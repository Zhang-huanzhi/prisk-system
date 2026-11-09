# 规则说明卡片：`data.django_signal_receiver_leak`

> 本卡片是设计记录。样例都是构造样例，不是某个已合并 PR 的复原。生命周期是 `implemented`（022 接入检测器与构造测试）；默认权重 0，不是 `validated`，也没有真实 PR 实证。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `data.django_signal_receiver_leak` |
| 规则名称 | Django 信号接收器缺少 dispatch_uid |
| 版本 | `v1` |
| 规则阵营 | `backend_contract` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

阵营放在 `backend_contract`，是因为判定的是 `connect` 上有没有框架关键字。ID 的 `data` 前缀表示关注数据副作用，不把阵营改成 `breaking_impact`。这是临时归类，后续可以改阵营，不改规则 ID。

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | 同一 Python 文件中，闭集信号上新增的 `connect` 或 `@receiver`，且调用处没有 `dispatch_uid` |
| 依赖层级 | `framework`。阵营是后端契约。依赖的是 Django `Signal.connect` 的参数，不是数据库行数 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `Medium` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度 `Medium` 是临时判断。当前文档写明：没有 `dispatch_uid` 时，模块级函数按对象身份只登记一次。命中不是重复执行已经发生。后续算法阶段可以修订，也可以把严重度留在 `Medium`。

## 3. 为什么制定

### 观察到的工程问题

`post_save.connect(...)` 或同类信号的 `connect` / `@receiver` 在新增代码里没有带上 `dispatch_uid`。

### 为什么值得检测

Django 把 `dispatch_uid` 定义为接收器的唯一标识，用来避免重复登记。绑定方法的身份跟实例走，新实例会再登记一次。`AppConfig.ready()` 在测试里也可能执行多次。审查者需要看到这次新增的连接没有这个关键字。

### 现有规则为什么不能覆盖

`data.django_raw_sql_execution` 的闭集是 `execute`、`executemany`、`raw` 和 `RawSQL`，不看 `connect`。`data.django_transaction_boundary_changed` 看的是 `atomic` 的包含关系，而且 011 把它列为延后。没有别的规则读 `dispatch_uid`。

### 研究或工程价值

框架适配。信号名是下面的闭集，不是任意 `.connect`。

## 4. 检测定义

### 比较单位

一次 `connect` 调用，或一次 `@receiver(...)` 调用。比较的是信号名的最后一段，以及关键字里有没有 `dispatch_uid`。

### 适用性

调用节点保存 `callee`、`args_count` 和 `keyword_names`。`post_save.connect` 的信号名在 `callee` 文本里。`@receiver(post_save)` 的信号名是位置参数，当前调用节点不保存位置参数文本，要从该调用的未截断切片读取。装饰器节点另有表达式文本，但不能代替关键字数组。

### 闭集

信号名的最后一段属于 `django.db.models.signals` 文档中的这些名字：

`pre_init`、`post_init`、`pre_save`、`post_save`、`pre_delete`、`post_delete`、`m2m_changed`、`class_prepared`、`pre_migrate`、`post_migrate`。

`request_started`、`request_finished`、`got_request_exception`、`setting_changed`、`connection_created` 以及任务信号不在闭集里。自定义 `Signal()` 也不在闭集里。

连接形态只有两种：`callee` 的最后一段是 `connect`，且其接收者最后一段属于闭集；或者 `callee` 的最后一段是 `receiver`，且位置参数里的信号最后一段属于闭集。`@receiver([post_save, post_delete])` 在列表元素都能读到、且至少一个元素属于闭集时，按这一次调用记录。

### 触发条件

连接形态属于闭集，调用与新增行相交，并且同时满足：

- `keyword_names` 不含 `dispatch_uid`；
- 不存在名为 `None` 的关键字，也就是没有 `**kwargs` 把关键字收进字典；
- `connect` 的 `args_count` 小于 4。`connect(receiver, sender, weak, dispatch_uid)` 的第四个位置参数可能就是 `dispatch_uid`，当前节点不保存位置参数的值。

`receiver` 的 `dispatch_uid` 只出现在关键字里。位置参数是信号本身。

### 触发特征

- `signal_name`：`source` 为 `callee` 接收者的最后一段，或 `receiver` 位置参数的最后一段；`value_type` 为 `string`；`operator` 为 `contains`；`threshold` 为上面十个名字；`required` 为 true。
- `connect_form`：`source` 为 `callee` 的最后一段；`value_type` 为 `enum`；`operator` 为 `contains`；`threshold` 为 `connect`、`receiver`；`required` 为 true。
- `dispatch_uid`：`source` 为 `keyword_names`；`value_type` 为 `boolean`；`operator` 为 `missing`；`threshold` 为 `dispatch_uid`；`required` 为 true。
- `call_changed`：`source` 为调用与新增行的交集；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true。

### 不触发条件

关键字里已有 `dispatch_uid`；`disconnect`；闭集之外的信号名；调用没有与新增行相交；`Signal.send` 与 `send_robust`。

### 输入

同一文件的 head AST 和三点 Diff。不导入应用，不调用 `ready()`，不统计接收器列表。

### Finding

设计线索：规则 ID、信号名、`connect` 或 `receiver`、文件和行、设计标签 `pr_intrinsic_risk`。不证明接收器已经执行了两次。022 生成运行时 Finding；默认权重 0。

### 证据位置

文件、`callee`、信号名、`keyword_names`、`args_count`、新增行号。

### 上下文切片

该调用或该装饰器。若接收器是属性访问，切片要带上这个参数；读不到则进入 Unanalyzed，不猜测它是不是绑定方法。

### 影响类型

数据相关的回调登记。

### 设计终态

设计预期，不是运行结果。

- Hit：闭集信号的 `connect` 或 `receiver` 与新增行相交，且按上一节确认没有 `dispatch_uid`。
- NotFound：调用已经读完，`dispatch_uid` 出现在关键字里，或闭集信号的连接都没有与新增行相交。
- Unanalyzed：信号名不在闭集，包括 `request_finished` 和自定义信号，原因是 `missing_framework_context`。`callee` 或 `receiver` 的位置参数切片被截断、`keyword_names` 含 `None`，或 `connect` 的 `args_count` 大于等于 4，原因是 `unsupported_stage04_details`。这些都不记 Hit，也不记 NotFound。

### 构造样例

正例：新增行含有 `post_save.connect(on_save, sender=Device)`，没有 `dispatch_uid`。另一个正例：`@receiver(post_save, sender=Device)`。

反例：`post_save.connect(on_save, sender=Device, dispatch_uid="device-save")`。另一个反例：`request_finished.connect(on_done)` 不在闭集，记 Unanalyzed，不记 Hit。

无法分析：`post_save.connect(handler, sender, True, "device-save")`。第四个位置参数可能是 `dispatch_uid`，当前节点没有这个值，记 Unanalyzed。

### 与现有规则的去重

原生 SQL、事务边界和迁移操作都不读 `dispatch_uid`。本规则不因为接收器函数体里有 `save()` 或 `execute()` 而合并到那些规则。

## 5. 理论与项目依据

- [Django 信号](https://docs.djangoproject.com/en/stable/topics/signals/) 的 `Signal.connect` 把 `dispatch_uid` 说明为可能重复发送时的唯一标识，并指向防止重复信号一节。
- 同页「防止重复信号」写明：未提供 `dispatch_uid` 时，Django 用 Python 对象身份识别接收器，同一接收器只登记一次。模块级函数、静态方法和类方法的身份稳定，重复 `connect` 没有效果。绑定方法的身份跟实例走，对新实例再次 `connect` 会多登记一个接收器。同页建议此时提供 `dispatch_uid`。
- 同页还写明 `ready()` 在测试期间可能执行多次，接收器若是会重建实例上的绑定方法，需要防止重复。
- [模型信号](https://docs.djangoproject.com/en/stable/ref/signals/#module-django.db.models.signals) 列出本卡片闭集里的模型信号和管理信号。`class_prepared` 在该页写明 Django 内部使用，第三方一般不用。它仍留在闭集里，因为连接形态相同；这不表示第三方代码里常见。
- 这些句子说明关键字的用途。它们不证明缺少关键字就一定重复执行，也没有 NetBox 试点结果。

## 6. 限制与反例

- 可能误报：模块级函数按文档不会因为再 `connect` 一次而多登记。命中仍只要求复核接收器是不是绑定方法，以及 `ready()` 会不会重复执行。
- 可能漏报：闭集之外的自定义信号；`dispatch_uid` 通过 `**kwargs` 传入。
- Python 动态特性限制：信号对象放在变量里，`callee` 只剩 `connect`，接收者最后一段读不出来。
- 规则不判断：接收器是否绑定方法、`ready()` 的实际次数、回调是否写了两次数据库。
- 必须人工复核的上下文：接收器是函数还是实例方法，连接代码放在 `ready()` 还是模块顶层。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `empirical_required` |
| 验证方法 | 将来的构造样例覆盖 `post_save.connect`、`@receiver`、带 `dispatch_uid`、闭集外信号和第四个位置参数。不导入 Django 应用，不下载真实 PR |
| 数据集 | 未圈定 |
| 判定依据 | 将来的人工标注。官方文档说明的是身份去重，不是本项目的误报率 |
| 指标 | 不预填 |
| 验收标准 | 022 以构造样例验收。当前 022 已接入检测器 |
| 未解决问题 | 是否把 Hit 收窄到接收器表达式为属性访问；位置参数还不是结构化字段；没有实证 |
