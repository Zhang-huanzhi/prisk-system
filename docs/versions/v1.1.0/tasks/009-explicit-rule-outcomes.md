---
task_id: "009"
target_version: "v1.1.0"
title: "显式规则终态"
status: "Accepted"
branch: "feat/009-explicit-rule-outcomes"
date: "2026-11-06"
---

# 009：显式规则终态

## 目标

在一次分析里，为现有 13 条运行时规则分别给出恰好一个终态：`Hit`、`NotFound` 或 `Unanalyzed`。只有 `Hit` 生成 Finding。`NotFound` 只在该规则已经完整执行、并且它的上下文适用时记录。零条 Finding 本身不是 `NotFound`。解析降级、证据不足、缺少框架或路径上下文、缺少前置阶段数据，都保持 `Unanalyzed`，并带上原因和对象。这些状态不加分，不是通过，也不是代码安全。

本任务不改检测器语义、规则 ID、13 条运行时目录、默认权重或评分公式。已保存的 demo 与历史快照不重写。用户已接受本任务。交付分支仍是 `feat/009-explicit-rule-outcomes`，交付记录是 [PR #9](https://github.com/Zhang-huanzhi/prisk-system/pull/9)。本提交把状态改为 Accepted，并把项目声明从 `requires-python >=3.13` 调整为 `>=3.12`。写下这条记录时该 PR 尚未合并，本提交也不合并、不打 tag、不删除分支。

## 编号核对

008 已说明下一个未使用编号是 009。v1.0.0 阶段 09 不是任务编号；仓库里没有已占用的任务 009。本任务不改 `docs/blueprint.md`。

## 范围

- 新鲜的 `evaluate_rules` 结果增加 `rule_outcomes`。已启用规则各一条，顺序与运行时目录一致。
- 演示 API 和分支报告带上终态是否可用。已保存 stage05 没有该字段时标为 `unavailable`，不回填终态。
- 看板用同一套终态文案。历史快照不显示“本次未命中”。没有测试上下文时不使用通过式图标。
- 用构造的小型 demo 覆盖：适用且零命中、实际命中、解析或证据不足、历史快照兼容，以及默认可得权重仍为 10。

## 不做事项

- 不把 JSON 登记册改成运行时配置，不引入机器学习，不对 NetBox 作有效性声明。
- 不新增规则，不改检测器命中条件，不把无法成立的规则一律写成 `NotFound`。
- 不重写已保存 demo、历史 Finding 或分数。本提交不合并，不打 tag，不删除分支。
- 不修改 `docs/blueprint.md`，不改写 v1.0.0 冻结目录，不改写 007 里当时的 Python 声明句子。不实现与本目标无关的 T010。
- 不把 `requires-python` 降到 3.12 以下。

## 技术方案

终态附在现有 stage05 结果上，不更换 schema 版本，也不把登记册读入运行时。

- `Hit`：现有检测器为该规则产出了 Finding。命中不表示其他对象都已查完；原有 `summary.unanalyzed` 仍保留缺口。
- `NotFound`：该规则的适用对象已经完整检查，没有 Finding，也没有属于该规则的证据缺口。
- `Unanalyzed`：规则没有 Finding，并且上下文没有成立或检查没有完成。原因沿用已有代码，并补充 `missing_framework_context`、`context_not_established`、`missing_file_change_channel` 和 `prior_stage_unavailable`。

框架路径规则没有对应路径、调用或装饰器时，终态是 `missing_framework_context`，不是 `NotFound`。代码异味没有检查到适用节点时，终态是 `context_not_established`。只有 AST、没有文件变更通道时，测试协同规则是 `missing_file_change_channel`；这不新增 `summary.unanalyzed` 行。前置阶段为 `excluded` 或 `error` 时，已启用规则都是 `prior_stage_unavailable`。

评分仍只使用 Finding 和原来的 `summary.test_collaboration`。默认权重、零权重和默认可得 10 分不变。

## 兼容性

- 规则结果仍是 `stage05.v2`。新字段是 `rule_outcomes`。旧快照没有该字段。
- 演示报告仍是 `stage07.report.v2`，分支报告仍是 `stage08.branch-report.v1`。二者增加 `rule_outcomes` 与 `rule_outcome_availability`。
- Finding、`summary.unanalyzed`、`test_collaboration` 和分数计算保持原样。
- 已保存 demo PR 12 仍是 3/10、分数 30，Finding 仍只有 `api.signature_changed`。
- `backend/pyproject.toml` 与 `backend/uv.lock` 的 `requires-python` 现为 `>=3.12`。仓库没有 Python 分类器（classifiers）。根 README 的当前版本要求改为 3.12 或更高。

## 验收

- 每个已启用规则恰好一个终态。`Hit` 与 Finding 中的规则 ID 集合相同。`NotFound` 和 `Unanalyzed` 都没有 Finding。
- 至少一条规则在适用上下文里完整执行后是 `NotFound`，同时至少一条规则因上下文不成立而是 `Unanalyzed`。
- 解析失败、缺少 stage04 细节或前置阶段不可用时，受影响规则是 `Unanalyzed` 并带原因和对象，不是 `NotFound`。
- 历史 demo 的终态为 `unavailable`，文件字节和分数不变。
- 默认可得权重仍是 10。代码异味默认权重仍是 0。
- `docs/blueprint.md` 的 SHA-256 仍是 `f0273030ec15fd0d8d87a767a37228b371d54a3f54b556f5e32c850f2454b817`。

## 实际测试

本工作区没有 GitHub Actions，也没有 `uv`。项目声明现为 `requires-python >=3.12`。系统 Python 是 3.12.3，与该声明一致。下面的命令是本机实际执行，也不是 CI。声明改为 `>=3.12` 之后，后端套件已在这个 3.12.3 运行时重新执行。

在 `backend/` 下：

- `python3 -m unittest discover -s tests -t .`：97 项全部通过，退出码 0。其中 `tests.domain.test_rule_outcomes` 覆盖适用且零命中、实际命中、解析失败、缺少 stage04 细节、前置阶段不可用、只有 AST 的文件通道、关闭单条规则，以及已保存 demo 的分数和字节。

在 `frontend/` 下：

- `npm ci`：安装锁定依赖。Node 是 v22.23.4，npm 是 10.9.9。
- `npm run lint`：通过。
- `npm run typecheck`：通过。
- `npm run build`：通过。
- `git diff --check`：通过。`docs/blueprint.md` 的 SHA-256 仍是 `f0273030ec15fd0d8d87a767a37228b371d54a3f54b556f5e32c850f2454b817`。

默认演示 API 读取已跟踪的 `backend/data/demo/`。`/api/pr/12` 的 `rule_outcome_availability` 是 `unavailable`，`rule_outcomes` 为 null。得分仍是 30，已得 3，可得 10，Finding 仍只有 `api.signature_changed`。stage05 文件字节没有变化。

用当前源码对仓库 `HEAD~1...HEAD` 做一次新鲜分支分析：13 条终态里 `workflow.test_collaboration_gap` 是 NotFound，其余 12 条是 Unanalyzed（4 条 `missing_framework_context`，8 条 `context_not_established`）。得分 0，可得 10。这次文档变更没有被写成 13 条 NotFound。

看板打开一份没有 `rule_outcomes` 的已保存 PR 时，协同横幅写明历史快照没有这条规则的终态，文件计数不能当成测试覆盖，也不表示代码安全。图标不是通过勾。规则目录徽章是「终态未记录」，页面上没有「本次未命中」。已有 Finding 仍照常列出。

## 遗留风险

- 同一条规则若已经产出 Finding，终态是 Hit。其他对象上的解析或证据缺口仍留在 `summary.unanalyzed`，不改叫 NotFound，也不把 Hit 说成全量通过。
- 代码异味的 NotFound 要求检测器确实检查过适用节点。新鲜解析里函数带有 `contains_global_statement: false`，或旧函数切片能够完整扫描且没有凭据字面量时，对应规则可以是 NotFound。仅仅缺少该类节点，终态是 `context_not_established`。
- 分支分析仍执行默认启用的全部目录。评分请求里的开关只影响计分，不把已执行规则从终态里删掉。这与原先分支 Finding 列表不被该开关裁剪的行为一致。
- 已保存快照没有终态。界面标为未记录，不回填。
- 测试协同在文件通道完整且没有「生产代码变更且没有测试路径变更」时是 NotFound，包括一次只改文档的变更。这只说明该复核特征没有出现，不是测试已经足够，也不是代码安全。
- 后端 97 项测试已在 Python 3.12.3 上通过，项目声明是 `requires-python >=3.12`。本环境没有 GitHub CI 结果。
