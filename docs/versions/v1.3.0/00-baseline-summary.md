# Prisk-System v1.3.0 基线摘要

| 属性 | 内容 |
| --- | --- |
| 基线版本 | v1.3.0 |
| 基线状态 | 运行时配置解耦、5 套场景预设、三级快照局部重跑缓存、可复现审查报告配置快照固化、GitHub Primer 审查工作台重构归档 |
| 规则库规模 | 29 条登记规则（26 张规范化卡片，3 条排除项；24 条 `implemented`，5 条 `draft`） |
| 运行时规则 | 29 条（5 条历史结构规则 + 9 条语言代码异味 + 11 条后端契约 + 4 条变更冲击） |
| 场景预设 | 5 套（`balanced`、`security_focus`、`framework_upgrade`、`daily_review`、`legacy_baseline`） |
| 满分基线与评分 | `legacy_baseline` 保持 `maximum_points = 10`；PR #12 得分 30 分完全兼容；其余 4 套预设支持动态分值与阈值 |
| 重跑与缓存 | 三级局部重跑（Tier 0 全量 / Tier 1 规则局部重算 / Tier 2 仅评分重算），输出 `snapshot_meta` |
| 报告与复现 | 强制固化 `config.snapshot.v1` 配置快照与 16 位确定性 SHA-256 `config_digest`，支持 JSON 载荷 100% 还原复现 |
| 前端工作台 | GitHub Primer 规范，左侧常驻 29 条规则目录与卡片抽屉，Files Changed 粘性目录树与连续 Diff 流，支持 `Viewed` 跟踪与行级高亮定位 |
| 自动化测试 | 209 项单元与集成测试全部通过 |
| 实证先导集 | 16 个真实 NetBox PR 摸底样本（永久排除出 v1.4 正式集） |

---

## 1. 核心技术能力现状

- **运行时配置解耦与场景预设（`config.v1`）**：
  - 领域模型 [`backend/prisk/domain/config.py`](../../../backend/prisk/domain/config.py) 全面接管规则开关、权重、分段阈值与规则内部判定参数；
  - 预设体系覆盖安全审计、框架升级、日常合规、均衡基线与历史兼容 5 大典型场景；
  - 规则内部判定参数（如深控制流最大嵌套深度 `max_depth` 与硬编码密钥最小长度 `min_length`）支持动态下发至 AST 检测器。
- **三级分析快照缓存与局部重跑机制**：
  - 服务层 [`backend/prisk/services/analysis_cache.py`](../../../backend/prisk/services/analysis_cache.py) 提供线程安全 LRU 缓存（上限 50 份）；
  - 精确比对配置差异，自动选择 `stage07_rescore_only`（毫秒级重算分数）、`stage05_rules_rerun`（复用 Diff/AST 语法树重算规则）或 `full_run`（全量重新提取）；
  - 输出 `snapshot_meta` 诊断元数据并在前端高对比度呈现 Tier 0/1/2 状态徽标。
- **可复现配置快照封存与报告导出（`config.snapshot.v1`）**：
  - 每次分析生成 16 位确定性 SHA-256 指纹 `config_digest`；
  - Markdown 与 JSON 报告强制封存完整配置参数表及可直接反序列化重新执行的配置载荷块，从根本上解决评审结论因权重变动无法追溯、不可复现的痛点。
- **GitHub Primer 交互工作台深度重构**：
  - 遵循 GitHub Primer 视觉体系，彻底解决长路径/分支名溢出穿透截断问题，正文字号提升至 13px~14px；
  - 左侧常驻 29 条规则目录导航树，按 6 大关注域分组折叠并实时标注 `Hit / NotFound / Unanalyzed` 终态徽标，支持全局搜索与规则定义侧边抽屉查阅；
  - 顶栏精简为紧凑 GitHub PR 双层头部；
  - Files Changed 审查视图采用「左侧 Sticky 固定高度目录树 + 右侧多文件连续 Diff 卡片流」，支持文件夹独立折叠、单文件 Diff 折叠、`Viewed` 已审阅勾选与进度跟踪，以及规则证据行级金色高亮聚焦。

---

## 2. 规则知识库体系

- 知识库 26 张规范化卡片中，所有具备局部 AST 条件的 **24 张卡片已 100% 实现为三态检测器**（生命周期晋升为 `implemented`）。
- 保持 2 张按原设计延后的草稿卡片（生命周期保持 `draft`）：
  - `data.django_transaction_boundary_changed`：依赖函数内语句相对于 `atomic` 块的层级包含关系；
  - `workflow.large_change_scope`：依赖项目级行数/文件数/模块数阈值配置与模块映射政策。
- 保持 3 张无卡片预留项保持 `draft`（`code.dead_code_after_exit`、`auth.drf_object_permission_bypass`、`auth.django_permission_module_changed`）。

---

## 3. 遗留与后续演进（v1.4 规划承接）

- **规模型实证打靶**：在严格物理隔离 v1.1 先导集（16 条样本）的前提下，构建独立的正式实证集，进行真实开源项目 PR 的规模型批量运行。
- **高噪规则筛选与治理**：基于正式集三态数据分布与人工标注准确率，识别低区分度或高噪声规则，实施权重降级或默认禁用，推进有效规则向 `validated` 晋升。
- **默认基线权重校准与论文实验数据产出**：打破过渡态全 0 权重，建立经真实 PR 检验的合理默认权重推荐值，产出学术论文所需的量化对比与有效性威胁分析数据。
