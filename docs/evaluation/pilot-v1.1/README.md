# v1.1 先导试点（仅试点）

本目录只服务 [012](../../tasks/012-pilot-protocol.md)。它是设计用的先导摸底，用来看现有规则和草稿卡片在真实 NetBox PR 上是否出现、标注难不难。

本目录不是正式实证集，不进入 `docs/versions/`，也不作为 v1.4 的评估样本。这里没有 Precision、Recall、经验有效性或 NetBox 生产效果。Hit 不是已证实缺陷。权重没有改。

## 永久排除

[manifest.json](manifest.json) 里的每一个 PR 编号都永久排除出未来的 v1.4 正式评估集。不得把这些编号写进正式集，也不得因为它们已经在这里出现过，就把它当成可以调规则的测试集。

本次 16 个编号都不在 v1.0.0 冻结调研的 120 条里。冻结调研的结论不在本目录改写。那些历史编号也没有被收进本试点。

## 文件

| 文件 | 作用 |
| --- | --- |
| [protocol.md](protocol.md) | 抽样、身份字段、判断口径、耗时和排除承诺 |
| [manifest.json](manifest.json) | 16 条 PR 的机器可读身份 |
| [sample-table.md](sample-table.md) | 同一批 PR 的人读表 |
| [screen.json](screen.json) | 筛查判断的机器可读记录 |
| [screen.md](screen.md) | 筛查说明 |
| [t013-priority.md](t013-priority.md) | 给下一任务的建议，不是实现决定 |

本地补丁、临时仓库和 stage04 JSONL 不提交。忽略规则见仓库 `.gitignore` 里的 pilot cache。

## 遗留风险 / Residual risks

完整六条在 [012](../../tasks/012-pilot-protocol.md) 的「遗留风险 / Residual risks」。这里先写短的，避免只出现在对话里。

1. 16 条是目的分层样本。命中次数不是 NetBox 发生率。
2. 筛查用合并提交对第一父提交的变更文件，不是完整克隆，也不是三点 merge-base。22473、19846、21941 落在 `feature`，不是 `main`。
3. 研究规则 Hit 大多是 `code.global_mutable_state` 的 false-looking Hit。`zero_hit` 为 9 不表示八条都已 NotFound。
4. 估计分钟只覆盖一个人一轮，不含把历史结构规则在测试上的每条证据标完。
5. 后端 unittest 和前端 lint、typecheck、build 没有跑。本次只有文档和 `.gitignore`，这是验证缺口。
6. [t013-priority.md](t013-priority.md) 只是建议，不授权开始 013，也不授权改卡片或权重。
