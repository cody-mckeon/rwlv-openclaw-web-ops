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
