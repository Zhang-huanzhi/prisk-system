# 已知框架基类映射

本页是设计身份表。它回答「最后一段标识符按哪个原生基类理解」。它不是运行时继承解析，也没有检测器读取它。

[核心蓝图](../blueprint.md) 把 NetBox 写成主实证对象，框架语义优先是 Django / DRF。014 起，若干卡片只把最后一段与原生名字整段相等当作身份，于是 `PrimaryModelSerializer`、`NetBoxModelViewSet`、`NetBoxModel` 落在 Unanalyzed。017 用本表写明哪些已经点名的项目基类按原生基类对待。表外的名字仍然 Unanalyzed。这不是静默放宽，也不是把后缀「像不像」算进去。

## 怎么匹配

类语句基类表达式按点号拆开，取最后一段。该段必须与下表左列整段相等，才使用右列。子串、后缀和「看起来像 ModelViewSet」都不算。不打开其他文件的 `class` 语句，不展开 MRO，不解析 import 别名。

别名、星号导入，或最后一段读不出来时，记 `missing_framework_context` 或 `unsupported_stage04_details`，与各卡片原有的缺口原因一致。不记 Hit，也不记 NotFound。

## 映射

| 最后一段 | 设计上视为 | 适用规则 | 说明 |
| --- | --- | --- | --- |
| `PrimaryModelSerializer` | `ModelSerializer` | `api.drf_public_parameter_added`，`api.drf_public_parameter_removed` | 仓库卡片和先导记录已经用这个名字表示 NetBox 的模型序列化器基类。按 `ModelSerializer` 的显式类体字段理解，不按「纯 `Serializer` 且省略 `required` 时默认必填」理解。 |
| `NetBoxModelViewSet` | `ModelViewSet` | `api.drf_viewset_action_changed`，`auth.drf_queryset_scope_tighten_bypassed` | 所有者指定的 ViewSet 身份。动作增减，以及 `get_queryset` 返回未过滤 `objects.all()`，按 `ModelViewSet` 的卡片条件判断。 |
| `NetBoxModel` | `Model` | `data.django_field_rename_without_db_column` | 与上两行同一类「最后一段身份」。字段改名规则的直接基类因此包含这一段。 |

原生闭集仍然有效，不必先出现在这张表里：`Serializer`、`ModelSerializer`、`ViewSet`、`GenericViewSet`、`ModelViewSet`、`ReadOnlyModelViewSet`、`Model`。映射只增加上表三行。

## 明确不在表内

- `RackBaseSerializer`。先导记录只说明它不是直接名称 `Serializer`。没有人把它写成哪一个原生基类。仍是 Unanalyzed。
- `restrict_queryset`。这是方法名，不是基类。查询集规则不因本表把「去掉 `restrict_queryset`」单独记成 Hit。返回值若不是未过滤的 `objects.all()`，仍按那张卡片的原条件处理。
- 任何其他自定义基类，包括名字里带有 `Serializer`、`ViewSet` 或 `Model` 的项目类。未写入本表就是 Unanalyzed。
- 本表不声称这些类在某一版 NetBox 源码里的 MRO 已经被自动证明。身份是整段名字对照，供设计和以后的检测器使用。

## 和 Hit 的关系

设计 Hit 仍然要满足各卡片自己的触发条件。映射只解决「这个类算不算那条规则的适用表面」。例如 `PrimaryModelSerializer` 上省略 `required` 仍然 Unanalyzed；写出 `required=True` 且没有 `default=` 才进入新增必填规则的设计 Hit。`NetBoxModelViewSet` 上的 `get_queryset` 只有在返回未过滤 `objects.all()` 时才进入查询集规则的设计 Hit。

这些规则的 `lifecycle` 仍是 `draft`。运行时目录不读取本表，今天不会因为本表产生 Finding。
