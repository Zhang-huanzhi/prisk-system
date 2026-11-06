---
task_id: "002"
target_version: "v1.1.0"
title: "建立规则知识库与首批规则卡片"
status: "Accepted"
branch: "v1.1.0-002-rule-knowledge-base"
date: "2026-11-04"
---

# 002：建立规则知识库与首批规则卡片

> 后续记录：003 已将 `smell.*` ID 迁移为 `code.*`，卡片路径改为 `docs/rules/catalog/code_smell/code.*.md`。004 将这三条规则实现为 `implemented`。005 为另外四条代码异味补了卡片，并把 `code.unmanaged_open` 与 `code.deep_control_flow` 接入同一管道。下文中的旧 ID、旧路径和“尚未实现”保留为当时记录。

## 目标与范围

建立[规则知识库](../rules/README.md)，按 `code_smell`、`backend_contract`、`breaking_impact` 三类阵营组织规则卡片。首批完善三条 Python 语言级代码异味规则，并将两条 PR 级过程信号纳入后续候选。

本任务不实现检测器、不运行 NetBox 实验、不预填验证结果。结构化登记册当前不是运行时配置；规则卡片是设计与验证记录的主要来源。

新增两张过程信号草案：`impact.test_collaboration_gap` 和 `impact.large_change_scope`。它们面向跨语言 PR，但依赖项目的测试路径分类、模块映射和阈值配置；引用共同演化和变更过程研究作为研究动机，不能据此直接判定缺陷或实际外部冲击。两条规则的卡片已建立，相关 JSON 登记册迁移待后续完成。

## 完成内容

### 1. 知识库结构

知识库长期目录位于 `docs/rules/`，迭代目录只保留任务记录：

```text
docs/rules/
├── README.md
├── rule-card-template.md
├── rule-responsibility-matrix.md
└── catalog/
    ├── code_smell/
    ├── backend_contract/
    └── breaking_impact/
```

`README.md` 是规则索引和状态看板；卡片是规则设计与验证记录的主要来源；`backend/data/rules/rule-registry.json` 继续承担结构化索引职责，目前不作为运行时配置。

### 2. 首批已登记卡片

以下三条规则状态为 `registered`，但尚未实现检测器：

- [`smell.swallowed_exception`](../rules/catalog/code_smell/smell.swallowed_exception.md)：处理体只有 `pass` 的异常分支；依据包含 CWE-390、PEP 20、Python 语言参考和异常处理研究。
- [`smell.bare_exception`](../rules/catalog/code_smell/smell.bare_exception.md)：裸 `except`、`Exception` 或 `BaseException` 捕获；依据包含 PEP 8、CWE-396 和 Python 异常层次文档，并区分裸捕获与 `except Exception:` 的语义。
- [`smell.dynamic_execution`](../rules/catalog/code_smell/smell.dynamic_execution.md)：直接调用 `eval` 或 `exec`；依据包含 CWE-95、OWASP A03、Bandit B307/B102 和 Python 官方函数文档。`compile` 已明确排除，因为它本身只编译、不执行。

每张卡片都已写明检测对象、触发与不触发条件、机器特征、输入输出、代码示例、限制、人工复核要求和验证计划。卡片中的 `registered` 只表示登记完成，不表示实现或有效性验证完成。

### 3. 过程信号候选

- [`impact.test_collaboration_gap`](../rules/catalog/breaking_impact/impact.test_collaboration_gap.md)：生产代码变化而同一 PR 没有测试文件变化。已补充纯删除、删除旧测试、外部测试仓库和不完整 Diff 等边界，并计划探索 NetBox 维护者评论与标签的弱监督用途。
- [`impact.large_change_scope`](../rules/catalog/breaking_impact/impact.large_change_scope.md)：按变更行数、文件数和模块数提示大范围复核。已补充 `fixtures/`、`migrations/`、生成文件和格式化噪声的统计边界，要求同时保留原始和过滤后计数。

两条卡片保持 `draft`，不计入已登记卡片数量。

## 文献与依据核验

本任务没有把未核实的论文结论写成事实，依据按“支持范围”记录：

- CWE、PEP、OWASP 和 Bandit 用于说明缺陷分类、语言规范或成熟工具的可比检测规则；它们不证明本项目实现的 Precision/Recall。
- Cabral 与 Marques 的异常处理研究已按 Crossref 核实为 ECOOP 2007 论文集章节，不再使用此前错误的 2009 年份。
- `CWE-391` 已在 MITRE 页面标记为 deprecated，因此只作为历史术语说明，不作为现行主依据。
- 未能可靠核实的 Barbosa 2014、Zhang/MSR 2020 等条目未写入正式依据；Richards 等人的研究是 JavaScript 动态行为研究，未被用作 Python `eval` 注入证据。
- Hassan 的 Change Entropy 和 Zaidman 等人的测试协同研究支持研究动机，但不直接给出本项目的模块阈值、测试缺失真值或缺陷因果结论。

## 验收结果

- 知识库索引、三类目录和两张过程信号草案卡片已建立。
- JSON 登记册中三条首批规则的生命周期为 `registered`，其余候选保持 `draft`；卡片与已登记条目的 ID、阵营和基础分类一致。
- 规则责任矩阵和卡片模板已同步，新增规则仍使用统一字段。
- 登记册与知识库一致性测试：4 项通过。
- JSON 解析检查通过，Markdown 本地链接检查通过，`git diff --check` 通过。
- 未修改现有规则引擎、评分配置或 Finding 运行行为；未运行 NetBox 实证实验。

## 未完成事项

- 三条已登记规则尚未接入 AST/Diff 检测器，尚无正反例单元测试结果。
- 两条过程信号尚未迁移为新的 JSON ID 和分类，阈值、项目路径分类、模块映射仍待确定。
- 文献目前以可核实的书目、官方规范和摘要级结论为主，关键论文仍需阅读全文并在论文中补充规范引用格式。
- 尚未进行 NetBox 人工标注、弱监督标签质量评估、Precision/Recall 或缺陷关联分析。

## 后续任务建议

建议下一任务为 `v1.1.0-003-rule-definition-review`：冻结首批规则的最终 ID 与卡片定义，建立构造样例和规则级测试数据契约，再进入检测器实现。过程信号的阈值和 NetBox 验证应在规则定义冻结后单独安排，避免实现与研究假设同时变化。

