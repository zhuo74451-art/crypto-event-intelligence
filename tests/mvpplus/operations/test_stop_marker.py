"""Tests for stop_marker."""

from pathlib import Path

from market_radar.operations.stop_marker import StopMarker


class TestStopMarker:
    def test_not_set_by_default(self, tmp_path: Path):
        m = StopMarker(tmp_path / "no.mrk")
        assert not m.is_set
        assert not m.check()

    def test_set_and_clear(self, tmp_path: Path):
        m = StopMarker(tmp_path / "go.mrk")
        m.set()
        assert m.is_set
        assert m.check()
        m.clear()
        assert not m.is_set

    def test_check_returns_bool(self, tmp_path: Path):
        m = StopMarker(tmp_path / "bool.mrk")
        assert m.check() is False
        m.set()
        assert m.check() is True
        m.clear()
