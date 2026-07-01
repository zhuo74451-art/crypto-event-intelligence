"""Test OpenTelemetry observability — in-memory exporter, data minimization."""

from experiments.stage2_foundation_spike.otel_spike import run_all


def test_run_all_completes():
    spans = run_all()
    assert len(spans) > 0


def test_contains_semantic_passes():
    spans = run_all()
    names = {s.name for s in spans}
    assert "semantic.synthesis" in names
    assert "semantic.risk_challenge" in names


def test_all_spans_have_run_id():
    spans = run_all()
    for s in spans:
        rid = s.attributes.get("run_id")
        assert rid is not None, f"span {s.name} missing run_id"
        assert isinstance(rid, str)


def test_cognition_spans_have_thesis_id():
    spans = run_all()
    for s in spans:
        if "retrieval" not in s.name.lower() and "root" not in s.name.lower() and "recovery" not in s.name.lower():
            tid = s.attributes.get("thesis_id")
            assert tid is not None, f"span {s.name} missing thesis_id"


def test_no_evidence_body_in_attributes():
    spans = run_all()
    for s in spans:
        for key in s.attributes:
            assert "evidence" not in key.lower() or "body" not in key.lower(), f"evidence body leaked in {s.name}:{key}"


def test_recovery_span_has_retry_count():
    spans = run_all()
    recovery = [s for s in spans if "recovery" in s.name.lower()]
    assert len(recovery) >= 1
    for s in recovery:
        assert s.attributes.get("retry_count") is not None
