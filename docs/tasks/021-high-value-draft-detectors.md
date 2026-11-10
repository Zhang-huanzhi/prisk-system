---
task_id: "021"
target_version: "v1.2.0"
title: "高价值草稿检测器批次（v1.2 第二切片）"
status: "Accepted"
branch: "feat/021-high-value-draft-detectors"
date: "2026-11-09"
---

# 021：高价值草稿检测器批次（v1.2 第二切片）

## 1. 背景与目标

承接 [`v1.2-entry.md`](v1.2-entry.md) §2，并复用 Task 020 建立的底层结构提取与辅助模块（`framework_bases`、`sensitive_settings`、Stage04 `default=/null=` 字段提取及 `gatekeeper`）。本任务作为 v1.2 阶段的第二切片，旨在将第一批 6 条高价值草稿规则（涵盖 4 条后端框架与安全契约、2 条变更破坏性冲击）落地为具备完整三态输出（`Hit / NotFound / Unanalyzed`）的 AST/Diff 检测器，并在构造测试通过后将其登记册生命周期从 `draft` 晋升为 `implemented`。

## 2. 范围与边界

### 纳入范围

本任务落地以下 6 条检测器并同步更新规则登记册与规则卡片状态：

1. `auth.django_csrf_exempt_added`（`backend_contract`）：新增 CSRF 豁免装饰器检测；
2. `api.drf_viewset_action_changed`（`backend_contract`）：DRF ViewSet 标准动作或 `@action` 路由契约变更检测；
3. `auth.drf_permission_policy_downgrade`（`backend_contract`）：DRF 权限策略降级为 `AllowAny` 或空权限列表检测；
4. `config.django_sensitive_settings_changed`（`backend_contract`）：Django 7 项核心敏感配置向不安全/放宽方向变更检测；
5. `data.django_destructive_migration`（`breaking_impact`）：Django 迁移文件破坏性 Schema 操作（删表/删字段）检测；
6. `data.django_non_null_constraint_tightened`（`breaking_impact`）：模型字段或迁移操作收紧非空约束且缺失 `default=` 检测。

### 不做事项（技术边界）

- 其余 14 条 `draft` 候选规则（如权限装饰器移除、QuerySet 范围绕过、信号泄漏、字段无 `db_column` 重命名、序列化器参数增删等）留待 Task 022 及后续切片处理。
- 不跨文件追踪继承链、路由注册表（`urls.py` / `router.register`）或自定义权限类内部实现。
- 不调整新落地规则的默认评分权重（均保持 `0`，实证校准归属 v1.4 阶段）。

## 3. 技术方案与契约设计

### 核心方案

新增 `backend/prisk/domain/high_value_detectors.py` 并接入 `evaluate_rules` 主链路。6 条规则的局部 AST/Diff 判定契约如下：

| 规则 ID | 比较单位与适用面 | `Hit` 触发闭集 | `NotFound` 条件 | `Unanalyzed` 缺口边界 |
| :--- | :--- | :--- | :--- | :--- |
| `auth.django_csrf_exempt_added` | 函数/类/方法节点上的装饰器（与新增行相交） | 同一所有者在 head 新增 `csrf_exempt` 或 `method_decorator(csrf_exempt...)`（base 无同形态） | 适用装饰器完整扫描且未新增豁免 | 装饰器切片截断记 `unsupported_stage04_details`；闭集外包装形式记 `missing_framework_context` |
| `api.drf_viewset_action_changed` | 继承自原生/映射 ViewSet 基类的类节点 | `list`/`create`/`retrieve`/`update`/`partial_update`/`destroy` 增删，或 `@action` 增删及 `detail`/`methods` 签名变化 | 闭集 ViewSet 动作集合及 `@action` 签名未变 | 基类不在闭集/映射表内记 `missing_framework_context`；装饰器截断记 `unsupported_stage04_details` |
| `auth.drf_permission_policy_downgrade` | 类属性 `permission_classes` 或 `@permission_classes` 装饰器 | head 侧赋值为含 `AllowAny` 或空列表/空元组 `[]`/`()`，且 base 非同形态 | 权限声明已检查且为非空受限权限类（如 `IsAuthenticated`） | 含 `\|`/`&`/`~` 组合运算符、变量别名或切片截断记 `unsupported_stage04_details` / `missing_framework_context` |
| `config.django_sensitive_settings_changed` | 模块级赋值节点（7 个部署检查清单配置名） | 复用 `classify_sensitive_direction` 判定为 `hit`（如 `DEBUG=True`、`ALLOWED_HOSTS=["*"]`、硬编码密钥/密码、关闭安全 Cookie） | 闭集配置项变更为收紧方向（如 `DEBUG=False`、环境变量读取） | 闭集外配置名记 `missing_framework_context`；下标赋值（如 `DATABASES["default"]=...`）或切片截断记 `unsupported_stage04_details` |
| `data.django_destructive_migration` | `migrations` 路径段下的调用节点（与新增行相交） | 调用尾段为 `DeleteModel` 或 `RemoveField` | `migrations` 文件内仅有 `CreateModel`/`AddField`/`AlterField` 等非破坏性调用 | 同路径下出现 `RunSQL`/`RunPython`/`SeparateDatabaseAndState` 或非 `migrations` 路径同名调用记 `missing_framework_context` |
| `data.django_non_null_constraint_tightened` | 模型字段赋值或 `migrations` 下 `AddField`/`AlterField` 调用 | 字段构造调用满足 `null` 收紧（显式 `null=False` 或由 `null=True` 改为省略）且未提供有效 `default=`（`default=None` 视同缺失） | 字段携带有效 `default=` 或保持 `null=True` | 含 `**kwargs` 展开或调用切片截断记 `unsupported_stage04_details`；非字段构造调用记 `missing_framework_context` |

### 契约与兼容性

- **阶段 Schema 与接口**：`stage05.v2`、`stage07.report.v2` 与 `stage08.branch-report.v1` 数据结构不变；运行时规则目录（`RULE_CATALOG`）由 **14 条扩充至 20 条**。
- **评分与权重基线**：新增 6 条规则默认启用，默认权重均设为 `0`，系统默认满分基线维持 `maximum_points=10`；其中 `data.django_destructive_migration` 与 `auth.drf_permission_policy_downgrade` 同时具备 Finding 输出与评分侧 Gatekeeper 一票抬升能力。
- **历史快照兼容**：`backend/data/demo/` 中已保存的演示快照（PR 12）不重算历史 stage05，得分（30 分，3/10）与 Finding 保持不变。

## 4. 交付物与改动清单

### 改动文件

- **源码实现**：
  - `backend/prisk/domain/high_value_detectors.py`（新增）：实现第一批 6 条规则的 AST/Diff 收集器与三态归因逻辑。
  - `backend/prisk/domain/rules.py`：将 `HIGH_VALUE_RULES` 并入 `RULE_CATALOG`、`DEFAULT_CONFIG`、`evaluate_rules` 与 `_build_rule_outcomes`。
  - `backend/prisk/services/demo_service.py`：补充 6 条新规则的中文展示标题与领域分类映射。
- **规则与数据资产**：
  - `backend/data/rules/rule-registry.json`：将 6 条规则的 `lifecycle` 从 `draft` 更新为 `implemented`。
  - `docs/rules/catalog/backend_contract/` 与 `docs/rules/catalog/breaking_impact/` 下对应 6 张规则卡片及目录 `README.md`、[`docs/rules/README.md`](../rules/README.md)：同步生命周期状态徽章。
- **测试与文档**：
  - `backend/tests/domain/test_high_value_detectors_021.py`（新增）：覆盖 6 条规则的正例、反例與 `Unanalyzed` 边界构造测试。
  - `backend/tests/domain/test_rules.py`、`backend/tests/services/test_demo_service.py`、`backend/tests/services/test_rule_registry.py`：同步运行时规则总数（20 条）与登记册状态计数断言（`implemented: 15`, `draft: 14`）。
  - [`docs/tasks/v1.2-entry.md`](v1.2-entry.md)、[`docs/tasks/README.md`](README.md)。

### 规则生命周期变更

| 规则 ID (`rule_id`) | 所属阵营 (`rule_family`) | 生命周期 (`before → after`) | 默认权重 | 备注（Gatekeeper / 支撑范围） |
| :--- | :--- | :---: | :---: | :--- |
| `auth.django_csrf_exempt_added` | `backend_contract` | `draft → implemented` | `0` | 覆盖 `@csrf_exempt` 与 `method_decorator(csrf_exempt)` |
| `api.drf_viewset_action_changed` | `backend_contract` | `draft → implemented` | `0` | 复用 `framework_bases` 识别原生与映射 ViewSet |
| `auth.drf_permission_policy_downgrade` | `backend_contract` | `draft → implemented` | `0` | `gatekeeper=true`（Finding + 评分一票抬升双通路） |
| `config.django_sensitive_settings_changed` | `backend_contract` | `draft → implemented` | `0` | 复用 `sensitive_settings` 7 项配置方向表 |
| `data.django_destructive_migration` | `breaking_impact` | `draft → implemented` | `0` | `gatekeeper=true`（Finding + 评分一票抬升双通路） |
| `data.django_non_null_constraint_tightened` | `breaking_impact` | `draft → implemented` | `0` | 覆盖模型字段与迁移 `AddField` / `AlterField` |

## 5. 验证与验收

### 验收要点

- 6 条规则在构造正例下准确产出 `Hit` Finding，在合规修改下产出 `NotFound`，在跨文件基类、动态表达式或切片截断下诚实产出 `Unanalyzed` 及对应原因码。
- `rule-registry.json` 与 26 张卡片元数据校验全部通过（`implemented` 升至 15 条，`draft` 降至 14 条）。
- 默认满分基线 `maximum_points=10` 及历史 Demo PR 12 输出保持不变。

### 执行检查

- **后端测试**：`backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend`（141 项测试全部通过，新增 `test_high_value_detectors_021.py`）
- **前端检查**：未改动前端代码，跳过 `lint` / `typecheck`
- **格式检查**：`git diff --check`（通过）

## 6. 已知限制与残余风险

- **静态分析边界**：ViewSet 跨文件自定义子类继承、DRF 权限类的位运算组合（`IsAdminUser | ReadOnly`）、`RunSQL` 内部手写 `DROP TABLE` 语句，以及字典下标赋值 `DATABASES["default"]["PASSWORD"] = ...` 均无法由单文件浅层 AST 完备判定，按设计记为 `Unanalyzed`。
- **启发式抬升边界**：Gatekeeper 结构抬升仍对包含 `AllowAny` 的变更节点生效，不区分测试夹具与生产代码路径。
- **后续演进事项**：当前晋升至 `implemented` 仅代表检测器与构造测试闭环；真实 PR 上的命中率与信噪比实证（晋升 `validated`）留待 v1.4 阶段执行。
