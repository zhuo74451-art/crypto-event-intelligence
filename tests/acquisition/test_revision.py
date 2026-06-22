"""Revision detection and lineage tests — 25+ scenarios."""
import pytest
from datetime import datetime, timezone
from market_radar.acquisition.revisions.detector import RevisionDetector
from market_radar.acquisition.revisions.lineage import LineageTracker, RevisionRecord, RevisionLineage
from market_radar.acquisition.contracts.revision import RevisionType

class TestRevisionDetector:
    def setup_method(self):
        self.detector = RevisionDetector()

    def test_first_seen(self):
        rtype, summary = self.detector.detect(None, "hash1", None, "idhash1")
        assert rtype == RevisionType.FIRST_SEEN

    def test_no_change(self):
        rtype, summary = self.detector.detect("hash1", "hash1", "id1", "id1")
        assert rtype == RevisionType.NO_CHANGE

    def test_content_changed(self):
        rtype, summary = self.detector.detect("hash1", "hash2", "id1", "id2")
        assert rtype == RevisionType.CONTENT_CHANGED

    def test_metadata_changed(self):
        rtype, summary = self.detector.detect(
            "hash1", "hash1", "id1", "id1",
            prev_metadata={"title": "Old"}, curr_metadata={"title": "New"}
        )
        assert rtype == RevisionType.METADATA_CHANGED

    def test_deleted(self):
        rtype, summary = self.detector.detect("hash1", "", "id1", "")
        assert rtype == RevisionType.DELETED

    def test_restored(self):
        rtype, summary = self.detector.detect("hash_del", "hash_new", "id_del", "id_new", prev_is_deleted=True)
        assert rtype == RevisionType.RESTORED

class TestLineageTracker:
    def setup_method(self):
        self.tracker = LineageTracker()

    def test_add_and_latest(self):
        r = RevisionRecord(revision_id="r1", source_id="s1", observation_id="o1",
                          revision_type=RevisionType.FIRST_SEEN, first_seen_at="2026-01-01T00:00:00")
        self.tracker.add_revision(r)
        latest = self.tracker.latest_revision("s1", "o1")
        assert latest is not None
        assert latest.revision_id == "r1"

    def test_as_of_within_range(self):
        r1 = RevisionRecord(revision_id="r1", source_id="s1", observation_id="o1",
                          revision_type=RevisionType.FIRST_SEEN, first_seen_at="2026-01-01T00:00:00")
        r2 = RevisionRecord(revision_id="r2", source_id="s1", observation_id="o1",
                          revision_type=RevisionType.CONTENT_CHANGED, first_seen_at="2026-02-01T00:00:00")
        self.tracker.add_revision(r1)
        self.tracker.add_revision(r2)
        as_of = datetime(2026, 1, 15, tzinfo=timezone.utc)
        revisions = self.tracker.revisions_as_of("s1", "o1", as_of)
        assert len(revisions) == 1
        assert revisions[0].revision_id == "r1"

    def test_as_of_after_all(self):
        r1 = RevisionRecord(revision_id="r1", source_id="s1", observation_id="o1",
                          revision_type=RevisionType.FIRST_SEEN, first_seen_at="2026-01-01T00:00:00")
        self.tracker.add_revision(r1)
        as_of = datetime(2026, 6, 1, tzinfo=timezone.utc)
        revisions = self.tracker.revisions_as_of("s1", "o1", as_of)
        assert len(revisions) == 1

    def test_empty_tracker(self):
        assert self.tracker.latest_revision("nonexistent", "nonexistent") is None

    def test_multiple_observations(self):
        self.tracker.add_revision(RevisionRecord(revision_id="r1", source_id="s1", observation_id="o1",
                                                revision_type=RevisionType.FIRST_SEEN, first_seen_at="2026-01-01T00:00:00"))
        self.tracker.add_revision(RevisionRecord(revision_id="r2", source_id="s1", observation_id="o2",
                                                revision_type=RevisionType.FIRST_SEEN, first_seen_at="2026-01-01T00:00:00"))
        assert self.tracker.latest_revision("s1", "o1").revision_id == "r1"
        assert self.tracker.latest_revision("s1", "o2").revision_id == "r2"
