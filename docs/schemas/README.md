# Schema

| 文件 | 作用 | 状态 |
| --- | --- | --- |
| [rule-metadata.schema.json](rule-metadata.schema.json) | 研究用规则元数据 `rule-registry.v1` | 文档契约。不是运行时配置，也不表示系统已经支持动态调参 |

运行时规则不从本 schema 加载。`backend/data/rules/rule-registry.json` 仍是结构化候选索引，不是代码登记册。规则状态字段是 `rules[].lifecycle`，允许值是 `draft`、`registered`、`implemented`、`validated`、`deprecated`。核对见 [v1.1 卡片就绪核对](../rules/v1.1-card-readiness.md)。`validation_obligation.level` 不是这个字段。

目标边界见 [核心蓝图](../blueprint.md)。当前实现见 [架构说明](../architecture.md)。
