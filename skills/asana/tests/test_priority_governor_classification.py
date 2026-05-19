import unittest

from skills.asana.actions.generate_current_priorities import (
    classify_tasks,
    render_current_priorities_markdown,
)
from scripts.send_priority_digest import build_digest


def field(name, value):
    return {"name": name, "display_value": value}


def task(name, section, fields=None, due_on=None, completed=False):
    return {
        "gid": name.lower().replace(" ", "-"),
        "name": name,
        "completed": completed,
        "assignee": {"name": "Cody McKeon"},
        "due_on": due_on,
        "memberships": [{"section": {"name": section}}],
        "custom_fields": fields or [],
    }


class PriorityGovernorClassificationTests(unittest.TestCase):
    def test_in_progress_section_is_active_even_when_health_is_waiting(self):
        tasks = [
            task(
                "WEB | 4th of July | Landing Page",
                "In Progress",
                [
                    field("Health / Execution", "Waiting on vendor"),
                    field("Priority", "P0 - Critical"),
                    field("Work Type", "New Build"),
                    field("Release Month", "May 2026"),
                ],
                due_on="2026-05-19",
            )
        ]

        classified = classify_tasks(tasks)

        self.assertEqual(classified["p0_interrupt"], tasks)
        self.assertEqual(classified["blocked_waiting_at_risk"], tasks)
        self.assertEqual(classified["date_visible"], tasks)

    def test_triage_ready_is_treated_as_triage_not_unknown(self):
        tasks = [
            task(
                "WEB | Resorts World Live | Bottom Section",
                "Triage / Ready",
                [
                    field("Health / Execution", "Waiting on details"),
                    field("Priority", "P3 - Backlog"),
                    field("Work Type", "Optimization"),
                ],
            )
        ]

        classified = classify_tasks(tasks)

        self.assertEqual(classified["triage_ready"], tasks)

    def test_markdown_and_digest_include_active_in_progress_tasks(self):
        tasks = [
            task(
                "WEB | Tag Audit and Consent Remediation",
                "In Progress",
                [
                    field("Health / Execution", "Waiting on confirmation"),
                    field("Priority", "P0 - Critical"),
                    field("Work Type", "Compliance"),
                ],
            )
        ]

        markdown = render_current_priorities_markdown("project-1", tasks)
        digest = build_digest(markdown)

        self.assertIn("WEB | Tag Audit and Consent Remediation", markdown)
        self.assertIn("1. P0 Interrupt work", digest)
        self.assertIn("WEB | Tag Audit and Consent Remediation", digest)
        self.assertNotIn("1. P0 Interrupt work\n- None found.", digest)


if __name__ == "__main__":
    unittest.main()
