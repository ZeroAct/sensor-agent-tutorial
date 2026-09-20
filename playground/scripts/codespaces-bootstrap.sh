#!/usr/bin/env bash
# Codespaces / first-clone helper. Does not start the stack (a key is usually missing).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created playground/.env — add OPENAI_API_KEY before the chatbot portion."
else
  echo "playground/.env already exists; leaving it unchanged."
fi

echo
echo "Next:"
echo "  1. Edit playground/.env with a free-tier OpenAI-compatible key"
echo "  2. ./playground/scripts/up.sh"
echo "  3. Open port 8080 (Open WebUI)"
echo
echo "Student guide: docs/STUDENT.md"
