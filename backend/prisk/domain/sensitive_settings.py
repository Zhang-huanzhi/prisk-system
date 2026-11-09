"""Sensitive Django settings direction helpers.

Classifies unsafe/loosening vs tightening for the closed name list on
config.django_sensitive_settings_changed. Returns Unanalyzed when direction
cannot be read from an untruncated assignment slice. Does not promote lifecycle.
"""

from __future__ import annotations

import ast
import textwrap
from typing import Any


SENSITIVE_SETTING_NAMES: frozenset[str] = frozenset({
    "SECRET_KEY",
    "SECRET_KEY_FALLBACKS",
    "DEBUG",
    "ALLOWED_HOSTS",
    "DATABASES",
    "CSRF_COOKIE_SECURE",
    "SESSION_COOKIE_SECURE",
})


def _parse_assignment(segment: str) -> tuple[str | None, ast.AST | None]:
    prepared = textwrap.dedent(segment).strip("\n")
    if not prepared.strip():
        return None, None
    try:
        tree = ast.parse(prepared)
    except SyntaxError:
        return None, None
    if len(tree.body) != 1:
        return None, None
    statement = tree.body[0]
    if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
        return statement.targets[0].id, statement.value
    if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
        return statement.target.id, statement.value
    return None, None


def _const_bool(value: ast.AST | None) -> bool | None:
    if isinstance(value, ast.Constant) and isinstance(value.value, bool):
        return value.value
    return None


def _str_list_has_star(value: ast.AST | None) -> bool | None:
    if not isinstance(value, (ast.List, ast.Tuple)):
        return None
    texts: list[str] = []
    for element in value.elts:
        if isinstance(element, ast.Constant) and isinstance(element.value, str):
            texts.append(element.value)
        else:
            return None
    return "*" in texts


def _password_literal(value: ast.AST | None) -> str | None | object:
    missing = object()
    if not isinstance(value, ast.Dict):
        return missing
    for key, item in zip(value.keys, value.values):
        if isinstance(key, ast.Constant) and key.value == "default" and isinstance(item, ast.Dict):
            for nested_key, nested_value in zip(item.keys, item.values):
                if isinstance(nested_key, ast.Constant) and nested_key.value == "PASSWORD":
                    if isinstance(nested_value, ast.Constant) and isinstance(nested_value.value, str):
                        return nested_value.value
                    return None
            return None
        if isinstance(key, ast.Constant) and key.value == "PASSWORD":
            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                return item.value
            return None
    return missing


def classify_sensitive_direction(
    name: str,
    *,
    base_segment: str | None,
    head_segment: str | None,
    truncated: bool = False,
) -> dict[str, Any]:
    """Return direction: hit | not_found | unanalyzed for one sensitive setting."""
    if name not in SENSITIVE_SETTING_NAMES:
        return {"direction": "unanalyzed", "reason": "missing_framework_context", "setting_name": name}
    if truncated:
        return {"direction": "unanalyzed", "reason": "unsupported_stage04_details", "setting_name": name}
    head_name, head_value = _parse_assignment(head_segment or "")
    base_name, base_value = _parse_assignment(base_segment or "")
    if head_segment and head_name not in {None, name}:
        return {"direction": "unanalyzed", "reason": "unsupported_stage04_details", "setting_name": name}
    if head_segment and head_name is None and head_value is None:
        return {"direction": "unanalyzed", "reason": "unsupported_stage04_details", "setting_name": name}

    if name == "DEBUG":
        head_bool = _const_bool(head_value)
        base_bool = _const_bool(base_value)
        if head_bool is True and base_bool is not True:
            return {"direction": "hit", "reason": "loosened", "setting_name": name}
        if head_bool is False and base_bool is True:
            return {"direction": "not_found", "reason": "tightened", "setting_name": name}
        return {"direction": "unanalyzed", "reason": "unsupported_stage04_details", "setting_name": name}

    if name in {"CSRF_COOKIE_SECURE", "SESSION_COOKIE_SECURE"}:
        head_bool = _const_bool(head_value)
        base_bool = _const_bool(base_value)
        if head_bool is False and base_bool is not False:
            return {"direction": "hit", "reason": "loosened", "setting_name": name}
        if head_bool is True and base_bool is False:
            return {"direction": "not_found", "reason": "tightened", "setting_name": name}
        return {"direction": "unanalyzed", "reason": "unsupported_stage04_details", "setting_name": name}

    if name == "ALLOWED_HOSTS":
        head_star = _str_list_has_star(head_value)
        base_star = _str_list_has_star(base_value) if base_segment else False
        if head_star is None or (base_segment and base_star is None and base_value is not None):
            return {"direction": "unanalyzed", "reason": "unsupported_stage04_details", "setting_name": name}
        if head_star is True and base_star is not True:
            return {"direction": "hit", "reason": "loosened", "setting_name": name}
        if head_star is False and base_star is True:
            return {"direction": "not_found", "reason": "tightened", "setting_name": name}
        return {"direction": "unanalyzed", "reason": "unsupported_stage04_details", "setting_name": name}

    if name == "SECRET_KEY":
        head_str = head_value.value if isinstance(head_value, ast.Constant) and isinstance(head_value.value, str) else None
        base_str = base_value.value if isinstance(base_value, ast.Constant) and isinstance(base_value.value, str) else None
        if head_str and (base_str is None or head_str != base_str):
            return {"direction": "hit", "reason": "loosened", "setting_name": name}
        if base_str and head_value is not None and head_str is None:
            return {"direction": "not_found", "reason": "tightened", "setting_name": name}
        if head_segment is None and base_segment:
            return {"direction": "hit", "reason": "removed", "setting_name": name}
        return {"direction": "unanalyzed", "reason": "unsupported_stage04_details", "setting_name": name}

    if name == "SECRET_KEY_FALLBACKS":
        def _literal_strs(value: ast.AST | None) -> list[str] | None:
            if not isinstance(value, (ast.List, ast.Tuple)):
                return None
            out: list[str] = []
            for element in value.elts:
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    out.append(element.value)
                else:
                    return None
            return out
        head_list = _literal_strs(head_value)
        base_list = _literal_strs(base_value) if base_segment else []
        if head_list is None or (base_segment and base_list is None and base_value is not None):
            return {"direction": "unanalyzed", "reason": "unsupported_stage04_details", "setting_name": name}
        if head_list and (not base_list or any(item not in (base_list or []) for item in head_list)):
            return {"direction": "hit", "reason": "loosened", "setting_name": name}
        if base_list and (not head_list or len(head_list) < len(base_list)):
            return {"direction": "not_found", "reason": "tightened", "setting_name": name}
        return {"direction": "unanalyzed", "reason": "unsupported_stage04_details", "setting_name": name}

    if name == "DATABASES":
        missing = object()
        head_password = _password_literal(head_value)
        base_password = _password_literal(base_value) if base_segment else missing
        if head_password is missing or (base_segment and base_password is missing and base_value is not None):
            return {"direction": "unanalyzed", "reason": "unsupported_stage04_details", "setting_name": name}
        if isinstance(head_password, str) and head_password and head_password != base_password:
            return {"direction": "hit", "reason": "loosened", "setting_name": name}
        if isinstance(base_password, str) and base_password and head_password is None:
            return {"direction": "not_found", "reason": "tightened", "setting_name": name}
        return {"direction": "unanalyzed", "reason": "unsupported_stage04_details", "setting_name": name}

    return {"direction": "unanalyzed", "reason": "unsupported_stage04_details", "setting_name": name}
