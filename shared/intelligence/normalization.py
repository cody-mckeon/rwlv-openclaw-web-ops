from __future__ import annotations

import re
from typing import Any, Dict, Iterable


def _collapse(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def normalize_priority_value(raw_priority: str | None) -> str:
    """Convert raw Asana priority labels into canonical operational values."""
    collapsed = _collapse(raw_priority or "")

    if not collapsed:
        return "unknown"

    match = re.match(r"p\s*([0-4])\b", collapsed)
    if match:
        return f"p{match.group(1)}"

    legacy_map = {
        "critical": "p0",
        "high": "p1",
        "medium": "p2",
        "low": "p3",
    }
    return legacy_map.get(collapsed, "unknown")


def extract_priority_raw(task: Dict[str, Any]) -> str:
    for field in task.get("custom_fields", []):
        if (field.get("name") or "").strip().lower() != "priority":
            continue
        return (
            field.get("display_value")
            or (field.get("enum_value") or {}).get("name")
            or field.get("text_value")
            or ""
        )
    return ""


def normalize_section_value(raw_section: str | None) -> str:
    value = _collapse(raw_section or "")
    if value == "in progress":
        return "in_progress"
    return value.replace(" ", "_") if value else "unknown"


def get_task_section_raw(task: Dict[str, Any]) -> str:
    memberships: Iterable[Dict[str, Any]] = task.get("memberships", [])
    for membership in memberships:
        section = (membership.get("section") or {}).get("name")
        if section:
            return section
    return ""


def canonicalize_task(task: Dict[str, Any]) -> Dict[str, Any]:
    raw_priority = extract_priority_raw(task)
    raw_section = get_task_section_raw(task)
    normalized_priority = normalize_priority_value(raw_priority)
    normalized_section = normalize_section_value(raw_section)

    return {
        **task,
        "raw_priority": raw_priority,
        "normalized_priority": normalized_priority,
        "raw_section": raw_section,
        "normalized_section": normalized_section,
    }
