---
task_id: "019"
target_version: "v1.1.0"
title: "v1.1 阶段里程碑收工归档与文档对齐精简"
status: "Accepted"
branch: "docs/019-v11-milestone-closure"
date: "2026-11-09"
---

# 019：v1.1 阶段里程碑收工归档与文档对齐精简

## 1. 背景与目标

在已合并的 Task 018（`766cacc`，v1.1 卡片门槛决策）之上，完成 v1.1.0 规则知识库里程碑的阶段收口与资产归档，并建立面向下一阶段（v1.2 核心规则实现与三态引擎）的活动工作区入口。

本任务定位为内部阶段里程碑收工（Stage Closure），旨在冻结 v1.1.0 阶段的研究与工程文档基线、固化规则卡片模板标准结构、解决跨平台测试换行符哈希差异，并清理文档中的历史陈旧陈述。

## 2. 范围与边界

### 纳入范围

1. **规则卡片母版升级**：更新 [`docs/rules/rule-card-template.md`](../rules/rule-card-template.md)，固化 26 张卡片实际采用的「第 4 节：检测定义」13 项标准化子节结构，并在有效性计划中补齐 `implementation_only` 验证义务枚举。
2. **跨平台测试修复**：修复 `backend/tests/domain/test_rule_outcomes.py` 中因 Windows CRLF 换行符导致的 `docs/blueprint.md` SHA-256 哈希断言失败。
3. **v1.1.0 阶段归档与 v1.2 入口建立**：建立 [`docs/versions/v1.1.0/`](../versions/v1.1.0/README.md) 冻结归档目录，迁入 Task 001–018 全部任务记录；同步创建 [`docs/tasks/v1.2-entry.md`](v1.2-entry.md)。
4. **文档对齐与协作规范维护**：清理 `docs/README.md`、`docs/rules/rule-responsibility-matrix.md`、`docs/versions/README.md` 中的过时状态与计数笔误，并修订根目录 `AGENTS.md`。

### 不做事项（技术边界）

- 不改动 `backend/prisk/` 下的运行时检测器、评分逻辑或 API 实现。
- 不改动 `docs/rules/catalog/` 下 26 张规则卡片的既有判定闭集与正文内容。
- 不修改 [`docs/blueprint.md`](../blueprint.md) 规格原文。

## 3. 技术方案与契约设计

### 核心方案

- **卡片模板与 Schema 对齐**：将卡片第 4 节统一为「比较单位、适用性、闭集、触发条件、触发特征、不触发条件、输入、Finding、证据位置、上下文切片、影响类型、规则终态、构造样例」标准子节，确保卡片母版与 [`rule-metadata.schema.json`](../schemas/rule-metadata.schema.json) 的 `validation_obligation` 枚举完全一致。
- **蓝图哈希跨平台归一化**：在 `test_rule_outcomes.py` 读取 `docs/blueprint.md` 时，先将 `\r\n` 归一化为 `\n` 再计算 SHA-256，消除 Git `core.autocrlf` 在 Windows 与 Linux/macOS 下的字节差异，同时保持蓝图内容零篡改。
- **阶段归档隔离**：按照 [`document-structure.md`](../standards/document-structure.md) 的冻结文本原则，将 v1.1.0 阶段完成的 18 条任务整体迁入 `docs/versions/v1.1.0/tasks/`，活动工作区 `docs/tasks/` 仅保留本收工任务及后续 v1.2 任务。

### 契约与兼容性

- **阶段 Schema 与接口**：不涉及 `stage03`–`stage08` Schema、CLI 或 HTTP API 变更。
- **评分与权重基线**：运行时规则目录维持 14 条（含先行合入的 Task 013 `data.django_raw_sql_execution`），默认满分基线 `maximum_points=10` 不变。
- **历史快照兼容**：`backend/data/demo/` 与 `docs/versions/v1.0.0/` 冻结资产保持原样。

## 4. 交付物与改动清单

### 改动文件

- **规则与标准规范**：
  - [`docs/rules/rule-card-template.md`](../rules/rule-card-template.md)：升级第 4 节检测定义子节与第 7 节验证义务枚举。
  - [`docs/rules/rule-responsibility-matrix.md`](../rules/rule-responsibility-matrix.md)、[`docs/rules/index.md`](../rules/index.md)：修正历史结构规则计数（5 条）与归档链接。
  - [`docs/standards/document-structure.md`](../standards/document-structure.md)、[`docs/standards/branching-and-tasks.md`](../standards/branching-and-tasks.md)：同步 v1.1.0 归档状态与任务编号基线。
  - [`AGENTS.md`](../../AGENTS.md)、[`docs/README.md`](../README.md)、[`docs/architecture.md`](../architecture.md)：更新仓库文档地图、开发工作流与阶段状态。
- **阶段归档与任务入口**：
  - 新增 [`docs/versions/v1.1.0/README.md`](../versions/v1.1.0/README.md)、[`00-baseline-summary.md`](../versions/v1.1.0/00-baseline-summary.md)、[`v1.1-entry.md`](../versions/v1.1.0/v1.1-entry.md)，并迁入 `docs/versions/v1.1.0/tasks/001..018`。
  - 新增 [`docs/tasks/v1.2-entry.md`](v1.2-entry.md)，更新 [`docs/tasks/README.md`](README.md) 与 [`docs/versions/README.md`](../versions/README.md)。
- **测试套件**：
  - `backend/tests/domain/test_rule_outcomes.py`：归一化 `docs/blueprint.md` 换行符后计算 SHA-256。

## 5. 验证与验收

### 验收要点

- `docs/blueprint.md` 哈希校验在 Windows CRLF 检出环境下稳定通过。
- 26 张规则卡片与更新后的卡片母版、`rule-metadata.schema.json` 及 `rule-registry.json` 保持 100% 字段与枚举对齐。
- `docs/versions/v1.1.0/` 归档目录链接与 `docs/tasks/` 活动入口链接全部可解析。

### 执行检查

- **后端测试**：`backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend`（121 项测试全部通过）
- **前端检查**：`npm --prefix frontend run lint` 与 `npm --prefix frontend run typecheck`（均通过，退出码 0）
- **格式检查**：`git diff --check`（通过，无空白或格式错误）

## 6. 已知限制与残余风险

- **合同差异留待 v1.2**：v1.1.0 归档时，`code.bare_exception`（需拆出 `except Exception`）与 `code.unmanaged_open`（需覆盖 `Path.open`）的检测器实现与卡片合同之间仍存差异，已作为首优遗留项列入 [`v1.2-entry.md`](v1.2-entry.md) 并由 Task 020 承接。
- **候选规则待落地**：研究登记册中的 20 条 `draft` 规则仅完成纸面卡片与结构可行性预审，尚未接入运行时检测器（由 Task 021、022 及后续切片分批落地）。
