# RWLV Runtime Docker Workflow

## Build runtime image

```bash
docker compose build
```

## Open runtime shell

```bash
docker compose run rwlv-runtime bash
```

## Run Asana tests

```bash
docker compose run rwlv-runtime python3 -m unittest discover -s skills/asana/tests -p 'test_*.py'
```

## Generate current priorities snapshot

```bash
docker compose run rwlv-runtime python3 -m skills.asana.actions.generate_current_priorities
```

## Send priority digest

```bash
docker compose run rwlv-runtime python3 -m scripts.send_priority_digest
```

## Artifact persistence

Generated runtime artifacts are written to:

- `generated/snapshots/`
- `generated/logs/`

Docker persists these through the `rwlv_generated` named volume mounted at `/app/generated`.
