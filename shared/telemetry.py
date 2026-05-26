from __future__ import annotations

from dataclasses import dataclass
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class SnapshotContext:
    snapshot_date: str
    execution_id: str
    snapshot_dir: Path
    priorities_file: Path
    runtime_log_file: Path


def build_snapshot_context(runtime_cfg: Dict[str, Any], today: date | None = None) -> SnapshotContext:
    current_day = today or date.today()
    snapshot_date = current_day.isoformat()

    paths_cfg = runtime_cfg.get("paths", {}) if isinstance(runtime_cfg, dict) else {}
    snapshots_dir = Path(paths_cfg.get("snapshots_dir", "generated/snapshots"))
    snapshot_dir = snapshots_dir / snapshot_date

    execution_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    return SnapshotContext(
        snapshot_date=snapshot_date,
        execution_id=execution_id,
        snapshot_dir=snapshot_dir,
        priorities_file=snapshot_dir / "CURRENT_PRIORITIES.generated.md",
        runtime_log_file=snapshot_dir / "runtime.jsonl",
    )


def resolve_latest_priorities_file(runtime_cfg: Dict[str, Any]) -> Path:
    paths_cfg = runtime_cfg.get("paths", {}) if isinstance(runtime_cfg, dict) else {}
    snapshots_dir = Path(paths_cfg.get("snapshots_dir", "generated/snapshots"))

    dated_dirs = sorted([path for path in snapshots_dir.glob("*") if path.is_dir()])
    if dated_dirs:
        latest = dated_dirs[-1]
        candidate = latest / "CURRENT_PRIORITIES.generated.md"
        if candidate.exists():
            return candidate

    # Fallback for legacy generated artifact location.
    return snapshots_dir / "CURRENT_PRIORITIES.generated.md"



def _section_label_set(task: Dict[str, Any]) -> set[str]:
    labels: set[str] = set()
    for membership in task.get("memberships", []) or []:
        section = membership.get("section") or {}
        name = (section.get("name") or "").strip().lower()
        if name:
            labels.add(name)
    return labels


def _priority_value(task: Dict[str, Any]) -> str:
    for field in task.get("custom_fields", []) or []:
        if (field.get("name") or "").strip().lower() == "priority":
            return (field.get("display_value") or "").strip().lower()
    return ""


def _is_open(task: Dict[str, Any]) -> bool:
    return not bool(task.get("completed"))


def _task_contributor(task: Dict[str, Any], reason: str, relevant_fields: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "task_name": task.get("name") or "Untitled task",
        "reason": reason,
        "relevant_fields": relevant_fields,
    }
    gid = task.get("gid")
    if gid:
        payload["task_gid"] = str(gid)
    return payload


def extract_operational_metrics(tasks: list[Dict[str, Any]], contradiction_count: int = 0, launch_risk_count: int = 0) -> Dict[str, int]:
    open_tasks = [task for task in tasks if _is_open(task)]

    def in_section(task: Dict[str, Any], section: str) -> bool:
        return section.strip().lower() in _section_label_set(task)

    p0_count = sum(1 for task in open_tasks if _priority_value(task).startswith("p0"))
    blocked_status_values = {
        "blocked",
        "waiting on vendor",
        "waiting on content",
        "waiting on stakeholder",
        "waiting approval",
        "at risk",
        "expedited",
    }

    def execution_status(task: Dict[str, Any]) -> str:
        aliases = {
            "health and execution status",
            "field health and execution status",
            "execution status",
            "health",
            "health / execution status",
            "health / execution",
        }
        for field in task.get("custom_fields", []) or []:
            if (field.get("name") or "").strip().lower() in aliases:
                return (field.get("display_value") or "").strip().lower()
        return ""

    blocked_count = sum(1 for task in open_tasks if execution_status(task) in blocked_status_values)
    in_progress_count = sum(1 for task in open_tasks if in_section(task, "In Progress"))
    intake_count = sum(1 for task in open_tasks if in_section(task, "Intake"))
    qa_count = sum(1 for task in open_tasks if in_section(task, "QA"))
    scheduled_launch_count = sum(1 for task in open_tasks if in_section(task, "Scheduled / Ready to Launch"))

    return {
        "task_count": len(tasks),
        "open_task_count": len(open_tasks),
        "p0_count": p0_count,
        "blocked_count": blocked_count,
        "in_progress_count": in_progress_count,
        "contradiction_count": int(contradiction_count),
        "launch_risk_count": int(launch_risk_count),
        "intake_count": intake_count,
        "qa_count": qa_count,
        "scheduled_launch_count": scheduled_launch_count,
    }


def append_telemetry_snapshot(runtime_cfg: Dict[str, Any], snapshot_date: str, execution_id: str, metrics: Dict[str, int]) -> Path:
    paths_cfg = runtime_cfg.get("paths", {}) if isinstance(runtime_cfg, dict) else {}
    telemetry_dir = Path(paths_cfg.get("telemetry_dir", "generated/telemetry"))
    telemetry_file = telemetry_dir / "daily_operational_metrics.jsonl"
    telemetry_dir.mkdir(parents=True, exist_ok=True)

    payload: Dict[str, Any] = {
        "snapshot_date": snapshot_date,
        "execution_id": execution_id,
        **metrics,
    }

    with telemetry_file.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n")

    return telemetry_file


def generate_telemetry_debug_artifacts(
    *,
    runtime_cfg: Dict[str, Any],
    snapshot_date: str,
    tasks: list[Dict[str, Any]],
    operational_signals: list[Any],
) -> Dict[str, Path]:
    paths_cfg = runtime_cfg.get("paths", {}) if isinstance(runtime_cfg, dict) else {}
    telemetry_dir = Path(paths_cfg.get("telemetry_dir", "generated/telemetry"))
    debug_dir = telemetry_dir / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    blocked_status_values = {
        "blocked",
        "waiting on vendor",
        "waiting on content",
        "waiting on stakeholder",
        "waiting approval",
        "at risk",
        "expedited",
    }

    contributors_blocked: list[Dict[str, Any]] = []
    for task in tasks:
        if not _is_open(task):
            continue
        health = ""
        for field in task.get("custom_fields", []) or []:
            if (field.get("name") or "").strip().lower() in {
                "health and execution status",
                "field health and execution status",
                "execution status",
                "health",
                "health / execution status",
                "health / execution",
            }:
                health = (field.get("display_value") or "").strip()
                break
        if health.strip().lower() in blocked_status_values:
            contributors_blocked.append(
                _task_contributor(
                    task,
                    reason=f"Health = {health}",
                    relevant_fields={"health_execution_status": health},
                )
            )

    contributors_contradictions: list[Dict[str, Any]] = []
    for signal in operational_signals or []:
        if getattr(signal, "signal_type", "") not in {"contradiction", "workflow_contradiction"}:
            continue
        entry: Dict[str, Any] = {
            "task_name": getattr(signal, "task_name", "Untitled task"),
            "reason": getattr(signal, "message", "Operational contradiction"),
            "relevant_fields": {
                "signal_type": getattr(signal, "signal_type", ""),
                "rule_name": getattr(signal, "rule_name", ""),
                "severity": getattr(signal, "severity", ""),
            },
        }
        task_gid = getattr(signal, "task_gid", None)
        if task_gid:
            entry["task_gid"] = str(task_gid)
        contributors_contradictions.append(entry)

    contributors_launch_risk: list[Dict[str, Any]] = []

    artifact_payloads = {
        f"blocked_tasks_{snapshot_date}.json": contributors_blocked,
        f"contradiction_tasks_{snapshot_date}.json": contributors_contradictions,
        f"launch_risk_tasks_{snapshot_date}.json": contributors_launch_risk,
    }

    generated_paths: Dict[str, Path] = {}
    for file_name, payload in artifact_payloads.items():
        artifact_path = debug_dir / file_name
        artifact_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        generated_paths[file_name] = artifact_path

    return generated_paths
