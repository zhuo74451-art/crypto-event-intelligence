"""Tests for chronological splitter, purge, embargo, and walk-forward."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from market_radar.intelligence.validation.splitter import ChronologicalSplitter


def make_record(event_time, event_id="evt_001", ref_period="2024-01"):
    return {
        "event_id": event_id,
        "event_time_utc": event_time,
        "reference_period": ref_period,
        "expected_effect": "bullish",
        "observed_direction": "positive",
    }


class TestChronologicalSplitter:

    def setup_method(self):
        self.splitter = ChronologicalSplitter(purge_hours=24, embargo_days=7)
        # 30 records spread across 10 years for robust walkforward testing
        self.records = []
        for year in range(2015, 2025):
            for month in range(1, 4):  # 3 events per year
                self.records.append(make_record(
                    f"{year}-{month:02d}-15T00:00:00Z",
                    f"evt_{year}_{month}",
                ))

    def test_fixed_time_split_orders(self):
        ti, vi, hi, manifest = self.splitter.fixed_time_split(
            self.records, train_end="2018-12-31T23:59:59Z",
            validation_end="2021-12-31T23:59:59Z")
        assert len(ti) > 0
        assert len(hi) > 0
        for t_idx in ti:
            for h_idx in hi:
                t_time = self.records[t_idx]["event_time_utc"]
                h_time = self.records[h_idx]["event_time_utc"]
                assert t_time < h_time, f"Train {t_time} not before holdout {h_time}"

    def test_holdout_later_than_train(self):
        ti, vi, hi, manifest = self.splitter.fixed_time_split(self.records)
        assert manifest.holdout_end > manifest.train_end

    def test_expanding_walkforward(self):
        folds, data = self.splitter.expanding_walkforward(
            self.records, initial_train_years=3, test_years=1)
        assert len(folds) >= 1
        for fold in folds:
            assert fold.train_count + fold.validation_count + fold.test_count > 0

    def test_rolling_walkforward(self):
        folds, data = self.splitter.rolling_walkforward(
            self.records, train_window_years=3, test_years=1)
        assert len(folds) >= 1

    def test_purge_embargo_filter(self):
        ti, vi, hi, manifest = self.splitter.fixed_time_split(self.records)
        kept, removed = self.splitter.purge_embargo_filter(
            self.records, ti, hi)
        assert len(kept) <= len(ti)
        assert len(removed) >= 0