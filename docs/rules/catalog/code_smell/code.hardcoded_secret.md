# 规则说明卡片：`code.hardcoded_secret`

> 本卡片同时服务于工程登记和毕业论文写作。没有证据的内容填写“待验证”，不要用推测替代结果。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.hardcoded_secret` |
| 规则名称 | 硬编码敏感字面量 |
| 版本 | `v1` |
| 规则阵营 | `code_smell` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

登记册 `lifecycle` 也是 `implemented`。006 已接入检测器。这不是 `validated`。名字表、长度 8 和占位符表是卡片常量。命中仍不是秘密已经确认。

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | Python 源文件及其 PR 差异中的字面量绑定 |
| 依赖层级 | `language`。阵营是代码异味；依赖的是绑定名字和字符串字面量，不是 Django 设置项是否变化 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `Medium` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

## 3. 为什么制定

### 观察到的工程问题

口令、令牌或密钥有时会以字符串字面量写在源码里，随后进入仓库历史。

### 为什么值得检测

名字像凭据并且值是较长的字符串时，值得人工看它是不是示例、测试夹具或真实秘密。结构重合不等于已经确认秘密，也不等于存在漏洞。

### 现有规则为什么不能覆盖

[`config.django_sensitive_settings_changed`](../backend_contract/config.django_sensitive_settings_changed.md) 关心 Django 配置项的方向。本规则只关心语言级绑定名字和字符串字面量，不覆盖 `DEBUG = False`。

### 研究或工程价值

文献与 Bandit 规则继承。本规则的名字表、长度 8 和占位符表是卡片自己的常量，不是 Bandit 的配置。

## 4. 检测定义

- **检测对象**：head AST 上的三类绑定。赋值或带值的注解赋值，目标是直接名称或属性的 `attr`；调用的关键字参数名；函数或方法参数的默认值。不扫描任意字符串内容。
- **触发条件**：绑定节点的行范围与新增行相交；名字整段属于下面的集合（大小写不敏感）；值是 `str` 常量，长度大于等于 8，并且不在占位符表中。每个绑定一条 Finding。严重度 `Medium`。
- **触发特征**：`credential_binding_name`（`source` 为绑定名字；`value_type` 为 `string`；`operator` 为 `contains`；`threshold` 为名字集合；`required` 为 true）。`string_literal_value`（`source` 为非空 `str` 常量、长度不少于 8、且不在占位符表；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true）。`binding_changed`（`source` 为行范围与新增行相交；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true）。
- **不触发条件**：`os.getenv`、名字、f-string、隐式拼接、`bytes`；空串和短于 8 的字符串；占位符表中的值；比较表达式；没有默认值的参数；只有注解没有值的赋值；注释和文档字符串。`db_password` 或 `password_changed_at` 与表中名字不相等，不触发。
- **输入**：head Python AST 和三点 Diff 新增行。新解析写入 `literal_binding`。这些节点不进入既有五条规则的 `structural_changes`。
- **Finding**：绑定名、绑定形式、值长度和前后各两个字符的预览，`pr_intrinsic_risk`，严重度 `Medium`。完整字面量不是必须展示的字段。说明这是字面量复核，不是秘密已确认。
- **证据位置**：文件、绑定名、行范围。
- **上下文切片**：该绑定。隐式拼接指值片段里有多于一个 STRING token。
- **影响类型**：可维护性与秘密复核。不是漏洞结论。

名字集合，大小写不敏感，必须整段相等：`password`、`passwd`、`secret`、`token`、`api_key`、`apikey`、`access_key`、`private_key`、`client_secret`、`auth_token`、`secret_key`。

占位符表同样大小写不敏感、整段相等：`password`、`passwd`、`secret`、`token`、`changeme`、`placeholder`、`example`、`xxx`、`redacted`、`todo`、`test`、`dummy`、`none`、`null`、`default`、`fixme`、`sample`、`your-secret`、`your_secret`。

赋值目标只认直接名称和属性 `attr`。解包、下标、增强赋值、海象表达式、lambda 默认值和类关键字不是本规则的绑定。006 之前没有 `literal_binding` 时，才回退到 field 名、调用的 `keyword_names` 和完整函数切片。切片缺失、截断或无法判断时，原因是 `unsupported_stage04_details`。头解析失败时标记未分析，不视作通过。

产生 Finding 时运行终态是 Hit。适用绑定已经分类、没有证据缺口、也没有解析失败时，终态是 NotFound。

触发：`password = "correct-horse"`、`self.api_key = "ak_live_0123456789"`、`def login(token="tok_0123456789")`、`client.connect(client_secret="cs_0123456789")`。

不触发：`password = os.getenv("PASSWORD")`、`password = "secret"`、`token = "short"`、`db_password = "this-name-is-not-exact"`、`note = "token=ak_live_0123456789"`。

## 5. 理论与项目依据

- [CWE-798](https://cwe.mitre.org/data/definitions/798.html) 描述源码或配置中的硬编码凭据。它不表示任意长字符串都是凭据。
- [OWASP A07:2021](https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/) 把认证失败作为背景。它不是 Python AST 规则定义。
- Bandit 的 [B105](https://bandit.readthedocs.io/en/latest/plugins/b105_hardcoded_password_string.html)、[B106](https://bandit.readthedocs.io/en/latest/plugins/b106_hardcoded_password_funcarg.html) 和 [B107](https://bandit.readthedocs.io/en/latest/plugins/b107_hardcoded_password_default.html) 是可比工具规则，不是本项目有效性证明。

## 6. 限制与反例

- 可能误报：测试夹具、示例项目和故意写长的假口令。
- 可能漏报：高熵字符串绑在 `value` 或 `data` 这类名字上；动态拼出来的口令；环境变量；密钥文件路径。
- Python 动态特性限制：解包、下标和 f-string 不在绑定表面里。
- 规则不判断：不查询密钥库，不判断字符串是否可登录，不调用熵检测器。
- 必须人工复核的上下文：绑定名字、字面量是否为示例、文件是业务代码还是测试，以及该值是否已经出现在公开文档中。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `literature_inherited` |
| 验证方法 | 迭代 006 的构造样例覆盖直接名称赋值、属性赋值、关键字参数、函数默认值、大小写、长度 8、占位符表、f-string、bytes、隐式拼接、环境变量和旧切片回退 |
| 数据集 | 006 构造样例 |
| 判定依据 | 本卡片的名字表、长度和占位符表 |
| 指标 | Precision、Recall 和「哪些字面量是真秘密」都不能填写 |
| 验收标准 | 构造样例按卡片常量命中。这不是秘密确认 |
| 未解决问题 | 实证数据集待确定。完整字面量不进入必填证据 |
