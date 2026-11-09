# 规则说明卡片：`auth.drf_queryset_scope_tighten_bypassed`

> 本卡片是设计记录。样例都是构造样例，不是某个已合并 PR 的复原。生命周期是 `implemented`（022 接入检测器与构造测试）；默认权重 0，不是 `validated`，也没有真实 PR 实证。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `auth.drf_queryset_scope_tighten_bypassed` |
| 规则名称 | DRF 查询集收紧被绕过 |
| 版本 | `v1` |
| 规则阵营 | `backend_contract` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `external_impact` |
| 适用范围 | 同一文件中，直接基类属于闭集的 DRF ViewSet 上的 `get_queryset` |
| 依赖层级 | `framework`。阵营是后端契约。`external_impact` 表示设计上关心调用方是否还能只看到原先收紧的行，不是已经测得的数据暴露 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `High` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度 `High` 是临时判断，不是权重，也不是一票抬升。后续算法阶段可以修订。

## 3. 为什么制定

### 观察到的工程问题

ViewSet 的 `get_queryset` 被改成返回 `Model.objects.all()`，或不再调用原来的 `super().get_queryset()` / 项目里的收紧函数。

### 为什么值得检测

DRF 写明 `get_queryset` 同时供给列表和详情查找。返回值若变成未过滤的 `objects.all()`，列表和单对象查找都会用这份查询集。审查者需要看到这个返回表达式，而不是只看到方法还在。

### 现有规则为什么不能覆盖

[`auth.drf_permission_policy_downgrade`](auth.drf_permission_policy_downgrade.md) 只看 `permission_classes`。它写明对象级 `has_object_permission` 与 `get_queryset` 过滤不属于那条规则。[`api.drf_viewset_action_changed`](api.drf_viewset_action_changed.md) 的动作闭集是 `list`、`create`、`retrieve`、`update`、`partial_update`、`destroy` 和 `@action`，不含 `get_queryset`。登记册里的 `auth.drf_object_permission_bypass` 仍是 011 的排除项，没有卡片。本规则不实现那条排除项，也不改它的生命周期。

### 研究或工程价值

框架适配。直接基类闭集与动作卡片相同。项目基类和 `restrict_queryset` 这类名字不在本卡片的 Hit 闭集里。要放进去，需要单独写明的继承或辅助函数名单。当前 [ADR 索引](../../../adr/README.md) 没有已发布条目。本任务不建这份名单，也不建 ADR。

## 4. 检测定义

### 比较单位

两侧或仅 head 存在的同一个类上的方法，方法名必须是 `get_queryset`。比较的是该方法的返回表达式，以及 base 里有没有 `super` 接收者上的 `get_queryset` 调用。类属性 `queryset = ...` 不是这个比较单位。

### 适用性

类语句的直接基类文本里，最后一段标识符属于 `ViewSet`、`GenericViewSet`、`ModelViewSet`、`ReadOnlyModelViewSet` 之一，或按 [已知框架基类映射](../../known-framework-bases.md) 视为 `ModelViewSet`（`NetBoxModelViewSet`）。按最后一段相等，不按子串。未列入的名字仍不适用。不沿继承链读其他文件。

当前函数节点没有「返回表达式」字段，控制流节点也没有「语句属于哪个 return」。`.objects.all` 的调用节点有 `callee`。返回值是不是这个调用，要从该方法未截断切片判断。切片截断时不能匹配。

### 闭集

设计 Hit 只接受一种 head 返回形态，称为未过滤的 `objects.all`：

- 返回表达式的调用链以属性 `all` 结束前的接收者属性恰好是 `objects`。`Device.objects.all()` 符合。`user.accounts.all()` 的接收者是 `accounts`，不符合。
- 调用链上若还有后续方法，只允许 `select_related`、`prefetch_related`、`order_by`、`distinct`、`using`、`only`、`defer`。
- `filter`、`exclude`、`none` 不算未过滤形态。

`super().get_queryset` 与 `super(Cls, self).get_queryset` 是证据形态：接收者文本以 `super` 开头，调用的最后一段是 `get_queryset`。它单独出现不是 Hit。

不在闭集、因此不能凭名字记 Hit 的例子：`restrict_queryset`、`restrict`。它们是方法名，不是基类。未写入映射表的项目基类同样不能凭名字记 Hit。

### 触发条件

类基类属于上面四个直接名称，head 的 `get_queryset` 返回未过滤的 `objects.all`，该返回与新增行相交，并且 base 的同一方法要么不存在，要么返回表达式不是这一种形态。base 方法不在本文件时，证据写 `base_method: absent`。这不证明父类原来更严。

若 base 有 `super().get_queryset` 而 head 没有，并且 head 同时满足上一句，证据里记 `super_removed`。这是同一条设计 Finding 上的标记，不是第二条规则。

仅去掉 `super().get_queryset()` 或 `restrict_queryset(...)`，但 head 的返回不是未过滤的 `objects.all`，不记 Hit。

### 触发特征

- `viewset_base`：`source` 为类节点 `details.bases` 的最后一段；`value_type` 为 `string`；`operator` 为 `contains`；`threshold` 为四个直接名称，或映射表中的 `NetBoxModelViewSet`；`required` 为 true。
- `method_name`：`source` 为函数名；`value_type` 为 `string`；`operator` 为 `eq`；`threshold` 为 `get_queryset`；`required` 为 true。
- `return_form`：`source` 为 head 返回表达式的调用链；`value_type` 为 `enum`；`operator` 为 `eq`；`threshold` 为 `objects_all`；`required` 为 true。
- `return_changed`：`source` 为该返回表达式与新增行的交集；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true。
- `super_call`：`source` 为同一方法 base/head 是否含有 `super` 接收者上的 `get_queryset`；`value_type` 为 `enum`；`operator` 为 `changed`；`threshold` 为 `removed`、`absent`、`kept`；`required` 为 false。

`return_form` 读不到时，不能用「方法里出现过 `.objects.all`」代替。调用可以是 `all().filter(...)` 的内部节点。

### 不触发条件

返回 `user.accounts.all()`；返回 `Model.objects.all().filter(...)` 或 `.exclude(...)` 或 `.none()`；只改类属性 `queryset = Model.objects.all()` 而没有改 `get_queryset`；方法名是 `list` 或 `retrieve`；最后一段不在四个直接名称里，也不在映射表里的类。

### 输入

同一文件的 base/head AST 和三点 Diff。不调用 `get_queryset()`，不读父类文件，不连接数据库。

### Finding

设计线索：规则 ID、类限定名、`return_form`、`base_method` 是表达式摘要或 `absent`、可选的 `super_removed`、设计标签 `external_impact`。不证明行已经对外可见。022 生成运行时 Finding；默认权重 0。

### 证据位置

文件、类限定名、方法切片中的返回表达式、行号、基类最后一段。

### 上下文切片

`get_queryset` 方法。切片必须能覆盖返回表达式；覆盖不了就进入 Unanalyzed，不截一半仍当 Hit。

### 影响类型

查询范围声明。

### 设计终态

设计预期，不是运行结果。

- Hit：直接基类在四个原生名字里，或是映射表中的 `NetBoxModelViewSet`，head 返回未过滤的 `objects.all`，且这个形态相对 base 是新的，返回与新增行相交。
- NotFound：直接基类在闭集里，方法切片已读完，head 返回不是该形态，并且不存在「去掉了 `super().get_queryset` 或项目收紧调用、但返回形态对不上」的情况。类属性 `queryset = Model.objects.all()` 对这条规则是 NotFound。
- Unanalyzed：直接基类不在四个原生名字里，也不在映射表里，即使方法里写了 `Model.objects.all()`。原因是 `missing_framework_context`。返回切片截断，原因是 `unsupported_stage04_details`。调用链上有闭集之外的方法名，原因是 `missing_framework_context`。去掉 `super().get_queryset()` 或 `restrict_queryset` 之后返回的是 `filter`、名字或其他表达式，原因是 `missing_framework_context`。这些都不记 Hit，也不记 NotFound。

单独去掉 `restrict_queryset` 仍然不是 Hit。映射表只解决 `NetBoxModelViewSet` 的基类身份，不把 `restrict_queryset` 收进返回形态闭集。未列入的项目基类仍是 `missing_framework_context`。当前没有 ADR。

### 构造样例

正例：`class DeviceViewSet(viewsets.ModelViewSet)` 的 head 新增 `def get_queryset(self): return Device.objects.all()`。base 的同一方法是 `return super().get_queryset()`。证据含 `super_removed`。

反例：同一基类上 `return request.user.accounts.all()`。另一个反例：`queryset = Device.objects.all()` 写在类体里，`get_queryset` 没有改。`return Device.objects.filter(status="active")` 也不是未过滤形态。

正例补充：`class DeviceViewSet(NetBoxModelViewSet)` 里，base 为 `return super().get_queryset()`，head 为 `return Device.objects.all()`。这按映射表记设计 Hit。无法分析：base 为 `return self.restrict_queryset(super().get_queryset())`，head 为 `return Device.objects.filter(status="active")`。另一个无法分析的例子：`class DeviceViewSet(ProjectViewSet)`，`ProjectViewSet` 不在映射表里。

### 与现有规则的去重

权限策略、动作集合和对象级权限排除项都不改写。本规则的 Hit 不抑制 `auth.permission_structure_changed`。`filter_queryset` 与 `get_object` 不是 `get_queryset`，不在本规则触发。

## 5. 理论与项目依据

- [DRF `get_queryset`](https://www.django-rest-framework.org/api-guide/generic-views/#get_querysetself) 写明它返回列表使用的查询集，并作为详情查找的基础，默认返回 `queryset` 属性。同页的例子是 `return user.accounts.all()`，接收者不是 `objects`。
- 同页没有写「必须调用 `super().get_queryset()`」，也没有定义 `restrict_queryset`。本卡片因此不把单独缺少 `super()` 记成 Hit。
- 四个 ViewSet 名字与 [`api.drf_viewset_action_changed`](api.drf_viewset_action_changed.md) 的直接名称相同。`NetBoxModelViewSet` 只通过 [已知框架基类映射](../../known-framework-bases.md) 视为 `ModelViewSet`，不按后缀并入。没有 ADR。
- 这些句子不是 NetBox 试点，也不是数据暴露已经发生的证据。

## 6. 限制与反例

- 可能误报：父类的 `get_queryset` 本来就返回 `objects.all()`，子类只是把同一表达式写进本文件。证据里的 `base_method: absent` 留给复核看这一点。
- 可能漏报：收紧放在 `filter_queryset`、`get_object` 或另一个文件的混入类里。
- Python 动态特性限制：返回值由辅助函数构造，方法由元类生成。
- 规则不判断：哪一个模型算敏感、过滤器谁更严、对象级权限是否仍会拒绝实例。
- 必须人工复核的上下文：父类实现、`permission_classes`，以及这个 ViewSet 是否挂在路由上。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `empirical_required` |
| 验证方法 | 将来的构造样例覆盖未过滤 `objects.all`、`accounts.all`、`filter`、项目基类和截断方法。不下载真实 PR |
| 数据集 | 未圈定 |
| 判定依据 | 将来的人工标注。DRF 文档不提供项目辅助函数的强弱顺序 |
| 指标 | 不预填 |
| 验收标准 | 022 以构造样例验收。当前 022 已接入检测器 |
| 未解决问题 | `NetBoxModelViewSet` 已写入映射表，检测器还不读这张表。`restrict_queryset` 仍不是 Hit。返回表达式还不是结构化字段；022 已接入检测器；没有实证 |
