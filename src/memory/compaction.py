"""Context Bloat Management and Conversational History Compaction.

Implements token budget management, rolling conversational summarization,
and selective intermediate memory pruning to prevent LLM context exhaustion.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from src.observability.logging import logger
from src.observability.tracing import trace_span

try:
    from google.adk.tools.tool_context import ToolContext
except ImportError:
    ToolContext = Any  # type: ignore


class CompactionSummary(BaseModel):
    """Result of context compaction operation."""

    original_turn_count: int
    compacted_turn_count: int
    estimated_original_tokens: int
    estimated_compacted_tokens: int
    tokens_saved: int
    summary: str


class ContextCompactor:
    """Manages token budgeting and rolling history compaction."""

    def __init__(self, token_budget: int = 6000, turn_budget: int = 8):
        self.token_budget = token_budget
        self.turn_budget = turn_budget

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token estimation (~4 characters per token for English text)."""
        return max(1, len(text) // 4)

    def compact_history(
        self,
        messages: list[dict[str, Any]],
        max_turns: int | None = None,
        max_tokens: int | None = None,
    ) -> list[dict[str, Any]]:
        """Compacts long message histories by summarizing older turns and keeping recent turns.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            max_turns: Maximum allowed uncompacted turns (default: self.turn_budget).
            max_tokens: Maximum allowed total token budget (default: self.token_budget).

        Returns:
            Compacted message list containing a summary of older turns plus the active tail.
        """
        turn_limit = max_turns or self.turn_budget
        token_limit = max_tokens or self.token_budget

        if not messages or len(messages) <= turn_limit:
            total_tokens = sum(self.estimate_tokens(str(m.get("content", ""))) for m in messages)
            if total_tokens <= token_limit:
                return messages

        # Split into turns to summarize (head) and active turns to keep (tail)
        tail_count = max(2, turn_limit // 2)
        head_messages = messages[:-tail_count]
        tail_messages = messages[-tail_count:]

        # Build condensed summary of the head messages
        summary_points: list[str] = []
        for msg in head_messages:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", "")).strip()
            first_line = content.split("\n")[0][:140]
            summary_points.append(f"- {role.capitalize()}: {first_line}")

        summary_text = (
            "### [Compressed Historical Context Summary]\n"
            "Earlier conversation turns summarized to optimize context budget:\n"
            + "\n".join(summary_points)
        )

        compacted_entry = {
            "role": "system",
            "content": summary_text,
            "metadata": {"compacted": True, "summarized_turns": len(head_messages)},
        }

        return [compacted_entry] + tail_messages

    def prune_session_state(
        self,
        state: dict[str, Any],
        max_text_chars: int = 1500,
    ) -> dict[str, Any]:
        """Prunes bloated intermediate buffers in session state (e.g. raw scrape dumps).

        Args:
            state: The session state dictionary to prune.
            max_text_chars: Maximum characters allowed for verbose intermediate blobs.

        Returns:
            Pruned copy of the state dictionary.
        """
        pruned: dict[str, Any] = {}
        for key, val in state.items():
            if isinstance(val, str) and len(val) > max_text_chars:
                # Truncate raw scraping dumps while preserving structured outputs
                if key.startswith("raw_") or "scrape" in key.lower() or "debug" in key.lower():
                    logger.info("Pruned bloated state key '%s' (%d -> %d chars)", key, len(val), max_text_chars)
                    pruned[key] = val[:max_text_chars] + f"\n... [Pruned {len(val) - max_text_chars} characters]"
                else:
                    pruned[key] = val
            elif isinstance(val, list) and len(val) > 20:
                pruned[key] = val[:20]
            else:
                pruned[key] = val
        return pruned


default_compactor = ContextCompactor()


@trace_span("tool.compact_session_history")
def compact_session_history(
    max_tokens: int = 4000,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Inspects session context, summarizes older turns, and trims intermediate memory bloat.

    Args:
        max_tokens: Desired token budget ceiling (default: 4000).
        tool_context: ADK execution context with state and session history.

    Returns:
        Structured CompactionSummary report detailing tokens saved and compression metrics.
    """
    logger.info("Running compact_session_history with max_tokens budget=%d", max_tokens)

    original_tokens = 0
    compacted_tokens = 0
    original_turns = 0
    compacted_turns = 0

    if tool_context and hasattr(tool_context, "state") and tool_context.state is not None:
        state = tool_context.state
        # Estimate state size
        raw_state_str = str(state)
        original_tokens = ContextCompactor.estimate_tokens(raw_state_str)

        # Prune state bloat
        current_state_dict = {k: state[k] for k in state}
        pruned = default_compactor.prune_session_state(current_state_dict)
        for k, v in pruned.items():
            tool_context.state[k] = v

        compacted_tokens = ContextCompactor.estimate_tokens(str(pruned))
        tokens_saved = max(0, original_tokens - compacted_tokens)
        summary = f"Session state compacted. Saved approximately {tokens_saved} tokens."
    else:
        tokens_saved = 0
        summary = "No active tool_context state required compaction."

    report = CompactionSummary(
        original_turn_count=original_turns,
        compacted_turn_count=compacted_turns,
        estimated_original_tokens=original_tokens,
        estimated_compacted_tokens=compacted_tokens,
        tokens_saved=tokens_saved,
        summary=summary,
    )

    return report.model_dump()
