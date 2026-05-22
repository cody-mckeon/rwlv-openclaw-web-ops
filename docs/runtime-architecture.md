# Runtime Architecture

## Purpose

RWLV uses a single operational runtime for deterministic, repeatable execution of Asana retrieval, operational intelligence generation, and Telegram digest delivery.

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
6. Write lightweight structured runtime logs in dated snapshot paths.

## Config and env model

- Non-secret runtime settings: `configs/runtime.yaml`
- Asana identifiers/config: `configs/asana.yaml`
- Secrets: `.env` and injected environment variables

## Execution flow

1. `skills.asana.actions.generate_current_priorities`
   - Reads config/env.
   - Pulls Asana tasks.
   - Runs operational intelligence.
   - Creates/uses `generated/snapshots/YYYY-MM-DD/`.
   - Writes `CURRENT_PRIORITIES.generated.md` into that dated snapshot directory.
   - Appends structured events to `generated/snapshots/YYYY-MM-DD/runtime.jsonl`.
2. `scripts.send_priority_digest`
   - Reads snapshot.
   - Builds digest text.
   - Sends to Telegram.
   - Logs digest send status and runtime events.

## Generated artifacts

- `generated/snapshots/YYYY-MM-DD/CURRENT_PRIORITIES.generated.md`: historical state snapshot.
- `generated/snapshots/YYYY-MM-DD/runtime.jsonl`: structured runtime events for that snapshot day.

## Container purpose and boundary

The container is intentionally focused on operational runtime execution only. It is not a Kubernetes service, distributed orchestrator, or cloud deployment abstraction.

This phase preserves the current architecture while improving runtime clarity, portability, and observability foundations for future VPS readiness.
