from __future__ import annotations

from dataclasses import dataclass
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
