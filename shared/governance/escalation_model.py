from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class EscalationClassification:
    escalation_state: str
    dependency_escalation: bool
    operational_instability: bool
    triggered_rules: List[str]
    reasons: List[str]
    persistence_indicators: Dict[str, int]
    contributing_metrics: Dict[str, int]
    intervention_semantics: List[str]


def _as_int(metrics: Dict[str, Any], key: str) -> int:
    return int(metrics.get(key, 0) or 0)


def _trailing_count(history: List[Dict[str, Any]], predicate) -> int:
    count = 0
    for item in reversed(history):
        if predicate(item):
            count += 1
            continue
        break
    return count


def _trailing_strict_increase_count(history: List[Dict[str, Any]], key: str) -> int:
    values = [_as_int(item, key) for item in history]
    if len(values) < 2:
        return 0

    count = 1
    for idx in range(len(values) - 1, 0, -1):
        if values[idx] > values[idx - 1]:
            count += 1
            continue
        break
    return count


def evaluate_escalation(history: List[Dict[str, Any]]) -> EscalationClassification:
    if not history:
        return EscalationClassification(
            escalation_state="Normal",
            dependency_escalation=False,
            operational_instability=False,
            triggered_rules=[],
            reasons=["No telemetry history available; escalation defaults to Normal."],
            persistence_indicators={
                "overloaded_consecutive": 0,
                "blocked_increase_consecutive": 0,
                "p0_active_consecutive": 0,
            },
            contributing_metrics={},
            intervention_semantics=["Continue standard operational governance monitoring cadence."],
        )

    current = history[-1]
    overloaded_consecutive = _trailing_count(
        history,
        lambda entry: str(entry.get("governance_state", "")) == "Overloaded",
    )
    blocked_increase_consecutive = _trailing_strict_increase_count(history, "blocked_count")
    p0_active_consecutive = _trailing_count(history, lambda entry: _as_int(entry, "p0_count") > 0)

    dependency_escalation = blocked_increase_consecutive >= 5
    operational_instability = p0_active_consecutive >= 3

    state_rank = {"Normal": 0, "Elevated": 1, "Escalated": 2, "Critical": 3}
    escalation_state = "Normal"
    triggered_rules: List[str] = []
    reasons: List[str] = []
    intervention_semantics: List[str] = []

    def promote(candidate: str, rule: str, reason: str, intervention: str) -> None:
        nonlocal escalation_state
        if state_rank[candidate] > state_rank[escalation_state]:
            escalation_state = candidate
        triggered_rules.append(rule)
        reasons.append(reason)
        intervention_semantics.append(intervention)

    if overloaded_consecutive >= 3:
        promote(
            "Elevated",
            "governance_state == 'Overloaded' for 3+ consecutive snapshots",
            f"Overloaded governance state persisted across {overloaded_consecutive} consecutive snapshots.",
            "Initiate leadership visibility review for sustained overload and rebalance active execution commitments.",
        )

    if dependency_escalation:
        promote(
            "Escalated",
            "blocked_count strictly increased for 5+ consecutive snapshots",
            f"Blocked work has increased across {blocked_increase_consecutive} consecutive snapshots, indicating persistent dependency pressure.",
            "Trigger dependency intervention semantics: prioritize blocker resolution sequencing and cross-team dependency clearing.",
        )

    if operational_instability:
        promote(
            "Critical",
            "p0_count > 0 for 3+ consecutive snapshots",
            f"P0 interrupts remained active for {p0_active_consecutive} consecutive snapshots, indicating sustained operational instability.",
            "Activate critical operational intervention semantics: stabilize interrupt handling before accepting additional execution load.",
        )

    if not reasons:
        reasons.append("No persistence-based escalation rule was triggered.")
        intervention_semantics.append("Maintain deterministic monitoring; no escalation intervention is currently required.")

    return EscalationClassification(
        escalation_state=escalation_state,
        dependency_escalation=dependency_escalation,
        operational_instability=operational_instability,
        triggered_rules=triggered_rules,
        reasons=reasons,
        persistence_indicators={
            "overloaded_consecutive": overloaded_consecutive,
            "blocked_increase_consecutive": blocked_increase_consecutive,
            "p0_active_consecutive": p0_active_consecutive,
        },
        contributing_metrics={
            "blocked_count": _as_int(current, "blocked_count"),
            "in_progress_count": _as_int(current, "in_progress_count"),
            "contradiction_count": _as_int(current, "contradiction_count"),
            "intake_count": _as_int(current, "intake_count"),
            "p0_count": _as_int(current, "p0_count"),
            "qa_count": _as_int(current, "qa_count"),
        },
        intervention_semantics=intervention_semantics,
    )
