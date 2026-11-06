# ViewSet 暴露动作变化

> 本卡片是设计记录。样例都是构造样例，不是某个已合并 PR 的复原。生命周期保持 `draft`：没有检测器，也没有运行终态。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `api.drf_viewset_action_changed` |
| 规则名称 | ViewSet 暴露动作变化 |
| 版本 | `v1` |
| 规则阵营 | `backend_contract` |
| 生命周期 | `draft` |
| 负责人 | `Prisk-System` |

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | 同一类语句的基类文本含有 `ViewSet`、`GenericViewSet`、`ModelViewSet` 或 `ReadOnlyModelViewSet` 的类。只看该类体里的标准动作方法和 `@action` |
| 依赖层级 | `framework`。阵营是后端契约；动作名单来自 DRF，而不是任意名为 `list` 的方法 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `High` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度是待验证的设计值，不是权重。

## 3. 为什么制定

### 观察到的工程问题

ViewSet 上新增、删除或改写暴露给 router 的动作后，URL 集合会变。调用方未必改函数签名。

### 为什么值得检测

标准动作和 `@action` 是 DRF 生成路由的依据。只看 `urls.py` 会漏掉“登记行没变、动作集合变了”。

### 现有规则为什么不能覆盖

`api.django_url_pattern_changed` 看本文件的 `path` / `register` 调用。`api.signature_changed` 不识别动作名单。权限装饰器规则不判断动作是否还暴露。

### 研究或工程价值

框架适配。动作名单以下列官方说明为准，不另造一套路由表。

## 4. 检测定义

### 适用性

类语句的 `bases` 文本里出现上述四个直接名称之一。基类只是项目自己的 `NetBoxModelViewSet` 这类名字时，不适用 Hit。不沿继承链追到其他文件。

### 检测边界

DRF 写明的标准动作是 `list`、`create`、`retrieve`、`update`、`partial_update`、`destroy`。[`ModelViewSet`](https://www.django-rest-framework.org/api-guide/viewsets/#modelviewset) 提供这六个；[`ReadOnlyModelViewSet`](https://www.django-rest-framework.org/api-guide/viewsets/#readonlymodelviewset) 只提供 `list` 和 `retrieve`。额外动作用 [`@action`](https://www.django-rest-framework.org/api-guide/viewsets/#marking-extra-actions-for-routing)，由 `detail` 和 `methods` 决定路由。

`http_method_names` 不在这次已核对的动作名单里。只改它时记 Unanalyzed。

### 检测对象

适用类体中：名字属于标准动作的函数；装饰器文本含 `@action` 的函数。

### 触发条件

与新增行或删除行相交，且满足下面之一：

- 标准动作函数在 base 与 head 的有无不同；
- `@action` 函数在 base 与 head 的有无不同；
- 同一个 `@action` 函数的装饰器表达式里，`detail=` 或 `methods=` 的源码文本不同。

`ReadOnlyModelViewSet` 上出现 `create`、`update`、`partial_update` 或 `destroy` 的新增，仍按“类体里多了一个标准动作名”记录，不另判它是否违反只读基类的意图。

### 触发特征

- `viewset_base`：`source` 为类节点 `details.bases` 的文本；`value_type` 为 `string`；`operator` 为 `contains`；`threshold` 为上面四个名字；`required` 为 true。
- `action_name`：`source` 为函数名，或 `@action` 所装饰的函数名；`value_type` 为 `string`；`operator` 为 `present`；`required` 为 true。
- `action_delta`：`source` 为该函数在 base/head 的有无，或装饰器表达式中 `detail` / `methods` 文本；`value_type` 为 `enum`；`operator` 为 `changed`；`threshold` 为 `added`、`removed`、`methods_or_detail_changed`；`required` 为 true。

类节点在类体任意一行变化时都会因行范围相交而保留，`bases` 因此可读。函数节点同理。装饰器节点的 `details.expression` 保存装饰器源码。

### 不触发条件

动作仍在，且 `detail` / `methods` 文本相同，只改了函数体；方法名不在标准名单里，也没有 `@action`；类基类文本不含上述名字。

### 输入

同一文件的 base/head AST 和三点 Diff。不读 router 文件，不调用 `get_extra_actions()`。

### Finding

设计线索：规则 ID、类名、动作名、`added` / `removed` / `methods_or_detail_changed`、`pr_intrinsic_risk`。不证明 URL 已经变化，因为 router 可能没有登记这个类。本任务不生成 Finding。

### 证据位置

类限定名、基类文本、函数名、装饰器表达式、相交行号。

### 上下文切片

类语句一行和该动作的装饰器及 `def` 行。不附带整个类体。

### 影响类型

接口表面。

### Unanalyzed

设计预期，不是运行结果。

- 基类不是四个直接名称之一：`missing_framework_context`。不记 NotFound。
- 装饰器表达式被截断，读不出 `detail` 或 `methods`：`unsupported_stage04_details`。不能把截断后的文本差异当成 Hit。
- 只改 `http_method_names`，或只改 `get_permissions`：`missing_framework_context`。
- router 是否登记了这个类：未知。未知不升格为 Hit，也不把“类变了”当成 URL 已变。本规则的 Hit 只表示类体动作集合的本地差异。

### 构造样例

正例：`class DeviceViewSet(viewsets.ModelViewSet)` 的 head 删掉 `def destroy`，或把 `@action(detail=True, methods=["post"])` 改成 `methods=["get"]`。

反例：同一个 `destroy` 只改了函数体里的查询，`def` 与装饰器未变。另一个反例：`class DeviceHelper` 没有 ViewSet 基类，增删 `list` 不触发。

边界：`class DeviceViewSet(BaseDeviceViewSet)`，`BaseDeviceViewSet` 定义在别的文件并继承 `ModelViewSet`。本文件基类文本对不上四个名字，记 Unanalyzed，不沿文件外的基类查找。

## 5. 理论与项目依据

- [DRF ViewSet 动作](https://www.django-rest-framework.org/api-guide/viewsets/#viewset-actions) 列出六个标准方法名。
- [`ModelViewSet`](https://www.django-rest-framework.org/api-guide/viewsets/#modelviewset) 与 [`ReadOnlyModelViewSet`](https://www.django-rest-framework.org/api-guide/viewsets/#readonlymodelviewset) 说明哪些动作由基类提供。
- [`@action`](https://www.django-rest-framework.org/api-guide/viewsets/#marking-extra-actions-for-routing) 说明 `detail` 与 `methods`，并写明默认方法是 GET。`@action(...).mapping.delete` 这种附加映射见到时，装饰器链比单个表达式复杂，按 Unanalyzed 处理，不在本卡片里猜路由。
- [Routers](https://www.django-rest-framework.org/api-guide/routers/) 说明登记以后才会变成 URL。本规则不读取登记点。

## 6. 限制与反例

- 可能误报：动作方法还在，但项目用 `get_extra_actions` 或自定义 router 把它排除了。本地类体看不出这层过滤。
- 可能漏报：动作继承自其他文件的基类，子类没有重写。
- Python 动态特性限制：运行时 `setattr` 添加的动作没有函数节点。
- 规则不判断：生成出来的具体 URL、尾斜线、basename 是否冲突。
- 必须人工复核的上下文：router 登记、自定义路由类，以及只读基类上多出来的写动作是否是有意覆盖。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `empirical_required` |
| 验证方法 | 构造样例覆盖标准动作增减、`@action` 的 methods 变化、非 ViewSet 类和跨文件基类。不下载真实 PR |
| 数据集 | 未圈定 |
| 判定依据 | 将来的人工标注 |
| 指标 | 不预填 |
| 验收标准 | 待实现任务再写 |
| 未解决问题 | 自定义 router 与跨文件继承不做；没有检测器 |
