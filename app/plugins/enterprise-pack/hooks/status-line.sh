#!/bin/bash
# status-line.sh — Optional enterprise status line module.
# Not installed by default; intended for opt-in plugin-pack adoption.

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'no-git')"
PENDING=$(git status --short 2>/dev/null | wc -l | xargs || echo 0)
echo "status-line: branch=${BRANCH} pending_changes=${PENDING}"

