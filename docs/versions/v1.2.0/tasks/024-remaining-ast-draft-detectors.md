---
task_id: "024"
target_version: "v1.2.0"
title: "剩余三张本地 AST 草稿检测器落地（v1.2 第四切片）"
status: "Accepted"
branch: "feat/024-remaining-ast-draft-detectors"
date: "2026-11-10"
---

# 024：剩余三张本地 AST 草稿检测器落地（v1.2 第四切片）

## 1. 背景与目标

在 `v1.2.0` 迭代中，Task 020 完成了残余检测器合同对齐与一票抬升联动，Task 021 与 Task 022 已分两批落地 12 条高价值规则检测器。
截至 Task 023，规则登记册（`backend/data/rules/rule-registry.json`，共 29 条）中仍有 8 条处于 `draft` 状态：
- 3 条无卡片预留项（`code.dead_code_after_exit`、`auth.drf_object_permission_bypass`、`auth.django_permission_module_changed`）；
- 2 条在结构预审与卡片中明确延后的规则（`data.django_transaction_boundary_changed` 受限于语句级事务包含关系缺失；`workflow.large_change_scope` 受限于项目模块映射与阈值未定义）；
- 3 条具备完备闭集触发定义与三态合同的**本地 AST 可行草稿卡片**：
  1. `api.django_url_pattern_changed`（`backend_contract`，路由映射变化）
  2. `code.assert_in_production`（`code_smell`，生产代码中的 assert）
  3. `code.mutable_default_argument`（`code_smell`，函数默认参数中的可变对象）

本任务的目标是：
1. 在 Stage04 `structure.py` 中补充提取这 3 条规则所需的有界 AST 结构细节；
2. 在 Stage05 落地三态检测器（`Hit` / `NotFound` / `Unanalyzed`），并编写覆盖构造正例、反例与未分析边界的单测；
3. 将这 3 条规则的生命周期在登记册与卡片中晋升为 `implemented`，默认权重保持 `0`，基线满分保持 `10` 不变，实现知识库中全部 24 张本地 AST 可行卡片 100% 完成检测器落地；
4. 同步更新 `docs/architecture.md`，使架构文档准确反映当前 29 条运行时规则（5 条旧结构规则 + 24 条已实现研究规则）的最新全貌。

## 2. 范围与边界

### 纳入范围

- **Stage04 AST 结构扩展**（`backend/prisk/domain/structure.py`）：
  - 路由调用参数提取：对 `path`、`re_path`、`register`、`include`、`url` 记录有界参数结构（`route_text`、`view_text`、`name_text`）；
  - `Assert` 语句节点：提取 `visit_Assert`，记录 `assert_statement` 种类及表达式切片，跳出粗粒度 `_structural_changes`；
  - 参数默认值容器种类：在函数及 lambda 上记录 `parameter_defaults` 及其容器分类（`list_display`、`dict_display`、`set_display`、`list_call`、`dict_call`、`set_call`、`non_mutable`）。
- **Stage05 检测器与三态执行**（`backend/prisk/domain/third_batch_detectors.py`）：
  - 落地 `api.django_url_pattern_changed`、`code.assert_in_production`、`code.mutable_default_argument` 检测器；
  - 接入 `high_value_detectors.py` 与 `rules.py`，保持三态 `Hit` / `NotFound` / `Unanalyzed` 契约；
  - 在 `demo_service.py` 的 `DEFAULT_CONFIG` 中为新增 3 条规则配置默认权重 `0`，并补充 `RULE_SCOPES`。
- **规则资产与文档同步**：
  - 更新 `backend/data/rules/rule-registry.json`（`lifecycle: "implemented"`）；
  - 更新 3 张规则说明卡片及 `docs/rules/README.md`、`docs/rules/catalog/backend_contract/README.md`；
  - 更新 `docs/architecture.md`。
- **单元测试套件**：
  - 新增 `backend/tests/domain/test_high_value_detectors_024.py`；
  - 对齐 `test_rules.py`、`test_demo_service.py`、`test_rule_registry.py` 中的规则计数断言（运行时目录 26 → 29，已实现研究规则 21 → 24，草稿 8 → 5）。

### 不做事项（技术边界）

- **2 条延后规则继续保持 `draft`**：`data.django_transaction_boundary_changed` 与 `workflow.large_change_scope` 本任务不强行实现近似启发式；
- **3 条排除项继续无卡片保持 `draft`**：不为 `code.dead_code_after_exit`、`auth.drf_object_permission_bypass`、`auth.django_permission_module_changed` 撰写卡片或实现检测器；
- **不跟随跨文件路由或模块图**：`include()` 明确不跟随进入目标 URLconf，跨文件参数引用不展开；
- **不改变基线满分与历史评分**：3 条新规则默认权重均为 `0`，历史 demo PR #12 的 `30` 分与 `rule_outcome_availability="unavailable"` 保持不变。

## 3. 技术方案与契约设计

### 核心方案

#### 1. Stage04 AST 结构提取扩展

1. **路由调用**（`visit_Call`）：
   - 当调用属性或直接名属于 `{"path", "re_path", "register", "include", "url"}` 时，在 `call.details["routing_call"]` 中记录：
     - `callee_name`: 属性最后一段；
     - `has_unpacking`: 是否存在星号实参展开；
     - `route_status`（`"str"` | `"missing"` | `"unreadable"`）与 `route_text`：第 1 位置实参或 `route=` / `prefix=` 关键字；仅当单个字符串字面量（`_literal_facts` 判定为 `str`）时为 `"str"`；
     - `view_status`（`"expr"` | `"include_call"` | `"missing"` | `"unreadable"`）与 `view_text`：第 2 位置实参或 `view=` / `viewset=` 关键字；若嵌套调用 `include(...)` 则单独标记；规范化 `ast.unparse` 文本以忽略格式换行；
     - `name_status`（`"str"` | `"absent"` | `"unreadable"`）与 `name_text`：`name=`、`basename=` 或对应的第 3/4 位置实参。
2. **`Assert` 语句节点**（`visit_Assert`）：
   - 生成 `kind="assert_statement"` 节点，记录 `details={"statement_kind": "Assert", "test_expression": ...}`；
   - 函数 details 中记录 `"assert_statements_recorded": True`；
   - 在 `_structural_changes` 中将 `assert_statement` 与 `lambda_defaults` 列入跳过名单，防止污染既有粗粒度变更。
3. **参数默认值容器分类**（`_visit_function` 与 `visit_Lambda`）：
   - 函数 details 中记录 `"parameter_defaults"` 列表，每项记录参数名与 `default_kind`（`_container_kind(default)` 或 `"non_mutable"`）；
   - 新增 `visit_Lambda`，生成 `kind="lambda_defaults"` 节点记录其参数默认值。

#### 2. 三态检测器矩阵（`third_batch_detectors.py`）

| 规则 ID | `Hit` 条件 | `NotFound` 条件 | `Unanalyzed` 条件与原因 |
| :--- | :--- | :--- | :--- |
| `api.django_url_pattern_changed` | 同一文件内 `path`/`re_path`/`register` 调用在一侧新增或删除（存在侧文本可读），或两侧配对调用的 `route_text`、`view_text`、`name_text` 任一发生变化且与 diff 行相交 | 至少检查过一条可读的路由调用（如纯换行格式化且各项文本一致），且无框架或细节缺口与解析失败 | - 包含 `include`、`url` 或目标为 `include(...)`：`missing_framework_context`<br>- route/view/name 无法静态提取字面量（如 `gettext_lazy`、变量、星号展开、截断）：`unsupported_stage04_details`<br>- 文件内无相交路由调用：`context_not_established` |
| `code.assert_in_production` | `classify_collaboration_path(path) == "production"` 的 Python 文件中，与新增行相交的 `assert_statement`（`statement_kind == "Assert"`） | - 路径为 `test` 或 `non_production`（`tests/`、`migrations/`、`settings.py`）且解析正常；或<br>- `production` Python 文件已扫描且无相交 `Assert` 语句 | - 路径分类为 `unknown`（如无后缀脚本）：`path_classification_unavailable`<br>- 切片截断，或旧节点无 `Assert` 种类且无法确认语句：`unsupported_stage04_details`<br>- 无 AST/状态通道：`context_not_established` |
| `code.mutable_default_argument` | `function`、`async_function` 或 `lambda_defaults` 上参数的 `default_kind` 属于闭集（`list_display`、`dict_display`、`set_display`、`list_call`、`dict_call`、`set_call`），且行范围与新增行相交 | 函数/lambda 签名已解析，默认值均属于 `non_mutable` 或无默认值，且无闭集默认值与新增行相交 | - 签名切片截断，或旧快照仅有 `has_default=True` 且无法从切片解析种类：`unsupported_stage04_details`<br>- 无相交函数/lambda 节点：`context_not_established` |

### 契约与兼容性

- **规则总数**：`RULE_CATALOG` 规则数量由 26 条增至 29 条。
- **权重基线**：新增 3 条规则默认权重全为 `0`，`maximum_points` 严格保持 10 分（5 条历史结构规则 9 分 + 测试协同 1 分）。
- **一票抬升**：3 条新规则 `gatekeeper` 全为 `false`，不影响一票抬升逻辑。
- **历史快照兼容**：已保存的 `backend/data/demo/stage05-rule-results.jsonl` 原样保持，Demo 分析报告依然返回 30 分（3/10）及 `rule_outcome_availability="unavailable"`。

## 4. 交付物与改动清单

### 改动文件

- **源码实现**：
  - `backend/prisk/domain/structure.py`：扩展路由调用、Assert 语句与 lambda/函数参数默认值提取；
  - `backend/prisk/domain/third_batch_detectors.py`：新增 3 条规则检测器与三态追踪；
  - `backend/prisk/domain/high_value_detectors.py`：汇聚第三批规则及优化文件级 gap 聚合；
  - `backend/prisk/services/demo_service.py`：`DEFAULT_CONFIG` 与 `RULE_SCOPES` 注册新规则。
- **规则与数据资产**：
  - `backend/data/rules/rule-registry.json`：更新 3 条规则 `lifecycle: "implemented"`；
  - `docs/rules/catalog/backend_contract/api.django_url_pattern_changed.md`：更新卡片生命周期与实现说明；
  - `docs/rules/catalog/code_smell/code.assert_in_production.md`：更新卡片生命周期与实现说明；
  - `docs/rules/catalog/code_smell/code.mutable_default_argument.md`：更新卡片生命周期与实现说明；
  - `docs/rules/README.md`、`docs/rules/catalog/backend_contract/README.md`：更新规则知识库索引徽章与说明；
  - `docs/architecture.md`：同步更新运行时目录规则总数（29 条）与分批检测器现状。
- **测试与任务记录**：
  - `backend/tests/domain/test_high_value_detectors_024.py`：新增 3 条规则的构造测试套件；
  - `backend/tests/domain/test_rules.py`、`test_demo_service.py`、`test_rule_registry.py`：对齐规则与生命周期计数；
  - `docs/tasks/024-remaining-ast-draft-detectors.md`、`docs/tasks/README.md`、`docs/tasks/v1.2-entry.md`。

### 规则生命周期变更

| 规则 ID (`rule_id`) | 所属阵营 (`rule_family`) | 生命周期 (`before → after`) | 默认权重 | 备注（如 Gatekeeper / 支撑范围） |
| :--- | :--- | :---: | :---: | :--- |
| `api.django_url_pattern_changed` | `backend_contract` | `draft → implemented` | `0` | `path` / `re_path` / DRF `router.register` 路由映射变更 |
| `code.assert_in_production` | `code_smell` | `draft → implemented` | `0` | 生产路径中的 `assert` 语句 |
| `code.mutable_default_argument` | `code_smell` | `draft → implemented` | `0` | 函数及 lambda 默认参数中的闭集可变容器 |

## 5. 验证与验收

### 验收要点

- 3 条新规则完整覆盖 `Hit`、`NotFound` 与各原因的 `Unanalyzed` 构造样例；
- 生产代码中的 `assert` 命中，而测试目录、迁移目录与 `settings.py` 均不误报；
- 闭集默认值（如 `bucket=[]`、`cache={}`、`items=list()`）命中，而 `None`、元组、函数内局部变量不误报；
- 路由调用 route 变更、view 变更、name 变更分别正确识别，换行格式化不误报，`include()` 正确识别为框架上下文未分析；
- `RULE_CATALOG` 总数 29 条，已实现研究规则 24 条，剩余 5 条草稿规则；基线满分保持 10 分不变。

### 执行检查

- **后端测试**：`backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend`
  - 运行结果：186 个测试全部通过（`Ran 186 tests in 135.526s - OK`），其中 `test_high_value_detectors_024.py` 19 个构造单测全绿。
- **前端代码检查**：`npm --prefix frontend run lint`（通过，0 警告 0 错误）
- **前端类型检查**：`npm --prefix frontend run typecheck`（通过，0 错误）
- **Git 格式检查**：`git diff --check`（通过，无空白异常与冲突残留）

## 6. 已知限制与残余风险

- **跨文件 URLconf 不跟踪**：Django `include("other.urls")` 目标模块内的路由变动不在本文件解析，按卡片规范进入 `missing_framework_context`；
- **动态路由构造不可见**：`urlpatterns += dynamic_patterns()` 等动态表达式无法静态解析具体 route 字符串，进入 `unsupported_stage04_details`；
- **优化模式运行时未知**：`code.assert_in_production` 仅识别语句出现在生产路径上，不证明解释器是否以 `-O` 启动；
- **推导式默认参数未纳入**：`def f(x=[i for i in range(3)])` 暂不在闭集容器显示内，按卡片合同保持 `non_mutable`；
- **实证打靶留待 v1.4**：本任务仅做构造样例与工程实现验证，真实 PR 规模化运行与基线权重校准留待 `v1.4.0`。
