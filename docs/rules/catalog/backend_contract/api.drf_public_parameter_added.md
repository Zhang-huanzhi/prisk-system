# 公有接口新增必填参数

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `api.drf_public_parameter_added` |
| 版本 / 阵营 / 生命周期 | `v1` / `backend_contract` / `draft` |
| 负责人 | `Prisk-System` |
| 风险性质 / 依赖层级 | `pr_intrinsic` / `framework` |
| 适用范围 | 使用 Django REST framework 的 Python API 表面；NetBox 的 REST serializer 与 API view 是首要语境，GraphQL 不在本规则内 |
| 分析目标层 / 证据形态 | `ast_syntax`, `diff_delta` / `code_slice`, `symbol_pair` |
| 严重度 / 一票抬升 | `High` / `false`，条件 `null`；严重度仍是待验证的设计值 |

## 制定理由

已发布的 HTTP 动作或序列化器如果新增没有默认值的输入，旧客户端会在缺少该字段时失败。NetBox 的可分析样本里，接口行为主要来自 REST，而不是任意 Python 函数多了一个参数。[02 阶段 NetBox 调研](../../../versions/v1.0.0/02-PR采样&定风险场景/NetBox调研.md) 把 REST API、serializer 和 API view 列为纳入场景。

`api.signature_changed` 只报告接口路径上的签名结构变化，不区分必填新增、可选新增和删除。`api.drf_public_parameter_removed` 是另一条草稿，方向相反。本规则只讨论“新增且必填”。

## 检测定义

下面是 005 的拟定合同，还不能实现。生命周期保持 `draft`。与后面的「011 补强」冲突时，以 011 补强为准：同一文件之外的路由不作为隐藏前提，省略 `required` 也不再按默认必填处理。

- 拟定对象：DRF `Serializer` / `ModelSerializer` 类体里新增的字段赋值，以及已经能对应到路由的 `APIView` 方法或 ViewSet 动作上新增的、没有默认值的参数。GraphQL 字段、普通 helper 和管理命令不在拟定范围内。
- 拟定触发：base 中不存在该字段或参数，head 中存在；序列化器字段没有 `required=False`，并且不是只在 `partial=True` 的更新里才必填的情形；函数参数没有默认值。变化出现在新增行上。
- 拟定不触发：带默认值的参数；`required=False`；只改字段标签或 `help_text`；测试客户端里的调用；无法把类或函数连到 URL router 时不猜测它是公有接口。
- 拟定特征：`parameter_added`（base 签名或字段集合里没有、head 里有，布尔值，`eq true`）；`required_flag`（静态可见的必填状态，布尔值，`eq true`）；`same_file_surface`（同一类或同一函数上能看到下面「011 补强」写明的表面，布尔值，`eq true`）。三条都要成立。任一输入缺失时记 Unanalyzed，而不是通过，也不是 NotFound。
- 输入与证据：同一文件的 head/base AST 和三点 Diff。不读取其他文件的 router。Finding 设计为复核线索，影响类型 `pr_intrinsic_risk`，并指出参数名和所在类。它不证明线上客户端已经失败。

构造样例。下面这个才符合 011 补强后的设计触发：同一文件的 `Serializer` 子类，新增字段写明 `required=True`。

```python
class DeviceSerializer(serializers.Serializer):
    asset_tag = serializers.CharField(required=True)
```

不作为本规则触发的例子：

```python
asset_tag = serializers.CharField(required=False)
def export(self, queryset, output="json"):
    ...
```

`ModelSerializer` 上省略 `required` 的新增字段不是上例的同类。011 补强把它记为 Unanalyzed，不按默认必填处理。

## 011 补强

本节收紧 005 留下的合同，供以后的实现评审阅读。生命周期仍是 `draft`。没有检测器。样例都是构造样例。009 的 Hit / NotFound / Unanalyzed 只覆盖当前 13 条运行时规则；下面的 Unanalyzed 是设计预期，不是一次分析输出。

适用表面只在同一文件内：

- 类语句的基类文本含有直接名称 `Serializer`，且不含 `ModelSerializer`。类体里新增的字段赋值才讨论必填。
- 或者函数节点的装饰器文本含有 `@api_view` 或 `@action`，签名里新增了 `has_default` 为假的参数。函数签名已经在 stage04 的函数节点上。

不把文件名、也不把其他文件里的 `router.register` 或 `include()` 当成表面已经证明。那些链接不存在时记 Unanalyzed，原因是 `missing_framework_context`，不记 Hit，也不记 NotFound。

必填只在源码自己写明时成立：

- 字段调用的关键字含有 `required=True`，并且没有 `default=`；或视图参数没有默认值。
- 省略 `required` 时，[字段文档](https://www.django-rest-framework.org/api-guide/fields/#required) 写的默认是 `True`，但 `ModelSerializer` 会随模型字段的 `blank` / `null` 改变默认。模型字段通常不在这个类体里。因此省略 `required` 的字段，包括 `ModelSerializer` 子类上的显式字段，记 Unanalyzed，不按默认 `True` 记 Hit。
- 当前 `literal_facts` 不保存布尔值。`required=False` 只能从调用的 `keyword_names` 和未截断切片确认。切片截断时记 `unsupported_stage04_details`。
- `partial=True` 写在别的方法或别的文件时看不见。同一文件看不到更新路径时，不把字段判成“只在部分更新里必填”，记 Unanalyzed。

构造边界：`class DeviceSerializer(serializers.ModelSerializer)` 新增 `asset_tag = serializers.CharField()`。这不是 Hit。`class DeviceSerializer(serializers.Serializer)` 新增 `asset_tag = serializers.CharField(required=True)` 才符合本节的设计触发。普通函数新增无默认值参数、但没有 `@api_view` 或 `@action`，不是 Hit。

`extra_kwargs`、父类字段和运行时 `get_fields` 仍然看不到。不为此做跨文件分析。

## 依据

- [DRF Serializer](https://www.django-rest-framework.org/api-guide/serializers/) 和 [字段 `required`](https://www.django-rest-framework.org/api-guide/fields/#required) 说明序列化器字段默认可为必填，更新时 `partial=True` 会改变这个要求。不同字段类的默认值要以所使用的 DRF 版本文档为准，本仓库没有冻结那张表。
- [DRF Viewsets](https://www.django-rest-framework.org/api-guide/viewsets/) 与 [Routers](https://www.django-rest-framework.org/api-guide/routers/) 说明动作要经过路由才成为 HTTP 表面。当前 stage04 没有这条链接。
- NetBox 场景纳入依据是仓库内的 [NetBox 调研](../../../versions/v1.0.0/02-PR采样&定风险场景/NetBox调研.md)。这里不引用未核对的漏洞编号。

## 限制与反例

即便将来实现，内部服务函数新增参数、只被测试调用的 serializer、以及由 `to_internal_value` 动态补齐的字段都会偏离静态必填判断。`ModelSerializer` 从模型生成的隐式字段如果没写在类体里，AST 看不到。规则不发送 HTTP 请求，不判断客户端兼容范围。

人工复核需要路由登记、序列化器继承链、`partial` 更新路径，以及发布说明是否把该字段标成不兼容变更。

## 未冻结、因此保持 draft 的部分

- 011 不再把“先有一张跨文件路由表”写成实现前提。同一文件没有表面证据时直接 Unanalyzed。项目自己的公有基类名单仍然没有，也不在本任务补。
- 省略 `required` 时的字段默认表仍不冻结。上面只接受源码里写明的 `required=True`。
- `partial=True`、`extra_kwargs` 和父类字段覆盖还不能从现有 stage04 节点可靠读出。
- 没有检测器，所以不把生命周期写成 `registered`。现有约定里，`registered` 表示卡片已登记且检测器未接入；本卡片的必填证据和表面证据仍依赖尚未接入的切片读取，验证也还没有构造测试。

## 有效性计划

`empirical_required`：合同冻结并实现之后，用构造样例检查新增必填、可选、非公有 helper 和缺失路由。再以冻结 NetBox PR 的人工标注看命中是否符合定义。现在没有检测器，也没有 Precision、Recall 或兼容性失败次数。验收标准待验证设计确定，不预填结果。
