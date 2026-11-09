# 破坏性与兼容冲击规则

候选规则列于[知识库索引](../../README.md)。结构可行性见 [筛选](../../structural-feasibility.md)。`workflow.test_collaboration_gap` 已按默认路径分类接入 Finding 管道，生命周期为 `implemented`。021 将 `data.django_destructive_migration` 与 `data.django_non_null_constraint_tightened` 升为 `implemented`（权重 0）。其余仍是 `draft`。事务边界和大规模变更在筛选里延后。016 另加一张字段改名草稿，也不实现检测器。

- [`data.django_destructive_migration`](data.django_destructive_migration.md)：`DeleteModel` 与 `RemoveField`。
- [`data.django_non_null_constraint_tightened`](data.django_non_null_constraint_tightened.md)：`null` 收紧。
- [`data.django_transaction_boundary_changed`](data.django_transaction_boundary_changed.md)：当前节点不能配对语句和 `atomic` 块。
- [`workflow.large_change_scope`](workflow.large_change_scope.md)：阈值和模块映射仍未指定。
- [`workflow.test_collaboration_gap`](workflow.test_collaboration_gap.md)：已实现的路径分类复核。不在本任务改写。
- [`data.django_field_rename_without_db_column`](data.django_field_rename_without_db_column.md)：非迁移文件里一对字段改名且没有 `db_column`。022 起 `implemented`。
