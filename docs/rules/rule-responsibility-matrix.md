# 规则责任矩阵

“文献继承类”表示规则思想有可追溯研究依据，不表示检测器实现免于测试，也不免除本项目的阈值或有效性验证。验证义务按具体规则确定，不与规则阵营一一绑定；文献依据仅覆盖其研究对象、方法和结论。

| 规则阵营 | 典型内容 | 论文责任 | 工程验证责任 |
| --- | --- | --- | --- |
| `code_smell`（文献继承类） | 吞异常、动态执行、硬编码凭据、资源未释放、深层控制流 | 说明问题背景，引用 CWE、OWASP、论文或语言文档 | 用正例、反例和边界样例验证 AST/Diff 检测器 |
| `backend_contract`（框架契约类） | DRF 接口和权限、原生 SQL、敏感配置 | 说明框架约束、规则设计和项目语境 | 使用真实 PR、人工标注和已知案例评估存在性、语义准确性和覆盖性 |
| `breaking_impact`（变更冲击类） | 破坏性 Migration、事务边界、大规模变更、测试协同信号 | 说明具体问题、文献依据和特征组合；过程信号不直接断言外部破坏 | 使用真实 PR、人工标注、阈值敏感性和可用案例评估规则；已有研究不替代本项目验证 |
| 历史演示规则（不纳入登记册） | v1.0.0 四条结构规则 | 仅在历史文档中说明其流程演示用途 | 不参与本迭代分类、评分或有效性结论 |

## 验证术语

- **存在性**：规则在真实项目变更中确实能够命中；命中频次不能单独证明有效性；
- **语义准确性**：人工判断 Finding 是否符合规则定义，必要时计算 Precision；
- **已知案例覆盖性**：可靠 Ground Truth 中的案例是否被命中，必要时计算 Recall；
- **工程实现正确性**：构造样例、单元测试和证据可追溯性证明检测器按定义工作。

Precision、Recall、阈值和样本量应在后续验证设计中说明依据，不在登记阶段预填结论。

迭代 004 已为 `code.swallowed_exception`、`code.bare_exception` 和 `code.dynamic_execution` 接入检测器，并用构造样例检查工程实现正确性。迭代 005 用同样方式接入 `code.unmanaged_open` 和 `code.deep_control_flow`，并为 `code.hardcoded_secret`、`code.global_mutable_state` 和三条 Django/DRF 契约写出卡片。迭代 006 把这两条剩余的语言级代码异味接入同一 AST/Diff Finding 管道，并用构造样例检查它们是否按卡片工作。这不产生 Precision、Recall 或 NetBox 实证结论。迭代 007 把 `workflow.test_collaboration_gap` 接入文件变更 Finding，并用构造样例检查路径分类；它仍不产生 Precision、Recall 或 NetBox 实证结论。`workflow.large_change_scope` 仍是 `draft`。011 为当时没有卡片的候选补了设计卡片，并写了结构可行性筛选。013 把 `data.django_raw_sql_execution` 按 011 闭集接入同一 Finding 管道，并用构造样例检查工程实现。默认权重是 0。命中不是注入已经发生，也不产生 Precision、Recall 或 NetBox 实证结论。其余后端契约卡片仍是 `draft`。014 核对了这些 `lifecycle`，没有因为卡片补了比较单位就把 `draft` 改成 `registered` 或 `implemented`，也没有 `validated`。015 只把 `workflow.large_change_scope` 的严重度和风险性质临时对齐为 `High` / `pr_intrinsic`，生命周期仍是 `draft`。这不是终局，也没有检测器。
