"""Test that real fixture data passes contract validation."""

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
    AssetClass,
    InstrumentType,
    Interval,
    DataQuality,
    validate_ohlc,
    utc_now,
)

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


class TestRealBinanceBarValidation:
    """Test that real Binance fixture data passes contract validation."""

    def load_kline_fixture(self, name: str) -> dict:
        path = FIXTURES_DIR / name
        if not path.exists():
            pytest.skip(f"Fixture not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_kline_full_24h_creates_valid_bars(self):
        fixture = self.load_kline_fixture("kline_fixture_full_24h.json")
        klines = fixture.get("klines", {})
        assert len(klines) > 0

        for symbol, rows in klines.items():
            for row in rows:
                open_time_ms, o, h, l, c, vol, close_time_ms = row
                bar = MarketBarV1(
                    instrument_id=f"binance_spot_{symbol.lower()}",
                    symbol=symbol,
                    venue="binance",
                    asset_class=AssetClass.CRYPTO.value,
                    instrument_type=InstrumentType.SPOT.value,
                    interval=Interval.H1.value,
                    open_time_utc="2026-06-15T12:00:00Z",
                    close_time_utc="2026-06-15T13:00:00Z",
                    open=float(o),
                    high=float(h),
                    low=float(l),
                    close=float(c),
                    volume=float(vol),
                    source_provider="binance_public_archive",
                    data_quality=DataQuality.EXACT_ARCHIVED.value,
                )
                errors = validate_ohlc(bar)
                assert errors == [], f"Bar {symbol} {row}: validation errors: {errors}"

    def test_kline_fixture_structure(self):
        fixture = self.load_kline_fixture("kline_fixture_full_24h.json")
        assert "fixture_id" in fixture
        assert "klines" in fixture

    def test_real_binance_sample_structure(self):
        fixture = self.load_kline_fixture("real_binance_response_sample.json")
        assert "response_sample" in fixture
        for entry in fixture["response_sample"]:
            assert float(entry["highPrice"]) >= float(entry["lowPrice"])


class TestGoldenFixtureContractValidation:
    def load_fixture(self, name):
        path = FIXTURES_DIR / name
        if not path.exists():
            pytest.skip(f"Fixture not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_golden_multi_asset_market_sync(self):
        fixture = self.load_fixture("golden_multi_asset_market_sync.json")
        signal = fixture["expected_signal"]
        assets = signal.get("metrics", {}).get("assets", [])
        for asset in assets:
            assert asset["price"] > 0


class TestContractFromRealData:
    def test_market_bar_from_realistic_data(self):
        bar = MarketBarV1(
            bar_id="real_001",
            instrument_id="binance_spot_btcusdt",
            symbol="BTCUSDT",
            venue="binance",
            asset_class=AssetClass.CRYPTO.value,
            instrument_type=InstrumentType.SPOT.value,
            interval=Interval.H1.value,
            open_time_utc="2026-06-15T06:00:00Z",
            close_time_utc="2026-06-15T07:00:00Z",
            open=89567.33,
            high=90500.00,
            low=88500.00,
            close=89000.00,
            volume=318592.3184,
            source_provider="binance_public_archive",
            data_quality=DataQuality.EXACT_ARCHIVED.value,
        )
        errors = validate_ohlc(bar)
        assert errors == []

    def test_derivative_snapshot_from_realistic_data(self):
        snap = DerivativeSnapshotV1(
            snapshot_id="real_snap_001",
            instrument_id="binance_futures_btcusdt_perp",
            symbol="BTCUSDT",
            venue="binance",
            observed_at_utc="2026-06-15T06:00:00Z",
            mark_price=89000.0,
            funding_rate=0.0001,
            open_interest=150000.5,
            source_provider="binance_public_api",
            data_quality=DataQuality.EXACT_PUBLIC_API.value,
        )
        assert snap.funding_rate == 0.0001

    def test_instrument_registry_from_realistic_data(self):
        reg = InstrumentRegistryV1(
            instrument_id="fred_us10y_yield",
            canonical_name="US 10-Year Treasury Yield",
            symbol="US10Y",
            venue="fred",
            asset_class=AssetClass.RATES.value,
            instrument_type=InstrumentType.YIELD.value,
            currency="USD",
            provider_symbols={"fred": "DGS10"},
        )
        assert reg.instrument_id == "fred_us10y_yield"
