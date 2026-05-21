from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from shared.config.runtime import ConfigError


class RuntimeValidationError(RuntimeError):
    """Raised when runtime preflight validation fails."""


StatusItem = Tuple[str, bool, str]


def _is_writable_directory(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".rwlv_write_check"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def _required_runtime_sections(config: Dict[str, Any]) -> List[str]:
    runtime_cfg = config.get("runtime") if isinstance(config, dict) else None
    if not isinstance(runtime_cfg, dict):
        return ["runtime"]

    required = ["paths", "logging"]
    missing = [section for section in required if section not in runtime_cfg]
    return missing


def _required_env_values(required_env: Iterable[str]) -> List[str]:
    missing = []
    for var_name in required_env:
        if not (os.getenv(var_name) or "").strip():
            missing.append(var_name)
    return missing


def evaluate_runtime_health(config: Dict[str, Any], required_env: Iterable[str]) -> List[StatusItem]:
    runtime_cfg = config.get("runtime", {}) if isinstance(config, dict) else {}
    asana_cfg = config.get("asana", {}) if isinstance(config, dict) else {}

    logs_dir = Path(str(runtime_cfg.get("paths", {}).get("logs_dir", "generated/logs")))
    generated_dir = Path(str(runtime_cfg.get("paths", {}).get("generated_dir", "generated")))

    missing_sections = _required_runtime_sections(config)
    missing_env = _required_env_values(required_env)

    asana_gid = str(asana_cfg.get("project_gid", "")).strip()
    asana_ok = bool(asana_gid)

    telegram_ok = all(
        (os.getenv(name) or "").strip()
        for name in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
    )

    generated_exists = generated_dir.exists() or _is_writable_directory(generated_dir)
    logs_ok = _is_writable_directory(logs_dir)

    return [
        ("Docker Runtime", True, "Running in deterministic CLI runtime"),
        ("Asana Config", asana_ok, "project_gid is configured" if asana_ok else "Missing asana.project_gid"),
        ("Telegram Config", telegram_ok, "Telegram env vars configured" if telegram_ok else "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID"),
        ("Generated Paths", generated_exists, f"{generated_dir} exists/writable" if generated_exists else f"{generated_dir} is unavailable"),
        ("Structured Logging", logs_ok, f"{logs_dir} is writable" if logs_ok else f"{logs_dir} is not writable"),
        ("Required Config", not missing_sections, "Required runtime config sections present" if not missing_sections else f"Missing runtime sections: {', '.join(missing_sections)}"),
        ("Environment Variables", not missing_env, "Required env vars present" if not missing_env else f"Missing env vars: {', '.join(missing_env)}"),
    ]


def validate_runtime_startup(config: Dict[str, Any], required_env: Iterable[str]) -> None:
    health = evaluate_runtime_health(config, required_env)
    failures = [f"{name}: {detail}" for name, ok, detail in health if not ok]
    if failures:
        raise RuntimeValidationError(
            "Runtime startup validation failed. " + " | ".join(failures)
        )
