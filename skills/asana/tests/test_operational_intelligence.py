import logging

from shared.intelligence.analyze_operational_health import analyze_operational_health
from shared.intelligence.contradictions import (
    classify_operational_task,
    detect_p0_without_due_date,
    detect_p4_in_progress,
    detect_scheduled_but_blocked,
    detect_workflow_contradictions,
)


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


def test_p4_in_progress_returns_medium_workflow_contradiction():
    signals = detect_p4_in_progress(
        task(
            "WEB | /dining | Redesign",
            "In Progress",
            [field("Priority", "P4 - Parking")],
        )
    )

    assert len(signals) == 1
    assert signals[0].signal_type == "workflow_contradiction"
    assert signals[0].severity == "medium"
    assert signals[0].task_name == "WEB | /dining | Redesign"
    assert signals[0].message == "P4 task currently in progress."
    assert signals[0].rule_name == "detect_p4_in_progress"


def test_p0_without_due_date_returns_high_workflow_contradiction():
    signals = detect_p0_without_due_date(
        task(
            "WEB | Booking Recovery",
            "In Progress",
            [field("Priority", "P0 - Interrupt")],
        )
    )

    assert len(signals) == 1
    assert signals[0].severity == "high"
    assert signals[0].message == "P0 task is missing a due date."
    assert signals[0].rule_name == "detect_p0_without_due_date"


def test_p0_with_due_date_does_not_trigger_missing_due_date():
    signals = detect_p0_without_due_date(
        task(
            "WEB | Booking Recovery",
            "In Progress",
            [field("Priority", "P0 - Interrupt")],
            due_on="2026-05-20",
        )
    )

    assert signals == []


def test_scheduled_but_blocked_detects_waiting_health():
    signals = detect_scheduled_but_blocked(
        task(
            "WEB | Offer Launch",
            "Scheduled / Ready to Launch",
            [
                field("Priority", "P2 - Scheduled"),
                field("Health / Execution", "Waiting on stakeholder"),
            ],
            due_on="2026-05-22",
        )
    )

    assert len(signals) == 1
    assert signals[0].severity == "medium"
    assert signals[0].message == "Scheduled task has blocked, waiting, or at-risk health."
    assert signals[0].rule_name == "detect_scheduled_but_blocked"


def test_aggregator_runs_all_tiny_rules():
    tasks = [
        task("WEB | Parking Work", "In Progress", [field("Priority", "P4 - Parking")]),
        task("WEB | P0 Missing Date", "Intake", [field("Priority", "Critical")]),
        task(
            "WEB | Blocked Launch",
            "Scheduled / Ready to Launch",
            [field("Priority", "P2 - Scheduled"), field("Health", "At Risk")],
        ),
    ]

    signals = detect_workflow_contradictions(tasks)

    assert [signal.rule_name for signal in signals] == [
        "detect_p4_in_progress",
        "detect_p0_without_due_date",
        "detect_scheduled_but_blocked",
    ]


def test_diagnostics_expose_normalized_facts_and_triggered_rules():
    tasks = [
        task(
            "WEB | Blocked Launch",
            "Scheduled / Ready to Launch",
            [field("Priority", "P2 - Scheduled"), field("Health", "Blocked")],
        )
    ]

    result = analyze_operational_health(tasks)

    assert result["diagnostics"] == [
        {
            "task_name": "WEB | Blocked Launch",
            "task_gid": "web-|-blocked-launch",
            "normalized_section": "scheduled",
            "normalized_priority": "p2",
            "normalized_health": "blocked",
            "classifications": [
                "section:scheduled",
                "priority:p2",
                "missing_due_date",
                "health:blocked_like",
            ],
            "rules_triggered": ["detect_scheduled_but_blocked"],
        }
    ]


def test_debug_logging_includes_clear_signal_fields(caplog):
    tasks = [
        task("WEB | /dining | Redesign", "In Progress", [field("Priority", "P4 - Parking")])
    ]

    with caplog.at_level(logging.INFO, logger="shared.intelligence.analyze_operational_health"):
        analyze_operational_health(tasks, debug=True)

    text = caplog.text
    assert "[workflow_contradiction][medium]" in text
    assert "WEB | /dining | Redesign" in text
    assert "P4 task currently in progress." in text
    assert "operational_diagnostic" in text
    assert "section=in_progress" in text
    assert "priority=p4" in text
    assert "rules_triggered=['detect_p4_in_progress']" in text


def test_classification_documents_real_rwlw_snapshot_assumptions():
    facts = classify_operational_task(
        task(
            "Dining page link updates",
            "In Progress",
            [field("Priority", "P1 - Committed"), field("Health / Execution", "On Track")],
            due_on="2026-05-19",
        )
    )

    assert facts["normalized_section"] == "in_progress"
    assert facts["normalized_priority"] == "p1"
    assert facts["classifications"] == ("section:in_progress", "priority:p1", "has_due_date")
