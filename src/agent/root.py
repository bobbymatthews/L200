"""Editor-in-Chief Root Agent & Orchestration Engine.

The central editorial director that orchestrates specialized sub-agents
(Research, Writer, SEO, Critic) across the autonomous publication lifecycle,
with strategic model routing, context bloat compaction, and human-in-the-loop gates.
"""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent
from google.adk.workflow._retry_config import RetryConfig

from src.agent.critic import critic_agent
from src.agent.research import research_agent
from src.agent.seo import seo_agent
from src.agent.writer import writer_agent
from src.config import settings
from src.memory.compaction import compact_session_history
from src.tools.approval_tools import (
    confirm_publication_approval,
    request_publication_approval,
)
from src.tools.artifact_tools import list_saved_articles, save_blog_artifact
from src.tools.memory_tools import (
    check_topic_history,
    get_brand_guidelines,
    update_brand_guidelines,
)

EDITOR_IN_CHIEF_INSTRUCTION = """You are the Editor-in-Chief and Orchestrator of OmniBlog, an autonomous multi-agent engineering publication engine.

You direct a newsroom of specialized sub-agents with strategic model routing:
- `research_agent` (Fast Flash tier): Gathers industry context, benchmarks, architectural patterns, and authoritative citations.
- `writer_agent` (Pro Reasoning tier): Crafts deep, engaging technical long-form markdown posts with code snippets and structure.
- `seo_agent` (Fast Flash tier): Analyzes keyword density, Flesch-Kincaid readability, heading distribution, and social metadata.
- `critic_agent` (Pro Reasoning tier): Audits technical accuracy, checks code validity, verifies citations, and identifies hallucinations.

Your Publication Workflow:
1. **Topic Ingestion & History Check**:
   - Check if a similar topic was previously covered using the `check_topic_history` tool.
   - If a collision exists, adjust the angle to focus on a complementary perspective or advanced follow-up.
2. **Research & Intelligence**:
   - Direct the `research_agent` to compile the evidence brief and extract authoritative references.
3. **Drafting**:
   - Direct the `writer_agent` to write the complete article in markdown adhering to brand guidelines.
4. **Context & Token Bloat Compaction**:
   - If session history or intermediate scrape data becomes large, trigger `compact_session_history` to maintain optimal context token budget.
5. **Audit & Review Loop**:
   - Direct `seo_agent` to run readability and SEO diagnostics.
   - Direct `critic_agent` to fact-check claims and verify code snippets.
   - If revisions are required, direct `writer_agent` to address the specific action items.
6. **Human-in-the-Loop Confirmation Gate**:
   - Once algorithmic criteria are met, trigger `request_publication_approval` to create a publication ticket awaiting explicit human editor confirmation.
   - If human confirmation is provided via `confirm_publication_approval`, proceed to final artifact packaging.
7. **Artifact Packaging & Publication**:
   - When verified and approved, invoke `save_blog_artifact` to save the finalized publication bundle to disk and artifact storage.
8. **Executive Delivery**:
   - Deliver a clear summary report containing the article title, slug, word count, SEO score, readability grade, approval status, artifact location, and social teaser snippets.
"""

orchestrator_retry_config = RetryConfig(
    max_attempts=settings.model_max_retries,
    initial_delay=settings.model_retry_delay,
    max_delay=settings.model_max_delay,
    backoff_factor=2.0,
    jitter=1.0,
)

editor_in_chief = Agent(
    model=settings.orchestrator_model,
    name="editor_in_chief",
    description="Editor-in-Chief orchestrator managing the autonomous multi-agent publication workflow.",
    instruction=EDITOR_IN_CHIEF_INSTRUCTION,
    tools=[
        check_topic_history,
        get_brand_guidelines,
        update_brand_guidelines,
        compact_session_history,
        request_publication_approval,
        confirm_publication_approval,
        save_blog_artifact,
        list_saved_articles,
    ],
    sub_agents=[
        research_agent,
        writer_agent,
        seo_agent,
        critic_agent,
    ],
    retry_config=orchestrator_retry_config,
)

# Canonical root_agent alias for ADK runner compatibility
root_agent = editor_in_chief
