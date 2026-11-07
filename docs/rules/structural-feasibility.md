# 结构可行性筛选

本页是设计复核，不是测试结果，也不是实现承诺。它不记录 Hit 次数、Precision、Recall 或真实 PR 试点。009 当时的 Hit / NotFound / Unanalyzed 覆盖当时的 13 条运行时规则；本页对尚未实现的候选只写设计预期。

011 记录当时的运行时目录是 13 条：五条历史结构规则、七条代码异味、一条测试协同。研究候选是下面 20 条。登记册还有 3 条故意不在这 20 条里的草稿。这三个计数不能互相替换。011 没有改权重。013 后来把 `data.django_raw_sql_execution` 按本页闭集接入运行时，默认权重 0。下面的 8 / 10 / 2 分类仍是 011 的设计筛选，不因这一条实现而重计。该命中不是注入已经发生，也没有 Precision 或 Recall。

筛选只用当前已经保存的局部证据：同一文件里、行范围与三点 Diff 相交的 AST 节点，以及文件路径和新增/删除行数。不新增跨文件符号表、继承链、URLconf 图或全仓库框架分析。

当前 call 节点有 `callee`、`direct_callee_name`、`args_count`、`keyword_names` 和 `used_as_with_context`。函数节点有带 `has_default` 的签名。类节点有基类文本和装饰器文本。装饰器节点有表达式。字段节点有名字和值指纹。`literal_text` 只保留单个字符串，不保留布尔值，也不保留 `path("...")` 这种位置参数。控制流节点没有“语句属于哪个 with”的字段。

## 三类

| 类 | 含义 | 条数 |
| --- | --- | --- |
| `local_diff_ast` | 触发特征已经在当前局部 Diff 或 AST 上，检测器也已经接入 | 8 |
| `bounded_framework_context` | 同一文件的节点够用，但还要一份写明的框架名单，或还要读当前节点没有结构化的字面量 | 10 |
| `deferred_cross_file_or_policy` | 要跨文件或全仓库关系，或者项目阈值/模块图仍未指定，当前不能定义可执行的 Hit | 2 |

8 + 10 + 2 = 20。条数以页末机器可读清单为准。

## 二十条候选

| 规则 ID | 类 | 局部证据 | 还缺的输入 | 评审去向 |
| --- | --- | --- | --- | --- |
| `code.swallowed_exception` | `local_diff_ast` | `except` 处理体是否单个 `pass`，以及与新增行相交 | 无 | 保持 `implemented`。不改已测试定义 |
| `code.bare_exception` | `local_diff_ast` | 处理类型的直接名称或裸 `except`，以及与新增行相交 | 无 | 同上 |
| `code.dynamic_execution` | `local_diff_ast` | `Call.func` 的直接名称 `eval` / `exec` | 无。属性调用本来就排除 | 同上 |
| `code.hardcoded_secret` | `local_diff_ast` | `literal_binding` 的名字、形式和字符串字面量 | 无 | 同上。命中不是秘密已经泄露 |
| `code.unmanaged_open` | `local_diff_ast` | 直接名称 `open`，且 `used_as_with_context` 为假 | 无 | 同上 |
| `code.deep_control_flow` | `local_diff_ast` | 控制流节点的 `nesting_depth` 与阈值 4 | 无。阈值是已接入的常量，不是未定的项目政策 | 同上 |
| `code.global_mutable_state` | `local_diff_ast` | 函数内 `global`，或模块/类体的可变容器 | 无 | 同上 |
| `workflow.test_collaboration_gap` | `local_diff_ast` | 三点 Diff 的文件状态、新增/删除行数，以及源码里已有的默认路径分类 | 无 | 保持 `implemented`。它不读 AST，但证据已经是局部 Diff |
| `api.drf_public_parameter_added` | `bounded_framework_context` | 同一函数签名的 `has_default`；同一类的基类文本和字段赋值 | 未截断切片里的 `required=True`。省略 `required` 或 `ModelSerializer` 不猜测 | 卡片已写明同一文件表面。适合以后评审，本任务不实现 |
| `api.drf_public_parameter_removed` | `bounded_framework_context` | 与删除行相交的字段名，或签名参数名；同一文件的 `@api_view` / `@action` 或 `Serializer` 基类 | 类基类若同时变化，则不能把消失当成 Hit | 与新增规则分开。不跟随父类文件 |
| `api.django_url_pattern_changed` | `bounded_framework_context` | `path` / `re_path` / `register` 的 `callee` 与行交集 | 位置参数里的 route 字符串。当前 call 节点没有这栏 | route 文本可读之前不应做检测器。`include()` 不跟随 |
| `api.drf_viewset_action_changed` | `bounded_framework_context` | 类基类文本、标准动作函数、`@action` 表达式 | 基类必须是四个 DRF 直接名称之一。跨文件基类不做 | 节点已经够用。比路由字符串更接近以后的实现评审 |
| `auth.drf_permission_decorator_removed` | `bounded_framework_context` | 装饰器表达式和已有的 `decorator_removed` | 五段闭集名称，以及同一文件出现类属性时改记 Unanalyzed | 闭集已写在卡片上，仍不是运行配置 |
| `auth.drf_permission_policy_downgrade` | `bounded_framework_context` | `permission_classes` 赋值或装饰器与新增行相交 | 列表元素是否为 `AllowAny` 或空列表。当前没有名字数组 | 不比较自定义权限类的强弱 |
| `data.django_raw_sql_execution` | `bounded_framework_context` | call 的 `callee` 最后一段或 `RawSQL` 直接名称 | 闭集已限于 `execute`、`executemany`、`raw`、`RawSQL`。接收者无类型 | 最接近现有节点。路径只作证据，不新设迁移政策 |
| `config.django_sensitive_settings_changed` | `bounded_framework_context` | 模块级直接名称赋值和值指纹 | 七个清单名字之外的设置不猜测。布尔方向没有结构化字段 | 名单来自 Django 部署清单，不是项目另交的政策 |
| `data.django_destructive_migration` | `bounded_framework_context` | 路径段 `migrations`，以及 `DeleteModel` / `RemoveField` | `RunSQL` 与 `RunPython` 不解析，见到则 Unanalyzed | 与非空规则分开。不建迁移依赖图 |
| `data.django_non_null_constraint_tightened` | `bounded_framework_context` | 字段或 `AlterField` / `AddField` 调用与 diff 相交 | `null=` 右侧的 `True` / `False` 文本。现有字面量字段不存布尔 | 只改 `blank` 不是本规则。不查库里有没有 `NULL` |
| `data.django_transaction_boundary_changed` | `deferred_cross_file_or_policy` | 只能看见 `atomic` 或 `select_for_update` 的调用文本 | 语句是否仍在同一函数的 `atomic` 块内。节点没有父语句 | 不实现。见到 `atomic` 会和现有粗粒度事务规则重复，且仍无边界 |
| `workflow.large_change_scope` | `deferred_cross_file_or_policy` | 行数和文件数能从 Diff 数出来 | 三个阈值都未指定；模块数还要项目映射 | 不实现。不临时指定 200 行或 3 个模块 |

## 为什么不是同一类

七条代码异味和测试协同已经按卡片接入，使用的字段就是上表那一列。它们不需要 Django 名单。测试协同的路径分类已经写在源码里，不是未指定的项目政策。

`code.deep_control_flow` 的深度阈值是检测器里的固定常量。`workflow.large_change_scope` 的行数、文件数和模块数阈值在卡片上仍是待定，模块映射也不存在。所以前者留在局部 Diff/AST，后者延后。不能因为两者都有数字，就放进同一类。

`data.django_raw_sql_execution` 的 `callee` 已经在节点上，所以它比路由规则更接近局部证据。它仍归入有界框架上下文：`execute` 不是语言关键字，闭集来自 Django 的游标、`raw()` 和 `RawSQL` 文档，而且接收者没有类型。`api.django_url_pattern_changed` 连 route 字符串都还不是结构化字段，所以同属有界上下文，但缺的输入不同，不该排成同一个实现顺序。

`data.django_destructive_migration` 只看两个操作类的名字和 `migrations` 路径段，不需要迁移图。`data.django_transaction_boundary_changed` 需要的是语句包含关系，当前控制流节点没有这条边。删除字段和移动事务块因此分成两类。

`config.django_sensitive_settings_changed` 使用部署检查清单上的七个名字作为闭集。清单没有点名的设置记 Unanalyzed，而不是把整条规则延后。`workflow.large_change_scope` 没有这样一份已经公布的闭集，阈值本身就是未指定的项目政策，所以延后。

`auth.drf_permission_policy_downgrade` 只接受 `AllowAny` 和空列表。这两个形态在 DRF 权限页有直接语句。自定义类谁更严没有官方全序，本页不补这张表，也不因此要求对象级权限分析。

## 延后与排除

`data.django_transaction_boundary_changed` 延后，是因为边界是包含关系，不是因为事务不重要。跨函数的 helper 也不内联。

`workflow.large_change_scope` 延后，是因为卡片已经禁止在阈值和模块映射缺失时产生 Finding。行数和文件数虽然局部可见，但不能单独改写成这条规则的 Hit。登记册里这条的严重度是 `High`、风险性质是 `external_impact`；卡片写的是 `Medium` 和 `pr_intrinsic`。011 不覆盖这处手工差异。状态两边都是 `draft`。

下面三条在登记册里，不在 20 条候选里。011 不给它们写卡片，也不改写登记册里尚未核实的占位依据。

| 规则 ID | 排除原因 |
| --- | --- |
| `code.dead_code_after_exit` | 知识库已说明暂不纳入，因为退出后的死代码已有编译器或 linter 广泛覆盖。局部 AST 看不看得见，不改变这条排除 |
| `auth.drf_object_permission_bypass` | 对象级权限要看 `has_object_permission` 和查询集过滤是否一起生效。DRF 写明列表接口不会自动对每个对象做对象级检查。这超出同一属性赋值，也常跨方法。20 条里的降级规则故意不覆盖它 |
| `auth.django_permission_module_changed` | “权限模块有改动”没有闭集。装饰器删除和显式降级已经各有一条更窄的候选。模块级全量变化仍然排除 |

`data.django_raw_sql_execution` 的卡片标题是「Django 原生 SQL 执行」，登记册名称仍是「绕过 ORM 的原生 SQL」。011 不改这条手工名称。013 把生命周期改为 `implemented`，名称仍留着登记册里的原文。

## 设计预期里的 Unanalyzed

尚未实现的规则没有运行终态。设计上：

- 同一文件缺少框架表面、闭集对不上、或要跟随 `include()` 和父类时，预期是 Unanalyzed，原因用 `missing_framework_context` 这个已有名字。不记 NotFound。
- 切片截断、布尔或位置参数读不出时，预期是 `unsupported_stage04_details`。不把残缺文本当成 Hit。
- 事务边界和大规模变更在缺字段或未定阈值时，整条规则没有 Hit 条件。这不是“本次未命中”。

这些句子不写入尚未实现规则的 `rule_outcomes`，也不改写已保存的 demo。013 已经为 `data.django_raw_sql_execution` 写入终态。本页不因此重计上面的分类。

## 机器可读清单

```yaml
feasibility_classes:
  local_diff_ast:
    - code.swallowed_exception
    - code.bare_exception
    - code.dynamic_execution
    - code.hardcoded_secret
    - code.unmanaged_open
    - code.deep_control_flow
    - code.global_mutable_state
    - workflow.test_collaboration_gap
  bounded_framework_context:
    - api.drf_public_parameter_added
    - api.drf_public_parameter_removed
    - api.django_url_pattern_changed
    - api.drf_viewset_action_changed
    - auth.drf_permission_decorator_removed
    - auth.drf_permission_policy_downgrade
    - data.django_raw_sql_execution
    - config.django_sensitive_settings_changed
    - data.django_destructive_migration
    - data.django_non_null_constraint_tightened
  deferred_cross_file_or_policy:
    - data.django_transaction_boundary_changed
    - workflow.large_change_scope
exclusions:
  - code.dead_code_after_exit
  - auth.drf_object_permission_bypass
  - auth.django_permission_module_changed
```
