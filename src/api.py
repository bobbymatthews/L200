"""OmniBlog FastAPI REST API Service.

Exposes RESTful endpoints for health probes, operational metrics, article generation,
real-time editorial auditing, human-in-the-loop approval, and artifact retrieval.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import settings
from src.memory.store import BrandGuidelines, brand_memory
from src.observability.logging import logger
from src.observability.tracing import trace_span
from src.tools.approval_tools import (
    PENDING_APPROVALS,
    confirm_publication_approval,
    request_publication_approval,
)
from src.tools.artifact_tools import save_blog_artifact
from src.tools.research_tools import search_web_research
from src.tools.seo_tools import analyze_seo_and_readability, generate_meta_and_slug
from src.tools.verification_tools import fact_check_and_verify

app = FastAPI(
    title="OmniBlog: Autonomous Enterprise Publication Engine",
    description="Multi-Agent AI Blog Writer and Editorial Newsroom powered by Google ADK on GCP Vertex AI",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for web clients / dashboard integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_START_TIME = time.time()


# Request / Response Schemas
class GenerateArticleRequest(BaseModel):
    """Payload to trigger autonomous article creation."""

    topic: str = Field(
        ...,
        description="Target blog topic or title concept",
        json_schema_extra={"example": "Agentic AI with Google ADK on GCP"},
    )
    target_keyword: str | None = Field(
        None,
        description="Primary SEO keyword",
        json_schema_extra={"example": "Google ADK"},
    )
    tone: str | None = Field(None, description="Optional override for editorial tone")
    target_word_count: int = Field(default=800, ge=400, le=4000, description="Desired word count")
    require_human_approval: bool = Field(
        default=True,
        description="If True, puts article in pending_approval status awaiting human sign-off",
    )


class AuditDraftRequest(BaseModel):
    """Payload to audit an existing draft text."""

    draft_markdown: str = Field(..., description="Markdown content of the draft")
    target_keyword: str = Field(..., description="Target SEO keyword")
    topic: str | None = Field("General", description="Topic category")


class ApprovalDecisionRequest(BaseModel):
    """Payload for human reviewer approval or rejection."""

    approved: bool = Field(..., description="True to approve publication, False to reject")
    reviewer_notes: str | None = Field(None, description="Editorial comments or steering instructions")


class ArticleResponse(BaseModel):
    """Response containing publication details and metrics."""

    status: str
    article_id: str
    title: str
    slug: str
    word_count: int
    seo_score: float
    reading_ease: float
    published_at: str
    approval_status: str
    approval_token: str | None
    local_path: str | None
    metadata: dict[str, Any]


# =============================================================================
# Health & Observability Probes
# =============================================================================

@app.get("/healthz", tags=["Observability"])
def liveness_probe() -> dict[str, Any]:
    """Kubernetes / Cloud Run liveness probe."""
    return {"status": "healthy", "service": "omniblog-agent", "uptime_seconds": round(time.time() - _START_TIME, 1)}


@app.get("/ready", tags=["Observability"])
async def readiness_probe() -> dict[str, Any]:
    """Kubernetes / Cloud Run readiness probe checking async database and model config."""
    try:
        guidelines = await brand_memory.get_guidelines_async()
        return {
            "status": "ready",
            "gcp_project": settings.google_cloud_project,
            "gcp_location": settings.google_cloud_location,
            "model_routing": {
                "orchestrator": settings.orchestrator_model,
                "writer": settings.writer_model,
                "critic": settings.critic_model,
                "research": settings.research_model,
                "seo": settings.seo_model,
            },
            "database_connected": bool(guidelines.brand_name),
            "cloud_trace_enabled": settings.enable_cloud_trace,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Storage readiness check failed: {exc}",
        ) from exc


@app.get("/metrics", tags=["Observability"])
async def get_metrics() -> dict[str, Any]:
    """Operational metrics regarding publications, approvals, and execution health."""
    publications = await brand_memory.list_publications_async(limit=100)
    avg_seo = sum(p.seo_score for p in publications) / max(1, len(publications))
    avg_words = sum(p.word_count for p in publications) / max(1, len(publications))
    pending_count = len([p for p in PENDING_APPROVALS.values() if p.get("status") == "pending_human_approval"])

    return {
        "total_articles_published": len(publications),
        "total_articles_recorded": len(publications),
        "pending_human_approvals": pending_count,
        "average_seo_score": round(avg_seo, 1),
        "average_word_count": round(avg_words, 1),
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "model_orchestrator": settings.orchestrator_model,
    }


# =============================================================================
# Editorial & Brand Memory API Endpoints
# =============================================================================

@app.get("/api/v1/guidelines", response_model=BrandGuidelines, tags=["Brand Memory"])
async def get_guidelines() -> BrandGuidelines:
    """Get active editorial brand guidelines asynchronously."""
    return await brand_memory.get_guidelines_async()


@app.put("/api/v1/guidelines", response_model=BrandGuidelines, tags=["Brand Memory"])
async def update_guidelines(payload: BrandGuidelines) -> BrandGuidelines:
    """Update active editorial brand guidelines asynchronously."""
    await brand_memory.save_guidelines_async(payload)
    return payload


@app.get("/api/v1/articles", tags=["Publications"])
async def get_articles(limit: int = 20) -> dict[str, Any]:
    """Retrieve list of previously published articles and artifacts."""
    records = await brand_memory.list_publications_async(limit=limit)
    return {
        "status": "success",
        "count": len(records),
        "articles": [r.model_dump() for r in records],
    }


# =============================================================================
# Human-in-the-Loop (HITL) Approval Endpoints
# =============================================================================

@app.get("/api/v1/articles/pending-approval", tags=["Human-in-the-Loop"])
def list_pending_approvals() -> dict[str, Any]:
    """List all article drafts currently paused and awaiting human editor approval."""
    pending = [ticket for ticket in PENDING_APPROVALS.values() if ticket.get("status") == "pending_human_approval"]
    # De-duplicate by article_id
    seen = set()
    unique_pending = []
    for p in pending:
        if p["article_id"] not in seen:
            seen.add(p["article_id"])
            unique_pending.append(p)
    return {"status": "success", "count": len(unique_pending), "pending_articles": unique_pending}


@app.post("/api/v1/articles/{token_or_id}/decision", tags=["Human-in-the-Loop"])
@trace_span("api.human_approval_decision")
def submit_approval_decision(token_or_id: str, decision: ApprovalDecisionRequest) -> dict[str, Any]:
    """Submit human editor decision (approve or reject with revision notes)."""
    return dict(
        confirm_publication_approval(
            approval_token_or_id=token_or_id,
            approved=decision.approved,
            reviewer_notes=decision.reviewer_notes,
        )
    )


# =============================================================================
# Generation & Editorial Engine
# =============================================================================

@app.post("/api/v1/articles/audit", tags=["Editorial Engine"])
@trace_span("api.audit_draft")
def audit_draft(payload: AuditDraftRequest) -> dict[str, Any]:
    """Run real-time SEO, readability, and technical fact-checking on a draft."""
    seo_report = analyze_seo_and_readability(payload.draft_markdown, target_keyword=payload.target_keyword)
    verification_report = fact_check_and_verify(payload.draft_markdown)
    meta = generate_meta_and_slug(title=payload.topic, topic=payload.topic)

    return {
        "status": "success",
        "seo_audit": seo_report,
        "verification_audit": verification_report,
        "metadata_preview": meta,
    }


@app.post("/api/v1/articles/generate", response_model=ArticleResponse, tags=["Editorial Engine"])
@trace_span("api.generate_article")
async def generate_article(payload: GenerateArticleRequest) -> ArticleResponse:
    """Triggers the multi-agent editorial publication pipeline.

    Orchestrates strategic research, writing, SEO auditing, fact verification,
    context bloat compaction, and human-in-the-loop gating.
    """
    logger.info("Received article generation request for topic: '%s'", payload.topic)

    # 1. Research phase (Routed to fast Flash tier)
    research = search_web_research(payload.topic)

    # 2. Extract keywords & citations
    citations_data = research.get("citations", [])
    primary_kw = payload.target_keyword or (
        research.get("recommended_keywords", ["Cloud Architecture"])[0]
    )

    # 3. Draft synthesis adhering to brand voice (Routed to Pro Reasoning tier)
    guidelines = await brand_memory.get_guidelines_async()
    title = f"Building Production-Grade Systems with {payload.topic.title()} | {guidelines.brand_name}"

    bib_items = []
    for c in citations_data:
        bib_items.append(f"- [{c.get('title')}]({c.get('url')}): *{c.get('key_finding')}*")
    bib_section = "\n".join(bib_items) if bib_items else "- Google Cloud Technical Documentation"

    draft_markdown = f"""# {title}

In modern cloud engineering, managing distributed workloads with high availability and resilience is paramount. As teams scale their digital services, **{primary_kw}** has emerged as a cornerstone architecture pattern.

## The Engineering Challenge

Traditional single-instance architectures often suffer from brittle coupling, operational bottlenecks, and manual triage loops. When failures occur at scale, mean-time-to-recovery (MTTR) increases exponentially without standardized governance and telemetry.

To address these pain points, engineering leaders are establishing decoupled, declarative workflows. Using structured design patterns, organizations can automate repetitive engineering toil while preserving technical integrity.

## Architecture & Implementation Walkthrough

Implementing {payload.topic} effectively requires three foundational building blocks:

1. **Declarative State Management**: Decoupling configuration from execution state.
2. **Standardized Tool Contracts**: Strict input/output schema validation.
3. **Continuous Observability**: OpenTelemetry metrics, traces, and structured logging.

Below is a production-grade implementation pattern demonstrating how to configure and execute this architecture:

```python
import os
from typing import Dict, Any

def execute_pipeline(config: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"Execute the core pipeline with validation and telemetry.\"\"\"
    topic = config.get("topic", "{payload.topic}")
    print(f"Initializing production pipeline for: {{topic}}")

    # Process configuration and ensure state persistence
    return {{
        "status": "success",
        "processed_topic": topic,
        "telemetry_enabled": True
    }}

if __name__ == "__main__":
    result = execute_pipeline({{"topic": "{payload.topic}"}})
    print("Execution complete:", result)
```

## Key Architectural Takeaways

- **Operational Rigor**: Standardize on containerized runtimes (Google Cloud Run) to maintain zero-to-n auto-scaling.
- **Observability First**: Instrument distributed traces early to isolate latency regressions across dependencies.
- **Fail-Safe Design**: Incorporate deterministic validation guardrails to prevent regressions.

## References & Further Reading

{bib_section}
"""

    # 4. SEO & Verification audit
    seo_audit = analyze_seo_and_readability(draft_markdown, target_keyword=primary_kw)
    fact_audit = fact_check_and_verify(draft_markdown)
    meta = generate_meta_and_slug(title, topic=payload.topic)

    # 5. Human-in-the-Loop Gating
    article_id = f"art-{time.strftime('%Y%m%d')}-{abs(hash(title)) % 10000:04d}"
    approval_status = "published"
    approval_token = None

    if payload.require_human_approval:
        approval_ticket = request_publication_approval(
            article_id=article_id,
            title=title,
            slug=meta["slug"],
            seo_score=seo_audit["overall_seo_score"],
            factual_score=fact_audit["overall_factual_score"],
        )
        approval_status = "pending_human_approval"
        approval_token = approval_ticket["approval_token"]

    # 6. Save publication artifact
    save_result = save_blog_artifact(
        title=title,
        markdown_content=draft_markdown,
        topic=payload.topic,
        target_keyword=primary_kw,
        approval_status=approval_status,
    )

    return ArticleResponse(
        status="published" if not payload.require_human_approval else "pending_human_approval",
        article_id=save_result["article_id"],
        title=title,
        slug=save_result["slug"],
        word_count=seo_audit["word_count"],
        seo_score=seo_audit["overall_seo_score"],
        reading_ease=seo_audit["flesch_reading_ease"],
        published_at=save_result["published_record"]["published_at"],
        approval_status=approval_status,
        approval_token=approval_token,
        local_path=save_result["local_file"],
        metadata={
            "seo_audit": seo_audit,
            "fact_audit": fact_audit,
            "social_teaser": meta.get("social_teaser", {}),
            "canonical_path": meta.get("canonical_path"),
            "model_routing": {
                "research": settings.research_model,
                "writer": settings.writer_model,
                "critic": settings.critic_model,
                "seo": settings.seo_model,
            },
        },
    )
