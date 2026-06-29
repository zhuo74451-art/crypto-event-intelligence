"""Tests for pilot runner — run_once integration, output file structure."""
import json
from unittest import mock
from pathlib import Path

from market_radar.acquisition.pilot_runner import (
    create_pilot_runner,
    run_pilot,
)
from market_radar.operations.run_once import run_once


def test_create_runner_and_run_once():
    """Runner must be compatible with run_once wrapper."""
    runner = create_pilot_runner(sources=["cisa"], limit=3)
    assert runner.label == "SourceEvidencePilot"
    assert callable(runner.fn)


def test_run_pilot_mocked(monkeypatch, tmp_path):
    """Run pilot with mocked CISA source."""
    from market_radar.acquisition.sources.cisa_kev import CISA_CONTRACT
    fixture_path = Path(__file__).parents[2] / "tests" / "fixtures" / "acquisition" / "cisa_kev_sample.json"
    with open(fixture_path, "rb") as f:
        sample = f.read()

    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200; resp.content = sample
        resp.headers = {"Content-Type": "application/json"}
        mg.return_value = resp
        result = run_pilot({
            "run_id": "test_pilot",
            "config": {
                "sources": ["cisa"],
                "limit": 3,
                "output_dir": str(tmp_path),
            }
        })
    assert result["status"] == "ok"
    assert result["total_observations"] == 3

    # Verify output files exist
    files = list(tmp_path.iterdir())
    names = [f.name for f in files]
    assert "RUN_TELEMETRY.jsonl" in names
    assert "run_manifest.json" in names
    assert "source_health.json" in names
    assert "observations.jsonl" in names
    assert "evidence_manifest.jsonl" in names

    # Verify manifest content
    manifest = json.loads((tmp_path / "run_manifest.json").read_text())
    assert manifest["status"] == "ok"
    assert manifest["sources"] == ["cisa"]

    # Verify observations
    obs_lines = (tmp_path / "observations.jsonl").read_text().strip().split("\n")
    assert len(obs_lines) == 3

    # Verify telemetry
    tel = (tmp_path / "RUN_TELEMETRY.jsonl").read_text().strip().split("\n")
    assert len(tel) >= 3  # run_started, source_acquisition_started, source_acquisition_completed, run_completed


def test_run_once_wrapper(monkeypatch, tmp_path):
    """run_once must execute the runner exactly once."""
    fixture_path = Path(__file__).parents[2] / "tests" / "fixtures" / "acquisition" / "cisa_kev_sample.json"
    with open(fixture_path, "rb") as f:
        sample = f.read()

    with mock.patch("requests.get") as mg:
        resp = mock.MagicMock()
        resp.status_code = 200; resp.content = sample
        resp.headers = {"Content-Type": "application/json"}
        mg.return_value = resp
        runner = create_pilot_runner(
            sources=["cisa"], limit=3, output_dir=str(tmp_path)
        )
        result = run_once(runner, run_id="run_once_test")
    assert result.status == "ok"
    assert result.run_id == "run_once_test"
    assert result.runner_label == "SourceEvidencePilot"
    assert result.summary["total_observations"] == 3
