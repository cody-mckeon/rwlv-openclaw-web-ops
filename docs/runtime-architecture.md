# Runtime Architecture

## Purpose

RWLV uses a single operational runtime for deterministic, repeatable execution of Asana retrieval, operational intelligence generation, telemetry summarization, and Telegram digest delivery.

## Runtime environments

- **Local machine**: developer environment for coding, testing, and manual execution.
- **Docker container**: operational runtime environment with consistent dependencies and runtime behavior.
- **GitHub**: source control and automation trigger surface.
- **Telegram**: delivery layer for operational digest output.

## Core runtime responsibilities

1. Load config from `configs/runtime.yaml` and `configs/asana.yaml`.
2. Load secrets from `.env` (local) or container env vars.
3. Pull Asana task data.
4. Generate dated operational snapshot artifacts.
5. Produce/send digest notifications.
6. Generate deterministic telemetry trend summary artifacts.
7. Write lightweight structured runtime logs.

## Config and env model

- Non-secret runtime settings: `configs/runtime.yaml`
- Asana identifiers/config: `configs/asana.yaml`
- Secrets: `.env` and injected environment variables

## Deterministic internal scheduler runtime

The runtime container owns scheduling through `runtime/scheduler.py`.

- Service command: `python3 -m runtime.scheduler`
- Startup event: `scheduler_started`
- Recurring heartbeat event: `scheduler_heartbeat`
- Per-job lifecycle events: `scheduled_job_triggered`, `scheduled_job_completed`, `scheduled_job_failed`
- Runtime uptime semantics are included in scheduler heartbeat and job lifecycle events.

This keeps orchestration deterministic and container-owned without adding cron daemons, distributed workers, or external orchestration systems.

## Scheduling semantics

Scheduler cadence is deterministic and interval-based.

- `RUNTIME_SCHEDULER_POLL_SECONDS`: loop poll cadence.
- `RUNTIME_HEARTBEAT_INTERVAL_SECONDS`: heartbeat cadence.
- `RUNTIME_JOB_GENERATE_PRIORITIES_INTERVAL_SECONDS`
- `RUNTIME_JOB_PRIORITY_DIGEST_INTERVAL_SECONDS`
- `RUNTIME_JOB_TELEMETRY_SUMMARY_INTERVAL_SECONDS`

Each job uses stable interval windows and a deterministic next-run calculation. If a run is delayed, the scheduler advances to the correct subsequent deterministic window rather than introducing random jitter.

## Scheduled operational jobs

1. `skills.asana.actions.generate_current_priorities`
2. `scripts.send_priority_digest`
3. `scripts.telemetry_summary`

Jobs run inside the same container lifecycle. Failures are logged and do not stop the scheduler loop, preserving operational continuity.

## Generated artifacts and persistence

The runtime writes generated artifacts under:

- `generated/`
- `generated/logs/`
- `generated/telemetry/`

In Docker, the host bind mount `./generated:/app/generated` preserves operational history across container restarts/recreation while keeping the architecture lightweight and file-based.

## Container purpose and boundary

The container is intentionally focused on deterministic operational runtime execution only.

This phase explicitly avoids:

- Linux cron daemons
- Kubernetes or distributed orchestration
- Airflow/Celery/Redis job systems
- cloud schedulers and queue infrastructure

The design goal is trusted, repeatable operational execution with minimal orchestration complexity.
