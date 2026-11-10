"""prisk.domain.config: 运行时配置解耦与场景预设体系。"""

from __future__ import annotations

import copy
from typing import Any

from .rules import RULE_CATALOG
from .test_collaboration import COLLABORATION_RULE_ID


CONFIG_SCHEMA_VERSION = "config.v1"

PRESET_BALANCED = "balanced"
PRESET_SECURITY_FOCUS = "security_focus"
PRESET_FRAMEWORK_UPGRADE = "framework_upgrade"
PRESET_DAILY_REVIEW = "daily_review"
PRESET_LEGACY_BASELINE = "legacy_baseline"

_ALL_RULE_IDS: list[str] = [item["rule_id"] for item in RULE_CATALOG]
_RULE_ID_SET: frozenset[str] = frozenset(_ALL_RULE_IDS)


# -----------------------------------------------------------------------------
# 规则内部判定参数校验规格
# -----------------------------------------------------------------------------
RULE_PARAM_SCHEMAS: dict[str, dict[str, tuple[type, int, int]]] = {
    "code.deep_control_flow": {
        "max_depth": (int, 2, 10),
    },
    "code.hardcoded_secret": {
        "min_length": (int, 4, 32),
    },
}


# -----------------------------------------------------------------------------
# 5 套场景化预设定义
# -----------------------------------------------------------------------------
PRESETS: dict[str, dict[str, Any]] = {
    PRESET_BALANCED: {
        "preset": PRESET_BALANCED,
        "name": "均衡基线",
        "description": "全量 29 条规则分层赋予 1~3 启发式分值，兼顾安全性、框架契约与代码健康度",
        "enabled_rules": list(_ALL_RULE_IDS),
        "rule_weights": {
            "api.signature_changed": 2,
            "auth.permission_structure_changed": 3,
            "data.transaction_structure_changed": 2,
            "config.configuration_structure_changed": 2,
            "code.exception_structure_changed": 2,
            "code.swallowed_exception": 2,
            "code.bare_exception": 2,
            "code.dynamic_execution": 3,
            "code.unmanaged_open": 2,
            "code.deep_control_flow": 2,
            "code.hardcoded_secret": 3,
            "code.global_mutable_state": 1,
            "data.django_raw_sql_execution": 2,
            "auth.django_csrf_exempt_added": 2,
            "api.drf_viewset_action_changed": 2,
            "data.django_destructive_migration": 3,
            "auth.drf_permission_policy_downgrade": 3,
            "config.django_sensitive_settings_changed": 2,
            "data.django_non_null_constraint_tightened": 2,
            "auth.drf_permission_decorator_removed": 3,
            "auth.drf_queryset_scope_tighten_bypassed": 2,
            "data.django_signal_receiver_leak": 1,
            "data.django_field_rename_without_db_column": 2,
            "api.drf_public_parameter_added": 1,
            "api.drf_public_parameter_removed": 2,
            "api.django_url_pattern_changed": 1,
            "code.assert_in_production": 1,
            "code.mutable_default_argument": 1,
            COLLABORATION_RULE_ID: 1,
        },
        "test_collaboration_weight": 1,
        "test_collaboration_enabled": True,
        "thresholds": {"medium": 30, "high": 65},
        "rule_thresholds": {
            "code.deep_control_flow": {"max_depth": 4},
            "code.hardcoded_secret": {"min_length": 8},
        },
    },
    PRESET_SECURITY_FOCUS: {
        "preset": PRESET_SECURITY_FOCUS,
        "name": "安全加固审查",
        "description": "聚焦认证权限降级、凭据泄露、CSRF 与危险执行等高危操作",
        "enabled_rules": list(_ALL_RULE_IDS),
        "rule_weights": {
            "api.signature_changed": 1,
            "auth.permission_structure_changed": 4,
            "data.transaction_structure_changed": 1,
            "config.configuration_structure_changed": 2,
            "code.exception_structure_changed": 1,
            "code.swallowed_exception": 1,
            "code.bare_exception": 1,
            "code.dynamic_execution": 4,
            "code.unmanaged_open": 3,
            "code.deep_control_flow": 1,
            "code.hardcoded_secret": 5,
            "code.global_mutable_state": 1,
            "data.django_raw_sql_execution": 4,
            "auth.django_csrf_exempt_added": 4,
            "api.drf_viewset_action_changed": 1,
            "data.django_destructive_migration": 1,
            "auth.drf_permission_policy_downgrade": 5,
            "config.django_sensitive_settings_changed": 4,
            "data.django_non_null_constraint_tightened": 1,
            "auth.drf_permission_decorator_removed": 5,
            "auth.drf_queryset_scope_tighten_bypassed": 3,
            "data.django_signal_receiver_leak": 1,
            "data.django_field_rename_without_db_column": 1,
            "api.drf_public_parameter_added": 1,
            "api.drf_public_parameter_removed": 1,
            "api.django_url_pattern_changed": 1,
            "code.assert_in_production": 2,
            "code.mutable_default_argument": 1,
            COLLABORATION_RULE_ID: 1,
        },
        "test_collaboration_weight": 1,
        "test_collaboration_enabled": True,
        "thresholds": {"medium": 25, "high": 55},
        "rule_thresholds": {
            "code.deep_control_flow": {"max_depth": 4},
            "code.hardcoded_secret": {"min_length": 6},
        },
    },
    PRESET_FRAMEWORK_UPGRADE: {
        "preset": PRESET_FRAMEWORK_UPGRADE,
        "name": "框架与迁移升级",
        "description": "聚焦破坏性迁移、数据库字段改名、URL 路由与公开 API 参数兼容性",
        "enabled_rules": list(_ALL_RULE_IDS),
        "rule_weights": {
            "api.signature_changed": 3,
            "auth.permission_structure_changed": 1,
            "data.transaction_structure_changed": 3,
            "config.configuration_structure_changed": 2,
            "code.exception_structure_changed": 1,
            "code.swallowed_exception": 1,
            "code.bare_exception": 1,
            "code.dynamic_execution": 1,
            "code.unmanaged_open": 1,
            "code.deep_control_flow": 1,
            "code.hardcoded_secret": 1,
            "code.global_mutable_state": 1,
            "data.django_raw_sql_execution": 1,
            "auth.django_csrf_exempt_added": 1,
            "api.drf_viewset_action_changed": 4,
            "data.django_destructive_migration": 5,
            "auth.drf_permission_policy_downgrade": 1,
            "config.django_sensitive_settings_changed": 1,
            "data.django_non_null_constraint_tightened": 4,
            "auth.drf_permission_decorator_removed": 1,
            "auth.drf_queryset_scope_tighten_bypassed": 1,
            "data.django_signal_receiver_leak": 2,
            "data.django_field_rename_without_db_column": 4,
            "api.drf_public_parameter_added": 3,
            "api.drf_public_parameter_removed": 4,
            "api.django_url_pattern_changed": 4,
            "code.assert_in_production": 1,
            "code.mutable_default_argument": 1,
            COLLABORATION_RULE_ID: 1,
        },
        "test_collaboration_weight": 1,
        "test_collaboration_enabled": True,
        "thresholds": {"medium": 30, "high": 65},
        "rule_thresholds": {
            "code.deep_control_flow": {"max_depth": 4},
            "code.hardcoded_secret": {"min_length": 8},
        },
    },
    PRESET_DAILY_REVIEW: {
        "preset": PRESET_DAILY_REVIEW,
        "name": "日常代码合规",
        "description": "聚焦测试覆盖协同、深层控制流、静默异常与可变默认参数等代码异味",
        "enabled_rules": list(_ALL_RULE_IDS),
        "rule_weights": {
            "api.signature_changed": 1,
            "auth.permission_structure_changed": 1,
            "data.transaction_structure_changed": 1,
            "config.configuration_structure_changed": 1,
            "code.exception_structure_changed": 2,
            "code.swallowed_exception": 4,
            "code.bare_exception": 4,
            "code.dynamic_execution": 1,
            "code.unmanaged_open": 3,
            "code.deep_control_flow": 4,
            "code.hardcoded_secret": 1,
            "code.global_mutable_state": 2,
            "data.django_raw_sql_execution": 1,
            "auth.django_csrf_exempt_added": 1,
            "api.drf_viewset_action_changed": 1,
            "data.django_destructive_migration": 1,
            "auth.drf_permission_policy_downgrade": 1,
            "config.django_sensitive_settings_changed": 1,
            "data.django_non_null_constraint_tightened": 1,
            "auth.drf_permission_decorator_removed": 1,
            "auth.drf_queryset_scope_tighten_bypassed": 1,
            "data.django_signal_receiver_leak": 1,
            "data.django_field_rename_without_db_column": 1,
            "api.drf_public_parameter_added": 1,
            "api.drf_public_parameter_removed": 1,
            "api.django_url_pattern_changed": 1,
            "code.assert_in_production": 3,
            "code.mutable_default_argument": 4,
            COLLABORATION_RULE_ID: 5,
        },
        "test_collaboration_weight": 5,
        "test_collaboration_enabled": True,
        "thresholds": {"medium": 30, "high": 60},
        "rule_thresholds": {
            "code.deep_control_flow": {"max_depth": 3},
            "code.hardcoded_secret": {"min_length": 8},
        },
    },
    PRESET_LEGACY_BASELINE: {
        "preset": PRESET_LEGACY_BASELINE,
        "name": "历史兼容基线",
        "description": "保持 v1.0~v1.2 初始 10 分满分基线（结构 9 分 + 协同 1 分），供历史测试与回归比对",
        "enabled_rules": list(_ALL_RULE_IDS),
        "rule_weights": {
            "api.signature_changed": 2,
            "auth.permission_structure_changed": 3,
            "data.transaction_structure_changed": 2,
            "config.configuration_structure_changed": 1,
            "code.exception_structure_changed": 1,
            "code.swallowed_exception": 0,
            "code.bare_exception": 0,
            "code.dynamic_execution": 0,
            "code.unmanaged_open": 0,
            "code.deep_control_flow": 0,
            "code.hardcoded_secret": 0,
            "code.global_mutable_state": 0,
            "data.django_raw_sql_execution": 0,
            "auth.django_csrf_exempt_added": 0,
            "api.drf_viewset_action_changed": 0,
            "data.django_destructive_migration": 0,
            "auth.drf_permission_policy_downgrade": 0,
            "config.django_sensitive_settings_changed": 0,
            "data.django_non_null_constraint_tightened": 0,
            "auth.drf_permission_decorator_removed": 0,
            "auth.drf_queryset_scope_tighten_bypassed": 0,
            "data.django_signal_receiver_leak": 0,
            "data.django_field_rename_without_db_column": 0,
            "api.drf_public_parameter_added": 0,
            "api.drf_public_parameter_removed": 0,
            "api.django_url_pattern_changed": 0,
            "code.assert_in_production": 0,
            "code.mutable_default_argument": 0,
            COLLABORATION_RULE_ID: 1,
        },
        "test_collaboration_weight": 1,
        "test_collaboration_enabled": True,
        "thresholds": {"medium": 30, "high": 65},
        "rule_thresholds": {
            "code.deep_control_flow": {"max_depth": 4},
            "code.hardcoded_secret": {"min_length": 8},
        },
    },
}

# 向后兼容常量：保持与历史 demo_service.DEFAULT_CONFIG 完全相同结构与键值
DEFAULT_CONFIG: dict[str, Any] = {
    "enabled_rules": list(_ALL_RULE_IDS),
    "rule_weights": copy.deepcopy(PRESETS[PRESET_LEGACY_BASELINE]["rule_weights"]),
    "test_collaboration_weight": 1,
    "test_collaboration_enabled": True,
    "thresholds": {"medium": 30, "high": 65},
}


def get_preset(preset_name: str) -> dict[str, Any]:
    """返回指定预设的独立深拷贝字典。"""
    if preset_name not in PRESETS:
        raise ValueError(f"未知预设: {preset_name}，可用预设: {sorted(PRESETS.keys())}")
    return copy.deepcopy(PRESETS[preset_name])


def list_presets() -> list[dict[str, Any]]:
    """返回所有可用预设的元数据清单（供前端选择器或 API 消费）。"""
    return [
        {
            "preset": item["preset"],
            "name": item["name"],
            "description": item["description"],
            "enabled_rule_count": len(item["enabled_rules"]),
            "thresholds": item["thresholds"],
            "rule_thresholds": item["rule_thresholds"],
        }
        for item in PRESETS.values()
    ]


def _validate_rule_thresholds(rule_thresholds: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """校验并规范化规则级内部参数。"""
    validated: dict[str, dict[str, Any]] = {}
    for rule_id, params in rule_thresholds.items():
        if rule_id not in _RULE_ID_SET:
            raise ValueError(f"rule_thresholds 包含未知规则: {rule_id}")
        if not isinstance(params, dict):
            raise ValueError(f"规则 {rule_id} 的参数配置必须是字典")
        schema = RULE_PARAM_SCHEMAS.get(rule_id, {})
        val_params: dict[str, Any] = {}
        for param_name, param_val in params.items():
            if param_name not in schema:
                raise ValueError(f"规则 {rule_id} 不支持参数: {param_name}")
            expected_type, min_v, max_v = schema[param_name]
            if not isinstance(param_val, expected_type) or isinstance(param_val, bool):
                raise ValueError(f"规则 {rule_id} 参数 {param_name} 类型必须为 {expected_type.__name__}")
            if not min_v <= param_val <= max_v:
                raise ValueError(f"规则 {rule_id} 参数 {param_name} 必须在 [{min_v}, {max_v}] 范围内，当前为 {param_val}")
            val_params[param_name] = param_val
        validated[rule_id] = val_params
    return validated


def normalize_audit_config(
    config: dict[str, Any] | None,
    default_preset: str = PRESET_LEGACY_BASELINE,
) -> dict[str, Any]:
    """标准化并严格校验审计配置。

    支持 preset 快速载入与字段细粒度覆盖（override）。
    default_preset 默认对齐 PRESET_LEGACY_BASELINE 以确保既有断言无缝兼容。
    """
    supplied = config or {}
    preset_name = supplied.get("preset", default_preset)
    base_preset = get_preset(preset_name)

    # 1. enabled_rules
    enabled_rules = supplied.get("enabled_rules", base_preset["enabled_rules"])
    if not isinstance(enabled_rules, list):
        raise ValueError("enabled_rules 必须是列表")
    for rule_id in enabled_rules:
        if rule_id not in _RULE_ID_SET:
            raise ValueError(f"enabled_rules 包含未知规则: {rule_id}")
    enabled_unique = list(dict.fromkeys(enabled_rules))

    # 2. rule_weights
    weights = {**base_preset["rule_weights"], **supplied.get("rule_weights", {})}
    for rule_id, weight in weights.items():
        if rule_id not in _RULE_ID_SET:
            raise ValueError(f"rule_weights 包含未知规则: {rule_id}")
        if not isinstance(weight, int) or isinstance(weight, bool) or not 0 <= weight <= 5:
            raise ValueError(f"规则权重必须是 0 到 5 的整数: {rule_id}={weight}")

    # 3. test_collaboration_weight
    supplied_weights = supplied.get("rule_weights") or {}
    if COLLABORATION_RULE_ID in supplied_weights and "test_collaboration_weight" not in supplied:
        collaboration_weight = supplied_weights[COLLABORATION_RULE_ID]
    else:
        collaboration_weight = supplied.get("test_collaboration_weight", base_preset["test_collaboration_weight"])

    if not isinstance(collaboration_weight, int) or isinstance(collaboration_weight, bool) or not 0 <= collaboration_weight <= 5:
        raise ValueError("测试协同权重必须是 0 到 5 的整数")
    weights[COLLABORATION_RULE_ID] = collaboration_weight

    # 4. thresholds (medium, high)
    thresholds = {**base_preset["thresholds"], **supplied.get("thresholds", {})}
    medium = thresholds.get("medium")
    high = thresholds.get("high")
    if not isinstance(medium, int) or isinstance(medium, bool) or not isinstance(high, int) or isinstance(high, bool) or not 0 <= medium < high <= 100:
        raise ValueError("风险阈值需满足 0 ≤ medium < high ≤ 100")

    result: dict[str, Any] = {
        "enabled_rules": enabled_unique,
        "rule_weights": weights,
        "test_collaboration_weight": collaboration_weight,
        "test_collaboration_enabled": bool(supplied.get("test_collaboration_enabled", base_preset["test_collaboration_enabled"])),
        "thresholds": {"medium": medium, "high": high},
    }

    # 5. rule_thresholds 与 preset 透传
    if "rule_thresholds" in supplied or "preset" in supplied or default_preset != PRESET_LEGACY_BASELINE:
        base_rule_thresholds = copy.deepcopy(base_preset.get("rule_thresholds", {}))
        supplied_rule_thresholds = supplied.get("rule_thresholds", {})
        merged_rule_thresholds = {**base_rule_thresholds}
        for r_id, p_dict in supplied_rule_thresholds.items():
            merged_rule_thresholds.setdefault(r_id, {}).update(p_dict)
        result["rule_thresholds"] = _validate_rule_thresholds(merged_rule_thresholds)

    if "preset" in supplied or default_preset != PRESET_LEGACY_BASELINE:
        result["preset"] = preset_name
        result["schema_version"] = CONFIG_SCHEMA_VERSION

    return result
