from shared.intelligence.contradictions import detect_p4_in_progress

from typing import Any, Dict, List

from shared.intelligence.contradictions import detect_p4_in_progress
from shared.intelligence.models import OperationalSignal


def _debug_finding(signal: OperationalSignal) -> None:
    print(f"[{signal.signal_type}][{signal.severity}]")
    print(signal.task_name)
    print(signal.message)


def analyze_operational_health(tasks: List[Dict[str, Any]], *, debug: bool = False) -> List[OperationalSignal]:
    """Run small deterministic operational rules and return emitted signals.

    We intentionally keep this tiny and composable so every rule is testable,
    explainable, and easy to observe before adding broader AI reasoning.
    """
    findings: List[OperationalSignal] = []
    for task in tasks:
        findings.extend(detect_p4_in_progress(task))

    if debug:
        for signal in findings:
            _debug_finding(signal)

    return findings
def analyze_operational_health(tasks):
    findings = []

    findings.extend(detect_p4_in_progress(tasks))

    return findings
