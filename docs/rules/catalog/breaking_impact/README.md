# 破坏性与兼容冲击规则

候选规则列于[知识库索引](../../README.md)。结构可行性见 [筛选](../../structural-feasibility.md)。`workflow.test_collaboration_gap` 已按默认路径分类接入 Finding 管道，生命周期为 `implemented`。下面四张仍是 `draft`，没有检测器。事务边界和大规模变更在筛选里延后。

- [`data.django_destructive_migration`](data.django_destructive_migration.md)：`DeleteModel` 与 `RemoveField`。
- [`data.django_non_null_constraint_tightened`](data.django_non_null_constraint_tightened.md)：`null` 收紧。
- [`data.django_transaction_boundary_changed`](data.django_transaction_boundary_changed.md)：当前节点不能配对语句和 `atomic` 块。
- [`workflow.large_change_scope`](workflow.large_change_scope.md)：阈值和模块映射仍未指定。
- [`workflow.test_collaboration_gap`](workflow.test_collaboration_gap.md)：已实现的路径分类复核。不在本任务改写。
