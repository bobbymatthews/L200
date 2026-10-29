"""OmniBlog Canonical ADK Agent Entrypoint.

This file exposes `root_agent` for Google ADK runtime discovery:
  - CLI execution: `adk run .`
  - Developer Web UI: `adk web .`
  - FastAPI Server: `adk api_server .`
  - Vertex AI Agent Engine Deployment: `adk deploy agent_engine .`
  - Cloud Run Deployment: `adk deploy cloud_run .`
"""

from __future__ import annotations

from dotenv import load_dotenv

from src.agent.root import editor_in_chief, root_agent

# Load local environment configuration
load_dotenv()

__all__ = ["editor_in_chief", "root_agent"]
