#!/bin/bash

set -e

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

python3 -m skills.asana.actions.generate_current_priorities

echo "Last priority refresh: $(date)" > HEARTBEAT.priority_governor.md
