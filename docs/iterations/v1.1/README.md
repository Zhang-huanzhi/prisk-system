# Prisk-System v1.1 下一阶段入口

| 目标版本 | v1.1.0 |
| --- | --- |
| 状态 | In Progress |
| 文档状态 | 发布后的迭代入口 |

## 当前迭代

v1.0.0 发布后，新增功能、问题修复和工程改造从这里建立编号迭代文档。v1.0.0 冻结目录不回写新行为。001、002、003 为 Accepted。004 正在把三条语言级代码异味规则接入现有 AST 与 Finding 管道。JSON 登记册仍不是运行时配置。

## 迭代文档

- [v1.1.0-001 规则分类体系重构与规则说明卡片规范](001-rule-taxonomy-and-card-template.md)
- [v1.1.0-002 建立规则知识库与首批规则卡片](002-rule-knowledge-base.md)
- [v1.1.0-003 规则 ID 命名迁移与四拆五解耦](003-rule-id-naming-and-five-rules.md)
- [v1.1.0-004 AST 代码异味检测器](004-ast-code-smell-detectors.md)

## 产物

规则卡片和责任矩阵放在 [`docs/rules/`](../../rules/)，Schema 放在 [`docs/schemas/`](../../schemas/)，规则草案登记册和初始化脚本分别放在 [`backend/data/rules/`](../../../backend/data/rules/) 和 [`backend/scripts/`](../../../backend/scripts/)。登记册尚未接入运行时。三条 `implemented` 规则写在阶段 05 规则目录中，不从登记册加载。
