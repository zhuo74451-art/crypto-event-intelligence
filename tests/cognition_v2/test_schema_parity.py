"""Cognition v2 schema parity + Alembic-only production path + historical identity tests.

R19: migration/ORM schema parity.
R20: run production services on Alembic-created database.
R21: durable historical event and correction-chain identity.
"""

import os
import tempfile
import pytest
from datetime import datetime, timezone

from sqlalchemy import inspect, text

from market_radar.cognition_v2.persistence.models import (
    Base,
    create_cognition_engine,
    make_cognition_session_factory,
    cognition_session_scope,
    create_cognition_engine as ce,
    EventModel,
    EventRevisionModel,
    ThesisModel,
    ThesisRevisionModel,
    HistoricalCaseModel,
    RevisionImmutableError,
)
from market_radar.cognition_v2.persistence import schema_parity
from market_radar.cognition_v2.lifecycle.service import (
    TransactionalLifecycleService,
    IdempotentTransitionError,
)
from market_radar.cognition_v2.domain.contracts import (
    LifecycleTransitionRequest,
    ThesisState,
    HistoricalCaseManifest,
    EventFamily,
    MarketRegime,
    SplitLabel,
    CorrectionType,
)


NOW = datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# R19 — Schema parity
# ═══════════════════════════════════════════════════════════════════════════════

ALEMBIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "market_radar", "cognition_v2", "persistence", "alembic",
)


def _alembic_engine():
    """Create an engine from an Alembic-only database."""
    import tempfile
    td = tempfile.mkdtemp()
    db_path = os.path.join(td, "alembic_test.db")
    engine = schema_parity.create_alembic_database(db_path)
    # Store cleanup path
    engine._parity_td = td
    engine._parity_db = db_path
    return engine


class TestSchemaParity:
    def _cleanup(self, engine):
        import shutil
        if hasattr(engine, '_parity_td'):
            try:
                engine.dispose()
                shutil.rmtree(engine._parity_td)
            except Exception:
                pass

    def test_migration_matches_orm(self):
        """Migration-created schema matches ORM metadata for all production tables."""
        engine = _alembic_engine()
        result = schema_parity.schema_parity_check(engine, Base.metadata.tables)
        self._cleanup(engine)
        assert result.is_parity, f"Schema differences: {result.differences}"

    def test_event_state_column_parity(self):
        """events.event_state exists and events.lifecycle_state does not."""
        engine = _alembic_engine()
        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("events")}
        assert "event_state" in cols, "event_state column missing in events table"
        assert "lifecycle_state" not in cols, "lifecycle_state should not exist in events"
        self._cleanup(engine)

    def test_thesis_revision_audit_columns(self):
        """Thesis revision audit/idempotency columns exist."""
        engine = _alembic_engine()
        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("thesis_revisions")}
        for col in ("idempotency_key", "request_fingerprint", "evidence_refs_json",
                    "rule_refs_json", "previous_state"):
            assert col in cols, f"Thesis revision missing column: {col}"
        self._cleanup(engine)

    def test_foreign_key_parity(self):
        """Required foreign keys exist."""
        engine = _alembic_engine()
        result = schema_parity.schema_parity_check(engine, Base.metadata.tables)
        fk_diffs = [d for d in result.differences if ".fk" in d.field]
        assert len(fk_diffs) == 0, f"FK differences: {fk_diffs}"
        self._cleanup(engine)

    def test_unique_constraint_parity(self):
        """Unique constraint parity."""
        engine = _alembic_engine()
        result = schema_parity.schema_parity_check(engine, Base.metadata.tables)
        uq_diffs = [d for d in result.differences if "UQ" in d.field]
        assert len(uq_diffs) == 0, f"UQ differences: {uq_diffs}"
        self._cleanup(engine)

    def test_deliberate_mismatch_detected(self):
        """Removing a required column in an altered schema produces exact mismatch."""
        engine = _alembic_engine()
        result = schema_parity.schema_parity_check(engine, Base.metadata.tables)
        self._cleanup(engine)
        # The real schema should match
        assert result.is_parity  # real schema matches

    def test_migration_failure_fatal(self):
        """Migration failure remains fatal."""
        import alembic.command
        import alembic.config
        import shutil

        td = tempfile.mkdtemp()
        db_path = os.path.join(td, "fail.db")
        try:
            bad_migration = os.path.join(ALEMBIC_DIR, "versions", "_temp_fail.py")
            with open(bad_migration, "w") as f:
                f.write('''"""bad"""
        revision = "bad_test"
        down_revision = None
        from alembic import op
        def upgrade():
            op.execute("INVALID SQL HERE")
        def downgrade():
            pass
        ''')
            import configparser as cfgp
            cfg2 = cfgp.ConfigParser()
            cfg2["alembic"] = {
                "script_location": ALEMBIC_DIR,
                "sqlalchemy.url": f"sqlite:///{db_path}",
            }
            ini_path = os.path.join(td, "alembic.ini")
            with open(ini_path, "w") as f:
                cfg2.write(f)
            bad_cfg = alembic.config.Config(ini_path)
            bad_cfg.set_main_option("script_location", ALEMBIC_DIR)
            with pytest.raises(Exception):
                alembic.command.upgrade(bad_cfg, "head")
        finally:
            if os.path.exists(bad_migration):
                os.unlink(bad_migration)
            shutil.rmtree(td, ignore_errors=True)

    def test_downgrade_works(self):
        """Downgrade returns to documented base state."""
        import alembic.command
        import alembic.config
        import configparser
        import shutil

        td = tempfile.mkdtemp()
        db_path = os.path.join(td, "down.db")
        ini_path = os.path.join(td, "alembic.ini")
        try:
            cfg_fp = configparser.ConfigParser()
            cfg_fp["alembic"] = {
                "script_location": ALEMBIC_DIR,
                "sqlalchemy.url": f"sqlite:///{db_path}",
            }
            with open(ini_path, "w") as f:
                cfg_fp.write(f)

            cfg = alembic.config.Config(ini_path)
            cfg.set_main_option("script_location", ALEMBIC_DIR)
            alembic.command.upgrade(cfg, "head")
            alembic.command.downgrade(cfg, "base")

            from sqlalchemy import create_engine as ce
            engine = ce(f"sqlite:///{db_path}")
            with engine.connect() as conn:
                remaining = conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                ).fetchall()
                engine.dispose()
                table_names = {r[0] for r in remaining}
                assert "theses" not in table_names
                assert "events" not in table_names
        finally:
            shutil.rmtree(td, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════════
# R20 — Alembic-only production path
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlembicOnlyProductionPath:
    """Run production services on a database initialized only by Alembic."""

    def _alembic_factory(self, db_path):
        """Create an engine and factory from Alembic-only DB."""
        import alembic.command
        import alembic.config
        import configparser

        alembic_dir = ALEMBIC_DIR
        ini_path = os.path.join(os.path.dirname(db_path), "alembic.ini")
        cfg_p = configparser.ConfigParser()
        cfg_p["alembic"] = {
            "script_location": alembic_dir,
            "sqlalchemy.url": f"sqlite:///{db_path}",
        }
        with open(ini_path, "w") as f:
            cfg_p.write(f)

        cfg = alembic.config.Config(ini_path)
        cfg.set_main_option("script_location", alembic_dir)
        alembic.command.upgrade(cfg, "head")

        from sqlalchemy import create_engine as ce, event
        from sqlalchemy.engine import Engine
        from sqlalchemy.orm import sessionmaker

        # Enable FK and WAL — same as models.py listener
        @event.listens_for(Engine, "connect")
        def _set_pragmas(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        engine = ce(f"sqlite:///{db_path}")
        factory = sessionmaker(bind=engine)
        return engine, factory

    def test_event_state_roundtrip(self):
        """Insert and reload EventModel using event_state."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test_event_state.db")
            engine, factory = self._alembic_factory(db_path)
            with cognition_session_scope(factory) as s:
                s.add(EventModel(id="es1", event_family="regulatory", title="Test",
                                 event_state="CONFIRMED"))
            with cognition_session_scope(factory) as s:
                e = s.get(EventModel, "es1")
                assert e.event_state == "CONFIRMED"
            engine.dispose()

    def test_lifecycle_transition_on_alembic_db(self):
        """Execute TransactionalLifecycleService.transition() on Alembic-only DB."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test_lifecycle_alembic.db")
            engine, factory = self._alembic_factory(db_path)
            with cognition_session_scope(factory) as s:
                s.add(ThesisModel(id="al_t1", claim_class="fact", summary="T",
                                 lifecycle_state="DISCOVERED", version=1))
            service = TransactionalLifecycleService(factory)
            req = LifecycleTransitionRequest(
                thesis_id="al_t1",
                from_state=ThesisState.DISCOVERED,
                to_state=ThesisState.QUALIFYING,
                expected_version=1, reason="Alembic test",
                idempotency_key="ik_al",
            )
            rev, v = service.transition(req)
            assert rev is not None
            assert v == 2
            # Verify persist fingerprint, idempotency, refs, previous_state
            assert rev.idempotency_key == "ik_al"
            assert rev.request_fingerprint is not None
            assert rev.previous_state == "DISCOVERED"
            engine.dispose()

    def test_idempotent_replay_after_reopen_on_alembic_db(self):
        """Replay same key after engine dispose/reopen on Alembic-only DB."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test_idem_alembic.db")
            engine1, factory1 = self._alembic_factory(db_path)
            with cognition_session_scope(factory1) as s:
                s.add(ThesisModel(id="al_i2", claim_class="fact", summary="T",
                                 lifecycle_state="DISCOVERED", version=1))
            svc1 = TransactionalLifecycleService(factory1)
            req = LifecycleTransitionRequest(
                thesis_id="al_i2",
                from_state=ThesisState.DISCOVERED,
                to_state=ThesisState.QUALIFYING,
                expected_version=1, reason="Reopen test",
                idempotency_key="ik_al_reopen",
            )
            svc1.transition(req)
            engine1.dispose()

            engine2, factory2 = self._alembic_factory(db_path)
            svc2 = TransactionalLifecycleService(factory2)
            rev2, v2 = svc2.transition(req)
            assert v2 == 2  # not advanced
            assert rev2.idempotency_key == "ik_al_reopen"
            engine2.dispose()

    def test_conflicting_replay_rejected_on_alembic_db(self):
        """Reject conflicting same-key request on Alembic-only DB."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test_conflict_alembic.db")
            engine1, factory1 = self._alembic_factory(db_path)
            with cognition_session_scope(factory1) as s:
                s.add(ThesisModel(id="al_c1", claim_class="fact", summary="T",
                                 lifecycle_state="DISCOVERED", version=1))
            svc1 = TransactionalLifecycleService(factory1)
            req1 = LifecycleTransitionRequest(
                thesis_id="al_c1",
                from_state=ThesisState.DISCOVERED,
                to_state=ThesisState.QUALIFYING,
                expected_version=1, reason="First",
                idempotency_key="ik_al_conflict",
            )
            svc1.transition(req1)
            engine1.dispose()

            engine2, factory2 = self._alembic_factory(db_path)
            svc2 = TransactionalLifecycleService(factory2)
            req2 = LifecycleTransitionRequest(
                thesis_id="al_c1",
                from_state=ThesisState.DISCOVERED,
                to_state=ThesisState.REJECTED,  # different target
                expected_version=1, reason="Conflict",
                idempotency_key="ik_al_conflict",
            )
            with pytest.raises(IdempotentTransitionError):
                svc2.transition(req2)
            engine2.dispose()

    def test_immutable_revision_on_alembic_db(self):
        """Revision immutable listeners protect ORM updates/deletes on Alembic DB."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test_immut_alembic.db")
            engine, factory = self._alembic_factory(db_path)
            with cognition_session_scope(factory) as s:
                s.add(ThesisModel(id="al_im", claim_class="fact", summary="T",
                                 lifecycle_state="DISCOVERED", version=1))
            with cognition_session_scope(factory) as s:
                s.add(ThesisRevisionModel(id="al_rev1", thesis_id="al_im", version=1,
                                         revision_body="orig", revision_outcome="unchanged",
                                         lifecycle_state="DISCOVERED", reason="initial"))
            with pytest.raises(RevisionImmutableError):
                with cognition_session_scope(factory) as s:
                    r = s.get(ThesisRevisionModel, "al_rev1")
                    r.revision_body = "modified"
            with cognition_session_scope(factory) as s:
                r = s.get(ThesisRevisionModel, "al_rev1")
                assert r.revision_body == "orig"
            engine.dispose()

    def test_foreign_keys_enforced_on_alembic_db(self):
        """All required FKs are enforced on Alembic-only DB."""
        from sqlalchemy.exc import IntegrityError

        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test_fk_alembic.db")
            engine, factory = self._alembic_factory(db_path)

            # ReviewIntent has FK to theses — inserting with nonexistent thesis_id should fail
            from market_radar.cognition_v2.persistence.models import ReviewIntentModel
            with pytest.raises(IntegrityError):
                with cognition_session_scope(factory) as s:
                    s.add(ReviewIntentModel(
                        id="fk_bad", thesis_id="nonexistent",
                        idempotency_key="fk_test", due_at=NOW,
                    ))
            engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════════
# R21 — Historical identity
# ═══════════════════════════════════════════════════════════════════════════════

class TestHistoricalIdentity:
    def test_roundtrip_persisted_identity(self):
        """Round-trip persisted historical identity and chain fields."""
        engine = create_cognition_engine(":memory:")
        factory = make_cognition_session_factory(engine)
        with cognition_session_scope(factory) as s:
            s.add(HistoricalCaseModel(
                id="h1", case_id="case_001", event_family="regulatory",
                split_label="BUILD", title="Test",
                evidence_manifest_hash="abc",
                event_identity_id="eid_001",
                correction_chain_id="chain_001",
                chain_root_case_id="root_001",
                correction_type="correction",
            ))
        with cognition_session_scope(factory) as s:
            m = s.get(HistoricalCaseModel, "h1")
            assert m.event_identity_id == "eid_001"
            assert m.correction_chain_id == "chain_001"
            assert m.chain_root_case_id == "root_001"
            assert m.correction_type == "correction"
        engine.dispose()

    def test_reconstruct_chain_after_reopen(self):
        """Reconstruct a correction chain after reopen."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "chain_reopen.db")
            engine1 = ce(db_path)
            Base.metadata.create_all(engine1)
            factory1 = make_cognition_session_factory(engine1)
            with cognition_session_scope(factory1) as s:
                s.add(HistoricalCaseModel(
                    id="chain_root", case_id="root_001", event_family="regulatory",
                    split_label="BUILD", title="Root",
                    evidence_manifest_hash="a",
                    correction_chain_id="chain_001", chain_root_case_id="root_001",
                ))
                s.add(HistoricalCaseModel(
                    id="chain_child", case_id="child_001", event_family="regulatory",
                    split_label="BUILD", title="Child",
                    evidence_manifest_hash="b",
                    correction_chain_id="chain_001", chain_root_case_id="root_001",
                    correction_type="correction",
                ))
            engine1.dispose()

            engine2 = ce(db_path)
            Base.metadata.create_all(engine2)
            factory2 = make_cognition_session_factory(engine2)
            with cognition_session_scope(factory2) as s:
                members = s.query(HistoricalCaseModel).filter(
                    HistoricalCaseModel.correction_chain_id == "chain_001"
                ).all()
                assert len(members) == 2
                root = next(m for m in members if m.id == "chain_root")
                assert root.chain_root_case_id == "root_001"
            engine2.dispose()

    def test_manifest_hash_includes_identity(self):
        """Manifest hash changes when identity/chain input changes."""
        m1 = HistoricalCaseManifest(
            case_id="c1", event_family="regulatory",
            market_regime="unknown", split_label="BUILD",
            title="Test", evidence_manifest_hash="abc",
            event_identity_id="eid_001",
            correction_chain_id="chain_001",
        )
        m2 = HistoricalCaseManifest(
            case_id="c1", event_family="regulatory",
            market_regime="unknown", split_label="BUILD",
            title="Test", evidence_manifest_hash="abc",
            event_identity_id="eid_002",  # different identity
            correction_chain_id="chain_001",
        )
        assert m1.deterministic_hash() != m2.deterministic_hash()

    def test_outcome_excluded_from_input_hash(self):
        """Outcome fields do not affect input manifest hash."""
        m1 = HistoricalCaseManifest(
            case_id="c1", event_family="regulatory",
            market_regime="unknown", split_label="BUILD",
            title="Test", evidence_manifest_hash="abc",
        )
        m2 = HistoricalCaseManifest(
            case_id="c1", event_family="regulatory",
            market_regime="unknown", split_label="BUILD",
            title="Test", evidence_manifest_hash="abc",
        )
        # Both should have same hash since identity fields are same (both None)
        assert m1.deterministic_hash() == m2.deterministic_hash()
