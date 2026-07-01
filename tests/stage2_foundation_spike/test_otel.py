"""Test OpenTelemetry observability."""

import pytest
from experiments.stage2_foundation_spike.otel_spike import (
    run_all,
    RunResult,
    emit_retrieval_span,
    emit_semantic_pass_a,
    emit_semantic_pass_b,
    emit_arbitration_span,
    emit_transition_span,
    emit_recovery_span,
    TracerProvider,
    SimpleSpanProcessor,
    InMemorySpanExporter,
)


class TestRunAll:
    def test_run_all_completes(self):
        spans = run_all()
        assert len(spans) > 0

    def test_run_all_contains_semantic_passes(self):
        spans = run_all()
        names = {s.name for s in spans}
        assert any("semantic" in n.lower() or "pass" in n.lower() for n in names)


class TestSpansHaveRunId:
    def test_all_spans_have_run_id(self):
        spans = run_all()
        for s in spans:
            run_id = s.attributes.get("run_id")
            assert run_id is not None, f"span {s.name} missing run_id"
            assert isinstance(run_id, str)


class TestDataMinimisation:
    def test_no_evidence_body_in_spans(self):
        spans = run_all()
        for s in spans:
            for attr_name in s.attributes:
                assert "evidence" not in attr_name.lower() or "body" not in attr_name.lower()


class TestSpansHaveThesisId:
    def test_cognition_spans_have_thesis_id(self):
        spans = run_all()
        # Skip root span and infrastructure spans (retrieval, recovery)
        cognition_spans = [s for s in spans
                          if s.name not in ('run_all.root',) 
                          and 'retrieval' not in s.name.lower()
                          and 'recovery' not in s.name.lower()]
        for s in cognition_spans:
            tid = s.attributes.get("thesis_id")
            assert tid is not None, f"span {s.name} missing thesis_id"
