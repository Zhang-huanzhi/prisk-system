"""Known framework base last-segment equality mappings.

Reads the design table from docs/rules/known-framework-bases.md as a closed
equality map. Unlisted last segments stay unresolved (Unanalyzed for rules
that require a native base). This module does not expand Hit surfaces.
"""

from __future__ import annotations

from typing import Any


# Last-segment equality only. Substring / suffix matching is forbidden.
KNOWN_FRAMEWORK_BASE_MAP: dict[str, str] = {
    "PrimaryModelSerializer": "ModelSerializer",
    "NetBoxModelViewSet": "ModelViewSet",
    "NetBoxModel": "Model",
}

NATIVE_FRAMEWORK_BASES: frozenset[str] = frozenset({
    "Serializer",
    "ModelSerializer",
    "ViewSet",
    "GenericViewSet",
    "ModelViewSet",
    "ReadOnlyModelViewSet",
    "Model",
})


def last_segment(expression: str | None) -> str | None:
    """Return the final dotted identifier segment, or None when unreadable."""
    if not isinstance(expression, str):
        return None
    text = expression.strip()
    if not text:
        return None
    # Strip call suffixes such as PrimaryModelSerializer(...) if ever passed.
    if "(" in text:
        text = text.split("(", 1)[0].strip()
    if not text:
        return None
    segment = text.replace("\\", "/").rsplit(".", 1)[-1].strip()
    if not segment or not segment.isidentifier():
        return None
    return segment


def resolve_framework_base(expression: str | None) -> dict[str, Any]:
    """Resolve one base expression via last-segment equality.

    Returns:
      status: "native" | "mapped" | "unlisted" | "unreadable"
      last_segment / native_base when known
    """
    segment = last_segment(expression)
    if segment is None:
        return {"status": "unreadable", "last_segment": None, "native_base": None}
    if segment in NATIVE_FRAMEWORK_BASES:
        return {"status": "native", "last_segment": segment, "native_base": segment}
    mapped = KNOWN_FRAMEWORK_BASE_MAP.get(segment)
    if mapped is not None:
        return {"status": "mapped", "last_segment": segment, "native_base": mapped}
    return {"status": "unlisted", "last_segment": segment, "native_base": None}


def resolve_class_bases(base_expressions: list[str | None] | None) -> dict[str, Any]:
    """Resolve every class base expression. Unlisted names stay Unanalyzed."""
    expressions = list(base_expressions or [])
    resolved = [resolve_framework_base(item) for item in expressions]
    native_or_mapped = [
        item["native_base"]
        for item in resolved
        if item.get("native_base")
    ]
    unlisted = [
        item["last_segment"]
        for item in resolved
        if item.get("status") == "unlisted" and item.get("last_segment")
    ]
    unreadable = any(item.get("status") == "unreadable" for item in resolved)
    return {
        "base_expressions": expressions,
        "resolved_bases": resolved,
        "native_or_mapped_bases": native_or_mapped,
        "unlisted_last_segments": unlisted,
        "has_unreadable_base": unreadable,
    }
