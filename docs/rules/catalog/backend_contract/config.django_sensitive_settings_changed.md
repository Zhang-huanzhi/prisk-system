# 规则说明卡片：`config.django_sensitive_settings_changed`

> 本卡片是设计记录。样例都是构造样例，不是某个已合并 PR 的复原。生命周期是 `implemented`（021 接入检测器与构造测试）；默认权重 0，不是 `validated`，也没有真实 PR 实证。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `config.django_sensitive_settings_changed` |
| 规则名称 | 敏感配置变化 |
| 版本 | `v1` |
| 规则阵营 | `backend_contract` |
| 生命周期 | `implemented` |
| 负责人 | `Prisk-System` |

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | 同一 Python 文件里，赋值目标名属于下面这份 Django 部署检查清单名单的模块级赋值 |
| 依赖层级 | `framework`。阵营是后端契约。名单来自 Django 文档，不是项目另交的配置政策 |
| 分析目标层 | `ast_syntax`，`diff_delta` |
| 证据呈现形态 | `code_slice`，`symbol_pair` |
| 严重度 | `High` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度是待验证的设计值，不是权重。

## 3. 为什么制定

### 观察到的工程问题

部署检查清单里的设置在 diff 中被改得更宽或不安全。收紧方向，例如 `DEBUG` 从 `True` 改为 `False`，不是同等的回归。

### 为什么值得检测

`SECRET_KEY` 和数据库密码被文档要求保密；`DEBUG` 被要求不要在生产打开；`ALLOWED_HOSTS` 与两个 cookie 安全标志被写进同一份清单。审查者需要看到不安全或放宽的方向。收紧不需要一条 High Hit。

### 现有规则为什么不能覆盖

运行时的 `config.configuration_structure_changed` 按设置文件路径报告结构变化，不指出哪一个设置名。`code.hardcoded_secret` 看的是像秘密的字面量绑定，不覆盖 `DEBUG = False` 这种没有秘密字面量的变更。

### 研究或工程价值

框架适配。名单以已核对的部署检查清单为闭集。清单没点名的项目自定义设置不在本规则里猜。

## 4. 检测定义

### 适用性

模块级简单赋值或带注解赋值，目标是直接名称，且名称属于：

`SECRET_KEY`、`SECRET_KEY_FALLBACKS`、`DEBUG`、`ALLOWED_HOSTS`、`DATABASES`、`CSRF_COOKIE_SECURE`、`SESSION_COOKIE_SECURE`。

这七个名字都出现在已核对的 [部署检查清单](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)。`CACHES`、静态文件和邮件设置也在该页，但该页没有把它们写成与 `SECRET_KEY` 同一句“必须保密”或“禁止在生产打开”。本规则不把它们并进来。

不要求文件名必须是 `settings.py`。不合并拆开的设置包。

### 检测边界

只把不安全或放宽记为 Hit，严重度 `High`。收紧记 NotFound，不是较低严重度的 Hit，也不是一票抬升。方向从赋值切片里读不出来时记 Unanalyzed，不能因为指纹变了就 Hit。不读取环境变量的运行值，不判断生产环境实际启用了哪一份设置。

| 名字 | 不安全或放宽，Hit | 收紧，NotFound | 方向不明，Unanalyzed |
| --- | --- | --- | --- |
| `DEBUG` | head 为常量 `True`，且 base 不是 `True` | 切片显示 `True` 变为 `False` | 不是常量 `True` / `False`，或切片截断 |
| `CSRF_COOKIE_SECURE` | `True` 变为 `False`，或 head 为 `False` 且 base 不是 `False` | `False` 变为 `True` | 同上 |
| `SESSION_COOKIE_SECURE` | 与 `CSRF_COOKIE_SECURE` 相同 | 与 `CSRF_COOKIE_SECURE` 相同 | 同上 |
| `ALLOWED_HOSTS` | head 的列表字面量含 `'*'`，且 base 的可读列表不含 `'*'`，或 base 没有这条赋值 | head 去掉 `'*'`，或从含 `'*'` 的列表字面量变成不含 `'*'` 的列表字面量 | 列表不是字符串字面量、含解包，或来自其他名字 |
| `SECRET_KEY` | head 是非空字符串字面量，且与 base 不同或 base 不是字面量；或 head 删掉了该赋值 | head 从字符串字面量改为非字面量，例如 `os.environ[...]` | 两侧都无法看出是写入字面量还是挪走字面量 |
| `SECRET_KEY_FALLBACKS` | head 新增字符串字面量元素，或从缺失/空变成非空字面量列表 | head 删掉字面量元素，或从非空字面量列表变成空列表或非字面量 | 元素不是可逐个读出的字符串字面量 |
| `DATABASES` | 可读结构里 `PASSWORD` 被写成非空字符串字面量，且 base 的同一位置不是这个字面量 | 同一 `PASSWORD` 从字符串字面量改为非字面量 | 字典不是字面量、键是动态的，或切片截断 |


### 检测对象

与新增行或删除行相交的模块级赋值。

### 触发条件

目标名在名单内，赋值与新增行或删除行相交，并且上一节的方向表给出 Hit。函数体内的同名局部变量不触发。指纹不同但方向表给不出 Hit 或 NotFound 时，是 Unanalyzed。

### 触发特征

- `setting_name`：`source` 为赋值目标的直接名称；`value_type` 为 `string`；`operator` 为 `contains`；`threshold` 为上面七个名字；`required` 为 true。
- `assignment_changed`：`source` 为该赋值与新增或删除行相交，且方向表的 Hit 列成立；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true。

stage04 的 field 节点记录名字和值指纹。字符串值会进入 `literal_binding.literal_text`。布尔值目前是 `literal_kind: non_literal`，没有单独的布尔字段。方向必须从未截断切片读出。读不出时是 Unanalyzed，不是 Hit。

### 不触发条件

名字不在七个之内；只改了注释；同名赋值在函数内部；方向表的收紧列成立，包括 `DEBUG = True` 改为 `DEBUG = False`，以及 `CSRF_COOKIE_SECURE` / `SESSION_COOKIE_SECURE` 从 `False` 改为 `True`。其他文件里的 `os.environ` 读取看不见。

### 输入

同一文件的 base/head AST 和三点 Diff。不读进程环境，不导入设置包。

### Finding

设计线索：规则 ID、设置名、方向是放宽、文件和行、`pr_intrinsic_risk`、严重度 `High`。不展示完整秘密值作为必须字段；字符串证据沿用 `code.hardcoded_secret` 已有的长度和短预览边界。收紧不生成 Finding。021 生成运行时 Finding；默认权重 0。

### 证据位置

文件、赋值目标名、行号、值指纹是否变化。秘密字符串的全文不是必填证据。

### 上下文切片

赋值语句本身。切片若包含长密钥，复核界面仍应按现有秘密规则的预览方式处理；本卡片不新增一种展示全文的要求。

### 影响类型

配置。

### Unanalyzed

设计预期，不是运行结果。

- 名字不在七个闭集里：不记 Hit，也不为本规则记 NotFound。该赋值对该规则是未分析对象，原因 `missing_framework_context`。项目若以后要加入自定义名字，需要单独的项目名单；本任务不写这份名单。
- 赋值目标不是直接名称，例如 `globals()["DEBUG"]`：`unsupported_stage04_details`。
- 切片截断，无法确认目标名：`unsupported_stage04_details`。
- 设置来自其他模块的 `from production import *`：不展开，记 `missing_framework_context`。

### 构造样例

正例：模块级 `DEBUG = False` 改为 `DEBUG = True`。另一个正例：`SECRET_KEY = os.environ["SECRET_KEY"]` 改为 `SECRET_KEY = "dev-only-secret"`。

反例：`DEBUG = True` 改为 `DEBUG = False`，记 NotFound。`SECRET_KEY` 从字符串字面量改为 `os.environ[...]`，记 NotFound。函数里 `def f(): DEBUG = True` 不触发。模块级 `PAGE_SIZE = 50` 改成 `100`，名字不在闭集。

边界：`DATABASES["default"]["PASSWORD"] = "..."` 这种下标赋值不是直接名称赋值。当前字段节点不覆盖下标目标，记 Unanalyzed，不把它漏当成已经检查过的 `DATABASES` 整体。若变化的是 `DATABASES = {...}` 这个直接名称，则按名单命中。

## 5. 理论与项目依据

- [Django 部署检查清单](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/) 把 `SECRET_KEY` 和 `DEBUG` 列为关键设置，并要求密钥不要提交进源码。同一页把 `ALLOWED_HOSTS`、`DATABASES` 的密码、`CSRF_COOKIE_SECURE` 和 `SESSION_COOKIE_SECURE` 列为部署时要核对的设置。`SECRET_KEY_FALLBACKS` 出现在该页的密钥轮换示例里。
- 分项说明：[SECRET_KEY](https://docs.djangoproject.com/en/stable/ref/settings/#secret-key)、[DEBUG](https://docs.djangoproject.com/en/stable/ref/settings/#debug)、[ALLOWED_HOSTS](https://docs.djangoproject.com/en/stable/ref/settings/#allowed-hosts)、[CSRF_COOKIE_SECURE](https://docs.djangoproject.com/en/stable/ref/settings/#csrf-cookie-secure)、[SESSION_COOKIE_SECURE](https://docs.djangoproject.com/en/stable/ref/settings/#session-cookie-secure)。
- 清单还提到可以用 `manage.py check --deploy` 做部署检查。那是 Django 自己的检查命令，不是本规则已经跑过的结果。

## 6. 限制与反例

- 可能误报：开发用设置文件里把 `DEBUG` 改成 `True`，对生产并没有影响。规则不区分文件是不是生产设置。收紧方向不再记成 High Hit。
- 可能漏报：设置在未改动的私有模块里，或通过环境变量在仓库外变化。
- Python 动态特性限制：`locals()`、动态字典和解包赋值。
- 规则不判断：新值是否适合生产、密钥是否已经泄露、cookie 标志在浏览器里是否生效。
- 必须人工复核的上下文：该文件是开发默认还是生产模块。密钥从字面量改成环境变量按方向表是 NotFound，不再用 High Hit 要求这次复核。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `empirical_required` |
| 验证方法 | 构造样例覆盖七个名字、闭集外名字、函数内赋值和下标赋值。不下载真实 PR，也不运行 `check --deploy` |
| 数据集 | 未圈定 |
| 判定依据 | 将来的人工标注。清单只提供名单，不提供本项目的 Precision |
| 指标 | 不预填 |
| 验收标准 | 021 以构造样例验收 |
| 未解决问题 | 布尔方向没有结构化字段，必须读未截断切片；读不出则 Unanalyzed。021 已接入检测器。项目自定义设置名单不存在，本任务不补 |
