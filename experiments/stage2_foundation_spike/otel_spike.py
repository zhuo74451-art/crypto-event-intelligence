"""OpenTelemetry observability spike — in-memory exporter, no backend."""

from __future__ import annotations

from typing import Any, Dict, List

from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def run_all() -> List[ReadableSpan]:
    """Emit correlated spans and return finished spans."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("stage2_spike")
    run_id = "run_001"

    with tracer.start_as_current_span("run_all.root", attributes={"run_id": run_id}):
        # Retrieval span
        with tracer.start_as_current_span("event.retrieval", attributes={"run_id": run_id, "event_id": "evt_001", "resource": "source"}):
            pass

        # Semantic pass A
        with tracer.start_as_current_span("semantic.synthesis", attributes={"run_id": run_id, "thesis_id": "ths_001", "pass_type": "semantic_a"}):
            pass

        # Semantic pass B
        with tracer.start_as_current_span("semantic.risk_challenge", attributes={"run_id": run_id, "thesis_id": "ths_001", "pass_type": "semantic_b"}):
            pass

        # Arbitration
        with tracer.start_as_current_span("arbitration.evaluate", attributes={"run_id": run_id, "thesis_id": "ths_001", "outcome": "decided"}):
            pass

        # Transition
        with tracer.start_as_current_span("lifecycle.transition", attributes={"run_id": run_id, "thesis_id": "ths_001", "from_state": "DISCOVERED", "to_state": "QUALIFYING"}):
            pass

        # Recovery
        with tracer.start_as_current_span("recovery.retry", attributes={"run_id": run_id, "review_id": "rev_001", "retry_count": 1}):
            pass

    provider.force_flush()
    return exporter.get_finished_spans()
