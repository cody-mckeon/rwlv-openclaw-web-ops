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

def _get_custom_field_value(task: Dict[str, Any], field_name: str) -> Optional[str]:
    """Return a custom field display value by exact field name."""
    target = field_name.strip().lower()

    for field in task.get("custom_fields", []) or []:
        name = (field.get("name") or "").strip().lower()
        if name == target:
            return field.get("display_value")

    return None


def _get_execution_status(task: Dict[str, Any]) -> str:
    """
    Return the task's health / execution status.

    Supports slight naming differences in Asana custom fields.
    """
    return (
        _get_custom_field_value(task, "Health and Execution Status")
        or _get_custom_field_value(task, "Field Health and Execution Status")
        or _get_custom_field_value(task, "Execution Status")
        or _get_custom_field_value(task, "Health")
        or _get_custom_field_value(task, "Health / Execution Status")
        or "No Health Status"
    )


def _get_priority(task: Dict[str, Any]) -> str:
    return _get_custom_field_value(task, "Priority") or "No Priority"


def _get_work_type(task: Dict[str, Any]) -> str:
    return _get_custom_field_value(task, "Work Type") or "No Work Type"


def _get_release_month(task: Dict[str, Any]) -> str:
    return _get_custom_field_value(task, "Release Month") or "No Release Month"


def _get_vendor(task: Dict[str, Any]) -> str:
    return _get_custom_field_value(task, "Vendor") or "No Vendor"


def _get_ready_for_vendor(task: Dict[str, Any]) -> str:
    return _get_custom_field_value(task, "Ready for Vendor") or "No"


def _get_property(task: Dict[str, Any]) -> str:
    return _get_custom_field_value(task, "Property") or "No Property"


def _has_section(task: Dict[str, Any], section_name: str) -> bool:
    target = section_name.strip().lower()
    return any(section.strip().lower() == target for section in _get_section_names(task))


def _is_execution_status(task: Dict[str, Any], *statuses: str) -> bool:
    execution_status = _get_execution_status(task).strip().lower()
    return execution_status in {status.strip().lower() for status in statuses}


def _normalize_priority(task: Dict[str, Any]) -> str:
    value = _get_priority(task).strip().lower()

    if value.startswith("p0"):
        return "P0"
    if value.startswith("p1"):
        return "P1"
    if value.startswith("p2"):
        return "P2"
    if value.startswith("p3"):
        return "P3"
    if value.startswith("p4"):
        return "P4"

    # Legacy fallback while old values still exist.
    if value == "critical":
        return "P0"
    if value == "high":
        return "P1"
    if value == "medium":
        return "P2"
    if value == "low":
        return "P3"

    return "NO_PRIORITY"


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
    execution_status = _get_execution_status(task)
    priority = _get_priority(task)
    work_type = _get_work_type(task)
    release_month = _get_release_month(task)
    vendor = _get_vendor(task)
    ready_for_vendor = _get_ready_for_vendor(task)
    property_value = _get_property(task)
    subtask_count = task.get("num_subtasks", 0)
    gid = task.get("gid") or "No GID"

    return (
        f"- {name} | Assignee: {assignee} | Due: {due} | "
        f"Section: {sections} | Health: {execution_status} | "
        f"Priority: {priority} | Work Type: {work_type} | "
        f"Release Month: {release_month} | Vendor: {vendor} | "
        f"Ready for Vendor: {ready_for_vendor} | Property: {property_value} | "
        f"Subtasks: {subtask_count} | GID: {gid}"fxy
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
    Classify Asana tasks using the current RWLV web ops workflow.

    Strongest signals:
    1. Section
    2. Field Health and Execution Status
    3. Priority
    4. Due date
    5. Release Month
    6. Work Type
    """

    open_tasks = [task for task in tasks if _is_open(task)]

    p0_interrupt: List[Dict[str, Any]] = []
    p1_active_committed: List[Dict[str, Any]] = []
    qa_review: List[Dict[str, Any]] = []
    scheduled_ready_to_launch: List[Dict[str, Any]] = []
    triage_ready: List[Dict[str, Any]] = []
    intake: List[Dict[str, Any]] = []
    blocked_waiting_at_risk: List[Dict[str, Any]] = []
    date_visible: List[Dict[str, Any]] = []
    hygiene_flags: List[Dict[str, Any]] = []
    backlog_parking: List[Dict[str, Any]] = []

    for task in open_tasks:
        priority_level = _normalize_priority(task)
        execution_status = _get_execution_status(task).lower()
        due = _get_due_value(task)
        release_month = _get_release_month(task)

        in_intake = _has_section(task, "Intake")
        in_triage_ready = _has_section(task, "Triage/Ready")
        in_progress = _has_section(task, "In Progress")
        in_qa = _has_section(task, "QA")
        in_scheduled = _has_section(task, "Scheduled / Ready to Launch")
        in_done = _has_section(task, "Done")
        in_canceled = _has_section(task, "Canceled")

        if in_done or in_canceled:
            continue

        if due or release_month != "No Release Month":
            date_visible.append(task)

        if execution_status in {
            "blocked",
            "waiting on vendor",
            "waiting on content",
            "waiting on stakeholder",
            "waiting approval",
            "at risk",
            "expedited",
        }:
            blocked_waiting_at_risk.append(task)

        # P0 means interrupt. Keep this explicit and visible.
        if priority_level == "P0":
            p0_interrupt.append(task)
            continue

        # QA is active review work and should be protected.
        if in_qa:
            qa_review.append(task)
            continue

        # Ready to launch is not intake. It is late-stage committed work.
        if in_scheduled:
            scheduled_ready_to_launch.append(task)
            continue

        # In Progress means active committed work.
        if in_progress:
            if priority_level in {"P1", "P2", "P3", "P4", "NO_PRIORITY"}:
                p1_active_committed.append(task)

            # Hygiene check: active work should usually not be backlog/parking/no priority.
            if priority_level in {"P3", "P4", "NO_PRIORITY"}:
                hygiene_flags.append(task)

            continue

        # Triage/Ready means it has enough shape to review and schedule.
        if in_triage_ready:
            triage_ready.append(task)
            continue

        # Intake is captured but not yet fully prioritized.
        if in_intake:
            intake.append(task)
            continue

        if priority_level in {"P3", "P4"}:
            backlog_parking.append(task)
            continue

        # Default unknowns should be triage, not active.
        triage_ready.append(task)

    return {
        "p0_interrupt": _sort_tasks(p0_interrupt),
        "p1_active_committed": _sort_tasks(p1_active_committed),
        "qa_review": _sort_tasks(qa_review),
        "scheduled_ready_to_launch": _sort_tasks(scheduled_ready_to_launch),
        "triage_ready": _sort_tasks(triage_ready),
        "intake": _sort_tasks(intake),
        "blocked_waiting_at_risk": _sort_tasks(blocked_waiting_at_risk),
        "date_visible": _sort_tasks(date_visible),
        "hygiene_flags": _sort_tasks(hygiene_flags),
        "backlog_parking": _sort_tasks(backlog_parking),
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
    lines.append(f"- Tasks with due dates: {len(classified['date_visible'])}")
    lines.append(f"- P0 interrupt work: {len(classified['p0_interrupt'])}")
    lines.append(f"- P1 active committed work: {len(classified['p1_active_committed'])}")
    lines.append(f"- QA / review: {len(classified['qa_review'])}")
    lines.append(f"- Scheduled / ready to launch: {len(classified['scheduled_ready_to_launch'])}")
    lines.append(f"- Triage / ready: {len(classified['triage_ready'])}")
    lines.append(f"- Intake: {len(classified['intake'])}")
    lines.append(f"- Blocked / waiting / at risk: {len(classified['blocked_waiting_at_risk'])}")
    lines.append(f"- Backlog / parking: {len(classified['backlog_parking'])}")
    lines.append(f"- Asana hygiene flags: {len(classified['hygiene_flags'])}")
    lines.append("")

    sections = [
        (
            "P0 / Interrupt Work",
            classified["p0_interrupt"],
            "Tasks marked P0. These may justify interrupting current work.",
        ),
        (
            "P1 / Active Committed Work",
            classified["p1_active_committed"],
            "Tasks in the In Progress section. This is the work to protect from new intake.",
        ),
        (
            "QA / Review",
            classified["qa_review"],
            "Tasks in QA that need validation, review, approval, or final checks.",
        ),
        (
            "Scheduled / Ready to Launch",
            classified["scheduled_ready_to_launch"],
            "Tasks scheduled or ready to launch.",
        ),
        (
            "Triage / Ready",
            classified["triage_ready"],
            "Tasks ready for priority review, assignment, scheduling, or clarification.",
        ),
        (
            "Intake",
            classified["intake"],
            "New or captured requests that should not become work until triaged.",
        ),
        (
            "Blocked / Waiting / At Risk",
            classified["blocked_waiting_at_risk"],
            "Tasks with an execution status showing blocked, waiting, at risk, or expedited.",
        ),
        (
            "Date-Visible Work",
            classified["date_visible"],
            "Tasks with Due Date or Release Month. Release Month is a planning bucket, not a hard deadline.",
        ),
        (
            "Backlog / Parking",
            classified["backlog_parking"],
            "P3/P4 work that should not interrupt committed work.",
        ),
        (
            "Asana Hygiene Flags",
            classified["hygiene_flags"],
            "Tasks where section, priority, or execution status may need cleanup.",
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
