from shared.intelligence.analyze_operational_health import analyze_operational_health
from shared.intelligence.contradictions import detect_p4_in_progress
from shared.intelligence.normalization import (
    normalize_health_value,
    normalize_priority_value,
    normalize_section_value,
)


def field(name, value):
    return {"name": name, "display_value": value}


def task(name, section, fields=None):
    return {
        "gid": name.lower().replace(" ", "-"),
        "name": name,
        "memberships": [{"section": {"name": section}}],
        "custom_fields": fields or [],
    }


def test_priority_labels_normalize_to_canonical_operational_values():
    assert normalize_priority_value("P0 - Critical / Interrupt") == "p0"
    assert normalize_priority_value("P1 - Active / Committed") == "p1"
    assert normalize_priority_value("P2 - Important / Scheduled") == "p2"
    assert normalize_priority_value("P3 - Backlog / Nice-to-have") == "p3"
    assert normalize_priority_value("P4 - Someday / Parking Lot") == "p4"


def test_section_labels_normalize_to_canonical_operational_values():
    assert normalize_section_value("Ideas / Parking Lot") == "ideas_parking_lot"
    assert normalize_section_value("Triage / Ready") == "triage_ready"
    assert normalize_section_value("In Progress") == "in_progress"


def test_health_labels_normalize_to_canonical_operational_values():
    assert normalize_health_value("On Track") == "on_track"
    assert normalize_health_value("Waiting on Vendor") == "waiting_on_vendor"
    assert normalize_health_value("Blocked") == "blocked"


def test_detect_p4_in_progress_emits_expected_signal_for_rwlv_label():
    signals = detect_p4_in_progress(
        [
            task(
                "WEB | /dining | Redesign",
                "In Progress",
                [field("Priority", "P4 - Someday / Parking Lot")],
            )
        ]
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.rule_name == "detect_p4_in_progress"
    assert signal.signal_type == "workflow_contradiction"
    assert signal.severity == "medium"
    assert signal.task_name == "WEB | /dining | Redesign"
    assert signal.message == "P4 task currently in progress."


def test_analyze_operational_health_detects_rwlv_contradiction_case():
    tasks = [
        task(
            "RWLV | Contradiction",
            "In Progress",
            [field("Priority", "P4 - Someday / Parking Lot")],
        ),
        task(
            "RWLV | Legit Active",
            "In Progress",
            [field("Priority", "P1 - Active / Committed")],
        ),
    ]

    findings = analyze_operational_health(tasks)

    assert len(findings) == 1
    assert findings[0].rule_name == "detect_p4_in_progress"
    assert findings[0].task_name == "RWLV | Contradiction"


def test_analyze_operational_health_debug_outputs_observable_fields(capsys):
    tasks = [
        task(
            "WEB | /dining | Redesign",
            "In Progress",
            [field("Priority", "P4 - Someday / Parking Lot")],
        )
    ]

    analyze_operational_health(tasks, debug=True)
    out = capsys.readouterr().out

    assert "raw_priority='P4 - Someday / Parking Lot'" in out
    assert "normalized_priority='p4'" in out
    assert "normalized_section='in_progress'" in out
    assert "normalized_health='unknown'" in out
    assert "dimensions=(section='in_progress',priority='p4',health='unknown')" in out
    assert "[debug][signal] rule=detect_p4_in_progress" in out
