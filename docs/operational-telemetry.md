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

## Metric semantics and explainability

Operational telemetry metrics are intentionally deterministic and auditable:

- `blocked_count`: count of open tasks whose health/execution custom field resolves to one of: `Blocked`, `Waiting on Vendor`, `Waiting on Content`, `Waiting on Stakeholder`, `Waiting Approval`, `At Risk`, or `Expedited`.
- `launch_risk_count`: currently supplied by runtime operational intelligence integration (presently `0` until launch-risk rule decomposition is introduced).
- `contradiction_count`: count of operational contradiction signals produced by contradiction rules (currently workflow contradictions such as P4 work in active execution lanes).

To preserve explainability and operational trust, each execution also writes metric decomposition artifacts under:

- `generated/telemetry/debug/blocked_tasks_YYYY-MM-DD.json`
- `generated/telemetry/debug/launch_risk_tasks_YYYY-MM-DD.json`
- `generated/telemetry/debug/contradiction_tasks_YYYY-MM-DD.json`

These files map aggregate counts back to task-level contributors (`task_name`, optional `task_gid`, explicit `reason`, and relevant operational fields). This keeps telemetry governance-first and avoids opaque analytics behavior.

## Future trend direction

Historical telemetry snapshots are intended as a foundation for future trend analysis (e.g., contradiction trendlines, blocked work trendlines, launch readiness trendlines). Future phases can read this append-only file and build reporting layers without changing runtime execution architecture.

## Deterministic historical trend analysis

Phase D extends telemetry foundations with deterministic historical trend interpretation via:

- `scripts/telemetry_summary.py`
- telemetry source: `generated/telemetry/daily_operational_metrics.jsonl`
- deterministic summary output: `generated/telemetry/daily_operational_trends.md`
- structured trend runtime log: `generated/telemetry/trend_analysis.jsonl`

### Trend analysis philosophy

Trend interpretation remains governance-first and explainable:

- no dashboarding, BI platforms, pandas analytics stacks, or databases
- no AI-generated recommendations, predictive forecasting, or black-box scoring
- no LLM-generated operational narrative dependencies

All trend statements are deterministic rule outputs grounded in explicit metric deltas.

### Deterministic trend calculations

The summary script compares:

- current snapshot vs previous snapshot
- recent historical movement (up to the latest 7 snapshots)

Metric deltas are rendered with explicit arithmetic semantics such as:

- increased (`previous → current`, `+delta`)
- reduced (`previous → current`, negative delta)
- stable (`current value` unchanged)

This keeps the trend layer fully auditable and reproducible from append-only telemetry state.

### Lightweight operational observations

Observation lines are deterministic operational heuristics based on metric relationships (for example blocked, intake, in-progress, QA, and contradiction shifts). They are intentionally constrained to operational interpretation only.

### Operational governance direction

Deterministic trend summaries are intended to support:

- operational visibility
- governance checkpoints
- client reporting context
- future outcome measurement baselines

This phase still avoids predictive intelligence and preserves architecture simplicity while enabling historical telemetry interpretation.

## Deterministic operational governance modeling (Phase E)

Phase E adds deterministic governance classification with no AI scoring, prediction, or ML behavior.

### Governance model location

- module: `shared/governance/health_model.py`
- output type: `GovernanceClassification`
- evaluation entrypoint: `evaluate_governance(metrics)`

### Governance states

The classifier emits one deterministic governance state per metrics snapshot:

- `Healthy`
- `Degraded`
- `At Risk`
- `Unstable`
- `Overloaded`

State assignment is rule-driven, explainable, and auditable from persisted metrics.

### Example deterministic governance rules

Representative rule semantics include:

- if `blocked_count > in_progress_count` → state promotion to `Degraded`
- if `contradiction_count > 3` → state promotion to `At Risk`
- if `contradiction_count > 5` → state promotion to `Unstable`
- if interrupt/dependency pressure thresholds are exceeded → state promotion to `Overloaded`
- if `intake_count > in_progress_count * 2` → execution pressure set to `Increasing`

State transitions follow deterministic severity promotion (`Healthy` < `Degraded` < `At Risk` < `Unstable` < `Overloaded`).

### Explainability semantics

Each governance evaluation produces:

- `governance_state`
- `execution_pressure`
- `triggered_rules`
- `reasons`
- `contributing_metrics`

This allows every classification decision to be traced back to explicit metric values and explicit triggered rules.

### Telemetry summary integration

`scripts/telemetry_summary.py` now embeds governance output into the deterministic daily summary:

- governance state
- triggered governance rules
- governance explanation reasons
- execution pressure indicator

### Governance runtime logging

Governance evaluation events are appended to:

- `generated/telemetry/trend_analysis.jsonl`

Logged event types include:

- `governance.evaluated`
- `governance.transition_observed`

This preserves historical governance auditability and state transition traceability without introducing external analytics systems.

### Architecture constraints preserved

Phase E continues to intentionally avoid:

- AI-generated scoring
- predictive systems
- LLM operational recommendations
- black-box analytics
- dashboards
- ML-based governance systems

Governance modeling is deterministic operational classification only.
