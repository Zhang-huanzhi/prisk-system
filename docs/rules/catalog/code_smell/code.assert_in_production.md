# 规则说明卡片：`code.assert_in_production`

> 本卡片是设计记录。样例都是构造样例，不是某个已合并 PR 的复原。生命周期保持 `draft`：没有检测器，也没有运行终态。严重度与风险性质是工程负责人的临时判断，不是终局。登记册没有权重字段；概念上的默认权重是 0，本任务不接入评分。

## 1. 基础信息

| 字段 | 内容 |
| --- | --- |
| 规则 ID | `code.assert_in_production` |
| 规则名称 | 生产代码中的 assert |
| 版本 | `v1` |
| 规则阵营 | `code_smell` |
| 生命周期 | `draft` |
| 负责人 | `Prisk-System` |

## 2. 分类标签

| 字段 | 内容 |
| --- | --- |
| 风险性质 | `pr_intrinsic` |
| 适用范围 | 路径分类为生产代码的 Python 文件中，与新增行相交的 `assert` 语句 |
| 依赖层级 | `language`。阵营是代码异味。路径分类使用已经写在源码里的 `default_source_and_test_directories`，不是一份新的项目政策 |
| 分析目标层 | `ast_syntax`，`diff_delta`，`change_metadata` |
| 证据呈现形态 | `code_slice` |
| 严重度 | `Medium` |
| 一票抬升 | `false` |
| 一票抬升条件 | `null` |

严重度 `Medium` 是临时判断。`assert` 被优化掉之后，权限或业务检查可能不再执行，但语句本身看不出它是不是权限检查。本规则不因此升到 `High`，也不设一票抬升。后续算法阶段可以修订。

## 3. 为什么制定

### 观察到的工程问题

生产路径上的 Python 文件新增 `assert` 语句。解释器在请求优化时不为这条语句生成代码。

### 为什么值得检测

业务检查、认证判断若写在 `assert` 里，会在 `python -O` 下消失。审查者需要看到新增的是语句，而不是测试方法名里的 `assert`。

### 现有规则为什么不能覆盖

现有代码异味看异常处理、动态执行、秘密字面量、打开文件、控制流深度和全局可变状态，不看 `assert`。`workflow.test_collaboration_gap` 只比较生产路径和测试路径有没有一起变化，不读语句。外部 linter 也可能标记 `assert`。那不是本仓库的检测器，也不能当作本规则已经验证。

### 研究或工程价值

语言语句加上本仓库已经版本化的路径分类。不新造「auth 目录」或「业务目录」名单。

## 4. 检测定义

### 比较单位

一个 Python 文件里的一条 `ast.Assert` 语句。比较的是这条语句有没有出现在新增行上，以及该文件的路径类。

### 适用性

路径策略 ID 固定为 `default_source_and_test_directories`，与 `workflow.test_collaboration_gap` 使用的是同一份分类，不另写一份：

- `test`：路径段 `test` 或 `tests`，或文件名 `test_*.py` / `*_test.py`（含 `.pyi`）；
- `non_production`：`doc` / `docs`、`.md` / `.rst`、`migration` / `migrations`、`generated`、`static`，以及 `settings.py`、`configuration*.py` 和 `config` / `settings` / `configuration` 路径段；
- `production`：其余 `.py`、`.pyi`、`.js`、`.jsx`、`.ts`、`.tsx`；
- 其他路径为 `unknown`。

本规则只读 Python AST。路径类即使是 `production`，没有 `.py` 或 `.pyi` 后缀的文件也没有 `assert` 语句对象，不记 Hit。stage03 的 `classify_path` 把 `netbox/` 下的 Python 记为 business，那是另一套分类，本规则不采用。认证与业务代码若落在这份策略的 `production` 类里，就进入比较；本规则不要求路径里出现 `auth`。

当前 stage04 没有 `Assert` 节点种类。函数切片里出现单词 `assert` 也不能当作语句。在节点种类存在之前，不能记 Hit，也不能因为「节点列表里没有 Assert」记 NotFound。

### 闭集

语句节点的种类是 `Assert`。`raise AssertionError`、`self.assertEqual`、`pytest.raises` 和字符串里的 `assert` 都不在闭集里。

### 触发条件

文件的路径类是 `production`，存在 `Assert` 语句，且该语句的行范围与新增行相交。一条语句一条设计 Finding。

### 触发特征

- `statement_kind`：`source` 为语句节点种类；`value_type` 为 `string`；`operator` 为 `eq`；`threshold` 为 `Assert`；`required` 为 true。
- `path_class`：`source` 为 `default_source_and_test_directories` 的分类结果；`value_type` 为 `enum`；`operator` 为 `eq`；`threshold` 为 `production`；`required` 为 true。
- `statement_changed`：`source` 为语句与新增行的交集；`value_type` 为 `boolean`；`operator` 为 `eq`；`threshold` 为 `true`；`required` 为 true。

### 不触发条件

路径类是 `test` 或 `non_production`；`Assert` 语句没有与新增行相交；`raise AssertionError(...)`；测试方法调用。迁移文件在该路径策略里属于 `non_production`，其中的 `assert` 不触发。`settings.py` 同样不触发。

### 输入

同一文件的 head Python AST、三点 Diff 新增行，以及上述路径策略。不读取进程的优化开关，不猜测部署命令。

### Finding

设计线索：规则 ID、路径、路径类、语句切片、设计标签 `pr_intrinsic_risk`。不证明优化已经打开，也不证明检查已经被跳过。本任务不生成 Finding。

### 证据位置

文件路径、路径类、语句行号、语句切片。

### 上下文切片

该 `assert` 语句。不附带整个函数，除非语句本身被截断。

### 影响类型

可维护性。语句在优化编译时不生成代码。

### 设计终态

设计预期，不是运行结果。

- Hit：路径类为 `production`，`Assert` 节点与新增行相交。
- NotFound：路径类是 `test` 或 `non_production`，或者生产 Python 文件已经抽出 `Assert` 节点且没有与新增行相交的语句。
- Unanalyzed：路径类是 `unknown`，原因沿用 `path_classification_unavailable`。文件是 Python 但当前节点没有 `Assert` 种类，或切片截断到无法确认它是语句而不是字符串，原因是 `unsupported_stage04_details`。这两种情况都不记 Hit，也不记 NotFound。

### 构造样例

正例：`app/views.py` 的新增行含有 `assert user.is_authenticated`。路径段不是 `test` 或 `tests`。

反例：`tests/test_views.py` 或 `app/tests/test_views.py` 里的 `assert response.status_code == 200`。另一个反例：`app/views.py` 里的 `raise AssertionError("denied")`，以及 `self.assertTrue(user.is_authenticated)`。

无法分析：路径无法归入 `test`、`non_production` 或 `production`，例如没有后缀的 `scripts/check`。不把单词 `assert` 的文本搜索记成 Hit。

### 与现有规则的去重

测试文件里的 `assert` 留给测试代码本身，不产生本规则的设计 Finding，也不改写 `workflow.test_collaboration_gap`。`code.bare_exception` 与 `code.swallowed_exception` 不因为 `assert` 失败会抛出 `AssertionError` 而覆盖这条语句。

## 5. 理论与项目依据

- [Python `assert` 语句](https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement) 写明：`assert` 等价于在 `__debug__` 为真时检查表达式。当前实现里，请求优化时（命令行选项 `-O`）`__debug__` 为假，代码生成器在编译期不为 `assert` 生成代码。
- 该页没有把这条语句定义成权限检查，也没有列出本仓库的路径类。
- 路径类来自本仓库 `workflow.test_collaboration_gap` 已经使用的 `default_source_and_test_directories`。引用该分类只说明边界已有版本，不说明 `assert` 规则已经实现或已经在 NetBox 上运行。

## 6. 限制与反例

- 可能误报：生产路径上的调试断言、常量检查和永远为真的文档性断言也会命中。命中不表示它承担认证。
- 可能漏报：检查写在 `raise AssertionError` 或普通 `if` 里；`assert` 出现在该路径策略的迁移文件或 `settings.py` 里。
- Python 动态特性限制：`exec` 里的字符串，以及被局部名字遮住的 `__debug__`。规则不判断运行中的 `__debug__`。
- 规则不判断：进程是否以 `-O` 启动，表达式是不是权限或业务不变量，测试是否已经覆盖。
- 必须人工复核的上下文：断言保护的是哪一个条件，以及部署命令会不会打开优化。

## 7. 有效性计划

| 字段 | 内容 |
| --- | --- |
| 验证义务 | `literature_inherited` |
| 验证方法 | 将来的构造样例覆盖生产路径、测试路径、迁移路径、`raise AssertionError` 和截断切片。不启动解释器的优化模式，也不下载真实 PR |
| 数据集 | 未圈定 |
| 判定依据 | 语言文档说明编译期行为。它不是本项目的 Ground Truth |
| 指标 | 不预填 |
| 验收标准 | `Assert` 节点进入结构结果并且构造测试按本卡片工作之前，不能写成 `implemented`。文档写完也不是 `registered` |
| 未解决问题 | 当前没有 `Assert` 节点；认证函数名单不建立；没有检测器，没有实证 |
