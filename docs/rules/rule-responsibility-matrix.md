# 规则责任矩阵

“文献继承类”表示规则思想有可追溯研究依据，不表示检测器实现免于测试，也不免除本项目的阈值或有效性验证。验证义务按具体规则确定，不与规则阵营一一绑定；文献依据仅覆盖其研究对象、方法和结论。

| 规则阵营 | 典型内容 | 论文责任 | 工程验证责任 |
| --- | --- | --- | --- |
| `code_smell`（文献继承类） | 吞异常、动态执行、硬编码凭据、资源未释放、深层控制流 | 说明问题背景，引用 CWE、OWASP、论文或语言文档 | 用公开可审查的正例、反例和边界微基准样例及大样本触发分布检验 AST/Diff 检测器与参数阈值收敛 |
| `backend_contract`（框架契约类） | DRF 接口和权限、原生 SQL、敏感配置 | 说明框架约束、规则设计和项目语境 | 使用真实 PR 的三态分布、第三方客观代理参照（行内评审批注空间对齐与随机基线对比、社区已知风险案例、非 DRF 退避对照与 DRF 跨仓迁移对照）及公开契约正反微基准评估存在性、契约语义与覆盖边界 |
| `breaking_impact`（变更冲击类） | 破坏性 Migration、事务边界、大规模变更、测试协同信号 | 说明具体问题、文献依据和特征组合；过程信号不直接断言外部破坏 | 使用真实 PR 的可用高危/回滚返工案例、权重与阈值敏感性、Gatekeeper 独立开关消融、第三方评审阻力对照及公开微基准评估规则；已有研究不替代本项目验证 |
| 历史演示规则（不纳入登记册） | v1.0.0 五条历史结构规则 | 仅在历史文档中说明其流程演示用途 | 不参与本迭代分类、单规则有效性结论或新版推荐权重（仅留作系统消融历史基线） |

## 验证术语

- **存在性**：规则在真实项目变更中确实能够命中；命中频次不能单独证明有效性；
- **语义准确性**：优先通过公开可独立检查的微基准正反边界样例及维护者行内评审批注位置对齐（须相对于同体积改动随机行重叠机会基线评估）检验检测逻辑与聚焦对齐，而不依赖单一作者对全量真实 PR 逐条打标作为主要精确率真值；
- **已知案例覆盖性**：来自第三方社区共识印记（安全/回归/破坏性标签及后续 `Revert`/`Fixes` 返工案例）的已知风险样本是否被命中或触发抬升（同时明确外部标签呈非穷尽性）；
- **工程实现正确性**：公开可审的构造微基准、单元测试和 `config.snapshot.v1` / 证据切片可追溯性证明检测器按定义工作。

验证方案框架已固化于 [`ADR-0001`](../adr/0001-v14-validation-strategy.md)（方案 III）；具体指标阈值、抽样窗口与样本量应在后续实证执行任务中确定，不在登记阶段预填结论。

## 验证现状小结

- **已接入检测器与构造测试（`implemented`，共 24 条）**：
  - 语言异味（9 条）：`code.swallowed_exception`、`code.bare_exception`、`code.dynamic_execution`、`code.unmanaged_open`、`code.deep_control_flow`、`code.hardcoded_secret`、`code.global_mutable_state`、`code.assert_in_production`、`code.mutable_default_argument`。
  - 过程与变更冲击（4 条）：`workflow.test_collaboration_gap`、`data.django_destructive_migration`、`data.django_non_null_constraint_tightened`、`data.django_field_rename_without_db_column`。
  - 框架契约（11 条）：`api.drf_public_parameter_added`、`api.drf_public_parameter_removed`、`api.django_url_pattern_changed`、`api.drf_viewset_action_changed`、`auth.drf_permission_decorator_removed`、`auth.drf_permission_policy_downgrade`、`data.django_raw_sql_execution`、`config.django_sensitive_settings_changed`、`auth.django_csrf_exempt_added`、`auth.drf_queryset_scope_tighten_bypassed`、`data.django_signal_receiver_leak`。
  - *注：上述规则已通过单元测试与构造样例验证工程实现正确性，尚未开展正式集规模实证评估。*
- **设计草稿（`draft`，共 5 条）**：
  - 延后草稿卡片（2 条）：`data.django_transaction_boundary_changed`（语句级包含关系）、`workflow.large_change_scope`（项目动态阈值与模块映射）。
  - 暂不建卡排除项（3 条）：`code.dead_code_after_exit`、`auth.drf_object_permission_bypass`、`auth.django_permission_module_changed`。
  - 上述草稿在接入检测器前按设计保持 `draft`，待后续全仓分析或动态工作台阶段演进。
