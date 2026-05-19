from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List

from shared.intelligence.contradictions import (
    classify_operational_task,
    detect_workflow_contradictions,
)
from shared.intelligence.models import OperationalSignal

LOGGER = logging.getLogger(__name__)


def format_operational_signal(signal: OperationalSignal) -> str:
    """Return a compact, structured human-readable signal block."""
    return "\n".join(
        [
            f"[{signal.signal_type}][{signal.severity}]",
            signal.task_name,
            signal.message,
        ]
    )


def log_operational_signal(
    signal: OperationalSignal,
    logger: logging.Logger | None = None,
) -> None:
    """Log a finding with stable fields for later dashboard or grep-based review."""
    logger = logger or LOGGER
    logger.info(
        "%s",
        format_operational_signal(signal),
        extra={
            "signal_type": signal.signal_type,
            "severity": signal.severity,
            "task_name": signal.task_name,
            "signal_message": signal.message,
            "rule_name": signal.rule_name,
            "normalized_section": signal.normalized_section,
            "normalized_priority": signal.normalized_priority,
            "classifications": signal.classifications,
        },
    )


def operational_diagnostics(
    tasks: Iterable[Dict[str, Any]],
    signals: Iterable[OperationalSignal],
) -> List[Dict[str, Any]]:
    """Expose deterministic facts used to validate false positives/negatives."""
    signals_by_gid: Dict[str | None, List[OperationalSignal]] = {}
    for signal in signals:
        signals_by_gid.setdefault(signal.task_gid, []).append(signal)

    diagnostics: List[Dict[str, Any]] = []
    for task in tasks:
        facts = classify_operational_task(task)
        triggered = signals_by_gid.get(facts["task_gid"], [])
        diagnostics.append(
            {
                "task_name": facts["task_name"],
                "task_gid": facts["task_gid"],
                "normalized_section": facts["normalized_section"],
                "normalized_priority": facts["normalized_priority"],
                "normalized_health": facts["normalized_health"],
                "classifications": list(facts["classifications"]),
                "rules_triggered": [signal.rule_name for signal in triggered],
            }
        )

    return diagnostics


def log_operational_diagnostics(
    diagnostics: Iterable[Dict[str, Any]],
    logger: logging.Logger | None = None,
) -> None:
    logger = logger or LOGGER
    for diagnostic in diagnostics:
        logger.info(
            "operational_diagnostic task=%r section=%s priority=%s health=%s classifications=%s rules_triggered=%s",
            diagnostic["task_name"],
            diagnostic["normalized_section"],
            diagnostic["normalized_priority"],
            diagnostic["normalized_health"],
            diagnostic["classifications"],
            diagnostic["rules_triggered"],
        )


def analyze_operational_health(
    tasks: List[Dict[str, Any]],
    *,
    debug: bool = False,
) -> Dict[str, Any]:
    """Run deterministic operational checks against task dictionaries."""
    signals = detect_workflow_contradictions(tasks)
    diagnostics = operational_diagnostics(tasks, signals)

    if debug:
        log_operational_diagnostics(diagnostics)
        for signal in signals:
            log_operational_signal(signal)

    return {
        "signals": signals,
        "diagnostics": diagnostics,
    }


def analyze_asana_project(
    project_gid: str,
    *,
    limit: int = 100,
    debug: bool = False,
) -> Dict[str, Any]:
    """Pull real Asana data, then run the same deterministic local checks."""
    from skills.asana.actions.read_tasks import read_project_tasks

    result = read_project_tasks(project_gid=project_gid, limit=limit)
    tasks = result.get("data", [])
    analysis = analyze_operational_health(tasks, debug=debug)
    analysis["project_gid"] = project_gid
    analysis["task_count"] = len(tasks)
    return analysis


def configure_debug_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze RWLV operational health from a JSON task export."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--task-json", type=Path, help="Path to JSON list of Asana task objects")
    source.add_argument("--project-gid", help="Asana project GID to inspect with live RWLV data")
    parser.add_argument("--limit", type=int, default=100, help="Maximum Asana tasks to pull")
    parser.add_argument("--debug", action="store_true", help="Print diagnostics and findings")
    args = parser.parse_args()

    configure_debug_logging()

    if args.project_gid:
        result = analyze_asana_project(args.project_gid, limit=args.limit, debug=args.debug)
    else:
        tasks = json.loads(args.task_json.read_text(encoding="utf-8"))
        result = analyze_operational_health(tasks, debug=args.debug)

    if not args.debug:
        for signal in result["signals"]:
            print(format_operational_signal(signal))


if __name__ == "__main__":
    main()
