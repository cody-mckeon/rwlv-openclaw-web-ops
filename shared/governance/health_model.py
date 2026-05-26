from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class GovernanceClassification:
    governance_state: str
    execution_pressure: str
    triggered_rules: List[str]
    reasons: List[str]
    contributing_metrics: Dict[str, int]


def _as_int(metrics: Dict[str, Any], key: str) -> int:
    return int(metrics.get(key, 0) or 0)


def evaluate_governance(metrics: Dict[str, Any]) -> GovernanceClassification:
    blocked_count = _as_int(metrics, "blocked_count")
    in_progress_count = _as_int(metrics, "in_progress_count")
    contradiction_count = _as_int(metrics, "contradiction_count")
    intake_count = _as_int(metrics, "intake_count")
    p0_count = _as_int(metrics, "p0_count")
    qa_count = _as_int(metrics, "qa_count")

    state_rank = {
        "Healthy": 0,
        "Degraded": 1,
        "At Risk": 2,
        "Unstable": 3,
        "Overloaded": 4,
    }

    triggered_rules: List[str] = []
    reasons: List[str] = []
    state = "Healthy"

    def promote(candidate: str, rule: str, reason: str) -> None:
        nonlocal state
        if state_rank[candidate] > state_rank[state]:
            state = candidate
        triggered_rules.append(rule)
        reasons.append(reason)

    if blocked_count > in_progress_count:
        promote(
            "Degraded",
            "blocked_count > in_progress_count",
            "Blocked work exceeds active execution capacity.",
        )

    if contradiction_count > 3:
        promote(
            "At Risk",
            "contradiction_count > 3",
            "Operational contradictions are accumulating above governance tolerance.",
        )

    if contradiction_count > 5:
        promote(
            "Unstable",
            "contradiction_count > 5",
            "High contradiction volume indicates unstable operating conditions.",
        )

    if p0_count >= 3 and in_progress_count <= 2:
        promote(
            "Overloaded",
            "p0_count >= 3 and in_progress_count <= 2",
            "Interrupt load is high while active delivery capacity is constrained.",
        )

    if blocked_count >= max(3, in_progress_count):
        promote(
            "Overloaded",
            "blocked_count >= max(3, in_progress_count)",
            "Dependency pressure and blocked volume indicate an overloaded execution lane.",
        )

    execution_pressure = "Stable"
    if intake_count > in_progress_count * 2:
        execution_pressure = "Increasing"
        triggered_rules.append("intake_count > in_progress_count * 2")
        reasons.append("Intake queue growth materially exceeds current in-progress throughput.")

    if state == "Healthy" and not reasons:
        reasons.append("No governance degradation rule was triggered.")

    contributing_metrics = {
        "blocked_count": blocked_count,
        "in_progress_count": in_progress_count,
        "contradiction_count": contradiction_count,
        "intake_count": intake_count,
        "p0_count": p0_count,
        "qa_count": qa_count,
    }

    return GovernanceClassification(
        governance_state=state,
        execution_pressure=execution_pressure,
        triggered_rules=triggered_rules,
        reasons=reasons,
        contributing_metrics=contributing_metrics,
    )
