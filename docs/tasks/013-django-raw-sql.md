---
task_id: "013"
target_version: "v1.2.0"
title: "Django 原生 SQL 执行"
status: "In Progress"
branch: "feat/013-django-raw-sql"
date: "2026-11-07"
---

# 013：Django 原生 SQL 执行

## 目标

在 Accepted 012 之上，把 `data.django_raw_sql_execution` 按 011 补强的闭集接入运行时。命中只标记“出现了原生 SQL 调用形态”。它不是已经证实的注入，也不是迁移里的 SQL 一定不该出现。

闭集只包括调用节点已经能提供的名字：

- `direct_callee_name` 为 `RawSQL`；
- `callee` 的最后一段是 `execute`、`executemany` 或 `raw`。

调用必须与新增行相交，沿用其他 AST 检测器的交集。每个匹配调用一条 Finding。证据写完整 `callee` 和路径。判定不截取 SQL 字符串。

本任务保持 In Progress。交付分支是 `feat/013-django-raw-sql`。评审记录是 [PR #13](https://github.com/Zhang-huanzhi/prisk-system/pull/13)。写下这条记录时该 PR 尚未合并。协调者接受之前不写成 Accepted，不合并，不删除分支，也不开始 014。

## 编号核对

012 已说明下一个未使用编号是 013。v1.2 是推进大纲里的核心规则实现阶段，不是已冻结版本。本任务不建立 `docs/versions/v1.2/`，也不改 `docs/blueprint.md`。

## 范围

- 实现 `data.django_raw_sql_execution`。默认启用。默认权重是 0。运行时目录从 13 条变为 14 条。默认可得权重仍是 10。
- `extra`、`callproc`，以及 `callee` 含 `schema_editor` 时记 Unanalyzed，原因是 `missing_framework_context`。
- 空 `callee`，或切片被截断到不能确认最后一段时，记 `unsupported_stage04_details`。
- 适用调用已经分类且没有上述缺口时记 NotFound。没有相交调用时沿用 009，记 `context_not_established`。
- 迁移文件和视图文件使用同一闭集。路径只留在证据里。
- 更新当前规则卡片、登记册、知识库索引、架构说明、活动任务索引和 v1.1 入口。登记册仍不是运行时配置。卡片生命周期改为 `implemented`。这不表示实证验证。

## 不做事项

- 不实现 `api.drf_public_parameter_added` 或其他草稿卡片。
- 不把 `migrations.RunSQL` 放进 Hit 闭集。
- 不发明迁移路径的纳入或排除政策。
- 不为 `run = cursor.execute` 这类别名做数据流。
- 不提高其他规则的权重，不把默认可得权重改成 11，不改写已保存 demo stage05 的分数或 Finding。
- 不把 JSON 登记册改成运行时配置。
- 不改先导试点的 16 条排除集，不改 v1.4 排除名单，不重计 011 的 8 / 10 / 2 分类。
- 不读取大型 frozen-netbox stage04，不运行 NetBox 实验，不报告 Precision、Recall 或经验有效性。
- 不改写冻结的 v1.0.0，不改写 `docs/blueprint.md`。
- 不合并，不打 tag，不删除分支，不开始 014。

## 技术方案

检测器在 `backend/prisk/domain/django_raw_sql.py`。`evaluate_rules` 在代码异味之后调用它，并把它放进 `RULE_CATALOG`。终态仍是 `stage05.v2` 的 `rule_outcomes`。登记册不参与这次调用。

新增行交集使用 head call 节点上已有的 `changed_lines`。这与代码异味检测器相同：没有交集的调用不检查。

分类顺序：

1. `callee` 为空，或最后一段不能确认：`unsupported_stage04_details`。
2. `callee` 文本包含 `schema_editor`，或最后一段是 `extra`、`callproc`：`missing_framework_context`。因此 `schema_editor.execute` 不是 Hit。
3. `direct_callee_name` 为 `RawSQL`，或最后一段是 `execute`、`executemany`、`raw`：一条 Finding。证据里的 `callee` 是完整调用名。
4. 其余已分类调用，例如 ORM 的 `filter`、`exclude`、`update`，以及 `migrations.RunSQL`：算作已检查，不是 Hit。

已经产出 Finding 时终态是 Hit。其他调用上的缺口仍留在 `summary.unanalyzed`。同一路径、同一原因的未分析条目合并成一行，避免和代码异味对同一次读不出的调用各写一条。

默认权重写在 `DEFAULT_CONFIG["rule_weights"]`，值是 0。评分仍只加 Finding 上的权值和原来的测试协同分。0 不增加已得分数，也不增加可得分数。

## 兼容性

- 规则结果仍是 `stage05.v2`。新 Finding 使用原有字段，并带 `impact_type: pr_intrinsic_risk`。证据包含路径、完整 `callee` 和调用切片。不另存 SQL 文本字段，也不用 SQL 内容决定命中。
- 运行时目录从 13 条变为 14 条。新规则默认启用，默认权重是 0。其他权重不变。默认可得权重仍是 10。
- 登记册里这条规则的生命周期改为 `implemented`。名称仍是「绕过 ORM 的原生 SQL」。运行时不加载登记册。
- 已保存 demo PR 12 仍是 3/10，分数 30，Finding 仍只有 `api.signature_changed`。终态仍是 `unavailable`。
- v1.0.0 冻结目录、先导试点记录和 Accepted 001–012 的历史句子没有改写。

## 验收

- 新增行上的 `cursor.execute` 命中，证据里的 `callee` 是 `cursor.execute`，路径被保留。消息不引用 SQL 字符串。
- 未改动的历史 `cursor.execute` 不命中。新增的 ORM `filter` 在适用调用已检查时是 NotFound。
- `filter`、`exclude`、`update` 不命中。只有 SQL 字符串、没有相交调用时是 `context_not_established`。
- `QuerySet.extra`、`callproc` 和 `schema_editor.execute` 是 Unanalyzed，原因是 `missing_framework_context`。
- 迁移文件里的 `cursor.execute` 与视图文件里的同形调用都命中，路径留在证据里。
- `executemany`、`Manager.raw()` 和直接名称 `RawSQL` 各一条 Finding。
- `migrations.RunSQL`、`run = cursor.execute` 之后的 `run(...)`，以及 `expressions.RawSQL` 不命中。
- `report.execute` 命中，证据保留 `report.execute`。
- 空 `callee` 和截断切片是 `unsupported_stage04_details`。
- 默认 `maximum_points` 仍是 10。已保存 demo PR 12 仍是 3/10，分数 30。新规则权重是 0。

## 实际测试

仓库没有 GitHub Actions，也没有 `uv`。系统 Python 是 3.12.3，项目声明是 `requires-python >=3.12`。以下是本工作区实际命令，不是 CI，也不是 NetBox、Precision 或 Recall 验证。输入是构造样例和已跟踪的小型 `backend/data/demo/`。没有读取 `backend/data/frozen-netbox/stage04-structure-objects.jsonl`。

在 `backend/` 下：

- `python3 -m unittest discover -s tests -t .`：110 项全部通过，退出码 0。其中 `tests.domain.test_django_raw_sql` 有 13 项，覆盖新增行上的 `cursor.execute`、未改动的历史 `execute`、ORM `filter` / `exclude` / `update`、`QuerySet.extra`、迁移路径、`RunSQL`、别名和空 `callee`。

在 `frontend/` 下：

- `npm ci`：安装锁定依赖。Node 是 v22.23.4，npm 是 10.9.9。
- `npm run lint`：通过。
- `npm run typecheck`：通过。
- `npm run build`：通过。
- `git diff --check`：通过。

`python3 -m prisk.cli.web_cli --port 8765` 后，`/api/dataset` 返回 14 条运行时规则。`data.django_raw_sql_execution` 默认启用，`default_weight` 为 0。除测试协同以外的默认权重之和仍是 9。`/api/pr/12` 的已保存结果仍是得分 30、已得 3、可得 10，Finding 仍只有 `api.signature_changed`，`rule_outcome_availability` 仍是 `unavailable`。这不是把 demo stage05 重算后的新 Finding。

## 遗留风险

- 接收者没有类型。`report.execute(...)` 会命中。证据带完整 `callee`，供人工区分游标执行和其他 `execute`。
- `callee` 文本只要包含 `schema_editor` 就记 Unanalyzed。变量名 `editor.execute` 仍会命中，因为名字对不上。
- 限定名 `expressions.RawSQL` 不命中。闭集只认直接名称 `RawSQL`。
- `run = cursor.execute` 之后的 `run(...)`、`getattr` 和包在 helper 里的执行会漏报。不为此做数据流。
- `migrations.RunSQL` 不在 Hit 闭集。迁移目录也没有纳入或排除政策。路径只说明调用落在哪个文件附近。
- 删除已有调用不会命中。闭集只看与新增行相交的 head 调用。
- 参数化的管理 SQL、数据修复迁移和只读报表会命中。命中不是注入已经发生，也不是语句不该出现。
- 规则不解析 SQL 方言，不连接数据库，不判断参数是否来自请求。
- 默认权重是 0。它不改变演示分数，也不表示这条规则已经完成权重校准或经验有效性验证。
- 已保存 demo 没有这条 Finding。目录里能看到新规则，PR 12 的已保存 Finding 列表没有它。
