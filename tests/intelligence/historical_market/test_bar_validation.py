"""Test OHLC validation rules."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest
from market_radar.intelligence.acquisition.historical_market.contracts import (
    MarketBarV1,
    validate_ohlc,
)


class TestOhlcValidation:
    def test_valid_bar_no_flags(self):
        bar = MarketBarV1(
            instrument_id="test",
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            volume=1000.0,
        )
        flags = validate_ohlc(bar)
        assert flags == []

    def test_negative_open(self):
        bar = MarketBarV1(open=-1.0, high=10.0, low=1.0, close=5.0, volume=100)
        flags = validate_ohlc(bar)
        assert "negative_open" in flags

    def test_negative_high(self):
        bar = MarketBarV1(open=10.0, high=-1.0, low=1.0, close=5.0, volume=100)
        flags = validate_ohlc(bar)
        assert "negative_high" in flags

    def test_negative_low(self):
        bar = MarketBarV1(open=10.0, high=20.0, low=-5.0, close=15.0, volume=100)
        flags = validate_ohlc(bar)
        assert "negative_low" in flags

    def test_negative_close(self):
        bar = MarketBarV1(open=10.0, high=20.0, low=1.0, close=-5.0, volume=100)
        flags = validate_ohlc(bar)
        assert "negative_close" in flags

    def test_negative_volume(self):
        bar = MarketBarV1(open=10.0, high=20.0, low=1.0, close=15.0, volume=-100)
        flags = validate_ohlc(bar)
        assert "negative_volume" in flags

    def test_high_below_low(self):
        bar = MarketBarV1(open=10.0, high=5.0, low=15.0, close=10.0, volume=100)
        flags = validate_ohlc(bar)
        assert "high_below_low" in flags

    def test_high_below_open(self):
        bar = MarketBarV1(open=10.0, high=8.0, low=5.0, close=9.0, volume=100)
        flags = validate_ohlc(bar)
        assert "high_below_open" in flags

    def test_high_below_close(self):
        bar = MarketBarV1(open=10.0, high=11.0, low=5.0, close=12.0, volume=100)
        flags = validate_ohlc(bar)
        assert "high_below_close" in flags

    def test_low_above_open(self):
        bar = MarketBarV1(open=10.0, high=15.0, low=12.0, close=14.0, volume=100)
        flags = validate_ohlc(bar)
        assert "low_above_open" in flags

    def test_low_above_close(self):
        bar = MarketBarV1(open=10.0, high=15.0, low=12.0, close=11.0, volume=100)
        flags = validate_ohlc(bar)
        assert "low_above_close" in flags

    def test_zero_price_flag(self):
        """A price of exactly 0.0 should trigger zero_price."""
        bar = MarketBarV1(open=0.0, high=10.0, low=1.0, close=5.0, volume=100)
        flags = validate_ohlc(bar)
        assert "zero_price" in flags

    def test_multiple_violations(self):
        bar = MarketBarV1(open=-10.0, high=5.0, low=20.0, close=1.0, volume=-1)
        flags = validate_ohlc(bar)
        assert "negative_open" in flags
        assert "negative_volume" in flags
        assert "high_below_low" in flags

    def test_all_zero_prices(self):
        bar = MarketBarV1(open=0.0, high=0.0, low=0.0, close=0.0, volume=0.0)
        flags = validate_ohlc(bar)
        assert "zero_price" in flags
        # All zero prices also cause high_below_low? No, because high==low, etc.
        # But zero_price should be present.
        assert "negative_volume" not in flags  # volume=0 is not negative
