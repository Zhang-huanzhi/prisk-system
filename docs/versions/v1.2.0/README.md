# Prisk-System v1.2.0 阶段基线与里程碑归档

| 项目 | 内容 |
| --- | --- |
| 版本 | v1.2.0 |
| 阶段定位 | 核心规则实现与三态引擎能力闭环 |
| 状态 | Frozen / Milestone Archive |
| 性质声明 | 本归档为内部阶段成果收工归档，非对外发布（Not a Release），不打 Git Tag |

本目录归档 v1.2.0 阶段的全部检测器实现、合同对齐、任务模板规范与阶段索引记录。后续 v1.3 迭代任务在 `docs/tasks/` 中新建，不回写本冻结目录。

---

## 一、 阶段核心产物

1. **残余检测器与合同对齐（Task 020）**：
   - `code.bare_exception`：将 `except Exception` 移出 Finding 集合，仅对裸 `except:` 与直接名称 `BaseException` 告警，实现检测器与卡片合同完全对齐。
   - `code.unmanaged_open`：扩展识别 `Path(...).open` 与 `pathlib.Path(...).open` 属性链式调用，对变量形式 `path.open()` 规范返回 `Unanalyzed (missing_framework_context)`。
   - 已知框架基类映射：引入 `framework_bases.py`，在 Stage04 AST 类节点精确解析 3 个 NetBox 映射基类（`PrimaryModelSerializer`、`NetBoxModelViewSet`、`NetBoxModel`）与 7 个原生基类。
   - 结构提取与细节扩展：支持内部类 `Meta.fields / exclude` 字符串常量列表解析、模型字段与迁移调用的 `default=` / `null=` 关键字提取。
   - 敏感配置方向分类：引入 `sensitive_settings.py`，支持 Django 7 项核心敏感配置变更的方向性判定。
   - 一票抬升（Gatekeeper）机制：引入 `gatekeeper.py`，在评分服务联动读取规则登记册 `gatekeeper=true` 元数据，对破坏性迁移与危险权限降级强制抬升 `risk_level="high"`。

2. **高价值规则三态检测器全量落地（Task 021、022、024）**：
   - 知识库 26 张规则卡片中，所有具备局部 Diff/AST 判定条件的 **24 张卡片全部实现为三态检测器** 并完成构造测试验证，生命周期晋升为 `implemented`：
     - **语言代码异味（`code_smell`，9/9）**：`swallowed_exception`、`bare_exception`、`dynamic_execution`、`hardcoded_secret`、`unmanaged_open`、`deep_control_flow`、`global_mutable_state`、`assert_in_production`、`mutable_default_argument`。
     - **后端契约（`backend_contract`，11/11）**：`drf_public_parameter_added`、`drf_public_parameter_removed`、`django_url_pattern_changed`、`drf_viewset_action_changed`、`drf_permission_decorator_removed`、`drf_permission_policy_downgrade`、`django_raw_sql_execution`、`django_sensitive_settings_changed`、`django_csrf_exempt_added`、`drf_queryset_scope_tighten_bypassed`、`django_signal_receiver_leak`。
     - **变更冲击（`breaking_impact`，4/6）**：`django_destructive_migration`、`django_non_null_constraint_tightened`、`django_field_rename_without_db_column`、`workflow.test_collaboration_gap`。
   - 剩余 2 张延后草稿卡片（`data.django_transaction_boundary_changed` 与 `workflow.large_change_scope`）按结构可行性筛选原设计保持 `draft`。

3. **运行时规则库与三态判定引擎升级**：
   - 运行时规则目录扩展至 **29 条**（5 条历史结构规则 + 24 条知识库规则）；
   - 新增规则默认权重均为 `0`，基线 PR #12 满分 `maximum_points = 10` 与得分 30 分保持完全一致；
   - 严格遵循三态协议（`Hit / NotFound / Unanalyzed`），“上下文不成立时不记 NotFound”，缺口准确记录原因码。

4. **任务文档规范重构（Task 023）**：
   - 建立标准任务模板 [`docs/tasks/_task-template.md`](../../tasks/_task-template.md)，固化标准六节结构；
   - 规范化历史活动任务记录，剔除流程编排套话，强化技术契约与生命周期账本。

---

## 二、 特别说明：Task 019 衔接性质

Task 019（`v1.1 阶段里程碑收工归档与文档对齐精简`）在性质上属于 v1.1.0 的收尾归档任务，但其执行跨越了 v1.1 与 v1.2 的交界。在本次 v1.2.0 归档中，Task 019 连同本阶段的 Task 020–024 一并迁入本目录下的 `tasks/`，确保仓库历史任务编号（001–024）形成完整连续的归档链条。

---

## 三、 归档任务索引（Task 019–024）

| 任务 | 标题 | 分支 | 状态 | 目标版本 |
| :---: | :--- | :--- | :---: | :---: |
| 019 | [v1.1 阶段里程碑收工归档与文档对齐精简](tasks/019-v11-milestone-closure.md) | `docs/019-v11-milestone-closure` | Accepted | v1.1.0 |
| 020 | [残余检测器与合同对齐（v1.2 首切片）](tasks/020-residual-detector-alignment.md) | `feat/020-residual-detector-alignment` | Accepted | v1.2.0 |
| 021 | [高价值草稿检测器批次（v1.2 第二切片）](tasks/021-high-value-draft-detectors.md) | `feat/021-high-value-draft-detectors` | Accepted | v1.2.0 |
| 022 | [第二批高价值草稿检测器（v1.2 第三切片）](tasks/022-second-high-value-draft-detectors.md) | `feat/022-second-high-value-draft-detectors` | Accepted | v1.2.0 |
| 023 | [任务文档规范重构与历史活动任务对齐](tasks/023-task-template.md) | `docs/023-task-template` | Accepted | v1.2.0 |
| 024 | [剩余三张本地 AST 草稿检测器落地（v1.2 第四切片）](tasks/024-remaining-ast-draft-detectors.md) | `feat/024-remaining-ast-draft-detectors` | Accepted | v1.2.0 |

归档任务原件见 [tasks/](tasks/) 子目录。
