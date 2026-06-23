"""Test label computation with synthetic data."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest
from market_radar.intelligence.acquisition.historical_market.contracts import (
    MarketReactionLabelV1,
    LabelDirection,
    LabelAvailability,
    DataQuality,
    make_label_id,
)
from market_radar.intelligence.acquisition.historical_market.event_window_builder import (
    compute_return,
    compute_direction,
    DIRECTION_EPSILON,
)


class TestMakeLabelId:
    def test_label_id_deterministic(self):
        id1 = make_label_id("evt001", "binance_spot_btcusdt", "2026-06-15T12:00:00Z")
        id2 = make_label_id("evt001", "binance_spot_btcusdt", "2026-06-15T12:00:00Z")
        assert id1 == id2

    def test_label_id_different_event(self):
        id1 = make_label_id("evt001", "binance_spot_btcusdt", "2026-06-15T12:00:00Z")
        id2 = make_label_id("evt002", "binance_spot_btcusdt", "2026-06-15T12:00:00Z")
        assert id1 != id2


class TestLabelCreation:
    def test_create_label_all_fields(self):
        lbl = MarketReactionLabelV1(
            label_id="lbl001",
            event_id="evt001",
            instrument_id="binance_spot_btcusdt",
            event_time_utc="2026-06-15T12:00:00Z",
            return_1m=0.0005,
            return_5m=0.002,
            return_15m=0.005,
            return_30m=0.01,
            return_1h=0.015,
            return_4h=0.03,
            return_1d=0.05,
            direction_5m=LabelDirection.POSITIVE.value,
            direction_1h=LabelDirection.POSITIVE.value,
            direction_1d=LabelDirection.NEUTRAL.value,
            label_availability=LabelAvailability.FULL.value,
        )
        assert lbl.return_5m == 0.002
        assert lbl.return_1h == 0.015
        assert lbl.direction_5m == "positive"

    def test_label_defaults(self):
        lbl = MarketReactionLabelV1()
        assert lbl.return_1m is None
        assert lbl.direction_5m == LabelDirection.NEUTRAL.value


class TestComputeReturn:
    def test_price_increase(self):
        assert compute_return(100.0, 105.0) == pytest.approx(0.05)

    def test_price_decrease(self):
        assert compute_return(100.0, 95.0) == pytest.approx(-0.05)

    def test_zero_division_protection(self):
        assert compute_return(0.0, 100.0) == 0.0


class TestComputeDirection:
    def test_positive(self):
        d = compute_direction(0.005, DIRECTION_EPSILON["crypto_5m"])
        assert d == "positive"

    def test_negative(self):
        d = compute_direction(-0.005, DIRECTION_EPSILON["crypto_5m"])
        assert d == "negative"

    def test_small_return_neutral(self):
        d = compute_direction(0.0001, DIRECTION_EPSILON["crypto_5m"])
        assert d == "neutral"


class TestLabelRoundTrip:
    def test_to_json_round_trip(self):
        lbl = MarketReactionLabelV1(
            label_id="lbl_rt",
            event_id="evt001",
            instrument_id="binance_spot_ethusdt",
            event_time_utc="2026-06-15T12:00:00Z",
            return_1h=0.02,
            direction_1h=LabelDirection.POSITIVE.value,
        )
        data = lbl.to_json()
        restored = MarketReactionLabelV1.from_json(data)
        assert restored.label_id == "lbl_rt"
        assert restored.return_1h == 0.02
