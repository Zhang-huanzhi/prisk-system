# 硬编码敏感字面量

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.hardcoded_secret` |
| 版本 / 阵营 / 生命周期 | `v1` / `code_smell` / `implemented` |
| 负责人 | `Prisk-System` |
| 风险性质 / 依赖层级 | `pr_intrinsic` / `language` |
| 适用范围 | Python 源文件及其 PR 差异 |
| 分析目标层 / 证据形态 | `ast_syntax`, `diff_delta` / `code_slice`, `symbol_pair` |
| 严重度 / 一票抬升 | `Medium` / `false`，条件 `null` |

## 制定理由

口令、令牌或密钥有时会以字符串字面量写在源码里，随后进入仓库历史。名字像凭据并且值是较长的字符串，值得人工看它是不是示例、测试夹具或真实秘密。结构重合不等于已经确认秘密，也不等于存在漏洞。

本规则不代替 `config.django_sensitive_settings_changed`。那条草稿关心 Django 配置项是否变化；本规则只关心语言级绑定名字和字符串字面量。迭代 006 按本卡片接入检测器。命中仍是字面量复核，不是秘密已确认，也不是漏洞结论。

## 检测定义

- 对象：head AST 上的三类绑定。赋值或带值的注解赋值，目标是直接名称，或属性的 `attr`；调用的关键字参数名；函数或方法参数的默认值。只看这些位置上的名字，不扫描任意字符串内容。
- 名字集合，大小写不敏感，必须整段相等：`password`、`passwd`、`secret`、`token`、`api_key`、`apikey`、`access_key`、`private_key`、`client_secret`、`auth_token`、`secret_key`。`db_password` 或 `password_changed_at` 不相等，不触发。
- 值必须是 `str` 常量，长度大于等于 8，并且不在占位符表中。占位符表同样大小写不敏感、整段相等：`password`、`passwd`、`secret`、`token`、`changeme`、`placeholder`、`example`、`xxx`、`redacted`、`todo`、`test`、`dummy`、`none`、`null`、`default`、`fixme`、`sample`、`your-secret`、`your_secret`。长度和下表都是卡片常量，不是运行时配置。
- 触发：绑定节点的行范围与新增行相交，名字命中，且值满足上一行。每个绑定一条复核 Finding，证据带上名字、值的长度和绑定形式，不把完整字面量当作必须展示的秘密材料；实现时可以只保留长度和前后各两个字符的预览，这个展示选择留到实现迭代。
- 不触发：`os.getenv`、名字、f-string、隐式拼接、`bytes`；空串和短于 8 的字符串；占位符表中的值；比较表达式；没有默认值的参数；只有注解没有值的赋值；注释和文档字符串。头解析失败时标记未分析，不视作通过。
- 特征：`credential_binding_name`（绑定名字，`contains` 上述名字集合）；`string_literal_value`（非空 `str` 常量、长度 `gte 8`、且不在占位符表，布尔值，`eq true`）；`binding_changed`（行范围与新增行相交，布尔值，`eq true`）。
- 输入与证据：head Python AST 和三点 Diff 新增行。影响类型设计为 `pr_intrinsic_risk`。Finding 应说明这是字面量复核，不是秘密已确认。
- 实现：新解析写入 `literal_binding`，记录绑定名、绑定形式和字面量种类。这些节点不进入既有五条规则的 `structural_changes`。证据带绑定名、绑定形式、值长度和前后各两个字符的预览；完整字面量不是必须展示的字段。代码切片仍沿用既有 `source_segment`。隐式拼接指值片段里有多于一个 STRING token。赋值目标只认直接名称和属性 `attr`；解包、下标、增强赋值、海象表达式、lambda 默认值和类关键字不是本规则的绑定。006 之前没有 `literal_binding` 时，才回退到 field 名、调用的 `keyword_names` 和完整函数切片。切片缺失、截断或无法判断时，该节点进入 `summary.unanalyzed`，原因是 `unsupported_stage04_details`。这不是通过。

触发：

```python
password = "correct-horse"
self.api_key = "ak_live_0123456789"
def login(token="tok_0123456789"):
    client.connect(client_secret="cs_0123456789")
```

不触发：

```python
password = os.getenv("PASSWORD")
password = "secret"
token = "short"
db_password = "this-name-is-not-exact"
note = "token=ak_live_0123456789"
```

## 依据

- [CWE-798 Use of Hard-coded Credentials](https://cwe.mitre.org/data/definitions/798.html) 描述源码或配置中的硬编码凭据。它不表示任意长字符串都是凭据。
- [OWASP Top 10:2021 A07 Identification and Authentication Failures](https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/) 把默认口令、弱口令等认证失败作为背景。它不是 Python AST 规则定义。
- Bandit 的 [B105](https://bandit.readthedocs.io/en/latest/plugins/b105_hardcoded_password_string.html)、[B106](https://bandit.readthedocs.io/en/latest/plugins/b106_hardcoded_password_funcarg.html) 和 [B107](https://bandit.readthedocs.io/en/latest/plugins/b107_hardcoded_password_default.html) 分别看字符串、函数参数和默认值。它们是可比工具规则，不是本项目有效性证明。本规则的名字表、长度 8 和占位符表是卡片自己的常量。

## 限制与反例

测试夹具、示例项目和故意写长的假口令会命中。高熵字符串如果绑在 `value` 或 `data` 这类名字上会漏报。动态拼出来的口令、环境变量和密钥文件路径也会漏报。规则不查询密钥库，不判断字符串是否可登录，不调用熵检测器。

人工复核要看绑定名字、字面量是否为示例、文件是业务代码还是测试，以及该值是否已经出现在公开文档中。

## 014 登记字段

登记册和卡片表格的 `lifecycle` 都是 `implemented`。006 已接入检测器，并用构造样例检查过。这不是 `validated`。014 不改名字表、长度 8 和占位符表，也不改这个字段。

比较单位是 head 上与新增行相交的字面量绑定：名字整段属于凭据表，值是长度不少于 8 且不在占位符表中的 `str`。产生 Finding 时运行终态是 Hit。适用绑定已经分类、没有证据缺口、也没有解析失败时，终态是 NotFound。切片缺失或截断是 `unsupported_stage04_details`。这些终态不是另一个生命周期字段。命中仍不是秘密已经确认。

## 有效性计划

`literature_inherited`：迭代 006 已按本卡片检查直接名称赋值、属性赋值、关键字参数、函数默认值、大小写、长度 8、占位符表、f-string、bytes、隐式拼接、环境变量、名字引用、比较、只有注解、解包、lambda、类关键字、新增行、删除，以及旧 field、调用和函数切片。这些构造测试只证明检测器按定义工作。Precision、Recall 和“哪些字面量是真秘密”都不能填写。
