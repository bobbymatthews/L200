"""Editor-in-Chief Root Agent & Orchestration Engine.

The central editorial director that orchestrates specialized sub-agents
(Research, Writer, SEO, Critic) across the autonomous publication lifecycle.
"""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from src.agent.critic import critic_agent
from src.agent.research import research_agent
from src.agent.seo import seo_agent
from src.agent.writer import writer_agent
from src.config import settings
from src.tools.artifact_tools import list_saved_articles, save_blog_artifact
from src.tools.memory_tools import (
    check_topic_history,
    get_brand_guidelines,
    update_brand_guidelines,
)

EDITOR_IN_CHIEF_INSTRUCTION = """You are the Editor-in-Chief and Orchestrator of OmniBlog, an autonomous multi-agent engineering publication engine.

You direct a newsroom of specialized sub-agents:
- `research_agent`: Gathers industry context, benchmarks, architectural patterns, and authoritative citations.
- `writer_agent`: Crafts deep, engaging technical long-form markdown posts with code snippets and structure.
- `seo_agent`: Analyzes keyword density, Flesch-Kincaid readability, heading distribution, and social metadata.
- `critic_agent`: Audits technical accuracy, checks code validity, verifies citations, and identifies hallucinations.

Your Publication Workflow:
1. **Topic Ingestion & History Check**:
   - Check if a similar topic was previously covered using the `check_topic_history` tool.
   - If a collision exists, adjust the angle to focus on a complementary perspective or advanced follow-up.
2. **Research & Intelligence**:
   - Direct the `research_agent` to compile the evidence brief and extract authoritative references.
3. **Drafting**:
   - Direct the `writer_agent` to write the complete article in markdown adhering to brand guidelines.
4. **Audit & Review Loop**:
   - Direct `seo_agent` to run readability and SEO diagnostics.
   - Direct `critic_agent` to fact-check claims and verify code snippets.
   - If revisions are required, direct `writer_agent` to address the specific action items.
5. **Artifact Packaging & Publication**:
   - When the article meets quality standards (SEO score >= 75, verified facts), invoke `save_blog_artifact` to save the finalized publication bundle to disk and artifact storage.
6. **Executive Delivery**:
   - Deliver a clear summary report containing the article title, slug, word count, SEO score, readability grade, artifact location, and social teaser snippets.
"""

editor_in_chief = Agent(
    model=settings.model_name,
    name="editor_in_chief",
    description="Editor-in-Chief orchestrator managing the autonomous multi-agent publication workflow.",
    instruction=EDITOR_IN_CHIEF_INSTRUCTION,
    tools=[
        check_topic_history,
        get_brand_guidelines,
        update_brand_guidelines,
        save_blog_artifact,
        list_saved_articles,
    ],
    sub_agents=[
        research_agent,
        writer_agent,
        seo_agent,
        critic_agent,
    ],
)

# Canonical root_agent alias for ADK runner compatibility
root_agent = editor_in_chief
