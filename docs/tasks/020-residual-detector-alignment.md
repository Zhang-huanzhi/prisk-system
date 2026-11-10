---
task_id: "020"
target_version: "v1.2.0"
title: "残余检测器与合同对齐（v1.2 首切片）"
status: "Accepted"
branch: "feat/020-residual-detector-alignment"
date: "2026-11-09"
---

# 020：残余检测器与合同对齐（v1.2 首切片）

## 目标

承接 [v1.2 入口](v1.2-entry.md) §1 与 Task 018 所有者终裁留下的残余实现项：让已实现检测器与卡片合同对齐，并为映射表、`Meta.fields`、`default=`、敏感配置方向、一票抬升提供可验证的运行时支撑。本任务是 v1.2.0 的首个实现切片，**不宣布 v1.2.0 完成**，不创建 `docs/versions/v1.2*`，不打 Tag。

## 范围

1. `code.bare_exception`：将 `except Exception` 移出 Finding 集合；Hit 仅保留裸 `except:` 与直接名称 `BaseException`。
2. `code.unmanaged_open`：覆盖 `Path(...).open` / `pathlib.Path(...).open`；名字形式 `path.open()` 记 `missing_framework_context`；`io.open` / `builtins.open` 不在 Hit 内。
3. 已知框架基类映射：新增 `framework_bases.py`，按最后一段整段相等解析；表外名字保持 Unanalyzed；不扩大 Hit。结构节点写入 `native_or_mapped_bases`。
4. `Meta.fields` / `Meta.exclude`：结构层可读嵌套列表字符串成员（`meta_list_members` / `meta_list_readable`），收窄 `unsupported_stage04_details` 缺口。
5. 非空路径 `default=`：字段赋值与调用节点可靠记录 `has_default_keyword` / `default_literal` 与 `null_literal`。
6. 敏感配置方向：`sensitive_settings.py` 按卡片方向表分类 hit / not_found / unanalyzed（支撑模块；`config.django_sensitive_settings_changed` 生命周期仍为 `draft`）。
7. 一票抬升：评分侧读取登记册 `gatekeeper` / `gatekeeper_condition`；至少对 migrations 路径上的 `DeleteModel`/`RemoveField` 与 `AllowAny`/空 `permission_classes` 结构命中强制 `risk_level=high`。

## 不做事项

- 不批量晋升 20 条草稿卡片（v1.2-entry §2）。
- 不宣布 v1.2.0，不建 `docs/versions/v1.2*`，不打 Tag。
- 不合并 PR、不删远程分支、不开 021、不建 docs/versions/v1.2*（合并由 Engineering Lead）。本任务文档已标 Accepted。
- 不改前端；不扩大 known-framework-bases Hit 映射。

## 设计

- bare / Path.open：检测器合同与 017 卡片一致；构造测试按新合同改写。
- 映射表与 Meta/`default=`：优先落在 stage04 结构细节，供后续检测器消费；本切片不把对应 draft 规则强行写成 implemented Finding。
- 一票抬升：即使 draft 规则尚未产出 Finding，评分侧也可按登记册条件对结构证据抬升，避免“登记了 gatekeeper 但永远不生效”。

## 实现

- `backend/prisk/domain/code_smells.py`：`BROAD_HANDLER_NAMES` 去掉 `Exception`；`_resolve_open_form` 识别 Path.open。
- `backend/prisk/domain/structure.py`：类基类解析、Meta 列表成员、调用/字段的 default/null 关键字。
- 新增 `framework_bases.py`、`sensitive_settings.py`、`gatekeeper.py`。
- `demo_service.py` / `branch_analysis.py`：接入 `apply_gatekeeper_lift`。
- 测试：更新 `test_code_smell_rules.py`、`test_rule_outcomes.py`；新增 `test_residual_alignment_020.py`。

## 验证

- `backend\.venv\Scripts\python.exe -m unittest discover -s backend\tests -t backend`：128 OK。
- 未改前端：跳过 lint/typecheck/build。
- `git diff --check`：通过。

## 生命周期增量

- `code.bare_exception` / `code.unmanaged_open`：保持 `implemented`（合同对齐，非 validated）。
- `data.django_non_null_constraint_tightened`、`config.django_sensitive_settings_changed`、`data.django_destructive_migration`、`auth.drf_permission_policy_downgrade` 及依赖映射表的 draft 规则：**仍为 draft**（本切片提供结构/评分支撑，不晋升）。
- 登记册 `lifecycle` 字段未改。

## 残余风险

- draft 规则仍无完整 Finding 检测器；一票抬升依赖结构切片启发式，可能对测试夹具中的 `AllowAny` 示例抬升。
- `Meta.fields = "__all__"` 与动态列表仍 Unanalyzed。
- 敏感配置方向支撑尚未接入 `RULE_CATALOG` Finding 通路。
- Path.open 仅识别接收者为 `Path(...)` 调用的形态；变量绑定后的 `path.open()` 仍是框架缺口。
