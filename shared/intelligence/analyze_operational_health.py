from __future__ import annotations

from typing import Any, Dict, List

from shared.intelligence.contradictions import detect_p4_in_progress
from shared.intelligence.models import OperationalSignal


def _debug_finding(signal: OperationalSignal) -> None:
    print(f"[{signal.signal_type}][{signal.severity}]")
    print(signal.task_name)
    print(signal.message)


def analyze_operational_health(
    tasks: List[Dict[str, Any]], *, debug: bool = False
) -> List[OperationalSignal]:
    findings: List[OperationalSignal] = []
    findings.extend(detect_p4_in_progress(tasks, debug=debug))

    if debug:
        for signal in findings:
            _debug_finding(signal)
            print(
                f"[debug][signal] rule={signal.rule_name} type={signal.signal_type} "
                f"severity={signal.severity}"
            )

    return findings
