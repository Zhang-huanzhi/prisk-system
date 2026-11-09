# Prisk-System v1.1.0 阶段基线与里程碑归档

| 项目 | 内容 |
| --- | --- |
| 版本 | v1.1.0 |
| 阶段定位 | 规则知识库全集与显式三态执行基线 |
| 状态 | Frozen / Milestone Archive |
| 性质声明 | 本归档为内部阶段成果收工归档，非对外发布（Not a Release），不打 Git Tag |

本目录归档 v1.1.0 阶段的全部设计卡片、可行性筛选、真实 PR 先导协议、显式规则终态与门槛决策记录。后续 v1.2 迭代任务在 `docs/tasks/` 中新建，不回写本冻结目录。

---

## 一、 阶段核心产物

1. **规则知识库全集（26 张规范化卡片 + 3 条排除项，共 29 条登记）**：
   - 语言级代码异味（`code_smell`，8 条卡片）：`swallowed_exception`、`bare_exception`、`dynamic_execution`、`hardcoded_secret`、`unmanaged_open`、`deep_control_flow`、`global_mutable_state`、`assert_in_production`、`mutable_default_argument`（卡片 9 张，含死代码 1 条未建卡排除项）。
   - 后端契约（`backend_contract`，11 条卡片）：涵盖 DRF 接口增删参数、ViewSet 动作变更、URL 路由、权限策略降级、CSRF 豁免、原生 SQL 执行、信号泄漏等；另含 2 条排除项。
   - 变更冲击（`breaking_impact`，6 条卡片）：破坏性 Migration、非空约束收紧、事务边界变更、字段未映射改名、大规模变更范围、测试协同缺失。
   - 卡片母版统一：基于 26 张卡片实际沉淀出的比较单位、适用性、闭集、触发特征等 12 项标准化结构对齐模板与 Schema。
2. **结构可行性筛选（3 分类）**：
   - 局部 Diff/AST 可行（8 条）：已接入运行时与构造测试。
   - 有界框架上下文（10 条）：同一文件表面或明确闭集支持。
   - 延后跨文件/策略依赖（2 条）：事务边界包含关系与大规模变更阈值。
3. **真实 PR 先导摸底协议（`docs/evaluation/pilot-v1.1/`）**：
   - 抽样并冻结 16 条公开已合并 NetBox PR，建立身份、规则终态与标注难度摸底。
   - 做出永久隔离承诺：16 个先导样本永久排除出 v1.4 正式实证评估集。
4. **运行时引擎与三态执行（Tri-State Execution）**：
   - 运行时规则目录扩展至 14 条（含 5 条历史结构规则、7 条代码异味、1 条测试协同、1 条原生 SQL）。
   - 每次新鲜分析产出显式三态记录（`Hit / NotFound / Unanalyzed`），仅 `Hit` 输出 Finding。
   - 评分保持启发式人工复核优先级定位，透明可追溯。
5. **门槛收口决策（Task 018）**：
   - 所有者终裁以 `yes with carve-outs` 收口设计范围；
   - 明确残余检测器差异（如 `bare_exception` 的 Exception 拆分、`unmanaged_open` 的 `Path.open`、一票抬升评分联动）进入 v1.2 及后续迭代；
   - 20 条草稿卡片在接入检测器前按设计保持 `draft`。

---

## 二、 特别说明：Task 013 先行合入口径

在迭代推进中，**Task 013（`data.django_raw_sql_execution`）** 目标版本虽标注为 `v1.2.0`，但其实质代码已先行合并入 `main`（PR #13，使运行时规则增至 14 条），并作为后续 014–018 任务的既定事实运行环境。在本次 v1.1.0 归档中，诚实记录该检测器已作为既成事实随代码库固化，其后续生产级有效性验证与配置优化统一纳入 v1.2。

---

## 三、 任务索引（Task 001–018）

| 任务 | 标题 | 分支 | 状态 |
| :---: | :--- | :--- | :---: |
| 001 | 规则分类体系重构与规则说明卡片规范 | `main` | Accepted |
| 002 | 建立规则知识库与首批规则卡片 | `v1.1.0-002-rule-knowledge-base` | Accepted |
| 003 | 规则 ID 命名迁移与四拆五解耦 | `docs/rule-id-naming` | Accepted |
| 004 | AST 代码异味检测器 | `feat/004-ast-detectors` | Accepted |
| 005 | 第二批代码异味与 Django 契约卡片 | `feat/005-second-batch-code-smells` | Accepted |
| 006 | 剩余语言级代码异味 | `feat/006-remaining-code-smells` | Accepted |
| 007 | 测试协同复核提示 | `feat/007-test-collaboration` | Accepted |
| 008 | 文档信息架构与核心蓝图 | `docs/008-docs-structure-blueprint` | Accepted |
| 009 | 显式规则终态与三态引擎 | `feat/009-explicit-rule-outcomes` | Accepted |
| 010 | 开发推进大纲制定 | `docs/010-development-roadmap` | Accepted |
| 011 | 规则卡片与结构可行性筛选 | `docs/011-rule-card-feasibility` | Accepted |
| 012 | 真实 PR 先导试点协议与排除承诺 | `docs/012-pilot-protocol` | Accepted |
| 013 | Django 原生 SQL 执行检测器（先行合入） | `feat/013-django-raw-sql` | Accepted |
| 014 | v1.1 规则卡片就绪核对 | `feat/014-rule-card-readiness` | Accepted |
| 015 | 大规模变更范围严重度与风险性质临时对齐 | `docs/015-large-change-scope-severity` | Accepted |
| 016 | 六张新的草稿规则卡片扩充 | `docs/016-six-new-draft-cards` | Accepted |
| 017 | 规则卡片内容与模板格式规范化 | `docs/017-card-content-format` | Accepted |
| 018 | v1.1 卡片门槛收口决策 | `docs/018-v11-card-gate` | Accepted |

归档任务原件见 [tasks/](tasks/) 子目录。
