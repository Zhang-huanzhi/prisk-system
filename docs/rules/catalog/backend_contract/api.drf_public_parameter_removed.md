# 规则说明卡片：`api.drf_public_parameter_removed`

> 本卡片是设计记录。样例都是构造样例，不是某个已合并 PR 的复原。生命周期是 `implemented`（022 接入检测器与构造测试）；默认权重 0，不是 `validated`，也没有真实 PR 实证。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `api.drf_public_parameter_removed` |
| 规则名称 | 公有接口删除既有参数 |
| 版本 | `v1` |
| 规则阵营 | `backend_contract` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

登记册使用同一 ID、同一名称、同一版本和同一生命周期。

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | 同一 Python 文件里的 DRF 序列化器类体，或同一函数上带有 `@api_view` / `@action` 的签名。GraphQL、普通 helper、管理命令不在适用面内 |
| 依赖层级 | `framework`。阵营是后端契约；它依赖的是 DRF 字段和视图装饰器这些框架约定，不是语言级异常形态 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `High` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度是待验证的设计值，不是权重，也不进入当前评分。

## 3. 为什么制定

### 观察到的工程问题

已出现在序列化器类体或已装饰视图签名里的字段、参数，在 head 中消失。旧客户端可能仍按原来的名字提交或读取。

### 为什么值得检测

删除和新增的兼容方向不同。[`api.drf_public_parameter_added`](api.drf_public_parameter_added.md) 只看新增且必填。可选字段被删、只读字段被删，同样会改变已经发布的合同，所以不并入那一条。

### 现有规则为什么不能覆盖

运行时的 `api.signature_changed` 只报告接口路径上的签名结构变化，不区分删除、改名和函数体修改。它也不读取序列化器字段赋值。

### 研究或工程价值

这是 DRF 框架适配。仓库内 [NetBox 调研](../../../versions/v1.0.0/02-PR采样&定风险场景/NetBox调研.md) 把 REST serializer 和 API view 列为纳入场景。调研计数不是本规则的命中率。

## 4. 检测定义

### 适用性

只看同一文件、同一类体或同一函数。不解析其他文件里的 `router.register`、`include()` 或父类类体。同一文件看不到适用表面时，不适用本规则的 Hit 条件。

### 检测边界

- 序列化器：基类最后一段是 `Serializer` 或 `ModelSerializer`，或按 [已知框架基类映射](../../known-framework-bases.md) 视为 `ModelSerializer`（`PrimaryModelSerializer`）时，类体里显式字段赋值可以比较是否消失。纯 `Serializer` 与 `ModelSerializer` 一样只比较写出来的字段。模型上未写进类体的隐式字段不在本规则里。未列入的名字，包括 `RackBaseSerializer`，不是适用表面。
- 视图：函数或方法节点的装饰器文本含有 `@api_view` 或 `@action` 时，该函数签名里的参数属于适用表面。
- 不把“文件名像 `serializers.py`”单独当成公有路由已经证明。

### 检测对象

base 与 head 上、与删除行或新增行相交的类体字段节点，以及函数签名里的参数名。

### 触发条件

适用表面成立，且同一个限定名下的字段名或参数名在 base 有、在 head 没有。一条名字一条设计 Finding。改名会同时表现为删除和新增；新增半边交给 `api.drf_public_parameter_added`，本规则只记录消失的名字。

同一适用类上的嵌套类 `Meta` 也在设计范围内，比较的是列表成员，不是类体字段赋值名：

- base 的 `Meta.fields` 含有字符串字面量 `S`，head 的 `Meta.fields` 仍是可读的列表或元组且不含 `S`：设计 Hit，表示该名字从公开字段名单里去掉。
- base 的 `Meta.exclude` 不含 `S`，head 的 `Meta.exclude` 新增字符串字面量 `S`：设计 Hit，表示该名字被排除。
- `Meta.fields = "__all__"` 与一个具体列表之间的替换读得出两侧形态，但无法列出消失的模型字段名。这不是 Hit，记 `missing_framework_context`。
- 当前 stage04 的类体字段节点保存的是序列化器字段赋值。嵌套类 `Meta` 的列表元素如果不是结构化的字符串名单，就读不出成员变化。此时记 `unsupported_stage04_details`，不把「看不到 Meta」写成 NotFound，也不把字段赋值通道上已经读完的名字补成已通过。
- 类上没有 `Meta` 时，这一通道不存在。字段赋值通道已经读完且没有缺口时，仍可以只按赋值名记 NotFound。

### 触发特征

- `parameter_removed`：`name` 为该字段；`source` 为 base 的类体字段名、签名参数名，或可读的 `Meta.fields` / `Meta.exclude` 字符串成员；head 上该名字按上一节的删除或排除形态消失；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true。
- `same_file_surface`：`source` 为同一类基类文本或同一函数装饰器文本；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true。

两个都要成立。当前 stage04 的函数节点带有完整 `signature.parameters`。类体字段只有赋值行与 diff 相交时才进入节点列表；未改动的兄弟字段不会出现。比较“消失”时，以 base 上与删除行相交的字段节点为准。

### 不触发条件

字段或参数仍在；只改 `help_text`、`label` 或字段内部校验，赋值目标名还在；测试客户端里的调用；没有 `@api_view` / `@action` 的普通函数少了一个参数。

### 输入

同一文件的 base/head AST，以及三点 Diff 的新增行和删除行。不读取其他文件。

### Finding

设计上的复核线索：规则 ID、消失的名字、所在类或函数、`pr_intrinsic_risk`。它不证明已有客户端已经失败。022 生成运行时 Finding；默认权重 0。

### 证据位置

文件路径、类或函数限定名、字段或参数名、相交的删除行，以及 base 侧代码切片。

### 上下文切片

展示 base 中的字段赋值或参数，以及 head 中同一类体或同一签名的对应片段。切片被截断时不能把缺失后半段当成“字段已删”。

### 影响类型

接口合同。`read_only` 字段主要影响响应，可写字段主要影响请求。关键字 `read_only` 是否出现，能从调用的 `keyword_names` 读到；关键字的值当前没有布尔字面量字段。值读不出时，证据里写明 `read_only` 未知，仍可记录名字消失，但不判断它原来只读。

### Unanalyzed

设计预期，不是 009 已经对这条规则产出的运行结果。009 的 Hit / NotFound / Unanalyzed 只覆盖当前 13 条运行时规则。

- 类基类最后一段不在 `Serializer` / `ModelSerializer` 里，也不在映射表里，或装饰器文本读不出：`missing_framework_context`。不记 Hit，也不记 NotFound。`PrimaryModelSerializer` 视为 `ModelSerializer`。
- 字段赋值的源码切片被截断，无法确认目标名：`unsupported_stage04_details`。
- 同一 diff 里类基类文本也变了：字段可能被挪到新的基类。记 `missing_framework_context`，不把本地消失直接当成 Hit。
- 父类文件里的字段本规则看不到。这是漏报边界，不启动跨文件分析来补。

### 构造样例

正例：base 的类体有 `asset_tag = serializers.CharField(required=False)`，head 的同一 `Serializer` 或 `PrimaryModelSerializer` 子类不再有 `asset_tag`。另一个正例：同一类的 `Meta.fields` 从 `("id", "asset_tag")` 变成 `("id",)`，且列表元素可读。

反例：只把 `help_text` 从 `"old"` 改成 `"new"`，字段名仍在。另一个反例：模块级 helper `def export(self, queryset, output="json")` 删掉 `output`，函数上没有 `@api_view` 或 `@action`。

边界：`ModelSerializer` 子类的类体里没有写 `name`，模型字段 `name` 仍由框架生成。本地 AST 看不到这条隐式字段，不能记成删除，也不能记成 NotFound。

## 5. 理论与项目依据

- [DRF Serializer](https://www.django-rest-framework.org/api-guide/serializers/) 说明序列化器如何声明字段。隐式模型字段不写在类体里。
- [字段 `required`](https://www.django-rest-framework.org/api-guide/fields/#required) 与 [`read_only`](https://www.django-rest-framework.org/api-guide/fields/#read_only) 说明必填和只读是字段参数。删除字段不等于“新增必填”。
- [DRF `@api_view`](https://www.django-rest-framework.org/api-guide/views/#api_view) 与 [ViewSet `@action`](https://www.django-rest-framework.org/api-guide/viewsets/#marking-extra-actions-for-routing) 是同一文件里能够看到的视图表面。
- [Routers](https://www.django-rest-framework.org/api-guide/routers/) 会把 ViewSet 登记成 URL。该登记经常在另一个文件。本规则不跟随它。
- NetBox 场景来自仓库内调研，不引用未核对的漏洞编号。

## 6. 限制与反例

- 可能误报：字段被改名，新名字与旧名字没有自动配对；或名字从类体赋值挪进本文件的 `get_fields`。`Meta.fields` 成员变化本身是设计 Hit，不再当成误报理由。
- 可能漏报：父类字段、`extra_kwargs` 里删除的名字、运行时拼接的字段，以及结构对象还读不出的 `Meta` 列表。后者按 Unanalyzed 记录，不算已经检查过。
- Python 动态特性限制：`locals()` 或循环里创建的字段没有稳定的赋值目标名。
- 规则不判断：客户端兼容范围、已发布版本是否承诺该字段、请求是否已经失败。
- 必须人工复核的上下文：发布说明、序列化器继承，以及该字段是请求字段还是响应字段。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `empirical_required` |
| 验证方法 | 先写构造正例、反例和上面的边界；再考虑冻结 PR 的人工标注。本任务不做这两步 |
| 数据集 | 未圈定。不使用、也不下载真实 PR 补丁 |
| 判定依据 | 将来以人工标注对照本卡片。当前卡片还不是检测器的 Ground Truth |
| 指标 | 命中频次、Precision、Recall 都待验证设计确定，不预填 |
| 验收标准 | 022 以构造样例验收。当前 022 已接入检测器 |
| 未解决问题 | 路由图未建。`Meta.fields` / `Meta.exclude` 的设计 Hit 已写明，当前结构对象读不出嵌套列表时必须 Unanalyzed。022 的检测器经 `resolve_class_bases` 按最后一段整段相等读取这张表。022 已接入检测器 |
