# 后端契约规则

候选规则列于[知识库索引](../../README.md)。结构可行性见 [筛选](../../structural-feasibility.md)。011 那 20 条里，本目录有八张卡片。其中 `data.django_raw_sql_execution` 已由 013 接入检测器，生命周期是 `implemented`，默认权重 0。命中不是注入已经发生。021 将 viewset/permission/sensitive/csrf 四条升为 `implemented`（权重 0）。其余仍是 `draft`。005 的另外两张仍保留原来的未实现结论；011 补了同一文件边界和 Unanalyzed 条件。016 在这八张之外另加三张 `draft`，没有检测器。

- [`api.drf_public_parameter_added`](api.drf_public_parameter_added.md)：新增的必填公有参数。022 起 `implemented`。
- [`api.drf_public_parameter_removed`](api.drf_public_parameter_removed.md)：删除已有的公有参数或字段。022 起 `implemented`。
- [`api.django_url_pattern_changed`](api.django_url_pattern_changed.md)：同一文件里的 `path`、`re_path` 或 `register`。
- [`api.drf_viewset_action_changed`](api.drf_viewset_action_changed.md)：ViewSet 标准动作或 `@action`。
- [`auth.drf_permission_decorator_removed`](auth.drf_permission_decorator_removed.md)：权限装饰器从视图上消失。022 起 `implemented`。
- [`auth.drf_permission_policy_downgrade`](auth.drf_permission_policy_downgrade.md)：显式改成 `AllowAny` 或空权限列表。
- [`data.django_raw_sql_execution`](data.django_raw_sql_execution.md)：Django 原生 SQL 调用形态。013 已按 011 闭集接入，权重 0。
- [`config.django_sensitive_settings_changed`](config.django_sensitive_settings_changed.md)：部署检查清单中的设置名发生变化。

- [`auth.django_csrf_exempt_added`](auth.django_csrf_exempt_added.md)：新增的 `csrf_exempt`。021 已接入检测器。
- [`auth.drf_queryset_scope_tighten_bypassed`](auth.drf_queryset_scope_tighten_bypassed.md)：闭集 ViewSet 上未过滤的 `objects.all()`。022 起 `implemented`。
- [`data.django_signal_receiver_leak`](data.django_signal_receiver_leak.md)：闭集信号缺少 `dispatch_uid`。022 起 `implemented`。

对象级权限和权限模块仍没有卡片。016 没有实现 `auth.drf_object_permission_bypass`。
