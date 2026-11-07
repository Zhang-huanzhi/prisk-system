# 给 013 的优先级建议

本页只是建议。012 已由用户接受，状态为 Accepted。这里不实现检测器，不改卡片，不改权重，也不启动 013，也不把任何判断写成 Precision、Recall 或有效性。

依据是 [screen.md](screen.md) 里这一份 16 条的目的样本。样本不是随机的，所以“出现过”不能换成“NetBox 里常见”。

## 更适合先做的草稿

**`data.django_raw_sql_execution`。** [21901](https://github.com/netbox-community/netbox/pull/21901) 在非迁移文件 `core/utils.py` 和 `core/views.py` 里新增了 `cursor.execute(...)`。这正是卡片闭集里的最后一段名称，而且现有 call 节点已经有 `callee`。旁边的 `except ...: pass` 被现有的 `code.swallowed_exception` 标成 Hit，说明这条 SQL 表面和一条已实现规则能在同一次 diff 里一起看到。标注大约 14 分钟，主要花在读 SQL 辅助函数和两处 pass，不是因为规则定义对不上。

同一层的 [23276](https://github.com/netbox-community/netbox/pull/23276) 使用 `migrations.RunSQL`。卡片没有把 `RunSQL` 放进闭集。建议保持这个边界。若把 `RunSQL` 并进去，迁移文件会把这条规则冲得很宽，而这一次它并不是设计 Hit。

## 第二条要先做决定，再谈实现

**`api.drf_public_parameter_added`。** [23175](https://github.com/netbox-community/netbox/pull/23175) 能在同一文件看见 `ChoiceField(..., required=True)`，包括把 `required=False` 改成 `required=True`。关键字本身已经是卡片要的文本。

类语句的基类却是 `PrimaryModelSerializer` 和 `RackBaseSerializer`，不是直接名称 `Serializer`。按 011 写明的同一文件表面，这次应记 Unanalyzed，不能记设计 Hit。[22473](https://github.com/netbox-community/netbox/pull/22473) 新增的是 `read_only=True` 字段，同样不是这条规则的触发。

因此它不是“照现卡片实现就会在这批 PR 上有正例”的候选。若 013 想做它，要先决定是否放宽同一文件的基类名字。那个决定本身不是本次试点的授权。

## 这一轮显得稀少

下面这些在 16 条里没有形成可直接实现的正例。稀少是这一份样本的观察，不是证明它们不该存在。

| 卡片 | 这一轮看到的情况 |
| --- | --- |
| `auth.drf_permission_decorator_removed` | 没有闭集装饰器被删除。19846 的 `permission_classes` 是类属性赋值。21941 改的是配置名 `LOGIN_REQUIRED` |
| `auth.drf_permission_policy_downgrade` | 没有 `AllowAny`，也没有空列表。19846 的自定义权限类按卡片应是 Unanalyzed |
| `api.drf_viewset_action_changed` | 19846 的类基类含 `ReadOnlyModelViewSet`，但没有标准动作或 `@action` 的增减。其他 PR 里的 ViewSet 字样在 import、注释或文档 |
| `api.django_url_pattern_changed` | 19846 的 `router.register` 和 21901 的 `path(...)` 人能看见 route 文本。卡片写明位置参数里的 route 还不是结构化字段，所以实现要先补字段，步子比原生 SQL 大 |
| `data.django_destructive_migration` | 23276 是 `RemoveConstraint`，不是 `DeleteModel` 或 `RemoveField` |
| `data.django_non_null_constraint_tightened` | 23429 的 `AlterField` 没有 `null=` 文本 |
| `config.django_sensitive_settings_changed` | 21941 和 23509 改了 settings 文件，历史配置规则可以 Hit，但七个闭集名字没有出现 |

## 不建议为了“有 Hit”先做的已实现规则

`code.global_mutable_state` 是这 16 条里最常出现的研究规则 Finding，但六条 PR 上的判断都是 false-looking Hit：框架或测试要求的列表和字典。它不适合当作 013 要新增的 Django 契约，也不说明应该调高它的权重。本次不改权重。

`workflow.test_collaboration_gap` 没有 Hit。迁移文件和 settings 按现有路径分类不是生产代码；带 css 或 requirements 的 PR 会停在 Unanalyzed。用它来给 Django 契约找正例，这一轮是空的。
