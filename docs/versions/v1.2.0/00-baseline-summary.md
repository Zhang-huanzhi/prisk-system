# Prisk-System v1.2.0 基线摘要

| 属性 | 内容 |
| --- | --- |
| 基线版本 | v1.2.0 |
| 基线状态 | 核心规则实现全量落地、三态引擎能力闭环、任务模板规范化归档 |
| 规则库规模 | 29 条登记规则（26 张规范化卡片，3 条排除项；24 条 `implemented`，5 条 `draft`） |
| 运行时规则 | 29 条（5 条历史结构规则 + 9 条语言代码异味 + 11 条后端契约 + 4 条变更冲击） |
| 满分基线与评分 | `maximum_points = 10`；新增规则默认权重为 0；PR #12 得分 30 分完全兼容 |
| 自动化测试 | 186 项单元与集成测试全部通过 |
| 实证先导集 | 16 个真实 NetBox PR 摸底样本（永久排除出 v1.4 正式集） |

---

## 1. 核心技术能力现状

- **增量 Diff 与多维 AST 提取（Stage03–Stage04）**：
  - 基于 Git `base...head` 三点对比精确圈定文件与 Hunk 增删行。
  - AST 结构提取层扩展支持：路由调用事实闭集提取（`path`/`re_path`/`register`/`include`/`url`）、`Assert` 语句节点、函数/Lambda 可变默认参数容器、`Meta.fields / exclude` 内部类列表常量，以及模型字段与迁移调用的 `default=` / `null=` 关键字。
- **已知框架基类映射支持**：
  - 运行时内置 `framework_bases.py`，支持将 `PrimaryModelSerializer`、`NetBoxModelViewSet`、`NetBoxModel` 精确映射为 Django/DRF 原生语义，并向后支持表外基类未分析原因标记。
- **严格三态判定（Stage05 `rule_outcomes`）**：
  - 运行时 29 条规则对新鲜分析产出显式三态（`Hit` / `NotFound` / `Unanalyzed`）。
  - `Hit`：精确满足 AST/Diff 闭集触发条件，输出 Finding（附代码切片与行号）；
  - `NotFound`：规则上下文适用且完整执行后无风险，静默不生成 Finding；
  - `Unanalyzed`：当遇到框架上下文缺失（`missing_framework_context`）、阶段细节不支持（`unsupported_stage04_details`）或上下文未建立（`context_not_established`）时显式记入缺口清单，绝不把“未能分析”伪饰为“安全通过”。
- **评分与一票抬升联动（Stage07）**：
  - 综合得分保持透明启发式复核优先级定位。
  - 评分服务联动读取登记册 `gatekeeper=true` 条件，对破坏性迁移与危险权限降级强制抬升 `risk_level="high"`。

## 2. 规则知识库体系

- 知识库 26 张规范化卡片中，所有具备局部 AST 条件的 **24 张卡片已 100% 实现为三态检测器**（生命周期晋升为 `implemented`）。
- 仅保留 2 张按原设计延后的草稿卡片（生命周期保持 `draft`）：
  - `data.django_transaction_boundary_changed`：依赖函数内语句相对于 `atomic` 块的层级包含关系；
  - `workflow.large_change_scope`：依赖项目级行数/文件数/模块数阈值配置与模块映射。

## 3. 遗留与后续演进（v1.3 规划承接）

- **运行时配置动态解耦**：当前规则目录与默认权重仍由代码静态驱动，v1.3 将探索规则启用开关、权重与阈值的动态配置与持久化。
- **快照局部重跑与交互工作台**：复用已提取的 Git Diff 与 Stage04 AST 上下文，支持前端在调整配置后快速局部重跑规则与评分。
- **审查报告可复现固化**：在导出 Markdown/JSON 报告时强制封存运行配置快照（开关/权重/阈值），确保审计结论可追溯。
