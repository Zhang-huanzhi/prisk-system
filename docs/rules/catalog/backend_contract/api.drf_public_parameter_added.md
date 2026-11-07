# 规则说明卡片：`api.drf_public_parameter_added`

> 本卡片同时服务于工程登记和毕业论文写作。没有证据的内容填写“待验证”，不要用推测替代结果。生命周期保持 `draft`：没有检测器，也没有运行终态。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `api.drf_public_parameter_added` |
| 规则名称 | 公有接口新增必填参数 |
| 版本 | `v1` |
| 规则阵营 | `backend_contract` |
| 生命周期 | `draft` |
| 负责人 | `Prisk-System` |

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | 同一 Python 文件里的 DRF 序列化器类体，或带 `@api_view` / `@action` 的函数签名。GraphQL 不在本规则内 |
| 依赖层级 | `framework`。阵营是后端契约；依赖的是 DRF 字段和视图装饰器，不是语言级异常形态 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `High` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度仍是待验证的设计值，不是权重。

## 3. 为什么制定

### 观察到的工程问题

已有序列化器或已装饰视图在 head 上多出一个没有默认值、并且源码写明 `required=True` 的输入。旧客户端在缺少该字段时会失败。

### 为什么值得检测

NetBox 的接口行为主要来自 REST serializer 和 API view，而不是任意 Python 函数多了一个参数。[02 阶段 NetBox 调研](../../../versions/v1.0.0/02-PR采样&定风险场景/NetBox调研.md) 把这些表面列为纳入场景。调研计数不是命中率。

### 现有规则为什么不能覆盖

`api.signature_changed` 只报告接口路径上的签名结构变化，不区分必填新增、可选新增和删除。[`api.drf_public_parameter_removed`](api.drf_public_parameter_removed.md) 方向相反。已有名字上把 `required=False` 改成 `required=True` 不是本规则，目录里也没有第三条规则承担这件事。

### 研究或工程价值

框架适配。身份使用原生最后一段，加上 [已知框架基类映射](../../known-framework-bases.md)。不把跨文件路由登记写成已经证明的前提。

## 4. 检测定义

- **检测对象**：base 与 head 都存在的同一个类限定名上的字段名，或同一个函数限定名上的参数名。
- **触发条件**：该名字在 base 没有、在 head 有；字段调用写出 `required=True` 且没有 `default=`，或者函数装饰器文本含有 `@api_view` 或 `@action` 且新增参数的 `has_default` 为假。变化出现在新增行上。
- **触发特征**：`parameter_added`（`source` 为 base 字段或签名没有该名、head 有；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true）。`required_flag`（`source` 为未截断调用切片里的 `required=True` 且没有 `default=`，或参数 `has_default` 为假；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true）。`same_file_surface`（`source` 为同一文件的基类最后一段或装饰器文本；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true）。
- **不触发条件**：`required=False`；带 `default=`；只改 `help_text`；没有 `@api_view` / `@action` 的普通函数；只在 head 出现的整份类或函数；已有名字只改必填性。
- **输入**：同一文件的 head/base AST 和三点 Diff。不读取其他文件的 router。
- **Finding**：设计线索，规则 ID、参数名、所在类、`pr_intrinsic_risk`、严重度 `High`。不证明线上客户端已经失败。本任务不生成 Finding。
- **证据位置**：文件、限定名、参数名、`required=True` 或 `has_default: false`、相交的新增行、head 侧切片。
- **上下文切片**：该字段赋值或该函数签名。切片截断时不能把缺关键字当成 `required=True`。
- **影响类型**：接口合同。

身份按 [已知框架基类映射](../../known-framework-bases.md) 的最后一段整段相等：

- 最后一段是 `Serializer` 或 `ModelSerializer`，或映射表把该段视为 `ModelSerializer`（`PrimaryModelSerializer`）时，显式 `required=True` 且没有 `default=` 是设计 Hit。017 起，原生 `ModelSerializer` 与映射后的模型序列化器在这条显式语法上使用同一判定。省略 `required` 仍然 Unanalyzed，不按文档默认 `True`，也不按模型字段的 `blank` / `null` 猜测。
- 未列入的名字，包括 `RackBaseSerializer`，记 `missing_framework_context`。子串和后缀不算直接名称。

路由边界：不把已路由写成检测前提。其他文件的 `router.register` 或 `include()` 不是表面证据。看到适用表面也不证明 URL 已经登记。看不到该表面时记 `missing_framework_context`，不记 Hit，也不记 NotFound。

`partial=True`、`extra_kwargs`、父类字段和 `get_fields` 看不见。不为此做跨文件分析。当前 `literal_facts` 不保存布尔值；`required=True` 要从未截断切片确认。切片截断记 `unsupported_stage04_details`。

构造正例：base 与 head 都有 `class DeviceSerializer(serializers.Serializer)` 或 `class DeviceSerializer(PrimaryModelSerializer)`，head 新增 `asset_tag = serializers.CharField(required=True)`。

构造反例：同一类上 `required=False`；或 `def export(self, queryset, output="json")` 没有 `@api_view` / `@action`。

不支持：整类是新建的；基类最后一段是 `RackBaseSerializer`；省略 `required`；调用切片被截断。

适用表面已经逐项分完且没有缺口时，才可以记 NotFound。当前没有运行终态。

## 5. 理论与项目依据

- [DRF Serializer](https://www.django-rest-framework.org/api-guide/serializers/) 和 [字段 `required`](https://www.django-rest-framework.org/api-guide/fields/#required) 说明序列化器字段默认可为必填，更新时 `partial=True` 会改变这个要求。本仓库没有冻结各字段类的默认表，因此省略 `required` 不记 Hit。
- [DRF Viewsets](https://www.django-rest-framework.org/api-guide/viewsets/) 与 [Routers](https://www.django-rest-framework.org/api-guide/routers/) 说明动作要经过路由才成为 HTTP 表面。当前 stage04 没有这条链接。
- NetBox 场景纳入依据是仓库内的 [NetBox 调研](../../../versions/v1.0.0/02-PR采样&定风险场景/NetBox调研.md)。映射表只收录已经点名的基类，不引用未核对的漏洞编号。

## 6. 限制与反例

- 可能误报：内部服务函数若被标成 `@api_view`，新增无默认值参数会命中，即使调用方都在仓库内。
- 可能漏报：`ModelSerializer` 从模型生成、但没写在类体里的隐式字段；`extra_kwargs`；父类字段；`to_internal_value` 动态补齐的字段。
- Python 动态特性限制：运行时拼接的字段不在静态类体中。
- 规则不判断：不发送 HTTP 请求，不判断客户端兼容范围，不证明 URL 已经登记。
- 必须人工复核的上下文：路由登记、序列化器继承链、`partial` 更新路径，以及发布说明是否把该字段标成不兼容变更。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `empirical_required` |
| 验证方法 | 合同按本卡片冻结后，用构造样例检查显式 `required=True`、省略 `required`、映射基类、未列入基类和非公有 helper。再以冻结 NetBox PR 的人工标注看命中是否符合定义 |
| 数据集 | 未圈定。当前没有运行结果 |
| 判定依据 | 将来的人工标注。拟定合同还不是已实现检测器的 Ground Truth |
| 指标 | 命中频次、Precision、Recall 待验证设计确定，不预填 |
| 验收标准 | 待验证设计确定；当前不预填结果 |
| 未解决问题 | 没有检测器，也没有构造测试。省略 `required` 的默认表仍不冻结。`partial=True` 与父类字段仍不可读。跨文件 `router.register` 仍然不是表面证据。映射表不由运行时执行 |
