"""Integration tests for OmniBlog FastAPI REST API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)


def test_healthz_endpoint():
    """Verify /healthz liveness probe returns 200 OK."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data


def test_ready_endpoint():
    """Verify /ready readiness probe returns 200 OK."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database_connected"] is True


def test_metrics_endpoint():
    """Verify /metrics endpoint returns operational metrics."""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_articles_published" in data
    assert "average_seo_score" in data


def test_guidelines_get_and_put():
    """Verify retrieving and updating brand guidelines via API."""
    # GET
    res_get = client.get("/api/v1/guidelines")
    assert res_get.status_code == 200
    guidelines = res_get.json()
    assert guidelines["brand_name"] == "CloudNative Insights"

    # PUT
    guidelines["brand_name"] = "Google Cloud Architecture Journal"
    res_put = client.put("/api/v1/guidelines", json=guidelines)
    assert res_put.status_code == 200
    updated = res_put.json()
    assert updated["brand_name"] == "Google Cloud Architecture Journal"


def test_audit_draft_endpoint():
    """Verify /api/v1/articles/audit calculates real-time diagnostics."""
    payload = {
        "draft_markdown": "# Event-Driven Systems\n\nExploring asynchronous messaging with Cloud Pub/Sub.\n\n## Architecture\n\n```python\nprint('pubsub')\n```\n\n## References\n\n- https://cloud.google.com/pubsub",
        "target_keyword": "Cloud Pub/Sub",
        "topic": "Event-Driven Systems",
    }
    response = client.post("/api/v1/articles/audit", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "seo_audit" in data
    assert "verification_audit" in data
    assert "metadata_preview" in data


def test_generate_article_endpoint():
    """Verify end-to-end article generation via REST API."""
    payload = {
        "topic": "Agentic AI with Google ADK",
        "target_keyword": "Google ADK",
        "target_word_count": 800,
        "require_human_approval": False,
    }
    response = client.post("/api/v1/articles/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "published"
    assert data["article_id"].startswith("art-")
    assert data["slug"].startswith("building-production-grade-systems-with-agentic-ai")
    assert data["word_count"] > 100
    assert data["seo_score"] > 0
    assert "metadata" in data

    # Verify article appears in GET /api/v1/articles
    res_list = client.get("/api/v1/articles")
    assert res_list.status_code == 200
    articles = res_list.json()["articles"]
    assert len(articles) >= 1
    assert any(a["article_id"] == data["article_id"] for a in articles)


def test_generate_article_with_hitl_approval():
    """Verify Human-in-the-Loop workflow with pending approval and decision."""
    payload = {
        "topic": "Microservices with GKE Autopilot",
        "target_keyword": "GKE Autopilot",
        "require_human_approval": True,
    }
    response = client.post("/api/v1/articles/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending_human_approval"
    token = data["approval_token"]
    assert token is not None

    # Check pending approvals endpoint
    pending_res = client.get("/api/v1/articles/pending-approval")
    assert pending_res.status_code == 200
    assert pending_res.json()["count"] >= 1

    # Submit approval decision
    decision_res = client.post(
        f"/api/v1/articles/{token}/decision",
        json={"approved": True, "reviewer_notes": "Approved by Senior Tech Lead"},
    )
    assert decision_res.status_code == 200
    assert decision_res.json()["status"] == "approved"
