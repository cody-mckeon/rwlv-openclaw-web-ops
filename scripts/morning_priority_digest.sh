#!/bin/bash

set -e

cd /Users/cody.mckeon/.openclaw/workspace

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

python3 -m skills.asana.actions.generate_current_priorities

python3 scripts/send_priority_digest.py

echo "Last morning priority digest run: $(date)" > HEARTBEAT.morning_priority_digest.md