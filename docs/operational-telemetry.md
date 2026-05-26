# Operational Telemetry Foundations

## Why snapshots exist

Operational state is point-in-time information. Overwriting a single generated file destroys history and weakens explainability. Snapshot persistence preserves deterministic runtime state per execution day.

## Telemetry philosophy

This runtime intentionally favors lightweight, deterministic telemetry:

- file-based snapshot history under `generated/snapshots/`
- structured JSONL logs per snapshot day
- no databases or cloud telemetry dependencies

The objective is to establish a durable telemetry substrate before introducing analytics layers.

## Historical operational state model

Each runtime day gets its own snapshot directory:

- `generated/snapshots/YYYY-MM-DD/CURRENT_PRIORITIES.generated.md`
- `generated/snapshots/YYYY-MM-DD/runtime.jsonl`

This provides a stable operational timeline that supports:

- workflow history
- root-cause review
- contradiction and task-volume trend baselining
- future outcome measurement

## Auditability goals

Snapshot-aware runtime events include context to support historical traceability:

- snapshot date
- runtime execution ID
- action/event type
- success/failure state
- counts (task volume, contradiction counts)

These records are intentionally minimal while still enabling operational audits.

## Future direction (not in this phase)

This phase does **not** add dashboards, databases, predictive systems, or BI tooling. Future phases can consume snapshot history for reporting and analytics without changing the core execution architecture.


## Lightweight operational metrics persistence

Phase D adds deterministic operational metrics extraction and append-only persistence:

- telemetry path: `generated/telemetry/daily_operational_metrics.jsonl`
- one metrics snapshot appended per runtime execution
- no dashboarding, databases, or analytics engines in this phase

Metrics are derived directly from runtime operational state and operational intelligence outputs, including:

- total task count
- open task count
- P0 count
- blocked count
- in progress count
- contradiction count
- launch risk count
- intake count
- QA count
- scheduled launch count

This telemetry is explainable and auditable because each metric is generated from explicit section, priority, or health labels and persisted with `snapshot_date` and `execution_id`.

## Future trend direction

Historical telemetry snapshots are intended as a foundation for future trend analysis (e.g., contradiction trendlines, blocked work trendlines, launch readiness trendlines). Future phases can read this append-only file and build reporting layers without changing runtime execution architecture.
