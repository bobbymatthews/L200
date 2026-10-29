"""SEO and Readability Analysis Tools.

Computes exact Flesch-Kincaid readability statistics, keyword density,
heading hierarchy analysis, and generates optimized slugs and social metadata.
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


class SeoAuditReport(BaseModel):
    """Detailed SEO and readability audit report."""

    word_count: int
    estimated_reading_time_minutes: float
    sentence_count: int
    flesch_reading_ease: float
    flesch_kincaid_grade: float
    readability_interpretation: str
    target_keyword: str
    keyword_count: int
    keyword_density_percent: float
    heading_counts: dict[str, int]
    overall_seo_score: float
    status: str
    recommendations: list[str]


def _count_syllables(word: str) -> int:
    """Estimate syllable count for an English word using phonetic heuristic."""
    word = word.lower().strip(".:;?!,'\"-")
    if not word:
        return 0
    if len(word) <= 3:
        return 1

    word = re.sub(r"(?:[^laeiouy]|ed|es|e)$", "", word)
    word = re.sub(r"^y", "", word)
    matches = re.findall(r"[aeiouy]{1,2}", word)
    return max(1, len(matches))


@trace_span("tool.analyze_seo_and_readability")
def analyze_seo_and_readability(
    text: str,
    target_keyword: str,
    secondary_keywords: list[str] | None = None,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Analyzes a markdown blog draft for SEO keyword density, structure, and readability.

    Args:
        text: The markdown blog text to analyze.
        target_keyword: The primary keyword to optimize for.
        secondary_keywords: Optional list of secondary semantic keywords.
        tool_context: ADK execution context.

    Returns:
        Structured SeoAuditReport containing readability metrics, heading counts, and actionable advice.
    """
    logger.info("Running analyze_seo_and_readability for keyword '%s'", target_keyword)

    # 1. Clean markdown tokens for text statistics
    clean_text = re.sub(r"#+\s*", "", text)
    clean_text = re.sub(r"\[.*?\]\(.*?\)", "", clean_text)
    clean_text = re.sub(r"```[\s\S]*?```", "", clean_text)
    clean_text = re.sub(r"`.*?`", "", clean_text)

    # 2. Tokenize words and sentences (considering periods, punctuation, and markdown line breaks)
    words = re.findall(r"\b[A-Za-z0-9'-]+\b", clean_text)
    word_count = len(words)
    sentences = [s.strip() for s in re.split(r"[\r\n.!?]+", clean_text) if s.strip()]
    sentence_count = max(1, len(sentences))

    # 3. Reading time (average 220 words per minute)
    reading_time = round(word_count / 220.0, 1)

    # 4. Syllable counting & Readability calculation
    total_syllables = sum(_count_syllables(w) for w in words)
    words_per_sentence = word_count / sentence_count
    syllables_per_word = total_syllables / max(1, word_count)

    # Flesch Reading Ease: 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
    flesch_ease = round(206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word), 1)
    flesch_ease = max(0.0, min(100.0, flesch_ease))

    # Flesch-Kincaid Grade Level: 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
    grade_level = round((0.39 * words_per_sentence) + (11.8 * syllables_per_word) - 15.59, 1)
    grade_level = max(1.0, grade_level)

    if flesch_ease >= 70:
        readability_interp = "Fairly Easy (Broad accessibility, conversational)"
    elif flesch_ease >= 50:
        readability_interp = "Standard / Moderate (Ideal for professional technical blogs)"
    elif flesch_ease >= 30:
        readability_interp = "Difficult (Dense technical treatise, university grade)"
    else:
        readability_interp = "Very Confusing (Overly complex sentence structures)"

    # 5. Heading hierarchy
    h1_count = len(re.findall(r"^#\s+.*$", text, flags=re.MULTILINE))
    h2_count = len(re.findall(r"^##\s+.*$", text, flags=re.MULTILINE))
    h3_count = len(re.findall(r"^###\s+.*$", text, flags=re.MULTILINE))

    # 6. Keyword density
    kw_regex = re.escape(target_keyword.lower())
    keyword_matches = len(re.findall(rf"\b{kw_regex}\b", clean_text.lower()))
    keyword_density = round((keyword_matches / max(1, word_count)) * 100.0, 2)

    # 7. Recommendations and Scoring
    recommendations: list[str] = []
    score = 100.0

    # Word count check
    if word_count < 500:
        penalty = min(30.0, (500 - word_count) * 0.1)
        score -= penalty
        recommendations.append(f"Length is short ({word_count} words). Aim for at least 600-1,000 words for technical authority.")
    elif word_count > 3000:
        recommendations.append(f"Article is very long ({word_count} words). Consider splitting into a series or adding a Table of Contents.")

    # Keyword density check (ideal: 0.8% - 2.5%)
    if keyword_matches == 0:
        score -= 25.0
        recommendations.append(f"Target keyword '{target_keyword}' was not found in the body text.")
    elif keyword_density < 0.5:
        score -= 10.0
        recommendations.append(f"Target keyword density is low ({keyword_density}%). Integrate '{target_keyword}' naturally into key headings.")
    elif keyword_density > 3.0:
        score -= 15.0
        recommendations.append(f"Target keyword density is high ({keyword_density}%). Reduce keyword stuffing.")

    # Heading hierarchy check
    if h1_count != 1:
        score -= 10.0
        recommendations.append(f"Found {h1_count} H1 headings. Every post should have exactly one H1 title.")
    if h2_count < 3:
        score -= 10.0
        recommendations.append(f"Found only {h2_count} H2 sections. Break content into at least 3-4 distinct H2 thematic sections.")

    # Readability adjustment
    if flesch_ease < 35.0:
        score -= 10.0
        recommendations.append("Sentences are quite complex. Shorten long paragraphs and use bulleted lists.")

    overall_score = round(max(10.0, min(100.0, score)), 1)
    status = "EXCELLENT" if overall_score >= 85 else "ACCEPTABLE" if overall_score >= 70 else "NEEDS_REVISION"

    if not recommendations:
        recommendations.append("Content meets high SEO and technical readability standards.")

    report = SeoAuditReport(
        word_count=word_count,
        estimated_reading_time_minutes=reading_time,
        sentence_count=sentence_count,
        flesch_reading_ease=flesch_ease,
        flesch_kincaid_grade=grade_level,
        readability_interpretation=readability_interp,
        target_keyword=target_keyword,
        keyword_count=keyword_matches,
        keyword_density_percent=keyword_density,
        heading_counts={"H1": h1_count, "H2": h2_count, "H3": h3_count},
        overall_seo_score=overall_score,
        status=status,
        recommendations=recommendations,
    )

    if tool_context and hasattr(tool_context, "state") and tool_context.state is not None:
        try:
            tool_context.state["seo_report"] = report.model_dump()
            logger.info("Persisted seo_report to tool_context.state")
        except Exception as exc:
            logger.warning("Could not persist seo_report to state: %s", exc)

    return report.model_dump()


@trace_span("tool.generate_meta_and_slug")
def generate_meta_and_slug(
    title: str,
    topic: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Generates an SEO URL slug, concise meta description, OpenGraph tags, and social teaser text.

    Args:
        title: The final title of the article.
        topic: The primary theme or subject.
        tool_context: ADK execution context.

    Returns:
        Dictionary containing slug, meta_description, social_copy, and opengraph metadata.
    """
    logger.info("Generating slug and metadata for title: %s", title)

    # 1. Clean slug
    clean_title = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[-\s]+", "-", clean_title).strip("-")[:75]

    # 2. Meta description (target 145-160 characters)
    meta_description = (
        f"Discover how to implement {topic} with production-grade architecture, benchmarks, and "
        "practical engineering best practices on Google Cloud."
    )
    if len(meta_description) > 160:
        meta_description = meta_description[:157] + "..."

    # 3. Social snippets
    social_copy = {
        "twitter": f"🚀 New Post: '{title}'! Dive into our deep-dive engineering guide on {topic} with full architecture breakdowns and code. #CloudComputing #DevOps #AI",
        "linkedin": f"We just published a comprehensive technical guide: '{title}'.\n\nKey takeaways include architectural patterns, observability telemetry, and production deployment strategies.\n\nRead the full post at /{slug}",
    }

    result = {
        "title": title,
        "slug": slug,
        "canonical_path": f"/blog/{slug}",
        "meta_description": meta_description,
        "meta_description_char_count": len(meta_description),
        "social_teaser": social_copy,
        "opengraph": {
            "og:title": title,
            "og:description": meta_description,
            "og:type": "article",
            "og:site_name": "OmniBlog Publication",
        },
    }

    if tool_context and hasattr(tool_context, "state") and tool_context.state is not None:
        try:
            tool_context.state["article_metadata"] = result
        except Exception:
            pass

    return result
