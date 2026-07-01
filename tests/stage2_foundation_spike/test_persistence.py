"""Test persistence with actual module API."""

import os
import tempfile
import pytest
from experiments.stage2_foundation_spike.persistence_spike import (
    create_engine_and_tables,
    make_session_factory,
    session_scope,
    Event,
    table_names,
)


class TestMigrationUpgrade:
    def test_tables_created(self):
        engine = create_engine_and_tables(":memory:")
        names = table_names(engine)
        assert "events" in names


class TestCRUD:
    def test_insert_and_read(self):
        engine = create_engine_and_tables(":memory:")
        factory = make_session_factory(engine)
        with session_scope(factory) as s:
            ev = Event(id="e1", idempotency_key="ik1", title="Test")
            s.add(ev)
        with session_scope(factory) as s:
            loaded = s.get(Event, "e1")
            assert loaded is not None
            assert loaded.title == "Test"

    def test_foreign_key_enforced(self):
        engine = create_engine_and_tables(":memory:")
        factory = make_session_factory(engine)
        from experiments.stage2_foundation_spike.persistence_spike import Signal
        with pytest.raises(Exception):
            with session_scope(factory) as s:
                sig = Signal(id="s1", event_id="nonexistent", signal_type="price", value="100")
                s.add(sig)
