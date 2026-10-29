"""Editorial Reviewer and Fact-Checking Critic Agent.

Specialized sub-agent dedicated to technical accuracy auditing, hallucination
detection, citation validation, and structured revision loops.
Routed to high-reasoning model (Gemini Pro tier) for rigorous contradiction detection.
"""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent
from google.adk.workflow._retry_config import RetryConfig

from src.config import settings
from src.tools.memory_tools import get_brand_guidelines
from src.tools.verification_tools import fact_check_and_verify

CRITIC_INSTRUCTION = """You are the Senior Editorial Reviewer & Technical Fact-Checker.

Your responsibilities:
1. Thoroughly review drafts using the `fact_check_and_verify` tool to inspect technical accuracy, code snippet validity, and citation coverage.
2. Check that the draft complies with the active brand rules via `get_brand_guidelines`.
3. Detect and flag:
   - Unsupported or hyperbolic claims (e.g. '100% guarantee', '1000x faster' without context).
   - Broken or incomplete code snippets with unaddressed TODOs or placeholder tags.
   - Missing citations or unverified assertions.
   - Tone deviations from the authoritative, pragmatic brand voice.
4. Issue a clear verdict:
   - If the draft satisfies technical rigor and scores >= 75: Approve the draft for final artifact packaging.
   - If the draft fails or has critical flaws: Provide bulleted, actionable revision instructions for the writer agent.
"""

critic_retry_config = RetryConfig(
    max_attempts=settings.model_max_retries,
    initial_delay=settings.model_retry_delay,
    max_delay=settings.model_max_delay,
    backoff_factor=2.0,
    jitter=1.0,
)

critic_agent = Agent(
    model=settings.critic_model,
    name="critic_agent",
    description="Audits technical claims, detects hallucinations, verifies code validity, and provides editorial revision feedback.",
    instruction=CRITIC_INSTRUCTION,
    tools=[fact_check_and_verify, get_brand_guidelines],
    retry_config=critic_retry_config,
)
