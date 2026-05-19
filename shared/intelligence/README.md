# Operational Intelligence Layer

This package contains deterministic operational intelligence primitives for the
Priority Governor system.

## Current assumptions

- Asana task dictionaries are the input shape.
- Operational meaning is split across dimensions:
  - `Section` = workflow lifecycle state (`where is the work operationally?`)
  - `Priority` = strategic importance / commitment (`how committed is this work?`)
  - `Health` = execution condition / risk (`what condition is execution in?`)
- Section and priority are intentionally independent. Example:
  `section=in_progress` with `priority=p4` is valid input and surfaced as an
  operational contradiction (low-commitment work consuming active capacity).
- `Priority` is normalized into `p0` through `p4`, with legacy values mapped as:
  `Critical -> p0`, `High -> p1`, `Medium -> p2`, and `Low -> p3`.
- `Scheduled / Ready to Launch` is normalized to `scheduled`.
- `Triage/Ready` and `Triage / Ready` are treated as the same section.
- Health/status values containing `blocked`, `waiting`, `at risk`, or `at_risk`
  are treated as blocked-like for contradiction detection.
- Due date means either `due_on` or `due_at` exists.

## Debugging real RWLV operational data

Use the analyzer in debug mode to inspect deterministic facts and findings before
any dashboard/rendering work:

```bash
python -m shared.intelligence.analyze_operational_health --project-gid "$ASANA_TEST_PROJECT_GID" --debug
```

Debug output includes:

- normalized section
- normalized priority
- normalized health
- classifications applied
- contradiction rules triggered
- emitted `OperationalSignal` fields (`signal_type`, `severity`, `task_name`, `message`)

You can also analyze an exported JSON list of Asana tasks:

```bash
python -m shared.intelligence.analyze_operational_health --task-json tasks.json --debug
```
