"""Falsification pack for cognition spine."""
import json, tempfile
from pathlib import Path
from market_radar.cognition.input_loader import load_observations
from market_radar.cognition.event_grouper import group_observations
from market_radar.cognition.event_store import EventStore
from market_radar.cognition.contracts import EventStatus

FIXTURE_DIR = Path(__file__).parents[2] / "tests" / "fixtures" / "cognition"

def test_duplicate_observation_ids(tmp_path):
    """Duplicate observation IDs must be rejected."""
    obs_path = tmp_path / "observations.jsonl"
    with open(obs_path, "w") as f:
        f.write(json.dumps({"observation_id": "dup1", "source": "test", "event_dedup_key": "k1", "observed_at": "2026-01-01T00:00:00+00:00", "event_time": "2026-01-01T00:00:00+00:00", "normalized_payload": {"title": "T"}, "affected_assets": []}) + chr(10))
        f.write(json.dumps({"observation_id": "dup1", "source": "test2", "event_dedup_key": "k1", "observed_at": "2026-01-01T00:01:00+00:00", "event_time": "2026-01-01T00:00:00+00:00", "normalized_payload": {"title": "T"}, "affected_assets": []}) + chr(10))
    obs_list, inv = load_observations(obs_path)
    assert inv.duplicate_ids == 1
    assert inv.rejected_observations >= 1

def test_same_event_different_sources(tmp_path):
    """Same dedup_key from different sources must merge."""
    obs_path = tmp_path / "observations.jsonl"
    with open(obs_path, "w") as f:
        f.write(json.dumps({"observation_id": "o1", "source": "cisa", "event_dedup_key": "cve-2026-test", "observed_at": "2026-01-01T00:00:00+00:00", "event_time": "2026-01-01T00:00:00+00:00", "normalized_payload": {"title": "CVE-2026-Test"}, "affected_assets": []}) + chr(10))
        f.write(json.dumps({"observation_id": "o2", "source": "sec", "event_dedup_key": "cve-2026-test", "observed_at": "2026-01-01T00:05:00+00:00", "event_time": "2026-01-01T00:00:00+00:00", "normalized_payload": {"title": "CVE-2026-Test"}, "affected_assets": []}) + chr(10))
    obs_list, inv = load_observations(obs_path)
    assert inv.valid_observations == 2
    events, conflicts = group_observations(obs_list)
    assert len(events) == 1
    assert len(events[0].observation_ids) == 2

def test_generic_title_no_false_merge(tmp_path):
    """Generic title must not cause false merge with different dedup keys."""
    obs_path = tmp_path / "observations.jsonl"
    with open(obs_path, "w") as f:
        f.write(json.dumps({"observation_id": "o1", "source": "cisa", "event_dedup_key": "k1", "observed_at": "2026-01-01T00:00:00+00:00", "event_time": "2026-01-01T00:00:00+00:00", "normalized_payload": {"title": "Update released"}, "affected_assets": []}) + chr(10))
        f.write(json.dumps({"observation_id": "o2", "source": "cisa", "event_dedup_key": "k2", "observed_at": "2026-01-02T00:00:00+00:00", "event_time": "2026-01-02T00:00:00+00:00", "normalized_payload": {"title": "Update released"}, "affected_assets": []}) + chr(10))
    obs_list, inv = load_observations(obs_path)
    events, conflicts = group_observations(obs_list)
    assert len(events) == 2, "Different dedup keys must remain separate even with same title"

def test_same_title_different_dates(tmp_path):
    """Same title on different dates must remain separate if dedup keys differ."""
    obs_path = tmp_path / "observations.jsonl"
    with open(obs_path, "w") as f:
        f.write(json.dumps({"observation_id": "o1", "source": "congress", "event_dedup_key": "jan_intro", "observed_at": "2026-01-15T10:00:00+00:00", "event_time": "2026-01-15T10:00:00+00:00", "normalized_payload": {"title": "House introduces crypto bill"}, "affected_assets": ["BTC"]}) + chr(10))
        f.write(json.dumps({"observation_id": "o2", "source": "congress", "event_dedup_key": "jun_intro", "observed_at": "2026-06-20T10:00:00+00:00", "event_time": "2026-06-20T10:00:00+00:00", "normalized_payload": {"title": "House introduces crypto bill"}, "affected_assets": ["BTC"]}) + chr(10))
    obs_list, inv = load_observations(obs_path)
    events, conflicts = group_observations(obs_list)
    assert len(events) == 2, "Same title different dates must remain separate"

def test_replay_idempotent(tmp_path):
    """Repeated replay must produce identical events."""
    obs_path = FIXTURE_DIR / "case_duplicate_cross_source" / "observations.jsonl"
    if not obs_path.exists(): return  # Skip if fixture missing
    obs_list1, inv1 = load_observations(obs_path)
    obs_list2, inv2 = load_observations(obs_path)
    events1, _ = group_observations(obs_list1)
    events2, _ = group_observations(obs_list2)
    assert len(events1) == len(events2)
    for e1, e2 in zip(events1, events2):
        assert e1.event_id == e2.event_id
        assert e1.observation_ids == e2.observation_ids

def test_nonempty_output_dir_rejected(tmp_path):
    """Cognition CLI must reject non-empty output dirs."""
    from market_radar.cognition.cli import main as cli_main
    (tmp_path / "existing_file.txt").write_text("test")
    rc = cli_main(["--input", str(FIXTURE_DIR / "case_regulatory_surprise"), "--output", str(tmp_path)])
    assert rc == 1, "Should reject non-empty output directory"
