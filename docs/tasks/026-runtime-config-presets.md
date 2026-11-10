---
task_id: "026"
target_version: "v1.3.0"
title: "运行时配置解耦与场景预设体系"
status: "Accepted"
branch: "feat/026-runtime-config-presets"
date: "2026-11-10"
---

# 026：运行时配置解耦与场景预设体系

## 1. 背景与目标

本任务承接 [v1.3 阶段入口文档](v1.3-entry.md) 与 [推进大纲](../standards/development-roadmap.md) 中关于「v1.3.0 动态交互工作台与报告」的第一阶段基础要求。

在 v1.2 阶段完成 24 条局部 AST 规则的落地后，规则目录扩充至 29 条，但系统在运行时配置层面存在以下结构性局限：
1. **配置耦合分散**：默认配置、权重表与合法性校验逻辑散落在 `backend/prisk/services/demo_service.py`，领域层（`domain`）缺乏独立配置抽象；
2. **启发式权重全 0 过渡态**：为保障既有测试中 10 分分母稳定，22 条规则的默认权重被置为 0，导致评分缺乏针对具体审查场景的区分度；
3. **缺乏场景化预设（Presets）**：无法针对不同审查目标（如安全加固、版本升级、日常合规）一键切换规则侧重点；
4. **规则内部判定参数硬编码**：控制流嵌套深度（4）、敏感凭据字面量最小长度（8）等关键判定阈值硬编码在检测器内，无法在运行时动态定制；
5. **API 与元数据缺失**：后端 HTTP 服务缺乏预设元数据查询端点，调用方无法获知支持的预设列表。

本任务旨在建立独立的配置领域模型（`backend/prisk/domain/config.py`），提供 5 套标准化场景预设、支持规则内部判定参数的动态注入，并扩展后端 HTTP API。

## 2. 范围与边界

### 纳入范围

1. **新建配置领域模型 [`backend/prisk/domain/config.py`](../../backend/prisk/domain/config.py)**：
   - 确立配置 Schema（`config.v1`），实现预设注册表与 `normalize_audit_config` 校验函数；
   - 支持细粒度覆盖（`enabled_rules`、`rule_weights`、`test_collaboration_weight`、`thresholds`、`rule_thresholds`）；
   - 提供预设元数据查询函数 `list_presets()`。
2. **内置 5 套标准化场景预设**：
   - `balanced`（均衡基线 / 默认预设）：29 条规则全覆盖，分层赋予 1~3 启发式分值；
   - `security_focus`（安全加固审查）：加权权限降级（5分）、CSRF（4分）、硬编码密钥（5分，阈值收紧至 6 位）、动态执行（4分）、未管 open（3分）等；
   - `framework_upgrade`（框架升级与迁移）：加权破坏性迁移（5分）、字段改名缺失 db_column（4分）、非空约束收紧（4分）、URL 路由变更（4分）、Serializer 参数增删（4分）等；
   - `daily_review`（日常代码合规）：加权测试协同缺口（5分）、控制流深嵌套（4分，嵌套阈值收紧至 3 层）、静默吞异常（4分）、宽泛捕获（4分）、可变默认参数（4分）；
   - `legacy_baseline`（历史兼容基线）：严格保持 10 分分母（结构规则 9 分 + 测试协同 1 分），保障既有自动化测试与回归快照 100% 兼容。
3. **规则参数下发与动态阈值注入**：
   - 在 `evaluate_rules(..., rule_config)` 中传递 `rule_thresholds`，下发至 `collect_code_smell_findings`；
   - `code.deep_control_flow` 支持动态 `max_depth`（默认 4）；
   - `code.hardcoded_secret` 支持动态 `min_length`（默认 8）。
4. **服务层与适配层对齐**：
   - 重构 `demo_service.py` 与 `branch_analysis.py`，接入新配置模型并向下兼容既有调用；
   - 新增 `GET /api/config/presets` 端点，增强 `POST /api/analyze` 与 `POST /api/branch-analysis` 支持透传 `preset` 与 `rule_thresholds`。
5. **单元测试与文档对齐**：
   - 新增 `backend/tests/domain/test_config.py`，覆盖预设加载、覆盖合并、非法输入拒绝与检测器参数注入；
   - 同步更新活动任务索引与架构说明。

### 不做事项（技术边界）

- 本任务不实现快照三点 Diff 与 AST 语法树的会话级重跑缓存（属于后续 Task 027 范围）。
- 本任务不实现 `workflow.large_change_scope` 的三态检测器逻辑（留待 Task 028 在本任务动态参数地基上落地）。
- 本任务不修改前端 Dashboard 的 UI 交互控件（属于 Task 029 范围）。

## 3. 技术方案与契约设计

### 核心方案

#### 1. 预设注册表与分级权重矩阵
各预设对 29 条规则的推荐权重与阈值分配遵循以下矩阵：

| 规则 ID | 均衡基线 (`balanced`) | 安全加固 (`security_focus`) | 框架升级 (`framework_upgrade`) | 日常合规 (`daily_review`) | 历史基线 (`legacy_baseline`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `api.signature_changed` | 2 | 1 | 3 | 1 | 2 |
| `auth.permission_structure_changed` | 3 | 4 | 1 | 1 | 3 |
| `data.transaction_structure_changed` | 2 | 1 | 3 | 1 | 2 |
| `config.configuration_structure_changed` | 2 | 2 | 2 | 1 | 1 |
| `code.exception_structure_changed` | 2 | 1 | 1 | 2 | 1 |
| `code.swallowed_exception` | 2 | 1 | 1 | 4 | 0 |
| `code.bare_exception` | 2 | 1 | 1 | 4 | 0 |
| `code.dynamic_execution` | 3 | 4 | 1 | 1 | 0 |
| `code.unmanaged_open` | 2 | 3 | 1 | 3 | 0 |
| `code.deep_control_flow` | 2 (depth>4) | 1 (depth>4) | 1 (depth>4) | 4 (depth>3) | 0 (depth>4) |
| `code.hardcoded_secret` | 3 (len>=8) | 5 (len>=6) | 1 (len>=8) | 1 (len>=8) | 0 (len>=8) |
| `code.global_mutable_state` | 1 | 1 | 1 | 2 | 0 |
| `data.django_raw_sql_execution` | 2 | 4 | 1 | 1 | 0 |
| `auth.django_csrf_exempt_added` | 2 | 4 | 1 | 1 | 0 |
| `api.drf_viewset_action_changed` | 2 | 1 | 4 | 1 | 0 |
| `data.django_destructive_migration` | 3 | 1 | 5 | 1 | 0 |
| `auth.drf_permission_policy_downgrade` | 3 | 5 | 1 | 1 | 0 |
| `config.django_sensitive_settings_changed` | 2 | 4 | 1 | 1 | 0 |
| `data.django_non_null_constraint_tightened` | 2 | 1 | 4 | 1 | 0 |
| `auth.drf_permission_decorator_removed` | 3 | 5 | 1 | 1 | 0 |
| `auth.drf_queryset_scope_tighten_bypassed` | 2 | 3 | 1 | 1 | 0 |
| `data.django_signal_receiver_leak` | 1 | 1 | 2 | 1 | 0 |
| `data.django_field_rename_without_db_column` | 2 | 1 | 4 | 1 | 0 |
| `api.drf_public_parameter_added` | 1 | 1 | 3 | 1 | 0 |
| `api.drf_public_parameter_removed` | 2 | 1 | 4 | 1 | 0 |
| `api.django_url_pattern_changed` | 1 | 1 | 4 | 1 | 0 |
| `code.assert_in_production` | 1 | 2 | 1 | 3 | 0 |
| `code.mutable_default_argument` | 1 | 1 | 1 | 4 | 0 |
| `workflow.test_collaboration_gap` | 1 | 1 | 1 | 5 | 1 |

#### 2. 参数动态下发链路
```
normalize_audit_config(supplied)
    ├── 解析 preset，加载预设基准 weights 与 rule_thresholds
    ├── 合并用户的显式 override
    └── 输出强校验后的 AuditConfig 字典
         ├── 传递至 evaluate_rules(stage04_record, config)
         │    └── 下发至 collect_code_smell_findings(..., rule_thresholds)
         │         ├── _control_flow_findings 使用 max_depth
         │         └── _secret_findings 使用 min_length
         └── 传递至 _score(rules, config) 计算总分与风险等级
```

### 契约与兼容性

- **向后兼容性**：
  - `normalize_config` 保持对外签名不变，默认对齐 `legacy_baseline`，既有单元测试与基准断言完全不受影响；
  - `DEFAULT_CONFIG` 常量保持导出，内部引用新模块基准。
- **Schema 扩展**：
  - `score_basis.configuration` 增加 `preset`（字符串，可选）与 `rule_thresholds`（字典，可选）字段；
  - `Evidence` 结构保持向后兼容，`depth_threshold` 动态反映实际生效阈值。
- **HTTP 接口**：
  - 新增 `GET /api/config/presets` 返回预设元数据；
  - `POST /api/analyze` 与 `POST /api/branch-analysis` 透传支持 `preset`。

## 4. 交付物与改动清单

### 改动文件

- **源码实现**：
  - `backend/prisk/domain/config.py` [NEW]：配置模型、5 大预设定义与校验器；
  - `backend/prisk/domain/rules.py` [MODIFY]：`evaluate_rules` 接收并下发 `rule_thresholds`；
  - `backend/prisk/domain/code_smells.py` [MODIFY]：接入动态控制流深度与密钥长度判定；
  - `backend/prisk/services/demo_service.py` [MODIFY]：委托新配置模型，保持向后兼容；
  - `backend/prisk/services/branch_analysis.py` [MODIFY]：分析链路注入完整配置；
  - `backend/prisk/adapters/http_server.py` [MODIFY]：增加 `/api/config/presets` 端点。
- **测试与文档**：
  - `backend/tests/domain/test_config.py` [NEW]：配置规范与预设系统单元测试；
  - `docs/tasks/026-runtime-config-presets.md` [NEW]：本任务规范文档；
  - `docs/tasks/README.md` [MODIFY]：登记 Task 026；
  - `docs/tasks/v1.3-entry.md` [MODIFY]：更新阶段入口索引。

## 5. 验证与验收

### 验收要点

1. 5 套预设均可完整加载，29 条规则与测试协同权重符合设计矩阵；
2. 既有 186 项测试在 `legacy_baseline` 下 100% 通过，无回归；
3. 动态阈值生效：
   - `code.deep_control_flow` 在 `max_depth=2` 时可检出嵌套为 3 的代码；
   - `code.hardcoded_secret` 在 `min_length=5` 时可检出长度为 6 的密钥；
4. `GET /api/config/presets` 成功返回 5 套预设元数据。

### 执行检查

- **后端测试**：`backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend`（通过全部 199 项测试，耗时 139.151s，新增 `test_config.py` 12 项测试与 `test_web_branch_api.py` 预设端点测试，0 失败 0 错误）
- **前端检查**：
  - `npm --prefix frontend run lint`（通过，0 警告 0 错误）
  - `npm --prefix frontend run typecheck`（通过，0 类型错误）
- **格式检查**：`git diff --check`（通过，无空白异常）

## 6. 已知限制与残余风险

- **静态分析边界**：规则阈值解耦仅针对支持纯局部判定或参数化的检测器，不扩展为跨文件过程内/过程间流分析；
- **前端集成时延**：本任务仅提供后端 API，前端看板界面中预设选择器与阈值滑块的视觉呈现留待 Task 029；
- **候补规则落地**：`workflow.large_change_scope` 的实际三态检测器将在 Task 028 中利用本任务建立的动态阈值机制正式接入。
