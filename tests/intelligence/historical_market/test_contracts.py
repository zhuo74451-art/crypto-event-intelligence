"""Test contract creation, JSON serialization/deserialization, field defaults."""

import sys
import json
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest
from market_radar.intelligence.acquisition.historical_market.contracts import (
    MarketBarV1,
    DerivativeSnapshotV1,
    InstrumentRegistryV1,
    EventMarketWindowV1,
    MarketReactionLabelV1,
    SourceSnapshotV1,
    AssetClass,
    InstrumentType,
    Interval,
    DataQuality,
    LabelDirection,
    LabelAvailability,
    ExactOrProxy,
    validate_ohlc,
)


class TestMarketBarV1:
    def test_defaults(self):
        bar = MarketBarV1()
        assert bar.contract_name == "MarketBarV1"
        assert bar.schema_version == "1.0.0"
        assert bar.asset_class == AssetClass.CRYPTO.value
        assert bar.instrument_type == InstrumentType.SPOT.value
        assert bar.interval == Interval.H1.value
        assert bar.quote_currency == "USDT"
        assert bar.data_quality == DataQuality.MISSING.value
        assert bar.bar_id == ""
        assert bar.open == 0.0
        assert bar.high == 0.0
        assert bar.low == 0.0
        assert bar.close == 0.0
        assert bar.volume == 0.0
        assert bar.quote_volume == 0.0
        assert bar.trade_count == 0
        assert bar.quality_flags == []

    def test_create_with_values(self):
        bar = MarketBarV1(
            bar_id="test123",
            instrument_id="binance_spot_btcusdt",
            symbol="BTCUSDT",
            venue="binance",
            asset_class=AssetClass.CRYPTO.value,
            instrument_type=InstrumentType.SPOT.value,
            interval=Interval.M5.value,
            open_time_utc="2026-06-15T12:00:00Z",
            close_time_utc="2026-06-15T12:05:00Z",
            open=68000.0,
            high=68100.0,
            low=67950.0,
            close=68050.0,
            volume=100.5,
            quote_volume=6800000.0,
            trade_count=42,
            source_provider="binance_public_archive",
            data_quality=DataQuality.EXACT_ARCHIVED.value,
        )
        assert bar.bar_id == "test123"
        assert bar.open == 68000.0
        assert bar.high == 68100.0

    def test_to_json_round_trip(self):
        bar = MarketBarV1(
            bar_id="rt123",
            instrument_id="binance_spot_ethusdt",
            symbol="ETHUSDT",
            venue="binance",
            interval=Interval.M15.value,
            open_time_utc="2026-06-15T12:00:00Z",
            close_time_utc="2026-06-15T12:15:00Z",
            open=3500.0,
            high=3520.0,
            low=3490.0,
            close=3510.0,
            volume=500.0,
            quality_flags=["zero_price"],
        )
        data = bar.to_json()
        assert isinstance(data, dict)
        assert data["bar_id"] == "rt123"
        restored = MarketBarV1.from_json(data)
        assert restored.bar_id == bar.bar_id
        assert restored.open == bar.open
        assert restored.quality_flags == ["zero_price"]

    def test_from_json_ignores_extra_fields(self):
        data = {
            "bar_id": "extra123",
            "instrument_id": "test",
            "open": 100.0,
            "high": 110.0,
            "low": 90.0,
            "close": 105.0,
            "volume": 10.0,
            "unknown_field": "should_be_ignored",
        }
        bar = MarketBarV1.from_json(data)
        assert bar.bar_id == "extra123"

    def test_json_serializable(self):
        bar = MarketBarV1(
            bar_id="json_test",
            instrument_id="test",
            open=100.0, high=110.0, low=90.0, close=105.0,
        )
        dumped = json.dumps(bar.to_json())
        loaded = json.loads(dumped)
        assert loaded["bar_id"] == "json_test"
        assert loaded["open"] == 100.0


class TestDerivativeSnapshotV1:
    def test_defaults(self):
        snap = DerivativeSnapshotV1()
        assert snap.contract_name == "DerivativeSnapshotV1"
        assert snap.funding_rate is None
        assert snap.open_interest is None

    def test_to_json_round_trip(self):
        snap = DerivativeSnapshotV1(
            snapshot_id="snap1",
            instrument_id="binance_futures_btcusdt_perp",
            symbol="BTCUSDT",
            venue="binance",
            observed_at_utc="2026-06-15T12:00:00Z",
            funding_rate=0.0001,
            open_interest=15000.5,
        )
        data = snap.to_json()
        restored = DerivativeSnapshotV1.from_json(data)
        assert restored.snapshot_id == "snap1"
        assert restored.funding_rate == 0.0001


class TestInstrumentRegistryV1:
    def test_defaults(self):
        reg = InstrumentRegistryV1()
        assert reg.timezone == "UTC"
        assert reg.exact_or_proxy == ExactOrProxy.EXACT.value

    def test_to_json_round_trip(self):
        reg = InstrumentRegistryV1(
            instrument_id="fred_us10y_yield",
            canonical_name="US 10-Year Treasury Yield",
            symbol="US10Y",
            venue="fred",
            asset_class=AssetClass.RATES.value,
            instrument_type=InstrumentType.YIELD.value,
            currency="USD",
        )
        data = reg.to_json()
        restored = InstrumentRegistryV1.from_json(data)
        assert restored.instrument_id == "fred_us10y_yield"


class TestEventMarketWindowV1:
    def test_defaults(self):
        win = EventMarketWindowV1()
        assert win.bar_interval == Interval.M5.value
        assert win.source_refs == []

    def test_to_json_round_trip(self):
        win = EventMarketWindowV1(
            window_id="win1",
            event_id="evt001",
            event_time_utc="2026-06-15T18:00:00Z",
            instrument_id="binance_spot_btcusdt",
            bars_expected=100,
            bars_present=95,
            coverage_ratio=0.95,
        )
        data = win.to_json()
        restored = EventMarketWindowV1.from_json(data)
        assert restored.window_id == "win1"
        assert restored.coverage_ratio == 0.95


class TestMarketReactionLabelV1:
    def test_defaults(self):
        lbl = MarketReactionLabelV1()
        assert lbl.direction_5m == LabelDirection.NEUTRAL.value
        assert lbl.label_availability == LabelAvailability.MISSING.value

    def test_to_json_round_trip(self):
        lbl = MarketReactionLabelV1(
            label_id="lbl1",
            event_id="evt001",
            instrument_id="binance_spot_btcusdt",
            event_time_utc="2026-06-15T18:00:00Z",
            return_5m=0.002,
            direction_5m=LabelDirection.POSITIVE.value,
        )
        data = lbl.to_json()
        restored = MarketReactionLabelV1.from_json(data)
        assert restored.label_id == "lbl1"


class TestSourceSnapshotV1:
    def test_defaults(self):
        ss = SourceSnapshotV1()
        assert ss.success is False
        assert ss.byte_size == 0

    def test_to_json_round_trip(self):
        ss = SourceSnapshotV1(
            source_snapshot_id="src1",
            source_provider="binance_public_archive",
            url="https://data.binance.vision/test.zip",
            retrieved_at_utc="2026-06-15T12:00:00Z",
            source_data_type="klines",
            success=True,
            record_count=720,
        )
        data = ss.to_json()
        restored = SourceSnapshotV1.from_json(data)
        assert restored.source_snapshot_id == "src1"
        assert restored.success is True
