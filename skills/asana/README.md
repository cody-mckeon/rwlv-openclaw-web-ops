# Asana Skill

## Purpose

This skill provides read-only Asana context for OpenClaw agents.

The first use case is helping the Priority Governor Agent compare incoming requests against current Asana priorities.

## Current Mode

MVP mode is read-only.

The skill can:

- Read tasks from a project
- Summarize project tasks
- Surface open tasks, due dates, assignees, sections, and custom fields
- Normalize Asana section names and custom-field aliases into Priority Governor buckets
- Emit optional debug diagnostics for section/custom-field parsing

The skill cannot:

- Create tasks
- Update tasks
- Delete tasks
- Comment on tasks
- Move tasks
- Assign tasks
- Change due dates

## Environment Variables

Required:

```bash
export ASANA_ACCESS_TOKEN="your_token_here"
export ASANA_MODE="read_only"
export ASANA_TEST_PROJECT_GID="your_project_gid"
```

Optional observability controls:

```bash
# Include a Debug Diagnostics section in CURRENT_PRIORITIES.generated.md.
export PRIORITY_GOVERNOR_DEBUG=1

# Emit per-task normalized parsing/classification logs.
export PRIORITY_GOVERNOR_LOG_LEVEL=DEBUG
```

## Generate Current Priorities Snapshot

After exporting the required environment variables, run:

```bash
python3 -m skills.asana.actions.generate_current_priorities
```

The generated snapshot treats Asana sections as the primary workflow signal. The RWLV queue currently uses sections such as `Intake`, `Triage / Ready`, `In Progress`, `QA`, `Central / Ready to Launch`, `Done`, and `Canceled`; it does not require a standalone `Status` custom field for a task to be considered active.
