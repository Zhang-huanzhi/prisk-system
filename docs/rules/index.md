# 研究规则索引

本目录是研究材料：规则卡片、卡片框架和状态看板。它不是运行时规则目录，也不是代码登记册。运行时目录在版本化源码中，不由本索引加载。

概念分类、Rule ID 与运行配置的目标边界以 [核心蓝图](../blueprint.md) 为准。本页不另写一套架构，也不把蓝图中的动态调参、权重调优或实证验证写成已经实现。

## 卡片框架

新卡片按 [规则说明卡片模板](rule-card-template.md) 编写。模板用于设计与验证记录。卡片上的生命周期是研究状态；`implemented` 只表示检测器和构造测试已经接入，不表示实证验证。

工程验证和实证责任见 [责任矩阵](rule-responsibility-matrix.md)。候选规则和生命周期的状态看板是 [规则知识库](README.md)。011 的 [结构可行性筛选](structural-feasibility.md) 覆盖看板上的 20 条候选，只区分局部 Diff/AST、有界框架上下文和需要跨文件或未定项目政策的延后项。它不是运行结果。登记册 JSON 若与卡片不一致，以卡片为设计依据。JSON 登记册和 [规则元数据 schema](../schemas/rule-metadata.schema.json) 都不是运行时配置。运行时目录现为 14 条。013 把 `data.django_raw_sql_execution` 按 011 闭集接入，默认权重 0。014 的 [就绪核对](v1.1-card-readiness.md) 不扩大这份目录，也不另设生命周期字段。登记册仍不是运行时配置。

## 阵营目录

- [后端契约](catalog/backend_contract/README.md)
- [变更冲击](catalog/breaking_impact/README.md)

语言级卡片由 [状态看板](README.md) 按文件链接。`catalog/code_smell/` 没有单独的目录说明页。
