#!/bin/bash

set -e

cd /Users/cody.mckeon/.openclaw/workspace

export ASANA_MODE="read_only"
export ASANA_TEST_PROJECT_GID="1213424083073059"

python3 -m skills.asana.actions.generate_current_priorities