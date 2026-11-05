# 权限装饰器被移除

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `auth.drf_permission_decorator_removed` |
| 版本 / 阵营 / 生命周期 | `v1` / `backend_contract` / `draft` |
| 负责人 | `Prisk-System` |
| 风险性质 / 依赖层级 | `external_impact` / `framework` |
| 适用范围 | Django 与 Django REST framework 视图上的权限装饰器；NetBox 同时含有 API 与 UI 视图 |
| 分析目标层 / 证据形态 | `ast_syntax`, `diff_delta` / `code_slice`, `symbol_pair` |
| 严重度 / 一票抬升 | `High` / `false`，条件 `null`；严重度仍是待验证的设计值 |

## 制定理由

视图上的权限装饰器如果在 diff 中消失，调用方可能不再经过原先写在装饰器里的检查。这只说明声明被拿掉，不说明运行时一定变成匿名可访问。NetBox 的认证与权限场景已纳入 [02 阶段调研](../../../versions/v1.0.0/02-PR采样&定风险场景/NetBox调研.md)，但 NetBox 的 DRF 视图更多使用类属性 `permission_classes`，而不是装饰器。

登记分类里的 `external_impact` 表示设计上关心 diff 之外的调用方是否仍受同一声明保护。它不是已经测得的外部影响。`auth.drf_permission_policy_downgrade` 拟定覆盖 `AllowAny`、空权限列表和类属性降级，本规则不重复那部分。`auth.permission_structure_changed` 只报告权限路径上的结构变化，不区分装饰器删除。

## 检测定义

拟定合同如下。装饰器名单和“删除后是否仍有等价类属性”都还没冻结，所以生命周期保持 `draft`，本迭代没有检测器。

- 拟定对象：函数、方法或类上的装饰器表达式。候选名单需要在实现前固定，当前只能列出需要裁决的来源：DRF 的 `permission_classes`、`authentication_classes` 装饰器，以及 Django 的 `login_required`、`permission_required`、`user_passes_test`。NetBox 自己的封装是否并入，尚未决定。
- 拟定触发：同一函数或类在 base 上有名单内装饰器，head 上该装饰器表达式消失，且消失处与删除行相交。一条装饰器一条 Finding。只改装饰器参数不算删除，留给降级规则。
- 拟定不触发：装饰器还在；新增装饰器；名单外的 `@action` 或缓存装饰器；类属性 `permission_classes = [...]` 的变化。base 或 head 的装饰器列表无法读取时标记未评估。
- 拟定特征：`decorator_name`（装饰器表达式的直接名称或属性名，`contains` 冻结后的名单）；`decorator_removed`（base 有、head 无，布尔值，`eq true`）。两个都要成立。
- 输入与证据：base/head 的装饰器节点和三点 Diff。Finding 设计为复核线索，带函数限定名、被移除的表达式和 `external_impact` 这一设计标签。它不证明请求已经越权。

示例：

```python
@permission_classes([IsAuthenticated])
def endpoint(request):
    ...
```

若 head 删除这一行，而函数仍是视图，则符合拟定触发。若删除的是 `@action(detail=True)`，不符合。

## 依据

- [DRF `@api_view` 与权限装饰器](https://www.django-rest-framework.org/api-guide/views/#api_view) 说明函数视图可以用装饰器设置 `permission_classes` 和 `authentication_classes`。
- [DRF Permissions](https://www.django-rest-framework.org/api-guide/permissions/) 说明权限类在视图访问时被检查。文档不说“删掉装饰器”本身就是漏洞，因为权限还可能来自默认设置或类属性。
- [Django `login_required`](https://docs.djangoproject.com/en/stable/topics/auth/default/#the-login-required-decorator) 和 [`permission_required`](https://docs.djangoproject.com/en/stable/topics/auth/default/#the-permission-required-decorator) 是 UI 视图上的另一组装饰器。是否与 DRF 装饰器放进同一条规则，本卡片没有冻结。
- NetBox 语境来自仓库内调研，不额外声称某个 CVE。

## 限制与反例

把装饰器挪成等价的 `permission_classes` 属性会看起来像删除。默认 `DEFAULT_PERMISSION_CLASSES` 仍可能保护视图。装饰器工厂和别名会漏报。规则不登录、不构造请求，也不比较两个权限类谁更严。那是降级规则尚未冻结的部分。

人工复核要看装饰器是否换成类属性、全局默认权限，以及该视图是否真的挂在 URL 上。

## 未冻结、因此保持 draft 的部分

- DRF 装饰器、Django 认证装饰器和 NetBox 封装的最终名单。
- 删除装饰器但新增等价类属性时如何抑制 Finding。
- 与 `auth.drf_permission_policy_downgrade` 的切分：空列表和 `AllowAny` 不在本规则里实现。
- stage04 目前没有稳定的“装饰器前后配对”字段专用于这张名单。

## 有效性计划

`empirical_required`：名单冻结后再写构造样例，覆盖删除、保留、换成类属性和名单外装饰器。NetBox 真实 PR 上的语义是否成立，要人工标注后才谈 Precision 或 Recall。当前没有这些数字，也没有检测器。
