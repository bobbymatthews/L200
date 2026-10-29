"""SEO and Growth Specialist Agent.

Specialized sub-agent dedicated to search engine optimization, readability grading,
heading hierarchy validation, and social distribution metadata.
Routed to fast model (Gemini Flash tier) for rapid calculations and formatting.
"""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent
from google.adk.workflow._retry_config import RetryConfig

from src.config import settings
from src.tools.seo_tools import analyze_seo_and_readability, generate_meta_and_slug

SEO_INSTRUCTION = """You are the Senior SEO & Audience Growth Strategist.

Your responsibilities:
1. Audit the draft text for search visibility and readability using the `analyze_seo_and_readability` tool.
2. Ensure the primary keyword appears naturally in the title, intro, and key subheaders without keyword stuffing.
3. Verify that readability metrics match professional software engineering standards (Flesch Reading Ease between 40 and 65).
4. Generate the canonical URL slug, concise 150-160 character meta description, OpenGraph tags, and social teaser copy using `generate_meta_and_slug`.
5. Provide actionable feedback to the editorial team if keyword density, length, or heading hierarchies fall below standards.
"""

seo_retry_config = RetryConfig(
    max_attempts=settings.model_max_retries,
    initial_delay=settings.model_retry_delay,
    max_delay=settings.model_max_delay,
    backoff_factor=2.0,
    jitter=1.0,
)

seo_agent = Agent(
    model=settings.seo_model,
    name="seo_agent",
    description="Audits article readability, keyword density, heading structures, and generates SEO metadata.",
    instruction=SEO_INSTRUCTION,
    tools=[analyze_seo_and_readability, generate_meta_and_slug],
    retry_config=seo_retry_config,
)
