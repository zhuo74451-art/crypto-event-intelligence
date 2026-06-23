"""Test parsing of Binance kline rows and FRED text format."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest
from market_radar.intelligence.acquisition.historical_market.contracts import (
    MarketBarV1,
)
from market_radar.intelligence.acquisition.historical_market.providers.crypto_archive import (
    _parse_binance_kline,
)
from market_radar.intelligence.acquisition.historical_market.providers.fred_csv import (
    FredCsvProvider,
    FRED_SERIES,
)


class TestParseBinanceKline:
    def test_parse_valid_kline(self):
        """Parse a standard Binance kline row."""
        raw = [
            "1781524800000",    # open_time_ms
            "68000.00",         # open
            "68100.00",         # high
            "67900.00",         # low
            "68050.00",         # close
            "100.5",            # volume
            "1781524860000",    # close_time_ms
            "6800000.0",        # quote_volume
            "42",               # trade_count
            "500000.0",         # taker_buy_base_vol
            "4800000.0",        # taker_buy_quote_vol
            "ignore",           # extra field
        ]
        result = _parse_binance_kline(raw, "BTCUSDT", "1m")
        assert result is not None
        assert result["symbol"] == "BTCUSDT"
        assert result["open"] == 68000.0
        assert result["high"] == 68100.0
        assert result["low"] == 67900.0
        assert result["close"] == 68050.0
        assert result["volume"] == 100.5
        assert result["quote_volume"] == 6800000.0
        assert result["trade_count"] == 42
        assert result["open_time_utc"].endswith("Z")
        assert result["close_time_utc"].endswith("Z")

    def test_parse_empty_list(self):
        result = _parse_binance_kline([], "BTCUSDT", "1m")
        assert result is None

    def test_parse_too_few_elements(self):
        result = _parse_binance_kline(["1", "2", "3"], "BTCUSDT", "1m")
        assert result is None

    def test_parse_invalid_number(self):
        raw = ["abc", "xyz", "def", "ghi", "jkl", "mno", "pqr", "stu", "vwx", "yza", "bcd"]
        result = _parse_binance_kline(raw, "BTCUSDT", "1m")
        assert result is None

    def test_parse_return_structure(self):
        raw = ["1000", "10.0", "20.0", "5.0", "15.0", "50.0", "2000", "750.0", "10", "25.0", "500.0"]
        result = _parse_binance_kline(raw, "SOLUSDT", "5m")
        assert result is not None
        assert isinstance(result["open"], float)
        assert isinstance(result["high"], float)
        assert isinstance(result["low"], float)
        assert isinstance(result["close"], float)
        assert isinstance(result["volume"], float)
        assert isinstance(result["quote_volume"], float)
        assert isinstance(result["trade_count"], int)
        assert isinstance(result["open_time_utc"], str)
        assert isinstance(result["close_time_utc"], str)


class TestFredCsvParsing:
    def test_parse_fred_text(self):
        """Parse FRED text format with headers and data rows."""
        fred_text = """Some header line
More header info
DATE                VALUE
2026-06-10          4.25
2026-06-11          4.26
2026-06-12          .
2026-06-13          4.24
2026-06-14          NA
2026-06-15          4.23
"""
        series_info = FRED_SERIES["DGS10"]
        # Create a minimal mock provider to access _parse_fred_text
        # We'll use a simpler approach: instantiate with dummy paths
        from pathlib import Path
        provider = FredCsvProvider(
            cache_dir=Path("/tmp/test_cache_fred"),
            output_dir=Path("/tmp/test_output_fred"),
        )
        bars = provider._parse_fred_text(fred_text, series_info)
        assert len(bars) == 4  # skips "." and "NA" rows
        assert bars[0].open_time_utc == "2026-06-10T00:00:00Z"
        assert bars[0].close == 4.25
        assert bars[1].close == 4.26
        assert bars[2].close == 4.24
        assert bars[3].close == 4.23
        assert all(b.interval == "1d" for b in bars)
        assert all(b.venue == "fred" for b in bars)

    def test_parse_fred_empty(self):
        provider = FredCsvProvider(
            cache_dir=Path("/tmp/test_cache_fred"),
            output_dir=Path("/tmp/test_output_fred"),
        )
        bars = provider._parse_fred_text("NO DATA HERE", {})
        assert bars == []

    def test_parse_fred_invalid_values(self):
        fred_text = """DATE                VALUE
2026-06-10          invalid
2026-06-11          4.25
"""
        from pathlib import Path
        provider = FredCsvProvider(
            cache_dir=Path("/tmp/test_cache_fred"),
            output_dir=Path("/tmp/test_output_fred"),
        )
        bars = provider._parse_fred_text(fred_text, FRED_SERIES["DGS10"])
        assert len(bars) == 1
        assert bars[0].close == 4.25
