---
task_id: "006"
target_version: "v1.1.0"
title: "剩余语言级代码异味"
status: "In Progress"
branch: "feat/006-remaining-code-smells"
date: "2026-11-06"
---

# 006：剩余语言级代码异味

## 目标

在 Accepted 001–005 之上，把卡片里已经写明、005 只登记未实现的两条语言级代码异味接入现有 AST 与三点 Diff Finding 管道：`code.hardcoded_secret` 和 `code.global_mutable_state`。

Finding 只是复核线索。`confidence` 仍是 `structural`。命中不表示秘密已经确认，不表示漏洞，不表示可变状态已经串扰，也不提供 Precision、Recall 或 NetBox 实证。

本记录状态是 In Progress。维护者尚未接受本迭代。

## 范围

- 按 005 卡片实现两条规则。默认启用，默认权重 0。
- 把卡片、登记册和知识库索引中的生命周期从 `registered` 改为 `implemented`。`implemented` 只表示检测器和构造测试已接入。
- 新解析补充绑定和可变状态节点，并让旧快照在切片无法判断时进入 `summary.unanalyzed`，而不是记为通过。
- 运行时目录、前端中文名和证据摘要带上这两条规则。
- 更新 v1.1 迭代索引、架构说明和责任矩阵里的当前描述。

## 不做事项

- 不把本迭代标为 Accepted，不打开 PR，不合并，不创建 tag。
- 不实现 `workflow.test_collaboration_gap`、`workflow.large_change_scope`，也不实现三条 Django/DRF 草稿。
- 不把 JSON 登记册改成运行时配置。
- 不提高其他规则的权重，不提高 `maximum_points`，不重算冻结 stage04/05，不上传被忽略的大型 frozen-netbox JSONL。
- 不放宽 004/005 已经写明的解析失败、源码不可用、`used_as_with_context` 缺失和控制流深度无法判断的边界。
- 不运行 NetBox 实验，不声称经验有效性。

## 技术方案

结构层继续使用 `parse_python_source` 和三点 Diff 的新增行映射。检测仍只看 head 节点里 `changed_lines` 非空的节点。删除行和未改动节点不触发。

现有节点不够表达这两张卡片，所以解析器增加两类只给异味规则使用的节点，并且像 `control_flow` 一样不写入 `structural_changes`。否则新增的赋值或 `global` 会变成 `node_added`，并被既有路径型规则当成结构变化。函数签名字典没有加入默认值文本，因此默认值变化不会单独制造新的 `signature_changed`。同一版本解析出的 base 和 head 都带有 `value_form` 时，这个字段本身不会制造 `field_modified`。

`literal_binding` 覆盖四类绑定：直接名称赋值、属性 `attr` 赋值、调用关键字参数、函数或异步函数的参数默认值。名字表、长度 8 和占位符表仍是卡片常量，比较时整段、大小写不敏感。值必须是单个 `str` 常量。f-string、bytes、名字、调用、比较、只有注解没有值、注释和文档字符串不触发。隐式拼接由解析器折成一个 Constant，实现用值片段里的 STRING token 个数识别：多于一个就不触发。赋值目标只认直接名称和属性 `attr`。解包、下标、增强赋值、海象表达式、lambda 默认值和类关键字不是本规则的绑定。

证据带 `binding_name`、`binding_form`、`value_length` 和前后各两个字符的 `value_preview`。Finding 不另带完整字面量字段。代码切片仍沿用既有 `source_segment`，所以切片本身可能含有该语句的源码。消息写明这是字面量复核，不是秘密已确认，也不是漏洞结论。

`mutable_state` 有两种形式。`global_statement` 只出现在最内层作用域是函数或异步函数的 `global` 语句；模块顶层和类体里的 `global` 不报告，`nonlocal` 不报告。`mutable_binding` 是模块体或类体里的赋值、带值注解赋值，值是列表、字典、集合显示，或没有参数、没有关键字的直接名称 `list()` / `dict()` / `set()`。这包括模块级 `if` 中的赋值，以及函数内部嵌套类的类体。函数体内的同形赋值不触发。一个赋值节点一条 Finding，多个目标放在 `binding_targets`。`global` 不要求随后的值是可变对象。函数默认参数里的可变对象不在本规则内。

旧快照按节点是否还能判断来处理，不把缺节点当成通过：

- 文件里没有 `literal_binding` 时，凭据规则回退到 field 的名字和赋值切片、调用节点的 `keyword_names` 和调用切片，以及没有 `literal_bindings_recorded` 的完整函数切片。函数切片用来恢复函数体内的赋值和默认值，不重复扫描已经由调用节点负责的关键字。
- 字段没有 `value_form` 时，可变状态规则用赋值切片判断值形态。同一赋值跨度只产生一条 Finding。
- 函数没有布尔字段 `contains_global_statement` 时，完整函数切片用来恢复函数体内的 `global`，以及切片里嵌套类的容器绑定。
- 相关切片缺失、被截断或无法解析时，该节点进入 `summary.unanalyzed`，原因是 `unsupported_stage04_details`。这不是通过。对应规则未启用时，不因缺字段把节点标为未分析。
- 丢失了 `binding_form` 的 `name=value` 切片在语法上同时是赋值，回退时按直接名称赋值恢复。关键字形式和参数默认值形式以调用节点、函数切片或仍在的记录字段为准。

005 对直接 `open` 缺少 `used_as_with_context`、控制流深度无法单独证明，以及 head 解析失败的处理保持原样。

## 兼容性

- 规则结果仍使用 `stage05.v2`。新 Finding 使用原有字段，并带 `impact_type: pr_intrinsic_risk`。`confidence` 仍是 `structural`。
- `code.hardcoded_secret` 的证据可带 `binding_name`、`binding_form`、`value_length` 和 `value_preview`。`code.global_mutable_state` 的证据可带 `mutable_state_form`、`binding_targets` 和 `value_kind`。旧消费者可以忽略这些字段。
- 运行时目录从 10 条变为 12 条。两条新规则默认启用，默认权重为 0。原有五条规则的权重和仍是 9，加上测试协同权重 1，默认可得权重仍是 10。已保存的 stage05 不重算，因此既有演示分数不变。
- 登记册仍不是运行时配置。三条 Django/DRF `draft` 契约和两条 `workflow` 草稿不进入 `RULE_CATALOG`。
- v1.0.0 冻结目录和 Accepted 001–005 的迭代记录没有改写。

## 验收

- 卡片中的正例命中：`password = "correct-horse"`、`self.api_key = "ak_live_0123456789"`、`def login(token="tok_0123456789")`、`client.connect(client_secret="cs_0123456789")`。
- 卡片中的反例不命中：`os.getenv`、占位符 `"secret"`、短字符串、非整段名字 `db_password`、普通字符串里的凭据文本。
- 另外不命中：大小写占位符、长度 7、f-string、bytes、隐式拼接、名字引用、比较、只有注解、解包、下标、增强赋值、海象表达式、lambda 默认值、类关键字、注释和文档字符串。长度恰好 8 且不在占位符表中的字符串会命中，包括 8 个空格。这不是熵判断。
- `CACHE = {}`、类体 `items = []`、函数体内 `global CACHE` 命中。`global` 与可变绑定同时出现时 Finding 分开。`left = right = []` 是一条 Finding。
- 不命中：`nonlocal`、函数内 `items = []`、整数、字符串、元组、名字引用、`None`、`cache.append`、`defaultdict`、`deque`、带参数的 `list`、`builtins.list`、推导式、函数默认参数里的列表、模块或类体里的 `global`、只删除绑定。
- 只有与新增行相交的节点命中。未改动节点和只删除的代码不命中。
- 旧 field 或调用切片能判断时按卡片产生 Finding。缺少切片的旧 field，以及截断的旧函数切片，进入 `summary.unanalyzed`。规则关闭时这些缺字段不把节点标为未分析。
- 两条新规则权重为 0。分支报告的 `maximum_points` 仍是 10。
- 三张契约卡片和两条过程草稿仍是 `draft`。运行时目录里没有它们。
- 不声称概率、缺陷、秘密、漏洞、串扰、Precision、Recall 或 NetBox 验证。

## 实际测试

仓库没有 GitHub Actions。以下是本工作区实际命令，不是 CI，也不是 NetBox、Precision 或 Recall 验证。输入是构造样例和已跟踪的小型 `backend/data/demo/`，没有读取被 gitignore 的大型 frozen-netbox stage04。

- `uv run --project backend python -m unittest discover -s backend/tests -t backend`：79 项全部通过，退出码 0。
- `npm --prefix frontend run lint`：通过。
- `npm --prefix frontend run typecheck`：通过。
- `npm --prefix frontend run build`：通过。
- `git diff --check`：通过。
- 用 `backend/data/demo/` 启动本地 API 后，`/api/dataset` 返回 12 条运行时规则。`code.hardcoded_secret` 和 `code.global_mutable_state` 默认权重为 0 且默认启用。十二条规则的默认权重之和为 9。登记册中的 `draft` 规则没有出现在这个目录里。已保存的 stage05 没有重算，演示 PR 的 Finding 仍是原来的 `api.signature_changed`。
- 前端构建产物包含这两条规则的中文名。本工作区没有把评分页点到一次真实分支分析上；页面标签由上述构建和 API 目录核对。样本按钮仍请求 PR 226，而当前已跟踪演示数据只有 PR 12，这个入口不是本迭代改动。

## 遗留风险

- 两条新规则的默认权重保持 0。后续实证验证再统一调整分数。本迭代不把默认可得权重改成 12。
- 名字表和长度 8 会漏掉绑在其他名字上的高熵字符串，也会命中测试夹具和故意写长的假口令。规则不查询密钥库，不做熵检测。
- 直接名称 `list` / `dict` / `set` 会漏掉 `defaultdict`、自定义容器和属性构造。`global` 后只读不写仍会命中该语句。规则不跨文件跟踪名字，不检测数据竞争。
- 006 之前的快照如果没有新节点，又没有完整切片，对应绑定不能被评价。这不是通过。丢失细节的 `name=value` 切片按赋值恢复，关键字和默认值要靠调用节点或函数切片才能保住形式。
- 模块级 `if` 里的容器赋值，以及函数内嵌套类的类体赋值，会按卡片的作用域命中。它们仍只是复核线索。
- 三条 Django/DRF 卡片和两条 `workflow` 草稿没有检测器。007 不在本迭代实现。
- 构造测试只证明检测器按当前卡片工作。实证数据集、Precision、Recall 和 NetBox 人工标注都还没有做。
