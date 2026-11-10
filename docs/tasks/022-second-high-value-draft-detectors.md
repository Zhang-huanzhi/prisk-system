---
task_id: "022"
target_version: "v1.2.0"
title: "第二批高价值草稿检测器（v1.2 第三切片）"
status: "Accepted"
branch: "feat/022-second-high-value-draft-detectors"
date: "2026-11-09"
---

# 022：第二批高价值草稿检测器（v1.2 第三切片）

## 目标

承接 [v1.2 入口](v1.2-entry.md) §2：把第二批高价值草稿规则接入 AST/Diff 检测器与构造测试，并在诚实 Hit/NotFound/Unanalyzed 成立后将登记册 `lifecycle` 升为 `implemented`（仍非 `validated`，默认权重 0）。不宣布 v1.2.0 完成。

## 范围

同一 PR 落地六条：

1. `auth.drf_permission_decorator_removed`
2. `auth.drf_queryset_scope_tighten_bypassed`
3. `data.django_signal_receiver_leak`
4. `data.django_field_rename_without_db_column`
5. `api.drf_public_parameter_added`
6. `api.drf_public_parameter_removed`

## 不做事项

- `api.django_url_pattern_changed`、`code.assert_in_production`、`code.mutable_default_argument`、deferred transaction/large_change、无卡片 exclusions。
- 不宣布 v1.2.0，不建 `docs/versions/v1.2*`，不打 Tag。
- 合并与删分支归 Engineering Lead；不开 023。
- 不扩展 known-framework-bases Hit 映射；不把 gatekeeper 条件扩出卡片。

## 设计

- 新建 `second_batch_detectors.py`，并入 `high_value_detectors` 的 `HIGH_VALUE_RULES` / `collect_high_value_findings`。
- 严格按卡片闭集输出 Finding / Unanalyzed；缺表面、截断、不可读细节用既有原因名。
- 生命周期：六条 `draft` → `implemented`；权重保持 0。

## 实现

- `backend/prisk/domain/second_batch_detectors.py`：六条收集器。
- `backend/prisk/domain/high_value_detectors.py`：合并第二批规则与轨迹。
- `backend/data/rules/rule-registry.json`：六条 lifecycle → `implemented`。
- 卡片与知识库索引徽章同步。
- `auth.drf_permission_decorator_removed`：检测器拿不到完整 head 文件（`structure._map_nodes` 只保留与改动行相交的节点，`evaluate_rules` 只收到 stage04 记录）。head 有未改动行时，删除候选记 Unanalyzed `unsupported_stage04_details`，不记 Hit；同一文件可见 `permission_classes = ...` 时仍记 `missing_framework_context`。所有者不在 head 节点里时，只有它的 base 节点整段被删，才算所有者已删除；否则按函数仍在处理，因为未改动的函数不会进入 stage04。
- `data.django_signal_receiver_leak`：闭集外的具名信号、Celery 任务信号、同一文件 `= Signal(...)` 绑定的接收者、关键字含 `sender`/`weak`/`dispatch_uid` 的 `.connect`，以及 `@receiver` 的闭集外名字，记 Unanalyzed `missing_framework_context`；它与 `unsupported_stage04_details` 同时成立时前者优先。无点号 `connect(...)`、读不出接收者的 `.connect` 和其他无关 `.connect` 不记缺口。
- 测试：`backend/tests/domain/test_high_value_detectors_022.py`（含卡片「022 运行时解释」行与代码常量的逐项比对）；更新 registry/demo 计数断言。

## 验证

- `backend\.venv\Scripts\python.exe -m unittest discover -s backend\tests -t backend`
- 未改前端：跳过 lint/typecheck/build
- `git diff --check`
- 最终 head：`unittest discover` 共 167 个测试通过；`git diff --check` 无错误。

## 生命周期增量

| rule_id | before | after |
| --- | --- | --- |
| auth.drf_permission_decorator_removed | draft | implemented |
| auth.drf_queryset_scope_tighten_bypassed | draft | implemented |
| data.django_signal_receiver_leak | draft | implemented |
| data.django_field_rename_without_db_column | draft | implemented |
| api.drf_public_parameter_added | draft | implemented |
| api.drf_public_parameter_removed | draft | implemented |

## 残余风险

- 构造样例覆盖主路径；真实 PR 实证仍属 validated 义务。
- ViewSet / Serializer 跨文件继承、`@receiver` 位置参数截断、一对一字段配对之外的多字段改名、省略 `required` 的默认表仍 Unanalyzed。
- stage04 只发出与 diff 相交的节点；类头是否预先存在依赖 `start_line` 不在 `changed_lines` 的启发式。
- `auth.drf_permission_decorator_removed`：head 只要有一行未改动就记 Unanalyzed，真实 PR 上多半得不到 Hit；要恢复 Hit，需要把完整 head 源码交给检测器，本任务不加这条管线。
- `data.django_signal_receiver_leak`：从别的模块导入、又不带 `sender`、`weak`、`dispatch_uid` 的自定义信号既不记 Hit 也不记 Unanalyzed，是接受的已知漏报。
