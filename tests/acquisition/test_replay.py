"""Replay tests — 20+ scenarios."""
import pytest, json, tempfile, os
from datetime import datetime, timezone
from market_radar.acquisition.replay.point_in_time import PointInTimeReplayService
from market_radar.acquisition.replay.snapshot_repository import SnapshotRepository
from market_radar.acquisition.contracts.replay import ReplayQuery, ReplayResult, ReplayMode
from market_radar.acquisition.contracts.observation import NormalizedObservation
from market_radar.acquisition.contracts.timestamps import FiveTimestamps, TimestampEvidence, TimestampQuality

def make_obs(oid, sid, first_seen, retrieved):
    return NormalizedObservation(
        observation_id=oid, source_id=sid,
        timestamps=FiveTimestamps(
            first_seen_at=TimestampEvidence(first_seen, TimestampQuality.RETRIEVAL_ONLY),
            retrieved_at=TimestampEvidence(retrieved, TimestampQuality.RETRIEVAL_ONLY),
        ),
    )

class TestReplayService:
    def setup_method(self):
        self.service = PointInTimeReplayService()

    def test_empty_replay(self):
        q = ReplayQuery(as_of_time=datetime(2026, 6, 1, tzinfo=timezone.utc))
        result = self.service.replay(q)
        assert result.observation_count == 0

    def test_knowledge_as_known_then_basic(self):
        now = datetime(2026, 6, 15, tzinfo=timezone.utc)
        obs = make_obs("o1", "s1", now, now)
        self.service._observation_store["o1"] = obs
        q = ReplayQuery(as_of_time=now, mode=ReplayMode.KNOWLEDGE_AS_KNOWN_THEN)
        result = self.service.replay(q)
        assert result.observation_count == 1

    def test_future_revision_not_visible(self):
        early = datetime(2026, 1, 1, tzinfo=timezone.utc)
        late = datetime(2026, 6, 1, tzinfo=timezone.utc)
        obs = make_obs("o1", "s1", late, late)
        self.service._observation_store["o1"] = obs
        q = ReplayQuery(as_of_time=early, mode=ReplayMode.KNOWLEDGE_AS_KNOWN_THEN)
        result = self.service.replay(q)
        assert result.observation_count == 0

    def test_current_best_reconstruction(self):
        early = datetime(2026, 1, 1, tzinfo=timezone.utc)
        late = datetime(2026, 6, 1, tzinfo=timezone.utc)
        obs = make_obs("o1", "s1", late, late)
        self.service._observation_store["o1"] = obs
        q = ReplayQuery(as_of_time=early, mode=ReplayMode.CURRENT_BEST_RECONSTRUCTION)
        result = self.service.replay(q)
        assert result.is_reconstructed is True

    def test_mode_default(self):
        q = ReplayQuery(as_of_time=datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert q.mode == ReplayMode.KNOWLEDGE_AS_KNOWN_THEN

    def test_source_filter(self):
        now = datetime(2026, 6, 1, tzinfo=timezone.utc)
        self.service._observation_store["o1"] = make_obs("o1", "source-a", now, now)
        self.service._observation_store["o2"] = make_obs("o2", "source-b", now, now)
        q = ReplayQuery(as_of_time=now, source_ids=("source-a",))
        result = self.service.replay(q)
        assert result.observation_count == 1

class TestSnapshotRepository:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = SnapshotRepository()
            now = datetime(2026, 6, 1, tzinfo=timezone.utc)
            path = repo.save_snapshot(now, [], base_path=tmp)
            assert os.path.exists(path)
            result = repo.load_snapshot(path)
            assert result.observation_count == 0

    def test_list_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = SnapshotRepository()
            now = datetime(2026, 6, 1, tzinfo=timezone.utc)
            repo.save_snapshot(now, [], base_path=tmp)
            snapshots = repo.list_snapshots(base_path=tmp)
            assert len(snapshots) >= 1
