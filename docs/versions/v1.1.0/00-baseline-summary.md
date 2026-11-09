# Prisk-System v1.1.0 基线摘要

| 属性 | 内容 |
| --- | --- |
| 基线版本 | v1.1.0 |
| 基线状态 | 规则知识库全集收口、三态引擎接入、卡片规范化归档 |
| 规则库规模 | 29 条登记规则（26 张规范化卡片，3 条排除项；9 条 `implemented`，20 条 `draft`） |
| 运行时规则 | 14 条（5 历史结构规则 + 7 语言代码异味 + 1 测试协同 + 1 Django 原生 SQL） |
| 实证先导集 | 16 个真实 NetBox PR 摸底样本（永久排除出 v1.4 正式集） |

---

## 1. 核心技术能力现状

- **增量 Diff 与 AST 分析**：通过 Git `base...head` 三点对比提取受改动文件，精确解析 Python AST 并将改动行与语法节点相交匹配。
- **三态判定输出**：
  - `Hit`：满足规则闭集条件，生成带有代码切片和行号的 Finding；
  - `NotFound`：规则上下文适用且执行完毕无风险，静默不生成 Finding；
  - `Unanalyzed`：当遇到框架上下文缺失（`missing_framework_context`）、阶段细节不支持（`unsupported_stage04_details`）或上下文未建立（`context_not_established`）时显式记入缺口清单，绝不把“未能分析”伪饰为“安全通过”。
- **透明复核评分**：综合得分仅为启发式人工复核优先级指导，支持 Critical/High 级别的 Red Flag 一票抬升机制（当前支持破坏性 Migration 与权限降级为 AllowAny 的设计定义）。

## 2. 规则知识库体系

- 建立了完整覆盖 `code_smell`、`backend_contract`、`breaking_impact` 三大维度的 26 张规范化卡片，包含比较单位、适用性、闭集、触发特征、终态定义与反例限制。
- 确立了 [已知框架基类映射](../../rules/known-framework-bases.md)，打通了 NetBox 典型基类（`PrimaryModelSerializer`、`NetBoxModelViewSet`、`NetBoxModel`）与 Django/DRF 原生语义的设计对照。

## 3. 遗留与后续演进（v1.2 规划承接）

- 残余检测器跟进：`code.bare_exception` 拆分出 `except Exception`、`code.unmanaged_open` 覆盖 `Path.open`、已知框架基类映射在检测器中的运行时读取。
- 动态运行配置解耦：在 v1.3 中探索规则开关、权重与阈值的动态配置，目前运行时仍由代码静态目录驱动。
