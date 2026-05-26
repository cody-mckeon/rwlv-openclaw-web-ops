from shared.governance import evaluate_governance


def test_governance_degraded_when_blocked_exceeds_in_progress() -> None:
    result = evaluate_governance(
        {
            "blocked_count": 4,
            "in_progress_count": 2,
            "contradiction_count": 0,
            "intake_count": 1,
            "p0_count": 0,
            "qa_count": 0,
        }
    )

    assert result.governance_state == "Overloaded"
    assert "blocked_count > in_progress_count" in result.triggered_rules


def test_governance_unstable_when_contradictions_are_high() -> None:
    result = evaluate_governance(
        {
            "blocked_count": 0,
            "in_progress_count": 3,
            "contradiction_count": 6,
            "intake_count": 1,
            "p0_count": 0,
            "qa_count": 0,
        }
    )

    assert result.governance_state == "Unstable"
    assert "contradiction_count > 5" in result.triggered_rules


def test_execution_pressure_increasing_when_intake_outpaces_in_progress() -> None:
    result = evaluate_governance(
        {
            "blocked_count": 0,
            "in_progress_count": 2,
            "contradiction_count": 0,
            "intake_count": 5,
            "p0_count": 0,
            "qa_count": 0,
        }
    )

    assert result.execution_pressure == "Increasing"
    assert "intake_count > in_progress_count * 2" in result.triggered_rules
