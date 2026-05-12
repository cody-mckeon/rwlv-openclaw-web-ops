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
