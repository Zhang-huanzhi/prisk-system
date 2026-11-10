# 规则知识库

这里记录规则的设计依据、判定边界和后续验证计划。卡片是规则设计与验证记录的主要来源；[JSON 登记册](../../backend/data/rules/rule-registry.json)是结构化候选索引，尚未接入运行时。登记本身不代表实现或验证；`implemented` 只表示检测器与构造测试已经接入，不表示实证验证。严重度和一票抬升均为待验证的设计属性。

每次新增规则先依据[卡片模板](rule-card-template.md)编写卡片，再同步登记册中 ID、名称、版本、阵营、生命周期和分类标签。登记册中其他内容若与卡片不一致，以卡片为设计依据；禁止覆盖手工维护的登记册。引用只能说明设计依据，工程验证和实证责任见[责任矩阵](rule-responsibility-matrix.md)。

研究入口和卡片框架见 [索引](index.md)。20 条候选的结构可行性见 [结构可行性筛选](structural-feasibility.md)。那是设计复核，不是测试结果。卡片、本状态看板和 JSON 登记册都是研究记录。它们不是运行时规则目录，也不是代码登记册。运行时目录现为 29 条（5 条历史结构规则、7 条代码异味、1 条测试协同、1 条 Django 原生 SQL，以及 021、022、024 阶段接入的 15 条高价值检测器）。011 整理的研究候选仍是 20 条，不与运行时目录混计。016 在这 20 条之外新增 6 条草稿候选，不重写这 20 条，也不接入运行时。

## 规则规划

以下为整理后的 **20 条候选方案**。规则 ID 使用关注域前缀，`rule_family` 仍作为登记属性。语言级规则须注明适用语言。`workflow.test_collaboration_gap` 使用源码中的默认路径分类；`workflow.large_change_scope` 仍依赖尚未实现的模块映射和阈值。`draft` 表示定义或验证方案仍待完善；`registered` 表示卡片已登记但检测器未接入；`implemented` 表示检测器已按卡片接入，并用构造样例做了工程测试。这些状态都不表示实证验证完成，也不表示命中即缺陷。

| 规则阵营                        | 候选规则                                                                                                                                                                                                                                                                                                                                                                                                                                         | 调整说明                                                         |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **`code_smell`**（7 条）       | [`code.swallowed_exception`](catalog/code_smell/code.swallowed_exception.md) · `implemented`<br>[`code.bare_exception`](catalog/code_smell/code.bare_exception.md) · `implemented`<br>[`code.dynamic_execution`](catalog/code_smell/code.dynamic_execution.md) · `implemented`<br>[`code.hardcoded_secret`](catalog/code_smell/code.hardcoded_secret.md) · `implemented`<br>[`code.unmanaged_open`](catalog/code_smell/code.unmanaged_open.md) · `implemented`<br>[`code.deep_control_flow`](catalog/code_smell/code.deep_control_flow.md) · `implemented`<br>[`code.global_mutable_state`](catalog/code_smell/code.global_mutable_state.md) · `implemented` | 测试协同缺失转入变更冲击类；暂不纳入已有编译器或 linter 广泛覆盖的退出后死代码。已实现规则仍不是实证验证。006 为 `code.hardcoded_secret` 和 `code.global_mutable_state` 接入检测器；命中仍不是秘密、漏洞或串扰已经发生。 |
| **`backend_contract`**（8 条） | [`api.drf_public_parameter_added`](catalog/backend_contract/api.drf_public_parameter_added.md) · `implemented`<br>[`api.drf_public_parameter_removed`](catalog/backend_contract/api.drf_public_parameter_removed.md) · `implemented`<br>[`api.django_url_pattern_changed`](catalog/backend_contract/api.django_url_pattern_changed.md) · `implemented`<br>[`api.drf_viewset_action_changed`](catalog/backend_contract/api.drf_viewset_action_changed.md) · `implemented`<br>[`auth.drf_permission_decorator_removed`](catalog/backend_contract/auth.drf_permission_decorator_removed.md) · `implemented`<br>[`auth.drf_permission_policy_downgrade`](catalog/backend_contract/auth.drf_permission_policy_downgrade.md) · `implemented`<br>[`data.django_raw_sql_execution`](catalog/backend_contract/data.django_raw_sql_execution.md) · `implemented`<br>[`config.django_sensitive_settings_changed`](catalog/backend_contract/config.django_sensitive_settings_changed.md) · `implemented`     | 八条都有设计卡片。013 将 `data.django_raw_sql_execution` 按 011 闭集接入检测器，生命周期是 `implemented`，默认权重 0。命中不是注入已经发生，也没有实证有效性。021 将 `api.drf_viewset_action_changed`、`auth.drf_permission_policy_downgrade`、`config.django_sensitive_settings_changed` 升为 `implemented`；022 将 `api.drf_public_parameter_added`、`api.drf_public_parameter_removed`、`auth.drf_permission_decorator_removed` 升为 `implemented`。它们默认权重都是 0，都不是 `validated`。024 将 `api.django_url_pattern_changed` 升为 `implemented`。本行八条均已接入检测器。011 把适用面收在同一文件，缺框架表面时设计预期是 Unanalyzed。对象级权限过滤变动和权限模块变动仍不在这 8 条里。 |
| **`breaking_impact`**（5 条）  | [`data.django_destructive_migration`](catalog/breaking_impact/data.django_destructive_migration.md) · `implemented`<br>[`data.django_non_null_constraint_tightened`](catalog/breaking_impact/data.django_non_null_constraint_tightened.md) · `implemented`<br>[`data.django_transaction_boundary_changed`](catalog/breaking_impact/data.django_transaction_boundary_changed.md) · `draft`<br>[`workflow.large_change_scope`](catalog/breaking_impact/workflow.large_change_scope.md) · `draft`<br>[`workflow.test_collaboration_gap`](catalog/breaking_impact/workflow.test_collaboration_gap.md) · `implemented`                                                               | 五条都有卡片。测试协同、破坏性迁移与非空约束收紧已接入检测器，生命周期为 `implemented`（默认权重 0）。事务边界和大规模变更在结构筛选里延后，生命周期保持 `draft`，不表示已经做了实验。 |

### 与现有登记册的关系

上述清单是知识库整理方案；[JSON 登记册](../../backend/data/rules/rule-registry.json)已完成关注域 ID 迁移。草稿规则的 ID 仍可在入册或实现前调整，已登记规则的改名需要在迭代中记录迁移关系。JSON 登记册仍不是运行时配置。`workflow.test_collaboration_gap` 的检测器在版本化源码中，不从登记册加载。`workflow.large_change_scope` 仍是 `draft`。015 按工程负责人的临时裁决，把这条的卡片和登记册写成严重度 `High`、风险性质 `pr_intrinsic`。后续算法阶段可以修订，这不是终局。015 不实现检测器，也不把 v1.1.0 写成已经完成。017 不改这条的严重度或风险性质。

`code.dead_code_after_exit` 暂不纳入本方案；`auth.drf_object_permission_bypass` 和 `auth.django_permission_module_changed` 暂缓，不代表它们已从登记册删除，011 也不给它们写卡片。20 条候选现在各有一张卡片。`draft` 仍表示定义或验证还没有接到检测器，不是实证结论。

014 的 [就绪核对](v1.1-card-readiness.md) 只引用登记册 `lifecycle`。它没有把任何 `draft` 改成 `registered` 或 `implemented`，也没有 `validated`。任务 Accepted 不表示 v1.1.0 已经完成。016 不改写上面这张 20 条表，也不把 014 的核对范围改成登记册里的全部条目。

## 016 新增的草稿

下面 6 条是 011 那 20 条之外的新候选。它们不替换 `code.dead_code_after_exit`、`auth.drf_object_permission_bypass`、`auth.django_permission_module_changed`。这 3 条仍然没有卡片。016 登记时，6 条的生命周期都是 `draft`，没有检测器。之后 021 将 `auth.django_csrf_exempt_added` 升为 `implemented`；022 将 `auth.drf_queryset_scope_tighten_bypassed`、`data.django_signal_receiver_leak`、`data.django_field_rename_without_db_column` 升为 `implemented`，默认权重 0，不是 `validated`。024 将 `code.mutable_default_argument` 与 `code.assert_in_production` 升为 `implemented`，默认权重 0，不是 `validated`。登记册没有权重字段；概念上的默认权重是 0，评分不因此变化。严重度和风险性质是临时判断，不是终局。文档写完不把它们改成 `registered`。

| 规则 | 阵营 |
| --- | --- |
| [`code.mutable_default_argument`](catalog/code_smell/code.mutable_default_argument.md) · `implemented` | `code_smell`。补 `code.global_mutable_state` 明确留给以后的函数默认参数。 |
| [`code.assert_in_production`](catalog/code_smell/code.assert_in_production.md) · `implemented` | `code_smell`。生产路径上的 `assert` 语句。路径类沿用已有的 `default_source_and_test_directories`。 |
| [`auth.django_csrf_exempt_added`](catalog/backend_contract/auth.django_csrf_exempt_added.md) · `implemented` | `backend_contract`。新增 `@csrf_exempt` 或 `method_decorator(csrf_exempt)`。 |
| [`auth.drf_queryset_scope_tighten_bypassed`](catalog/backend_contract/auth.drf_queryset_scope_tighten_bypassed.md) · `implemented` | `backend_contract`。闭集 ViewSet 的 `get_queryset` 改为未过滤的 `objects.all()`。`NetBoxModelViewSet` 按 [已知框架基类映射](known-framework-bases.md) 视为 `ModelViewSet`。未列入的项目基类不在 Hit 里。`restrict_queryset` 仍不是 Hit。 |
| [`data.django_signal_receiver_leak`](catalog/backend_contract/data.django_signal_receiver_leak.md) · `implemented` | `backend_contract`。闭集信号的 `connect` / `@receiver` 没有 `dispatch_uid`。ID 里的 leak 指重复登记。 |
| [`data.django_field_rename_without_db_column`](catalog/breaking_impact/data.django_field_rename_without_db_column.md) · `implemented` | `breaking_impact`。非迁移文件里一对字段改名且没有 `db_column`。不运行 `makemigrations`。 |

结构可行性仍把 011 的 20 条记成局部 Diff/AST 8、有界框架上下文 10、延后 2。016 的六条写在筛选页末尾，不重计这三类。
