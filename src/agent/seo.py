"""SEO and Growth Specialist Agent.

Specialized sub-agent dedicated to search engine optimization, readability grading,
heading hierarchy validation, and social distribution metadata.
"""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent

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

seo_agent = Agent(
    model=settings.model_name,
    name="seo_agent",
    description="Audits article readability, keyword density, heading structures, and generates SEO metadata.",
    instruction=SEO_INSTRUCTION,
    tools=[analyze_seo_and_readability, generate_meta_and_slug],
)
