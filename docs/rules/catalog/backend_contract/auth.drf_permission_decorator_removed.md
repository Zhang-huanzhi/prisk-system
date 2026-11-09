# 规则说明卡片：`auth.drf_permission_decorator_removed`

> 本卡片是设计记录。样例都是构造样例，不是某个已合并 PR 的复原。生命周期是 `implemented`（022 接入检测器与构造测试）；默认权重 0，不是 `validated`，也没有真实 PR 实证。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `auth.drf_permission_decorator_removed` |
| 规则名称 | 权限装饰器被移除 |
| 版本 | `v1` |
| 规则阵营 | `backend_contract` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `external_impact` |
| 适用范围 | Django 与 Django REST framework 视图上、最后一段属于下面五段闭集的装饰器。NetBox 同时含有 API 与 UI 视图 |
| 依赖层级 | `framework`。阵营是后端契约。`external_impact` 表示设计上关心调用方是否仍受同一声明保护，不是已经测得的外部影响 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `High` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度仍是待验证的设计值，不是权重。

## 3. 为什么制定

### 观察到的工程问题

视图上的权限装饰器在 diff 中消失。这只说明声明被拿掉，不说明运行时一定变成匿名可访问。

### 为什么值得检测

NetBox 的认证与权限场景已纳入 [02 阶段调研](../../../versions/v1.0.0/02-PR采样&定风险场景/NetBox调研.md)。NetBox 的 DRF 视图更多使用类属性 `permission_classes`，装饰器删除仍然是另一条可见表面。调研计数不是命中率。

### 现有规则为什么不能覆盖

[`auth.drf_permission_policy_downgrade`](auth.drf_permission_policy_downgrade.md) 看留下的列表是否变成 `AllowAny` 或空列表。本规则不解释留下的列表变成了什么。`auth.permission_structure_changed` 只报告权限路径上的结构变化，不区分装饰器删除。

### 研究或工程价值

框架适配。五段名字是设计闭集。NetBox 自己的封装不在闭集里，也不因 [已知框架基类映射](../../known-framework-bases.md) 并入；那张表不覆盖装饰器名字。

## 4. 检测定义

- **检测对象**：同一函数或同一类上的一条装饰器。函数或类本身在 head 仍然存在。
- **触发条件**：表达式最后一段属于 `permission_classes`、`authentication_classes`、`login_required`、`permission_required`、`user_passes_test`；base 有这条装饰器，head 没有，并且删除行与它相交。一条装饰器一条设计 Finding。只改装饰器参数不算删除。
- **触发特征**：`decorator_name`（`source` 为装饰器表达式的直接名称或属性最后一段；`value_type` 为 `string`；`operator` 为 `contains`；`threshold` 为上面五个名字；`required` 为 true）。`decorator_removed`（`source` 为 base 有、head 无，且与删除行相交；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true）。
- **不触发条件**：装饰器还在；新增装饰器；`@action` 或名单外的缓存装饰器；类属性 `permission_classes = [...]` 的取值变化。空列表和 `AllowAny` 只属于权限降级规则。
- **输入**：同一文件 base/head 的装饰器节点和三点 Diff。
- **Finding**：设计线索，函数或类限定名、被移除的表达式、`external_impact`。不证明请求已经越权。022 生成运行时 Finding；默认权重 0。
- **证据位置**：文件、限定名、被移除的表达式、相交的删除行、base 侧切片。
- **上下文切片**：该装饰器表达式。不附带整个函数体。
- **影响类型**：权限声明。

同一文件的 head 出现 `permission_classes = ...` 时，记 `missing_framework_context`，不是 Hit，也不是 NotFound。这包括赋在与被删装饰器无关的类上。

同一文件里的无关类仍触发抑制。下面的 head 中，`endpoint` 上的闭集装饰器已经删除，`OtherView` 与它不是同一个类：

```python
def endpoint(request):
    return None

class OtherView(APIView):
    permission_classes = [IsAuthenticated]
```

设计终态是 Unanalyzed，不是 Hit。收窄到同一个函数或同一个类，是未决提议。现行抑制不声称和「只看同一所有者」等价。

表达式截断、工厂调用或别名，记 `unsupported_stage04_details`。适用装饰器已经看完且没有缺口时，才可以记 NotFound。运行时的 `auth.permission_structure_changed` 仍可能因路径或权限文本出现。本规则不抑制它，也还没有 Finding。

构造正例：`@permission_classes([IsAuthenticated])` 整行删除，函数还在，且整个文件的 head 都没有 `permission_classes = ...`。构造反例：删除 `@action(detail=True)`。不支持：装饰器改成别名后再删掉别名。

## 5. 理论与项目依据

- [DRF `@permission_classes`](https://www.django-rest-framework.org/api-guide/permissions/#setting-the-permission-policy) 与 Django 的 `login_required`、`permission_required`、`user_passes_test` 是本闭集的文档来源。文档不证明删除装饰器之后请求已经匿名可写。
- NetBox 调研把认证与权限列为场景。它不把项目封装装饰器自动并入这五个名字。

## 6. 限制与反例

- 可能误报：装饰器被换成同等严格的类属性，文件里又能看见 `permission_classes = ...`。现行合同把这种情况记成 Unanalyzed，而不是放行。
- 可能漏报：NetBox 自己的封装装饰器不在五段闭集里；别名删除也看不到。
- Python 动态特性限制：装饰器由工厂函数返回，最后一段不是闭集名字。
- 规则不判断：请求是否已经越权，全局默认是否本来就放开。
- 必须人工复核的上下文：装饰器是否换成类属性、全局默认权限，以及该视图是否真的挂在 URL 上。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `empirical_required` |
| 验证方法 | 名单冻结后再写构造样例，覆盖删除、保留、换成类属性和名单外装饰器。不下载真实 PR |
| 数据集 | 未圈定 |
| 判定依据 | 将来的人工标注 |
| 指标 | Precision、Recall 不预填 |
| 验收标准 | 022 以构造样例验收。当前 022 已接入检测器 |
| 未解决问题 | 五段名字还没有写进运行时代码。同一文件抑制，包括无关类 `OtherView`。收窄到同一个函数或同一个类，是未决提议。022 已接入检测器 |
