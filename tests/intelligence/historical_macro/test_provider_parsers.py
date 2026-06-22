"""Tests for provider parsers - verifying BLS, FRED, and other provider parsing."""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from market_radar.intelligence.acquisition.historical_macro.contracts import (
    MacroReleaseEventV1,
    EventFamily,
)
from market_radar.intelligence.acquisition.historical_macro.providers.bls import BLSProvider, BLS_SERIES_MAP
from market_radar.intelligence.acquisition.historical_macro.providers.fred_alfred import FREDAlfredProvider, FRED_SERIES_MAP


class TestBLSProviderParser:
    def setup_method(self):
        self.provider = BLSProvider()

    def test_series_map_has_required_families(self):
        families = {v["family"] for v in BLS_SERIES_MAP.values()}
        assert "us_cpi" in families
        assert "us_core_cpi" in families
        assert "us_nonfarm_payrolls" in families
        assert "us_unemployment_rate" in families

    def test_series_map_cpi(self):
        assert "CUUR0000SA0" in BLS_SERIES_MAP
        assert BLS_SERIES_MAP["CUUR0000SA0"]["family"] == "us_cpi"

    def test_series_map_core_cpi(self):
        assert "CUUR0000SA0L1E" in BLS_SERIES_MAP

    def test_series_map_nfp(self):
        assert "CES0000000001" in BLS_SERIES_MAP

    def test_series_map_unemp(self):
        assert "LNS14000000" in BLS_SERIES_MAP

    def test_unknown_series_returns_none(self):
        raw = {
            "series_id": "UNKNOWNSERIES",
            "year": "2023",
            "period": "M01",
            "value": "1.0",
        }
        event = self.provider.normalize_release(raw)
        assert event is None


class TestFREDProviderParser:
    def setup_method(self):
        self.provider = FREDAlfredProvider()

    def test_series_map_has_required_families(self):
        families = {v["family"] for v in FRED_SERIES_MAP.values()}
        assert "us_cpi" in families
        assert "us_core_cpi" in families
        assert "us_nonfarm_payrolls" in families
        assert "us_unemployment_rate" in families
        assert "us_core_pce" in families
        assert "us_fomc_rate_decision" in families

    def test_fred_series_map(self):
        assert "CPIAUCSL" in FRED_SERIES_MAP

    def test_fred_series_map_unemp(self):
        assert "UNRATE" in FRED_SERIES_MAP
        assert FRED_SERIES_MAP["UNRATE"]["family"] == "us_unemployment_rate"

    def test_null_value_returns_none(self):
        raw = {"series_id": "CPIAUCSL", "date": "2023-01-01", "value": None}
        event = self.provider.normalize_release(raw)
        assert event is None

    def test_unknown_series_returns_none(self):
        raw = {"series_id": "UNKNOWN", "date": "2023-01-01", "value": 1.0}
        event = self.provider.normalize_release(raw)
        assert event is None
