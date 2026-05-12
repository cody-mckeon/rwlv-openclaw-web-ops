# skills/asana/actions/generate_current_priorities.py

from __future__ import annotations

import os
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from skills.asana.actions.read_tasks import read_project_tasks


DEFAULT_OUTPUT_PATH = "CURRENT_PRIORITIES.generated.md"

# Add Custom Field Helpers for Priority Fix
def _get_custom_field_value(task: Dict[str, Any], field_name: str) -> Optional[str]:
    """Return a custom field display value by field name."""
    target = field_name.strip().lower()

    for field in task.get("custom_fields", []) or []:
        name = (field.get("name") or "").strip().lower()
        if name == target:
            return field.get("display_value")

    return None


def _get_status(task: Dict[str, Any]) -> str:
    return _get_custom_field_value(task, "Status") or "No Status"


def _get_priority(task: Dict[str, Any]) -> str:
    return _get_custom_field_value(task, "Priority") or "No Priority"


def _get_work_type(task: Dict[str, Any]) -> str:
    return _get_custom_field_value(task, "Work Type") or "No Work Type"


def _get_target_ship(task: Dict[str, Any]) -> str:
    return _get_custom_field_value(task, "Target Ship") or "No Target Ship"


def _has_section(task: Dict[str, Any], section_name: str) -> bool:
    target = section_name.strip().lower()
    return any(section.strip().lower() == target for section in _get_section_names(task))


def _is_status(task: Dict[str, Any], *statuses: str) -> bool:
    task_status = _get_status(task).strip().lower()
    return task_status in {status.strip().lower() for status in statuses}


def _is_priority(task: Dict[str, Any], *priorities: str) -> bool:
    task_priority = _get_priority(task).strip().lower()
    return task_priority in {priority.strip().lower() for priority in priorities}


def _is_work_type(task: Dict[str, Any], *work_types: str) -> bool:
    task_work_type = _get_work_type(task).strip().lower()
    return task_work_type in {work_type.strip().lower() for work_type in work_types}
    
def _get_section_names(task: Dict[str, Any]) -> List[str]:
    """Return all section names associated with an Asana task."""
    sections: List[str] = []

    for membership in task.get("memberships", []) or []:
        section = membership.get("section") or {}
        section_name = section.get("name")
        if section_name:
            sections.append(section_name)

    return sections or ["No Section"]


def _get_assignee_name(task: Dict[str, Any]) -> str:
    assignee = task.get("assignee") or {}
    return assignee.get("name") or "Unassigned"


def _get_due_value(task: Dict[str, Any]) -> Optional[str]:
    return task.get("due_on") or task.get("due_at")


def _is_open(task: Dict[str, Any]) -> bool:
    return not bool(task.get("completed"))


def _has_due_date(task: Dict[str, Any]) -> bool:
    return bool(_get_due_value(task))


def _section_matches(section_names: List[str], keywords: List[str]) -> bool:
    section_text = " ".join(section_names).lower()
    return any(keyword.lower() in section_text for keyword in keywords)


def _task_line(task: Dict[str, Any]) -> str:
    """Format one Asana task as a markdown bullet."""
    name = task.get("name") or "Untitled task"
    assignee = _get_assignee_name(task)
    due = _get_due_value(task) or "No due date"
    sections = ", ".join(_get_section_names(task))
    status = _get_status(task)
    priority = _get_priority(task)
    work_type = _get_work_type(task)
    target_ship = _get_target_ship(task)

    return (
        f"- {name} | Assignee: {assignee} | Due: {due} | "
        f"Section: {sections} | Status: {status} | "
        f"Priority: {priority} | Work Type: {work_type} | "
        f"Target Ship: {target_ship}"
    )

def _sort_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort tasks so dated tasks appear first, then undated tasks.
    """
    return sorted(
        tasks,
        key=lambda task: (
            _get_due_value(task) is None,
            _get_due_value(task) or "9999-12-31",
            task.get("name") or "",
        ),
    )


def classify_tasks(tasks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Classify Asana tasks using structured Asana fields first.

    Priority logic:
    1. Section is the strongest operational signal.
    2. Status confirms or contradicts the section.
    3. Priority and Work Type add business context.
    4. Due dates and target ship dates add urgency.
    5. Task-name keywords are not enough to create P0.
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
    hygiene_flags: List[Dict[str, Any]] = []

    for task in open_tasks:
        due = _get_due_value(task)
        status = _get_status(task).lower()
        priority = _get_priority(task).lower()
        work_type = _get_work_type(task).lower()
        task_name = (task.get("name") or "").lower()

        in_intake = _has_section(task, "Intake")
        in_progress = _has_section(task, "In Progress")
        in_scheduled = _has_section(task, "Scheduled")

        if due:
            due_dated.append(task)

        # Blocked/waiting should be separated before normal prioritization.
        if (
            "blocked" in status
            or "waiting" in status
            or "on hold" in status
            or "blocked" in task_name
            or "waiting" in task_name
            or _section_matches(_get_section_names(task), ["blocked", "waiting", "on hold"])
        ):
            blocked_or_waiting.append(task)
            continue

        # P0 should be confirmed by structured fields, not just task name.
        # Keep this narrow.
        if (
            _is_priority(task, "Critical", "P0")
            or _is_status(task, "Critical", "Emergency")
        ):
            p0_critical_confirmed.append(task)
            continue

        # In Progress section takes precedence.
        if in_progress:
            if _is_status(task, "In Progress", "Ready for Work", "Ready", "Active"):
                p1_active.append(task)
            else:
                p1_active_needs_cleanup.append(task)
                hygiene_flags.append(task)
            continue

        # Scheduled section or dated work.
        if in_scheduled or due or _get_target_ship(task) != "No Target Ship":
            p2_scheduled_or_due.append(task)
            continue

        # Intake section needs triage. Priority/work type can affect how seriously it is reviewed,
        # but it should not automatically interrupt active work.
        if in_intake:
            p2_intake_needs_triage.append(task)
            continue

        # Low priority tasks are backlog by default.
        if _is_priority(task, "Low") and not due:
            p3_backlog_low.append(task)
            continue

        # New builds, analytics, optimization, maintenance, etc. are useful,
        # but without active/scheduled signals they are P2 review items.
        if any(
            value in work_type
            for value in ["new build", "analytics", "optimization", "maintenance", "redesign"]
        ):
            p2_intake_needs_triage.append(task)
            continue

        # Default: do not pretend unknown work is urgent.
        p2_intake_needs_triage.append(task)

    return {
        "p0_critical_confirmed": _sort_tasks(p0_critical_confirmed),
        "p1_active": _sort_tasks(p1_active),
        "p1_active_needs_cleanup": _sort_tasks(p1_active_needs_cleanup),
        "p2_intake_needs_triage": _sort_tasks(p2_intake_needs_triage),
        "p2_scheduled_or_due": _sort_tasks(p2_scheduled_or_due),
        "p3_backlog_low": _sort_tasks(p3_backlog_low),
        "blocked_or_waiting": _sort_tasks(blocked_or_waiting),
        "due_dated": _sort_tasks(due_dated),
        "hygiene_flags": _sort_tasks(hygiene_flags),
        "open_tasks": _sort_tasks(open_tasks),
    }


def group_tasks_by_section(tasks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for task in tasks:
        for section_name in _get_section_names(task):
            grouped[section_name].append(task)

    return dict(sorted(grouped.items(), key=lambda item: item[0].lower()))


def render_current_priorities_markdown(
    project_gid: str,
    tasks: List[Dict[str, Any]],
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
    lines.append("")

    sections = [
        (
            "P0 / Critical Confirmed",
            classified["p0_critical_confirmed"],
            "Only tasks with explicit Critical/P0 priority or Critical/Emergency status. Task-name keywords alone do not qualify.",
        ),
        (
            "P1 / Active In Progress",
            classified["p1_active"],
            "Tasks in the In Progress section with an active status such as In Progress, Ready for Work, Ready, or Active.",
        ),
        (
            "P1 Review / Active but Field Mismatch",
            classified["p1_active_needs_cleanup"],
            "Tasks in the In Progress section where Status does not confirm active work. These may need Asana field cleanup.",
        ),
        (
            "P2 / Intake Needs Triage",
            classified["p2_intake_needs_triage"],
            "Tasks in Intake or reviewable work that should be prioritized, clarified, scheduled, or deferred.",
        ),
        (
            "P2 / Scheduled or Due-Dated",
            classified["p2_scheduled_or_due"],
            "Tasks with due dates, target ship dates, or Scheduled section placement.",
        ),
        (
            "P3 / Backlog or Low Priority",
            classified["p3_backlog_low"],
            "Low-priority or low-urgency work that should not interrupt active work.",
        ),
        (
            "Blocked / Waiting",
            classified["blocked_or_waiting"],
            "Tasks that appear blocked, waiting, or on hold.",
        ),
        (
            "Due-Dated Tasks",
            classified["due_dated"],
            "Open tasks with due dates. These may need priority review.",
        ),
        (
            "Asana Hygiene Flags",
            classified["hygiene_flags"],
            "Tasks where section/status/priority signals appear inconsistent.",
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

    lines.append("---")
    lines.append("")
    lines.append("## Notes for Priority Governor")
    lines.append("")
    lines.append(
        "- Treat this generated file as a current Asana snapshot, not a final business decision."
    )
    lines.append(
        "- Use section, assignee, due date, and task name as priority signals, but do not over-trust them."
    )
    lines.append(
        "- If a new request conflicts with P1 or due-dated work, call out the tradeoff."
    )
    lines.append(
        "- If a request is vague or missing launch context, classify it as Needs Clarification unless there is clear risk."
    )
    lines.append(
        "- Do not assume Asana section names perfectly represent priority."
    )
    lines.append("")

    return "\n".join(lines)


def generate_current_priorities(
    project_gid: Optional[str] = None,
    output_path: str = DEFAULT_OUTPUT_PATH,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Pull Asana tasks and generate CURRENT_PRIORITIES.generated.md.

    This action is read-only against Asana.
    It writes only to a local generated markdown file.
    """

    project_gid = project_gid or os.getenv("ASANA_TEST_PROJECT_GID")

    if not project_gid:
        raise ValueError(
            "Missing project_gid. Pass project_gid or set ASANA_TEST_PROJECT_GID."
        )

    result = read_project_tasks(project_gid=project_gid, limit=limit)
    tasks = result.get("data", [])

    markdown = render_current_priorities_markdown(
        project_gid=project_gid,
        tasks=tasks,
    )

    output = Path(output_path)
    output.write_text(markdown, encoding="utf-8")

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
