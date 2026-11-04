# 规则知识库

这里记录规则的设计依据、判定边界和后续验证计划。卡片是规则设计与验证记录的主要来源；[JSON 登记册](../../backend/data/rules/rule-registry.json)是结构化候选索引，尚未接入运行时。已登记不代表已实现或已验证；严重度和一票抬升均为待验证的设计属性。

每次新增规则先依据[卡片模板](rule-card-template.md)编写卡片，再同步登记册中 ID、名称、版本、阵营、生命周期和分类标签。登记册中其他内容若与卡片不一致，以卡片为设计依据；禁止覆盖手工维护的登记册。引用只能说明设计依据，工程验证和实证责任见[责任矩阵](rule-responsibility-matrix.md)。

## 规则规划

以下为整理后的 **20 条候选方案**。语言级规则须注明适用语言；两条 PR 过程规则面向跨语言项目，但路径分类、模块映射和阈值依赖项目配置。`registered` 表示卡片已登记，`draft` 表示定义或验证方案仍待完善；均不表示规则已实现或验证。

| 规则阵营                        | 候选规则                                                                                                                                                                                                                                                                                                                                                                                                                                         | 调整说明                                                         |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **`code_smell`**（7 条）       | [`smell.swallowed_exception`](catalog/code_smell/smell.swallowed_exception.md) · `registered`<br>[`smell.bare_exception`](catalog/code_smell/smell.bare_exception.md) · `registered`<br>[`smell.dynamic_execution`](catalog/code_smell/smell.dynamic_execution.md) · `registered`<br>`smell.hardcoded_secret` · `draft`<br>`smell.unmanaged_open` · `draft`<br>`smell.deep_control_flow` · `draft`<br>`smell.global_mutable_state` · `draft` | 测试协同缺失转入变更冲击类；暂不纳入已有编译器或 linter 广泛覆盖的退出后死代码。                 |
| **`backend_contract`**（8 条） | `contract.drf_required_parameter_added` · `draft`<br>`contract.drf_public_parameter_removed` · `draft`<br>`contract.django_url_pattern_changed` · `draft`<br>`contract.drf_viewset_action_changed` · `draft`<br>`contract.drf_permission_decorator_removed` · `draft`<br>`contract.drf_permission_policy_downgrade` · `draft`<br>`contract.django_raw_sql_execution` · `draft`<br>`contract.django_sensitive_settings_changed` · `draft`     | 聚焦 API 与权限契约；强调新增参数为必填参数。对象级权限过滤变动和权限模块变动暂缓，后续再决定是否合并或单独定义。  |
| **`breaking_impact`**（5 条）  | `impact.django_destructive_migration` · `draft`<br>`impact.django_non_null_constraint_tightened` · `draft`<br>`impact.django_transaction_boundary_changed` · `draft`<br>[`impact.large_change_scope`](catalog/breaking_impact/impact.large_change_scope.md) · `draft`<br>[`impact.test_collaboration_gap`](catalog/breaking_impact/impact.test_collaboration_gap.md) · `draft`                                                               | 测试协同缺失和变更规模是 PR 复核信号，不直接认定缺陷或实际外部冲击；破坏性迁移与非空约束收紧的严重度层级待分别论证。 |

### 与现有登记册的关系

上述清单是知识库整理方案，尚未迁移 [JSON 登记册](../../backend/data/rules/rule-registry.json)：登记册仍有原来的 23 条草案和已登记条目。本表中的 `contract.drf_required_parameter_added` 对应现有 `contract.drf_public_parameter_added`；`impact.test_collaboration_gap` 对应现有 `smell.test_collaboration_gap`，其阵营和 ID 迁移均待后续完成。两条过程规则卡片的跨语言范围、标签与判定是待评审的设计，旧登记册相关占位信息尚未同步，不可作为运行配置。

`smell.dead_code_after_exit` 暂不纳入本方案；`contract.drf_object_permission_bypass` 和 `contract.django_permission_module_changed` 暂缓或合并，不代表它们已从登记册删除。其他待完善候选仍未编写规则卡片。
