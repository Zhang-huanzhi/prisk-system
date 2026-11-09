# 研究规则索引

本目录保存规则知识库的研究材料：规则卡片、规范化母版模板、责任矩阵与设计决策记录。它不是运行时规则目录，也不是代码登记册。

概念分类、Rule ID 与运行配置的目标边界以 [核心蓝图](../blueprint.md) 为准。

## 卡片框架与规范

- **卡片模板**：统一按照 [规则说明卡片模板](rule-card-template.md) 编写，包含 12 项标准化检测定义子节。
- **元数据契约**：结构化 Schema 见 [rule-metadata.schema.json](../schemas/rule-metadata.schema.json)，登记册见 [rule-registry.json](../../backend/data/rules/rule-registry.json)。
- **基类映射**：NetBox 典型基类与框架原生语义对照见 [已知框架基类映射](known-framework-bases.md)。
- **可行性与责任**：
  - [结构可行性筛选](structural-feasibility.md)：明确局部 AST、有界框架上下文、延后跨文件/策略三分类；
  - [责任矩阵](rule-responsibility-matrix.md)：区分论文责任与工程验证责任；
  - [v1.1 卡片门槛决策](v1.1-card-gate-decision.md)：Task 018 所有者终裁以 `yes with carve-outs` 收口设计范围。

## 阵营目录

- **通用代码异味**：[规则状态看板](README.md)（语言级卡片直接按文件索引）
- **框架契约**：[后端契约规则卡片](catalog/backend_contract/README.md)
- **变更破坏冲击**：[变更冲击规则卡片](catalog/breaking_impact/README.md)
