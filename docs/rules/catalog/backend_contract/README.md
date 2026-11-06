# 后端契约规则

候选规则列于[知识库索引](../../README.md)。结构可行性见 [筛选](../../structural-feasibility.md)。本目录八张卡片都是 `draft`，没有检测器。005 的三张仍保留原来的未实现结论；011 补了同一文件边界和 Unanalyzed 条件。

- [`api.drf_public_parameter_added`](api.drf_public_parameter_added.md)：新增的必填公有参数。
- [`api.drf_public_parameter_removed`](api.drf_public_parameter_removed.md)：删除已有的公有参数或字段。
- [`api.django_url_pattern_changed`](api.django_url_pattern_changed.md)：同一文件里的 `path`、`re_path` 或 `register`。
- [`api.drf_viewset_action_changed`](api.drf_viewset_action_changed.md)：ViewSet 标准动作或 `@action`。
- [`auth.drf_permission_decorator_removed`](auth.drf_permission_decorator_removed.md)：权限装饰器从视图上消失。
- [`auth.drf_permission_policy_downgrade`](auth.drf_permission_policy_downgrade.md)：显式改成 `AllowAny` 或空权限列表。
- [`data.django_raw_sql_execution`](data.django_raw_sql_execution.md)：Django 原生 SQL 调用形态。
- [`config.django_sensitive_settings_changed`](config.django_sensitive_settings_changed.md)：部署检查清单中的设置名发生变化。

对象级权限和权限模块仍没有卡片。
