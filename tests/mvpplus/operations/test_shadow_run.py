"""Tests for shadow_run."""

from pathlib import Path

from market_radar.operations.shadow_run import shadow_run
from market_radar.operations.stop_marker import StopMarker


def _ok_runner(ctx: dict) -> dict:
    return {"status": "ok", "iter": ctx.get("iteration", 0)}


def _fail_runner(ctx: dict) -> dict:
    raise ValueError("intentional failure")


class TestShadowRun:
    def test_bounded_iteration(self):
        results = shadow_run(_ok_runner, "test", max_iterations=3)
        assert len(results) == 3
        assert all(r.status == "ok" for r in results)

    def test_max_iterations_validation(self):
        import pytest
        with pytest.raises(ValueError, match=">= 1"):
            shadow_run(_ok_runner, "test", max_iterations=0)

    def test_failure_stops(self):
        results = shadow_run(_fail_runner, "fail", max_iterations=5)
        assert len(results) == 1
        assert results[0].status == "failed"

    def test_stop_marker_interrupts(self, tmp_path: Path):
        marker = StopMarker(tmp_path / "stop.mrk")
        i = [0]

        def runner(ctx):
            i[0] += 1
            if i[0] >= 2:
                marker.set()
            return {"status": "ok"}

        results = shadow_run(runner, "stop", max_iterations=10, stop_marker=marker)
        # Should have run a few, then stopped
        assert 1 <= len(results) <= 3
        assert any(r.status == "stopped" for r in results) or results[-1].status == "ok"

    def test_config_passed(self):
        config = {"key": "value"}

        def runner(ctx):
            assert ctx["config"]["key"] == "value"
            return {"status": "ok"}

        results = shadow_run(runner, "cfg", max_iterations=1, config=config)
        assert results[0].status == "ok"
