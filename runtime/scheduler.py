from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List

from shared.runtime_logging import log_event


@dataclass
class ScheduledJob:
    name: str
    module_name: str
    interval_seconds: int
    next_run_at: float = 0.0


def _runtime_log_path() -> Path:
    return Path("generated/logs/runtime.jsonl")


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default

    try:
        value = int(raw)
    except ValueError:
        return default

    return max(1, value)


def _build_jobs(now: float) -> List[ScheduledJob]:
    jobs = [
        ScheduledJob(
            name="generate_current_priorities",
            module_name="skills.asana.actions.generate_current_priorities",
            interval_seconds=_int_env("RUNTIME_JOB_GENERATE_PRIORITIES_INTERVAL_SECONDS", 1800),
        ),
        ScheduledJob(
            name="send_priority_digest",
            module_name="scripts.send_priority_digest",
            interval_seconds=_int_env("RUNTIME_JOB_PRIORITY_DIGEST_INTERVAL_SECONDS", 1800),
        ),
        ScheduledJob(
            name="generate_telemetry_summary",
            module_name="scripts.telemetry_summary",
            interval_seconds=_int_env("RUNTIME_JOB_TELEMETRY_SUMMARY_INTERVAL_SECONDS", 3600),
        ),
    ]

    for job in jobs:
        job.next_run_at = now

    return jobs


def _run_job(job: ScheduledJob, log_file: Path, runtime_started_at: float) -> None:
    trigger_ts = time.time()
    runtime_uptime_seconds = int(trigger_ts - runtime_started_at)
    log_event(
        log_file,
        "scheduled_job_triggered",
        job=job.name,
        module=job.module_name,
        interval_seconds=job.interval_seconds,
        runtime_uptime_seconds=runtime_uptime_seconds,
    )

    started = time.time()
    result = subprocess.run(["python3", "-m", job.module_name], capture_output=True, text=True, check=False)
    duration_ms = int((time.time() - started) * 1000)

    if result.returncode == 0:
        log_event(
            log_file,
            "scheduled_job_completed",
            job=job.name,
            module=job.module_name,
            duration_ms=duration_ms,
            runtime_uptime_seconds=int(time.time() - runtime_started_at),
        )
        return

    log_event(
        log_file,
        "scheduled_job_failed",
        severity="error",
        job=job.name,
        module=job.module_name,
        duration_ms=duration_ms,
        return_code=result.returncode,
        stdout_tail=result.stdout[-1000:],
        stderr_tail=result.stderr[-1000:],
        runtime_uptime_seconds=int(time.time() - runtime_started_at),
    )


def main() -> None:
    log_file = _runtime_log_path()
    heartbeat_seconds = _int_env("RUNTIME_HEARTBEAT_INTERVAL_SECONDS", 300)
    poll_seconds = _int_env("RUNTIME_SCHEDULER_POLL_SECONDS", 1)

    runtime_started_at = time.time()
    jobs = _build_jobs(runtime_started_at)
    last_heartbeat = 0.0

    log_event(
        log_file,
        "scheduler_started",
        heartbeat_interval_seconds=heartbeat_seconds,
        scheduler_poll_seconds=poll_seconds,
        jobs=[
            {
                "job": job.name,
                "module": job.module_name,
                "interval_seconds": job.interval_seconds,
            }
            for job in jobs
        ],
    )

    while True:
        now = time.time()

        if now - last_heartbeat >= heartbeat_seconds:
            log_event(
                log_file,
                "scheduler_heartbeat",
                runtime_uptime_seconds=int(now - runtime_started_at),
                tracked_jobs=len(jobs),
            )
            last_heartbeat = now

        for job in jobs:
            if now >= job.next_run_at:
                _run_job(job, log_file, runtime_started_at)
                job.next_run_at += job.interval_seconds
                if job.next_run_at <= now:
                    missed_intervals = int((now - job.next_run_at) // job.interval_seconds) + 1
                    job.next_run_at += missed_intervals * job.interval_seconds

        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
