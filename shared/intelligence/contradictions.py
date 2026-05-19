from __future__ import annotations

from typing import Any, Dict, Iterable, List

from shared.intelligence.models import OperationalSignal
from shared.intelligence.normalization import canonicalize_task


def detect_p4_in_progress(tasks: Iterable[Dict[str, Any]], *, debug: bool = False) -> List[OperationalSignal]:
    """
    Detect active lifecycle + low strategic commitment contradictions.

    Section (lifecycle) and priority (strategic commitment) are distinct dimensions.
    Running P4 work inside In Progress is an operational contradiction worth surfacing.
    """
    findings: List[OperationalSignal] = []

    for task in tasks:
        canonical_task = canonicalize_task(task)
        priority = canonical_task.get("normalized_priority")
        section = canonical_task.get("normalized_section")
        health = canonical_task.get("normalized_health")

        if debug:
            print(
                "[debug][detect_p4_in_progress]",
                f"task={canonical_task.get('name', '<unknown>')}",
                f"raw_priority={canonical_task.get('raw_priority', '')!r}",
                f"raw_section={canonical_task.get('raw_section', '')!r}",
                f"raw_health={canonical_task.get('raw_health', '')!r}",
                f"normalized_priority={priority!r}",
                f"normalized_section={section!r}",
                f"normalized_health={health!r}",
                f"dimensions=(section={section!r},priority={priority!r},health={health!r})",
            )

        if priority == "p4" and section == "in_progress":
            findings.append(
                OperationalSignal(
                    rule_name="detect_p4_in_progress",
                    signal_type="workflow_contradiction",
                    severity="medium",
                    task_name=canonical_task["name"],
                    message="P4 task currently in progress.",
                )
            )

    return findings
