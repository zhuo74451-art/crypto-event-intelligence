"""Tests for source_health."""

from pathlib import Path

from market_radar.operations.sqlite_schema import initialize_sqlite
from market_radar.operations.source_health import record_health, get_source_health


class TestSourceHealth:
    def test_record_and_read(self, tmp_path: Path):
        db = tmp_path / "health.db"
        initialize_sqlite(db)
        record_health(db, "binance", "ok", response_ms=120)
        record_health(db, "binance", "degraded", response_ms=5000)
        rows = get_source_health(db, "binance")
        assert len(rows) == 2
        assert rows[0]["health_status"] == "degraded"

    def test_empty_source(self, tmp_path: Path):
        db = tmp_path / "empty.db"
        initialize_sqlite(db)
        rows = get_source_health(db, "nonexistent")
        assert rows == []
