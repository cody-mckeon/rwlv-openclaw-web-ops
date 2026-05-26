from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .escalation_model import EscalationClassification


@dataclass(frozen=True)
class EscalationRoutingDecision:
    visibility_level: str
    routing_reason: str
    operational_attention: bool
    notification_semantics: List[str]


def derive_escalation_routing(escalation: EscalationClassification) -> EscalationRoutingDecision:
    """Derive deterministic operational visibility routing from escalation semantics."""

    if escalation.operational_instability:
        visibility_level = "Critical Operational Attention"
        routing_reason = "Operational instability is true because sustained P0 activity crossed deterministic thresholds."
    elif escalation.escalation_state == "Escalated":
        visibility_level = "Leadership Visibility Recommended"
        routing_reason = "Escalation state is Escalated due to persistent dependency pressure signals."
    elif escalation.escalation_state == "Elevated":
        visibility_level = "Team Awareness"
        routing_reason = "Escalation state is Elevated due to sustained overload persistence."
    else:
        visibility_level = "Normal Visibility"
        routing_reason = "No elevated deterministic escalation condition currently requires expanded visibility."

    notification_semantics: List[str] = []
    if escalation.persistence_indicators.get("overloaded_consecutive", 0) >= 3:
        notification_semantics.append("Operational Pressure Digest")
    if escalation.dependency_escalation:
        notification_semantics.append("Vendor Dependency Escalation")
    if escalation.persistence_indicators.get("p0_active_consecutive", 0) > 0:
        notification_semantics.append("Launch Governance Alert")
    if escalation.operational_instability:
        notification_semantics.append("Persistent Overload Warning")

    if not notification_semantics:
        notification_semantics.append("Operational Pressure Digest")

    operational_attention = visibility_level in {
        "Leadership Visibility Recommended",
        "Critical Operational Attention",
    }

    return EscalationRoutingDecision(
        visibility_level=visibility_level,
        routing_reason=routing_reason,
        operational_attention=operational_attention,
        notification_semantics=notification_semantics,
    )
