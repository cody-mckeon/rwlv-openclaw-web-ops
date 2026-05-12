# skills/asana/actions/generate_current_priorities.py

from __future__ import annotations

import os
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from skills.asana.actions.read_tasks import read_project_tasks


DEFAULT_OUTPUT_PATH = "CURRENT_PRIORITIES.generated.md"


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

    return f"- {name} | Assignee: {assignee} | Due: {due} | Section: {sections}"


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
    Classify Asana tasks into broad priority/context groups.

    This is intentionally conservative.
    It does not invent true business priority from weak data.
    It uses section names and due dates as signals.
    """

    open_tasks = [task for task in tasks if _is_open(task)]

    p0_critical: List[Dict[str, Any]] = []
    p1_active: List[Dict[str, Any]] = []
    p2_scheduled: List[Dict[str, Any]] = []
    p3_backlog: List[Dict[str, Any]] = []
    blocked_or_waiting: List[Dict[str, Any]] = []
    due_dated: List[Dict[str, Any]] = []

    for task in open_tasks:
        section_names = _get_section_names(task)
        task_name = (task.get("name") or "").lower()
        due = _get_due_value(task)

        if due:
            due_dated.append(task)

        # Blocked/waiting signals
        if _section_matches(section_names, ["blocked", "waiting", "on hold"]) or any(
            word in task_name for word in ["blocked", "waiting", "on hold"]
        ):
            blocked_or_waiting.append(task)
            continue

        # P0 signals should stay narrow.
        if any(
            word in task_name
            for word in [
                "urgent",
                "critical",
                "broken",
                "outage",
                "emergency",
                "booking broken",
            ]
        ) or _section_matches(section_names, ["p0", "critical", "urgent"]):
            p0_critical.append(task)
            continue

        # Active work signals.
        if _section_matches(
            section_names,
            ["in progress", "active", "doing", "current", "launch", "scheduled"],
        ):
            p1_active.append(task)
            continue

        # Scheduled/planned work.
        if due or _section_matches(
            section_names,
            ["scheduled", "next up", "ready", "approved", "planned"],
        ):
            p2_scheduled.append(task)
            continue

        # Intake/backlog style work.
        if _section_matches(section_names, ["intake", "backlog", "ideas", "triage"]):
            p3_backlog.append(task)
            continue

        # Default to P2 instead of pretending everything is urgent.
        p2_scheduled.append(task)

    return {
        "p0_critical": _sort_tasks(p0_critical),
        "p1_active": _sort_tasks(p1_active),
        "p2_scheduled": _sort_tasks(p2_scheduled),
        "p3_backlog": _sort_tasks(p3_backlog),
        "blocked_or_waiting": _sort_tasks(blocked_or_waiting),
        "due_dated": _sort_tasks(due_dated),
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
    lines.append("")

    sections = [
        (
            "P0 / Critical",
            classified["p0_critical"],
            "Tasks that appear urgent, critical, broken, or production-impacting.",
        ),
        (
            "P1 / Active Launches and Committed Work",
            classified["p1_active"],
            "Tasks that appear active, in progress, launch-related, or currently scheduled.",
        ),
        (
            "P2 / Scheduled or Important Work",
            classified["p2_scheduled"],
            "Tasks that appear planned, due-dated, approved, or important but not clearly critical.",
        ),
        (
            "P3 / Intake or Backlog",
            classified["p3_backlog"],
            "Tasks that appear to be intake, backlog, triage, or lower-urgency work.",
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
