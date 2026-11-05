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

下面是拟定合同，还不能实现。生命周期保持 `draft`，因为“公有”和“必填”仍然依赖尚未冻结的项目与框架信息。

- 拟定对象：DRF `Serializer` / `ModelSerializer` 类体里新增的字段赋值，以及已经能对应到路由的 `APIView` 方法或 ViewSet 动作上新增的、没有默认值的参数。GraphQL 字段、普通 helper 和管理命令不在拟定范围内。
- 拟定触发：base 中不存在该字段或参数，head 中存在；序列化器字段没有 `required=False`，并且不是只在 `partial=True` 的更新里才必填的情形；函数参数没有默认值。变化出现在新增行上。
- 拟定不触发：带默认值的参数；`required=False`；只改字段标签或 `help_text`；测试客户端里的调用；无法把类或函数连到 URL router 时不猜测它是公有接口。
- 拟定特征：`parameter_added`（base 签名或字段集合里没有、head 里有，布尔值，`eq true`）；`required_flag`（静态可见的必填状态，布尔值，`eq true`）；`public_route`（存在已解析的 URL 或 router 登记，布尔值，`eq true`）。三条都要成立。任一输入缺失时该候选标记未评估，而不是通过。
- 输入与证据：head/base AST、三点 Diff，以及一份尚未提供的路由到 callable 映射。Finding 设计为复核线索，影响类型 `pr_intrinsic_risk`，并指出参数名和所在类。它不证明线上客户端已经失败。

示例：

```python
class DeviceSerializer(serializers.ModelSerializer):
    asset_tag = serializers.CharField()  # 若相对 base 是新增且没有 required=False
```

不作为本规则触发的例子：

```python
asset_tag = serializers.CharField(required=False)
def export(self, queryset, output="json"):
    ...
```

## 依据

- [DRF Serializer](https://www.django-rest-framework.org/api-guide/serializers/) 和 [字段 `required`](https://www.django-rest-framework.org/api-guide/fields/#required) 说明序列化器字段默认可为必填，更新时 `partial=True` 会改变这个要求。不同字段类的默认值要以所使用的 DRF 版本文档为准，本仓库没有冻结那张表。
- [DRF Viewsets](https://www.django-rest-framework.org/api-guide/viewsets/) 与 [Routers](https://www.django-rest-framework.org/api-guide/routers/) 说明动作要经过路由才成为 HTTP 表面。当前 stage04 没有这条链接。
- NetBox 场景纳入依据是仓库内的 [NetBox 调研](../../../versions/v1.0.0/02-PR采样&定风险场景/NetBox调研.md)。这里不引用未核对的漏洞编号。

## 限制与反例

即便将来实现，内部服务函数新增参数、只被测试调用的 serializer、以及由 `to_internal_value` 动态补齐的字段都会偏离静态必填判断。`ModelSerializer` 从模型生成的隐式字段如果没写在类体里，AST 看不到。规则不发送 HTTP 请求，不判断客户端兼容范围。

人工复核需要路由登记、序列化器继承链、`partial` 更新路径，以及发布说明是否把该字段标成不兼容变更。

## 未冻结、因此保持 draft 的部分

- 哪个路径或基类算 NetBox 公有 REST，还没有项目配置。
- 字段类的默认 `required` 依赖 DRF 版本，版本表未冻结。
- `partial=True`、`extra_kwargs` 和父类字段覆盖还不能从现有 stage04 节点可靠读出。
- 没有路由映射时，不能把“函数多了一个参数”冻结成公有接口合同。

## 有效性计划

`empirical_required`：合同冻结并实现之后，用构造样例检查新增必填、可选、非公有 helper 和缺失路由。再以冻结 NetBox PR 的人工标注看命中是否符合定义。现在没有检测器，也没有 Precision、Recall 或兼容性失败次数。验收标准待验证设计确定，不预填结果。
