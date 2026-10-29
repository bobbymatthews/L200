"""OmniBlog Configuration Module.

Manages application settings, GCP environment variables, ADK storage URIs,
strategic model routing per agent role, human-in-the-loop gates, and editorial quality thresholds.
"""

from __future__ import annotations

import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application and infrastructure configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Agent & LLM Configuration
    agent_name: str = Field(default="omniblog_editor_in_chief", description="Name of the root agent")
    model_name: str = Field(default="gemini-2.5-flash", description="Base default Gemini model identifier")
    temperature: float = Field(default=0.4, description="Sampling temperature for creative balance")
    max_tokens: int = Field(default=8192, description="Max output tokens for long-form content")

    # =========================================================================
    # Strategic Model Routing (Tiered by Agent Cognitive Requirements)
    # =========================================================================
    orchestrator_model: str = Field(
        default_factory=lambda: os.getenv("ORCHESTRATOR_MODEL", "gemini-2.5-pro"),
        description="High-reasoning model for Editor-in-Chief planning and routing",
    )
    writer_model: str = Field(
        default_factory=lambda: os.getenv("WRITER_MODEL", "gemini-2.5-pro"),
        description="High-capacity model for nuanced, long-form technical prose and code generation",
    )
    critic_model: str = Field(
        default_factory=lambda: os.getenv("CRITIC_MODEL", "gemini-2.5-pro"),
        description="Precision reasoning model for fact-checking, code auditing, and contradiction detection",
    )
    research_model: str = Field(
        default_factory=lambda: os.getenv("RESEARCH_MODEL", "gemini-2.5-flash"),
        description="Fast, cost-efficient model for web search synthesis and citation extraction",
    )
    seo_model: str = Field(
        default_factory=lambda: os.getenv("SEO_MODEL", "gemini-2.5-flash"),
        description="Fast model for algorithmic scoring, slugification, and metadata formatting",
    )

    # =========================================================================
    # Human-in-the-Loop (HITL) Publication Gate
    # =========================================================================
    require_human_approval: bool = Field(
        default=True,
        description="Whether publishing requires explicit human confirmation before catalog entry",
    )

    # =========================================================================
    # Resilience & Retry Configuration (Handles 503 / 429 transient errors)
    # =========================================================================
    model_max_retries: int = Field(default=5, description="Max retry attempts for model API calls")
    model_retry_delay: float = Field(default=1.5, description="Initial retry delay in seconds")
    model_max_delay: float = Field(default=30.0, description="Max retry delay in seconds")

    # Google Cloud Platform Configuration
    google_cloud_project: str | None = Field(
        default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT", "msk-fde")),
        description="GCP Project ID",
    )
    google_cloud_location: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_CLOUD_LOCATION", os.getenv("GCP_REGION", "us-central1")),
        description="GCP Region",
    )
    google_genai_use_enterprise: bool = Field(
        default=True,
        description="Whether to use Google Cloud Vertex AI backend",
    )
    gemini_api_key: str | None = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY")),
        description="Google AI Studio API Key (optional fallback)",
    )

    # ADK Service URIs (Storage, Memory, Sessions, Artifacts)
    session_service_uri: str = Field(
        default="sqlite:///.adk/sessions.db",
        description="Session service URI (sqlite://..., memory://, agentengine://...)",
    )
    memory_service_uri: str = Field(
        default="sqlite:///.adk/memory.db",
        description="Memory service URI (sqlite://..., memory://, agentengine://...)",
    )
    artifact_service_uri: str = Field(
        default="file://./artifacts",
        description="Artifact service URI (file://..., memory://, gs://...)",
    )

    # Observability & Tracing Configuration
    enable_cloud_trace: bool = Field(
        default=False,
        description="Whether to export OpenTelemetry traces to Google Cloud Trace",
    )
    otel_service_name: str = Field(
        default="omniblog-agent",
        description="OpenTelemetry service name for distributed tracing",
    )
    log_level: str = Field(
        default="INFO",
        description="Application logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="API server host")
    port: int = Field(default=8000, description="API server port")

    # Editorial Quality Guardrails
    min_word_count: int = Field(default=600, description="Minimum acceptable blog word count")
    target_flesch_reading_ease: float = Field(default=45.0, description="Minimum readability score (standard)")
    min_seo_score: float = Field(default=75.0, description="Minimum acceptable SEO quality score (0-100)")
    max_critique_iterations: int = Field(default=3, description="Maximum iterative revision cycles")


# Global singleton settings instance
settings = Settings()
