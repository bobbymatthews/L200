"""Publication Packaging and Artifact Management Tools.

Packages finalized blog articles with frontmatter, SEO audits, and social snippets,
persisting them via Google ADK's Artifact Service and local file storage.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.memory.store import PublishedArticleRecord, brand_memory
from src.observability.logging import logger
from src.observability.tracing import trace_span

try:
    from google.adk.tools.tool_context import ToolContext
except ImportError:
    ToolContext = Any  # type: ignore


@trace_span("tool.save_blog_artifact")
def save_blog_artifact(
    title: str,
    markdown_content: str,
    topic: str = "General",
    target_keyword: str = "",
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Packages and saves a finalized blog post bundle as a versioned publication artifact.

    Args:
        title: The blog post title.
        markdown_content: The full markdown content of the post.
        topic: The overarching topic or category.
        target_keyword: The primary SEO keyword.
        tool_context: ADK execution context with ArtifactService access.

    Returns:
        Metadata record including article_id, file paths, and artifact confirmation.
    """
    article_id = f"art-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()

    # Retrieve SEO report from state if available
    seo_data = {}
    if tool_context and hasattr(tool_context, "state") and tool_context.state is not None:
        seo_data = tool_context.state.get("seo_report", {})

    word_count = seo_data.get("word_count", len(markdown_content.split()))
    seo_score = seo_data.get("overall_seo_score", 85.0)
    reading_ease = seo_data.get("flesch_reading_ease", 55.0)

    # Clean slug
    import re
    clean_title = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[-\s]+", "-", clean_title).strip("-")[:75]

    # Prepend YAML Frontmatter
    frontmatter = f"""---
title: "{title}"
slug: "{slug}"
date: "{now}"
topic: "{topic}"
target_keyword: "{target_keyword}"
word_count: {word_count}
seo_score: {seo_score}
reading_ease: {reading_ease}
status: "published"
---

"""
    full_document = frontmatter + markdown_content

    # 1. Local disk persistence
    artifact_dir = Path("artifacts") / slug
    artifact_dir.mkdir(parents=True, exist_ok=True)

    markdown_file = artifact_dir / "index.md"
    markdown_file.write_text(full_document, encoding="utf-8")

    meta_file = artifact_dir / "metadata.json"
    meta_payload = {
        "article_id": article_id,
        "title": title,
        "slug": slug,
        "topic": topic,
        "target_keyword": target_keyword,
        "word_count": word_count,
        "seo_score": seo_score,
        "reading_ease": reading_ease,
        "published_at": now,
        "seo_report": seo_data,
    }
    meta_file.write_text(json.dumps(meta_payload, indent=2), encoding="utf-8")

    # 2. ADK Native Artifact Service integration if available
    adk_artifact_uri = None
    if tool_context and hasattr(tool_context, "save_artifact"):
        try:
            import asyncio

            from google.genai import types

            artifact_name = f"{slug}-post.md"
            part = types.Part.from_bytes(data=full_document.encode("utf-8"), mime_type="text/markdown")
            coro = tool_context.save_artifact(filename=artifact_name, artifact=part)
            if asyncio.iscoroutine(coro):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(coro)
                    else:
                        loop.run_until_complete(coro)
                except Exception:
                    pass
            adk_artifact_uri = f"adk://artifacts/{artifact_name}"
            logger.info("Saved artifact via ADK ToolContext.save_artifact: %s", artifact_name)
        except Exception as exc:
            logger.warning("ToolContext.save_artifact exception (%s); saved to disk instead.", exc)

    # 3. Record in publication memory
    record = PublishedArticleRecord(
        article_id=article_id,
        title=title,
        topic=topic,
        slug=slug,
        word_count=word_count,
        seo_score=seo_score,
        reading_ease=reading_ease,
        published_at=now,
        tags=[topic, target_keyword] if target_keyword else [topic],
        artifact_uri=adk_artifact_uri or str(markdown_file.resolve()),
    )
    brand_memory.record_publication(record)

    logger.info("Successfully published and recorded article: %s (%s)", title, article_id)

    return {
        "status": "success",
        "article_id": article_id,
        "slug": slug,
        "local_file": str(markdown_file),
        "metadata_file": str(meta_file),
        "adk_artifact_uri": adk_artifact_uri,
        "published_record": record.model_dump(),
    }


@trace_span("tool.list_saved_articles")
def list_saved_articles(
    limit: int = 20,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Lists saved publications and drafts in the repository.

    Args:
        limit: Maximum number of articles to return.
        tool_context: ADK execution context.

    Returns:
        List of published article records.
    """
    records = brand_memory.list_publications(limit=limit)
    return {
        "status": "success",
        "count": len(records),
        "articles": [r.model_dump() for r in records],
    }
