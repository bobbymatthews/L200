"""Structured JSON Logging with Google Cloud Trace Correlation.

Formats logs as structured JSON compatible with Google Cloud Logging,
automatically injecting OpenTelemetry trace and span IDs to correlate logs
with distributed traces in the GCP Cloud Operations Console.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from src.config import settings
from src.observability.tracing import get_current_trace_and_span_id


class GCPStructuredJsonFormatter(logging.Formatter):
    """JSON formatter formatted specifically for Google Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "sourceLocation": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            },
        }

        # Inject OpenTelemetry trace and span IDs for Cloud Logging correlation
        trace_id, span_id = get_current_trace_and_span_id()
        if trace_id and settings.google_cloud_project:
            log_entry["logging.googleapis.com/trace"] = (
                f"projects/{settings.google_cloud_project}/traces/{trace_id}"
            )
        if span_id:
            log_entry["logging.googleapis.com/spanId"] = span_id

        # Attach custom extra fields
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_entry.update(record.extra_fields)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(level: str | None = None) -> logging.Logger:
    """Configure root logger with GCP structured JSON formatting."""
    log_level = level or settings.log_level
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(GCPStructuredJsonFormatter())
    root_logger.addHandler(console_handler)

    return logging.getLogger("omniblog")


logger = setup_logging()
