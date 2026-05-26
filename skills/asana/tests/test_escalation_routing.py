from shared.governance import derive_escalation_routing, evaluate_escalation


def test_routing_team_awareness_for_elevated_state() -> None:
    history = [
        {"governance_state": "Healthy", "blocked_count": 1, "p0_count": 0},
        {"governance_state": "Overloaded", "blocked_count": 2, "p0_count": 0},
        {"governance_state": "Overloaded", "blocked_count": 2, "p0_count": 0},
        {"governance_state": "Overloaded", "blocked_count": 3, "p0_count": 0},
    ]

    escalation = evaluate_escalation(history)
    routing = derive_escalation_routing(escalation)

    assert escalation.escalation_state == "Elevated"
    assert routing.visibility_level == "Team Awareness"
    assert routing.operational_attention is False
    assert "Operational Pressure Digest" in routing.notification_semantics


def test_routing_leadership_visibility_for_escalated_state() -> None:
    history = [
        {"governance_state": "Degraded", "blocked_count": 1, "p0_count": 0},
        {"governance_state": "At Risk", "blocked_count": 2, "p0_count": 0},
        {"governance_state": "At Risk", "blocked_count": 3, "p0_count": 0},
        {"governance_state": "Overloaded", "blocked_count": 4, "p0_count": 0},
        {"governance_state": "Overloaded", "blocked_count": 5, "p0_count": 0},
    ]

    escalation = evaluate_escalation(history)
    routing = derive_escalation_routing(escalation)

    assert escalation.escalation_state == "Escalated"
    assert routing.visibility_level == "Leadership Visibility Recommended"
    assert routing.operational_attention is True
    assert "Vendor Dependency Escalation" in routing.notification_semantics


def test_routing_critical_attention_for_operational_instability() -> None:
    history = [
        {"governance_state": "At Risk", "blocked_count": 1, "p0_count": 1},
        {"governance_state": "At Risk", "blocked_count": 2, "p0_count": 1},
        {"governance_state": "Overloaded", "blocked_count": 2, "p0_count": 2},
    ]

    escalation = evaluate_escalation(history)
    routing = derive_escalation_routing(escalation)

    assert escalation.operational_instability is True
    assert routing.visibility_level == "Critical Operational Attention"
    assert routing.operational_attention is True
    assert "Launch Governance Alert" in routing.notification_semantics
    assert "Persistent Overload Warning" in routing.notification_semantics
