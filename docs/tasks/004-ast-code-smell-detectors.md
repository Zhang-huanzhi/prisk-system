---
task_id: "004"
target_version: "v1.1.0"
title: "AST 代码异味检测器"
status: "Accepted"
branch: "feat/004-ast-detectors"
date: "2026-11-05"
---

# 004：AST 代码异味检测器

## 目标

把已登记的 `code.swallowed_exception`、`code.bare_exception` 和 `code.dynamic_execution` 接入现有 AST/Diff 与 Finding 管道，并用构造正例、反例和边界样例检查它们是否按当前规则卡片工作。

这是 Accepted 001–003 的增量继续。规则 ID 使用 003 之后的 `code.*` 名称。检测器只提示复核，不表示缺陷、漏洞、执行已经发生或经验性 Precision/Recall。

## 范围

- 在现有 stage04 访问器上补充异常处理体、直接异常名和直接调用名。
- 在 stage05 `evaluate_rules` 中对 head 侧、已经与新增行相交的节点运行这三条规则。
- 为三条规则补充目录、默认启用状态、权重、前端标签，以及正例、反例、边界和解析失败测试。
- 把卡片、登记册和知识库索引中的生命周期从 `registered` 改为 `implemented`。`implemented` 只表示检测器和构造测试已接入。

## 不做事项

- 不运行 NetBox 实验，不重算冻结 stage05。
- 不实现其余草稿规则，不覆盖 `code.exception_structure_changed` 的原有结构匹配。
- 不把 JSON 登记册改成运行时配置。
- 不检测 `compile`、`except*`、别名、属性调用或只移动代码。这些仍按卡片排除或留待设计。
- 不创建 tag，不合并。本记录状态为 Accepted。

## 技术方案

结构层继续使用 `parse_python_source` 和三点 Diff 的新增行映射。`ExceptHandler` 记录 `handler_type_names`、`handler_body_is_single_pass` 和 `ordinary_handler`。`Call` 只在 `func` 是 `Name` 时记录 `direct_callee_name`。`except*` 的处理分支仍保留为 `except_handler`，但 `ordinary_handler` 为 false，因此三条异味规则不命中。

规则层新增 `backend/prisk/domain/code_smells.py`，由 `evaluate_rules` 调用。触发条件是 head 节点的 `changed_lines` 非空，也就是现有映射已经确认该节点与新增行相交。删除行和未改动节点不触发。同一异常分支可以同时命中静默吞异常和宽泛捕获，但 Finding 分开，消息分别说明处理体和捕获形式。同一分支里的多个宽泛类型只生成一条 `code.bare_exception`。每个直接 `eval` 或 `exec` 调用各生成一条。

旧 stage04 节点没有 `handler_type_names`、`handler_body_is_single_pass` 或 `direct_callee_name` 时，检测器只做有界回退：调用名使用已有 `callee` 文本，标识符视为直接名称，属性或复杂表达式视为非直接调用；异常分支在完整且未截断的 `source_segment` 上按同一 AST 语义还原，包括元组和 `except*`。无法还原的相关节点不生成异味 Finding，文件写入 `summary.unanalyzed`，原因是 `unsupported_stage04_details`，并列出 `node_ids`。这不是通过。对应规则未启用时，不因缺字段把文件标为未分析。

head 解析失败时，该文件进入 `summary.unanalyzed`，`parse_degraded` 仍为 true，并且不为该文件生成异味 Finding。源码无法通过 git show 读取时，沿用现有 stage04/stage05 错误状态，整条记录为 `error`，空 Finding 不是通过。

## 兼容性

- 规则结果仍使用 `stage05.v2`。新 Finding 保留原有 `rule_id`、`severity`、`confidence`、`message`、`evidence` 和 `suggested_action`。`confidence` 仍是 `structural`。
- 可选扩展：Finding 和证据可带 `impact_type: pr_intrinsic_risk`；证据可带 `start_line`、`end_line`、`capture_form`、`callee_name` 或 `handler_body_is_single_pass`。旧消费者可以忽略这些字段。
- 004 的原始异味证据包含代码切片和前后对照。切片来自 stage04 节点的 `source_segment`；没有切片时 `source_status` 为 `unavailable`。`before`/`after` 只携带已有节点切片。没有 base 节点时原因是 `no_base_node`，节点没有切片时原因是 `source_missing`。不编造切片，也不从 stage03 hunk 复制 unified diff 原文，因为 `evaluate_rules` 的输入是 stage04。分支报告和演示报告保留这些标记；节点上另有切片时用它填充，不把已标记为缺失的切片改写成文本。
- `summary.unanalyzed` 是新增字段。`status` 为 `excluded` 或 `error` 时它为空列表，记录状态本身表示未分析。`unsupported_stage04_details` 表示相关节点无法按卡片语义评估。
- 运行时目录从 5 条变为 8 条。三条新规则默认启用，默认权重保持 0。权重调整留给后续实证验证迭代，届时再统一调整分数。因此原有五条规则加测试协同的默认可得权重仍是 10，冻结样本在不重算 Finding 时分数不变。
- 分支报告补充 `domains`，与 003 的前端契约对齐。`scenes` 仍保留；当前 Finding 没有 `scene`，所以该列表为空。
- 登记册中 `code.dynamic_execution` 的问题描述曾写入 `compile`。当前卡片明确排除 `compile`，本迭代按卡片改正该句，检测器不报告 `compile`。

## 验收

- 直接 `eval`/`exec` 命中；`compile`、`ast.literal_eval`、属性调用、别名、字符串和注释不命中。
- 裸 `except`、`Exception` 和 `BaseException` 的消息不同；元组中多个宽泛类型只有一条 Finding。
- 处理体恰好一个 `pass` 才命中静默吞异常；带日志、重新抛出、两个 `pass` 或 `...` 不命中。
- 只有新增行相交的节点命中。未改动处理分支、只改 `try` 行、只删除相关代码不命中。
- 语法错误标记未分析；不可用源码保持错误状态。
- 不声称概率、缺陷确定性、Precision/Recall 或 NetBox 验证。

## 实际测试

仓库没有 GitHub Actions。以下是本工作区实际命令，不是 CI。

- `uv run --project backend python -m unittest discover -s backend/tests -t backend`：60 项，59 项通过，1 项失败，退出码 1。失败项是 `test_web_defaults_use_project_local_demo_data`。该失败在本分支改动之前的 `main` 上同样出现，原因是 `.gitignore` 排除了 `backend/data/frozen-netbox/stage04-structure-objects.jsonl`，当前检出没有这个文件。本迭代没有重算该快照，也不把整套测试说成全部通过。
- `npm --prefix frontend run lint`：通过。
- `npm --prefix frontend run typecheck`：通过。
- `npm --prefix frontend run build`：通过。
- `git diff --check`：通过。
- 用 `backend/data/demo/` 的 stage03/04/05 启动本地 API 后，`/api/dataset` 返回 8 条规则，三条新规则的默认权重为 0 且默认启用。对构造仓库 `main...feature` 的分支分析返回 `domains: ["code"]`，Finding 包含三条异味规则和 `code.exception_structure_changed`，其中动态执行证据只有 `eval`，没有 `compile`。分数为 20，已得权重 2，可得权重 10。
- 用无头 Chrome 打开前端，加载同一仓库并完成 `main → feature` 分析。概览显示“代码结构”且没有页面崩溃；风险规则页显示三条中文规则名，以及 pass、裸捕获和 `eval` 的复核说明；评分配置页列出这三条规则。页面文本没有把 `compile` 显示为直接调用。
- 随后的兼容性与证据修正没有改动默认权重。旧字段加完整切片的构造输入能还原裸 `pass`、元组中的 `BaseException`、`except*` 排除和 `compile` 排除；去掉细节和切片后，相关节点进入 `unsupported_stage04_details`，且不产生异味 Finding。修改过的 `eval` 调用在原始 Finding 中同时带有可用的 before/after 切片；新增文件的 before 标记为 `no_base_node`。演示报告在节点缺失时保留 `unavailable`，不补造切片。

## 遗留风险

- 三条新规则的默认权重保持 0。后续实证验证迭代再统一调整分数，本迭代不把默认可得权重改成 13。
- `except*`、重命名和只移动代码仍待设计。当前删除或未改动代码不触发，但同一节点只要与新增行相交就会按 head 形态报告，即使相似代码在 base 中已经存在。`except*` 只有在 004 字段或完整切片能认出时才排除；认不出时标为未分析，而不是当成普通 `except`。
- 名称遮蔽会按源码名字命中，这是卡片已经写明的限制。
- 构造测试只证明检测器按卡片工作。实证数据集、Precision、Recall 和 NetBox 人工标注都还没有做。
- 冻结 stage04 快照缺失使一条既有 CLI 测试失败。恢复该测试需要本地补齐被忽略的快照，不属于本迭代。
