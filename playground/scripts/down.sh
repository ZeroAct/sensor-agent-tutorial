#!/usr/bin/env bash
# Stop the classroom stack. Data in the Open WebUI volume is kept.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "docker compose plugin is required"
  exit 1
fi

"${COMPOSE[@]}" down
echo "Stack stopped. Run ./scripts/up.sh to start again."
echo "To also delete Open WebUI local data: docker compose down -v"
