"""Human-in-the-Loop (HITL) Publication Approval Tools.

Implements an explicit human-in-the-loop confirmation gate requiring human sign-off
before articles are finalized, indexed into the public catalog, or pushed to production.
"""

from __future__ import annotations

import secrets
from typing import Any

from pydantic import BaseModel, Field

from src.observability.logging import logger
from src.observability.tracing import trace_span

try:
    from google.adk.tools.tool_context import ToolContext
except ImportError:
    ToolContext = Any  # type: ignore


# In-memory approval ticket store for active HITL sessions
PENDING_APPROVALS: dict[str, dict[str, Any]] = {}


class ApprovalTicket(BaseModel):
    """Human-in-the-loop approval ticket for a pending publication."""

    article_id: str
    title: str
    slug: str
    approval_token: str
    seo_score: float
    factual_score: float
    status: str = Field(default="pending_human_approval")
    message: str


@trace_span("tool.request_publication_approval")
def request_publication_approval(
    article_id: str,
    title: str,
    slug: str,
    seo_score: float,
    factual_score: float,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Generates a Human-in-the-Loop approval gate ticket requiring explicit human confirmation.

    Args:
        article_id: Identifier of the generated article.
        title: Title of the article.
        slug: Canonical URL slug.
        seo_score: The calculated SEO audit score.
        factual_score: The calculated factual accuracy score.
        tool_context: ADK execution context.

    Returns:
        Structured ApprovalTicket containing approval token and review instructions.
    """
    token = f"appr-{secrets.token_hex(6)}"
    ticket = {
        "article_id": article_id,
        "title": title,
        "slug": slug,
        "approval_token": token,
        "seo_score": seo_score,
        "factual_score": factual_score,
        "status": "pending_human_approval",
        "message": (
            f"Draft '{title}' has satisfied all algorithmic SEO ({seo_score}/100) and factual ({factual_score}/100) gates. "
            f"Human-in-the-loop confirmation is required before official release. "
            f"Approve with token: {token}"
        ),
    }

    PENDING_APPROVALS[article_id] = ticket
    PENDING_APPROVALS[token] = ticket

    logger.info("Created HITL publication approval ticket for article '%s' (token: %s)", article_id, token)

    if tool_context and hasattr(tool_context, "state") and tool_context.state is not None:
        try:
            tool_context.state["pending_approval"] = ticket
        except Exception:
            pass

    return ticket


@trace_span("tool.confirm_publication_approval")
def confirm_publication_approval(
    approval_token_or_id: str,
    approved: bool = True,
    reviewer_notes: str | None = None,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Processes human confirmation to publish or reject an article draft.

    Args:
        approval_token_or_id: The approval token or article ID to confirm.
        approved: True to approve and publish, False to request revisions.
        reviewer_notes: Optional feedback from human reviewer.
        tool_context: ADK execution context.

    Returns:
        Status result of the human approval decision.
    """
    ticket = PENDING_APPROVALS.get(approval_token_or_id)
    if not ticket:
        return {
            "status": "error",
            "message": f"No pending approval ticket found matching '{approval_token_or_id}'.",
        }

    article_id = ticket["article_id"]
    if approved:
        ticket["status"] = "approved"
        logger.info("Human reviewer approved article '%s' for publication.", article_id)
        return {
            "status": "approved",
            "article_id": article_id,
            "title": ticket["title"],
            "slug": ticket["slug"],
            "message": f"Article '{ticket['title']}' officially approved by human reviewer. Safe to publish.",
            "reviewer_notes": reviewer_notes or "Approved without modification.",
        }
    else:
        ticket["status"] = "rejected_needs_revision"
        logger.warning("Human reviewer rejected article '%s': %s", article_id, reviewer_notes)
        return {
            "status": "rejected",
            "article_id": article_id,
            "title": ticket["title"],
            "message": "Human reviewer requested editorial revisions before publication.",
            "reviewer_notes": reviewer_notes or "Please revise draft according to standards.",
        }
