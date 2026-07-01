"""Cognition v2 persistence and migration tests."""

import os
import tempfile
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from market_radar.cognition_v2.persistence.models import (
    Base,
    create_cognition_engine,
    make_cognition_session_factory,
    cognition_session_scope,
    compare_and_swap_thesis,
    block_revision_modification,
    StaleVersionError,
    SourceModel,
    EvidenceModel,
    EventModel,
    EventRevisionModel,
    ThesisModel,
    ThesisRevisionModel,
    ClaimModel,
    ReviewIntentModel,
    HistoricalCaseModel,
    OutcomeWindowModel,
)
from market_radar.cognition_v2.persistence import alembic_helpers


NOW = datetime.now(timezone.utc)


class TestModelCreation:
    def test_all_tables_created(self):
        engine = create_cognition_engine(":memory:")
        tables = Base.metadata.tables
        expected = {"sources", "source_health", "evidence", "events", "event_revisions",
                    "theses", "thesis_revisions", "claims", "exposure_links",
                    "counter_evidence", "review_intents", "attention_allocations",
                    "notification_decisions", "provenance_edges", "historical_cases",
                    "outcome_windows", "run_records", "configuration_versions"}
        for name in expected:
            assert name in tables, f"Missing table: {name}"
        engine.dispose()


class TestForeignKey:
    def test_foreign_key_enforced(self):
        engine = create_cognition_engine(":memory:")
        factory = make_cognition_session_factory(engine)
        with pytest.raises(IntegrityError):
            with cognition_session_scope(factory) as s:
                r = ReviewIntentModel(
                    id="fk_test", thesis_id="nonexistent",
                    idempotency_key="ik1", due_at=NOW,
                )
                s.add(r)
        engine.dispose()


class TestUniqueIdempotencyKey:
    def test_duplicate_rejected(self):
        engine = create_cognition_engine(":memory:")
        factory = make_cognition_session_factory(engine)
        with cognition_session_scope(factory) as s:
            s.add(ThesisModel(id="t_ik", claim_class="fact", summary="t",
                             lifecycle_state="DISCOVERED"))
        with cognition_session_scope(factory) as s:
            s.add(ReviewIntentModel(id="r1", thesis_id="t_ik",
                                   idempotency_key="dup", due_at=NOW))
        with pytest.raises(IntegrityError):
            with cognition_session_scope(factory) as s:
                s.add(ReviewIntentModel(id="r2", thesis_id="t_ik",
                                       idempotency_key="dup", due_at=NOW))
        engine.dispose()


class TestTransactionRollback:
    def test_rollback(self):
        engine = create_cognition_engine(":memory:")
        factory = make_cognition_session_factory(engine)
        try:
            with cognition_session_scope(factory) as s:
                s.add(ThesisModel(id="rb1", claim_class="fact", summary="rb",
                                 lifecycle_state="DISCOVERED"))
                s.add(ThesisModel(id="rb1", claim_class="fact", summary="dup",
                                 lifecycle_state="DISCOVERED"))  # duplicate PK
        except Exception:
            pass
        # Verify rollback — no rows persisted
        with cognition_session_scope(factory) as s:
            count = s.query(ThesisModel).count()
            assert count == 0, f"Expected 0 rows after rollback, got {count}"
        engine.dispose()


class TestCloseReopen:
    def test_close_and_reopen_recovers_state(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            engine = create_cognition_engine(db_path)
            factory = make_cognition_session_factory(engine)
            with cognition_session_scope(factory) as s:
                s.add(ThesisModel(id="cr1", claim_class="fact", summary="cr",
                                 lifecycle_state="DISCOVERED"))
            engine.dispose()
            # Reopen
            engine2 = create_cognition_engine(db_path)
            factory2 = make_cognition_session_factory(engine2)
            with cognition_session_scope(factory2) as s:
                t = s.get(ThesisModel, "cr1")
                assert t is not None
                assert t.summary == "cr"
            engine2.dispose()


class TestCompareAndSwap:
    def test_correct_version_succeeds(self):
        engine = create_cognition_engine(":memory:")
        factory = make_cognition_session_factory(engine)
        with cognition_session_scope(factory) as s:
            s.add(ThesisModel(id="cas1", claim_class="fact", summary="orig",
                             lifecycle_state="DISCOVERED", version=1))
        rows = compare_and_swap_thesis(factory, "cas1", 1, {"summary": "updated"})
        assert rows == 1
        with cognition_session_scope(factory) as s:
            t = s.get(ThesisModel, "cas1")
            assert t.summary == "updated"
            assert t.version == 2
        engine.dispose()

    def test_stale_version_raises(self):
        engine = create_cognition_engine(":memory:")
        factory = make_cognition_session_factory(engine)
        with cognition_session_scope(factory) as s:
            s.add(ThesisModel(id="cas2", claim_class="fact", summary="orig",
                             lifecycle_state="DISCOVERED", version=1))
        compare_and_swap_thesis(factory, "cas2", 1, {"summary": "v2"})
        with pytest.raises(StaleVersionError):
            compare_and_swap_thesis(factory, "cas2", 1, {"summary": "stale"})
        engine.dispose()


class TestRevisionImmutability:
    def test_append_only_revisions(self):
        engine = create_cognition_engine(":memory:")
        factory = make_cognition_session_factory(engine)
        with cognition_session_scope(factory) as s:
            s.add(ThesisModel(id="t_ar", claim_class="fact", summary="t",
                             lifecycle_state="DISCOVERED"))
        with cognition_session_scope(factory) as s:
            s.add(ThesisRevisionModel(id="ar1", thesis_id="t_ar", version=1,
                                     revision_body="v1", revision_outcome="unchanged",
                                     lifecycle_state="DISCOVERED", reason="initial"))
        with cognition_session_scope(factory) as s:
            s.add(ThesisRevisionModel(id="ar2", thesis_id="t_ar", version=2,
                                     revision_body="v2", revision_outcome="strengthened",
                                     lifecycle_state="ACTIVE", reason="new evidence"))
        with engine.connect() as c:
            vs = [r[0] for r in c.execute(
                text("SELECT version FROM thesis_revisions WHERE thesis_id='t_ar' ORDER BY version")
            )]
        assert vs == [1, 2]
        engine.dispose()

    def test_duplicate_revision_version_rejected(self):
        engine = create_cognition_engine(":memory:")
        factory = make_cognition_session_factory(engine)
        with cognition_session_scope(factory) as s:
            s.add(ThesisModel(id="t_dr", claim_class="fact", summary="t",
                             lifecycle_state="DISCOVERED"))
        with cognition_session_scope(factory) as s:
            s.add(ThesisRevisionModel(id="dr1", thesis_id="t_dr", version=1,
                                     revision_body="v1", revision_outcome="unchanged",
                                     lifecycle_state="DISCOVERED", reason="initial"))
        with pytest.raises(IntegrityError):
            with cognition_session_scope(factory) as s:
                s.add(ThesisRevisionModel(id="dr2", thesis_id="t_dr", version=1,
                                         revision_body="v1_dup",
                                         revision_outcome="unchanged",
                                         lifecycle_state="DISCOVERED",
                                         reason="dup"))
        engine.dispose()


class TestAlembicMigration:
    def test_upgrade_creates_tables(self):
        import os
        alembic_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "market_radar", "cognition_v2", "persistence", "alembic",
        )
        result = alembic_helpers.verify_alembic_upgrade(alembic_dir)
        assert result is True


class TestHistoricalCaseUniqueness:
    def test_unique_case_id(self):
        engine = create_cognition_engine(":memory:")
        factory = make_cognition_session_factory(engine)
        with cognition_session_scope(factory) as s:
            s.add(HistoricalCaseModel(id="hc1", case_id="case_001",
                                     event_family="regulatory",
                                     split_label="BUILD", title="Test",
                                     evidence_manifest_hash="abc"))
        with pytest.raises(IntegrityError):
            with cognition_session_scope(factory) as s:
                s.add(HistoricalCaseModel(id="hc2", case_id="case_001",
                                         event_family="regulatory",
                                         split_label="BLIND", title="Test",
                                         evidence_manifest_hash="abc"))
        engine.dispose()
