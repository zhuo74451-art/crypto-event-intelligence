"""Tests for revision as-of queries and historical state management."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from market_radar.intelligence.acquisition.historical_macro.contracts import (
    MacroReleaseEventV1,
    MacroRevisionRecordV1,
    MacroAsOfEngine,
)


class TestRevisionAsOf:
    def setup_method(self):
        self.event = MacroReleaseEventV1(
            event_family="us_cpi",
            series_id="CUUR0000SA0",
            reference_period="2023-01",
            actual_release_at_utc="2023-02-14T13:30:00Z",
            actual_initial=6.4,
            prior_as_known_then=6.5,
        )
        self.revisions = [
            MacroRevisionRecordV1(
                event_id=self.event.event_id,
                series_id="CUUR0000SA0",
                reference_period="2023-01",
                revision_published_at_utc="2023-03-14T13:30:00Z",
                previous_value=6.4,
                revised_value=6.3,
                revision_sequence=1,
                source_url="https://example.com/rev1",
            ),
            MacroRevisionRecordV1(
                event_id=self.event.event_id,
                series_id="CUUR0000SA0",
                reference_period="2023-01",
                revision_published_at_utc="2023-05-14T13:30:00Z",
                previous_value=6.3,
                revised_value=6.2,
                revision_sequence=2,
                source_url="https://example.com/rev2",
            ),
        ]
        self.engine = MacroAsOfEngine()

    def test_before_release_returns_prior(self):
        result = self.engine.get_release_as_of(
            self.event, self.revisions, "2023-02-13T12:00:00Z",
        )
        assert result.actual_initial is None
        assert result.prior_as_known_then == 6.5

    def test_at_release_returns_initial(self):
        result = self.engine.get_release_as_of(
            self.event, self.revisions, "2023-02-14T13:30:00Z",
        )
        # at release time we use the initial value
        assert result.prior_revised_latest == 6.4

    def test_after_first_revision(self):
        result = self.engine.get_release_as_of(
            self.event, self.revisions, "2023-04-01T12:00:00Z",
        )
        assert result.prior_revised_latest == 6.3

    def test_after_second_revision(self):
        result = self.engine.get_release_as_of(
            self.event, self.revisions, "2023-06-01T12:00:00Z",
        )
        assert result.prior_revised_latest == 6.2

    def test_no_revisions_returns_initial(self):
        result = self.engine.get_release_as_of(
            self.event, [], "2023-03-01T12:00:00Z",
        )
        assert result.prior_revised_latest == 6.4

    def test_future_revision_not_visible_in_past(self):
        """Revision published in May should not be visible in April."""
        result = self.engine.get_release_as_of(
            self.event, self.revisions, "2023-04-15T12:00:00Z",
        )
        assert result.prior_revised_latest == 6.3  # First revision visible
        assert result.prior_revised_latest != 6.2  # Second revision not visible

    def test_revision_chain_ordering(self):
        chain = self.engine.get_revision_chain(self.event.event_id, self.revisions)
        assert len(chain) == 2
        assert chain[0].revision_sequence == 1
        assert chain[1].revision_sequence == 2
        assert chain[0].previous_value == 6.4
        assert chain[1].previous_value == 6.3

    def test_current_best(self):
        best = self.engine.get_current_best(self.event, self.revisions)
        assert best == 6.2

    def test_current_best_no_revisions(self):
        best = self.engine.get_current_best(self.event, [])
        assert best == 6.4

    def test_consensus_as_of_filter(self):
        from market_radar.intelligence.acquisition.historical_macro.contracts import (
            MacroConsensusObservationV1,
        )
        obs = [
            MacroConsensusObservationV1(
                event_id=self.event.event_id,
                source_name="S1",
                source_url="https://example.com/1",
                published_at_utc="2023-02-10T12:00:00Z",
                consensus_value=6.2,
                consensus_unit="percent",
            ),
            MacroConsensusObservationV1(
                event_id=self.event.event_id,
                source_name="S2",
                source_url="https://example.com/2",
                published_at_utc="2023-02-15T12:00:00Z",
                consensus_value=6.3,
                consensus_unit="percent",
            ),
        ]
        before = self.engine.get_consensus_as_of(obs, "2023-02-14T13:00:00Z")
        assert len(before) == 1
        assert before[0].source_name == "S1"
