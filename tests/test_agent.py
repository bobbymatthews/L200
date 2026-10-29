"""Unit tests for ADK Agent definitions and newsroom orchestration."""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from src.agent.critic import critic_agent
from src.agent.research import research_agent
from src.agent.root import editor_in_chief, root_agent
from src.agent.seo import seo_agent
from src.agent.writer import writer_agent


def test_agent_definitions_and_roles():
    """Verify all specialized agents are correctly instantiated with tools and instructions."""
    agents = [
        (research_agent, "research_agent", 2),
        (writer_agent, "writer_agent", 1),
        (seo_agent, "seo_agent", 2),
        (critic_agent, "critic_agent", 2),
        (editor_in_chief, "editor_in_chief", 5),
    ]

    for agent, expected_name, min_tools in agents:
        assert isinstance(agent, Agent)
        assert agent.name == expected_name
        assert len(agent.instruction) > 50
        assert len(agent.tools) >= min_tools


def test_root_orchestrator_subagents():
    """Verify editor_in_chief orchestrates all four sub-agents."""
    sub_names = [sub.name for sub in editor_in_chief.sub_agents]
    expected_subs = ["research_agent", "writer_agent", "seo_agent", "critic_agent"]

    for expected in expected_subs:
        assert expected in sub_names

    # Verify root_agent alias
    assert root_agent is editor_in_chief
