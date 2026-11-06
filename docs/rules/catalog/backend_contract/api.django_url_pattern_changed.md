# 路由映射变化

> 本卡片是设计记录。样例都是构造样例，不是某个已合并 PR 的复原。生命周期保持 `draft`：没有检测器，也没有运行终态。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `api.django_url_pattern_changed` |
| 规则名称 | 路由映射变化 |
| 版本 | `v1` |
| 规则阵营 | `backend_contract` |
| 生命周期 | `draft` |
| 负责人 | `Prisk-System` |

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | 同一 Python 文件里对 `path`、`re_path` 或 DRF `router.register` 的直接调用。`include()` 的目标模块不在适用面内 |
| 依赖层级 | `framework`。阵营是后端契约；依赖 Django URL 调度和 DRF router 的调用形态 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `High` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度是待验证的设计值，不是权重。

## 3. 为什么制定

### 观察到的工程问题

`urlpatterns` 或 router 登记里的路由字符串、视图引用或 `name` 在 diff 中变化后，已有的 URL 可能对不上。

### 为什么值得检测

路由字符串是 HTTP 表面的一部分。只看视图函数签名会漏掉“函数还在，路径变了”。

### 现有规则为什么不能覆盖

`api.signature_changed` 按路径粗分类报告签名变化，不比较 `path()` 的 route。`api.drf_viewset_action_changed` 看 ViewSet 动作，不看 `urlpatterns` 里的字符串。

### 研究或工程价值

框架适配。NetBox 的 REST 表面使用 Django URL 与 DRF router。调研文档只说明场景纳入，不提供本规则的命中。

## 4. 检测定义

### 适用性

调用的属性名是 `path`、`re_path` 或 `register`，并且调用节点与新增行或删除行相交。不跟随 `include()` 进入另一个模块，不合并多文件 URLconf。

### 检测边界

现行文档里的比较对象是：

- Django [`path()`](https://docs.djangoproject.com/en/stable/ref/urls/#path) 与 [`re_path()`](https://docs.djangoproject.com/en/stable/ref/urls/#re-path) 的 `route`、`view` 和 `name`；
- DRF router 的 `register`。视图集文档中的用法是 `router.register(r"users", UserViewSet, basename="user")`，见 [ViewSet 示例](https://www.django-rest-framework.org/api-guide/viewsets/#example)。

历史别名 `url()` 未在这次核对的现行 `django.urls` 页作为现行函数列出。见到属性名 `url` 时记 Unanalyzed，不把它并进 `path`。

### 检测对象

同一文件 base/head 中上述调用。

### 触发条件

适用调用在一侧消失，或两侧都能读到 route 文本且 route 文本不同，或 `name` / `basename` 关键字的字符串不同。视图表达式文本不同也记一条设计 Finding，并在证据里标明变的是 view 而不是 route。

### 触发特征

- `routing_callee`：`source` 为调用节点 `details.callee` 的最后一段属性名；`value_type` 为 `string`；`operator` 为 `contains`；`threshold` 为 `path`、`re_path`、`register`；`required` 为 true。
- `route_text`：`source` 为第一个位置参数或 `route` 关键字的字符串文本；`value_type` 为 `string`；`operator` 为 `changed`；`required` 为 true。新增或删除调用时，缺失的一侧用空文本参与“有无”比较，前提是存在的一侧文本可读。
- `call_changed`：`source` 为调用节点与新增行或删除行的交集；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true。

当前 stage04 的 call 节点有 `callee`、`args_count` 和 `keyword_names`，没有位置参数的字符串值。`literal_text` 只保留赋值和关键字上的单个字符串，不保留 `path("devices/")` 这种位置参数。因此 route 文本是有界的新输入，不是已经结构化的字段。在该输入被实现任务接上之前，不能只凭 `args_count` 变化记 Hit。

### 不触发条件

route、view 和 name 的可读文本都没变，只改了无关的格式；调用不在上述三个属性名里；`include()` 所指向的模块内容变了，但本文件的 `include()` 调用文本没变。

### 输入

同一文件的 base/head AST、三点 Diff，以及尚未作为结构化字段存在的位置参数字符串。不构建 URLconf 图。

### Finding

设计线索：规则 ID、调用名、变化的 route 或 name、文件和行、`pr_intrinsic_risk`。不证明线上路由已经 404。本任务不生成 Finding。

### 证据位置

文件、调用切片、route 文本的前后值。文本不可读时证据写 `unavailable`，并且该调用不是 Hit。

### 上下文切片

展示该调用前后各不多于该列表项的相邻项。不展开 `include()` 的目标文件。

### 影响类型

接口路径。

### Unanalyzed

设计预期，不是运行结果。

- route 或 name 的字面量读不出、切片被截断，或参数是 `gettext_lazy()` 以外的函数调用：`unsupported_stage04_details`。Django 允许 route 使用 `gettext_lazy()`；这种调用见到时也记 Unanalyzed，不把函数名当成路径。
- 属性名是 `include`：`missing_framework_context`。文档说明它装入另一个 URLconf。[`include()`](https://docs.djangoproject.com/en/stable/ref/urls/#include) 的目标不在本文件解析。
- 属性名是 `url` 或其他未列入的路由包装：`missing_framework_context`。
- 视图参数是跨文件的名称引用时，只比较本文件写出来的表达式文本，不解析它指向的函数。表达式读不出则 Unanalyzed。

### 构造样例

正例：同一文件里 `path("devices/", DeviceView)` 变成 `path("dcim/devices/", DeviceView)`，两段 route 字符串都能读到。

反例：`path("devices/", DeviceView)` 只被重新换行，route 与 view 文本相同。另一个反例：`DeviceView` 的函数体改了，`urls.py` 没有变化。

边界：`path("api/", include("api.urls"))` 的目标模块里删了一条路由。本文件这条 `include` 没有变。不跟随 `api.urls`，也不把本文件记成 Hit。

## 5. 理论与项目依据

- [Django `path()`](https://docs.djangoproject.com/en/stable/ref/urls/#path)、[`re_path()`](https://docs.djangoproject.com/en/stable/ref/urls/#re-path) 和 [`include()`](https://docs.djangoproject.com/en/stable/ref/urls/#include) 说明 route、view 和包含关系。`include()` 的目标是另一个模块。
- [DRF ViewSet 与 `register`](https://www.django-rest-framework.org/api-guide/viewsets/#example) 说明 router 登记会生成 URL。同页警告不要在 prefix 末尾加斜线。这是框架约定，不是本项目已经测得的误报率。
- [DRF Routers](https://www.django-rest-framework.org/api-guide/routers/) 是 router 行为的总页。本卡片不从该页推出尚未逐段核对的默认路由表。
- NetBox 调研只提供项目场景，不提供 PR 编号或命中次数。

## 6. 限制与反例

- 可能误报：route 只改了引号或原始字符串前缀，规范化前看起来不同；`name` 改了但外部 URL 仍由其他名字兼容。
- 可能漏报：路由由循环拼接，或写在本规则不识别的项目包装函数里。
- Python 动态特性限制：`urlpatterns += something()` 的右侧不在本文件展开。
- 规则不判断：反向解析是否失败、客户端是否缓存了旧 URL、斜线策略在运行中的实际匹配。
- 必须人工复核的上下文：`include()` 链、`app_name` 和发布说明里的路径变更。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `empirical_required` |
| 验证方法 | 构造样例先覆盖 route 变化、纯格式、`include` 不跟随和字面量缺失。真实 PR 不在本任务 |
| 数据集 | 未圈定 |
| 判定依据 | 将来的人工标注。当前没有检测器 |
| 指标 | 不预填 Precision 或 Recall |
| 验收标准 | 待实现任务再写。位置参数文本尚未进入 stage04 之前，不能验收为可运行规则 |
| 未解决问题 | 位置参数字符串还不是结构化字段；`include()` 图明确不做 |
