# skills/asana/actions/read_subtasks.py

from __future__ import annotations

from typing import Any, Dict, List

from skills.asana.tools.asana_client import AsanaClient


def read_task_subtasks(task_gid: str, limit: int = 50) -> Dict[str, Any]:
    """
    Read subtasks for a specific Asana task.

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
            "custom_fields.name,"
            "custom_fields.display_value"
        ),
    }

    result = client.get(f"/tasks/{task_gid}/subtasks", params=params)
    subtasks: List[Dict[str, Any]] = result.get("data", [])

    return {
        "ok": True,
        "action": "asana.read_task_subtasks",
        "summary": f"Found {len(subtasks)} subtasks.",
        "task_gid": task_gid,
        "data": subtasks,
        "errors": [],
    }