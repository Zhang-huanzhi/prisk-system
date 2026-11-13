# Prisk v1.4 人工核验标注指南 (`annotation-guide.md`)

本指南基于 [`pilot-v1.1/protocol.md`](../pilot-v1.1/protocol.md) 四值核验经验收敛而成，服务于 `v1.4.0` 正式集人工复核与准确率自动化统计。

## 1. 四值判断词表（`finding_judgments[].judgment`）

核验人员针对 PR 中工具触发的每条 Finding（或抽查关键规则结局）结合目标 PR 的 Diff、基类上下文与测试协同关系给出唯一判断：

| 判断取值 | 英文语义 | 判定标准 | 计量口径 |
| :--- | :--- | :--- | :--- |
| `hit` | 结构规则定义命中 (TP) | 改动内容**真实满足该规则卡片定义的风险结构与语义条件**，值得向代码审查者提示复核（即使合入后未发生线上故障） | 计入 `tp_hit`，Precision 分子 |
| `false_looking_hit` | 规则误报 / 高噪命中 (FP) | Diff 或 AST 中存在形似触发字面量/结构，但在真实框架语义或上下文中**并不构成该规则所描述的审查信号**（例如框架标准常量名被误判硬编码密钥、无害全局配置常量被误报全局可变状态） | 计入 `fp_noise`，Precision 分母 |
| `unanalyzed` | 不可分析 / 上下文不足 | 缺少父基类解析、语法退化、或所需跨文件引用超出当前局部上下文，无法在规则定义层面下定论 | 单独统计，**不计入 Precision 分母** |
| `not_applicable` | 无适用结构表面 | 变更仅涉及非目标文件或无相应框架对象，不应作为误报归咎规则逻辑 | 单独统计，**不计入 Precision 分母** |

> 标注原则：**先按规则卡片/代码实现定义核验结构条件是否真实成立**，不要以「作者后来有没有被回滚」逆推当前 Finding 是否为误报；若属于高噪但结构上确实命中了过宽规则，请仍记为 `false_looking_hit` 并填写 `noise_pattern` 归因，以便在 Task 033 定向收窄规则或降权。

---

## 2. 标注记录 JSONL Schema（`prisk.eval.annotation.v1`）

每行对应一条已合并 PR 的完整人工核验记录，存放于正式实验目录下的 `annotations.jsonl`：

```json
{
  "schema_version": "prisk.eval.annotation.v1",
  "repo": "netbox-community/netbox",
  "pr_number": 24001,
  "track": "track_a_random",
  "review_minutes": 7.5,
  "finding_judgments": [
    {
      "rule_id": "code.global_mutable_state",
      "judgment": "false_looking_hit",
      "path": "netbox/dcim/models/devices.py",
      "start_line": 42,
      "end_line": 48,
      "reason_note": "模块级 MODEL_ORDERING 常量配置元组/字典并非运行时可变状态",
      "noise_pattern": "module_constant_mapping"
    },
    {
      "rule_id": "workflow.test_collaboration_gap",
      "judgment": "hit",
      "path": "netbox/dcim/api/views.py",
      "start_line": 1,
      "end_line": 1,
      "reason_note": "修改生产 ViewSet 业务逻辑，同 PR 未改动任何测试文件"
    }
  ]
}
```

### 字段约束（由 `prisk.domain.evaluation.validate_annotation_records` 强制校验）

- `schema_version`：固定 `"prisk.eval.annotation.v1"`；
- `repo`、`pr_number`：联合唯一，同一 PR 不得重复标注两行；
- `track`：枚举限 `"track_a_random"` | `"track_b_targeted"` | `"external_control"`；
- `review_minutes`：非负数字，记录阅读该 PR Diff 并完成 Finding 逐条核验的真实分钟数（用于评估人工审计耗时与上限控制）；
- `finding_judgments`：列表（零命中且无需核验条目的 PR 可填 `[]`）；每项必须包含 `rule_id`（非空字符串）与四值 `judgment`。

---

## 3. 29 条运行时规则分类核验要点

当前运行时目录包含 **29 条已执行规则**（另 [`rule-registry.json`](../../../backend/data/rules/rule-registry.json) 中 5 条 `draft` 规则暂不运行、不参与正式核验）：

### A. 历史基础结构规则（5 条，`historical_baseline`）

| Rule ID | 核验重点 |
| :--- | :--- |
| `api.signature_changed` | 识别公开函数/方法参数、装饰器、返回值或路由入口签名变更是否真实改变接口契约 |
| `auth.permission_structure_changed` | 鉴权装饰器、权限类配置、访问控制分支发生实质结构改写 |
| `data.transaction_structure_changed` | 涉及数据库事务边界（如 `atomic` 上下文）、模型写操作或迁移事务结构 |
| `config.configuration_structure_changed` | 影响运行时配置键值、环境变量读取、默认配置映射的结构性变更 |
| `code.exception_structure_changed` | 异常捕获/抛出层级或关键错误处理控制流结构改写 |

### B. 代码坏味道与防御式边界规则（9 条，`code_smell`）

| Rule ID | 核验重点 | 常见高噪排查 (`noise_pattern`) |
| :--- | :--- | :--- |
| `code.swallowed_exception` | `except` 块体仅余 `pass` 且缺乏兜底注释/合理意图 | 刻意忽略可预期异常清理分支 |
| `code.bare_exception` | 裸 `except:` 无任何异常类型约束 | 极少误报；确认是否在生产路径而非注释/字符串 |
| `code.dynamic_execution` | 新增或改写 `eval`/`exec`/`__import__` 等动态求值调用 | 确认非安全静态替代场景 |
| `code.unmanaged_open` | 直接调用 `open()` 而未使用 `with` 上下文管理器且句柄逃逸 | 局部立即关闭或轻量工具脚本模式 |
| `code.deep_control_flow` | 变更涉及深层控制流嵌套，核查是否确属高复杂度改动 | 机械表驱动结构嵌套深度边界 |
| `code.hardcoded_secret` | 赋值键名像凭据且值为非空字面量 | **重点排查**：表单字段标签、校验常量、测试/文档示例键名（如 `token_field` 字符串常量） |
| `code.global_mutable_state` | 模块顶层存在可变容器并存在跨请求状态污染风险 | **重点排查**：NetBox `CHOICES`、Django 配置字典等只读约定的模块常量表 |
| `code.assert_in_production` | 生产代码（非测试路径）出现 `assert` 断言 | 内部类型缩窄（mypy narrowing）与业务不变量校验差异 |
| `code.mutable_default_argument` | 函数签名默认参数为字面量 `[]` / `{}` / `set()` 等可变对象 | 基本无误报，核对是否为生产路径且非不可变约定 |

### C. 后端高危契约与破坏性变更规则（15 条，`backend_contract` / `breaking_impact`）

| Rule ID | 规则族 | Gatekeeper | 核验重点 |
| :--- | :--- | :---: | :--- |
| `data.django_raw_sql_execution` | `backend_contract` | - | `.raw()` / `.extra()` / `cursor.execute()` 等原生 SQL 执行，重点分辨是否参数化绑定与可信表名拼接 |
| `auth.django_csrf_exempt_added` | `backend_contract` | - | 新增 `@csrf_exempt` 是否确为暴露给浏览器会话的视图豁免 |
| `api.drf_viewset_action_changed` | `backend_contract` | - | DRF `@action` 路由、HTTP methods 或 `detail` 契约变化 |
| `data.django_destructive_migration` | `breaking_impact` | **Yes** | 迁移文件出现 `DeleteModel` / `RemoveField` 等破坏性变更 |
| `auth.drf_permission_policy_downgrade` | `backend_contract` | **Yes** | 权限类收窄为更宽松权限（如移除鉴权或替换为 `AllowAny` 等价放宽） |
| `config.django_sensitive_settings_changed` | `backend_contract` | - | 修改 `DEBUG`、`ALLOWED_HOSTS`、`SECRET_KEY` 等敏感安全设置 |
| `data.django_non_null_constraint_tightened` | `breaking_impact` | - | 收紧模型字段 `null=False` 等非空约束导致已有库或迁移兼容风险 |
| `auth.drf_permission_decorator_removed` | `backend_contract` | - | 从视图/方法上移除了权限控制装饰器 |
| `auth.drf_queryset_scope_tighten_bypassed` | `backend_contract` | - | `get_queryset` 范围限制或权限过滤链被放宽或绕过 |
| `data.django_signal_receiver_leak` | `backend_contract` | - | `@receiver` 注册或信号绑定生命周期异常导致重复触发/泄漏 |
| `data.django_field_rename_without_db_column` | `breaking_impact` | - | 重命名字段而未通过 `db_column` 保留原列名或迁移配合 |
| `api.drf_public_parameter_added` | `backend_contract` | - | 公开序列化器/接口参数新增及兼容性影响 |
| `api.drf_public_parameter_removed` | `backend_contract` | - | 公开序列化器/接口参数删除导致的破坏性兼容风险 |
| `api.django_url_pattern_changed` | `backend_contract` | - | `urlpatterns` 中公开 `path()`/`re_path()` 映射或路由名变动 |
| `workflow.test_collaboration_gap` | `breaking_impact` | - | 业务生产代码变更且同 PR 未包含任何测试路径变更 |

> 另 5 条处于 `draft` 状态的规则（`auth.django_permission_module_changed`、`auth.drf_object_permission_bypass`、`code.dead_code_after_exit`、`data.django_transaction_boundary_changed`、`workflow.large_change_scope`）在当前 `v1.4` 运行时目录中不触发；标注时若遇到对应漏洞但当前未产出 Finding，可在 PR 备注中留痕作为后续缺口观察依据。
