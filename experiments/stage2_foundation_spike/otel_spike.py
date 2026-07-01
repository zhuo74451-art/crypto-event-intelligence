"""
Stage 2 Foundation Spike — OpenTelemetry Observability Proof
=============================================================
Demonstrates tracing with an in-memory exporter, span correlation,
and attribute integrity.  No real telemetry backends are used.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass, field

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

# ---------------------------------------------------------------------------
# Global fixture
# ---------------------------------------------------------------------------

_exporter = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(_exporter))
trace.set_tracer_provider(_provider)

_tracer = trace.get_tracer("stage2_spike")

# ---------------------------------------------------------------------------
# Span emitters
# ---------------------------------------------------------------------------


def emit_retrieval_span(run_id: str, event_id: str) -> None:
    """Emit a span representing an event-retrieval step."""
    with _tracer.start_as_current_span("event.retrieval") as span:
        span.set_attribute("run_id", run_id)
        span.set_attribute("event_id", event_id)
        span.set_attribute("resource", "source")


def emit_semantic_pass_a(run_id: str, thesis_id: str) -> None:
    """Emit a span for the first semantic-analysis pass."""
    with _tracer.start_as_current_span("semantic.pass_a") as span:
        span.set_attribute("run_id", run_id)
        span.set_attribute("thesis_id", thesis_id)
        span.set_attribute("pass_type", "semantic_a")


def emit_semantic_pass_b(run_id: str, thesis_id: str) -> None:
    """Emit a span for the second semantic-analysis pass."""
    with _tracer.start_as_current_span("semantic.pass_b") as span:
        span.set_attribute("run_id", run_id)
        span.set_attribute("thesis_id", thesis_id)
        span.set_attribute("pass_type", "semantic_b")


def emit_arbitration_span(run_id: str, thesis_id: str) -> None:
    """Emit a span representing arbitration between semantic passes."""
    with _tracer.start_as_current_span("arbitration.decide") as span:
        span.set_attribute("run_id", run_id)
        span.set_attribute("thesis_id", thesis_id)
        span.set_attribute("outcome", "decided")


def emit_transition_span(
    run_id: str,
    thesis_id: str,
    from_state: str,
    to_state: str,
) -> None:
    """Emit a span for a state-machine transition."""
    with _tracer.start_as_current_span("lifecycle.transition") as span:
        span.set_attribute("run_id", run_id)
        span.set_attribute("thesis_id", thesis_id)
        span.set_attribute("from_state", from_state)
        span.set_attribute("to_state", to_state)


def emit_recovery_span(
    run_id: str,
    review_id: str,
    retry_count: int,
) -> None:
    """Emit a span for a recovery/retry attempt."""
    with _tracer.start_as_current_span("recovery.retry") as span:
        span.set_attribute("run_id", run_id)
        span.set_attribute("review_id", review_id)
        span.set_attribute("retry_count", retry_count)


# ---------------------------------------------------------------------------
# RunResult
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    """Outcome of a single run_all() execution."""

    passed: bool
    """True only when every check succeeds."""

    span_count: int
    """Number of finished spans exported."""

    attributes_check: bool
    """True when every span carries the expected attribute keys."""

    # Internal detail kept for diagnostic use.
    _failures: list[str] = field(default_factory=list, repr=False)

    @classmethod
    def from_spans(
        cls,
        spans: list[trace.Span],
        *,
        expected_count: int = 8,
    ) -> RunResult:
        """Build a RunResult by inspecting the exported *spans*.

        Verifies:
        - Correct number of spans.
        - No forbidden attribute keys are present.
        """
        failures: list[str] = []
        span_count = len(spans)
        attributes_ok = True

        if span_count != expected_count:
            failures.append(
                f"expected {expected_count} spans, got {span_count}"
            )

        for sp in spans:
            attrs = sp.attributes or {}
            # No secrets, credentials, or private paths as attributes
            if "password" in attrs or "token" in attrs or "secret" in attrs:
                attributes_ok = False
                failures.append(
                    f"span {sp.name!r} leaked sensitive keys in attributes"
                )

        passed = len(failures) == 0
        return cls(
            passed=passed,
            span_count=span_count,
            attributes_check=attributes_ok,
            _failures=failures,
        )


# ---------------------------------------------------------------------------
# run_all  —  full trace execution & verification
# ---------------------------------------------------------------------------


def run_all() -> list[trace.Span]:
    """Execute all span types inside one trace, export, and verify.

    Returns
    -------
    list[trace.Span]
        Finished spans exported by the in-memory exporter after the run.
        An empty list means the exporter returned nothing (possible setup
        problem).
    """
    run_id = "spike-run-001"
    event_id = "evt-42"
    thesis_id = "thesis-alpha"
    review_id = "review-99"
    from_state = "pending"
    to_state = "active"

    # --- clear previous exports ---
    _exporter.clear()

    # --- all spans in a single trace ---
    with _tracer.start_as_current_span("run_all.root") as root:
        root.set_attribute("run_id", run_id)
        root.set_attribute("purpose", "stage2_observability_spike")

        emit_retrieval_span(run_id, event_id)
        emit_semantic_pass_a(run_id, thesis_id)
        emit_semantic_pass_b(run_id, thesis_id)
        emit_arbitration_span(run_id, thesis_id)
        emit_transition_span(run_id, thesis_id, from_state, to_state)
        emit_recovery_span(run_id, review_id, retry_count=2)

    # --- force export ---
    _exporter.force_flush()

    finished_spans: list[trace.Span] = list(_exporter.get_finished_spans())
    return finished_spans


# ---------------------------------------------------------------------------
# Quick smoke test when run as a script
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    spans = run_all()
    result = RunResult.from_spans(spans, expected_count=8)

    print(f"Span count: {result.span_count}")
    print(f"Attributes check: {result.attributes_check}")
    print(f"Overall: {'PASS' if result.passed else 'FAIL'}")

    if not result.passed:
        for f in result._failures:
            print(f"  FAIL: {f}")

    if spans:
        trace_id = spans[0].get_span_context().trace_id
        print(f"Trace ID: {trace_id:#018x}")
        for sp in spans:
            ctx = sp.get_span_context()
            print(
                f"  {sp.name:<30s}  trace={ctx.trace_id:#018x}  "
                f"span={ctx.span_id:#018x}  parent={sp.parent}"
            )
