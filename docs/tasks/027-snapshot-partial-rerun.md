---
task_id: "027"
target_version: "v1.3.0"
title: "快照局部重跑与分析缓存"
status: "Accepted"
branch: "feat/027-snapshot-partial-rerun"
date: "2026-11-10"
---

# 027：快照局部重跑与分析缓存

## 1. 背景与目标

本任务承接 [v1.3 阶段入口文档](v1.3-entry.md) 与 [推进大纲](../standards/development-roadmap.md) 中关于「v1.3.0 动态交互工作台与报告」的第二项核心指标。

在 Task 026 完成运行时配置解耦与 5 套场景预设后，前端看板与 API 能够动态切换预设、调整权重与阈值。但在当前实现中，用户每次发起分析时系统均必须完整调用 Git 差异提取（Stage03）与 Python AST 语法树全量解析（Stage04），在大型项目和多文件变更分支上时延过长。

本任务旨在建立线程安全的分析快照缓存（`AnalysisSnapshotCache`）与三级局部重跑判定机制（Three-tier Partial Rerun）：
1. **Tier 0 (`full_run`)**：缓存未命中或强制刷新时，全量执行 Stage03 -> Stage04 -> Stage05 -> Stage07 并缓存；
2. **Tier 1 (`stage05_rules_rerun`)**：规则开关（`enabled_rules`）或规则内部参数（`rule_thresholds`）变动时，直接复用 Stage03/Stage04 语法树，仅局部重跑 Stage05 规则评估与 Stage07 评分；
3. **Tier 2 (`stage07_rescore_only`)**：仅规则权重（`rule_weights`）或风险判定阈值（`thresholds`）变动时，直接复用 Stage03/Stage04/Stage05，毫秒级重算 Stage07 评分。

## 2. 范围与边界

### 纳入范围

1. **新建分析快照缓存管理模块 [`backend/prisk/services/analysis_cache.py`](../../backend/prisk/services/analysis_cache.py)**：
   - 确立缓存数据类 `CachedSnapshot`；
   - 基于 LRU 机制实现线程安全缓存管理类 `AnalysisSnapshotCache`（默认上限 50 份快照）；
   - 提供缓存命中、驱逐与统计能力（`hits`、`misses`、`tier1_reruns`、`tier2_rescores`）。
2. **重构分支分析服务 [`backend/prisk/services/branch_analysis.py`](../../backend/prisk/services/branch_analysis.py)**：
   - 接入缓存三元组 Key：`f"{repo}:{base_sha}..{head_sha}"`；
   - 接入三级局部重跑判定机制；
   - 报表输出透明的快照复用元数据 `snapshot_meta`（包含 `cache_hit`、`rerun_tier`、`diff_reused`、`ast_reused`、`rules_reused`）。
3. **对齐演示服务 [`backend/prisk/services/demo_service.py`](../../backend/prisk/services/demo_service.py)**：
   - 在 `DemoData.analyze` 报表中补充 `snapshot_meta`，统一全系统快照诊断协议。
4. **扩展 HTTP 适配层 [`backend/prisk/adapters/http_server.py`](../../backend/prisk/adapters/http_server.py)**：
   - `POST /api/branch-analysis` 支持 `refresh: bool` 参数强制全量重跑；
   - 新增 `GET /api/cache/stats` 端点返回当前缓存运行指标。
5. **单元测试与文档同步**：
   - 新增 `backend/tests/services/test_analysis_cache.py`；
   - 更新活动任务索引与阶段入口。

### 不做事项（技术边界）

- 不改动 Stage03（Diff）与 Stage04（AST）的核心提取算法与数据 Schema。
- 不改动 29 条规则的内部检测逻辑（`Hit / NotFound / Unanalyzed` 判定保持原状）。
- 不实现跨进程分布式缓存（如 Redis），仅保持单机轻量级进程内快照缓存。

## 3. 技术方案与契约设计

### 核心方案

#### 1. 缓存三元组与强绑定校验
- 缓存键为 `f"{repo_path}:{base_sha}..{head_sha}"`；
- 使用已解析的 40 位 Commit SHA，当分支提交更新时，SHA 改变自然引发缓存 Miss，绝不产生脏数据。

#### 2. 三级重跑判定矩阵
| 重跑层级 (`rerun_tier`) | 触发条件 | Diff (Stage03) | AST (Stage04) | Rules (Stage05) | Score (Stage07) | 预期耗时 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`full_run`** (Tier 0) | 首次分析或 `refresh=True` | 全量执行 | 全量解析 | 全量评估 | 全量打分 | 100~1000ms |
| **`stage05_rules_rerun`** (Tier 1) | `enabled_rules` 或 `rule_thresholds` 变动 | 缓存复用 | 缓存复用 | 局部重算 | 全量打分 | 1~10ms |
| **`stage07_rescore_only`** (Tier 2) | 仅 `rule_weights`、`thresholds` 或测试协同变动 | 缓存复用 | 缓存复用 | 缓存复用 | 重新打分 | < 0.5ms |

### 契约与兼容性

- **报表 Schema 扩展**：
  在 Stage08 分支报告中增加可选对象字段 `snapshot_meta`：
  ```json
  "snapshot_meta": {
      "cache_hit": true,
      "rerun_tier": "stage07_rescore_only",
      "diff_reused": true,
      "ast_reused": true,
      "rules_reused": true,
      "cached_at": "2026-11-10T19:40:00Z"
  }
  ```
  该字段纯属增量元数据，不破坏既有 UI 与自动化测试对原有字段（`score`, `risk_level`, `summary`, `files`, `findings`）的断言。
- **历史测试兼容**：全量测试套件（199 项）无缝兼容。

## 4. 交付物与改动清单

### 改动文件

- **源码实现**：
  - `backend/prisk/services/analysis_cache.py` [NEW]：快照缓存与三级重跑管理器；
  - `backend/prisk/services/branch_analysis.py` [MODIFY]：分支分析接入快照缓存与重跑链路；
  - `backend/prisk/services/demo_service.py` [MODIFY]：对齐 PR 分析的 `snapshot_meta`；
  - `backend/prisk/adapters/http_server.py` [MODIFY]：接入 `refresh` 参数与 `/api/cache/stats` 端点。
- **测试与文档**：
  - `backend/tests/services/test_analysis_cache.py` [NEW]：快照缓存与三级重跑单元测试；
  - `docs/tasks/027-snapshot-partial-rerun.md` [NEW]：本任务规范文档；
  - `docs/tasks/README.md` [MODIFY]：登记 Task 027；
  - `docs/tasks/v1.3-entry.md` [MODIFY]：更新活动任务索引。

## 5. 验证与验收

### 验收要点

1. 首次执行记录 `full_run`，`cache_hit=False`；
2. 调整规则权重或风险等级阈值时，触发 `stage07_rescore_only`，Diff/AST/Rules 全部复用；
3. 调整规则开关或规则参数时，触发 `stage05_rules_rerun`，Diff/AST 复用，重跑 Stage05；
4. 传 `refresh=True` 时，强制触发 `full_run`；
5. LRU 驱逐策略生效，线程安全无锁竞争异常。

### 执行检查

- **后端测试**：`backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend`
- **前端检查**：`npm --prefix frontend run lint` / `npm --prefix frontend run typecheck`
- **格式检查**：`git diff --check`

## 6. 已知限制与残余风险

- **单机内存边界**：当前缓存存储在进程内存中（LRU 容量上限 50），后端进程重启后缓存重置；
- **前端指示器对接**：`snapshot_meta` 的复用标签（如“秒级重算”、“Diff已复用”）在前端界面上的视觉标签由 Task 028 对齐完成。
