#!/usr/bin/env bash
# Start the classroom stack. Safe to re-run.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created playground/.env from .env.example"
  echo "Put your free-tier OPENAI_API_KEY in playground/.env if you want the chatbot."
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required. In GitHub Codespaces wait for the devcontainer, or install Docker Desktop."
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "docker compose plugin is required"
  exit 1
fi

"${COMPOSE[@]}" --env-file .env up --build -d
"${COMPOSE[@]}" ps
echo
echo "Open WebUI:  http://localhost:8080"
echo "MCP health:  http://localhost:8000/health"
echo "MCP demo:    http://localhost:8000/demo/sensors"
echo "MCP URL:     http://mcp-server:8000/mcp  (from Open WebUI container)"
echo "             http://localhost:8000/mcp   (from the Codespaces/host browser)"
echo
echo "Codespaces: open the Ports tab → 8080 → Open in Browser"
