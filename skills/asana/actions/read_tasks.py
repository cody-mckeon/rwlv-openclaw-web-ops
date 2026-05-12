# skills/asana/actions/read_tasks.py

from typing import Any, Dict, List, Optional

from skills.asana.tools.asana_client import AsanaClient


def read_project_tasks(project_gid: str, limit: int = 50) -> Dict[str, Any]:
    """
    Read tasks from a specific Asana project.

    This action is read-only.
    """

    client = AsanaClient()

    params = {
        "limit": limit,
        "opt_fields": (
            "gid,"
            "name,"
            "completed,"
            "assignee.name,"
            "due_on,"
            "due_at,"
            "memberships.section.name,"
            "custom_fields.name,"
            "custom_fields.display_value"
        ),
    }

    result = client.get(f"/projects/{project_gid}/tasks", params=params)
    tasks: List[Dict[str, Any]] = result.get("data", [])

    return {
        "ok": True,
        "action": "asana.read_project_tasks",
        "summary": f"Found {len(tasks)} tasks.",
        "project_gid": project_gid,
        "data": tasks,
        "errors": [],
    }


def summarize_project_tasks(project_gid: str, limit: int = 50) -> Dict[str, Any]:
    """
    Read and lightly summarize tasks for priority review.
    """

    result = read_project_tasks(project_gid=project_gid, limit=limit)
    tasks = result.get("data", [])

    open_tasks = [task for task in tasks if not task.get("completed")]
    completed_tasks = [task for task in tasks if task.get("completed")]

    due_tasks = [
        task for task in open_tasks if task.get("due_on") or task.get("due_at")
    ]

    return {
        "ok": True,
        "action": "asana.summarize_project_tasks",
        "summary": (
            f"Found {len(tasks)} total tasks, "
            f"{len(open_tasks)} open, "
            f"{len(completed_tasks)} completed, "
            f"{len(due_tasks)} with due dates."
        ),
        "project_gid": project_gid,
        "counts": {
            "total": len(tasks),
            "open": len(open_tasks),
            "completed": len(completed_tasks),
            "with_due_dates": len(due_tasks),
        },
        "data": {
            "open_tasks": open_tasks,
            "due_tasks": due_tasks,
        },
        "errors": [],
    }
