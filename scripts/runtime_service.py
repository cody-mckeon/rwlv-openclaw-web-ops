from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from shared.runtime_logging import log_event


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _runtime_log_path() -> Path:
    return Path("generated/logs/runtime.jsonl")


def _run_step(step_name: str, module_name: str, log_file: Path) -> None:
    started_at = time.time()
    log_event(log_file, "scheduled_execution_triggered", step=step_name, module=module_name)

    result = subprocess.run(
        ["python3", "-m", module_name],
        capture_output=True,
        text=True,
        check=False,
    )

    duration_ms = int((time.time() - started_at) * 1000)
    if result.returncode == 0:
        log_event(
            log_file,
            "scheduled_execution_completed",
            step=step_name,
            module=module_name,
            duration_ms=duration_ms,
        )
        return

    log_event(
        log_file,
        "scheduled_execution_failed",
        severity="error",
        step=step_name,
        module=module_name,
        duration_ms=duration_ms,
        return_code=result.returncode,
        stdout_tail=result.stdout[-1000:],
        stderr_tail=result.stderr[-1000:],
    )


def main() -> None:
    log_file = _runtime_log_path()
    interval_seconds = int(os.getenv("RUNTIME_SCHEDULE_INTERVAL_SECONDS", "1800"))
    heartbeat_seconds = int(os.getenv("RUNTIME_HEARTBEAT_INTERVAL_SECONDS", "300"))

    started_at = time.time()
    last_heartbeat = 0.0

    log_event(log_file, "runtime_started", runtime_started_at=_utc_now(), schedule_interval_seconds=interval_seconds)
    log_event(log_file, "scheduler_active", heartbeat_interval_seconds=heartbeat_seconds)

    while True:
        loop_started = time.time()

        _run_step("generate_priorities", "skills.asana.actions.generate_current_priorities", log_file)
        _run_step("send_priority_digest", "scripts.send_priority_digest", log_file)

        now = time.time()
        if now - last_heartbeat >= heartbeat_seconds:
            uptime_seconds = int(now - started_at)
            log_event(log_file, "runtime_heartbeat", uptime_seconds=uptime_seconds)
            last_heartbeat = now

        elapsed = time.time() - loop_started
        sleep_seconds = max(0, interval_seconds - int(elapsed))
        log_event(log_file, "scheduler_sleeping", sleep_seconds=sleep_seconds)
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()
