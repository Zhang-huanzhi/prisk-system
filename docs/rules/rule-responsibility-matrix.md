# 规则责任矩阵

“文献继承类”表示规则思想有可追溯研究依据，不表示检测器实现免于测试，也不免除本项目的阈值或有效性验证。验证义务按具体规则确定，不与规则阵营一一绑定；文献依据仅覆盖其研究对象、方法和结论。

| 规则阵营 | 典型内容 | 论文责任 | 工程验证责任 |
| --- | --- | --- | --- |
| `code_smell`（文献继承类） | 吞异常、动态执行、硬编码凭据、资源未释放、深层控制流 | 说明问题背景，引用 CWE、OWASP、论文或语言文档 | 用正例、反例和边界样例验证 AST/Diff 检测器 |
| `backend_contract`（框架契约类） | DRF 接口和权限、原生 SQL、敏感配置 | 说明框架约束、规则设计和项目语境 | 使用真实 PR、人工标注和已知案例评估存在性、语义准确性和覆盖性 |
| `breaking_impact`（变更冲击类） | 破坏性 Migration、事务边界、大规模变更、测试协同信号 | 说明具体问题、文献依据和特征组合；过程信号不直接断言外部破坏 | 使用真实 PR、人工标注、阈值敏感性和可用案例评估规则；已有研究不替代本项目验证 |
| 历史演示规则（不纳入登记册） | v1.0.0 五条历史结构规则 | 仅在历史文档中说明其流程演示用途 | 不参与本迭代分类、评分或有效性结论 |

## 验证术语

- **存在性**：规则在真实项目变更中确实能够命中；命中频次不能单独证明有效性；
- **语义准确性**：人工判断 Finding 是否符合规则定义，必要时计算 Precision；
- **已知案例覆盖性**：可靠 Ground Truth 中的案例是否被命中，必要时计算 Recall；
- **工程实现正确性**：构造样例、单元测试和证据可追溯性证明检测器按定义工作。

Precision、Recall、阈值和样本量应在后续验证设计中说明依据，不在登记阶段预填结论。

## 验证现状小结

- **已接入检测器与构造测试（`implemented`，共 24 条）**：
  - 语言异味（9 条）：`code.swallowed_exception`、`code.bare_exception`、`code.dynamic_execution`、`code.unmanaged_open`、`code.deep_control_flow`、`code.hardcoded_secret`、`code.global_mutable_state`、`code.assert_in_production`、`code.mutable_default_argument`。
  - 过程与变更冲击（4 条）：`workflow.test_collaboration_gap`、`data.django_destructive_migration`、`data.django_non_null_constraint_tightened`、`data.django_field_rename_without_db_column`。
  - 框架契约（11 条）：`api.drf_public_parameter_added`、`api.drf_public_parameter_removed`、`api.django_url_pattern_changed`、`api.drf_viewset_action_changed`、`auth.drf_permission_decorator_removed`、`auth.drf_permission_policy_downgrade`、`data.django_raw_sql_execution`、`config.django_sensitive_settings_changed`、`auth.django_csrf_exempt_added`、`auth.drf_queryset_scope_tighten_bypassed`、`data.django_signal_receiver_leak`。
  - *注：上述规则已通过单元测试与构造样例验证工程实现正确性，但尚未开展生产级 Precision / Recall 实证验证。*
- **设计草稿（`draft`，共 5 条）**：
  - 延后草稿卡片（2 条）：`data.django_transaction_boundary_changed`（语句级包含关系）、`workflow.large_change_scope`（项目动态阈值与模块映射）。
  - 暂不建卡排除项（3 条）：`code.dead_code_after_exit`、`auth.drf_object_permission_bypass`、`auth.django_permission_module_changed`。
  - 上述草稿在接入检测器前按设计保持 `draft`，待后续全仓分析或动态工作台阶段演进。
