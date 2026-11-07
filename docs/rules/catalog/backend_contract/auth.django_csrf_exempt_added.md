# 新增的 Django CSRF 豁免

> 本卡片是设计记录。样例都是构造样例，不是某个已合并 PR 的复原。生命周期保持 `draft`：没有检测器，也没有运行终态。严重度与风险性质是工程负责人的临时判断，不是终局。登记册没有权重字段；概念上的默认权重是 0，本任务不接入评分。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `auth.django_csrf_exempt_added` |
| 规则名称 | 新增的 Django CSRF 豁免 |
| 版本 | `v1` |
| 规则阵营 | `backend_contract` |
| 生命周期 | `draft` |
| 负责人 | `Prisk-System` |

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `external_impact` |
| 适用范围 | 同一 Python 文件中，新出现在函数、方法或类上的 `csrf_exempt` 或 `method_decorator(csrf_exempt)` |
| 依赖层级 | `framework`。阵营是后端契约。`external_impact` 表示设计上关心中间件保护是否还覆盖这个视图，不是已经测得的跨站请求 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `High` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度 `High` 是临时判断。豁免可能是有意的机器接口。`High` 不是权重，也不是一票抬升。后续算法阶段可以修订。

## 3. 为什么制定

### 观察到的工程问题

视图上新加了 `@csrf_exempt`，或用 `method_decorator` 把 `csrf_exempt` 加到方法或类上。

### 为什么值得检测

Django 写明 `csrf_exempt` 把视图标成不受中间件保护。审查者需要看到豁免是这次 diff 加上的，而不是文件里原有的装饰器。

### 现有规则为什么不能覆盖

[`auth.drf_permission_decorator_removed`](auth.drf_permission_decorator_removed.md) 与 [`auth.drf_permission_policy_downgrade`](auth.drf_permission_policy_downgrade.md) 看的是 DRF 权限装饰器和 `permission_classes`。`config.django_sensitive_settings_changed` 的闭集含有 `CSRF_COOKIE_SECURE`，那是设置名，不是视图装饰器。`auth.permission_structure_changed` 只报告权限路径上的粗结构变化。

### 研究或工程价值

框架适配。闭集只含下面两种装饰器形态。不把每个提到 CSRF 的设置都收进来。

## 4. 检测定义

### 比较单位

同一个函数、方法或类上的一个装饰器表达式。base 与 head 按所有者限定名和表达式文本对照。「新增」指 head 有、base 的同一所有者没有这条闭集表达式。

### 适用性

装饰器节点已经保存表达式文本。类装饰器和函数装饰器都算。不要求基类名字属于 `View` 或 `APIView`：`csrf_exempt` 文档把被装饰对象称为视图。不沿其他文件的 `urls.py` 确认它已经挂上路由。

### 闭集

head 的装饰器表达式属于下面之一：

- 直接名称是 `csrf_exempt`，或属性链的最后一段是 `csrf_exempt`，且表达式本身不是别的调用；
- 调用的最后一段是 `method_decorator`，且某个位置参数、关键字 `decorator`，或这两个位置上的列表、元组元素，其最后一段是 `csrf_exempt`。

`csrf_protect`、`requires_csrf_token`、`ensure_csrf_cookie` 不在闭集里。

### 触发条件

闭集表达式出现在 head，base 的同一所有者没有同一表达式，且该装饰器与新增行相交。所有者是这次 diff 里新出现的函数或类时，base 侧记为 `absent`，仍符合触发。一条装饰器一条设计 Finding。

### 触发特征

- `decorator_form`：`source` 为装饰器表达式的直接名称、最后一段，或 `method_decorator` 参数的最后一段；`value_type` 为 `enum`；`operator` 为 `contains`；`threshold` 为 `csrf_exempt`、`method_decorator`；`required` 为 true。`method_decorator` 必须同时满足参数最后一段是 `csrf_exempt`。
- `decorator_added`：`source` 为同一所有者在 base/head 的表达式有无；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true。
- `decorator_changed`：`source` 为装饰器与新增行的交集；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true。

`method_decorator` 的参数若是列表，当前调用节点不保存位置参数的名字数组。名字要从该装饰器的未截断表达式读取。截断时不能匹配。

### 不触发条件

base 与 head 都有同一条 `@csrf_exempt`；只新增 `@csrf_protect`；只改 `CSRF_COOKIE_SECURE`；注释或字符串里出现 `csrf_exempt`；装饰器还在，只改了视图函数体。

### 输入

同一文件的 base/head 装饰器节点和三点 Diff。不发送请求，不读取中间件列表。

### Finding

设计线索：规则 ID、所有者限定名、表达式、base 侧是同一表达式或 `absent`、设计标签 `external_impact`。不证明存在跨站请求伪造。本任务不生成 Finding。

### 证据位置

文件、所有者限定名、装饰器表达式、行号、base 侧状态。

### 上下文切片

该装饰器。不附带整个视图函数体。

### 影响类型

认证与请求保护声明。

### 设计终态

设计预期，不是运行结果。

- Hit：闭集装饰器相对 base 是新增，且与新增行相交。
- NotFound：适用文件的装饰器表达式已经读完，没有新增的闭集表达式。原有 `@csrf_exempt` 未改动也是 NotFound。
- Unanalyzed：表达式被截断，或名字是别名、星号导入后的局部名，看不出最后一段是 `csrf_exempt`。原因是 `unsupported_stage04_details` 或 `missing_framework_context`。别名用后者。不把残缺文本记成 Hit，也不记 NotFound。

### 构造样例

正例：head 新增 `@csrf_exempt`，base 的同一函数没有这个装饰器。另一个正例：类上新增 `@method_decorator(csrf_exempt, name="dispatch")`。

反例：同一函数上 `@csrf_exempt` 在 base 与 head 都在，只改了返回值。另一个反例：新增 `@csrf_protect`，或把 `CSRF_COOKIE_SECURE = False` 改成 `True`。

无法分析：`from django.views.decorators.csrf import csrf_exempt as skip_csrf` 之后使用 `@skip_csrf`。最后一段不是 `csrf_exempt`，记 Unanalyzed，不记 Hit。

### 与现有规则的去重

权限装饰器删除、权限策略降级和 `CSRF_COOKIE_SECURE` 仍由各自的规则表达。本规则不因为视图同时改了 `permission_classes` 而抑制或合并。`csrf_exempt` 被删掉不是本规则的反向 Hit。

## 5. 理论与项目依据

- [Django `csrf_exempt`](https://docs.djangoproject.com/en/stable/ref/csrf/#django.views.decorators.csrf.csrf_exempt) 写明该装饰器把视图标成不受中间件保护，并给出函数视图示例。
- [Django `method_decorator`](https://docs.djangoproject.com/en/stable/ref/utils/#django.utils.decorators.method_decorator) 写明它把函数装饰器转成方法装饰器，装饰类时必须给出方法名 `name`。
- [`config.django_sensitive_settings_changed`](config.django_sensitive_settings_changed.md) 已核对部署清单里的 `CSRF_COOKIE_SECURE`。那一栏不覆盖视图装饰器。
- 这些文档说明豁免的含义。它们不证明这次新增已经被利用，也没有 NetBox 试点结果。

## 6. 限制与反例

- 可能误报：支付回调、健康检查或测试里的视图有意豁免，仍会命中。测试路径不排除。
- 可能漏报：豁免写在中间件子类或 `dispatch` 的运行时包装里，装饰器表达式没有出现 `csrf_exempt`。
- Python 动态特性限制：装饰器由工厂函数返回，或 `method_decorator` 的参数是名字列表变量。
- 规则不判断：中间件是否启用、视图是否挂在 URL 上、请求是否真的跨站。
- 必须人工复核的上下文：豁免的方法是不是会改状态，以及同一视图上还有没有别的来源校验。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `empirical_required` |
| 验证方法 | 将来的构造样例覆盖两种闭集形态、原有装饰器、`csrf_protect`、设置名和别名。不发送请求，不下载真实 PR |
| 数据集 | 未圈定 |
| 判定依据 | 将来的人工标注。官方文档只定义装饰器 |
| 指标 | 不预填 |
| 验收标准 | 待实现任务再写。当前没有检测器 |
| 未解决问题 | `method_decorator` 的位置参数还不是名字数组；别名不解析；没有实证 |
