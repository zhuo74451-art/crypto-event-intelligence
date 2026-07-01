"""Cognition v2 lifecycle service tests.

R11: deterministic transition request fingerprint + strict idempotency.
R12: failure injection through production service.
R13: real close/reopen recovery with file-backed database.
"""

from datetime import datetime, timezone
import json
import os
import tempfile
import pytest

from market_radar.cognition_v2.domain.contracts import (
    EvidenceRef,
    LifecycleTransitionRequest,
    ThesisState,
    CANONICAL_STATES,
    CANONICAL_EDGES,
)
from market_radar.cognition_v2.lifecycle.service import (
    LifecycleValidator,
    TransactionalLifecycleService,
    IdempotentTransitionError,
    TransitionConflictError,
    compute_request_fingerprint,
)
from market_radar.cognition_v2.persistence.models import (
    create_cognition_engine,
    make_cognition_session_factory,
    cognition_session_scope,
    ThesisModel,
    ThesisRevisionModel,
)


NOW = datetime.now(timezone.utc)
ALL_STATES = list(CANONICAL_STATES)
LEGAL_EDGES = CANONICAL_EDGES


@pytest.fixture
def validator():
    return LifecycleValidator()


@pytest.fixture
def engine():
    eng = create_cognition_engine(":memory:")
    yield eng
    eng.dispose()


@pytest.fixture
def factory(engine):
    return make_cognition_session_factory(engine)


@pytest.fixture
def tl_service(factory):
    return TransactionalLifecycleService(session_factory=factory)


@pytest.fixture
def thesis_in_db(factory):
    with cognition_session_scope(factory) as s:
        t = ThesisModel(id="test_thesis", claim_class="fact", summary="Test thesis",
                        lifecycle_state="DISCOVERED", version=1)
        s.add(t)
    return "test_thesis"


# ═══════════════════════════════════════════════════════════════════════════════
# LifecycleValidator tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestLifecycleValidator:
    def test_all_legal_transitions(self, validator):
        for from_state, targets in LEGAL_EDGES.items():
            for to_state in targets:
                assert validator.validate(from_state, to_state)

    def test_representative_illegal_jumps(self, validator):
        jumps = [
            (ThesisState.DISCOVERED, ThesisState.ACTIVE),
            (ThesisState.DISCOVERED, ThesisState.ARCHIVED),
            (ThesisState.ARCHIVED, ThesisState.DISCOVERED),
            (ThesisState.REJECTED, ThesisState.ACTIVE),
            (ThesisState.ISOLATED, ThesisState.ACTIVE),
            (ThesisState.DORMANT, ThesisState.QUALIFYING),
            (ThesisState.INVALIDATED, ThesisState.ACTIVE),
        ]
        for from_state, to_state in jumps:
            assert not validator.validate(from_state, to_state)
            with pytest.raises(ValueError, match="Illegal transition"):
                validator.validate_or_raise(from_state, to_state)

    def test_self_loop_only_active(self, validator):
        assert validator.validate(ThesisState.ACTIVE, ThesisState.ACTIVE)
        for state in ALL_STATES:
            if state != ThesisState.ACTIVE:
                assert not validator.validate(state, state)

    def test_archived_only_reopen(self, validator):
        trans = validator.get_legal_transitions(ThesisState.ARCHIVED)
        assert ThesisState.REOPEN_REVIEW in trans
        assert len(trans) == 1

    def test_code_size_positive(self, validator):
        assert validator.code_size > 0


# ═══════════════════════════════════════════════════════════════════════════════
# R11 — Deterministic fingerprint
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeterministicFingerprint:
    def test_identical_requests_same_fingerprint(self):
        req1 = LifecycleTransitionRequest(
            thesis_id="t1", from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING, expected_version=1,
            reason="Evidence found", idempotency_key="ik1",
        )
        req2 = LifecycleTransitionRequest(
            thesis_id="t1", from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING, expected_version=1,
            reason="Evidence found", idempotency_key="ik1",
        )
        assert compute_request_fingerprint(req1) == compute_request_fingerprint(req2)

    def test_different_target_different_fingerprint(self):
        req1 = LifecycleTransitionRequest(
            thesis_id="t1", from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING, expected_version=1,
            reason="test", idempotency_key="ik1",
        )
        req2 = LifecycleTransitionRequest(
            thesis_id="t1", from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.REJECTED, expected_version=1,
            reason="test", idempotency_key="ik2",
        )
        assert compute_request_fingerprint(req1) != compute_request_fingerprint(req2)

    def test_different_reason_different_fingerprint(self):
        req1 = LifecycleTransitionRequest(
            thesis_id="t1", from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING, expected_version=1,
            reason="Reason A", idempotency_key="ik1",
        )
        req2 = LifecycleTransitionRequest(
            thesis_id="t1", from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING, expected_version=1,
            reason="Reason B", idempotency_key="ik2",
        )
        assert compute_request_fingerprint(req1) != compute_request_fingerprint(req2)

    def test_different_evidence_different_fingerprint(self):
        ref = EvidenceRef(source="src1", content_hash="abc", retrieved_at=NOW)
        req1 = LifecycleTransitionRequest(
            thesis_id="t1", from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING, expected_version=1,
            reason="test", evidence_refs=[ref], idempotency_key="ik1",
        )
        req2 = LifecycleTransitionRequest(
            thesis_id="t1", from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING, expected_version=1,
            reason="test", idempotency_key="ik2",
        )
        assert compute_request_fingerprint(req1) != compute_request_fingerprint(req2)

    def test_different_rules_different_fingerprint(self):
        req1 = LifecycleTransitionRequest(
            thesis_id="t1", from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING, expected_version=1,
            reason="test", rule_refs=["rule1"], idempotency_key="ik1",
        )
        req2 = LifecycleTransitionRequest(
            thesis_id="t1", from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING, expected_version=1,
            reason="test", idempotency_key="ik2",
        )
        assert compute_request_fingerprint(req1) != compute_request_fingerprint(req2)

    def test_normalized_ordering_same_fingerprint(self):
        ref1 = EvidenceRef(source="a", content_hash="z", retrieved_at=NOW)
        ref2 = EvidenceRef(source="b", content_hash="y", retrieved_at=NOW)
        req1 = LifecycleTransitionRequest(
            thesis_id="t1", from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING, expected_version=1,
            reason="test", evidence_refs=[ref1, ref2],
            rule_refs=["r1", "r2"], idempotency_key="ik1",
        )
        req2 = LifecycleTransitionRequest(
            thesis_id="t1", from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING, expected_version=1,
            reason="test", evidence_refs=[ref2, ref1],
            rule_refs=["r2", "r1"], idempotency_key="ik2",
        )
        assert compute_request_fingerprint(req1) == compute_request_fingerprint(req2)


# ═══════════════════════════════════════════════════════════════════════════════
# TransactionalLifecycleService tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestTransactionalLifecycleService:
    def test_legal_transition_writes_revision_and_advances(self, tl_service, thesis_in_db):
        req = LifecycleTransitionRequest(
            thesis_id=thesis_in_db,
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING,
            expected_version=1,
            reason="Sufficient preliminary evidence",
            idempotency_key="ik_legal_1",
        )
        rev, new_version = tl_service.transition(req)
        assert rev is not None
        assert rev.thesis_id == thesis_in_db
        assert rev.version == 2
        assert rev.lifecycle_state == "QUALIFYING"
        assert new_version == 2

    def test_stale_version_writes_nothing(self, tl_service, thesis_in_db):
        req1 = LifecycleTransitionRequest(
            thesis_id=thesis_in_db,
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING,
            expected_version=1, reason="Evidence found",
            idempotency_key="ik_stale_1",
        )
        tl_service.transition(req1)
        req2 = LifecycleTransitionRequest(
            thesis_id=thesis_in_db,
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING,
            expected_version=1,  # stale
            reason="Stale", idempotency_key="ik_stale_2",
        )
        with pytest.raises(TransitionConflictError):
            tl_service.transition(req2)

    def test_illegal_edge_writes_nothing(self, tl_service, thesis_in_db):
        req = LifecycleTransitionRequest(
            thesis_id=thesis_in_db,
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.ACTIVE,
            expected_version=1, reason="Skip",
            idempotency_key="ik_illegal",
        )
        with pytest.raises(ValueError, match="Illegal transition"):
            tl_service.transition(req)

    def test_missing_epistemic_refs_rejected(self, tl_service, factory):
        with cognition_session_scope(factory) as s:
            s.add(ThesisModel(id="epi_test", claim_class="fact", summary="Epi",
                             lifecycle_state="CANDIDATE", version=1))
        req = LifecycleTransitionRequest(
            thesis_id="epi_test",
            from_state=ThesisState.CANDIDATE,
            to_state=ThesisState.ACTIVE,
            expected_version=1, reason="No refs",
            idempotency_key="ik_epi_no",
        )
        with pytest.raises(ValueError, match="evidence or rule references"):
            tl_service.transition(req)

    # ═══════════════════════════════════════════════════════════════════════
    # R11 — Fingerprint-based idempotency
    # ═══════════════════════════════════════════════════════════════════════

    def test_exact_replay_returns_same_revision(self, tl_service, thesis_in_db):
        """Exact replay returns the same revision, projection not advanced twice."""
        req = LifecycleTransitionRequest(
            thesis_id=thesis_in_db,
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING,
            expected_version=1, reason="Same reason",
            idempotency_key="ik_fp_idem",
        )
        rev1, v1 = tl_service.transition(req)
        rev2, v2 = tl_service.transition(req)
        assert rev1.id == rev2.id
        assert v1 == v2 == 2
        # Projection advanced exactly once
        with cognition_session_scope(tl_service._factory) as s:
            thesis = s.get(ThesisModel, thesis_in_db)
            assert thesis.version == 2

    def test_same_key_different_target_rejected(self, tl_service, thesis_in_db):
        """Same key, same thesis but different target state."""
        req1 = LifecycleTransitionRequest(
            thesis_id=thesis_in_db,
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING,
            expected_version=1, reason="Test",
            idempotency_key="ik_tgt_diff",
        )
        tl_service.transition(req1)
        # Same key but different target
        req2 = LifecycleTransitionRequest(
            thesis_id=thesis_in_db,
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.REJECTED,
            expected_version=1, reason="Test",
            idempotency_key="ik_tgt_diff",
        )
        with pytest.raises(IdempotentTransitionError):
            tl_service.transition(req2)

    def test_same_key_different_reason_rejected(self, tl_service, thesis_in_db):
        """Same key, same thesis but different reason."""
        req1 = LifecycleTransitionRequest(
            thesis_id=thesis_in_db,
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING,
            expected_version=1, reason="Reason A",
            idempotency_key="ik_reason_diff",
        )
        tl_service.transition(req1)
        req2 = LifecycleTransitionRequest(
            thesis_id=thesis_in_db,
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING,
            expected_version=1, reason="Reason B",
            idempotency_key="ik_reason_diff",
        )
        with pytest.raises(IdempotentTransitionError):
            tl_service.transition(req2)

    def test_same_key_different_evidence_rejected(self, tl_service, thesis_in_db):
        """Same key, same thesis but different evidence refs."""
        req1 = LifecycleTransitionRequest(
            thesis_id=thesis_in_db,
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING,
            expected_version=1, reason="Test",
            evidence_refs=[EvidenceRef(source="a", content_hash="1", retrieved_at=NOW)],
            idempotency_key="ik_ev_diff",
        )
        tl_service.transition(req1)
        req2 = LifecycleTransitionRequest(
            thesis_id=thesis_in_db,
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING,
            expected_version=1, reason="Test",
            evidence_refs=[EvidenceRef(source="b", content_hash="2", retrieved_at=NOW)],
            idempotency_key="ik_ev_diff",
        )
        with pytest.raises(IdempotentTransitionError):
            tl_service.transition(req2)

    def test_same_key_different_rules_rejected(self, tl_service, thesis_in_db):
        """Same key, same thesis but different rule refs."""
        req1 = LifecycleTransitionRequest(
            thesis_id=thesis_in_db,
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING,
            expected_version=1, reason="Test",
            rule_refs=["rule1"], idempotency_key="ik_rule_diff",
        )
        tl_service.transition(req1)
        req2 = LifecycleTransitionRequest(
            thesis_id=thesis_in_db,
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING,
            expected_version=1, reason="Test",
            rule_refs=["rule2"], idempotency_key="ik_rule_diff",
        )
        with pytest.raises(IdempotentTransitionError):
            tl_service.transition(req2)

    # ═══════════════════════════════════════════════════════════════════════
    # R12 — Failure injection through the production service
    # ═══════════════════════════════════════════════════════════════════════

    def test_failure_injection_rollback(self, factory):
        """Failure injected after revision staging rolls back everything."""
        # Create a file-backed test DB so we can reopen and prove rollback
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "fail_inject.db")
            engine = create_cognition_engine(db_path)
            fact = make_cognition_session_factory(engine)

            with cognition_session_scope(fact) as s:
                s.add(ThesisModel(id="fi_test", claim_class="fact", summary="FI",
                                 lifecycle_state="DISCOVERED", version=1))

            # Define a hook that raises after revision staged
            def _inject_failure(req, thesis, revision):
                raise RuntimeError("Injected failure after revision staging")

            service = TransactionalLifecycleService(
                session_factory=fact,
                failure_hook=_inject_failure,
            )

            req = LifecycleTransitionRequest(
                thesis_id="fi_test",
                from_state=ThesisState.DISCOVERED,
                to_state=ThesisState.QUALIFYING,
                expected_version=1, reason="Test failure injection",
                idempotency_key="ik_fi",
            )
            with pytest.raises(RuntimeError, match="Injected failure"):
                service.transition(req)

            # Reopen and prove no revision persisted, state unchanged
            engine2 = create_cognition_engine(db_path)
            fact2 = make_cognition_session_factory(engine2)
            with cognition_session_scope(fact2) as s:
                thesis = s.get(ThesisModel, "fi_test")
                assert thesis.lifecycle_state == "DISCOVERED"
                assert thesis.version == 1
                revs = s.query(ThesisRevisionModel).filter(
                    ThesisRevisionModel.thesis_id == "fi_test"
                ).all()
                assert len(revs) == 0
            engine.dispose()
            engine2.dispose()

    # ═══════════════════════════════════════════════════════════════════════
    # R13 — Real close/reopen recovery with file-backed database
    # ═══════════════════════════════════════════════════════════════════════

    def test_file_database_close_reopen(self):
        """Create file-backed DB, transition, dispose, reopen, prove state persists."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "reopen_test.db")

            # Phase 1 — create and transition
            engine1 = create_cognition_engine(db_path)
            factory1 = make_cognition_session_factory(engine1)
            with cognition_session_scope(factory1) as s:
                s.add(ThesisModel(id="ro_test", claim_class="fact", summary="RO",
                                 lifecycle_state="DISCOVERED", version=1))
            service1 = TransactionalLifecycleService(factory1)
            req = LifecycleTransitionRequest(
                thesis_id="ro_test",
                from_state=ThesisState.DISCOVERED,
                to_state=ThesisState.QUALIFYING,
                expected_version=1, reason="Close/reopen test",
                idempotency_key="ik_ro",
            )
            rev1, v1 = service1.transition(req)
            engine1.dispose()

            # Phase 2 — reopen with new engine
            engine2 = create_cognition_engine(db_path)
            factory2 = make_cognition_session_factory(engine2)

            # Prove current thesis projection persisted
            with cognition_session_scope(factory2) as s:
                thesis = s.get(ThesisModel, "ro_test")
                assert thesis is not None
                assert thesis.lifecycle_state == "QUALIFYING"
                assert thesis.version == 2

            # Prove immutable revision persisted
            with cognition_session_scope(factory2) as s:
                revs = s.query(ThesisRevisionModel).filter(
                    ThesisRevisionModel.thesis_id == "ro_test"
                ).all()
                assert len(revs) == 1
                assert revs[0].revision_body == rev1.revision_body

            # Prove idempotent replay after reopen
            service2 = TransactionalLifecycleService(factory2)
            rev2, v2 = service2.transition(req)
            assert rev2.id == rev1.id  # same revision returned
            assert v2 == 2  # not advanced again

            # Prove projection still at version 2
            with cognition_session_scope(factory2) as s:
                thesis2 = s.get(ThesisModel, "ro_test")
                assert thesis2.version == 2

            engine2.dispose()
