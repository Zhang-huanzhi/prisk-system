# 规则说明卡片：`<rule_id>`

> 本卡片同时服务于工程登记和毕业论文写作。没有证据的内容填写“待验证”，不要用推测替代结果。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `<rule_id>` |
| 规则名称 | `<name>` |
| 版本 | `<version>` |
| 规则阵营 | `code_smell` / `backend_contract` / `breaking_impact` |
| 生命周期 | `draft` / `registered` / `implemented` / `validated` / `deprecated` |
| 负责人 | `<owner>` |

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` / `external_impact` |
| 适用范围 | 语言、框架、项目和文件/变更场景 |
| 依赖层级 | `language` / `framework` / `database` / `process`；填写它依赖的技术约束，并说明与规则阵营的关系 |
| 分析目标层 | `ast_syntax` / `diff_delta` / `call_graph` / `change_metadata` |
| 证据呈现形态 | `code_slice` / `symbol_pair` / `metric_value` |
| 严重度 | `Critical` / `High` / `Medium` / `Low` |
| 一票抬升 | `true` / `false` |
| 一票抬升条件 | 触发 Red Flag 的具体机器条件；无则填 `null` |

## 3. 为什么制定

### 观察到的工程问题

描述要检测的具体问题，不写成“存在安全风险”这种结论式表述。

### 为什么值得检测

说明问题的后果、影响对象和人工复核价值。

### 现有规则为什么不能覆盖

指出与现有规则的边界，避免同一问题由多条规则重复表达。

### 研究或工程价值

说明这是文献继承、框架适配、项目约束还是变更规模类通用规则。

## 4. 检测定义

> 推荐采用如下标准化子节进行规范定义。

### 比较单位

说明单次判定的物理或语法比较粒度（例如：一个 Python 文件里的一条 `ast.Assert` 语句，或一个函数签名上的一个参数）。

### 适用性

说明该规则生效的上下文边界、路径策略或类库范围（如框架 ViewSet、迁移文件、或特定路径分类）。

### 闭集

明确进入检测范围的具体标识符、类名、方法名或节点种类的穷举闭集；排除表外名称，不做模糊子串推测。

### 触发条件

可执行、可复核的判定条件（例如：比较单位属于闭集，且其 AST 节点范围与新增行相交）。

### 触发特征

机器可计算的结构化字段。每个字段至少写明 `name`、`source`、`value_type`、`operator`，可选 `threshold` 和 `required`。例如：
- `statement_kind`：`source` 为节点种类；`value_type` 为 `string`；`operator` 为 `eq`；`threshold` 为目标节点名；`required` 为 true。
- `changed_overlap`：`source` 为与新增行交集；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true。

### 不触发条件

明确排除的情况与反例（如测试文件、注释、非相交行、已有安全默认值等）。

### 输入

所需的阶段数据和字段（例如同一文件的 head Python AST、三点 Diff 新增行等）。

### Finding

生成的规则 ID、消息描述、严重度和影响类型；说明是否为复核线索或已确认问题。

### 证据位置

文件路径、节点限定名、调用切片、行号等。

### 上下文切片

人工复核时需要呈现给审查者的代码上下文。

### 影响类型

接口、权限、数据、配置、可维护性或过程协同等。

### 规则终态

说明该规则在三态引擎中的判定边界：
- **Hit**：明确命中触发条件并生成 Finding；
- **NotFound**：上下文适用且完整检查后无风险特征；
- **Unanalyzed**：缺少必要上下文、证据截断或语法降级时的原因（如 `missing_framework_context`、`unsupported_stage04_details`、`context_not_established`）。

### 构造样例

给出构造正例、构造反例与边界样例。

## 5. 理论与项目依据

记录论文、CWE、OWASP、语言/框架官方文档、框架源码约束、项目架构约定、历史漏洞或项目代码依据。引用只说明规则思想有依据，不等于已经证明检测实现没有误报。

## 6. 限制与反例

- 可能误报：
- 可能漏报：
- Python 动态特性限制：
- 规则不判断：
- 必须人工复核的上下文：

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `literature_inherited` / `empirical_required` / `implementation_only` |
| 验证方法 | 构造样例、真实 PR、人工标注、已知案例或组合方法 |
| 数据集 | 数据来源、范围和版本 |
| 判定依据 | 谁或什么作为 Ground Truth |
| 指标 | 例如命中频次、Precision、Recall、覆盖率或排序效果 |
| 验收标准 | 待验证的标准，不预填结果 |
| 未解决问题 | 当前不能由规则回答的问题 |
