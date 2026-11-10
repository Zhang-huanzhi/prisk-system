---
task_id: "022"
target_version: "v1.2.0"
title: "第二批高价值草稿检测器（v1.2 第三切片）"
status: "Accepted"
branch: "feat/022-second-high-value-draft-detectors"
date: "2026-11-09"
---

# 022：第二批高价值草稿检测器（v1.2 第三切片）

## 1. 背景与目标

承接 [`v1.2-entry.md`](v1.2-entry.md) §2 与 Task 021（第一批高价值草稿检测器），继续推进 v1.2 阶段第三切片。本任务旨在将第二批 6 条高价值草稿规则（涵盖 5 条后端框架与安全契约、1 条变更破坏性冲击）落地为具备完整三态输出（`Hit / NotFound / Unanalyzed`）的 AST/Diff 检测器，并在构造测试与卡片常量双向核对通过后，将其登记册生命周期从 `draft` 晋升为 `implemented`。

## 2. 范围与边界

### 纳入范围

本任务落地以下 6 条检测器并同步更新规则登记册与规则卡片状态：

1. `auth.drf_permission_decorator_removed`（`backend_contract`）：视图权限或认证装饰器移除检测；
2. `auth.drf_queryset_scope_tighten_bypassed`（`backend_contract`）：ViewSet `get_queryset` 退化为未过滤 `.objects.all()` 检测；
3. `data.django_signal_receiver_leak`（`backend_contract`）：Django 信号注册缺失 `dispatch_uid` 检测；
4. `api.drf_public_parameter_added`（`backend_contract`）：已有 Serializer 或接口动作新增必填参数/字段检测；
5. `api.drf_public_parameter_removed`（`backend_contract`）：已有 Serializer 或接口动作移除公开参数/字段（含 `Meta.fields/exclude` 成员缩减）检测；
6. `data.django_field_rename_without_db_column`（`breaking_impact`）：模型字段一对一重命名且未显式指定 `db_column` 检测。

### 不做事项（技术边界）

- 剩余 8 条 `draft` 规则（`api.django_url_pattern_changed`、`code.assert_in_production`、`code.mutable_default_argument`、2 条延后规则 `data.django_transaction_boundary_changed` / `workflow.large_change_scope` 及 3 条无卡片排除项）留待后续切片或保持设计冻结。
- 不为 `auth.drf_permission_decorator_removed` 扩展完整未改动 head 源码读取管线（严格在现有 Stage04 相交节点输入下工作）。
- 不调整新落地规则的默认评分权重（均保持 `0`）。

## 3. 技术方案与契约设计

### 核心方案

新增 `backend/prisk/domain/second_batch_detectors.py` 并并入 `high_value_detectors.py` 的统一调度入口。6 条规则的局部 AST/Diff 判定契约如下：

| 规则 ID | 比较单位与适用面 | `Hit` 触发闭集 | `NotFound` 条件 | `Unanalyzed` 缺口边界 |
| :--- | :--- | :--- | :--- | :--- |
| `auth.drf_permission_decorator_removed` | 同一未删除函数/方法/类在 base 与 head 上的装饰器集合（与删除行相交） | base 含闭集装饰器（`permission_classes`/`authentication_classes`/`login_required`/`permission_required`/`user_passes_test`）而 head 消失，且同文件无 `permission_classes = ...` 赋值 | 装饰器仍保留，或整个所有者函数/类本身被一并删除 | 同文件出现 `permission_classes = ...` 记 `missing_framework_context`；head 存在未改动行导致无法排除装饰器下移时记 `unsupported_stage04_details` |
| `auth.drf_queryset_scope_tighten_bypassed` | 原生/映射 ViewSet 子类中的 `get_queryset` 方法（与新增行相交） | `return` 表达式为 `<Model>.objects.all()`（仅允许后接 `select_related`/`prefetch_related`/`order_by`/`distinct`/`using`/`only`/`defer`），且相对 base 为新形态 | `get_queryset` 含 `.filter(...)`/`.exclude(...)` 等过滤链或保持未变 | 基类不在闭集内记 `missing_framework_context`；返回链含未知尾段方法或切片截断记 `unsupported_stage04_details` |
| `data.django_signal_receiver_leak` | 新增行相交的 `.connect(...)` 调用或 `@receiver(...)` 装饰器 | 信号属于 10 个 Django 内置模型/迁移信号闭集，且调用未传入非空 `dispatch_uid` | 闭集信号连接显式携带非空 `dispatch_uid` | 见下方「关键边界设计说明」 |
| `data.django_field_rename_without_db_column` | 非 `migrations` 路径下 `Model` / `NetBoxModel` 子类的字段赋值集合 | 同类内 base 消失字段与 head 新增字段恰好构成 **1 对 1** 替换、字段构造器同名（`*Field`/`ForeignKey` 等），且 head 字段未传 `db_column` | 字段名未变、显式指定 `db_column`，或仅纯新增/纯删除字段 | 同时增删多个字段（多对多无法配对）、构造器类型同时改变或含 `**kwargs` 记 `unsupported_stage04_details` |
| `api.drf_public_parameter_added` | 原生/映射 `Serializer`（非新建类）字段，或已有 `@api_view` / `@action` 函数参数 | 已有 Serializer 新增显式 `required=True` 且无 `default=` 的字段；或已有动作函数新增无默认值的位置/关键字参数 | 新增字段带 `default=` / `required=False` / `read_only=True`，或整个类/函数为全新定义 | 新增字段省略 `required=`（不猜测 DRF 默认值）、基类不在闭集或切片截断记 `unsupported_stage04_details` / `missing_framework_context` |
| `api.drf_public_parameter_removed` | 原生/映射 `Serializer`（非删除类）字段与 `Meta.fields/exclude`，或已有 `@api_view` / `@action` 参数 | base 存在的字段或函数参数在 head 消失；或可读 `Meta.fields` 成员被删 / `Meta.exclude` 新增成员 | 字段、参数及可读 `Meta` 列表未缩减，或整个类/函数被删除 | 基类同时变更、或修改了不可读 `Meta.fields/exclude`（如 `"__all__"`）记 `unsupported_stage04_details` |

### 关键边界设计说明

1. **`auth.drf_permission_decorator_removed` 的 Stage04 局部可见性处理**：
   - `structure._map_nodes` 仅输出与 diff 改动行相交的 AST 节点。当所有者函数头未被修改（仅删除上方装饰器行）时，所有者可能不出现在 head 相交节点中：此时仅当其 base 节点整段行号均被删除才判定为“所有者已删除（`NotFound`）”，否则视为所有者仍存活。
   - 若文件 head 侧存在未与 diff 相交的行，单靠 Stage04 节点无法排除装饰器仅移位至未改动行的可能，此时保守记为 `Unanalyzed (unsupported_stage04_details)`，不冒进报 `Hit`；若同文件可见 `permission_classes = ...` 赋值则优先记 `missing_framework_context`。
2. **`data.django_signal_receiver_leak` 的闭集外信号与优先级区分**：
   - 当遇到 5 个已知请求/数据库信号（如 `request_finished`）、13 个 Celery 任务信号（如 `task_prerun`）、同文件 `= Signal(...)` 自定义信号绑定、携带 `sender`/`weak`/`dispatch_uid` 关键字的未知 `.connect(...)` 或闭集外 `@receiver(...)` 时，明确归入 `Unanalyzed (missing_framework_context)`（与 `unsupported_stage04_details` 并发时前者优先）。
   - 普通无点号 `connect(...)` 或无关对象的 `.connect()` 不计入信号缺口，避免误报数据库连接池或 Socket 调用。

### 契约与兼容性

- **阶段 Schema 与接口**：`stage05.v2`、`stage07.report.v2` 与 `stage08.branch-report.v1` 结构保持不变；运行时规则目录（`RULE_CATALOG`）由 **20 条扩充至 26 条**。
- **评分与权重基线**：新增 6 条规则默认启用，默认权重均设为 `0`，系统默认满分基线维持 `maximum_points=10`。
- **历史快照兼容**：`backend/data/demo/` 中已保存的演示快照（PR 12）得分（30 分，3/10）与 Finding 列表不变。

## 4. 交付物与改动清单

### 改动文件

- **源码实现**：
  - `backend/prisk/domain/second_batch_detectors.py`（新增）：实现第二批 6 条规则的 AST/Diff 收集器与三态归因逻辑。
  - `backend/prisk/domain/high_value_detectors.py`：合并 `SECOND_BATCH_RULES` 与 `collect_second_batch_findings`。
  - `backend/prisk/services/demo_service.py`：补充第二批 6 条规则的中文展示标题与领域分类映射。
- **规则与数据资产**：
  - `backend/data/rules/rule-registry.json`：将 6 条规则的 `lifecycle` 从 `draft` 更新为 `implemented`。
  - `docs/rules/catalog/backend_contract/` 与 `docs/rules/catalog/breaking_impact/` 下对应 6 张规则卡片（补充「022 运行时解释」常量对齐说明）及目录索引、`docs/rules/README.md`、`known-framework-bases.md`、`structural-feasibility.md`、`v1.1-card-readiness.md`。
- **测试与文档**：
  - `backend/tests/domain/test_high_value_detectors_022.py`（新增）：覆盖 6 条规则的正例、反例、`Unanalyzed` 边界，以及卡片「022 运行时解释」与代码常量的双向一致性校验。
  - `backend/tests/domain/test_rules.py`、`backend/tests/services/test_demo_service.py`、`backend/tests/services/test_rule_registry.py`：同步运行时规则总数（26 条）与登记册状态计数断言（`implemented: 21`, `draft: 8`）。
  - [`docs/tasks/v1.2-entry.md`](v1.2-entry.md)、[`docs/tasks/README.md`](README.md)。

### 规则生命周期变更

| 规则 ID (`rule_id`) | 所属阵营 (`rule_family`) | 生命周期 (`before → after`) | 默认权重 | 备注 |
| :--- | :--- | :---: | :---: | :--- |
| `auth.drf_permission_decorator_removed` | `backend_contract` | `draft → implemented` | `0` | 覆盖 5 个权限/认证装饰器闭集 |
| `auth.drf_queryset_scope_tighten_bypassed` | `backend_contract` | `draft → implemented` | `0` | 覆盖 ViewSet `get_queryset` 退化为 `.objects.all()` |
| `data.django_signal_receiver_leak` | `backend_contract` | `draft → implemented` | `0` | 覆盖 10 个内置信号 `.connect` 与 `@receiver` |
| `data.django_field_rename_without_db_column` | `breaking_impact` | `draft → implemented` | `0` | 覆盖 `Model` / `NetBoxModel` 单字段同名构造器替换 |
| `api.drf_public_parameter_added` | `backend_contract` | `draft → implemented` | `0` | 覆盖 Serializer 显式必填字段与动作无默认参数新增 |
| `api.drf_public_parameter_removed` | `backend_contract` | `draft → implemented` | `0` | 覆盖 Serializer 字段、`Meta.fields/exclude` 与动作参数移除 |

## 5. 验证与验收

### 验收要点

- 6 条规则的正例、反例与 `Unanalyzed` 边界构造用例全部通过。
- `data.django_signal_receiver_leak` 卡片中的「022 运行时解释」常量集合与 `second_batch_detectors.py` 中的 `_SIGNAL_NAMES`、`_OUT_OF_SET_SIGNALS`、`_TASK_SIGNALS`、`_SIGNAL_CONNECT_KEYWORDS` 逐项自动比对一致。
- 运行时规则目录达 26 条，登记册 `implemented` 达 21 条、`draft` 余 8 条，默认满分基线仍为 10。

### 执行检查

- **后端测试**：`backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend`（167 项测试全部通过，新增 `test_high_value_detectors_022.py`）
- **前端检查**：未改动前端代码，跳过 `lint` / `typecheck`
- **格式检查**：`git diff --check`（通过）

## 6. 已知限制与残余风险

- **Stage04 相交节点可见性限制**：由于 `evaluate_rules` 仅接收与 diff 行相交的 Stage04 节点，`auth.drf_permission_decorator_removed` 在 head 文件含有任何未改动行时均会因无法排除装饰器移位而保守记为 `Unanalyzed (unsupported_stage04_details)`；若后续需在真实 PR 上提高 `Hit` 召回率，需向规则层透传完整 head AST。
- **静态分析边界**：跨文件继承的 ViewSet/Serializer、省略 `required=` 的 DRF 字段默认值推导、同一 Model 内同时重命名多个字段，以及从外部模块导入且未携带 `sender`/`weak`/`dispatch_uid` 关键字的自定义信号连接，仍受限于单文件局部 AST 能力（记 `Unanalyzed` 或作为已知漏报）。
- **后续演进事项**：新增规则尚未在独立真实 PR 实证集上校准信噪比与权重，生命周期停留于 `implemented`（非 `validated`）。
