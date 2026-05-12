# skills/asana/tests/test_asana_read.py

import os

from skills.asana.actions.read_tasks import summarize_project_tasks


def main() -> None:
    project_gid = os.getenv("ASANA_TEST_PROJECT_GID")

    if not project_gid:
        raise ValueError("Missing ASANA_TEST_PROJECT_GID")

    result = summarize_project_tasks(project_gid)

    print(result["summary"])
    print()

    for task in result["data"]["open_tasks"]:
        assignee = task.get("assignee") or {}
        section_names = [
            membership.get("section", {}).get("name")
            for membership in task.get("memberships", [])
            if membership.get("section")
        ]

        print(
            "-",
            task.get("name"),
            "| due:",
            task.get("due_on") or task.get("due_at"),
            "| assignee:",
            assignee.get("name"),
            "| sections:",
            ", ".join(section_names) if section_names else "None",
        )


if __name__ == "__main__":
    main()
