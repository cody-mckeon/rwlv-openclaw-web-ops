from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


@dataclass
class OperationalSignal:
    rule_name: str
    signal_type: str
    severity: str
    task_name: str
    message: str
    task_gid: str | None = None
    normalized_section: str = "unknown"
    normalized_priority: str = "unknown"
    classifications: Tuple[str, ...] = field(default_factory=tuple)
    details: Dict[str, Any] = field(default_factory=dict)
