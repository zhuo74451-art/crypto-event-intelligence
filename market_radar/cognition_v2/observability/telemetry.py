"""Observability — structured logging and OpenTelemetry bootstrap.

No evidence bodies, credentials, or private paths are exported.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# Structured JSON logging
# ═══════════════════════════════════════════════════════════════════════════════

class StructuredFormatter(logging.Formatter):
    """JSON-structured log formatter. Excludes evidence bodies and secrets."""

    SAFE_KEYS = {"message", "level", "logger", "timestamp", "run_id", "thesis_id",
                  "event_id", "case_id", "version", "duration_ms", "component"}

    def format(self, record: logging.LogRecord) -> str:
        entry: Dict[str, Any] = {
            "timestamp": _utc_now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in self.SAFE_KEYS:
            val = getattr(record, key, None)
            if val is not None:
                entry[key] = val
        # Explicitly exclude evidence bodies and secrets
        for exclude in ("body", "evidence", "secret", "password", "key", "credential"):
            if exclude in entry:
                entry[exclude] = "__redacted__"
        return json.dumps(entry, default=str)


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure structured JSON logging."""
    logger = logging.getLogger("cognition_v2")
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    # Prevent duplicate handlers
    if not logger.handlers:
        logger.addHandler(handler)
    return logger


# ═══════════════════════════════════════════════════════════════════════════════
# OpenTelemetry
# ═══════════════════════════════════════════════════════════════════════════════

_exporter: Optional[InMemorySpanExporter] = None
_provider: Optional[TracerProvider] = None


def setup_otel(
    service_name: str = "cognition_v2",
    in_memory: bool = True,
) -> TracerProvider:
    """Set up OpenTelemetry with in-memory exporter (no backend)."""
    global _exporter, _provider

    _provider = TracerProvider()

    if in_memory:
        _exporter = InMemorySpanExporter()
        _provider.add_span_processor(SimpleSpanProcessor(_exporter))
    else:
        _exporter = None

    trace.set_tracer_provider(_provider)
    return _provider


def get_tracer(name: str = "cognition_v2"):
    return trace.get_tracer(name)


def get_in_memory_exporter() -> Optional[InMemorySpanExporter]:
    return _exporter


def reset_otel() -> None:
    """Reset OpenTelemetry (for test cleanup)."""
    global _exporter, _provider
    _exporter = None
    _provider = None


def exportable_attributes(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """Filter attributes to exclude evidence bodies, secrets, and private paths."""
    safe = {}
    exclude_prefixes = ("evidence_body", "secret", "credential", "password", "private_path")
    for key, value in attributes.items():
        if any(key.startswith(prefix) for prefix in exclude_prefixes):
            continue
        safe[key] = value
    return safe


# ═══════════════════════════════════════════════════════════════════════════════
# Correlation IDs
# ═══════════════════════════════════════════════════════════════════════════════

class CorrelationContext:
    """Manages correlation IDs across a cognition run."""

    def __init__(self):
        self.run_id: str = str(uuid4())
        self.thesis_id: Optional[str] = None
        self.event_id: Optional[str] = None
        self.case_id: Optional[str] = None

    def to_span_attributes(self) -> Dict[str, str]:
        attrs: Dict[str, str] = {
            "run_id": self.run_id,
        }
        if self.thesis_id:
            attrs["thesis_id"] = self.thesis_id
        if self.event_id:
            attrs["event_id"] = self.event_id
        if self.case_id:
            attrs["case_id"] = self.case_id
        return attrs
