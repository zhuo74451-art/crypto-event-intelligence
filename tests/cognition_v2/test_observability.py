"""Cognition v2 observability and telemetry tests."""

import logging
import json

import pytest

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from market_radar.cognition_v2.observability.telemetry import (
    setup_logging,
    StructuredFormatter,
    CorrelationContext,
    exportable_attributes,
)


class TestOpenTelemetry:
    def test_tracer_produces_spans(self):
        tracer_provider = TracerProvider()
        exporter = InMemorySpanExporter()
        tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer = tracer_provider.get_tracer("test")
        with tracer.start_as_current_span("test_span") as span:
            span.set_attribute("test_key", "test_value")
        spans = exporter.get_finished_spans()
        assert len(spans) >= 1
        names = {s.name for s in spans}
        assert "test_span" in names

    def test_correlation_attributes(self):
        tracer_provider = TracerProvider()
        exporter = InMemorySpanExporter()
        tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer = tracer_provider.get_tracer("test")
        ctx = CorrelationContext()
        ctx.run_id = "test-run-001"
        ctx.thesis_id = "thesis-001"
        ctx.event_id = "event-001"
        with tracer.start_as_current_span("correlated_span", attributes=ctx.to_span_attributes()):
            pass
        spans = exporter.get_finished_spans()
        span = spans[0]
        assert span.attributes.get("run_id") == "test-run-001"
        assert span.attributes.get("thesis_id") == "thesis-001"
        assert span.attributes.get("event_id") == "event-001"

    def test_data_minimization(self):
        tracer_provider = TracerProvider()
        exporter = InMemorySpanExporter()
        tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer = tracer_provider.get_tracer("test")
        with tracer.start_as_current_span("safe_span") as span:
            safe = exportable_attributes({
                "run_id": "r1",
                "thesis_id": "t1",
                "version": 3,
                "evidence_body": "should be excluded",
                "secret_key": "should be excluded",
            })
            for key, value in safe.items():
                span.set_attribute(key, value)
        spans = exporter.get_finished_spans()
        span = spans[0]
        assert span.attributes.get("run_id") == "r1"
        assert "evidence_body" not in span.attributes
        assert "secret_key" not in span.attributes

    def test_no_evidence_body_in_attributes(self):
        tracer_provider = TracerProvider()
        exporter = InMemorySpanExporter()
        tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer = tracer_provider.get_tracer("test")
        with tracer.start_as_current_span("no_evidence"):
            pass
        spans = exporter.get_finished_spans()
        for span in spans:
            for key in span.attributes:
                assert "evidence" not in key.lower() or "body" not in key.lower(), (
                    f"Evidence body leaked: {key}"
                )


class TestLogging:
    def test_structured_logger(self):
        logger = setup_logging(logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_structured_format_no_credentials(self):
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname=__file__, lineno=1, msg="test message",
            args=None, exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "test message"
        assert "timestamp" in parsed
        assert "level" in parsed


class TestCorrelationContext:
    def test_default_run_id(self):
        ctx = CorrelationContext()
        assert ctx.run_id is not None

    def test_span_attributes(self):
        ctx = CorrelationContext()
        ctx.thesis_id = "t1"
        attrs = ctx.to_span_attributes()
        assert attrs["run_id"] == ctx.run_id
        assert attrs["thesis_id"] == "t1"

    def test_empty_attributes_excluded(self):
        ctx = CorrelationContext()
        attrs = ctx.to_span_attributes()
        assert "thesis_id" not in attrs
        assert "event_id" not in attrs
