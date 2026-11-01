# Prisk-System 文档

本目录保存代码仓库的工程文档，以及构成 v1.0.0 冻结证据的经筛选研究样本和阶段产物。个人开题材料、完整 NetBox/Saleor 实验克隆、API 缓存、本机秘密和临时文件不进入本仓库。

## 文档分层

| 路径 | 职责 | 生命周期 |
| --- | --- | --- |
| `development-process.md` | 分支、迭代、检查、版本和发布流程 | 持续更新 |
| `architecture.md` | Python 分层、Web 和数据边界 | 随架构更新 |
| `operations.md` | uv、npm、API、看板、测试和本地报告 | 持续更新 |
| `versions/v1.0.0/` | 系统基线、阶段状态和可复用冻结证据 | Frozen |
| `iterations/v1.1/` | 发布后的下一阶段迭代入口 | Planned |
| `adr/` | 长期架构和仓库边界决策 | 按需新增 |

生命周期规则：源码和测试进入 Git；versions 保存冻结阶段事实及必要的可复核产物；iterations 保存活动计划和实际验证；本机依赖、上游仓库克隆、API 响应缓存和临时文件不进入 Git。冻结目录不收录个人材料，样本中的贡献者身份字段应脱敏。

## 入口

- [根 README](../README.md)
- [开发流程](development-process.md)
- [架构说明](architecture.md)
- [运维手册](operations.md)
- [v1.0.0 基线](versions/v1.0.0/README.md)
- [v1.1 下一阶段迭代](iterations/v1.1/README.md)
- [ADR 索引](adr/README.md)
