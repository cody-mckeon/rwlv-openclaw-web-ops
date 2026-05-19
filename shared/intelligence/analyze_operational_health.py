from __future__ import annotations

from typing import Any, Dict, List

from shared.intelligence.contradictions import detect_p4_in_progress
from shared.intelligence.models import OperationalSignal


def _debug_finding(signal: OperationalSignal) -> None:
    print(f"[{signal.signal_type}][{signal.severity}]")
    print(signal.task_name)
    print(signal.message)


<<<<<<< HEAD
def analyze_operational_health(
    tasks: List[Dict[str, Any]], *, debug: bool = False
) -> List[OperationalSignal]:
    """
    Run deterministic multidimensional operational rules.

    Normalization happens before rule evaluation so rules reason on canonical
    (section, priority, health) dimensions instead of raw UI labels.
    """
    findings: List[OperationalSignal] = []
    findings.extend(detect_p4_in_progress(tasks, debug=debug))
=======
def analyze_operational_health(tasks, debug=False):
    findings = []

    findings.extend(detect_p4_in_progress(tasks))
>>>>>>> 247b2ef (Validate operational intelligence signal pipeline)

    if debug:
        for signal in findings:
            print(
                f"[debug][signal] rule={signal.rule_name} "
                f"type={signal.signal_type} "
                f"severity={signal.severity}"
            )

    return findings
