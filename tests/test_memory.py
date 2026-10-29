"""Unit tests for Brand Memory and publication history persistence."""

from __future__ import annotations

from src.memory.store import PublishedArticleRecord
from src.tools.memory_tools import (
    check_topic_history,
    get_brand_guidelines,
    update_brand_guidelines,
)


def test_brand_memory_initialization(isolated_brand_memory):
    """Verify default brand guidelines are populated on initialization."""
    guidelines = isolated_brand_memory.get_guidelines()
    assert guidelines.brand_name == "CloudNative Insights"
    assert len(guidelines.style_rules) > 0
    assert len(guidelines.key_themes) > 0


def test_update_brand_guidelines(isolated_brand_memory):
    """Verify updating brand tone and style rules persists into database."""
    res = update_brand_guidelines(
        brand_name="Vertex Developers",
        tone="Incisive and pragmatic.",
        style_rules=["Always provide benchmark numbers.", "Include Terraform examples."],
    )
    assert res["status"] == "updated"
    assert res["guidelines"]["brand_name"] == "Vertex Developers"
    assert res["guidelines"]["tone"] == "Incisive and pragmatic."

    # Verify retrieval reflects updates
    retrieved = get_brand_guidelines()
    assert retrieved["guidelines"]["brand_name"] == "Vertex Developers"
    assert len(retrieved["guidelines"]["style_rules"]) == 2


def test_check_topic_history_collision(isolated_brand_memory):
    """Verify topic collision detection prevents publishing duplicate content."""
    # First check: topic should be clean
    check1 = check_topic_history("Event-Driven Architecture on Cloud Run")
    assert check1["is_duplicate"] is False

    # Record publication
    rec = PublishedArticleRecord(
        article_id="art-test-1",
        title="Event-Driven Architecture on Cloud Run",
        topic="Event-Driven Architecture",
        slug="event-driven-architecture-on-cloud-run",
        word_count=1200,
        seo_score=92.0,
        reading_ease=58.0,
        published_at="2026-10-29T00:00:00Z",
    )
    isolated_brand_memory.record_publication(rec)

    # Second check: collision should be detected
    check2 = check_topic_history("Event-Driven Architecture on Cloud Run")
    assert check2["is_duplicate"] is True
    assert "already been published" in check2["message"]
    assert "recommendation" in check2
