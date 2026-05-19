from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class OperationalSignal:
    """A deterministic operational finding produced by a tiny rule."""

    signal_type: str
    severity: str
    task_name: str
    message: str
    task_gid: str | None = None
    rule_name: str | None = None
    normalized_section: str | None = None
    normalized_priority: str | None = None
    classifications: Tuple[str, ...] = field(default_factory=tuple)
    details: Dict[str, Any] = field(default_factory=dict)
