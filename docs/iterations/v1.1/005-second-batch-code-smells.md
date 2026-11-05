---
task_id: "005"
target_version: "v1.1.0"
title: "第二批代码异味与 Django 契约卡片"
status: "In Progress"
branch: "feat/005-second-batch-code-smells"
date: "2026-11-05"
---

# 005：第二批代码异味与 Django 契约卡片

## 目标

在 Accepted 001–004 之上补齐第二批语言级代码异味，并写出第一批 Django/DRF 契约设计卡片。四条草稿都要有完整卡片。其中 `code.unmanaged_open` 和 `code.deep_control_flow` 接入 004 的 AST/Diff Finding 管道。另外两条代码异味只登记，不实现。三条后端契约只写设计，不实现。

Finding 只是复核线索。`confidence` 仍是 `structural`。本迭代不声称缺陷、漏洞、资源泄漏、Precision 或 Recall，也不跑 NetBox 实验。

## 范围

- 为 `code.hardcoded_secret`、`code.unmanaged_open`、`code.deep_control_flow`、`code.global_mutable_state` 按卡片模板写完整说明，并同步登记册与知识库索引。
- 前两条中的 `code.hardcoded_secret` 和 `code.global_mutable_state` 生命周期为 `registered`。
- 实现 `code.unmanaged_open` 和 `code.deep_control_flow`，生命周期改为 `implemented`。默认启用，默认权重 0。
- 为 `api.drf_public_parameter_added`、`auth.drf_permission_decorator_removed`、`data.django_raw_sql_execution` 写设计卡片。检测合同仍被项目或框架配置挡住，生命周期保持 `draft`。
- 更新 v1.1 迭代索引、架构说明和责任矩阵里对“只有 004 三条异味在 AST 管道中”的当前描述。004 的迭代记录保持原样。

## 不做事项

- 不实现 `code.hardcoded_secret` 和 `code.global_mutable_state`。
- 不实现三条 Django/DRF 卡片，也不实现其他草稿 ID，包括 `workflow.*`。
- 不把 JSON 登记册改成运行时配置。
- 不提高默认权重，不改变默认可得权重，不重算冻结 stage04/05，不上传被忽略的大 JSONL。
- 不运行 NetBox 实验，不声称经验有效性。
- 不合并，不创建 tag，不打开 pull request。本记录保持 In Progress，由维护者决定何时 Accepted。

## 技术方案

结构层继续使用 `parse_python_source` 和三点 Diff 的新增行映射。检测仍只看 head 节点里 `changed_lines` 非空的节点。删除行和未改动节点不触发。

`Call` 增加 `used_as_with_context`：仅当这个 `Call` 正好是 `with` 或 `async with` 的 `context_expr` 时为 true。`code.unmanaged_open` 只接受直接名称 `open`，与 004 排除属性调用的方式相同。`Path.open`、`io.open` 和 `builtins.open` 不触发。`handle = open(path)` 之后再 `with handle`、`contextlib.closing(open(path))`，以及写在条件表达式里的 `open`，都不是这条规则承认的局部 `with` 模式。旧调用节点若能确定名字是 `open` 但没有布尔字段 `used_as_with_context`，调用切片看不到外层 `with`，该节点进入 `summary.unanalyzed`，原因是 `unsupported_stage04_details`。这不是通过。对应规则未启用时，不因缺字段把节点标为未分析。

控制流节点种类为 `control_flow`。计入深度的语句是 `if`、`for`、`async for`、`while`、`with`、`async with`、`try` 和 `try*`。进入函数、异步函数或类时深度归零。`else`、`finally` 和 `except` 不再加一层。`elif` 是外层 `if` 的 `orelse` 中唯一的 `If`，与该 `if` 共用深度。`match`、推导式、三元表达式和 `assert` 不计入。固定阈值是 `nesting_depth > 4`，常量 `CONTROL_FLOW_DEPTH_THRESHOLD = 4`，不是运行时配置。每个超限且与新增行相交的控制流节点一条 Finding。只改外层条件、而较深节点的行范围没有碰上新增行时，不报告那些较深节点。

这些 `control_flow` 节点不写入 `structural_changes`。否则 `models.py` 里新增的 `if` 会变成 `node_added`，并被既有的路径型数据规则当成结构变化。

旧的 `control_flow` 节点如果已有合法 `control_kind` 和整数 `nesting_depth`，直接使用。没有这些字段时，只有未截断切片自身的深度已经大于 4，才按 `segment_lower_bound` 报告。切片更浅、无法解析或被截断时，节点进入 `unsupported_stage04_details`。005 之前的 stage04 根本没有 `control_flow` 节点；没有节点不等于深度已经不超过 4，需要重新解析后才能评估。

`code.hardcoded_secret` 固定了整段匹配的名字表、长度 8 和占位符表，覆盖赋值、属性赋值、关键字参数和函数默认值。`code.global_mutable_state` 固定了两种形式：函数体内的 `global`，以及模块或类体里的列表、字典、集合或无参 `list` / `dict` / `set`。两条都没有检测器。

三条契约卡片保持 `draft` 的原因：

- 公有必填参数需要路由到 callable 的映射，以及尚未冻结的 DRF 字段 `required` 默认表。`partial=True` 也不能从现有 stage04 可靠读出。
- 权限装饰器删除需要冻结 DRF、Django 和 NetBox 封装的名单，并决定换成类属性时是否抑制。`AllowAny` 和空列表仍留给 `auth.drf_permission_policy_downgrade`。
- 原生 SQL 需要冻结属性调用名单，以及迁移目录是排除、纳入还是单独标记。路径政策缺失时不能默认通过，也不能默认忽略迁移。

## 兼容性

- 规则结果仍使用 `stage05.v2`。新 Finding 使用原有字段，并带 `impact_type: pr_intrinsic_risk`。`confidence` 仍是 `structural`。
- `code.unmanaged_open` 的证据可带 `callee_name: "open"` 和 `used_as_with_context: false`。`code.deep_control_flow` 的证据可带 `control_kind`、`nesting_depth`、`depth_threshold: 4` 和 `nesting_depth_basis`。旧消费者可以忽略这些字段。
- 运行时目录从 8 条变为 10 条。两条新规则默认启用，默认权重为 0。原有五条规则的权重和仍是 9，加上测试协同权重 1，默认可得权重仍是 10。冻结样本在不重算 Finding 时分数不变。
- 登记册仍不是运行时配置。`code.hardcoded_secret`、`code.global_mutable_state` 和三条 `draft` 契约不进入 `RULE_CATALOG`。
- 新解析出的 `Call` 都带有 `used_as_with_context`。同一版本的 base 和 head 一起解析时，这个字段不会单独制造 `call_touched`。控制流节点不进入粗粒度结构变化列表。

## 验收

- 直接 `open(...)` 在赋值、链式调用、`(open)(...)`、遮蔽名、内层调用、`closing` 和条件上下文中命中。`with` / `async with` 的上下文表达式，以及 `Path.open`、`io.open`、`path.open()`、`builtins.open` 不命中。
- 深度大于 4 的 `if`、`for`、`while`、`with`、`try` 和对应异步语句命中。深度 4、长 `elif`、函数内重置、`match`、推导式和三元表达式不命中。
- 只有与新增行相交的节点命中。未改动节点和只删除的代码不命中。只改外层条件不报告未相交的内层节点。
- 缺少 `used_as_with_context` 的直接 `open`，以及切片深度不能单独证明超过 4 的旧控制流节点，进入 `summary.unanalyzed`，不产生对应 Finding。
- 两条新规则权重为 0。分支报告的 `maximum_points` 仍是 10。
- 三张契约卡片仍是 `draft`，运行时目录里没有它们。
- 不声称概率、缺陷、泄漏、Precision、Recall 或 NetBox 验证。

## 实际测试

仓库没有 GitHub Actions。以下是本工作区实际命令，不是 CI。

- `uv run --project backend python -m unittest discover -s backend/tests -t backend`：71 项，70 项通过，1 项失败，退出码 1。失败项是 `test_web_defaults_use_project_local_demo_data`。该失败在本分支改动之前的 `main` 上同样出现，原因是 `.gitignore` 排除了 `backend/data/frozen-netbox/stage04-structure-objects.jsonl`，当前检出没有这个文件。`stage03` 和 `stage05` 两个冻结文件存在。本迭代没有重算该快照，也不把整套测试说成全部通过。
- 新增和既有代码异味测试、结构测试、目录测试和登记册一致性测试包含在上述 70 项通过结果中。其中 `SecondBatchCodeSmellTests` 覆盖两条新规则的正例、反例、新增行、删除和旧节点未分析。
- `npm --prefix frontend run lint`：通过。
- `npm --prefix frontend run typecheck`：通过。
- `npm --prefix frontend run build`：通过。
- `git diff --check`：通过。
- 用 `backend/data/demo/` 的 stage03/04/05 启动本地 API 后，`/api/dataset` 返回 10 条运行时规则。`code.unmanaged_open` 和 `code.deep_control_flow` 默认权重为 0 且默认启用。十条规则的默认权重之和为 9。登记册中的 `registered` 和 `draft` 规则没有出现在这个目录里。
- 评分页上的两条中文规则名已写入前端标签，并由 lint、typecheck 和 build 检查。本工作区没有把一次冻结 PR 点进评分页做浏览器点击；页面行为以上述构建和 API 目录为准。

## 遗留风险

- 两条新规则的默认权重保持 0。后续实证验证再统一调整分数。本迭代不把默认可得权重改成 12。
- 直接名称 `open` 会漏掉 `io.open` 和 `Path.open`，也会把稍后手动关闭的调用报出来。这是卡片上的边界，不是泄漏证明。
- 深度阈值 4 没有用 NetBox 校准。`elif` 与单独的 `else: if` 在 AST 中相同，可能少算一层。`match` 本身不计入。
- 005 之前的 stage04 没有控制流节点。不重新解析时，本规则不能把“没有节点”当成深度合格。
- `code.hardcoded_secret` 和 `code.global_mutable_state` 还没有检测器，名字表和两种可变状态形式也还没有构造测试。
- 三条 Django/DRF 卡片不能实现，直到路由映射、装饰器名单和迁移路径政策被单独接受。
- 冻结 stage04 快照缺失使一条既有 CLI 测试失败。恢复该测试需要本地补齐被忽略的快照，不属于本迭代。
