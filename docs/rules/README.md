# 规则知识库

这里记录规则的设计依据、判定边界和后续验证计划。卡片是规则设计与验证记录的主要来源；[JSON 登记册](../../backend/data/rules/rule-registry.json)是结构化候选索引，尚未接入运行时。登记本身不代表实现或验证；`implemented` 只表示检测器与构造测试已经接入，不表示实证验证。严重度和一票抬升均为待验证的设计属性。

每次新增规则先依据[卡片模板](rule-card-template.md)编写卡片，再同步登记册中 ID、名称、版本、阵营、生命周期和分类标签。登记册中其他内容若与卡片不一致，以卡片为设计依据；禁止覆盖手工维护的登记册。引用只能说明设计依据，工程验证和实证责任见[责任矩阵](rule-responsibility-matrix.md)。

## 规则规划

以下为整理后的 **20 条候选方案**。规则 ID 使用关注域前缀，`rule_family` 仍作为登记属性。语言级规则须注明适用语言；两条 PR 过程规则面向跨语言项目，但路径分类、模块映射和阈值依赖项目配置。`draft` 表示定义或验证方案仍待完善；`registered` 表示卡片已登记但检测器未接入；`implemented` 表示检测器已按卡片接入，并用构造样例做了工程测试。这些状态都不表示实证验证完成，也不表示命中即缺陷。

| 规则阵营                        | 候选规则                                                                                                                                                                                                                                                                                                                                                                                                                                         | 调整说明                                                         |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **`code_smell`**（7 条）       | [`code.swallowed_exception`](catalog/code_smell/code.swallowed_exception.md) · `implemented`<br>[`code.bare_exception`](catalog/code_smell/code.bare_exception.md) · `implemented`<br>[`code.dynamic_execution`](catalog/code_smell/code.dynamic_execution.md) · `implemented`<br>[`code.hardcoded_secret`](catalog/code_smell/code.hardcoded_secret.md) · `registered`<br>[`code.unmanaged_open`](catalog/code_smell/code.unmanaged_open.md) · `implemented`<br>[`code.deep_control_flow`](catalog/code_smell/code.deep_control_flow.md) · `implemented`<br>[`code.global_mutable_state`](catalog/code_smell/code.global_mutable_state.md) · `registered` | 测试协同缺失转入变更冲击类；暂不纳入已有编译器或 linter 广泛覆盖的退出后死代码。已实现规则仍不是实证验证。005 只为 `code.unmanaged_open` 和 `code.deep_control_flow` 接入检测器。 |
| **`backend_contract`**（8 条） | [`api.drf_public_parameter_added`](catalog/backend_contract/api.drf_public_parameter_added.md) · `draft`<br>`api.drf_public_parameter_removed` · `draft`<br>`api.django_url_pattern_changed` · `draft`<br>`api.drf_viewset_action_changed` · `draft`<br>[`auth.drf_permission_decorator_removed`](catalog/backend_contract/auth.drf_permission_decorator_removed.md) · `draft`<br>`auth.drf_permission_policy_downgrade` · `draft`<br>[`data.django_raw_sql_execution`](catalog/backend_contract/data.django_raw_sql_execution.md) · `draft`<br>`config.django_sensitive_settings_changed` · `draft`     | 聚焦 API 与权限契约；强调新增参数为必填参数。005 的三张设计卡片仍是 `draft`：公有路由、装饰器名单和迁移路径还没有冻结。对象级权限过滤变动和权限模块变动暂缓。  |
| **`breaking_impact`**（5 条）  | `data.django_destructive_migration` · `draft`<br>`data.django_non_null_constraint_tightened` · `draft`<br>`data.django_transaction_boundary_changed` · `draft`<br>[`workflow.large_change_scope`](catalog/breaking_impact/workflow.large_change_scope.md) · `draft`<br>[`workflow.test_collaboration_gap`](catalog/breaking_impact/workflow.test_collaboration_gap.md) · `draft`                                                               | 测试协同缺失和变更规模是 PR 复核信号，不直接认定缺陷或实际外部冲击；破坏性迁移与非空约束收紧的严重度层级待分别论证。 |

### 与现有登记册的关系

上述清单是知识库整理方案；[JSON 登记册](../../backend/data/rules/rule-registry.json)已完成关注域 ID 迁移。草稿规则的 ID 仍可在入册或实现前调整，已登记规则的改名需要在迭代中记录迁移关系。两条过程规则卡片的跨语言范围、标签与判定仍待后续验证，不可作为运行配置。

`code.dead_code_after_exit` 暂不纳入本方案；`auth.drf_object_permission_bypass` 和 `auth.django_permission_module_changed` 暂缓或合并，不代表它们已从登记册删除。其他待完善候选仍未编写规则卡片。
