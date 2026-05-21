from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def log_event(log_file: Path, event: str, **fields: Any) -> None:
    """Append a lightweight structured JSONL runtime event."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
