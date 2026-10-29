"""Unit tests for OpenTelemetry tracing and GCP structured JSON logging."""

from __future__ import annotations

import json
import logging

import pytest
from opentelemetry import trace

from src.observability.logging import GCPStructuredJsonFormatter
from src.observability.tracing import get_tracer, trace_span


def test_init_and_get_tracer():
    """Verify tracer initialization and retrieval."""
    tracer = get_tracer("test-tracer")
    assert tracer is not None
    assert isinstance(tracer, trace.Tracer)


def test_trace_span_decorator_sync():
    """Verify synchronous functions are traced without error."""

    @trace_span("test.sync_func", attributes={"component": "unit_test"})
    def sample_func(x: int) -> int:
        return x * 2

    result = sample_func(5)
    assert result == 10


@pytest.mark.asyncio
async def test_trace_span_decorator_async():
    """Verify asynchronous coroutines are traced properly."""

    @trace_span("test.async_func")
    async def sample_async_func(name: str) -> str:
        return f"Hello, {name}"

    res = await sample_async_func("ADK")
    assert res == "Hello, ADK"


def test_gcp_structured_json_formatter():
    """Verify log record formatting conforms to Google Cloud Logging specification."""
    formatter = GCPStructuredJsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="/app/src/test.py",
        lineno=42,
        msg="Test log message for GCP Cloud Logging",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["severity"] == "INFO"
    assert data["message"] == "Test log message for GCP Cloud Logging"
    assert data["logger"] == "test_logger"
    assert "timestamp" in data
    assert "sourceLocation" in data
    assert data["sourceLocation"]["line"] == 42
