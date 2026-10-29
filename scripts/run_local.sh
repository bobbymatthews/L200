#!/usr/bin/env bash
# ==============================================================================
# OmniBlog: Local Development Launch Script
# ==============================================================================
set -euo pipefail

MODE="${1:-api}"

case "${MODE}" in
  "api")
    echo "Starting OmniBlog FastAPI REST API Server on port 8000..."
    uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
    ;;
  "web")
    echo "Starting ADK Developer Web UI..."
    adk web .
    ;;
  "run")
    echo "Starting ADK Interactive Terminal Session..."
    adk run .
    ;;
  "cli")
    shift || true
    python -m src.cli "$@"
    ;;
  *)
    echo "Usage: $0 {api|web|run|cli [args]}"
    exit 1
    ;;
esac
