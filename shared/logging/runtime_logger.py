from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _utc_timestamp() -> str:
    """Return an ISO8601 UTC timestamp with a trailing Z."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def log_event(
    log_file: Path,
    event_type: str,
    severity: str = "info",
    **fields: Any,
) -> None:
    """Append a single structured JSONL runtime event."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {
        "timestamp": _utc_timestamp(),
        "event_type": event_type,
        "severity": severity,
        **fields,
    }

    with log_file.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n")
