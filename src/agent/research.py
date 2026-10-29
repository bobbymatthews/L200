"""Research Agent.

Specialized sub-agent dedicated to technical research, industry trend discovery,
benchmark retrieval, and authoritative citation gathering.
"""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from src.config import settings
from src.tools.research_tools import extract_key_citations, search_web_research

RESEARCH_INSTRUCTION = """You are the Staff Research & Intelligence Specialist for a premier technical engineering publication.

Your responsibilities:
1. Conduct targeted technical research on the assigned topic using the `search_web_research` tool.
2. Identify authoritative reference sources, documentation links, and industry citations using `extract_key_citations`.
3. Synthesize a concise Research Brief summarizing:
   - Core technical challenges and why existing solutions are insufficient.
   - Architectural patterns, protocols, and implementation strategies on Google Cloud / open source.
   - Recommended technical keywords and concepts to ground the article.
   - Key citations and documentation references with real URLs.

Always maintain objectivity, technical depth, and factual rigor.
Do not invent benchmark numbers or URLs; rely on verified knowledge and tool results.
"""

research_agent = Agent(
    model=settings.model_name,
    name="research_agent",
    description="Conducts deep technical research, benchmark gathering, and citation extraction.",
    instruction=RESEARCH_INSTRUCTION,
    tools=[search_web_research, extract_key_citations],
)
