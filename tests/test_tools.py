"""Unit tests for OmniBlog research, SEO, verification, and artifact tools."""

from __future__ import annotations

from pathlib import Path

from src.tools.artifact_tools import list_saved_articles, save_blog_artifact
from src.tools.research_tools import extract_key_citations, search_web_research
from src.tools.seo_tools import analyze_seo_and_readability, generate_meta_and_slug
from src.tools.verification_tools import fact_check_and_verify


def test_search_web_research_known_topic():
    """Verify research tool returns structured brief with citations for known topic."""
    result = search_web_research("Agentic AI")
    assert result["topic"] == "Agentic AI"
    assert len(result["citations"]) > 0
    assert "Google ADK" in result["recommended_keywords"]
    assert any("adk-docs" in c["url"] for c in result["citations"])


def test_search_web_research_dynamic_topic():
    """Verify research tool dynamically synthesizes brief for novel topics."""
    result = search_web_research("Quantum Edge Computing Architecture")
    assert "Quantum Edge Computing Architecture" in result["topic"]
    assert len(result["citations"]) >= 2
    assert len(result["key_takeaways"]) >= 3


def test_extract_key_citations():
    """Verify citations extractor creates formatted bibliography."""
    result = extract_key_citations("FinOps Cloud Cost Optimization")
    assert result["status"] == "success"
    assert result["count"] > 0
    assert "### References & Further Reading" in result["bibliography_markdown"]


def test_analyze_seo_and_readability_good_content():
    """Verify SEO and readability analyzer scores compliant technical markdown."""
    sample_text = """# Building Resilient Systems on Google Cloud

In modern software engineering, building reliable **Google Cloud** infrastructure is essential for success. In this guide, we will walk you through how to design simple, fast, and robust cloud services that can scale to millions of users.

## Decoupled Architecture

Distributed architectures require asynchronous messaging and isolated failure domains. When components are decoupled, cascading outages are mitigated and teams can deploy code independently.

## Automated Observability

Continuous telemetry through OpenTelemetry metrics and traces ensures engineers detect regressions early. Distributed systems require automated health probes and clear dashboards.

## Practical Implementation Walkthrough

Review the following Python implementation for managing distributed workers safely:

```python
def process_message(payload: dict) -> bool:
    print(f"Processing: {payload}")
    return True
```

## References & Further Reading

- [Google Cloud Architecture](https://cloud.google.com): Official architectural patterns.
"""
    report = analyze_seo_and_readability(sample_text, target_keyword="Google Cloud")
    assert report["word_count"] > 50
    assert report["target_keyword"] == "Google Cloud"
    assert report["keyword_count"] >= 1
    assert report["heading_counts"]["H1"] == 1
    assert report["heading_counts"]["H2"] >= 3
    assert report["flesch_reading_ease"] >= 0
    assert report["flesch_kincaid_grade"] > 0
    assert report["overall_seo_score"] >= 60.0


def test_analyze_seo_penalties():
    """Verify SEO analyzer penalizes missing keyword and missing headings."""
    short_text = "This is a short note without headings or primary keyword."
    report = analyze_seo_and_readability(short_text, target_keyword="SuperKubernetes")
    assert report["keyword_count"] == 0
    assert report["heading_counts"]["H1"] == 0
    assert report["status"] == "NEEDS_REVISION"
    assert any("not found" in r for r in report["recommendations"])


def test_generate_meta_and_slug():
    """Verify slug generation and meta description length."""
    title = "Building Scalable Microservices with GKE Autopilot & KEDA!"
    meta = generate_meta_and_slug(title, topic="Microservices")
    assert meta["slug"] == "building-scalable-microservices-with-gke-autopilot-keda"
    assert meta["canonical_path"].startswith("/blog/")
    assert len(meta["meta_description"]) <= 160
    assert "twitter" in meta["social_teaser"]
    assert "linkedin" in meta["social_teaser"]


def test_fact_check_and_verify_passes():
    """Verify verification tool approves clean, substantiated draft."""
    valid_draft = """# Architecture Guide

This guide explores architectural patterns for high-availability systems.

## Implementation

```python
import os
print("Running system")
```

## References & Further Reading

- [CNCF Cloud Native Patterns](https://www.cncf.io): Best practices guide.
"""
    # Pad draft to satisfy minimum length requirement
    valid_draft += "\n" + ("Designing distributed systems requires operational rigor, observability, and decoupled workflows. " * 30)

    result = fact_check_and_verify(valid_draft)
    assert result["overall_factual_score"] >= 75.0
    assert result["code_snippets_verified"] == 1
    assert result["unsupported_claims_count"] <= 1


def test_fact_check_and_verify_flags_buzzwords():
    """Verify verification tool flags unsubstantiated absolute claims."""
    bad_draft = """# Quick Post
This solution is 100% guaranteed and provides a 100x faster miracle speedup that never fails.
"""
    result = fact_check_and_verify(bad_draft)
    assert result["overall_factual_score"] < 75.0
    assert len(result["flagged_issues"]) >= 2
    assert any("guaranteed" in issue.lower() for issue in result["flagged_issues"])


def test_save_and_list_blog_artifacts():
    """Verify blog artifact saving, frontmatter injection, and catalog listing."""
    title = "Production Cloud Workflows with Google ADK"
    content = "# Production Cloud Workflows with Google ADK\n\nContent details here."
    save_res = save_blog_artifact(
        title=title,
        markdown_content=content,
        topic="Cloud Architecture",
        target_keyword="Google ADK",
    )

    assert save_res["status"] == "success"
    assert save_res["slug"] == "production-cloud-workflows-with-google-adk"
    assert Path(save_res["local_file"]).exists()
    assert Path(save_res["metadata_file"]).exists()

    # Verify frontmatter in saved file
    saved_text = Path(save_res["local_file"]).read_text(encoding="utf-8")
    assert "title: \"Production Cloud Workflows with Google ADK\"" in saved_text
    assert "status: \"published\"" in saved_text

    # Verify list_saved_articles
    articles_list = list_saved_articles()
    assert articles_list["count"] == 1
    assert articles_list["articles"][0]["title"] == title
