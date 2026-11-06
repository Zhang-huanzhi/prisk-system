---
task_id: "007"
target_version: "v1.1.0"
title: "测试协同复核提示"
status: "Accepted"
branch: "feat/007-test-collaboration"
date: "2026-11-06"
---

# 007：测试协同复核提示

## 目标

在 Accepted 001–006 之上，把 `workflow.test_collaboration_gap` 从草稿变成一条保守的 PR 级复核提示。提示只使用三点 Diff 已经留下的文件状态、新增行数和删除行数，以及版本化源码里的默认路径分类。

Finding 只要求复核生产代码路径和测试计划。它不说明测试缺失、覆盖不足、回归、外部破坏、缺陷概率或因果测试债务。本迭代不计算 Precision 或 Recall，也不跑 NetBox 实验。

维护者已接受本迭代。交付分支是 `feat/007-test-collaboration`，交付记录是 [PR #7](https://github.com/Zhang-huanzhi/prisk-system/pull/7)。写下这条提交时，该 PR 尚未合并。本提交只把状态改为 Accepted，不改实现。

## 范围

- 实现 `workflow.test_collaboration_gap`。默认启用。默认权重沿用原来的 `test_collaboration_weight` 1，不把另一分加进 `rule_weights` 合计。结构规则权重和仍是 9，加上这一分，默认可得权重仍是 10。
- 命中时产生一条普通 Finding，并让历史摘要字段 `summary.test_collaboration` 只在这条 Finding 出现时为 true。评分仍用这个字段和原来的权重，不重算已保存的 demo stage05。
- 路径分类、纯删除、纯重命名、仅文档、仅测试、无生产代码、未知路径和缺少行数都有构造测试。已跟踪的 `backend/data/demo/` 用来核对摘要与文件列表不一致时未分析，以及已保存分数不变。
- 更新当前规则卡片、登记册、知识库索引、架构说明和 v1.1 入口。登记册仍不是运行时配置。
- 交付记录是 [PR #7](https://github.com/Zhang-huanzhi/prisk-system/pull/7)，分支 `feat/007-test-collaboration`。本提交只把状态改为 Accepted，不改实现。写下这条提交时该 PR 尚未合并。

## 不做事项

- 不实现 `workflow.large_change_scope`，也不实现 Django/DRF 草稿。
- 不新增按项目配置的路径映射、调用图或阈值表。
- 不把 JSON 登记册改成运行时配置。
- 不提高其他规则的权重，不把默认可得权重改成 11，不改写已保存 demo stage05 的分数或 Finding。
- 不读取 gitignore 的大型 frozen-netbox stage04，不运行 NetBox 实验，不声称经验有效性。
- 不创建 tag，也不在本提交中合并。交付是 [PR #7](https://github.com/Zhang-huanzhi/prisk-system/pull/7)。本记录状态为 Accepted。写下这条提交时该 PR 尚未合并。

## 技术方案

检测器在 `backend/prisk/domain/test_collaboration.py`。`evaluate_rules` 在代码异味之后调用它。stage04 文件记录继续带上 stage03 已有的 `status`、`additions`、`deletions` 和 `binary`，并增加由 hunk 算出的 `diff_lines`。没有这些计数字段的旧 AST 记录不进入文件变更通道。

默认策略 `default_source_and_test_directories`：

- 测试：路径段 `test` 或 `tests`，或 `test_*.py` / `*_test.py`（含 `.pyi`）。这与 `classify_path` 的测试约定相同，覆盖 `backend/tests`。
- 非生产：文档、迁移、生成目录、`static`，以及 settings / configuration 路径。
- 生产：其余 `.py`、`.pyi`、`.js`、`.jsx`、`.ts`、`.tsx`。
- 其余路径为未知。

生产内容变化要求状态是新增、修改或删除，或者重命名/复制同时有大于 0 的新增或删除行数。纯重命名不是内容变化。测试路径上的重命名仍算测试文件变化，因此不触发。全部生产内容变化的新增行数为 0 且删除行数大于 0 时，`change_boundary` 为 `code_removal`。

`summary.unanalyzed` 使用两个已有风格的原因：`diff_stats_unavailable` 和 `path_classification_unavailable`。出现任一条时不产生 Finding，`test_collaboration` 为 false，不把这一分记为命中。规则关闭时，未知路径不写入未分析。

已保存分数的计算方式不变：结构规则权重相加，协作规则的 `rule_weights` 值不重复相加，再按 `test_collaboration_enabled` 和摘要布尔值加上原来的 1 分。demo stage05 仍记录 `test_collaboration: true` 和 `api.signature_changed`，所以 PR 12 的已保存结果仍是 3/10，分数 30。新鲜评估不会把这条已保存结果改写进仓库。

分支报告里的 `test_collaboration_gap` 改为与 Finding 一致。以前它和演示 API 的布尔方向相反。

## 兼容性

- 规则结果仍是 `stage05.v2`。新 Finding 使用原有字段，并带 `impact_type: pr_intrinsic_risk`。证据使用 `node_kind: file`、状态、路径类别和行数。没有 hunk 时不编造行号。
- 运行时目录从 12 条变为 13 条。新规则默认启用，默认权重是原来的 1，不是 0。其他权重不变。默认可得权重仍是 10。
- 登记册里这条规则的阵营改为与卡片一致的 `breaking_impact`，生命周期改为 `implemented`。运行时不加载登记册。
- `rule-metadata.schema.json` 没有新增字段。实现落在现有登记 schema 和 stage05.v2 里。
- v1.0.0 冻结目录和 Accepted 001–006 的迭代记录没有改写。

## 验收

- 生产代码有行数变化且没有测试路径变化时命中，消息写明这不是测试缺失、回归或缺陷结论。
- 同一变更同时改生产和测试时不命中。
- 只删除生产代码时命中，并标记 `code_removal`。
- 生产代码纯重命名不命中。测试路径重命名阻止命中。
- 只改文档、只改测试、只改迁移或配置时不命中。
- 未知路径、缺少行数、二进制生产文件，以及摘要计数和文件列表不一致时进入 `summary.unanalyzed`，不命中。
- 只有 AST、没有文件变更通道的记录不命中，也不记协作分。
- 规则关闭时，未知路径不制造未分析记录。
- 默认 `maximum_points` 仍是 10。已保存 demo PR 12 仍是 3/10，分数 30。

## 实际测试

仓库没有 GitHub Actions。以下是本工作区实际命令，不是 CI，也不是 NetBox、Precision 或 Recall 验证。输入是构造样例和已跟踪的小型 `backend/data/demo/`。没有读取 `backend/data/frozen-netbox/stage04-structure-objects.jsonl`。

本工作区没有 `uv`，系统 Python 是 3.12.3，而 `pyproject.toml` 写的是 `>=3.13`。检测器只用标准库。在 `backend/` 下实际执行的是与文档等价的发现命令：

- `python3 -m unittest discover -s tests -t .`：91 项全部通过，退出码 0。
- `npm --prefix frontend ci`：安装锁定依赖。
- `npm --prefix frontend run lint`：通过。
- `npm --prefix frontend run typecheck`：通过。
- `npm --prefix frontend run build`：通过。
- `git diff --check`：通过。
- `python3 -m prisk.cli.web_cli --port 8765` 后，`/api/dataset` 返回 13 条运行时规则。`workflow.test_collaboration_gap` 默认启用，`default_weight` 为 1。其余规则的默认权重之和为 9。`/api/pr/12` 的已保存结果仍是得分 30、已得 3、可得 10，Finding 仍只有 `api.signature_changed`。这不是把 demo stage05 重算后的新 Finding。

## 遗留风险

- 默认分类不认识 `test_*.py` 以外的其他语言测试文件名。这类路径是未知，整次判断停止，而不是当成已有测试协同。
- `pyproject.toml`、图片和其他未列出的路径也会使整次判断未分析。这是保守边界，不是“没有生产代码”。
- 已保存的 demo stage04 没有文件状态和行数，新鲜评估不会从它产生这条 Finding。demo stage03 的摘要写着有测试文件变化，文件列表里却只有 `src/example.py`，因此未分析。两条都不表示通过。
- 已保存 stage05 的协作布尔值仍来自旧摘要，不是这条检测器重算的结果。不重写该文件时，演示 API 的分数保持原样，目录里能看到新规则，但 PR 12 的已保存 Finding 列表没有它。
- 文献只说明生产和测试会共同演化。它不证明单次变更未改测试就是缺陷。
