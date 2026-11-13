# Prisk v1.4 正式实证评估协议 (`protocol.md`)

## 1. 研究目标与表述边界

1. **实证目标与方法论总纲**：具体的有效性四层边界、三大阵营差异化证明义务及最终选定的 **方案 III 三层混合验证与外部代理体系** 统一由 [`validation-strategy.md`](validation-strategy.md) 与长期架构决策 [`ADR-0001`](../../adr/0001-v14-validation-strategy.md) 裁决固化。按更新后的 [`docs/rules/rule-responsibility-matrix.md`](../../rules/rule-responsibility-matrix.md) 边界，正式统计围绕 **24 条 `implemented` 精细研究规则** 展开；**5 条 `historical_baseline` 演示规则** 已确认剔除出 `v1.4.0` 单规则有效性与新默认校准权重主体，仅随 `legacy_baseline` 预设保留为系统级历史对照（`G1`）。面向外部未参与设计的独立真实 PR 快照与 `analyze_branches` 审查报告，核心观测：
   - 三态分布：`Hit` / `NotFound` / `Unanalyzed` 及其原因码分布；
   - P1 可公开检查规格微基准通过情况、P2 大样本饱和度与高噪聚类模式、以及 P3/P4（强制配对基于变更体积的随机行重叠机会基线）/P5 外部有噪代理对齐表现；
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

## 3. 双轨抽样与双层外部对照设计（`G3a` + `G3b`）

为兼顾一般研发窗口的代表性、稀缺高危场景覆盖与跨仓库适用性边界，正式样本按内部双轨 + 外部双层对照构建（路线选型已由 [`ADR-0001`](../../adr/0001-v14-validation-strategy.md) 确定采用 **方案 III** + 完整启用 `P3/P4`（配对随机行重叠机会基线）/`P5` + 外部对照分拆为 **`G3a`（`saleor/saleor` 非 DRF 退避）** 与 **`G3b`（真实 Django+DRF 迁移，具体仓名由 Task `033` 筛选）**；当前协议中的数量区间仅作草案参考，最终定量采样规模上限待 Task `033` 确立）：

| 轨道标识 (`track`) | 外部子命题 / 目标仓库 | 建议规模（待 `033` 定标） | 抽样机制 | 统计用途 |
| :--- | :--- | :---: | :--- | :--- |
| `track_a_random` | 主仓：`netbox-community/netbox` | **30–40 条**（草案 36，待 `033` 定标） | 按时间窗口 × 改动规模档位（`small <= 5`、`medium 6..20`、`large > 20`）使用固定种子做分层随机抽样；**不看内容挑拣** | 无偏度量 24 条精细规则（及 `legacy_baseline` 对照）自然命中率、`Unanalyzed` 比例与触发分布基线 |
| `track_b_targeted` | 主仓：`netbox-community/netbox` | **10–15 条**（草案 12，待 `033` 定标） | 围绕高危/迁移除外稀缺规则关键词（如 `csrf_exempt`、`permission`、`migrations`、`raw sql` 等）检索已合并 PR，并传入 `--exclude-from` 排除 Track A 已有编号 | 定向检验低频高危检测器在高危与回归场景下的捕获表现与独立 `G2b` `gatekeeper_lift` 边界；**严禁混入 Track A 计算自然命中率** |
| `external_control`（`G3a` 非 DRF 退避对照） | 大型 Django（GraphQL-only 非 DRF / 非 NetBox 基类）：**`saleor/saleor`**（[ADR-0001](../../adr/0001-v14-validation-strategy.md) 选定） | 待 Task `033` 定标（草案 10–15） | 同等分层与 bot 过滤条件抽取（保持 `track = external_control`，按 `repo` 或后续子轨元数据区分）；直接以通用非测试 `.py` 业务分类接入 `analyze_branches` | 检验通用 Python 规则跨仓适用性，以及 DRF 专属规则面对非 DRF / 未登记基类项目时的 `Unanalyzed` 诚实退避能力（**不用于声称 DRF 迁移**） |
| `external_control`（`G3b` DRF 契约迁移对照） | **真实采用 Django + DRF 的同栈开源项目**（具体仓名待 Task `033` 筛选确立） | 待 Task `033` 筛选并定标 | 同等分层与 bot 过滤条件抽取（保持 `track = external_control`，按 `repo` 或后续子轨元数据区分）；直接以通用非测试 `.py` 业务分类接入 `analyze_branches` | 独立检验 11 条 `backend_contract` DRF 契约规则跨仓库迁移能力与自定义 DRF 基类退避边界 |

### 纳入与排除标准

1. **必须满足**：状态为已合并（`is:pr is:merged`）；至少改动 1 个 `.py` 文件；非历史排除编号。
2. **自动排除**：
   - `user.type == "Bot"` 或登录名属于常见自动化账号（如 `dependabot[bot]`、`renovate[bot]`、`pre-commit-ci[bot]`、`github-actions[bot]`）；
   - PR 标题以 `Release ` 开头（不区分大小写，版本发布合并单）；
   - 缺失完整 SHA 或文件列表为空。
3. **随机种子**：默认 `seed = 20261113`，写入抽样 `manifest.json` 保证相同候选池下可复现重抽。

---

## 4. Diff 物化与最新管线执行口径

1. **本地全量克隆模式（主路径）**：使用已签出的本地 Git 仓库，直接面向 PR 对应的 `base...head` 提交快照调用最新动态审查引擎 `analyze_branches`（自动将非测试 `.py` 文件纳入业务分析，产出 `stage08.branch-report.v1` 报告），无需退回 `v1.0.0` `dataset_cli` → `Stage 03–07` 离线串联脚本。
2. **轻量双提交物化模式（无全库克隆备选）**：复用并标准化 `pilot-v1.1` 的轻量化思路，通过 `prisk.services.evaluation_service.materialize_two_commit_repo` 从 `merge_commit^1` 与 `merge_commit` 拉取变更文件构造隔离双提交临时 Git 仓库，校对变更文件数与元数据一致后交由同一 `analyze_branches` 主分析管线执行。
3. **配置溯源与缓存重跑**：在 `analyze_branches`、`AnalysisSnapshotCache` 三级快照局部重跑或后续对齐 `stage08.branch-report.v1` 的 `eval_cli` 对比流程中运行任意预设时，结果均固化 `config.snapshot.v1`（含 **SHA-256 十六进制摘要截断前 16 位 `config_digest`**），确保 `G1`/`G2a`/`G2b` 等单因子消融对比与权重调优完全可追溯。

---

## 5. 治理决策门槛（由 `validation-strategy.md` 定案后在后续执行与校准任务落地）

- **高噪规则候选标记**：遵循 `ADR-0001` 选定的 **方案 III** 验证体系，在 P2 大样本诊断中呈现异常饱和（极端高频但缺乏结合随机基线归一化后的行级/评审区分度）或因固定框架样板稳定触发的规则标为 `high_noise_candidate = true`，提交后续治噪与校准任务（Task `033`）审定是否降权、收敛内部参数或调整默认启用开关（本协议保留的 `annotation-guide.md` 仅作兼容参考，不作为方案 III 必需前置条件）；
- **生命周期晋升**：仅当规则按更新后的[`规则责任矩阵`](../../rules/rule-responsibility-matrix.md)、[`validation-strategy.md`](validation-strategy.md) 与 `ADR-0001` 确立的对应路径获得充分实证支撑且高噪边界受控时，方可在后续校准定案任务中将 `rule-registry.json` 状态由 `implemented` 晋升为 `validated`（`draft` 规则仍不参与线上运行）；
- **方法论定案与定量执行**：先在 Task 032（[`validation-strategy.md`](validation-strategy.md)）完成定性证明路线选型，再由后续执行与校准任务（Task `033`）独立拆分执行 `G0`、`G1`（`legacy_baseline` 历史 10 分兼容回归基线对照）、`G2a`（阈值/权重校准）与 `G2b`（单独开关 Gatekeeper），形成论文正文所需的消融对照与实证结论（且 5 条历史演示规则不进入 `v1.4.0` 单规则有效性统计与新权重校准主体；P3/P4/P5 代理真值噪声边界须随结论一并呈报）。
