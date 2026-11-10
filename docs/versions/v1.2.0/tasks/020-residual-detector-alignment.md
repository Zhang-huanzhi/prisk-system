---
task_id: "020"
target_version: "v1.2.0"
title: "残余检测器与合同对齐（v1.2 首切片）"
status: "Accepted"
branch: "feat/020-residual-detector-alignment"
date: "2026-11-09"
---

# 020：残余检测器与合同对齐（v1.2 首切片）

## 1. 背景与目标

承接 [`v1.2-entry.md`](v1.2-entry.md) §1 与 [v1.1 卡片门槛决策](../rules/v1.1-card-gate-decision.md) 留下的 7 项残余实现缺口。本任务作为 v1.2 阶段的首个实现切片，旨在：

1. 消除既有代码异味检测器（`code.bare_exception`、`code.unmanaged_open`）与规则卡片合同之间的行为偏差；
2. 在 Stage04 结构提取层与领域支撑层补齐「已知框架基类映射」、「`Meta.fields / exclude` 列表成员解析」、「字段与调用 `default= / null=` 关键字提取」以及「敏感配置变更方向分类」能力；
3. 在复核评分侧联动读取规则登记册的 `gatekeeper`（一票抬升）元数据，为后续高价值草稿检测器批次（Task 021、022）提供完备的底层结构与评分支撑。

## 2. 范围与边界

### 纳入范围

1. **`code.bare_exception` 合同对齐**：将 `except Exception` 移出 Finding 集合，仅对裸 `except:` 与直接名称 `BaseException` 生成 Finding。
2. **`code.unmanaged_open` 合同对齐**：扩展识别 `Path(...).open` 与 `pathlib.Path(...).open` 链式调用；对变量形式 `path.open()` 记 `Unanalyzed (missing_framework_context)`。
3. **已知框架基类映射**：新增 `framework_bases.py`，按最后一段标识符精确相等解析 [`known-framework-bases.md`](../rules/known-framework-bases.md) 闭集，并在 Stage04 类节点写入 `native_or_mapped_bases`。
4. **`Meta.fields` / `Meta.exclude` 结构解析**：在 Stage04 类节点解析嵌套 `Meta` 的字符串列表/元组字面量（`meta_list_members`、`meta_list_readable`），收窄 `unsupported_stage04_details` 缺口。
5. **非空约束路径 `default=` / `null=` 提取**：在 Stage04 字段赋值与调用节点记录 `has_default_keyword`、`default_literal` 与 `null_literal`。
6. **敏感配置方向判定支撑**：新增 `sensitive_settings.py`，按卡片方向表将 7 个敏感配置项的赋值变更分类为 `hit` / `not_found` / `unanalyzed`。
7. **一票抬升（Gatekeeper）评分联动**：新增 `gatekeeper.py` 并接入分支分析与演示评分服务，读取登记册 `gatekeeper=true` 条件，对破坏性迁移与权限降级结构证据强制抬升 `risk_level="high"`。

### 不做事项（技术边界）

- 本切片仅提供底层结构提取与辅助模块，不将 20 条 `draft` 候选规则批量接入 `RULE_CATALOG` 或晋升其 `lifecycle`（留待 Task 021、022 分批落地）。
- 不扩大 [`known-framework-bases.md`](../rules/known-framework-bases.md) 映射表之外的自定义基类命中面，不做模糊后缀或跨文件继承推导。
- 不改动前端组件与页面展示逻辑。

## 3. 技术方案与契约设计

### 核心方案

本切片涉及的 7 项合同对齐与支撑能力设计如下：

| 序号 | 目标项 / 关联规则 | 核心判定与结构提取机制 | 三态 / 评分边界 |
| :---: | :--- | :--- | :--- |
| 1 | `code.bare_exception` | `BROAD_HANDLER_NAMES` 移除 `Exception`，仅保留裸 `except:`（`type is None`）与直接名称 `BaseException`（含元组形式）。 | 仅捕获 `Exception` 时记 `NotFound`，不再产生 Finding。 |
| 2 | `code.unmanaged_open` | `_resolve_open_form` 除直接 `open(...)` 外，新增识别接收者为 `Path(...)` 或 `pathlib.Path(...)` 的 `.open(...)` 调用（未置于 `with` 上下文中）。 | `io.open` / `builtins.open` 不在闭集内；变量接收者 `path.open()` 记 `Unanalyzed (missing_framework_context)`。 |
| 3 | 已知框架基类映射 | `resolve_class_bases` 按点分表达式最后一段精确匹配 7 个原生基类与 3 个 NetBox 映射基类（`PrimaryModelSerializer → ModelSerializer`、`NetBoxModelViewSet → ModelViewSet`、`NetBoxModel → Model`）。 | 表外基类名记入 `unlisted_last_segments`，供下游规则判定 `Unanalyzed (missing_framework_context)`。 |
| 4 | `Meta.fields` / `exclude` | AST 扫描类体内的内部类 `Meta`，当 `fields` 或 `exclude` 为纯字符串常量的列表/元组时提取成员列表并标记 `meta_list_readable=True`。 | `"__all__"` 或动态拼接表达式标记为不可读，下游记 `Unanalyzed (unsupported_stage04_details)`。 |
| 5 | `default=` 与 `null=` 关键字 | 扫描模型字段赋值与迁移操作调用的关键字参数，记录 `has_default_keyword`（排除 `default=None` 作为有效填充值）及布尔字面量 `null_literal`。 | `**kwargs` 展开或截断切片无法确认关键字时，供下游记 `Unanalyzed`。 |
| 6 | 敏感配置方向分类 | `classify_sensitive_direction` 针对 `SECRET_KEY`、`DEBUG`、`ALLOWED_HOSTS`、`DATABASES` 等 7 个闭集名称解析 base/head 赋值切片，区分放宽/不安全方向与收紧方向。 | 放宽/硬编码记 `hit`；收紧（如 `DEBUG: True → False`）记 `not_found`；截断或动态表达式记 `unanalyzed`。 |
| 7 | 一票抬升（Gatekeeper） | `apply_gatekeeper_lift` 读取 `rule-registry.json` 中 `gatekeeper=true` 的规则，结合 Finding 或 Stage04 结构命中（`migrations` 下的 `DeleteModel`/`RemoveField`，或 `permission_classes` 设为 `AllowAny`/空容器）。 | 触发时将报告 `risk_level` 强制抬升为 `"high"`，并附带 `gatekeeper_lifted=True` 与 `gatekeeper_hits` 证据列表。 |

### 契约与兼容性

- **阶段 Schema 与接口**：`stage04` 节点 `details` 增量扩展基类映射、`Meta` 列表与 `default/null` 字段，向后兼容旧消费者；评分输出增量附带 `gatekeeper_lifted` 与 `gatekeeper_hits`。
- **评分与权重基线**：运行时规则目录维持 14 条，默认满分基线 `maximum_points=10` 不变。
- **历史快照兼容**：`backend/data/demo/` 下已保存的演示快照（如 PR 12）不触发 Gatekeeper 抬升，得分（30 分，3/10）与 Finding 列表完全不变。

## 4. 交付物与改动清单

### 改动文件

- **源码实现**：
  - `backend/prisk/domain/code_smells.py`：对齐 `code.bare_exception` 与 `code.unmanaged_open` 检测逻辑。
  - `backend/prisk/domain/structure.py`：在 Stage04 节点提取框架基类解析结果、`Meta.fields/exclude` 列表成员及 `default/null` 关键字特征。
  - `backend/prisk/domain/framework_bases.py`（新增）：已知框架基类尾段精确相等映射表与解析函数。
  - `backend/prisk/domain/sensitive_settings.py`（新增）：Django 7 项敏感配置变更方向分类器。
  - `backend/prisk/domain/gatekeeper.py`（新增）：基于登记册元数据的一票抬升判定与评分修正器。
  - `backend/prisk/services/branch_analysis.py`、`backend/prisk/services/demo_service.py`：在评分汇总链路接入 `apply_gatekeeper_lift`。
- **规则与文档资产**：
  - [`docs/rules/catalog/code_smell/code.bare_exception.md`](../rules/catalog/code_smell/code.bare_exception.md)、[`code.unmanaged_open.md`](../rules/catalog/code_smell/code.unmanaged_open.md)：同步运行时合同说明。
  - [`docs/rules/known-framework-bases.md`](../rules/known-framework-bases.md)、[`docs/tasks/v1.2-entry.md`](v1.2-entry.md)、[`docs/tasks/README.md`](README.md)。
- **测试套件**：
  - `backend/tests/domain/test_residual_alignment_020.py`（新增）：覆盖 7 项合同对齐与支撑模块的构造测试。
  - `backend/tests/domain/test_code_smell_rules.py`、`backend/tests/domain/test_rule_outcomes.py`：更新 `except Exception` 与 `Path.open` 相关断言。

### 规则生命周期变更

| 规则 ID (`rule_id`) | 所属阵营 (`rule_family`) | 生命周期 (`before → after`) | 默认权重 | 备注 |
| :--- | :--- | :---: | :---: | :--- |
| `code.bare_exception` | `code_smell` | `implemented → implemented` | `0` | 拆出 `except Exception`，对齐卡片闭集 |
| `code.unmanaged_open` | `code_smell` | `implemented → implemented` | `0` | 补充 `Path(...).open` 链式调用识别 |
| `data.django_destructive_migration` | `breaking_impact` | `draft → draft` | `0` | 接入评分侧 Gatekeeper 结构抬升支撑（Task 021 晋升） |
| `auth.drf_permission_policy_downgrade` | `backend_contract` | `draft → draft` | `0` | 接入评分侧 Gatekeeper 结构抬升支撑（Task 021 晋升） |
| `config.django_sensitive_settings_changed` | `backend_contract` | `draft → draft` | `0` | 完成 `sensitive_settings.py` 方向分类支撑（Task 021 晋升） |
| `data.django_non_null_constraint_tightened` | `breaking_impact` | `draft → draft` | `0` | 完成 Stage04 `default=/null=` 提取支撑（Task 021 晋升） |

## 5. 验证与验收

### 验收要点

- `except Exception:` 不再产生 `code.bare_exception` Finding，裸 `except:` 与 `except BaseException:` 正常命中。
- 未置于 `with` 中的 `Path("a").open()` 与 `pathlib.Path("a").open()` 命中 `code.unmanaged_open`；变量调用 `p.open()` 记 `Unanalyzed (missing_framework_context)`。
- `PrimaryModelSerializer`、`NetBoxModelViewSet`、`NetBoxModel` 精确映射为对应 DRF/Django 原生基类；未知基类保持 `unlisted`。
- `Meta.fields = ["id", "name"]` 可读出成员列表；`Meta.fields = "__all__"` 标记为 `meta_list_readable=False`。
- `DeleteModel` / `RemoveField` 及 `AllowAny` / 空 `permission_classes` 在总分低于高风险阈值时仍可通过 Gatekeeper 将 `risk_level` 抬升至 `"high"`。

### 执行检查

- **后端测试**：`backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -t backend`（128 项测试全部通过，含新增 `test_residual_alignment_020.py`）
- **前端检查**：未改动前端代码，跳过 `lint` / `typecheck`
- **格式检查**：`git diff --check`（通过）

## 6. 已知限制与残余风险

- **静态分析边界**：`code.unmanaged_open` 对 `Path.open` 的识别仅限接收者直接为 `Path(...)` / `pathlib.Path(...)` 构造调用的语法形态；经变量绑定后的 `path.open()` 因缺乏局部类型推断仍记为 `Unanalyzed (missing_framework_context)`。
- **动态列表限制**：`Meta.fields = "__all__"` 或非常量列表推导式在单文件 AST 下无法展开字段集合，保持 `Unanalyzed (unsupported_stage04_details)`。
- **启发式抬升边界**：评分侧 Gatekeeper 的结构切片匹配不区分测试夹具文件与生产视图文件，若变更的测试夹具中出现 `permission_classes = [AllowAny]` 亦会触发抬升。
