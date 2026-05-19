from shared.intelligence.analyze_operational_health import analyze_operational_health
from shared.intelligence.contradictions import detect_p4_in_progress


def field(name, value):
    return {"name": name, "display_value": value}


def task(name, section, fields=None):
    return {
        "gid": name.lower().replace(" ", "-"),
        "name": name,
        "memberships": [{"section": {"name": section}}],
        "custom_fields": fields or [],
    }


def test_detect_p4_in_progress_emits_expected_signal():
    signals = detect_p4_in_progress(
        task(
            "WEB | /dining | Redesign",
            "In Progress",
            [field("Priority", "P4 - Parking")],
        )
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.signal_type == "workflow_contradiction"
    assert signal.severity == "medium"
    assert signal.task_name == "WEB | /dining | Redesign"
    assert signal.message == "P4 task currently in progress."


def test_analyze_operational_health_aggregates_p4_findings_only():
    tasks = [
        task("WEB | P4 work", "In Progress", [field("Priority", "P4 - Parking")]),
        task("WEB | P1 work", "In Progress", [field("Priority", "P1 - Committed")]),
    ]

    findings = analyze_operational_health(tasks)

    assert len(findings) == 1
    assert findings[0].rule_name == "detect_p4_in_progress"


def test_analyze_operational_health_debug_outputs_observable_fields(capsys):
    tasks = [task("WEB | /dining | Redesign", "In Progress", [field("Priority", "P4 - Parking")])]

    analyze_operational_health(tasks, debug=True)
    out = capsys.readouterr().out

    assert "[workflow_contradiction][medium]" in out
    assert "WEB | /dining | Redesign" in out
    assert "P4 task currently in progress." in out
