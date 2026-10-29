"""Unit tests for Human-in-the-Loop publication approvals and context compaction."""

from __future__ import annotations

from src.memory.compaction import ContextCompactor, compact_session_history
from src.tools.approval_tools import (
    confirm_publication_approval,
    request_publication_approval,
)


def test_context_compactor_pruning():
    """Verify context compactor prunes bloated state keys."""
    compactor = ContextCompactor(token_budget=1000)
    bloated_state = {
        "raw_scrape_data": "x" * 5000,
        "clean_summary": "Short clean summary",
        "nested_items": list(range(100)),
    }
    pruned = compactor.prune_session_state(bloated_state, max_text_chars=500)

    assert len(pruned["raw_scrape_data"]) < 1000
    assert "[Pruned" in pruned["raw_scrape_data"]
    assert pruned["clean_summary"] == "Short clean summary"
    assert len(pruned["nested_items"]) == 20


def test_context_compactor_history():
    """Verify history compaction compresses older turns while preserving recent ones."""
    compactor = ContextCompactor(turn_budget=4)
    long_history = [
        {"role": "user", "content": "Turn 1: Research topic A in depth"},
        {"role": "assistant", "content": "Turn 2: Here is the research brief for A"},
        {"role": "user", "content": "Turn 3: Write draft for topic A"},
        {"role": "assistant", "content": "Turn 4: Here is draft A"},
        {"role": "user", "content": "Turn 5: Now optimize SEO for A"},
        {"role": "assistant", "content": "Turn 6: Here is SEO report"},
    ]
    compacted = compactor.compact_history(long_history, max_turns=4)

    assert len(compacted) <= 4
    assert any("[Compressed Historical Context Summary]" in m["content"] for m in compacted)
    # Most recent turn preserved
    assert compacted[-1]["content"] == "Turn 6: Here is SEO report"


def test_compact_session_history_tool():
    """Verify compact_session_history tool executes without error."""
    res = compact_session_history(max_tokens=2000)
    assert "summary" in res
    assert res["estimated_compacted_tokens"] <= res["estimated_original_tokens"]


def test_hitl_approval_lifecycle():
    """Verify Human-in-the-Loop ticket creation, confirmation, and rejection."""
    # 1. Request approval ticket
    ticket = request_publication_approval(
        article_id="art-test-hitl-01",
        title="Production Microservices with GKE Autopilot",
        slug="production-microservices-with-gke-autopilot",
        seo_score=88.5,
        factual_score=92.0,
    )
    assert ticket["status"] == "pending_human_approval"
    token = ticket["approval_token"]
    assert token.startswith("appr-")

    # 2. Confirm approval
    decision = confirm_publication_approval(token, approved=True, reviewer_notes="LGTM!")
    assert decision["status"] == "approved"
    assert "officially approved" in decision["message"]

    # 3. Test rejection flow with new ticket
    ticket2 = request_publication_approval(
        article_id="art-test-hitl-02",
        title="Unverified Cloud Claims",
        slug="unverified-cloud-claims",
        seo_score=65.0,
        factual_score=50.0,
    )
    rejection = confirm_publication_approval(ticket2["approval_token"], approved=False, reviewer_notes="Fix code")
    assert rejection["status"] == "rejected"
    assert "requested editorial revisions" in rejection["message"]
