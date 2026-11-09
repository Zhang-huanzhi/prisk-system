---
task_id: "021"
target_version: "v1.2.0"
title: "高价值草稿检测器批次（v1.2 第二切片）"
status: "In Progress"
branch: "feat/021-high-value-draft-detectors"
date: "2026-11-09"
---

# 021：高价值草稿检测器批次（v1.2 第二切片）

## 目标

承接 [v1.2 入口](v1.2-entry.md) §2：把第一批高价值草稿规则接入 AST/Diff 检测器与构造测试，并在诚实 Hit/NotFound/Unanalyzed 成立后将登记册 `lifecycle` 升为 `implemented`（仍非 `validated`，默认权重 0）。不宣布 v1.2.0 完成。

## 范围

同一 PR 落地六条：

1. `auth.django_csrf_exempt_added`
2. `api.drf_viewset_action_changed`
3. `data.django_destructive_migration`
4. `auth.drf_permission_policy_downgrade`
5. `config.django_sensitive_settings_changed`
6. `data.django_non_null_constraint_tightened`

## 不做事项

- 其余草稿（参数增删、URL pattern、decorator_removed、queryset bypass、signal leak、field rename、mutable_default、assert_in_production、deferred transaction/large_change、exclusions）。
- 不宣布 v1.2.0，不建 `docs/versions/v1.2*`，不打 Tag。
- 不合并、不 Accepted、不删远程分支、不开 022。
- 不扩大 known-framework-bases Hit 映射；不改 gatekeeper 条件超出卡片。

## 设计

- 新建 `high_value_detectors.py`，按卡片闭集与终态输出 Finding / Unanalyzed gaps；复用 T020 的 `framework_bases`、`sensitive_settings`、结构层 `null`/`default` 字段。
- 破坏性迁移与 AllowAny 既走 Finding 通路，也继续可由评分侧 gatekeeper 抬升。
- 生命周期：六条 `draft` → `implemented`；权重保持 0。

## 实现

- `backend/prisk/domain/high_value_detectors.py`：六条收集器。
- `backend/prisk/domain/rules.py`：接入 `RULE_CATALOG`、`evaluate_rules`、`rule_outcomes`。
- `backend/data/rules/rule-registry.json`：六条 lifecycle → `implemented`。
- 卡片与知识库索引徽章同步。
- 测试：`backend/tests/domain/test_high_value_detectors_021.py`；更新 registry 计数断言。

## 验证

- `backend\.venv\Scripts\python.exe -m unittest discover -s backend\tests -t backend`：141 OK
- 未改前端：跳过 lint/typecheck/build
- `git diff --check`：通过

## 生命周期增量

| rule_id | before | after |
| --- | --- | --- |
| auth.django_csrf_exempt_added | draft | implemented |
| api.drf_viewset_action_changed | draft | implemented |
| data.django_destructive_migration | draft | implemented |
| auth.drf_permission_policy_downgrade | draft | implemented |
| config.django_sensitive_settings_changed | draft | implemented |
| data.django_non_null_constraint_tightened | draft | implemented |

## 残余风险

- 构造样例覆盖主路径；真实 PR 实证仍属 validated 义务。
- ViewSet 跨文件继承、permission 组合运算符、RunSQL 字符串、下标赋值 DATABASES 仍 Unanalyzed。
- gatekeeper 结构启发式仍可能对测试夹具中的 AllowAny 示例抬升。

## 验收说明

任务状态保持 In Progress。PR 开出后由 Engineering Lead 审查；不合并、不 Accepted、不删分支、不开 022、不宣布 v1.2.0。
