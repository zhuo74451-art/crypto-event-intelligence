"""Cognition v2 domain contract tests."""

import pytest
from pydantic import ValidationError
from datetime import datetime, timezone

from market_radar.cognition_v2.domain.contracts import (
    ClaimRecord,
    EvidenceRecord,
    EventRecord,
    EventRevision,
    ThesisRecord,
    ThesisRevision,
    ReviewIntent,
    EvidenceRef,
    EvidenceStatus,
    ClaimClass,
    Horizon,
    ThesisState,
    ActionType,
    SourceIdentity,
    SourcePermission,
    ExposureLink,
    CounterEvidence,
    AttentionAllocation,
    NotificationDecision,
    ProvenanceEdge,
    HistoricalCaseManifest,
    OutcomeWindow,
    FutureEvidenceBlocker,
    LifecycleTransitionRequest,
    CorrectionType,
    SplitLabel,
    EventFamily,
    MarketRegime,
    RevisionOutcome,
    CANONICAL_EDGES,
    CANONICAL_STATES,
)


NOW = datetime.now(timezone.utc)


@pytest.fixture
def valid_evidence_ref():
    return EvidenceRef(source="test_source", content_hash="abc123", retrieved_at=NOW)


class TestSourceIdentity:
    def test_valid_minimal(self):
        s = SourceIdentity(name="Test Source", source_type="api")
        assert s.name == "Test Source"
        assert s.id is not None

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            SourceIdentity(name="", source_type="api")

    def test_no_trade_fields(self):
        fields = SourceIdentity.model_fields
        for bad in ("trade", "wallet", "order", "position", "leverage"):
            assert bad not in fields, f"Field {bad} must not exist"


class TestEvidenceRecord:
    def test_valid_minimal(self):
        e = EvidenceRecord(source_id="s1", source_name="src", content_hash="abc")
        assert e.content_hash == "abc"

    def test_empty_hash_rejected(self):
        with pytest.raises(ValidationError):
            EvidenceRecord(source_id="s1", source_name="src", content_hash="")

    def test_time_fields(self):
        e = EvidenceRecord(source_id="s1", source_name="src", content_hash="abc",
                           publication_time=NOW, effective_time=NOW,
                           retrieval_time=NOW, assessment_time=NOW)
        assert e.publication_time == NOW
        assert e.effective_time == NOW


class TestEventRecord:
    def test_valid(self):
        e = EventRecord(event_family="regulatory", title="Test event")
        assert e.event_family == EventFamily.REGULATORY

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            EventRecord(event_family="regulatory", title="")

    def test_no_lifecycle_action(self):
        fields = EventRecord.model_fields
        for bad in ("trade_action", "publish", "wallet", "transition_cmd", "lifecycle_state"):
            assert bad not in fields


class TestEventRevision:
    def test_valid(self):
        r = EventRevision(event_id="e1", version=1, revision_body="body",
                          revision_outcome="unchanged", reason="test")
        assert r.version == 1

    def test_version_sequence(self):
        with pytest.raises(ValidationError):
            EventRevision(event_id="e1", version=1, previous_version=2,
                          revision_body="body", revision_outcome="unchanged", reason="test")


class TestThesisRecord:
    def test_valid(self):
        t = ThesisRecord(claim_class="fact", summary="Test thesis")
        assert t.lifecycle_state == ThesisState.DISCOVERED

    def test_no_numeric_confidence(self):
        assert not hasattr(ThesisRecord, "confidence")
        assert not hasattr(ThesisRecord, "confidence_band")

    def test_no_trade_field(self):
        fields = ThesisRecord.model_fields
        for bad in ("trade", "wallet", "publish", "order"):
            assert bad not in fields


class TestThesisRevision:
    def test_valid(self):
        r = ThesisRevision(thesis_id="t1", version=1, revision_body="body",
                          revision_outcome="unchanged", lifecycle_state="DISCOVERED",
                          reason="initial")
        assert r.revision_outcome == RevisionOutcome.UNCHANGED

    def test_version_sequence(self):
        with pytest.raises(ValidationError):
            ThesisRevision(thesis_id="t1", version=1, previous_version=2,
                          revision_body="body", revision_outcome="unchanged",
                          lifecycle_state="DISCOVERED", reason="test")


class TestClaimRecord:
    def test_valid_minimal(self, valid_evidence_ref):
        c = ClaimRecord(claim_class="fact", summary="Test claim",
                       evidence_status="tentative")
        assert c.claim_class == ClaimClass.FACT

    def test_supported_requires_refs(self):
        with pytest.raises(ValidationError):
            ClaimRecord(claim_class="fact", summary="test",
                       evidence_status="supported", evidence_refs=[])

    def test_strong_requires_refs(self):
        with pytest.raises(ValidationError):
            ClaimRecord(claim_class="fact", summary="test",
                       evidence_status="strong", evidence_refs=[])

    def test_insufficient_allows_empty(self):
        c = ClaimRecord(claim_class="fact", summary="test",
                       evidence_status="insufficient", evidence_refs=[])
        assert c.evidence_refs == []

    def test_no_numeric_confidence(self):
        assert not hasattr(ClaimRecord, "confidence")

    def test_empty_summary_rejected(self):
        with pytest.raises(ValidationError):
            ClaimRecord(claim_class="fact", summary="", evidence_status="tentative")


class TestReviewIntent:
    def test_valid(self):
        r = ReviewIntent(thesis_id="t1", idempotency_key="ik1", due_at=NOW)
        assert r.status == "PENDING"
        assert r.checkpoint_step == 0

    def test_idempotency_key_required(self):
        with pytest.raises(ValidationError):
            ReviewIntent(thesis_id="t1", idempotency_key="", due_at=NOW)


class TestActionType:
    def test_only_safe_actions(self):
        values = {m.value for m in ActionType}
        assert values == {"log", "flag", "review", "escalate", "silence"}


class TestNotificationDecision:
    def test_no_trade_fields(self):
        fields = NotificationDecision.model_fields
        for bad in ("trade", "wallet", "publish", "order", "position"):
            assert bad not in fields


class TestProvenanceEdge:
    def test_valid(self):
        e = ProvenanceEdge(source_id="s1", target_id="t1", relationship_type="derived_from")
        assert e.relationship_type == "derived_from"


class TestHistoricalCaseManifest:
    def test_valid_minimal(self):
        m = HistoricalCaseManifest(
            case_id="case_001",
            event_family="regulatory",
            market_regime="unknown",
            split_label="BUILD",
            title="Test case",
            evidence_manifest_hash="abc123",
        )
        assert m.case_id == "case_001"

    def test_deterministic_hash(self):
        m1 = HistoricalCaseManifest(
            case_id="case_001",
            event_family="regulatory",
            market_regime="unknown",
            split_label="BUILD",
            title="Test case",
            evidence_manifest_hash="abc123",
        )
        m2 = HistoricalCaseManifest(
            case_id="case_001",
            event_family="regulatory",
            market_regime="unknown",
            split_label="BUILD",
            title="Test case",
            evidence_manifest_hash="abc123",
        )
        assert m1.deterministic_hash() == m2.deterministic_hash()

    def test_different_inputs_different_hashes(self):
        m1 = HistoricalCaseManifest(
            case_id="case_001", event_family="regulatory",
            market_regime="bull", split_label="BUILD",
            title="Case A", evidence_manifest_hash="abc",
        )
        m2 = HistoricalCaseManifest(
            case_id="case_002", event_family="regulatory",
            market_regime="bear", split_label="DEVELOPMENT",
            title="Case B", evidence_manifest_hash="def",
        )
        assert m1.deterministic_hash() != m2.deterministic_hash()


class TestEventState:
    def test_event_states_separate_from_thesis(self):
        from market_radar.cognition_v2.domain.contracts import EventState
        # Event state values
        event_values = {s.value for s in EventState}
        thesis_values = {s.value for s in ThesisState}
        # Event states should exist but not be the same set
        assert "CONFIRMED" in event_values
        assert "CORRECTED" in event_values
        assert "RETRACTED" in event_values
        assert "SUPERSEDED" in event_values
        # Thesis-specific states should not be event states
        assert "QUALIFYING" not in event_values
        assert "DORMANT" not in event_values

    def test_event_record_uses_event_state(self):
        e = EventRecord(event_family="regulatory", title="Test event")
        assert e.event_state.value == "DISCOVERED"
        assert not hasattr(e, "lifecycle_state")


class TestAbstentionReason:
    def test_valid(self):
        from market_radar.cognition_v2.domain.contracts import AbstentionReason
        r = AbstentionReason(
            claim_class="fact",
            reason_type="missing_evidence",
            description="No evidence available",
        )
        assert r.claim_class == ClaimClass.FACT
        assert r.reason_type == "missing_evidence"

    def test_empty_description_rejected(self):
        from market_radar.cognition_v2.domain.contracts import AbstentionReason
        with pytest.raises(ValidationError):
            AbstentionReason(
                claim_class="fact",
                reason_type="missing_evidence",
                description="",
            )


class TestOutcomeWindow:
    def test_valid(self):
        w = OutcomeWindow(
            window_label="1h",
            event_id="e1",
            open_time=NOW,
            close_time=NOW,
        )
        assert w.window_label == "1h"


class TestFutureEvidenceBlocker:
    def test_no_leak(self):
        blocker = FutureEvidenceBlocker(cutoff_time=NOW, max_allowed_time=NOW)
        early = datetime(2020, 1, 1, tzinfo=timezone.utc)
        assert not blocker.is_leaked(early)

    def test_leak_detected(self):
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        blocker = FutureEvidenceBlocker(cutoff_time=NOW, max_allowed_time=NOW)
        assert blocker.is_leaked(future)

    def test_filter_evidence(self):
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        blocker = FutureEvidenceBlocker(cutoff_time=NOW, max_allowed_time=NOW)
        filtered = blocker.filter_evidence([future, past])
        assert future not in filtered
        assert past in filtered


class TestLifecycleTransitionRequest:
    def test_valid(self):
        req = LifecycleTransitionRequest(
            thesis_id="t1",
            from_state="DISCOVERED",
            to_state="QUALIFYING",
            expected_version=1,
            reason="New evidence",
            idempotency_key="ik1",
        )
        assert req.from_state == ThesisState.DISCOVERED
        assert req.to_state == ThesisState.QUALIFYING

    def test_empty_reason_rejected(self):
        with pytest.raises(ValidationError):
            LifecycleTransitionRequest(
                thesis_id="t1",
                from_state="DISCOVERED",
                to_state="QUALIFYING",
                expected_version=1,
                reason="",
                idempotency_key="ik1",
            )


class TestCanonicalEdges:
    def test_all_states_have_edges(self):
        for state in CANONICAL_STATES:
            assert state in CANONICAL_EDGES, f"State {state.value} missing from edges"

    def test_no_undefined_targets(self):
        all_states = set(CANONICAL_STATES)
        for targets in CANONICAL_EDGES.values():
            for t in targets:
                assert t in all_states, f"Target {t.value} not in CANONICAL_STATES"

    def test_self_loop_active_only(self):
        for state, targets in CANONICAL_EDGES.items():
            if state.value == "ACTIVE":
                assert state in targets
            else:
                assert state not in targets, f"Self-loop not allowed for {state.value}"


class TestHorizon:
    def test_valid_values(self):
        for h in ["immediate", "short_term", "medium_term", "long_term"]:
            assert Horizon(h).value == h


class TestEvidenceStatus:
    def test_valid_values(self):
        for s in ["blocked", "insufficient", "tentative", "supported", "strong"]:
            assert EvidenceStatus(s).value == s


class TestProhibitedFields:
    """Verify no trade/wallet/publish fields exist on key models."""

    MODELS = [EvidenceRecord, EventRecord, ThesisRecord, ClaimRecord,
              NotificationDecision, AttentionAllocation, ReviewIntent]

    def test_no_trade_fields(self):
        for model in self.MODELS:
            fields = model.model_fields
            for bad in ("trade_action", "wallet_address", "order_id",
                        "position_size", "leverage", "publish_now"):
                assert bad not in fields, f"{model.__name__} has {bad}"
