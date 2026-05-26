from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from shared.config.runtime import load_dotenv, load_runtime_config
from shared.runtime_logging import log_event


METRIC_ORDER = [
    ("blocked_count", "Blocked Work"),
    ("p0_count", "P0 Interrupts"),
    ("contradiction_count", "Contradictions"),
    ("qa_count", "QA Queue"),
    ("intake_count", "Intake Queue"),
    ("in_progress_count", "In Progress"),
    ("scheduled_launch_count", "Scheduled Launch"),
    ("open_task_count", "Open Tasks"),
]


@dataclass(frozen=True)
class TrendLine:
    label: str
    metric_key: str
    previous_value: int
    current_value: int

    @property
    def delta(self) -> int:
        return self.current_value - self.previous_value

    def render(self) -> str:
        if self.delta > 0:
            return f"* {self.label}: Increased from {self.previous_value} → {self.current_value} (+{self.delta})"
        if self.delta < 0:
            return f"* {self.label}: Reduced from {self.previous_value} → {self.current_value} ({self.delta})"
        return f"* {self.label}: Stable at {self.current_value}"


def _read_metrics_history(telemetry_file: Path) -> List[Dict[str, Any]]:
    if not telemetry_file.exists():
        return []

    entries: List[Dict[str, Any]] = []
    for line in telemetry_file.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        payload = json.loads(raw)
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def _trend_lines(previous: Dict[str, Any], current: Dict[str, Any]) -> List[TrendLine]:
    lines: List[TrendLine] = []
    for metric_key, label in METRIC_ORDER:
        lines.append(
            TrendLine(
                label=label,
                metric_key=metric_key,
                previous_value=int(previous.get(metric_key, 0)),
                current_value=int(current.get(metric_key, 0)),
            )
        )
    return lines


def _history_change_text(entries: Iterable[Dict[str, Any]], metric_key: str, label: str) -> str:
    values = [int(item.get(metric_key, 0)) for item in entries]
    if len(values) < 3:
        return f"* {label}: Insufficient history for multi-day change context"

    oldest = values[0]
    latest = values[-1]
    delta = latest - oldest
    if delta > 0:
        state = f"increased by +{delta} over {len(values)} samples"
    elif delta < 0:
        state = f"reduced by {delta} over {len(values)} samples"
    else:
        state = f"stable over {len(values)} samples"

    return f"* {label}: {oldest} → {latest} ({state})"


def _deterministic_observations(current: Dict[str, Any], previous: Dict[str, Any]) -> List[str]:
    observations: List[str] = []

    blocked_delta = int(current.get("blocked_count", 0)) - int(previous.get("blocked_count", 0))
    if blocked_delta > 0:
        observations.append("* Vendor/content dependency load is increasing.")

    scheduled_delta = int(current.get("scheduled_launch_count", 0)) - int(previous.get("scheduled_launch_count", 0))
    qa_delta = int(current.get("qa_count", 0)) - int(previous.get("qa_count", 0))
    if scheduled_delta >= 0 and qa_delta == 0:
        observations.append("* Launch readiness workload is stabilizing.")

    intake_delta = int(current.get("intake_count", 0)) - int(previous.get("intake_count", 0))
    in_progress_delta = int(current.get("in_progress_count", 0)) - int(previous.get("in_progress_count", 0))
    if intake_delta > in_progress_delta:
        observations.append("* Intake queue growth exceeds in-progress execution.")

    contradiction_delta = int(current.get("contradiction_count", 0)) - int(previous.get("contradiction_count", 0))
    if contradiction_delta < 0 and int(current.get("contradiction_count", 0)) == 0:
        observations.append("* Operational contradiction load has cleared for this snapshot.")

    if not observations:
        observations.append("* No deterministic operational shift detected beyond normal variation.")

    return observations


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> None:
    load_dotenv()
    config = load_runtime_config()

    runtime_cfg = config.get("runtime", {}) if isinstance(config, dict) else {}
    paths_cfg = runtime_cfg.get("paths", {}) if isinstance(runtime_cfg, dict) else {}
    telemetry_dir = Path(paths_cfg.get("telemetry_dir", "generated/telemetry"))
    telemetry_file = telemetry_dir / "daily_operational_metrics.jsonl"
    summary_file = telemetry_dir / "daily_operational_trends.md"
    trend_log_file = telemetry_dir / "trend_analysis.jsonl"

    history = _read_metrics_history(telemetry_file)
    if len(history) < 2:
        print("Not enough telemetry history. Need at least two snapshots.")
        log_event(
            trend_log_file,
            "telemetry_summary.skipped",
            reason="insufficient_history",
            telemetry_file=str(telemetry_file),
            snapshot_count=len(history),
        )
        return

    current = history[-1]
    previous = history[-2]
    trend_lines = _trend_lines(previous, current)

    log_event(
        trend_log_file,
        "telemetry_summary.generation_started",
        telemetry_file=str(telemetry_file),
        snapshot_count=len(history),
        current_snapshot_date=str(current.get("snapshot_date", "")),
        previous_snapshot_date=str(previous.get("snapshot_date", "")),
    )

    sections: List[str] = []
    sections.append("# Daily Operational Telemetry Trend Summary")
    sections.append("")
    sections.append(f"Generated at (UTC): {_utc_now()}")
    sections.append(f"Current snapshot: `{current.get('snapshot_date', 'unknown')}`")
    sections.append(f"Previous snapshot: `{previous.get('snapshot_date', 'unknown')}`")
    sections.append("")
    sections.append("## Current vs Previous")
    sections.extend([line.render() for line in trend_lines])
    sections.append("")
    sections.append("## Recent Historical Changes")
    recent_entries = history[-7:]
    sections.append(_history_change_text(recent_entries, "blocked_count", "Blocked Work"))
    sections.append(_history_change_text(recent_entries, "contradiction_count", "Contradictions"))
    sections.append(_history_change_text(recent_entries, "qa_count", "QA Queue"))
    sections.append(_history_change_text(recent_entries, "intake_count", "Intake Queue"))
    sections.append("")
    sections.append("## Deterministic Operational Observations")
    sections.extend(_deterministic_observations(current, previous))
    sections.append("")
    sections.append("## Explainability")
    sections.append("* Trend deltas are direct arithmetic comparisons from append-only daily operational metrics snapshots.")
    sections.append("* Observation statements are rule-based and only emitted when deterministic metric conditions are met.")

    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text("\n".join(sections) + "\n", encoding="utf-8")

    log_event(
        trend_log_file,
        "telemetry_summary.generated",
        summary_file=str(summary_file),
        telemetry_file=str(telemetry_file),
        trend_line_count=len(trend_lines),
        snapshot_count=len(history),
    )
    log_event(
        trend_log_file,
        "telemetry_summary.comparison_completed",
        compared_metrics=[metric for metric, _ in METRIC_ORDER],
        current_execution_id=str(current.get("execution_id", "")),
        previous_execution_id=str(previous.get("execution_id", "")),
    )

    print(summary_file)


if __name__ == "__main__":
    main()
