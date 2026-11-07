# 命中与可标注性筛查

口径在 [protocol.md](protocol.md)。机器可读记录是 [screen.json](screen.json)。本节是 2026-11-07 这一轮的结果。

分析调用了未改动的 `analyze_branches`。输入是合并提交与其第一父提交上的变更文件，不是完整 NetBox 克隆。16 条的文件数和增删行数都与 GitHub PR 计数一致。草稿卡片没有检测器，下面的设计判断是人工对照卡片。

Hit 不是缺陷。这里没有 Precision、Recall 或有效性。

## 计数

八条研究规则是七条代码异味加 `workflow.test_collaboration_gap`。

| 观察 | 条数 |
| --- | ---: |
| PR | 16 |
| 八条里没有任何 Hit（`zero_hit`） | 9 |
| 八条全部为 NotFound | 1（22777） |
| 八条全部为 Unanalyzed | 1（23509） |
| 至少一条研究规则 Hit | 7 |
| 饱和（`saturated_hit`） | 0 |

7 条有 Hit 的 PR 里，6 条只命中 `code.global_mutable_state`，而且人工判断都是 `false_looking_hit`：类体里的列表或字典，分别是序列化器 `Meta.fields`、测试夹具、权限类属性、迁移的 `dependencies` / `operations`。剩下 1 条是 21901 的 `code.swallowed_exception`，两处 `except ...: pass`，人工判断为 `hit`。

其余研究规则在这 16 条上没有 Finding：`code.bare_exception`、`code.dynamic_execution`、`code.hardcoded_secret`、`code.unmanaged_open`、`code.deep_control_flow`、`workflow.test_collaboration_gap`。这是这一份目的样本上的观察，不是这些规则在 NetBox 里的发生率。

很多 PR 上，`code.swallowed_exception` 和 `code.bare_exception` 的终态是 Unanalyzed，原因 `context_not_established`。解析没有降级。按 009，没有适用的异常处理节点时不记 NotFound。人工把“没有 except 表面”理解为不适用，终态字段不改写成 NotFound。

## 每条 PR

| PR | 研究规则 Hit | 人工判断 | 零命中 | 难度 | 估计分钟 |
| --- | --- | --- | --- | --- | ---: |
| [23175](https://github.com/netbox-community/netbox/pull/23175) | 无 |  | 是 | medium | 8 |
| [22473](https://github.com/netbox-community/netbox/pull/22473) | `code.global_mutable_state` | false_looking_hit | 否 | easy | 6 |
| [22472](https://github.com/netbox-community/netbox/pull/22472) | 无 |  | 是 | easy | 4 |
| [23071](https://github.com/netbox-community/netbox/pull/23071) | `code.global_mutable_state` | false_looking_hit | 否 | medium | 10 |
| [23631](https://github.com/netbox-community/netbox/pull/23631) | 无 |  | 是 | medium | 8 |
| [19846](https://github.com/netbox-community/netbox/pull/19846) | `code.global_mutable_state` | false_looking_hit | 否 | medium | 12 |
| [22777](https://github.com/netbox-community/netbox/pull/22777) | 无（八条皆 NotFound） |  | 是 | hard | 15 |
| [22469](https://github.com/netbox-community/netbox/pull/22469) | `code.global_mutable_state` | false_looking_hit | 否 | medium | 8 |
| [23205](https://github.com/netbox-community/netbox/pull/23205) | 无 |  | 是 | medium | 10 |
| [23276](https://github.com/netbox-community/netbox/pull/23276) | `code.global_mutable_state` | false_looking_hit | 否 | medium | 12 |
| [23429](https://github.com/netbox-community/netbox/pull/23429) | `code.global_mutable_state` 两处 | false_looking_hit | 否 | easy | 5 |
| [21901](https://github.com/netbox-community/netbox/pull/21901) | `code.swallowed_exception` 两处 | hit | 否 | medium | 14 |
| [23509](https://github.com/netbox-community/netbox/pull/23509) | 无（八条皆 Unanalyzed） |  | 是 | easy | 6 |
| [21941](https://github.com/netbox-community/netbox/pull/21941) | 无 |  | 是 | easy | 6 |
| [23606](https://github.com/netbox-community/netbox/pull/23606) | 无 |  | 是 | medium | 7 |
| [23626](https://github.com/netbox-community/netbox/pull/23626) | 无 |  | 是 | easy | 4 |

估计分钟合计 135。单条大约 4 到 15。22777 标成 hard，是因为测试 diff 长，而且注释里的 `@action` 会让字符串检索误报，需要打开补丁确认它不是装饰器变化。

## 值得单独记下的终态

21901 的协作规则是 Unanalyzed，原因 `path_classification_unavailable`。diff 里有 css、scss 和 html。未知路径挡住了 NotFound，也没有协作 Hit。

23509 删除了 `netbox/netbox/monkey.py`，同时改了 `requirements.txt`。八条研究规则全部 Unanalyzed。协作规则同样因为未知路径不能收成 Hit 或 NotFound。历史规则 `data.transaction_structure_changed` 仍有 Hit。零命中旗标在这里只说明八条研究规则没有 Hit。

23276 只有迁移文件。协作规则把 `migrations` 当作 non_production，终态 NotFound。迁移专属的草稿不能指望这条协作规则提供正例。

23205 的主题是 API token，但 `code.hardcoded_secret` 的终态是 NotFound。本屏不摘录字面量。

## 草稿表面

这些判断不是运行时 Hit。

| PR | 卡片 | 判断 | 理由摘要 |
| --- | --- | --- | --- |
| 23175 | `api.drf_public_parameter_added` | unanalyzed | `required=True` 写在 ChoiceField 上，但类基类是 `PrimaryModelSerializer` / `RackBaseSerializer`，不是直接名称 `Serializer` |
| 22473 | `api.drf_public_parameter_added` | not_applicable | 新增字段是 `read_only=True`，没有 `required=True` |
| 19846 | `api.django_url_pattern_changed` | unanalyzed | 人能看见 `router.register('object-types', ...)`，卡片还不能把 route 字符串当结构化字段 |
| 19846 | `api.drf_viewset_action_changed` | not_applicable | 基类文本含 `ReadOnlyModelViewSet`，类体没有标准动作或 `@action` 的增减 |
| 19846 | `auth.drf_permission_decorator_removed` | not_applicable | `permission_classes = [...]` 是类属性，不是装饰器删除 |
| 19846 | `auth.drf_permission_policy_downgrade` | unanalyzed | 列表元素是自定义类，不是 `AllowAny` 或空列表 |
| 21901 | `data.django_raw_sql_execution` | hit | `cursor.execute(...)` 出现在 `core/utils.py` 和 `core/views.py`，最后一段名称在闭集里，且不在迁移中 |
| 21901 | `api.django_url_pattern_changed` | unanalyzed | 新增一条 `path(...)`，route 文本人能看见，检测定义仍缺这个字段 |
| 23276 | `data.django_raw_sql_execution` | not_applicable | 出现的是 `migrations.RunSQL`，不在 execute / executemany / raw / RawSQL 闭集 |
| 23276 | `data.django_destructive_migration` | not_applicable | `RemoveConstraint`，不是 `DeleteModel` 或 `RemoveField` |
| 23429 | `data.django_non_null_constraint_tightened` | not_applicable | `AlterField` 没有 `null=` 文本 |
| 23509 | `config.django_sensitive_settings_changed` | not_applicable | 没有七个闭集名字 |
| 21941 | `config.django_sensitive_settings_changed` | not_applicable | 变化的是 `LOGIN_REQUIRED` 等名字，不在七个闭集里 |
| 21941 | `auth.drf_permission_decorator_removed` | not_applicable | 没有删除 `login_required` 装饰器 |

22777、23631 上的 ViewSet、`@action`、`isnull=False` 字符串来自注释、import 或查询条件，记为不适用。

这一轮没有看到：权限装饰器被删除、`AllowAny` 或空权限列表、`DeleteModel` / `RemoveField`、七个敏感设置名的赋值变化、ViewSet 标准动作或 `@action` 的增减。

## 历史结构规则

五条历史结构规则不进入上面的零命中计数。`auth.permission_structure_changed` 和 `data.transaction_structure_changed` 在测试和模型路径上多次 Hit。21941 上 `config.configuration_structure_changed` 为 Hit，因为文件是 settings；草稿的七个名字并没有对上。这些 Hit 不解释成缺陷，也不作为改权重的依据。

## 可标注性

按这一轮的估计，只看八条研究规则和草稿表面，16 条合计约 135 分钟，多数是 easy 或 medium。难的部分不是异味规则的正例太多，而是两类噪声：`code.global_mutable_state` 在框架列表上的 false-looking Hit，以及历史结构规则在测试文件上的大量 Finding。若正式标注把后者也逐条看完，耗时不能沿用 135 这个数。
