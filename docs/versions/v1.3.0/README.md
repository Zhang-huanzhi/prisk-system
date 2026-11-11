# Prisk-System v1.3.0 阶段基线与里程碑归档

| 项目 | 内容 |
| --- | --- |
| 版本 | v1.3.0 |
| 阶段定位 | 动态交互工作台、快照局部重跑与可复现审查报告 |
| 状态 | Frozen / Milestone Archive |
| 性质声明 | 本归档为内部阶段成果收工归档，非对外发布（Not a Release），不打 Git Tag |

本目录归档 v1.3.0 阶段的全部运行时配置解耦、场景预设体系、分析快照局部重跑缓存、可复现配置快照报告固化以及 GitHub Primer 前端工作台深度重构记录。后续 v1.4 迭代任务在 `docs/tasks/` 中新建，不回写本冻结目录。

---

## 一、 阶段核心产物

1. **运行时配置解耦与 5 套场景预设体系（Task 026）**：
   - 确立配置领域模型 [`backend/prisk/domain/config.py`](../../../backend/prisk/domain/config.py)（`config.v1`），实现规则启用开关（`enabled_rules`）、启发式权重（`rule_weights`）、风险分段阈值（`thresholds`）与规则内部判定参数（`rule_thresholds`）的彻底解耦。
   - 内置 5 套标准化场景预设：`balanced`（均衡基线）、`security_focus`（安全加固审查）、`framework_upgrade`（框架与迁移升级）、`daily_review`（日常代码合规）与 `legacy_baseline`（历史兼容基线）。
   - 实现规则内部参数动态注入：`code.deep_control_flow` 动态支持 `max_depth`，`code.hardcoded_secret` 动态支持 `min_length`。
   - 提供预设元数据查询接口 `GET /api/config/presets`，并在 `legacy_baseline` 下严格保障 10 分满分基线与历史快照 100% 兼容。

2. **快照局部重跑与三级分析缓存（Task 027）**：
   - 建立线程安全、带 LRU 驱逐策略的分析快照缓存管理模块 [`backend/prisk/services/analysis_cache.py`](../../../backend/prisk/services/analysis_cache.py)（`AnalysisSnapshotCache`）。
   - 确立缓存三元组 Key：`f"{repo}:{base_sha}..{head_sha}"`，实现三级局部重跑判定机制：
     - **Tier 0 (`full_run`)**：首次分析或强制刷新（`refresh=True`）时全量解析 Stage03/04/05/07；
     - **Tier 1 (`stage05_rules_rerun`)**：规则开关或内部参数变动时，复用 Stage03 Diff 与 Stage04 AST，局部重跑 Stage05 规则；
     - **Tier 2 (`stage07_rescore_only`)**：仅权重或分段阈值变动时，复用 Stage03/04/05，毫秒级重算 Stage07 评分。
   - 报表输出透明的快照复用诊断元数据 `snapshot_meta`，并提供 `GET /api/cache/stats` 统计端点。

3. **可复现审查报告配置快照固化（Task 028）**：
   - 确立自包含配置快照契约 `config.snapshot.v1` 与 16 位确定性 SHA-256 指纹 `config_digest`，在 Stage07/08 审查报告顶层注入 `config_snapshot`。
   - 实现标准 Markdown 审查报告导出引擎 [`backend/prisk/domain/report_export.py`](../../../backend/prisk/domain/report_export.py)（`render_markdown_report`），强制在导出的 Markdown 与 JSON 报告中封存本次运行的完整配置快照及可反序列化复现的配置载荷块。
   - 编写复现验证测试，证明从导出的 Markdown 报告提取配置块重新发起审查可还原 100% 一致的分数、等级与指纹。

4. **前端工作台 GitHub Primer 风格深度重构与布局优化（Task 029）**：
   - 解决左侧栏长路径与长分支名溢出穿透截断问题，完善省略与原生悬停提示。
   - 左侧栏常驻 29 条规则目录导航树，按 6 大关注域分组折叠，实时标注 `Hit / NotFound / Unanalyzed` 状态徽标，支持搜索过滤与规则卡片抽屉弹窗。
   - 整合顶栏与 Heading 为 GitHub PR 紧凑双层头部，高对比度呈现复核等级、Gatekeeper 一票抬升徽标、SHA 快照对比与操作栏。
   - 全面引入 GitHub Primer 色彩排版体系，废除 `<12px` 超小难辨字体，正文提升至 13px~14px。
   - 审查视图重构为 GitHub PR "Files changed" 范式：「左侧 Sticky 层级目录树 + 右侧多文件连续 Diff 卡片流 + `Viewed` 已审阅跟踪 + 规则证据行级金色高亮定位」。

---

## 二、 特别说明：Task 025 衔接性质

Task 025（`v1.2 阶段里程碑收工归档与文档对齐`）在性质上属于 v1.2.0 的收尾归档任务，但其执行跨越了 v1.2 与 v1.3 的交界。在本次 v1.3.0 归档中，Task 025 连同本阶段的 Task 026–029 一并迁入本目录下的 `tasks/`，确保仓库历史任务编号（001–029）形成完整连续的归档链条。

---

## 三、 归档任务索引（Task 025–029）

| 任务 | 标题 | 分支 | 状态 | 目标版本 |
| :---: | :--- | :--- | :---: | :---: |
| 025 | [v1.2 阶段里程碑收工归档与文档对齐](tasks/025-v12-milestone-closure.md) | `docs/025-v12-milestone-closure` | Accepted | v1.2.0 |
| 026 | [运行时配置解耦与场景预设体系](tasks/026-runtime-config-presets.md) | `feat/026-runtime-config-presets` | Accepted | v1.3.0 |
| 027 | [快照局部重跑与分析缓存](tasks/027-snapshot-partial-rerun.md) | `feat/027-snapshot-partial-rerun` | Accepted | v1.3.0 |
| 028 | [Web 动态交互工作台与可复现审查报告固化](tasks/028-workbench-and-report-snapshot.md) | `feat/028-workbench-and-report-snapshot` | Accepted | v1.3.0 |
| 029 | [前端工作台 GitHub 风格重构与交互布局优化](tasks/029-frontend-github-ui-refactor.md) | `refactor/029-frontend-github-ui-refactor` | Accepted | v1.3.0 |

归档任务原件见 [tasks/](tasks/) 子目录。
