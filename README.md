# RWLV OpenClaw Web Ops

## Purpose

This repository is no longer treated as a standalone AI experiment.

It is the operational implementation layer for a future multi-client AI operations platform.

The current simulated production client is:

* Resorts World Las Vegas (RWLV)

The goal is not simply to build AI agents.

The goal is to build:

* operational intelligence systems
* reusable infrastructure patterns
* maintainable agent architecture
* scalable workflow automation
* governance-aware operational tooling
* observable operational pipelines
* future multi-client operational capability

This repository represents:

> the RWLV operational environment.

It is intentionally separated from any future reusable core platform infrastructure.

---

## Runtime Observability (Phase A)

This runtime now writes lightweight structured operational events to:

```text
generated/logs/runtime.jsonl
```

### Philosophy

- Runtime logs are **machine-readable operational observability**.
- Telegram digest output is **human-facing operational summary**.
- These are intentionally separate concerns.

### Logging approach

- JSON Lines (`.jsonl`) append-only file
- One valid JSON object per line
- UTC timestamped events
- Sparse, meaningful operational events (not verbose noise)
- Python standard library only (no external logging frameworks)

Typical events include runtime start, Asana fetch results, operational intelligence analysis, contradiction detections, digest generation, and Telegram send results.

## Operational Artifact Persistence

The runtime writes operational artifacts into:

```text
generated/
```

In Docker, container filesystems are ephemeral by default. If artifacts are only written inside the container layer, they can disappear when that container lifecycle ends.

To preserve operational history, `docker-compose.yml` bind-mounts the local repository path:

```text
./generated
```

to the container path:

```text
/app/generated
```

This keeps runtime outputs visible on the host and durable across container runs while staying lightweight and explicit.

### Container filesystem

Ephemeral runtime state used during execution.

### generated/

Persistent operational artifacts (for example logs and snapshots) retained on the local host filesystem.

### Persistence philosophy

- Keep infrastructure simple and explainable.
- Preserve deterministic operational history in plain files.
- Maintain runtime portability and reproducibility without external storage systems.

# Architectural Philosophy

## Core Principle

Operational intelligence quality is driven primarily by:

* workflow semantics
* normalization quality
* operational truth
* observability
* maintainability

NOT simply:

* LLM prompting
* AI summaries
* automation complexity

The system is designed around deterministic operational modeling first.

---

# Repository Role

This repository:

```text
rwlv-openclaw-web-ops/
```

represents:

```text
RWLV-specific operational implementation
```

A future repository such as:

```text
openclaw-core/
```

would instead contain:

* reusable runtime infrastructure
* shared logging
* scheduler abstractions
* notification systems
* execution frameworks
* generic utilities
* shared operational primitives

This repository contains:

* RWLV workflow semantics
* operational rules
* Asana structure
* runtime configuration
* delivery formatting
* operational intelligence behavior
* client-specific implementation details

---

# Operational Workflow Taxonomy

The operational workflow taxonomy is intentionally semantic.

Each section represents a distinct operational meaning.

## Workflow Lifecycle

```text
Ideas / Parking Lot
↓
Intake
↓
Triage / Ready
↓
In Progress
↓
QA
↓
Scheduled / Ready to Launch
↓
Done
↓
Canceled
```

---

## Section Definitions

### Ideas / Parking Lot

Represents:

* idea capture
* future concepts
* optional initiatives
* long-term thoughts
* non-committed work

This section is intentionally low-pressure.

Items here are NOT expected to move quickly.

---

### Intake

Represents:

* newly captured work
* discovery
* clarification
* scoping
* prioritization evaluation

Work here has not yet been operationally committed.

---

### Triage / Ready

Represents:

> work that could realistically enter execution soon.

This is a near-term execution candidate queue.

---

### In Progress

Represents:

* active execution
* operational focus
* currently consuming execution capacity

This section should remain intentionally constrained.

---

### QA

Represents:

* validation
* review
* testing
* stakeholder verification
* pre-launch checks

---

### Scheduled / Ready to Launch

Represents:

* approved work
* operationally near launch
* release coordination
* awaiting deployment timing

---

### Done

Represents:

* completed work
* launched work
* operationally resolved items

---

### Canceled

Represents:

* intentionally abandoned work
* invalidated initiatives
* deprioritized tasks

Canceled work is operationally useful historical context.

---

# Operational Dimensions

The system intentionally models multiple dimensions of operational meaning.

These dimensions are NOT interchangeable.

---

## 1. Section

Represents:

```text
workflow lifecycle state
```

Examples:

* Intake
* In Progress
* QA
* Done

This answers:

> "Where is the work operationally?"

---

## 2. Priority

Represents:

```text
strategic importance / execution commitment
```

Examples:

* P0 - Critical / Interrupt
* P1 - Active / Committed
* P2 - Important / Scheduled
* P3 - Backlog / Nice-to-have
* P4 - Someday / Parking Lot

This answers:

> "How strategically important or committed is this work?"

---

## 3. Health / Execution

Represents:

```text
execution condition / operational risk
```

Examples:

* On Track
* Waiting on Vendor
* Blocked
* Waiting on Stakeholder
* At Risk

This answers:

> "What is the current execution condition?"

---

# Important Operational Principle

Section and Priority are NOT the same thing.

Examples of VALID states:

```text
Section = Intake
Priority = P4
```

Meaning:

> captured idea with low strategic commitment.

This is healthy.

---

```text
Section = Ideas / Parking Lot
Priority = P4
```

Also healthy.

---

```text
Section = In Progress
Priority = P4
```

This is a meaningful operational contradiction because low-commitment work is consuming active execution capacity.

This distinction is foundational to the operational intelligence architecture.

---

# Operational Intelligence Philosophy

Operational intelligence should:

* surface workflow contradictions
* identify execution drift
* reduce operational ambiguity
* improve prioritization clarity
* expose bottlenecks
* support governance
* remain deterministic and explainable

Operational intelligence should NOT:

* generate vague AI commentary
* replace operational judgment
* create noisy alerts
* invent false urgency
* overcomplicate workflow semantics

---

# Current Operational Intelligence Rules

## Implemented

### detect_p4_in_progress()

Purpose:

Detect low-commitment work consuming active execution capacity.

Example:

```text
Priority = P4
+
Section = In Progress
```

This is classified as:

```text
workflow hygiene drift
```

---

# Normalization Philosophy

Operational rules should NEVER depend on:

* raw UI labels
* verbose human strings
* exact workflow wording

Instead:

all operational logic runs on canonical normalized values.

Example:

```text
P4 - Someday / Parking Lot
↓
p4
```

This allows:

* stable operational reasoning
* reusable rule logic
* workflow wording flexibility
* maintainable architecture

---

# Repository Structure

The current repository structure reflects the present operational implementation state of the RWLV operational intelligence system.

The architecture is intentionally evolving gradually through real operational pressure rather than premature enterprise abstraction.

Current repository structure:

```text
rwlv-openclaw-web-ops/

.github/
  workflows/

configs/
  asana.yaml
  runtime.yaml

scripts/
  morning_digest.sh
  morning_priority_digest.sh
  send_priority_digest.py
  update_priorities.sh

shared/
  config/
  intelligence/
  __init__.py

skills/
  asana/
    actions/
      generate_current_priorities.py
      read_subtasks.py
      read_tasks.py

    tests/
      test_asana_read.py
      test_operational_intelligence.py
      test_priority_governor_classification.py

    tools/
      asana_client.py

README.md
requirements.txt
.gitignore

AGENTS.md
CURRENT_PRIORITIES.md
HEARTBEAT.md
IDENTITY.md
SOUL.md
TOOLS.md
USER.md
```

---

## Current Repository Layer Responsibilities

### configs/

Represents:

```text
runtime configuration layer
```

Contains:

* Asana project configuration
* runtime behavior settings
* operational toggles
* environment-independent repository configuration

Examples:

* asana.yaml
* runtime.yaml

This layer intentionally separates:

* operational configuration
  FROM:
* application logic

---

### scripts/

Represents:

```text
operational orchestration + runtime entrypoints
```

Contains:

* digest execution
* scheduled workflows
* operational runtime scripts
* shell wrappers
* delivery execution

Examples:

* send_priority_digest.py
* update_priorities.sh
* morning_digest.sh

This layer is intentionally thin.

Scripts should orchestrate systems rather than contain operational intelligence logic.

---

### shared/

Represents:

```text
shared operational infrastructure
```

Contains:

* normalization
* operational intelligence
* reusable runtime helpers
* shared operational models
* cross-system operational primitives

Examples:

* shared/config/
* shared/intelligence/

This layer is intended to evolve into reusable operational infrastructure over time.

---

### skills/

Represents:

```text
integration-specific operational capability
```

Current implementation:

```text
skills/asana/
```

Contains:

* Asana actions
* Asana tools
* integration tests
* workflow extraction logic
* operational task processing

This layer intentionally isolates:

* external integration behavior
  FROM:
* shared operational intelligence

---

### .github/workflows/

Represents:

```text
automation + scheduled execution infrastructure
```

Current usage includes:

* GitHub Actions digest execution
* scheduled operational workflows
* future CI/testing automation

---

## Legacy OpenClaw Bootstrap Files

The repository currently still contains legacy OpenClaw workspace bootstrap files:

* AGENTS.md
* HEARTBEAT.md
* IDENTITY.md
* SOUL.md
* TOOLS.md
* USER.md

These originate from the earlier OpenClaw workspace experimentation phase.

They currently remain in the repository while the architecture transitions toward a more structured operational platform.

These files are NOT yet fully integrated into the newer operational architecture.

Over time they may:

* move into docs/
* become runtime identity layers
* evolve into operational agent configuration
* or be deprecated entirely

The current priority is:

```text
operational system stabilization
```

NOT large-scale repository restructuring.

---

## Important Architectural Principle

The current repository intentionally reflects:

```text
RWLV-specific operational implementation
```

NOT:

```text
future multi-client core platform abstraction
```

This distinction matters.

The repository is expected to contain:

* RWLV workflow semantics
* RWLV operational taxonomy
* RWLV operational intelligence rules
* RWLV delivery workflows
* RWLV runtime configuration

This is currently healthy and intentional.

Future repositories such as:

```text
openclaw-core/
```

may eventually extract:

* reusable runtime systems
* generic operational primitives
* shared orchestration
* cross-client infrastructure

But that abstraction layer is intentionally deferred until operational pressure justifies it.

---

# Config Philosophy

The system intentionally separates:

## Operational Configuration

Stored in:

```text
configs/
```

Examples:

* Asana project IDs
* workflow settings
* operational toggles
* digest behavior
* runtime settings

These are NOT secrets.

---

## Secrets

Stored in:

```text
.env
```

Bootstrap from the repository-safe template:

```bash
cp .env.example .env
```

Then populate only real secrets in `.env`.

Examples:

* Asana access tokens
* OpenAI API keys
* Telegram tokens

Secrets should NEVER be committed.

---

# Runtime Flow

Current operational pipeline:

```text
Asana API
↓
Normalization
↓
Operational Intelligence
↓
Generated Snapshot
↓
Digest Rendering
↓
Delivery Layer
```

This separation is intentional.

The delivery layer should NOT:

* directly query Asana
* perform normalization
* contain operational intelligence logic

It should consume generated operational state.

---

# Local Development Workflow

## Pull Latest Changes

```bash
git checkout main
git pull
```

---

## Runtime Setup

```bash
cp .env.example .env
```

Then:

* populate `.env` secrets
* configure `configs/asana.yaml` with project IDs and workflow settings

---

## Run Unit Tests

```bash
python3 -m unittest discover -s skills/asana/tests -p 'test_*.py'
```

---

## Generate Operational Snapshot

```bash
python3 -m skills.asana.actions.generate_current_priorities
```

---

## Send Digest

```bash
python3 -m scripts.send_priority_digest
```

---

# Operational Development Philosophy

Development should follow:

```text
small rule
↓
real workflow validation
↓
observability
↓
operational usefulness
↓
expand carefully
```

NOT:

```text
build giant AI system immediately
```

---

# Design Principles

## Prefer:

* deterministic logic
* explainable signals
* modular architecture
* operational truth
* observability
* semantic clarity
* low-noise intelligence
* maintainability
* workflow realism

---

## Avoid:

* overengineering
* giant rule engines
* premature abstraction
* AI-generated noise
* vague governance systems
* enterprise complexity for its own sake

---

# Current State

The system currently supports:

* Asana retrieval
* workflow normalization
* multidimensional operational modeling
* operational contradiction detection
* generated operational snapshots
* Telegram digest delivery
* Natural language Telegram operational retrieval routing (see `docs/telegram-operational-routing.md`)
* structured workflow taxonomy
* regression testing
* config-driven runtime behavior

The platform is still evolving, but the architecture is now moving toward a maintainable operational intelligence system rather than isolated automation scripts.

---

# Phase 1 Containerization (Lightweight Runtime)

This repository now supports a lightweight Dockerized runtime focused on deterministic local execution.

The container setup intentionally preserves the current architecture and workflow. It does **not** add orchestration, infrastructure stacks, or deployment tooling.

## Build Runtime Image

```bash
docker compose build
```

## Open Interactive Runtime Shell

```bash
docker compose run rwlv-runtime bash
```

## Run Unit Tests in Container

```bash
docker compose run rwlv-runtime python3 -m unittest discover -s skills/asana/tests -p 'test_*.py'
```

## Generate Operational Snapshot in Container

```bash
docker compose run rwlv-runtime python3 -m skills.asana.actions.generate_current_priorities
```

## Send Priority Digest in Container

```bash
docker compose run rwlv-runtime python3 -m scripts.send_priority_digest
```

## Notes

- The repository is mounted into `/app` so local edits are reflected immediately.
- `.env` is loaded automatically via `docker-compose.yml`.
- The container is interactive (`stdin_open` + `tty`) for manual operational execution.
- This phase is runtime containerization only; no repository restructuring is introduced.

## Operational Runtime Management (Phase B)

Phase B adds lightweight runtime management without introducing orchestration platforms.

### Runtime validation

Before execution, runtime actions now validate:

- required configuration structure
- required environment variables
- generated and logging path writeability
- Asana and Telegram configuration presence

Validation failures are raised clearly for operators and logged as structured failures.

### Runtime status script

Use a deterministic runtime status check:

```bash
python3 -m scripts.runtime_status
```

Docker usage:

```bash
docker compose run rwlv-runtime python3 -m scripts.runtime_status
```

Expected output style:

```text
## Runtime Status

Docker Runtime: OK
Asana Config: OK
Telegram Config: OK
Generated Paths: OK
Structured Logging: OK
```

### Failure observability

Structured JSONL logging (`generated/logs/runtime.jsonl`) now includes explicit events for:

- startup validation failures
- runtime failures and exception states
- degraded/invalid operational states
- outbound delivery failures

### Operational lifecycle philosophy

Operational runtime management remains intentionally lightweight and client-safe:

- deterministic execution over autonomous behavior
- inspectable file-based artifacts over hidden systems
- explicit operational checks over implicit assumptions
- no Kubernetes, dashboards, distributed queues, or databases in this phase


## Persistent Operational Runtime (Phase C)

This phase upgrades the runtime from developer-invoked container commands to a persistent single-node operational service.

### Goals

- Long-running deterministic runtime lifecycle
- Container-owned scheduling (no host cron dependency)
- Automatic restart recovery (`restart: unless-stopped`)
- Durable generated/log/telemetry outputs via mounted `generated/`
- Explicit runtime uptime semantics in structured logs

### Start runtime service

```bash
docker compose up -d rwlv-runtime
```

### Follow runtime logs

```bash
docker compose logs -f rwlv-runtime
```

### Stop runtime service

```bash
docker compose stop rwlv-runtime
```

### Runtime semantics

The runtime emits structured lifecycle semantics to `generated/logs/runtime.jsonl` including:

- `runtime_started`
- `scheduler_active`
- `runtime_heartbeat`
- `scheduled_execution_triggered`

### Operational philosophy

This remains intentionally simple infrastructure:

- single-node
- containerized
- deterministic
- operationally inspectable

It intentionally excludes Kubernetes, distributed queues, cloud schedulers, and database-backed orchestration in this phase.
