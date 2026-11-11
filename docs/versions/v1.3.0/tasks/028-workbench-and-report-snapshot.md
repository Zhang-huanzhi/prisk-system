---
task_id: "028"
target_version: "v1.3.0"
title: "Web 动态交互工作台与可复现审查报告固化"
status: "Accepted"
branch: "feat/028-workbench-and-report-snapshot"
date: "2026-11-10"
---

# 028：Web 动态交互工作台与可复现审查报告固化

## 1. 背景与目标

本任务承接 [v1.3 阶段入口文档](v1.3-entry.md) 与 [推进大纲](../standards/development-roadmap.md) 中关于「v1.3.0 动态交互工作台与报告」的第三项核心目标：**Web 看板与报告导出——报告强制固化本次运行的配置快照（开关/权重/阈值），确保审查结论可复现**。

在前序 Task 026（运行时配置解耦与 5 套场景预设）和 Task 027（快照局部重跑与分析缓存）完成后端基础建设后，系统仍存在以下闭环缺口：
1. **前端规则集滞后于 v1.2**：`frontend/src/components/dashboard.tsx` 的 `ruleLabels` 与 `initialConfig` 仅包含 v1.1 的 14 条规则，导致用户在界面执行重算或恢复默认时，v1.2 新增的 15 条高价值规则被意外截断禁用；
2. **前后端工作台能力未打通**：后端新增的 5 套场景预设（`balanced`、`security_focus`、`framework_upgrade`、`daily_review`、`legacy_baseline`）、规则内部判定阈值（`code.deep_control_flow.max_depth`、`code.hardcoded_secret.min_length`）、三级局部重跑诊断元数据（`snapshot_meta`）以及 Gatekeeper 一票抬升依据尚未在 Web 看板中呈现与交互；
3. **导出报告缺乏配置快照封存**：导出的 Markdown 与 JSON 报告未封存本次运行的完整配置快照（场景预设、SHA-256 配置指纹 `config_digest`、启用/禁用规则名单、29 条规则权重矩阵、等级分段阈值与规则内部判定阈值），无法满足评分可追溯、可复现的硬性要求；
4. **前序文档偏差修正**：清理 `v1.3-entry.md` 与 `026-runtime-config-presets.md` 中关于在 v1.3 落地 `workflow.large_change_scope` 检测器的偏差表述，严格对齐 `structural-feasibility.md` 与 `test_rule_registry.py`（保持该规则 `draft` 延后状态与 29 条运行时规则契约不变）。

## 2. 范围与边界

### 纳入范围

1. **可复现配置快照封存模型（[`backend/prisk/domain/config.py`](../../backend/prisk/domain/config.py)）**：
   - 新增 `build_config_snapshot(config)`，产出 `schema_version = "config.snapshot.v1"` 的自包含配置快照；
   - 计算规范化配置载荷的确定性 SHA-256 指纹 `config_digest`（16 位 hex）；
   - 完整记录 `preset`、`preset_name`、`customized`、`enabled_rules`、`disabled_rules`、`rule_weights`（29 条）、`test_collaboration_enabled`、`test_collaboration_weight`、`thresholds` 与 `rule_thresholds`；
   - 扩展 `list_presets()` 返回完整的 `enabled_rules` 与 `rule_weights` 供前端工作台即时载入。
2. **标准化 Markdown 报告导出引擎（[`backend/prisk/domain/report_export.py`](../../backend/prisk/domain/report_export.py)）**：
   - 实现 `render_markdown_report(report)`，在报告中强制生成 `## 运行配置快照（可复现封存）` 章节，包含配置指纹、预设状态、双重阈值（等级分段阈值 + 规则内部参数阈值）、29 条规则权重与终态明细表，以及可直接反序列化复现的 `json` 配置块；
   - 在 `DemoData.analyze` 与 `analyze_branches` 输出报表中统一注入顶层 `config_snapshot` 字段。
3. **Web 动态交互工作台升级（[`frontend/src/components/dashboard.tsx`](../../frontend/src/components/dashboard.tsx) 与 [`globals.css`](../../frontend/src/app/globals.css)）**：
   - 补齐全部 29 条运行时规则的中文名称、初始配置与结构化证据展示（`operation`、`route`、`action_name`、`setting_name`、`direction`、`permission_policy` 等）；
   - 在「评分配置」页接入 5 套场景预设选择器（Preset Cards）与规则内部判定阈值输入框（`max_depth`、`min_length`）；
   - 在顶栏、概览与评分页接入 `snapshot_meta` 局部重跑层级徽标（Tier 0 / Tier 1 / Tier 2）、配置指纹 `#digest`、本地分支「强制刷新快照」按钮（`refresh: true`）以及 Gatekeeper 一票抬升告警横幅；
   - 在「风险规则」页的 29 条规则目录中增加按三态结果（`Hit` / `NotFound` / `Unanalyzed` / 未启用）与按关注域的组合筛选器；
   - 升级前端 `renderMarkdown` 与后端报告格式严格对齐，导出 Markdown 与 JSON 报告均强制封存运行配置快照。
4. **测试与工程文档对齐**：
   - 新增 [`backend/tests/services/test_report_snapshot.py`](../../backend/tests/services/test_report_snapshot.py)，验证配置指纹确定性与从 Markdown 导出报告提取 JSON 载荷还原完全一致评分的复现闭环；
   - 修正 `v1.3-entry.md` 与 `026-runtime-config-presets.md` 中的边界描述，更新 `docs/tasks/README.md` 与 `docs/architecture.md`。

### 不做事项（技术边界）

- 不修改知识库中 2 张延后草稿卡片（`workflow.large_change_scope` 与 `data.django_transaction_boundary_changed`）的 `draft` 状态，不新增第 30 条运行时规则。
- 不改变默认 `legacy_baseline` 预设下的 10 分满分基线（结构规则 9 分 + 测试协同 1 分）与历史快照分数。
- 不进行面向大规模正式实证集的权重校准（属于 v1.4.0 阶段范围）。

## 3. 技术方案与契约设计

### 核心方案

#### 1. 配置快照封存与可复现验证链路
```text
用户选择 Preset / 调整开关、权重、阈值
  → normalize_audit_config(config) 校验并合并参数
  → build_config_snapshot(config) 生成 config.snapshot.v1 + SHA-256 config_digest
  → 注入 Stage07 (PR) / Stage08 (Branch) 报表顶层 config_snapshot
  → 导出 JSON / Markdown 报告（封存完整参数表与可复现 JSON 载荷）
  → 任意审计者提取 JSON 载荷重新调用 analyze_branches / analyze → 产出完全相同的 config_digest 与评分
```

#### 2. 配置快照 Schema (`config.snapshot.v1`)
| 字段 | 类型 | 说明 |
| :--- | :---: | :--- |
| `schema_version` | `string` | 固定为 `"config.snapshot.v1"` |
| `preset` / `preset_name` | `string` | 基础场景预设标识与中文名称（如 `"security_focus"` / `"安全加固审查"`） |
| `customized` | `boolean` | 是否在基础预设之上进行了手动开关、权重或阈值覆盖 |
| `config_digest` | `string` | 对规范化配置载荷计算的 16 位确定性 SHA-256 指纹 |
| `enabled_rules` / `disabled_rules` | `list[str]` | 本次运行启用与禁用的规则 ID 列表（合集恒为 29 条） |
| `rule_weights` | `dict[str, int]` | 全部 29 条规则的生效启发式权重（`0..5`） |
| `thresholds` | `dict[str, int]` | 复核优先级分段阈值 `{"medium": int, "high": int}` |
| `rule_thresholds` | `dict[str, dict]` | 规则内部判定阈值（`code.deep_control_flow.max_depth`、`code.hardcoded_secret.min_length`） |

### 契约与兼容性

- **阶段 Schema 与接口**：
  - `DemoData.analyze`（`stage07.report.v2`）与 `analyze_branches`（`stage08.branch-report.v1`）新增顶层字典字段 `config_snapshot`；
  - `GET /api/config/presets` 返回的预设项扩充 `enabled_rules`、`rule_weights`、`test_collaboration_weight` 与 `test_collaboration_enabled`；
  - 原有 `score_basis.configuration` 与 `normalize_config(DEFAULT_CONFIG) == DEFAULT_CONFIG` 保持 100% 不变。
- **评分与权重基线**：运行时规则目录维持 29 条，默认兼容基线（`legacy_baseline`）满分仍为 10 分，PR #12 默认得分 30 分保持不变。
- **历史快照兼容**：`backend/data/demo/` 快照数据零改动，历史快照 `rule_outcome_availability` 保持 `"unavailable"`。

## 4. 交付物与改动清单

### 改动文件

- **源码实现**：
  - [`backend/prisk/domain/config.py`](../../backend/prisk/domain/config.py) [MODIFY]：新增 `build_config_snapshot` 与 `CONFIG_SNAPSHOT_SCHEMA_VERSION`，扩展 `list_presets`；
  - [`backend/prisk/domain/report_export.py`](../../backend/prisk/domain/report_export.py) [NEW]：实现标准 Markdown 审查报告渲染器 `render_markdown_report`；
  - [`backend/prisk/services/demo_service.py`](../../backend/prisk/services/demo_service.py) [MODIFY]：在 PR 审查报告中注入 `config_snapshot` 并提供 `write_markdown_report`；
  - [`backend/prisk/services/branch_analysis.py`](../../backend/prisk/services/branch_analysis.py) [MODIFY]：在本地分支审查报告中注入 `config_snapshot`；
  - [`frontend/src/components/dashboard.tsx`](../../frontend/src/components/dashboard.tsx) [MODIFY]：补齐 29 条规则标签与证据展示，接入 5 套预设切换器、规则内部阈值控件、局部重跑徽标、强制刷新按钮、Gatekeeper 提示、规则目录三态筛选，并升级 Markdown/JSON 报告导出固化配置快照；
  - [`frontend/src/app/globals.css`](../../frontend/src/app/globals.css) [MODIFY]：新增预设卡片网格、Gatekeeper 横幅、重跑徽标与规则筛选栏样式。
- **测试与文档**：
  - [`backend/tests/services/test_report_snapshot.py`](../../backend/tests/services/test_report_snapshot.py) [NEW]：配置快照指纹与 Markdown 报告配置还原复现测试；
  - [`docs/tasks/028-workbench-and-report-snapshot.md`](028-workbench-and-report-snapshot.md) [NEW]：本任务记录；
  - [`docs/tasks/v1.3-entry.md`](v1.3-entry.md) [MODIFY]：修正阶段描述并登记 Task 028；
  - [`docs/tasks/026-runtime-config-presets.md`](026-runtime-config-presets.md) [MODIFY]：修正后续任务引用说明；
  - [`docs/tasks/README.md`](README.md) [MODIFY]：更新活动任务表，下一个未使用编号更新为 `029`；
  - [`docs/architecture.md`](../architecture.md) [MODIFY]：同步 v1.3 运行时配置预设、三级局部重跑缓存与报告配置快照固化说明。

## 5. 验证与验收

### 验收要点

1. `build_config_snapshot` 对 5 套预设及自定义覆盖配置生成唯一的 16 位 SHA-256 `config_digest`，完整覆盖 29 条规则开关、权重与内部参数阈值；
2. 从 `render_markdown_report` 导出的 Markdown 报告中正则提取 `json` 配置块并重新传入分析服务，所得 `score`、`risk_level` 与 `config_digest` 与原报告 100% 一致；
3. 前端 `dashboard.tsx` 完整覆盖 29 条规则中文名与初始配置，支持预设切换、内部参数阈值调节、三级局部重跑状态展示、Gatekeeper 横幅展示与可复现报告导出；
4. 全部后端单元测试、前端 ESLint 与 TypeScript 类型检查、Git 格式检查通过。

### 执行检查

- **后端测试**：`backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend`（全部 209 项测试通过，耗时 138.489s，含新增 `test_report_snapshot.py` 5 项测试，0 失败 0 错误）
- **前端检查**：
  - `npm --prefix frontend run lint`（通过，0 警告 0 错误）
  - `npm --prefix frontend run typecheck`（通过，0 类型错误）
- **格式检查**：`git diff --check`（通过，无空白字符或格式异常）

## 6. 已知限制与残余风险

- **预设权重性质**：内置的 5 套场景预设权重与阈值属于面向不同审查焦点的启发式复核优先级配置，不等同于缺陷概率；面向独立正式集的实证统计与高噪规则筛选按推进大纲安排在 v1.4.0 阶段。
- **延后草稿边界**：`workflow.large_change_scope` 与 `data.django_transaction_boundary_changed` 仍按 `structural-feasibility.md` 保持 `draft` 状态，不纳入当前局部 AST 运行时目录。
