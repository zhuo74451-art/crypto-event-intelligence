"""Test persistence — real Alembic, compare-and-swap, immutable revisions."""

import os
import tempfile
from datetime import datetime, timezone
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from experiments.stage2_foundation_spike.persistence_spike import (
    create_engine_and_tables,
    make_session_factory,
    session_scope,
    apply_alembic_migration,
    prove_rollback,
    prove_reopen_recovery,
    prove_append_only_revision,
    prove_optimistic_conflict,
    compare_and_swap_thesis,
    StaleVersionError,
    Evidence,
    Event,
    Thesis,
    ThesisRevision,
    ReviewIntent,
    Base,
)


NOW = datetime.now(timezone.utc)


class TestModels:
    def test_all_contracted_models_exist(self):
        tables = Base.metadata.tables
        for name in ("evidence", "events", "theses", "thesis_revisions", "review_intents"):
            assert name in tables, f"Missing table: {name}"

    def test_foreign_key_enforced(self):
        engine = create_engine_and_tables(":memory:")
        factory = make_session_factory(engine)
        with pytest.raises(IntegrityError):
            with session_scope(factory) as s:
                r = ReviewIntent(id="fk_test", thesis_id="nonexistent", idempotency_key="ik1", due_at=NOW)
                s.add(r)

    def test_unique_idempotency_key(self):
        engine = create_engine_and_tables(":memory:")
        factory = make_session_factory(engine)
        with session_scope(factory) as s:
            s.add(Thesis(id="t_ik", claim_class="fact", summary="t", lifecycle_state="DISCOVERED"))
        with session_scope(factory) as s:
            r1 = ReviewIntent(id="idem1", thesis_id="t_ik", idempotency_key="dup_key", due_at=NOW)
            s.add(r1)
        with pytest.raises(IntegrityError):
            with session_scope(factory) as s:
                r2 = ReviewIntent(id="idem2", thesis_id="t_ik", idempotency_key="dup_key", due_at=NOW)
                s.add(r2)


class TestAlembicMigration:
    def test_alembic_upgrade_creates_tables(self):
        """Alembic upgrade against empty SQLite must create schema and alembic_version."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test_alembic.db")
            from sqlalchemy import create_engine as ce
            engine = ce(f"sqlite:///{db_path}")
            rev_id = apply_alembic_migration(engine)
            assert rev_id == "stage2_spike_001"
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                rows = result.fetchall()
                assert len(rows) == 1
                assert rows[0][0] == "stage2_spike_001"
            engine.dispose()

    def test_alembic_downgrade_drops_tables(self):
        """Alembic downgrade must drop tables."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test_down.db")
            from sqlalchemy import create_engine as ce
            engine = ce(f"sqlite:///{db_path}")
            # Create simple migration with downgrade
            import alembic.config
            import alembic.command
            versions_dir = os.path.join(td, "versions")
            os.makedirs(versions_dir)
            ini = os.path.join(td, "alembic.ini")
            with open(ini, "w") as f:
                f.write(f"[alembic]\nscript_location = {td}\nsqlalchemy.url = sqlite:///{db_path}\n")
            with open(os.path.join(td, "env.py"), "w") as f:
                f.write("from alembic import context\nfrom sqlalchemy import engine_from_config\nconfig = context.config\ndef run_migrations_online():\n    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix='sqlalchemy.')\n    with connectable.connect() as connection:\n        context.configure(connection=connection)\n        with context.begin_transaction():\n            context.run_migrations()\nrun_migrations_online()\n")
            with open(os.path.join(td, "script.py.mako"), "w") as f:
                f.write("${upgrades if upgrades else 'pass'}\n${downgrades if downgrades else 'pass'}\n")
            with open(os.path.join(versions_dir, "rev1.py"), "w") as f:
                f.write('''"""rev1"""
revision = "rev1"
down_revision = None
from alembic import op
import sqlalchemy as sa
def upgrade():
    op.create_table("down_test", sa.Column("id", sa.String(36), primary_key=True))
def downgrade():
    op.drop_table("down_test")
''')
            cfg = alembic.config.Config(ini)
            cfg.set_main_option("script_location", td)
            alembic.command.upgrade(cfg, "head")
            with engine.connect() as conn:
                assert conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='down_test'")).fetchone() is not None
            alembic.command.downgrade(cfg, "base")
            with engine.connect() as conn:
                assert conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='down_test'")).fetchone() is None
            engine.dispose()

    def test_alembic_failure_is_fatal(self):
        """A bad migration must propagate the exception."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test_fail.db")
            from sqlalchemy import create_engine as ce
            engine = ce(f"sqlite:///{db_path}")
            import alembic.config
            import alembic.command
            versions_dir = os.path.join(td, "versions")
            os.makedirs(versions_dir)
            ini = os.path.join(td, "alembic.ini")
            with open(ini, "w") as f:
                f.write(f"[alembic]\nscript_location = {td}\nsqlalchemy.url = sqlite:///{db_path}\n")
            with open(os.path.join(td, "env.py"), "w") as f:
                f.write("from alembic import context\nfrom sqlalchemy import engine_from_config\nconfig = context.config\ndef run_migrations_online():\n    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix='sqlalchemy.')\n    with connectable.connect() as connection:\n        context.configure(connection=connection)\n        with context.begin_transaction():\n            context.run_migrations()\nrun_migrations_online()\n")
            with open(os.path.join(td, "script.py.mako"), "w") as f:
                f.write("${upgrades if upgrades else 'pass'}\n${downgrades if downgrades else 'pass'}\n")
            with open(os.path.join(versions_dir, "bad.py"), "w") as f:
                f.write('''"""bad"""
revision = "bad"
down_revision = None
from alembic import op
def upgrade():
    op.execute("INVALID SQL")
def downgrade():
    pass
''')
            cfg = alembic.config.Config(ini)
            cfg.set_main_option("script_location", td)
            with pytest.raises(Exception):
                alembic.command.upgrade(cfg, "head")
            engine.dispose()


class TestRollback:
    def test_transaction_rollback(self):
        engine = create_engine_and_tables(":memory:")
        assert prove_rollback(engine) is True


class TestReopenRecovery:
    def test_close_and_reopen_recovers_state(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            assert prove_reopen_recovery(db_path) is True


class TestCompareAndSwap:
    def test_correct_version_succeeds(self):
        engine = create_engine_and_tables(":memory:")
        factory = make_session_factory(engine)
        with session_scope(factory) as s:
            s.add(Thesis(id="cas_t", claim_class="fact", summary="orig", lifecycle_state="DISCOVERED", version=1))
        rows = compare_and_swap_thesis(factory, "cas_t", 1, {"summary": "updated"})
        assert rows == 1
        with session_scope(factory) as s:
            t = s.get(Thesis, "cas_t")
            assert t.summary == "updated"
            assert t.version == 2

    def test_stale_version_raises(self):
        engine = create_engine_and_tables(":memory:")
        factory = make_session_factory(engine)
        with session_scope(factory) as s:
            s.add(Thesis(id="cas_t2", claim_class="fact", summary="orig", lifecycle_state="DISCOVERED", version=1))
        compare_and_swap_thesis(factory, "cas_t2", 1, {"summary": "v2"})
        with pytest.raises(StaleVersionError):
            compare_and_swap_thesis(factory, "cas_t2", 1, {"summary": "stale"})


class TestAppendOnlyRevision:
    def test_append_only(self):
        engine = create_engine_and_tables(":memory:")
        factory = make_session_factory(engine)
        with session_scope(factory) as s:
            s.add(Thesis(id="app_t", claim_class="fact", summary="t", lifecycle_state="DISCOVERED"))
            s.add(ThesisRevision(id="ar1", thesis_id="app_t", version=1, revision_body="v1"))
        with session_scope(factory) as s:
            s.add(ThesisRevision(id="ar2", thesis_id="app_t", version=2, revision_body="v2"))
        with engine.connect() as c:
            vs = [r[0] for r in c.execute(text("SELECT version FROM thesis_revisions WHERE thesis_id='app_t' ORDER BY version"))]
        assert vs == [1, 2]

    def test_duplicate_revision_version_rejected(self):
        """ThesisRevision (thesis_id, version) must be unique."""
        engine = create_engine_and_tables(":memory:")
        factory = make_session_factory(engine)
        with session_scope(factory) as s:
            s.add(Thesis(id="dup_t", claim_class="fact", summary="t", lifecycle_state="DISCOVERED"))
            s.add(ThesisRevision(id="dr1", thesis_id="dup_t", version=1, revision_body="v1"))
        with pytest.raises(IntegrityError):
            with session_scope(factory) as s:
                s.add(ThesisRevision(id="dr2", thesis_id="dup_t", version=1, revision_body="v1_dup"))
