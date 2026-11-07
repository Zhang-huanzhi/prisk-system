# 先导试点协议

| 适用 | 仅 [012](../../tasks/012-pilot-protocol.md) 的先导试点 |
| --- | --- |
| 状态 | Accepted |
| 抓取日 | 2026-11-07 |
| 仓库 | `netbox-community/netbox` |

本协议冻结这一次先导摸底怎么抽样、怎么记身份、怎么下判断。它落实推进大纲里的先导摸底，并与最终评估集严格隔离。[开发推进大纲](../../standards/development-roadmap.md) 是规划文档。This is a planning document and is not evidence of completion or implemented functionality.

## 目的

看两件事：当前已经实现的研究规则在这些 PR 上会不会出现；高优先级草稿卡片的表面能不能由人在 diff 里对上，以及一个人一轮要多久。产出是实现优先级和样本量级，不是论文指标。

## 明确不做

- 不计算 Precision 或 Recall，不写经验有效性，不写 NetBox 的生产效果。
- 不把 Hit 写成已证实缺陷、漏洞或回归。
- 不改规则语义，不改默认权重，不新增检测器。
- 不把本目录的 PR 放进 `docs/versions/`，也不启动 013 的实现。
- 不改写 v1.0.0 冻结调研的结论。调研只作历史背景，见 [02 阶段](../../versions/v1.0.0/02-PR采样&定风险场景/README.md)。

研究候选仍是 20 条。运行时仍是 13 条：五条历史结构规则、七条代码异味、`workflow.test_collaboration_gap`。这两个计数不能互换。结构分类见 [结构可行性筛选](../../rules/structural-feasibility.md)：局部 Diff/AST 8、有界框架上下文 10、延后 2。

## 抽样框

公开、已合并、抓取日仍能用 GitHub API 取回的 NetBox PR。

- 仓库固定为 `netbox-community/netbox`。
- `merged_at` 非空，且落在 2024-01-01 至 2026-11-07。
- 不使用 v1.0.0 冻结调研 JSONL 里的 120 个编号。该文件是 `docs/versions/v1.0.0/02-PR采样&定风险场景/artifacts/netbox-survey.jsonl`。
- 抓取时 GitHub 记录的 `changed_files` 为 1 到 25，`additions + deletions` 为 8 到 800。
- 变更文件里至少有一个 `.py`。
- 标题不是版本发布 PR（`Release v`）。
- `base.ref` 可以是抓取时的默认分支 `main`，也可以是别的分支。不是 `main` 的必须在清单里标出。这类 PR 合并进的是该分支，不一定是默认分支上的最终提交。

超过行数上限的候选不进入清单，因此也不进入下面的排除名单。本次看过但未纳入的例子是 PR 23137（约 1090 行）。它不是试点 PR。

## 分层

这是目的抽样，不是随机样本，也不能当作 NetBox 里各类变化的发生率。层是为了让即将到来的 Django/DRF 草稿和当前研究规则都有表面可看。同一层里优先体积更小、并且标题或路径已经指向该表面的已合并 PR。

| 层 | 条数 | 编号 |
| --- | ---: | --- |
| `api_serializer` | 4 | 23175、22473、22472、23071 |
| `api_endpoint` | 2 | 23631、19846 |
| `auth` | 3 | 22777、22469、23205 |
| `data` | 3 | 23276、23429、21901 |
| `config` | 2 | 23509、21941 |
| `ordinary` | 2 | 23606、23626 |

`ordinary` 从抓取日附近、已经满足纳入条件、且没有为了某条异味去搜标题的已合并 PR 里留下。合计 16。

## 身份字段

机器可读清单是 [manifest.json](manifest.json)。每条 PR 记录：

| 字段 | 含义 |
| --- | --- |
| `repo` | `netbox-community/netbox` |
| `number` | PR 编号 |
| `title` | 抓取时的标题 |
| `html_url` | `https://github.com/netbox-community/netbox/pull/<number>` |
| `merged_at` | 合并时间 |
| `base_ref` / `head_ref` | 抓取时 API 返回的分支名 |
| `base_ref_is_default` | `base_ref` 是否为 `main` |
| `api_base_sha` | 抓取时 `pull.base.sha`。已合并 PR 上这经常是基分支的当前尖端，不是合并前的父提交 |
| `api_head_sha` | 抓取时 `pull.head.sha`，即 PR 分支头 |
| `merge_commit_sha` | 合并提交。压缩合并时它通常不是 `api_head_sha` |
| `merge_parent_count` | 合并提交的父提交个数 |
| `landed_base_sha` | 合并提交的第一父提交。筛查 diff 的基 |
| `landed_head_sha` | 合并提交本身。筛查 diff 的头，等于 `merge_commit_sha` |
| `changed_files` / `additions` / `deletions` | GitHub PR 计数 |
| `stratum` | 上表的层 |
| `in_v1_0_0_frozen_survey` | 本次全部为 false |
| `excluded_from_v1_4_formal_set` | 本次全部为 true |

人读表是 [sample-table.md](sample-table.md)。两边编号必须一致。

## 筛查怎么跑

优先用现有分析入口，不改语义。本次没有克隆完整 NetBox。对每条 PR：

1. 读取合并提交及其第一父提交。
2. 用 compare API 确定落地 diff 的文件列表，再用 Contents API 取这些文件在两侧的全文。
3. 在临时双提交仓库里调用 `prisk.services.branch_analysis.analyze_branches`。
4. 临时仓库的文件数、新增行数、删除行数与 GitHub PR 计数一致时，才把运行终态写入 [screen.json](screen.json)。本次 16 条全部一致，没有缺失 blob。

这覆盖变更文件的落地 diff，不包含未改文件，也不是三点 diff 相对一个更早的 merge-base 的另一种切法。历史结构规则会一起跑，因为它们就在 13 条运行时目录里。筛查正文分开记录，不把它们算进八条研究规则的零命中。

草稿卡片没有检测器。对上表面与否是人工对照卡片闭集，写在 `draft_judgments`。新增行上的字符串检索只用来找候选行，注释和文档里的同名文本不记成设计 Hit。

不记录评分数字。权重保持原样。

## 判断口径

运行终态和人工判断分开记。运行终态只有 Hit、NotFound、Unanalyzed，含义与 [009](../../tasks/009-explicit-rule-outcomes.md) 相同：没有适用上下文时不记 NotFound。

人工判断只用下面四个词。

| 判断 | 含义 |
| --- | --- |
| `hit` | 八条研究规则给出 Finding，且形态就是卡片在问的那件事；或草稿卡片的设计触发能在同一文件 diff 里逐条对上。两者都不是已证实缺陷 |
| `false_looking_hit` | 有 Finding，或 diff 里有很像触发的名字，但按卡片自己的限制，不把它当成那条规则要看的问题 |
| `unanalyzed` | 运行终态是 Unanalyzed，而且缺的是证据或框架上下文，不是“根本没有这张表面”；或草稿写明要记未分析 |
| `not_applicable` | diff 里没有这条规则的适用表面 |

`context_not_established` 的运行终态仍写 Unanalyzed。若原因只是 diff 里没有 `except` 或其他适用节点，人工判断记 `not_applicable`，避免把“没表面”说成分析失败，也避免把它说成 NotFound。

研究规则的 `hit` / `false_looking_hit` 只落在真正的 Finding 上。草稿规则的 `hit` 只表示设计表面对得上，检测器并不存在。

## 耗时

每条 PR 记 `review_minutes_estimate`，单位是分钟，整数。

记法：一个人一轮。先看文件清单和八条研究规则的终态，再看有 Finding 或草稿关键词的补丁。不要求读完无关测试的每一行。数字是这一轮的估计，不是秒表，也不是第二个人的复核。小 diff 大约 4 到 8 分钟；长测试或长迁移列表大约 10 到 15 分钟。

这个数字不含把五条历史结构规则的每条证据都标完。那些规则在测试文件上很吵，正式标注若要覆盖它们，耗时会更高。

## 零命中与饱和

两个旗标只描述八条研究规则，不是质量分，也不是预先登记的试验终点。

- `zero_hit`：八条里没有 Hit。Unanalyzed 也可以使这个旗标为真。它不等于八条都已 NotFound。
- `saturated_hit`：八条里至少四条为 Hit，或这八条的 Finding 合计至少 8。

## 永久排除

`manifest.json` 的 `v14_exclusion.numbers` 是排除名单，与 `pull_requests` 的编号相同。每一个编号都永久不得进入 v1.4 正式评估集。

v1.0.0 冻结调研的 120 个编号本次没有复用。若以后有人把其中某个编号放进先导或调试，必须单独标成 pilot-contaminated，并且同样不得进入 v1.4。本协议不把那 120 个编号抄进来，也不把“没有复用”写成“正式集已经获准使用它们”。

## 标注记录字段

[screen.json](screen.json) 里每条 PR 使用：

- `number`、`stratum`、`html_url`
- `annotability`：`easy`、`medium` 或 `hard`
- `review_minutes_estimate`
- `annotability_why`
- `zero_hit`、`saturated_hit`
- `research_terminals`：八条研究规则各自的 Hit / NotFound / Unanalyzed
- `research_hit_judgments`：每条 Finding 的 `rule_id`、`path`、`start_line`、`end_line`、`judgment`、`why`
- `draft_judgments`：看过的草稿卡片，字段为 `rule_id`、`judgment`、`why`
- `historical_structure_hits`：五条历史结构规则里终态为 Hit 的 ID，只列名字

Finding 不保存源代码切片，也不保存字面量内容。
