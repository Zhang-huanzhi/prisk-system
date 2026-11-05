# Prisk-System v1.1 下一阶段入口

| 目标版本 | v1.1.0 |
| --- | --- |
| 状态 | In Progress |
| 文档状态 | 发布后的迭代入口 |

## 当前迭代

v1.0.0 发布后，新增功能、问题修复和工程改造从这里建立编号迭代文档。v1.0.0 冻结目录不回写新行为。任务 `v1.1.0-001` 已完成规则分类体系与规则说明卡片规范；目标版本的其他任务仍需后续完成。

## 迭代文档

- [v1.1.0-001 规则分类体系重构与规则说明卡片规范](001-rule-taxonomy-and-card-template.md)
- [v1.1.0-002 建立规则知识库与首批规则卡片](002-rule-knowledge-base.md)
- [v1.1.0-003 规则 ID 命名迁移与四拆五解耦](003-rule-id-naming-and-five-rules.md)

## 产物

规则卡片和责任矩阵放在 [`docs/rules/`](../../rules/)，Schema 放在 [`docs/schemas/`](../../schemas/)，规则草案登记册和初始化脚本分别放在 [`backend/data/rules/`](../../../backend/data/rules/) 和 [`backend/scripts/`](../../../backend/scripts/)。登记册尚未接入运行时。
