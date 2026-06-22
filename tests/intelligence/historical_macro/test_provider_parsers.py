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

    def test_normalize_cpi_record(self):
        raw = {
            "series_id": "CUUR0000SA0",
            "year": "2023",
            "period": "M01",
            "value": "6.4",
            "footnotes": [{"text": "test"}],
        }
        event = self.provider.normalize_release(raw)
        assert event is not None
        assert event.event_family == "us_cpi"
        assert event.actual_initial == 6.4
        assert event.reference_period == "2023-01"

    def test_normalize_core_cpi(self):
        raw = {
            "series_id": "CUUR0000SA0L1E",
            "year": "2023",
            "period": "M01",
            "value": "5.6",
        }
        event = self.provider.normalize_release(raw)
        assert event is not None
        assert event.event_family == "us_core_cpi"
        assert event.actual_initial == 5.6

    def test_normalize_nonfarm_payrolls(self):
        raw = {
            "series_id": "CES0000000001",
            "year": "2023",
            "period": "M01",
            "value": "517",
        }
        event = self.provider.normalize_release(raw)
        assert event is not None
        assert event.event_family == "us_nonfarm_payrolls"
        assert event.actual_initial == 517.0

    def test_normalize_unemployment_rate(self):
        raw = {
            "series_id": "LNS14000000",
            "year": "2023",
            "period": "M01",
            "value": "3.4",
        }
        event = self.provider.normalize_release(raw)
        assert event is not None
        assert event.event_family == "us_unemployment_rate"
        assert event.actual_initial == 3.4

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

    def test_normalize_cpi(self):
        raw = {"series_id": "CPIAUCSL", "date": "2023-01-01", "value": 301.2}
        event = self.provider.normalize_release(raw)
        assert event is not None
        assert event.event_family == "us_cpi"
        assert event.reference_period == "2023-01"

    def test_normalize_unemployment(self):
        raw = {"series_id": "UNRATE", "date": "2023-01-01", "value": 3.4}
        event = self.provider.normalize_release(raw)
        assert event is not None
        assert event.event_family == "us_unemployment_rate"
        assert event.actual_initial == 3.4

    def test_null_value_returns_none(self):
        raw = {"series_id": "CPIAUCSL", "date": "2023-01-01", "value": None}
        event = self.provider.normalize_release(raw)
        assert event is None

    def test_unknown_series_returns_none(self):
        raw = {"series_id": "UNKNOWN", "date": "2023-01-01", "value": 1.0}
        event = self.provider.normalize_release(raw)
        assert event is None
