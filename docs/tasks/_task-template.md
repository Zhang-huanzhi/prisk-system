---
task_id: "NNN"
target_version: "vX.Y.Z"
title: "任务标题"
status: "In Progress"
branch: "<type>/NNN-short-name"
date: "YYYY-MM-DD"
---

# NNN：任务标题

## 1. 背景与目标

说明本任务承接的阶段入口（如 `v1.2-entry.md`）、前序任务遗留项或待解决的具体问题，明确本任务完成后要达成的核心工程或研究目标。

## 2. 范围与边界

### 纳入范围

- 列出本任务实际落地的事项（如具体规则 ID、功能模块、实验协议或文档资产）。

### 不做事项（技术边界）

- 列出与本任务相邻但明确排除的**技术或业务边界**（如留待后续切片的候选规则、不做跨文件数据流追踪、不改变默认评分权重等）。
- 注：仅写技术与产品范围边界，不写 Git 操作或日常流程套话（如“不合并 PR、不打 Tag、不开下一任务”）。

## 3. 技术方案与契约设计

### 核心方案

按任务类型侧重说明关键设计与实现机制：

- **规则与检测器任务**：说明 AST/Diff 比较单位、触发闭集，以及三态引擎（`Hit` / `NotFound` / `Unanalyzed` 及其原因码 `missing_framework_context`、`unsupported_stage04_details`、`context_not_established`）的判定边界；批量落地多条规则时建议使用表格汇总。
- **系统架构与工作台任务**：说明模块职责划分、数据流转链路、状态管理或接口设计。
- **实验评估与文档规范任务**：说明抽样与核对协议、文档重构逻辑或规范对齐原则。

### 契约与兼容性

说明对系统既有稳定契约的影响（纯文档任务可简述“仅涉及文档与规范，不改变运行时代码与既有数据契约”）：

- **阶段 Schema 与接口**：`stage03`–`stage08` 数据格式、CLI 或 HTTP API 载荷是否变更；
- **评分与权重基线**：运行时规则目录总数、新增规则默认权重（如保持 `0`）及默认满分基线（如 `maximum_points=10`）是否保持不变；
- **历史快照兼容**：已保存的 `backend/data/demo/` 快照分数、Finding 与终态可用性（`unavailable`）是否保持兼容。

## 4. 交付物与改动清单

### 改动文件

- **源码实现**：列出新增或修改的后端/前端代码路径及职责说明（无则删去此项）；
- **规则与数据资产**：列出登记册（`backend/data/rules/rule-registry.json`）、规则卡片（`docs/rules/catalog/`）或索引更新（无则删去此项）；
- **测试与文档**：列出新增或更新的测试模块与工程文档路径。

### 规则生命周期变更（可选）

> 若本任务新增运行时规则或变更登记册 `lifecycle` / 默认权重，保留下表；若不涉及规则状态变更，直接删除本小节。

| 规则 ID (`rule_id`) | 所属阵营 (`rule_family`) | 生命周期 (`before → after`) | 默认权重 | 备注（如 Gatekeeper / 支撑范围） |
| :--- | :--- | :---: | :---: | :--- |
| `<domain.rule_name>` | `code_smell` / `backend_contract` / `breaking_impact` | `draft → implemented` | `0` | 补充说明 |

## 5. 验证与验收

### 验收要点

- 列出本任务达成目标的核心验收断言（如构造正例/反例/边界样例覆盖、三态输出准确性、登记册与卡片一致性、历史快照分数不变等）。

### 执行检查

记录本机实际执行的验证命令与结果（未涉及的端注明跳过原因）：

- **后端测试**：`backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend`（记录通过总数及新增测试文件）
- **前端检查**：`npm --prefix frontend run lint` / `npm --prefix frontend run typecheck`
- **格式检查**：`git diff --check`

## 6. 已知限制与残余风险

客观记录本任务完成后仍存在的边界或待演进事项，供后续任务衔接与论文有效性威胁分析（Threats to Validity）参考：

- **静态分析边界**：如跨文件继承、动态属性、别名传递等按设计记为 `Unanalyzed` 或已知漏报的场景；
- **工程管线限制**：如 Stage04 仅保留与 Diff 相交节点带来的上下文启发式限制；
- **后续演进事项**：如构造测试已通过，但真实 PR 实证（`validated`）与权重校准留待后续阶段。
