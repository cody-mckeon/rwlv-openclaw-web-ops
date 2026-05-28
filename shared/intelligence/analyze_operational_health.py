from __future__ import annotations

from shared.intelligence.contradictions import classify_operational_task, detect_p4_in_progress
from shared.intelligence.models import OperationalSignal


def _debug_finding(signal: OperationalSignal) -> None:
    print(f"[{signal.signal_type}][{signal.severity}]")
    print(signal.task_name)
    print(signal.message)


def analyze_operational_health(tasks, debug=False):
    task_list = list(tasks)
    findings = detect_p4_in_progress(task_list)

    if debug:
        for task in task_list:
            facts = classify_operational_task(task)
            print(
                f"[debug][task] raw_priority='{facts['raw_priority']}' "
                f"normalized_priority='{facts['normalized_priority']}' "
                f"normalized_section='{facts['normalized_section']}' "
                f"normalized_health='{facts['normalized_health']}' "
                f"dimensions=(section='{facts['normalized_section']}',priority='{facts['normalized_priority']}',health='{facts['normalized_health']}')"
            )
        for signal in findings:
            print(
                f"[debug][signal] rule={signal.rule_name} "
                f"type={signal.signal_type} "
                f"severity={signal.severity}"
            )

    return findings
