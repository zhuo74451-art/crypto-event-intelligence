"""Test event window building with synthetic events and bars."""

import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest
from market_radar.intelligence.acquisition.historical_market.event_window_builder import (
    parse_time,
    find_bar_at_time,
    find_last_bar_before,
    find_bars_in_range,
    compute_return,
    compute_direction,
    compute_realized_vol,
    compute_volume_zscore,
    load_bars_index,
    DIRECTION_EPSILON,
    CALCULATION_VERSION,
)


class TestParseTime:
    def test_parse_utc_z(self):
        dt = parse_time("2026-06-15T12:00:00Z")
        assert dt.year == 2026
        assert dt.month == 6
        assert dt.day == 15
        assert dt.hour == 12
        assert dt.minute == 0
        assert dt.tzinfo is not None

    def test_parse_with_offset(self):
        dt = parse_time("2026-06-15T12:00:00+00:00")
        assert dt.hour == 12

    def test_parse_raises_on_invalid(self):
        with pytest.raises((ValueError, TypeError)):
            parse_time("not-a-date")


class TestFindBarAtTime:
    def make_bar(self, open_time, close_time):
        return {"open_time_utc": open_time, "close_time_utc": close_time}

    def test_find_exact_match(self):
        bars = [
            self.make_bar("2026-06-15T10:00:00Z", "2026-06-15T11:00:00Z"),
            self.make_bar("2026-06-15T11:00:00Z", "2026-06-15T12:00:00Z"),
            self.make_bar("2026-06-15T12:00:00Z", "2026-06-15T13:00:00Z"),
        ]
        target = datetime(2026, 6, 15, 11, 30, 0, tzinfo=timezone.utc)
        found = find_bar_at_time(bars, target)
        assert found is not None
        assert found["open_time_utc"] == "2026-06-15T11:00:00Z"

    def test_find_no_match(self):
        bars = [self.make_bar("2026-06-15T10:00:00Z", "2026-06-15T11:00:00Z")]
        target = datetime(2026, 6, 16, 0, 0, 0, tzinfo=timezone.utc)
        assert find_bar_at_time(bars, target) is None

    def test_find_empty_bars(self):
        assert find_bar_at_time([], datetime.now(timezone.utc)) is None


class TestFindLastBarBefore:
    def make_bar(self, open_time, close_time):
        return {"open_time_utc": open_time, "close_time_utc": close_time}

    def test_find_last_before(self):
        bars = [
            self.make_bar("2026-06-15T10:00:00Z", "2026-06-15T11:00:00Z"),
            self.make_bar("2026-06-15T11:00:00Z", "2026-06-15T12:00:00Z"),
            self.make_bar("2026-06-15T12:00:00Z", "2026-06-15T13:00:00Z"),
        ]
        target = datetime(2026, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        found = find_last_bar_before(bars, target)
        assert found is not None
        assert found["close_time_utc"] == "2026-06-15T12:00:00Z"

    def test_no_bar_before(self):
        bars = [self.make_bar("2026-06-15T12:00:00Z", "2026-06-15T13:00:00Z")]
        target = datetime(2026, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
        assert find_last_bar_before(bars, target) is None


class TestFindBarsInRange:
    def make_bar(self, open_time, close_time):
        return {"open_time_utc": open_time, "close_time_utc": close_time}

    def test_find_range(self):
        bars = [
            self.make_bar("2026-06-15T10:00:00Z", "2026-06-15T11:00:00Z"),
            self.make_bar("2026-06-15T11:00:00Z", "2026-06-15T12:00:00Z"),
            self.make_bar("2026-06-15T12:00:00Z", "2026-06-15T13:00:00Z"),
            self.make_bar("2026-06-15T13:00:00Z", "2026-06-15T14:00:00Z"),
        ]
        start = datetime(2026, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 6, 15, 13, 0, 0, tzinfo=timezone.utc)
        result = find_bars_in_range(bars, start, end)
        assert len(result) == 2
        assert result[0]["open_time_utc"] == "2026-06-15T11:00:00Z"
        assert result[1]["open_time_utc"] == "2026-06-15T12:00:00Z"


class TestComputeReturn:
    def test_positive_return(self):
        assert compute_return(100.0, 110.0) == pytest.approx(0.10)

    def test_negative_return(self):
        assert compute_return(100.0, 90.0) == pytest.approx(-0.10)

    def test_zero_return(self):
        assert compute_return(100.0, 100.0) == 0.0

    def test_zero_before_price(self):
        assert compute_return(0.0, 100.0) == 0.0


class TestComputeDirection:
    def test_positive(self):
        assert compute_direction(0.01, 0.001) == "positive"

    def test_negative(self):
        assert compute_direction(-0.01, 0.001) == "negative"

    def test_neutral_below_epsilon(self):
        assert compute_direction(0.0005, 0.001) == "neutral"

    def test_neutral_exact_zero(self):
        assert compute_direction(0.0, 0.001) == "neutral"


class TestComputeRealizedVol:
    def test_insufficient_data(self):
        assert compute_realized_vol([100.0]) == 0.0

    def test_empty_data(self):
        assert compute_realized_vol([]) == 0.0

    def test_sufficient_data(self):
        prices = [100.0, 101.0, 99.0, 102.0, 100.5]
        assert compute_realized_vol(prices) > 0.0


class TestComputeVolumeZscore:
    def test_insufficient_bars(self):
        assert compute_volume_zscore([{"volume": 100}]) == 0.0

    def test_all_zero_volumes(self):
        bars = [{"volume": 0}, {"volume": 0}, {"volume": 0}]
        assert compute_volume_zscore(bars) == 0.0

    def test_normal_case(self):
        bars = [{"volume": 100}, {"volume": 110}, {"volume": 90}, {"volume": 200}]
        z = compute_volume_zscore(bars)
        assert z > 0.0


class TestLoadBarsIndex:
    def test_nonexistent_file(self):
        assert load_bars_index("/tmp/nonexistent_file.jsonl") == {}

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("")
            tmp = f.name
        try:
            assert load_bars_index(tmp) == {}
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_with_data(self):
        lines = [
            json.dumps({"instrument_id": "btc", "interval": "1h", "open_time_utc": "2026-06-15T10:00:00Z"}),
            json.dumps({"instrument_id": "btc", "interval": "1h", "open_time_utc": "2026-06-15T11:00:00Z"}),
            json.dumps({"instrument_id": "eth", "interval": "5m", "open_time_utc": "2026-06-15T10:00:00Z"}),
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for line in lines:
                f.write(line + chr(10))
            tmp = f.name
        try:
            idx = load_bars_index(tmp)
            assert "btc|1h" in idx
            assert "eth|5m" in idx
            assert len(idx["btc|1h"]) == 2
            assert len(idx["eth|5m"]) == 1
        finally:
            Path(tmp).unlink(missing_ok=True)


class TestDirectionEpsilon:
    def test_epsilon_constants_exist(self):
        assert "crypto_5m" in DIRECTION_EPSILON
        assert "crypto_1h" in DIRECTION_EPSILON
        assert "crypto_1d" in DIRECTION_EPSILON
        assert "daily_cross_asset" in DIRECTION_EPSILON
        assert DIRECTION_EPSILON["crypto_1h"] == 0.001

    def test_calculation_version(self):
        assert CALCULATION_VERSION == "1.0.0"
