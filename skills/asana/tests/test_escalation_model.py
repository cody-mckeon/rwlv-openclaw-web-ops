from shared.governance import evaluate_escalation


def test_escalation_elevated_when_overloaded_persists() -> None:
    history = [
        {"governance_state": "Healthy", "blocked_count": 1, "p0_count": 0},
        {"governance_state": "Overloaded", "blocked_count": 2, "p0_count": 0},
        {"governance_state": "Overloaded", "blocked_count": 2, "p0_count": 0},
        {"governance_state": "Overloaded", "blocked_count": 3, "p0_count": 0},
    ]

    result = evaluate_escalation(history)

    assert result.escalation_state == "Elevated"
    assert result.persistence_indicators["overloaded_consecutive"] == 3
    assert "governance_state == 'Overloaded' for 3+ consecutive snapshots" in result.triggered_rules


def test_escalation_escalated_when_blocked_increases_persistently() -> None:
    history = [
        {"governance_state": "Degraded", "blocked_count": 1, "p0_count": 0},
        {"governance_state": "Degraded", "blocked_count": 2, "p0_count": 0},
        {"governance_state": "At Risk", "blocked_count": 3, "p0_count": 0},
        {"governance_state": "At Risk", "blocked_count": 4, "p0_count": 0},
        {"governance_state": "Overloaded", "blocked_count": 5, "p0_count": 0},
    ]

    result = evaluate_escalation(history)

    assert result.escalation_state == "Escalated"
    assert result.dependency_escalation is True
    assert result.persistence_indicators["blocked_increase_consecutive"] == 5


def test_escalation_critical_when_p0_persists() -> None:
    history = [
        {"governance_state": "At Risk", "blocked_count": 1, "p0_count": 1},
        {"governance_state": "At Risk", "blocked_count": 2, "p0_count": 1},
        {"governance_state": "Overloaded", "blocked_count": 2, "p0_count": 2},
    ]

    result = evaluate_escalation(history)

    assert result.escalation_state == "Critical"
    assert result.operational_instability is True
    assert result.persistence_indicators["p0_active_consecutive"] == 3
