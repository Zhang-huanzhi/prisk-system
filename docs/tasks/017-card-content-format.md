---
task_id: "017"
target_version: "v1.1.0"
title: "规则卡片内容与模板格式"
status: "In Progress"
branch: "docs/017-card-content-format"
date: "2026-11-07"
---

# 017：规则卡片内容与模板格式

## 目标

在已合并的 `a914091`（016）之上，修正所有者指出的卡片语义矛盾，并把 `docs/rules/catalog/` 下每张活动规则卡片对齐到 [规则说明卡片模板](../rules/rule-card-template.md)。本任务只改文档、卡片和登记册里与这些合同对应的文字。不实现检测器，不标记 v1.1.0 完成，不开始 v1.2。

任务状态保持 In Progress。工程负责人以后再 Accept。接受前不把前言写成 Accepted。

## 编号核对

016 写明下一个未使用编号是 017，并且 017 不因 016 被接受而开始。开始时没有任务 017。分支、本文件和前言 `branch` 都是 `docs/017-card-content-format`。

## 范围

- 新建 [已知框架基类映射](../rules/known-framework-bases.md)。最后一段整段相等才使用表中的「设计上视为」。不沿其他文件展开继承，不改 `backend/prisk/`。
- 重写受影响卡片的 Hit / NotFound / Unanalyzed，并同步登记册中对应的 `definition`、`limitations`、`gatekeeper_condition` 和未解决问题。
- `data.django_destructive_migration` 与 `auth.drf_permission_policy_downgrade` 的一票抬升为 `true`，条件非空，且与卡片触发面一致。其余规则保持 `false` / `null`。
- `workflow.large_change_scope` 的现行文字只保留严重度 `High`、风险性质 `pr_intrinsic`。去掉「011 留下差异、014 两边都不改」这种仍像未决冲突的卡片正文。
- 每张目录卡片使用模板的标题、两张分开的表、第 3 节四个小节、第 5 节标题、第 6 节五个固定槽和第 7 节七行表。过程性标题（例如 `014 比较单位`）不留在正式正文里。比较单位里仍然有效的判定写进第 4 节。
- 活动任务索引、v1.1 入口、分支规范、规则知识库、规则索引、责任矩阵、就绪页和结构筛选页改到与上述合同一致。016 及更早任务记录里的当时句子不改写。

## 语义决定

| 项 | 决定 |
| --- | --- |
| NetBox 基类 | 映射表列出 `PrimaryModelSerializer` → `ModelSerializer`，`NetBoxModelViewSet` → `ModelViewSet`，`NetBoxModel` → `Model`。未列入的名字，包括先导记录里的 `RackBaseSerializer`，仍是 Unanalyzed。`restrict_queryset` 不是基类，单独去掉它仍然不是 Hit。 |
| 新增必填 | 显式 `required=True` 且没有 `default=` 时，原生 `Serializer` / `ModelSerializer` 和映射到它们的基类可以记设计 Hit。省略 `required` 仍是 Unanalyzed。 |
| 非空与 `default=` | 已有模型上非空且没有可见 `default=` 才是 Hit。看见 `default=` 是 NotFound，不能只因 `AddField` 省略 `null=True` 就 Hit。 |
| 敏感配置方向 | 放宽或不安全方向是 High Hit。收紧是 NotFound，不是较低严重度的 Hit。方向读不出是 Unanalyzed。一票抬升仍是 `false`。 |
| 一票抬升 | 破坏性迁移：`DeleteModel` 或已在范围内的 `RemoveField`。权限降级：head 成为 `AllowAny`，或成为卡片里已经写明的空列表 / 空元组。`RunSQL` 不抬升。 |
| `Meta.fields` | 删除规则写明列表成员变化的设计 Hit。当前结构对象读不出嵌套 `Meta` 的字符串列表时记 `unsupported_stage04_details`，不把这个缺口当成 NotFound。 |
| `Path.open` | 设计 Hit 包含未作为 `with` 上下文的 `Path(...).open(...)`。运行时检测器仍只认直接名称 `open`。 |
| 裸异常 | 设计 Hit 只保留裸 `except:` 和 `except BaseException`。`except Exception:` 不是本规则的 Hit。运行时仍把三者放在同一条 Finding 里。 |

## 不做事项

- 不新增规则 ID，不把任何 `draft` 改成 `registered`、`implemented` 或 `validated`。
- 不修改 `backend/prisk/` 的检测器，不把六条 016 规则放进 `RULE_CATALOG`，不改权重。
- 不把 `RackBaseSerializer`、`restrict_queryset` 或未列入的自定义基类写进 Hit。
- 不建 ADR，不改 `docs/blueprint.md` 的产品目标。蓝图仍把 NetBox 写成主实证对象；映射表说明哪些最后一段按原生基类对待，哪些仍然不能。
- 不重计 011 的 8 / 10 / 2，不重跑先导 16 条，不填写 Precision 或 Recall。
- 不标记 v1.1.0 完成，不建立 `docs/versions/v1.1/` 或 `docs/versions/v1.1.0/`，不把本任务写成 Accepted。
- 不改 001–016 的任务结论。那些文件里的「不扩大 NetBox 继承上的 Hit」是当时的事实。

## 实际验证

仓库没有 GitHub Actions。没有改前端，所以没有跑 lint、typecheck 或 build。没有改 `backend/prisk/` 的检测器。没有改 `docs/blueprint.md`。

在 `backend/` 下：

- `python3 -m unittest discover -s tests -t .`：121 项全部通过，退出码 0。016 记录的是 118 项。多出的 3 项核对一票抬升条件、已知框架基类映射，以及 `code.bare_exception` / `code.unmanaged_open` 的检测器差异仍写在卡片上。登记册仍是 29 条。运行时目录仍是 14 条。`draft` 仍是 20，`implemented` 仍是 9。
- `git diff --check` 在提交前通过。

这些测试不是先导试点，也不是 Precision 或 Recall。任务状态保持 In Progress。

## 遗留（检测器后续任务）

- `code.bare_exception`：卡片合同已把 `except Exception:` 移出 Hit。`BROAD_HANDLER_NAMES` 仍包含 `Exception`。构造测试仍按旧行为期望 Finding。
- `code.unmanaged_open`：卡片合同已纳入 `Path.open`。检测器仍声明不含属性调用 `Path.open`。
- 映射表、`Meta.fields`、非空 `default=` 和敏感配置方向都还没有检测器。对应规则的 `lifecycle` 仍是 `draft`。
- 一票抬升条件写在卡片和登记册里。运行时评分不读取登记册，因此现在不会执行抬升。
