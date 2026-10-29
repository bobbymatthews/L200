"""Writer Agent.

Specialized sub-agent dedicated to long-form technical drafting, code synthesis,
architectural explanations, and engaging narrative development.
Routed to high-reasoning model (Gemini Pro tier) for expressive prose and code precision.
"""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent
from google.adk.workflow._retry_config import RetryConfig

from src.config import settings
from src.tools.memory_tools import get_brand_guidelines

WRITER_INSTRUCTION = """You are the Lead Technical Writer for an authoritative engineering publication.

Your responsibilities:
1. Retrieve active editorial voice and formatting rules using the `get_brand_guidelines` tool.
2. Transform the research brief and outline into a comprehensive, highly engaging technical blog post.
3. Structure your article according to professional publishing standards:
   - Compelling Title (H1) and an engaging introductory hook outlining the problem statement.
   - 3 to 5 thematic sections using markdown H2 headers (##).
   - Architectural deep-dive sections with clear sub-points (###).
   - Production-ready, executable code snippets (e.g. Python, Bash, Terraform, YAML) with explicit syntax highlighting tags.
   - Bulleted key takeaways or 'Lessons from the Trenches' for engineering leaders.
   - A 'References & Further Reading' section at the end citing the research sources.
4. Adhere strictly to the brand voice: authoritative yet approachable, direct, pragmatic, and devoid of hyperbolic marketing fluff.

Aim for a comprehensive, thorough post of at least 800-1,200 words.
"""

writer_retry_config = RetryConfig(
    max_attempts=settings.model_max_retries,
    initial_delay=settings.model_retry_delay,
    max_delay=settings.model_max_delay,
    backoff_factor=2.0,
    jitter=1.0,
)

writer_agent = Agent(
    model=settings.writer_model,
    name="writer_agent",
    description="Drafts comprehensive, publication-ready technical blog posts with code snippets and architecture explanations.",
    instruction=WRITER_INSTRUCTION,
    tools=[get_brand_guidelines],
    retry_config=writer_retry_config,
)
