# Prisk v1.4 正式实证评估协议 (`protocol.md`)

## 1. 研究目标与表述边界

1. **实证目标**：在未曾参与规则设计、调参与先导试点的独立真实 PR 样本上，定量观测 Prisk 当前 **29 条运行时规则**（5 条历史结构规则 + 24 条精细规则）在真实研发场景中的：
   - 三态分布：`Hit` / `NotFound` / `Unanalyzed` 及其原因码分布；
   - 结构定义核验精度（Empirical Precision）与固定误报噪声模式；
   - 2 条 Gatekeeper 规则（`data.django_destructive_migration`、`auth.drf_permission_policy_downgrade`）的抬升触发率与合理性；
   - 多套配置预设（`legacy_baseline`、`balanced`、`security_focus`、`framework_upgrade`、`daily_review`）的分值区分度与可复现快照（`config.snapshot.v1`）。
2. **明确不主张的边界**：
   - 规则命中（`Hit`）表示结构化复核信号成立，**不直接等价于线上缺陷或漏洞已触发**；
   - PR 风险分与 `Low / Medium / High` 表示**启发式复核优先级**，不是校准后的缺陷概率估计；
   - 已冻结的 `v1.0.0` 调研集（120 PR）与 [`pilot-v1.1`](../pilot-v1.1/protocol.md) 先导集（16 PR）只用于开发与调参摸底，严禁混入 `v1.4.0` 正式实证分母。

---

## 2. 物理隔离红线（136 条永久排除清单）

- **来源 1**：`docs/versions/v1.0.0/02-PR采样&定风险场景/artifacts/netbox-survey.jsonl` —— **120** 个 `netbox-community/netbox` PR；
- **来源 2**：[`docs/evaluation/pilot-v1.1/manifest.json`](../pilot-v1.1/manifest.json) —— **16** 个 `netbox-community/netbox` PR；
- **合并导出**：[`exclusion-list.json`](exclusion-list.json) —— **136** 个不重复 PR 编号（两源交集为空），附带 LF 归一化 UTF-8 SHA-256 校验指纹；
- **强制门禁**：任何正式数据集候选文件入库或进入汇总统计前，均须通过 `eval_cli check-isolation` 校验，要求：
  1. `(repo, pr_number)` 与 136 条排除清单交集严格为空；
  2. 数据集内部无重复 PR 编号（含跨轨道去重，Track A 与 Track B 不得重复纳入同一 PR）；
  3. 每条记录包含合法 40 位十六进制 `base_sha`/`head_sha` 或 `merge_commit_sha`；
  4. `track` 属于 `track_a_random`、`track_b_targeted`、`external_control` 三者之一。

---

## 3. 双轨抽样与外部对照设计

结合 `development-roadmap.md` 风险 #1（单人精细核验每 PR 均摊约 8.4 分钟的工时上限）与风险 #3（稀缺高危规则在纯随机窗口中易零命中），正式集按三条严格分列统计的轨道构建：

| 轨道标识 (`track`) | 目标仓库 | 建议规模 | 抽样机制 | 统计用途 |
| :--- | :--- | :---: | :--- | :--- |
| `track_a_random` | `netbox-community/netbox` | **30–40 条**（默认 36） | 按时间窗口 × 改动规模档位（`small <= 5`、`medium 6..20`、`large > 20`）使用固定种子做分层随机抽样；**不看内容挑拣** | 无偏度量 29 规则自然命中率、`Unanalyzed` 比例与噪声基线 |
| `track_b_targeted` | `netbox-community/netbox` | **10–15 条**（默认 12） | 围绕高危/迁移除外稀缺规则关键词（如 `csrf_exempt`、`permission`、`migrations`、`raw sql` 等）检索已合并 PR，并传入 `--exclude-from` 排除 Track A 已有编号 | 定向检验低频高危检测器的真实 Precision 与边界；**严禁混入 Track A 计算自然命中率** |
| `external_control` | 外部 Django/DRF 项目（如 `saleor/saleor`） | **10–15 条**（默认 12） | 同等分层与 bot 过滤条件抽取；以 `--path-mode generic --repo-name <repo>` 运行 Stage 03 | 检验未登记框架基类项目的 `Unanalyzed` 诚实收口能力与通用 Python 规则跨仓库适用性 |

### 纳入与排除标准

1. **必须满足**：状态为已合并（`is:pr is:merged`）；至少改动 1 个 `.py` 文件；非历史排除编号。
2. **自动排除**：
   - `user.type == "Bot"` 或登录名属于常见自动化账号（如 `dependabot[bot]`、`renovate[bot]`、`pre-commit-ci[bot]`、`github-actions[bot]`）；
   - PR 标题以 `Release ` 开头（不区分大小写，版本发布合并单）；
   - 缺失完整 SHA 或文件列表为空。
3. **随机种子**：默认 `seed = 20261113`，写入抽样 `manifest.json` 保证相同候选池下可复现重抽。

---

## 4. Diff 物化与管线执行口径

1. **本地全量克隆模式（主路径）**：使用已签出的本地 Git 仓库，通过 `prisk.cli.dataset_cli`（主仓库用默认 `--path-mode netbox`，外部对照库用 `--path-mode generic --repo-name <owner/repo>`）接入 Stage 03 → 04 → 05 → 07。
2. **轻量双提交物化模式（无全库克隆备选）**：复用并标准化 `pilot-v1.1` 的轻量化思路，通过 `prisk.services.evaluation_service.materialize_two_commit_repo` 从 `merge_commit^1` 与 `merge_commit` 拉取变更文件构造隔离双提交临时 Git 仓库，并校对变更文件数与元数据一致后再运行同一分析管线。
3. **阶段配置溯源**：在 `rules_cli`、`scoring_cli` 或 `eval_cli compare-presets` 中运行非默认基线预设时，结果清单强制写入 `config.snapshot.v1`（含 16 位十六进制 SHA-256 摘要 `config_digest`），确保后续权重对比表可追溯。

---

## 5. 治理决策门槛（供后续 Task 033–034 使用）

- **高噪规则候选标记**：在可判定样本（`tp_hit + fp_noise >= 3`）中，`empirical_precision < 0.50` 或由固定框架样板稳定触发误报的规则自动标为 `high_noise_candidate = true`，提交 Task 033 审定是否降权、收敛 AST 条件或调整默认启用开关；
- **生命周期晋升**：仅当规则在正式实证集中验证具备有效可解释命中且高噪边界受控时，方可在 Task 033 将 `rule-registry.json` 状态由 `implemented` 晋升为 `validated`（`draft` 规则仍不参与线上运行）；
- **权重校准**：Task 034 在完整对比 `legacy_baseline`（历史 10 分兼容回归基线）与其他预设的基础上，形成论文正文所需的实证基线权重与消融对照表。
