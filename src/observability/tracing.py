"""OpenTelemetry Tracing and Google Cloud Trace Integration.

Configures distributed tracing for OmniBlog agents, custom spans for
orchestration turns, tool execution times, and LLM reasoning cycles.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode

from src.config import settings

logger = logging.getLogger(__name__)

_TRACER_INITIALIZED = False


def init_tracer(service_name: str | None = None) -> trace.Tracer:
    """Initialize OpenTelemetry tracer with optional Google Cloud Trace exporter."""
    global _TRACER_INITIALIZED
    svc_name = service_name or settings.otel_service_name

    resource = Resource.create({SERVICE_NAME: svc_name})
    provider = TracerProvider(resource=resource)

    if settings.enable_cloud_trace:
        try:
            from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

            cloud_exporter = CloudTraceSpanExporter(project_id=settings.google_cloud_project)
            provider.add_span_processor(BatchSpanProcessor(cloud_exporter))
            logger.info("Google Cloud Trace exporter configured for project %s", settings.google_cloud_project)
        except Exception as exc:
            logger.warning("Failed to initialize CloudTraceSpanExporter (%s); falling back to default.", exc)
            from opentelemetry.sdk.trace.export import SimpleSpanProcessor
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    else:
        # Local development / unit test in-memory processor
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
        provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))

    trace.set_tracer_provider(provider)
    _TRACER_INITIALIZED = True
    return trace.get_tracer(svc_name)


def get_tracer(name: str | None = None) -> trace.Tracer:
    """Return an active tracer instance."""
    if not _TRACER_INITIALIZED:
        init_tracer()
    return trace.get_tracer(name or settings.otel_service_name)


def get_current_trace_and_span_id() -> tuple[str | None, str | None]:
    """Get hex representations of current trace_id and span_id for logging correlation."""
    span = trace.get_current_span()
    if span and span.is_recording():
        ctx = span.get_span_context()
        trace_id = format(ctx.trace_id, "032x")
        span_id = format(ctx.span_id, "016x")
        return trace_id, span_id
    return None, None


def trace_span(span_name: str, attributes: dict[str, Any] | None = None):
    """Decorator to trace synchronous or asynchronous functions with custom span attributes."""

    def decorator(func: Callable):
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for k, v in attributes.items():
                        span.set_attribute(k, str(v))
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    raise

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for k, v in attributes.items():
                        span.set_attribute(k, str(v))
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
