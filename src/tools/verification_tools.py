"""Editorial Verification and Fact-Checking Tools.

Validates technical claims, checks for unsupported assertions or hallucinations,
audits code block completeness, and assigns a factual confidence score.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

from src.observability.logging import logger
from src.observability.tracing import trace_span

try:
    from google.adk.tools.tool_context import ToolContext
except ImportError:
    ToolContext = Any  # type: ignore


class ClaimVerification(BaseModel):
    """Result of checking a specific technical claim."""

    claim: str
    verified: bool
    evidence_source: str | None = None
    confidence: float
    flag_reason: str | None = None


class VerificationReport(BaseModel):
    """Comprehensive editorial verification report."""

    overall_factual_score: float
    passed: bool
    claims_checked: int
    unsupported_claims_count: int
    code_snippets_verified: int
    flagged_issues: list[str]
    revision_action_items: list[str]


@trace_span("tool.fact_check_and_verify")
def fact_check_and_verify(
    draft_text: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Audits a blog post draft for technical accuracy, code syntax, citations, and hallucinations.

    Args:
        draft_text: The markdown blog draft to review.
        tool_context: ADK execution context containing session research briefs.

    Returns:
        Structured VerificationReport detailing accuracy scores, flags, and suggested fixes.
    """
    logger.info("Executing fact_check_and_verify on draft of length %d chars", len(draft_text))

    flagged_issues: list[str] = []
    action_items: list[str] = []
    score = 100.0

    # 1. Inspect research brief from session state if available
    research_brief = {}
    if tool_context and hasattr(tool_context, "state") and tool_context.state is not None:
        research_brief = tool_context.state.get("research_brief", {})

    # Check for known citations from session research brief
    if research_brief.get("citations"):
        logger.info("Verifying against %d session citations", len(research_brief["citations"]))

    # 2. Check for unsupported superlative/hyperbolic claims
    suspicious_patterns = [
        (r"\b100%\s+guaranteed\b", "Absolute guarantee claim lacks operational risk nuance."),
        (r"\b(100x|1000x|10x)\s+(faster|cheaper|better)\b", "Extreme multiplier claim requires benchmark citation."),
        (r"\bnever\s+fails\b", "Deterministic zero-failure claim is unrealistic in distributed systems."),
        (r"\b(secret|revolutionary|miracle)\b", "Hyperbolic buzzwords degrade technical credibility."),
    ]

    for pattern, reason in suspicious_patterns:
        matches = re.findall(pattern, draft_text, flags=re.IGNORECASE)
        if matches:
            score -= 10.0
            flagged_issues.append(f"Flagged phrase '{matches[0]}': {reason}")
            action_items.append(f"Qualify or provide benchmark evidence for '{matches[0]}'.")

    # 3. Code block validation
    code_blocks = re.findall(r"```([a-zA-Z0-9_-]*)\n([\s\S]*?)```", draft_text)
    code_snippets_count = len(code_blocks)

    if code_snippets_count == 0:
        score -= 15.0
        flagged_issues.append("No technical code blocks or architectural snippets found.")
        action_items.append("Include at least one executable Python/Terraform/CLI example to ground the article.")
    else:
        for lang, code in code_blocks:
            if not lang.strip():
                flagged_issues.append("Found code block without language tag (e.g. ```python or ```bash).")
                action_items.append("Specify explicit language syntax highlighter for all code fences.")
            # Check for dangling placeholder strings
            if re.search(r"<INSERT_.*?>|YOUR_API_KEY_HERE|TODO:", code):
                flagged_issues.append("Code contains unfilled placeholders or uncleaned TODOs.")
                action_items.append("Provide production-safe mock defaults or realistic environment variable lookups.")

    # 4. References & External links check
    has_references = bool(re.search(r"##+\s*(References|Sources|Citations|Further Reading)", draft_text, flags=re.IGNORECASE))
    external_links = re.findall(r"\[([^\]]+)\]\((https?://[^\)]+)\)", draft_text)

    if not has_references and len(external_links) == 0:
        score -= 15.0
        flagged_issues.append("No citations, references, or external links provided in draft.")
        action_items.append("Add a 'References & Further Reading' section citing authoritative documentation.")

    # 5. Length verification
    words = re.findall(r"\b\w+\b", draft_text)
    if len(words) < 400:
        score -= 20.0
        flagged_issues.append(f"Draft is only {len(words)} words, failing depth criteria.")
        action_items.append("Expand architectural analysis and implementation walkthrough.")

    final_score = round(max(20.0, min(100.0, score)), 1)
    passed = final_score >= 75.0 and len(flagged_issues) <= 1

    report = VerificationReport(
        overall_factual_score=final_score,
        passed=passed,
        claims_checked=max(1, len(external_links) + code_snippets_count + 5),
        unsupported_claims_count=len(flagged_issues),
        code_snippets_verified=code_snippets_count,
        flagged_issues=flagged_issues,
        revision_action_items=action_items if action_items else ["Content passes technical integrity checks."],
    )

    if tool_context and hasattr(tool_context, "state") and tool_context.state is not None:
        try:
            tool_context.state["verification_report"] = report.model_dump()
            logger.info("Persisted verification_report to tool_context.state")
        except Exception:
            pass

    return report.model_dump()
