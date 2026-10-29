"""Brand Voice, Editorial Guidelines, and Long-Term Memory Management.

Maintains persistent editorial standards, author personas, publication history,
and anti-duplication memory with both native asynchronous (aiosqlite) and
synchronous storage engines.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
from pydantic import BaseModel, Field

from src.observability.logging import logger


class BrandGuidelines(BaseModel):
    """Brand voice, style rules, and target audience definitions."""

    brand_name: str = Field(default="CloudNative Insights", description="Publication or brand name")
    tone: str = Field(
        default="Authoritative, practical, engaging, and technically rigorous.",
        description="Editorial tone of voice",
    )
    target_audience: str = Field(
        default="Cloud architects, DevOps engineers, tech leads, and engineering executives.",
        description="Target readership",
    )
    perspective: str = Field(
        default="First-person plural ('we', 'our team') or objective technical narrative.",
        description="Narrative perspective",
    )
    style_rules: list[str] = Field(
        default_factory=lambda: [
            "Use active voice and direct sentence structures.",
            "Always include realistic, working code snippets or architectural diagrams.",
            "Support all quantitative claims with citations or benchmarks.",
            "Avoid buzzwords (e.g. 'game-changer', 'revolutionize') without concrete evidence.",
            "Structure articles with clear H2 and H3 markdown sections and bulleted takeaways.",
        ],
        description="Core stylistic guidelines",
    )
    key_themes: list[str] = Field(
        default_factory=lambda: [
            "Google Cloud Platform & Vertex AI",
            "Agentic AI and LLM Orchestration",
            "Distributed Systems & Cloud Architecture",
            "Site Reliability Engineering (SRE) & Observability",
            "DevOps, CI/CD, and Infrastructure as Code",
        ],
        description="Primary topic pillars",
    )


class PublishedArticleRecord(BaseModel):
    """Metadata record of an article produced and published by the agent."""

    article_id: str
    title: str
    topic: str
    slug: str
    word_count: int
    seo_score: float
    reading_ease: float
    published_at: str
    tags: list[str] = Field(default_factory=list)
    artifact_uri: str | None = None
    approval_status: str = Field(default="published", description="published, pending_approval, or draft")


class BrandMemoryStore:
    """Persistent SQLite-backed storage supporting both async and sync execution modes."""

    def __init__(self, db_path: str = ".adk/brand_memory.db"):
        self.db_path = db_path
        self._ensure_dir()
        self._init_db_sync()

    def _ensure_dir(self) -> None:
        """Ensure parent directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _init_db_sync(self) -> None:
        """Synchronous database schema initialization."""
        self._ensure_dir()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS brand_guidelines (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    data TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS publication_history (
                    article_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    word_count INTEGER NOT NULL,
                    seo_score REAL NOT NULL,
                    reading_ease REAL NOT NULL,
                    published_at TEXT NOT NULL,
                    tags TEXT,
                    artifact_uri TEXT,
                    approval_status TEXT DEFAULT 'published'
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS session_summaries (
                    session_id TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    token_count INTEGER NOT NULL,
                    turn_count INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

        # Seed initial default guidelines if missing
        if not self.get_guidelines():
            self.save_guidelines(BrandGuidelines())

    # =========================================================================
    # Asynchronous Database Operations (aiosqlite)
    # =========================================================================

    async def get_guidelines_async(self) -> BrandGuidelines:
        """Asynchronously fetch current brand guidelines."""
        self._ensure_dir()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT data FROM brand_guidelines WHERE id = 1") as cursor:
                row = await cursor.fetchone()
                if row:
                    try:
                        return BrandGuidelines.model_validate_json(row[0])
                    except Exception as exc:
                        logger.warning("Error parsing stored guidelines (%s); using defaults.", exc)
        return BrandGuidelines()

    async def save_guidelines_async(self, guidelines: BrandGuidelines) -> None:
        """Asynchronously save updated brand guidelines."""
        self._ensure_dir()
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO brand_guidelines (id, data, updated_at)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at
                """,
                (guidelines.model_dump_json(), now),
            )
            await db.commit()

    async def record_publication_async(self, record: PublishedArticleRecord) -> None:
        """Asynchronously record a publication entry."""
        self._ensure_dir()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO publication_history (
                    article_id, title, topic, slug, word_count, seo_score, reading_ease,
                    published_at, tags, artifact_uri, approval_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.article_id,
                    record.title,
                    record.topic,
                    record.slug,
                    record.word_count,
                    record.seo_score,
                    record.reading_ease,
                    record.published_at,
                    json.dumps(record.tags),
                    record.artifact_uri,
                    record.approval_status,
                ),
            )
            await db.commit()

    async def list_publications_async(self, limit: int = 50) -> list[PublishedArticleRecord]:
        """Asynchronously list published articles."""
        self._ensure_dir()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT article_id, title, topic, slug, word_count, seo_score, reading_ease,
                       published_at, tags, artifact_uri, approval_status
                FROM publication_history
                ORDER BY published_at DESC LIMIT ?
                """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
                records: list[PublishedArticleRecord] = []
                for row in rows:
                    records.append(
                        PublishedArticleRecord(
                            article_id=row[0],
                            title=row[1],
                            topic=row[2],
                            slug=row[3],
                            word_count=row[4],
                            seo_score=row[5],
                            reading_ease=row[6],
                            published_at=row[7],
                            tags=json.loads(row[8]) if row[8] else [],
                            artifact_uri=row[9],
                            approval_status=row[10] if len(row) > 10 and row[10] else "published",
                        )
                    )
                return records

    async def check_similar_topic_async(self, topic: str) -> PublishedArticleRecord | None:
        """Asynchronously check if an article on a matching or similar topic exists."""
        normalized = topic.lower().strip()
        articles = await self.list_publications_async(limit=100)
        for article in articles:
            if (
                normalized in article.topic.lower()
                or article.topic.lower() in normalized
                or normalized in article.title.lower()
            ):
                return article
        return None

    # =========================================================================
    # Synchronous Database Operations (Convenience & CLI compatibility)
    # =========================================================================

    def get_guidelines(self) -> BrandGuidelines:
        """Fetch current brand guidelines synchronously."""
        self._ensure_dir()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM brand_guidelines WHERE id = 1")
            row = cursor.fetchone()
            if row:
                try:
                    return BrandGuidelines.model_validate_json(row[0])
                except Exception as exc:
                    logger.warning("Error parsing stored guidelines (%s); using defaults.", exc)
        return BrandGuidelines()

    def save_guidelines(self, guidelines: BrandGuidelines) -> None:
        """Save updated brand guidelines synchronously."""
        self._ensure_dir()
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO brand_guidelines (id, data, updated_at)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at
                """,
                (guidelines.model_dump_json(), now),
            )
            conn.commit()

    def record_publication(self, record: PublishedArticleRecord) -> None:
        """Record an article publication synchronously."""
        self._ensure_dir()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO publication_history (
                    article_id, title, topic, slug, word_count, seo_score, reading_ease,
                    published_at, tags, artifact_uri, approval_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.article_id,
                    record.title,
                    record.topic,
                    record.slug,
                    record.word_count,
                    record.seo_score,
                    record.reading_ease,
                    record.published_at,
                    json.dumps(record.tags),
                    record.artifact_uri,
                    record.approval_status,
                ),
            )
            conn.commit()

    def list_publications(self, limit: int = 50) -> list[PublishedArticleRecord]:
        """List published articles synchronously."""
        self._ensure_dir()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT article_id, title, topic, slug, word_count, seo_score, reading_ease,
                       published_at, tags, artifact_uri, approval_status
                FROM publication_history
                ORDER BY published_at DESC LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            records: list[PublishedArticleRecord] = []
            for row in rows:
                records.append(
                    PublishedArticleRecord(
                        article_id=row[0],
                        title=row[1],
                        topic=row[2],
                        slug=row[3],
                        word_count=row[4],
                        seo_score=row[5],
                        reading_ease=row[6],
                        published_at=row[7],
                        tags=json.loads(row[8]) if row[8] else [],
                        artifact_uri=row[9],
                        approval_status=row[10] if len(row) > 10 and row[10] else "published",
                    )
                )
            return records

    def check_similar_topic(self, topic: str) -> PublishedArticleRecord | None:
        """Check if an article on a matching or similar topic exists synchronously."""
        normalized = topic.lower().strip()
        articles = self.list_publications(limit=100)
        for article in articles:
            if (
                normalized in article.topic.lower()
                or article.topic.lower() in normalized
                or normalized in article.title.lower()
            ):
                return article
        return None


# Global singleton instance
brand_memory = BrandMemoryStore()
