# DRF 权限策略显式降级

> 本卡片是设计记录。样例都是构造样例，不是某个已合并 PR 的复原。生命周期保持 `draft`：没有检测器，也没有运行终态。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `auth.drf_permission_policy_downgrade` |
| 规则名称 | DRF 权限策略显式降级 |
| 版本 | `v1` |
| 规则阵营 | `backend_contract` |
| 生命周期 | `draft` |
| 负责人 | `Prisk-System` |

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `external_impact` |
| 适用范围 | 同一类或同一函数上，写在源码里的 `permission_classes` 属性，或 `@permission_classes(...)` 的参数列表 |
| 依赖层级 | `framework`。阵营是后端契约。`external_impact` 只表示设计上关心调用方是否仍受同一声明保护，不是已经测得的外部影响 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `High` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度是待验证的设计值，不是权重。

## 3. 为什么制定

### 观察到的工程问题

视图上的权限列表从明确的限制类改成 `AllowAny`，或改成空列表、空元组。

### 为什么值得检测

DRF 说明空列表与 `AllowAny` 都是不加限制的写法，而且类属性或装饰器会忽略 `settings` 里的默认列表。这是声明变化，不是一次越权实验的结果。

### 现有规则为什么不能覆盖

[`auth.drf_permission_decorator_removed`](auth.drf_permission_decorator_removed.md) 只看装饰器表达式是否消失，不解释留下的列表变成了什么。`auth.permission_structure_changed` 只报告权限路径上的结构变化。

### 研究或工程价值

框架适配。不比较自定义权限类谁更严；那需要项目自己的强弱顺序，本任务不设定这种顺序。

## 4. 检测定义

### 适用性

同一类体里的 `permission_classes = ...`，或同一函数上 `@permission_classes(...)`。不读其他文件的 `REST_FRAMEWORK` 设置，不调用 `get_permissions()`。

### 检测边界

只把下面两种 head 形态当成显式降级，并且 base 不是同一种形态：

- 列表、元组或单个类的直接名称是 `AllowAny`，或属性链的最后一段是 `AllowAny`；
- `permission_classes` 被写成空列表或空元组。

[权限策略](https://www.django-rest-framework.org/api-guide/permissions/#setting-the-permission-policy) 写明：未指定时默认是 `AllowAny`；类属性或装饰器会忽略 `settings.py` 里的默认列表。[`AllowAny`](https://www.django-rest-framework.org/api-guide/permissions/#allowany) 写明空列表或空元组与它一样，是不加限制。

`IsAuthenticated` 改成 `IsAuthenticatedOrReadOnly`、两个自定义类互换、按位组合 `IsAuthenticated | ReadOnly`，都不是本规则的 Hit。文档说明了这些类和运算符，但没有给出本项目可用的全序。

`authentication_classes` 不在本规则的触发面里。这次核对的权限页没有把“空的认证类列表”定义成与 `AllowAny` 相同的语句。

### 检测对象

字段赋值节点和装饰器表达式。

### 触发条件

适用赋值或装饰器与新增行相交，head 属于上面两种形态，base 的同一属性或同一装饰器不属于这两种形态。base 没有该属性、head 新增 `AllowAny` 或空列表，也符合触发：这是从“未在本文件声明”变成“显式不加限制”。它不证明原来的全局默认更严。证据必须写明 base 侧是 `absent`。

### 触发特征

- `policy_binding`：`source` 为赋值目标名或装饰器名；`value_type` 为 `string`；`operator` 为 `eq`；`threshold` 为 `permission_classes`；`required` 为 true。
- `downgrade_form`：`source` 为 head 侧列表元素的直接名称，或空列表/空元组；`value_type` 为 `enum`；`operator` 为 `contains`；`threshold` 为 `AllowAny` 与 `empty`；`required` 为 true。
- `binding_changed`：`source` 为该节点与新增行的交集；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true。

当前 call 与 literal 节点不把列表元素保存成名字数组。`AllowAny` 是否在列表里，要从赋值或装饰器的源码切片读取。切片截断时不能匹配。

### 不触发条件

head 仍是 `IsAuthenticated` 或其他非 `AllowAny` 的直接名称；只改了无关格式；删除装饰器但没有留下 `AllowAny` 或空列表，那是装饰器删除规则的范围。

### 输入

同一文件 base/head AST 和三点 Diff。不读设置模块。

### Finding

设计线索：规则 ID、绑定位置、head 形态、base 形态或 `absent`、设计标签 `external_impact`。不证明请求已经匿名可写。本任务不生成 Finding。

### 证据位置

文件、类或函数限定名、赋值或装饰器切片、行号。

### 上下文切片

只展示该赋值或该装饰器。不附带视图函数体。

### 影响类型

权限声明。

### Unanalyzed

设计预期，不是运行结果。

- 列表里有别名、星号导入后的名字，或 `get_permissions` 的返回值：`missing_framework_context`。
- 切片截断，或列表元素不是直接名称也不是以 `AllowAny` 结尾的属性：`unsupported_stage04_details`。
- 权限类用 `&`、`|`、`~` 组合：`missing_framework_context`。文档说明可以这样组合，本规则不化简布尔表达式。
- 对象级 `has_object_permission` 与 `get_queryset` 过滤不属于本规则，也不在 20 条候选的实现范围内。

### 构造样例

正例：base 为 `permission_classes = [IsAuthenticated]`，head 为 `permission_classes = [AllowAny]`。另一个正例：head 为 `permission_classes = []`，base 为 `[IsAuthenticated]`。

反例：`[IsAuthenticated]` 改成 `[IsAdminUser]`。另一个反例：只删除 `@permission_required("dcim.view_device")`，没有写 `AllowAny`。

边界：`permission_classes = [permissions.AllowAny]` 的最后一段是 `AllowAny`，按本卡片可以进入设计 Hit。`permission_classes = [PublicRead]` 不能从名字推出它等于 `AllowAny`，记 Unanalyzed。

### 014 比较单位

`lifecycle` 仍是 `draft`。没有检测器，不写成 `registered`。

- **比较单位**：同一类或同一函数上的 `permission_classes` 赋值，或 `@permission_classes(...)`。
- **变更后**：列表、元组或单个表达式的最后一段是 `AllowAny`，或者写成空列表、空元组。
- **变更前**：同一绑定不是这两种形态。base 没有该绑定时，证据写 `absent`，不证明原来的全局默认更严。
- **排除**：`IsAuthenticated` 换成 `IsAdminUser`；只删除 `@permission_required`，没有留下 `AllowAny` 或空列表，那是装饰器删除规则；`authentication_classes`；用 `&`、`|`、`~` 组合的表达式。
- **证据位置**：文件、限定名、赋值或装饰器切片、行号、head 形态、base 形态或 `absent`。
- **设计终态**：别名、星号导入、`get_permissions` 或组合表达式是 `missing_framework_context`。切片截断是 `unsupported_stage04_details`。适用绑定已经看完且没有缺口时，才可以记 NotFound。当前没有运行终态。

## 5. 理论与项目依据

- [DRF：设置权限策略](https://www.django-rest-framework.org/api-guide/permissions/#setting-the-permission-policy) 说明默认值、类属性和 `@permission_classes`，以及类属性会忽略设置文件中的默认列表。
- [DRF：`AllowAny`](https://www.django-rest-framework.org/api-guide/permissions/#allowany) 说明无限制访问，并写明空列表或空元组效果相同。
- [DRF 设置 `DEFAULT_PERMISSION_CLASSES`](https://www.django-rest-framework.org/api-guide/settings/#default_permission_classes) 是全局默认的设置项。本规则不打开设置文件。
- 对象级权限的官方限制见同一权限页的 [Object level permissions](https://www.django-rest-framework.org/api-guide/permissions/#object-level-permissions)。那是另一类问题，本规则不覆盖。

## 6. 限制与反例

- 可能误报：base 没有本地声明，head 写了 `AllowAny`，但全局默认本来就是 `AllowAny`。证据里的 `absent` 就是为了让复核看到这一点。
- 可能漏报：降级写在 `get_permissions()` 或另一个混入类里。
- Python 动态特性限制：权限类由工厂函数返回。
- 规则不判断：某个自定义类是否比另一个更松，也不发请求。
- 必须人工复核的上下文：全局默认、继承来的 `permission_classes`，以及该视图是否挂在 URL 上。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `empirical_required` |
| 验证方法 | 构造样例覆盖 `AllowAny`、空列表、非全序替换、别名和截断切片。不下载真实 PR |
| 数据集 | 未圈定 |
| 判定依据 | 将来的人工标注 |
| 指标 | 不预填 |
| 验收标准 | 待实现任务再写。当前没有权限类强弱表，也不计划在本规则里补一张 |
| 未解决问题 | 列表元素还不是结构化名字；`get_permissions` 不解释 |
