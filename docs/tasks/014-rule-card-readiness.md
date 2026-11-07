---
task_id: "014"
target_version: "v1.1.0"
title: "v1.1 规则卡片就绪核对"
status: "In Progress"
branch: "feat/014-rule-card-readiness"
date: "2026-11-07"
---

# 014：v1.1 规则卡片就绪核对

## 目标

在已合并的 013 之上，核对 v1.1 规则卡片是否把比较单位、身份、排除和终态边界写清楚，并核对每张卡片已有的 `lifecycle` 是否和登记册一致。交付是设计记录。不把 v1.1.0 写成已经完成。

起始提交是 `98d145cd3dbb7d790dd3094b5faa0c61b4c87630`。核对页是 [v1.1 卡片就绪核对](../rules/v1.1-card-readiness.md)。

本任务保持 In Progress，留给工程负责人评审。不合并，不打 tag，不把状态写成 Accepted。

## 编号核对

013 已说明下一个未使用编号是 014。开始时没有任务 014，也没有打开的竞争 PR。分支、本文件和前言 `branch` 都是 `feat/014-rule-card-readiness`。

## 范围

- 卡片正文只覆盖 011 的 20 条候选。登记册另有 3 条排除项，本轮不给它们写卡片，也不把这件事写成永久禁止。`lifecycle` 允许值只使用已有的 `draft`、`registered`、`implemented`、`validated`、`deprecated`。
- 给接口和权限卡片补比较单位。已有表面上的必填新增、名字删除、路由调用变化、ViewSet 动作变化、装饰器删除和显式降级仍用原来的规则 ID。
- 写明「直接名称」按最后一段标识符相等。`PrimaryModelSerializer` 不进入闭集。
- 给已实现卡片补一句登记字段和运行终态的对应，不改命中条件。
- 更新活动任务索引、v1.1 入口、规则索引和登记册里与新比较单位冲突的定义文字。`lifecycle` 不改。

## 不做事项

- 不实现检测器，不修改 `backend/prisk/` 的规则语义，不改默认权重，不改评分上限。
- 不把任何 `draft` 改成 `registered`、`implemented` 或 `validated`。文档写完不是升级条件。
- 不为「新增端点」或「已有参数改必填性」新建规则 ID。
- 不把 `PrimaryModelSerializer` 按后缀并入 `ModelSerializer` 或 `Serializer`。
- 不重计 011 的 8 / 10 / 2，不重跑先导 16 条，不报告 Precision、Recall 或经验有效性。
- 不改 `docs/blueprint.md`，不改推进大纲正文，不改冻结的 v1.0.0。
- 不覆盖 `workflow.large_change_scope` 登记册里与卡片不一致的严重度和风险性质。
- 不给三条排除项写卡片。
- 不合并，不打 tag，不把本任务写成 Accepted。

## 技术方案

状态只读登记册字段 `rules[].lifecycle` 和卡片表格里的「生命周期」。两者允许值与 [rule-metadata.schema.json](../schemas/rule-metadata.schema.json) 相同。任务状态和 `rule_outcomes.state` 不写入这个字段。

`implemented` 保留给已经有检测器和构造测试的 9 条。其余 14 条登记册记录保持 `draft`，其中 11 条有卡片，3 条按 011 没有卡片。`registered`、`validated`、`deprecated` 仍是空集。

接口卡片把比较单位收在「两侧都存在的同一个类或函数」或「头侧仍在的同一个类或函数」。只在一侧出现的整份声明，不记成参数新增或参数删除。路由卡片内部仍区分调用加上、调用去掉和文本改写，但 route 字符串还不是结构化字段，所以 `lifecycle` 保持 `draft`。

## 兼容性

- 运行时目录仍是 14 条。`evaluate_rules` 的命中条件不变。
- 登记册仍不是运行时配置。`api.drf_public_parameter_added` 的 `definition.target` 改为 011 的同一文件表面，不再写「已路由」作为已经证明的对象。跨文件 `router.register` 与 `include()` 仍不是表面证据；看不到该表面时仍是 Unanalyzed。`auth.drf_permission_decorator_removed` 的抑制保持同一文件，不收窄到同一所有者。`lifecycle` 的值没有改。
- 已保存 demo 的 Finding 和分数不重算。
- 先导 16 条仍排除出 v1.4。本任务不新增筛查结果。

## 验收

- 前言 `status` 为 In Progress，`branch` 与 Git 分支同为 `feat/014-rule-card-readiness`。
- 有卡片的规则，卡片生命周期与登记册 `lifecycle` 一致，且值属于 schema 枚举。
- 没有新的规则 ID，运行时目录仍是 14 条，默认可得权重仍是 10。
- 核对页写明大纲三条的现有证据，以及尚未接受为版本完成的部分。
- `docs/blueprint.md` 未被修改。

## 实际验证

仓库没有 GitHub Actions。系统 Python 是 3.12.3，项目声明是 `requires-python >=3.12`。没有改前端，所以没有跑 lint、typecheck 或 build。没有改 `docs/blueprint.md` 和推进大纲。

在 `backend/` 下：

- `python3 -m unittest discover -s tests -t .`：116 项全部通过，退出码 0。其中 `tests.services.test_rule_registry` 核对卡片表格里的生命周期与登记册 `lifecycle` 一致。同一文件还检查 `api.drf_public_parameter_added` 的 `definition.target` 不再把「已路由」写成已经证明的对象，以及装饰器删除在同一文件出现无关类的 `permission_classes` 时保持 Unanalyzed。核对页写明范围是 011 的 20 条候选，不是登记册 23 条，也不禁止以后写卡片。运行时目录测试仍期待 14 条。`lifecycle` 的值没有改。

新增和改写的活动 Markdown 相对链接已检查，没有断链。`git diff --check` 在提交前通过。这些测试不是先导试点，也不是 Precision 或 Recall。

## 遗留风险

- `PrimaryModelSerializer` 仍不能识别。按最后一段标识符，它落在设计上的 `missing_framework_context`。这不是 NetBox 上已经测得的命中率。
- 已有字段只改 `required` 时，新增规则和删除规则都不覆盖。目录里没有另一条规则。
- 「新增端点」没有规则 ID。路由卡片和 ViewSet 卡片各管自己的局部差异，而且都还是 `draft`。
- `api.django_url_pattern_changed` 的 route 文本仍不是结构化字段。
- `workflow.large_change_scope` 的严重度与风险性质仍和登记册不一致。这是 011 留下的分类例外，不是生命周期差异，014 不改，也不声称分类元数据已经一致。
- `api.drf_public_parameter_added` 不证明 URL 已经登记。同一文件没有 011 表面时仍是 Unanalyzed。
- 权限装饰器删除的抑制是同一文件里的 `permission_classes` 赋值，无关类也包括在内。收窄到同一所有者是未决提议。
- 先导 16 条是目的样本。014 没有重跑。013 的原生 SQL 检测器没有出现在那次筛查里。
- 构造样例写在卡片上，不表示先导有效，也不表示 `validated`。
- v1.1.0 没有冻结目录。三条大纲是否算完成，本任务不代为宣布。
