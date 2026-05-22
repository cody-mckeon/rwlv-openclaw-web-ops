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
