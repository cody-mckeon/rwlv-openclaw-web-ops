# skills/asana/actions/generate_current_priorities.py

from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from skills.asana.actions.read_tasks import read_project_tasks


DEFAULT_OUTPUT_PATH = "CURRENT_PRIORITIES.generated.md"
LOGGER = logging.getLogger(__name__)

FIELD_ALIASES: Dict[str, List[str]] = {
    "health": ["Health / Execution", "Health", "Execution", "Status"],
    "priority": ["Priority"],
    "work_type": ["Work Type", "Type"],
    "target_ship": ["Target Ship", "Release Month", "Release", "Launch Month"],
    "ready_for_launch": ["Ready for Launch", "Ready for ...", "Ready for"],
}

SECTION_ALIASES: Dict[str, List[str]] = {
    "intake": ["Intake"],
    "triage_ready": ["Triage / Ready", "Triage", "Ready"],
    "in_progress": ["In Progress", "Doing", "Active"],
    "qa": ["QA", "Quality Assurance", "Review"],
    "ready_to_launch": ["Central / Ready to Launch", "Ready to Launch", "Launch Ready"],
    "done": ["Done", "Complete", "Completed"],
    "canceled": ["Canceled", "Cancelled"],
}

ACTIVE_SECTION_KEYS = {"in_progress"}
QA_SECTION_KEYS = {"qa"}
READY_TO_LAUNCH_SECTION_KEYS = {"ready_to_launch"}
INTAKE_SECTION_KEYS = {"intake"}
TRIAGE_SECTION_KEYS = {"triage_ready"}

BLOCKED_HEALTH_TERMS = ("blocked", "waiting", "on hold", "stalled")
CRITICAL_PRIORITY_TERMS = ("p0", "critical", "urgent", "emergency")
LOW_PRIORITY_TERMS = ("p3", "p4", "low", "someday")


def _setup_logging() -> None:
    level_name = os.getenv("PRIORITY_GOVERNOR_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _normalize_text(value).lower()).strip()


def _contains_any(value: str, terms: Iterable[str]) -> bool:
    normalized = _normalize_key(value)
    return any(_normalize_key(term) in normalized for term in terms)


def _custom_field_display_value(field: Dict[str, Any]) -> Optional[str]:
    """Return the best human-readable value for an Asana custom field."""
    for key in ("display_value", "text_value", "number_value"):
        value = field.get(key)
        if value not in (None, ""):
            return str(value)

    enum_value = field.get("enum_value") or {}
    if enum_value.get("name"):
        return str(enum_value["name"])

    multi_enum_values = field.get("multi_enum_values") or []
    enum_names = [value.get("name") for value in multi_enum_values if value.get("name")]
    if enum_names:
        return ", ".join(enum_names)

    date_value = field.get("date_value") or {}
    if date_value.get("date"):
        return str(date_value["date"])

    return None


def _custom_field_map(task: Dict[str, Any]) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    for field in task.get("custom_fields", []) or []:
        name = _normalize_text(field.get("name"))
        value = _custom_field_display_value(field)
        if name and value:
            fields[name] = value
    return fields


def _get_custom_field_value(task: Dict[str, Any], *field_names: str) -> Optional[str]:
    """Return a custom field display value by exact or normalized field alias."""
    aliases = [_normalize_text(name) for name in field_names if _normalize_text(name)]
    normalized_aliases = {_normalize_key(name) for name in aliases}

    for name, value in _custom_field_map(task).items():
        normalized_name = _normalize_key(name)
        if normalized_name in normalized_aliases:
            return value

    return None


def _get_field_by_alias(task: Dict[str, Any], field_key: str) -> Optional[str]:
    return _get_custom_field_value(task, *FIELD_ALIASES[field_key])


def _get_health(task: Dict[str, Any]) -> str:
    return _get_field_by_alias(task, "health") or "No Health"


def _get_status(task: Dict[str, Any]) -> str:
    # Backward-compatible name for generated markdown. The Asana board currently
    # exposes health/execution instead of a standalone Status field.
    return _get_health(task)


def _get_priority(task: Dict[str, Any]) -> str:
    return _get_field_by_alias(task, "priority") or "No Priority"


def _get_work_type(task: Dict[str, Any]) -> str:
    return _get_field_by_alias(task, "work_type") or "No Work Type"


def _get_target_ship(task: Dict[str, Any]) -> str:
    return _get_field_by_alias(task, "target_ship") or "No Target Ship"


def _get_ready_for_launch(task: Dict[str, Any]) -> str:
    return _get_field_by_alias(task, "ready_for_launch") or "No Ready Signal"


def _get_section_names(task: Dict[str, Any]) -> List[str]:
    """Return all section names associated with an Asana task."""
    sections: List[str] = []

    for membership in task.get("memberships", []) or []:
        section = membership.get("section") or {}
        section_name = _normalize_text(section.get("name"))
        if section_name:
            sections.append(section_name)

    return sections or ["No Section"]


def _canonical_section_name(section_name: str) -> str:
    normalized = _normalize_key(section_name)
    for canonical, aliases in SECTION_ALIASES.items():
        if any(_normalize_key(alias) == normalized for alias in aliases):
            return canonical
    return "unknown"


def _get_section_keys(task: Dict[str, Any]) -> List[str]:
    return [_canonical_section_name(section_name) for section_name in _get_section_names(task)]


def _get_assignee_name(task: Dict[str, Any]) -> str:
    assignee = task.get("assignee") or {}
    return assignee.get("name") or "Unassigned"


def _get_due_value(task: Dict[str, Any]) -> Optional[str]:
    return task.get("due_on") or task.get("due_at")


def _is_open(task: Dict[str, Any]) -> bool:
    return not bool(task.get("completed"))


def _section_matches(section_names: List[str], keywords: List[str]) -> bool:
    section_text = " ".join(section_names)
    return _contains_any(section_text, keywords)


def _task_name(task: Dict[str, Any]) -> str:
    return task.get("name") or "Untitled task"


@dataclass(frozen=True)
class TaskSignals:
    gid: str
    name: str
    sections: List[str]
    section_keys: List[str]
    assignee: str
    due: Optional[str]
    health: str
    priority: str
    work_type: str
    target_ship: str
    ready_for_launch: str
    custom_fields: Dict[str, str]


def _task_signals(task: Dict[str, Any]) -> TaskSignals:
    return TaskSignals(
        gid=str(task.get("gid") or "unknown"),
        name=_task_name(task),
        sections=_get_section_names(task),
        section_keys=_get_section_keys(task),
        assignee=_get_assignee_name(task),
        due=_get_due_value(task),
        health=_get_health(task),
        priority=_get_priority(task),
        work_type=_get_work_type(task),
        target_ship=_get_target_ship(task),
        ready_for_launch=_get_ready_for_launch(task),
        custom_fields=_custom_field_map(task),
    )


def _task_line(task: Dict[str, Any]) -> str:
    """Format one Asana task as a markdown bullet."""
    signals = _task_signals(task)
    due = signals.due or "No due date"
    sections = ", ".join(signals.sections)

    return (
        f"- {signals.name} | Assignee: {signals.assignee} | Due: {due} | "
        f"Section: {sections} | Status: {signals.health} | "
        f"Priority: {signals.priority} | Work Type: {signals.work_type} | "
        f"Target Ship: {signals.target_ship}"
    )


def _sort_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort tasks so dated tasks appear first, then undated tasks."""
    return sorted(
        tasks,
        key=lambda task: (
            _get_due_value(task) is None,
            _get_due_value(task) or "9999-12-31",
            _task_name(task),
        ),
    )


def _debug_task_classification(task: Dict[str, Any], buckets: List[str]) -> None:
    if not LOGGER.isEnabledFor(logging.DEBUG):
        return

    signals = _task_signals(task)
    LOGGER.debug(
        "task_classified %s",
        json.dumps(
            {
                "gid": signals.gid,
                "name": signals.name,
                "sections": signals.sections,
                "section_keys": signals.section_keys,
                "assignee": signals.assignee,
                "due": signals.due,
                "health": signals.health,
                "priority": signals.priority,
                "work_type": signals.work_type,
                "target_ship": signals.target_ship,
                "ready_for_launch": signals.ready_for_launch,
                "custom_field_names": sorted(signals.custom_fields.keys()),
                "buckets": buckets,
            },
            sort_keys=True,
        ),
    )


def classify_tasks(tasks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Classify Asana tasks using normalized Asana sections and custom fields.

    Priority logic:
    1. Sections are the strongest workflow signal.
    2. Health/status, priority, work type, and launch fields add context.
    3. A task may appear in more than one observability bucket when useful
       (for example, In Progress and Blocked / Waiting).
    4. Task-name keywords alone are not enough to create P0.
    """

    open_tasks = [task for task in tasks if _is_open(task)]

    p0_critical_confirmed: List[Dict[str, Any]] = []
    p1_active: List[Dict[str, Any]] = []
    p1_active_needs_cleanup: List[Dict[str, Any]] = []
    p2_intake_needs_triage: List[Dict[str, Any]] = []
    p2_scheduled_or_due: List[Dict[str, Any]] = []
    p3_backlog_low: List[Dict[str, Any]] = []
    blocked_or_waiting: List[Dict[str, Any]] = []
    due_dated: List[Dict[str, Any]] = []
    ready_for_review: List[Dict[str, Any]] = []
    hygiene_flags: List[Dict[str, Any]] = []
    unclassified: List[Dict[str, Any]] = []

    for task in open_tasks:
        signals = _task_signals(task)
        buckets: List[str] = []
        section_keys = set(signals.section_keys)

        if signals.due:
            due_dated.append(task)
            buckets.append("due_dated")

        if _contains_any(signals.health, BLOCKED_HEALTH_TERMS) or _section_matches(signals.sections, list(BLOCKED_HEALTH_TERMS)):
            blocked_or_waiting.append(task)
            buckets.append("blocked_or_waiting")

        if _contains_any(signals.priority, CRITICAL_PRIORITY_TERMS) or _contains_any(signals.health, ("critical", "emergency")):
            p0_critical_confirmed.append(task)
            buckets.append("p0_critical_confirmed")

        if section_keys.intersection(ACTIVE_SECTION_KEYS):
            p1_active.append(task)
            buckets.append("p1_active")
            if signals.health == "No Health" or signals.priority == "No Priority":
                p1_active_needs_cleanup.append(task)
                hygiene_flags.append(task)
                buckets.extend(["p1_active_needs_cleanup", "hygiene_flags"])

        if section_keys.intersection(QA_SECTION_KEYS | READY_TO_LAUNCH_SECTION_KEYS) or _contains_any(signals.ready_for_launch, ("yes", "ready")):
            ready_for_review.append(task)
            p2_scheduled_or_due.append(task)
            buckets.extend(["ready_for_review", "p2_scheduled_or_due"])

        if signals.due or signals.target_ship != "No Target Ship":
            if task not in p2_scheduled_or_due:
                p2_scheduled_or_due.append(task)
                buckets.append("p2_scheduled_or_due")

        if section_keys.intersection(INTAKE_SECTION_KEYS | TRIAGE_SECTION_KEYS):
            p2_intake_needs_triage.append(task)
            buckets.append("p2_intake_needs_triage")

        if _contains_any(signals.priority, LOW_PRIORITY_TERMS) and not signals.due and not section_keys.intersection(ACTIVE_SECTION_KEYS):
            p3_backlog_low.append(task)
            buckets.append("p3_backlog_low")

        if not buckets:
            # Unknown sections/fields should be visible instead of silently buried.
            p2_intake_needs_triage.append(task)
            hygiene_flags.append(task)
            unclassified.append(task)
            buckets.extend(["p2_intake_needs_triage", "hygiene_flags", "unclassified"])

        _debug_task_classification(task, buckets)

    LOGGER.info(
        "priority_governor_classification_counts %s",
        json.dumps(
            {
                "input_tasks": len(tasks),
                "open_tasks": len(open_tasks),
                "p0_critical_confirmed": len(p0_critical_confirmed),
                "p1_active": len(p1_active),
                "p1_active_needs_cleanup": len(p1_active_needs_cleanup),
                "p2_intake_needs_triage": len(p2_intake_needs_triage),
                "p2_scheduled_or_due": len(p2_scheduled_or_due),
                "p3_backlog_low": len(p3_backlog_low),
                "blocked_or_waiting": len(blocked_or_waiting),
                "due_dated": len(due_dated),
                "ready_for_review": len(ready_for_review),
                "hygiene_flags": len(hygiene_flags),
                "unclassified": len(unclassified),
            },
            sort_keys=True,
        ),
    )

    return {
        "p0_critical_confirmed": _sort_tasks(p0_critical_confirmed),
        "p1_active": _sort_tasks(p1_active),
        "p1_active_needs_cleanup": _sort_tasks(p1_active_needs_cleanup),
        "p2_intake_needs_triage": _sort_tasks(p2_intake_needs_triage),
        "p2_scheduled_or_due": _sort_tasks(p2_scheduled_or_due),
        "p3_backlog_low": _sort_tasks(p3_backlog_low),
        "blocked_or_waiting": _sort_tasks(blocked_or_waiting),
        "due_dated": _sort_tasks(due_dated),
        "ready_for_review": _sort_tasks(ready_for_review),
        "hygiene_flags": _sort_tasks(hygiene_flags),
        "unclassified": _sort_tasks(unclassified),
        "open_tasks": _sort_tasks(open_tasks),
    }


def group_tasks_by_section(tasks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for task in tasks:
        for section_name in _get_section_names(task):
            grouped[section_name].append(task)

    return dict(sorted(grouped.items(), key=lambda item: item[0].lower()))


def _render_debug_diagnostics(tasks: List[Dict[str, Any]]) -> List[str]:
    open_tasks = [task for task in tasks if _is_open(task)]
    section_counter: Counter[str] = Counter()
    custom_field_counter: Counter[str] = Counter()
    unknown_sections: Counter[str] = Counter()

    for task in open_tasks:
        signals = _task_signals(task)
        section_counter.update(signals.sections)
        custom_field_counter.update(signals.custom_fields.keys())
        for section_name, section_key in zip(signals.sections, signals.section_keys):
            if section_key == "unknown":
                unknown_sections.update([section_name])

    lines = [
        "## Debug Diagnostics",
        "",
        "Operational parsing summary for section and custom-field observability.",
        "",
        f"- Known section aliases: {', '.join(sorted(SECTION_ALIASES))}",
        f"- Custom field aliases: {json.dumps(FIELD_ALIASES, sort_keys=True)}",
        "",
        "### Open Task Sections Seen",
        "",
    ]

    if not section_counter:
        lines.append("- None found.")
    else:
        for section_name, count in sorted(section_counter.items(), key=lambda item: item[0].lower()):
            lines.append(f"- {section_name}: {count}")

    lines.extend(["", "### Custom Fields Seen", ""])
    if not custom_field_counter:
        lines.append("- None found.")
    else:
        for field_name, count in sorted(custom_field_counter.items(), key=lambda item: item[0].lower()):
            lines.append(f"- {field_name}: {count}")

    lines.extend(["", "### Unknown Sections", ""])
    if not unknown_sections:
        lines.append("- None found.")
    else:
        for section_name, count in sorted(unknown_sections.items(), key=lambda item: item[0].lower()):
            lines.append(f"- {section_name}: {count}")

    lines.append("")
    return lines


def render_current_priorities_markdown(
    project_gid: str,
    tasks: List[Dict[str, Any]],
    include_debug: bool = False,
) -> str:
    today = date.today().isoformat()
    classified = classify_tasks(tasks)
    grouped = group_tasks_by_section([task for task in tasks if _is_open(task)])

    lines: List[str] = []

    lines.append("# CURRENT_PRIORITIES.generated.md")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This file is auto-generated from Asana task data for the Priority Governor Agent."
    )
    lines.append("")
    lines.append("Asana remains the source of truth.")
    lines.append("")
    lines.append("Do not manually edit this file. Regenerate it from Asana instead.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Snapshot Metadata")
    lines.append("")
    lines.append(f"- Generated on: {today}")
    lines.append(f"- Asana project GID: `{project_gid}`")
    lines.append(f"- Total tasks pulled: {len(tasks)}")
    lines.append(f"- Open tasks: {len(classified['open_tasks'])}")
    lines.append(f"- Tasks with due dates: {len(classified['due_dated'])}")
    lines.append(f"- P0 critical confirmed: {len(classified['p0_critical_confirmed'])}")
    lines.append(f"- P1 active: {len(classified['p1_active'])}")
    lines.append(f"- P1 active needing cleanup: {len(classified['p1_active_needs_cleanup'])}")
    lines.append(f"- P2 intake needing triage: {len(classified['p2_intake_needs_triage'])}")
    lines.append(f"- P2 scheduled/due/review: {len(classified['p2_scheduled_or_due'])}")
    lines.append(f"- Ready for QA/review: {len(classified['ready_for_review'])}")
    lines.append(f"- Blocked/waiting: {len(classified['blocked_or_waiting'])}")
    lines.append("")

    sections = [
        (
            "P0 / Critical Confirmed",
            classified["p0_critical_confirmed"],
            "Tasks with explicit Critical/P0 priority or Critical/Emergency health. Task-name keywords alone do not qualify.",
        ),
        (
            "P1 / Active In Progress",
            classified["p1_active"],
            "Open tasks in the In Progress section. Health/status values are displayed as context instead of excluding active work.",
        ),
        (
            "P1 Review / Active but Field Mismatch",
            classified["p1_active_needs_cleanup"],
            "In Progress tasks missing expected Health/Status or Priority fields. These may need Asana field cleanup.",
        ),
        (
            "P2 / Intake Needs Triage",
            classified["p2_intake_needs_triage"],
            "Tasks in Intake or Triage / Ready that should be prioritized, clarified, scheduled, or deferred.",
        ),
        (
            "P2 / Scheduled or Due-Dated",
            classified["p2_scheduled_or_due"],
            "Tasks with due dates, target ship/release dates, QA/review placement, ready-to-launch placement, or ready-for-launch signals.",
        ),
        (
            "P3 / Backlog or Low Priority",
            classified["p3_backlog_low"],
            "Low-priority or low-urgency work that should not interrupt active work.",
        ),
        (
            "Blocked / Waiting",
            classified["blocked_or_waiting"],
            "Tasks that appear blocked, waiting, stalled, or on hold. They may also appear in active work if they are in In Progress.",
        ),
        (
            "Due-Dated Tasks",
            classified["due_dated"],
            "Open tasks with due dates. These may need priority review.",
        ),
        (
            "Ready for QA / Review",
            classified["ready_for_review"],
            "Open tasks in QA, ready-to-launch, or explicit ready-for-launch states.",
        ),
        (
            "Asana Hygiene Flags",
            classified["hygiene_flags"],
            "Tasks where workflow, section, or custom-field signals appear missing or inconsistent.",
        ),
    ]

    for heading, task_list, description in sections:
        lines.append(f"## {heading}")
        lines.append("")
        lines.append(description)
        lines.append("")

        if not task_list:
            lines.append("- None found.")
        else:
            for task in task_list:
                lines.append(_task_line(task))

        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Open Tasks by Asana Section")
    lines.append("")

    if not grouped:
        lines.append("- No open tasks found.")
    else:
        for section_name, section_tasks in grouped.items():
            lines.append(f"### {section_name}")
            lines.append("")
            for task in _sort_tasks(section_tasks):
                lines.append(_task_line(task))
            lines.append("")

    if include_debug:
        lines.append("---")
        lines.append("")
        lines.extend(_render_debug_diagnostics(tasks))

    lines.append("---")
    lines.append("")
    lines.append("## Notes for Priority Governor")
    lines.append("")
    lines.append(
        "- Treat this generated file as a current Asana snapshot, not a final business decision."
    )
    lines.append(
        "- Use section, assignee, due date, health/status, priority, work type, and launch signals as priority inputs, but do not over-trust any single field."
    )
    lines.append(
        "- If a new request conflicts with P1 or due-dated work, call out the tradeoff."
    )
    lines.append(
        "- If a request is vague or missing launch context, classify it as Needs Clarification unless there is clear risk."
    )
    lines.append("- Do not assume Asana section names perfectly represent priority.")
    lines.append("")

    return "\n".join(lines)


def generate_current_priorities(
    project_gid: Optional[str] = None,
    output_path: str = DEFAULT_OUTPUT_PATH,
    limit: int = 100,
    include_debug: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Pull Asana tasks and generate CURRENT_PRIORITIES.generated.md.

    This action is read-only against Asana.
    It writes only to a local generated markdown file.
    """

    _setup_logging()
    project_gid = project_gid or os.getenv("ASANA_TEST_PROJECT_GID")
    include_debug = (
        include_debug
        if include_debug is not None
        else os.getenv("PRIORITY_GOVERNOR_DEBUG") == "1"
    )

    if not project_gid:
        raise ValueError(
            "Missing project_gid. Pass project_gid or set ASANA_TEST_PROJECT_GID."
        )

    result = read_project_tasks(project_gid=project_gid, limit=limit)
    tasks = result.get("data", [])

    markdown = render_current_priorities_markdown(
        project_gid=project_gid,
        tasks=tasks,
        include_debug=include_debug,
    )

    output = Path(output_path)
    output.write_text(markdown, encoding="utf-8")

    LOGGER.info(
        "wrote_priority_snapshot path=%s task_count=%s include_debug=%s",
        output,
        len(tasks),
        include_debug,
    )

    return {
        "ok": True,
        "action": "asana.generate_current_priorities",
        "summary": f"Wrote {output_path} using {len(tasks)} Asana tasks.",
        "project_gid": project_gid,
        "output_path": str(output),
        "task_count": len(tasks),
        "errors": [],
    }


def main() -> None:
    result = generate_current_priorities()
    print(result["summary"])


if __name__ == "__main__":
    main()
