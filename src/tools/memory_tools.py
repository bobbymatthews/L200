"""Brand Memory and Editorial Standards Tools.

Provides agents with access to long-term memory regarding publication style,
editorial tone, author profiles, and historical topic coverage.
"""

from __future__ import annotations

from typing import Any

from src.memory.store import BrandGuidelines, brand_memory
from src.observability.logging import logger
from src.observability.tracing import trace_span

try:
    from google.adk.tools.tool_context import ToolContext
except ImportError:
    ToolContext = Any  # type: ignore


@trace_span("tool.get_brand_guidelines")
def get_brand_guidelines(
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Retrieves active brand voice, tone, audience, and editorial formatting rules.

    Args:
        tool_context: ADK execution context.

    Returns:
        Dictionary of active brand guidelines.
    """
    guidelines = brand_memory.get_guidelines()
    logger.info("Retrieved active brand guidelines for '%s'", guidelines.brand_name)

    if tool_context and hasattr(tool_context, "state") and tool_context.state is not None:
        try:
            tool_context.state["brand_guidelines"] = guidelines.model_dump()
        except Exception:
            pass

    return {
        "status": "success",
        "guidelines": guidelines.model_dump(),
    }


@trace_span("tool.update_brand_guidelines")
def update_brand_guidelines(
    brand_name: str | None = None,
    tone: str | None = None,
    target_audience: str | None = None,
    style_rules: list[str] | None = None,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Updates the brand editorial rules and style guidelines in long-term memory.

    Args:
        brand_name: New publication or brand name.
        tone: Updated tone of voice.
        target_audience: Updated target audience.
        style_rules: List of style rules to set or append.
        tool_context: ADK execution context.

    Returns:
        Status and the newly updated guidelines.
    """
    current = brand_memory.get_guidelines()

    updated = BrandGuidelines(
        brand_name=brand_name or current.brand_name,
        tone=tone or current.tone,
        target_audience=target_audience or current.target_audience,
        perspective=current.perspective,
        style_rules=style_rules or current.style_rules,
        key_themes=current.key_themes,
    )

    brand_memory.save_guidelines(updated)
    logger.info("Updated brand guidelines for '%s'", updated.brand_name)

    return {
        "status": "updated",
        "guidelines": updated.model_dump(),
    }


@trace_span("tool.check_topic_history")
def check_topic_history(
    topic: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Checks long-term publication memory to detect if a topic or similar theme has already been covered.

    Args:
        topic: The topic title or keyword to verify.
        tool_context: ADK execution context.

    Returns:
        Dictionary indicating whether a collision was found and details of past articles.
    """
    collision = brand_memory.check_similar_topic(topic)
    if collision:
        logger.warning("Found topic collision with article: %s", collision.title)
        return {
            "is_duplicate": True,
            "message": f"A similar topic has already been published: '{collision.title}' on {collision.published_at}",
            "existing_article": collision.model_dump(),
            "recommendation": "Differentiate the angle, focus on a complementary subtopic, or provide an advanced follow-up.",
        }

    return {
        "is_duplicate": False,
        "message": f"No previous articles directly match '{topic}'. Safe to proceed with content creation.",
    }
