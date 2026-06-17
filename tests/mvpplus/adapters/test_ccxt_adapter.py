"""Unit tests for CcxtPublicMarketAdapter — no live network.

Tests timeout config, kwargs support, normalization, and credential safety.
"""
import unittest, json
from unittest.mock import MagicMock, patch

from market_radar.external_adapters.ccxt_public_market_adapter import (
    CcxtPublicMarketAdapter, ALLOWLISTED_EXCHANGES, SUPPORTED_OPERATIONS,
    DEFAULT_EXCHANGE_TIMEOUT,
    _normalize_ticker, _normalize_ohlcv,
    _normalize_open_interest, _normalize_funding_rate,
)


# ── Timeout Configuration ──


class TestTimeoutConfig(unittest.TestCase):
    def test_default_timeout(self):
        adapter = CcxtPublicMarketAdapter()
        self.assertEqual(adapter._exchange_timeout, DEFAULT_EXCHANGE_TIMEOUT)

    def test_bounded_timeout(self):
        adapter = CcxtPublicMarketAdapter(exchange_timeout=999.0)
        self.assertLessEqual(adapter._exchange_timeout, 60.0)

    def test_min_timeout(self):
        adapter = CcxtPublicMarketAdapter(exchange_timeout=0.1)
        self.assertGreaterEqual(adapter._exchange_timeout, 1.0)

    def test_custom_timeout(self):
        adapter = CcxtPublicMarketAdapter(exchange_timeout=25.0)
        self.assertEqual(adapter._exchange_timeout, 25.0)


# ── Normalization ──


class TestNormalizeTicker(unittest.TestCase):
    def test_normalize_standard(self):
        raw = {
            "last": 50000.0, "bid": 49900.0, "ask": 50100.0,
            "baseVolume": 1000.0, "quoteVolume": 50_000_000.0,
            "high": 51000.0, "low": 49000.0, "percentage": -1.5,
        }
        result = _normalize_ticker(raw, "BTC/USDT")
        self.assertEqual(result["symbol"], "BTC/USDT")
        self.assertEqual(result["last"], 50000.0)
        self.assertEqual(result["changePct24h"], -1.5)
        self.assertIn("_raw", result)
        self.assertEqual(result["_raw"], raw)


class TestNormalizeOHLCV(unittest.TestCase):
    def test_normalize_standard(self):
        raw = [[1700000000000, 50000.0, 51000.0, 49000.0, 50500.0, 1000.0]]
        results = _normalize_ohlcv(raw, "BTC/USDT")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["symbol"], "BTC/USDT")
        self.assertEqual(results[0]["timestamp"], 1700000000000)
        self.assertEqual(results[0]["close"], 50500.0)
        self.assertEqual(results[0]["volume"], 1000.0)
        self.assertIn("_raw", results[0])

    def test_skips_short_rows(self):
        raw = [[1700000000000, 50000.0]]
        results = _normalize_ohlcv(raw, "BTC/USDT")
        self.assertEqual(len(results), 0)


class TestNormalizeOpenInterest(unittest.TestCase):
    def test_normalize_standard(self):
        raw = {"openInterest": 5000.0, "timestamp": 1700000000000, "baseVolume": 100.0}
        result = _normalize_open_interest(raw, "BTC/USDT")
        self.assertEqual(result["symbol"], "BTC/USDT")
        self.assertEqual(result["openInterest"], 5000.0)
        self.assertIn("_raw", result)


class TestNormalizeFundingRate(unittest.TestCase):
    def test_normalize_standard(self):
        raw = {
            "fundingRate": 0.0001, "fundingTimestamp": 1700000000000,
            "nextFundingRate": 0.0002, "interval": "8h",
        }
        result = _normalize_funding_rate(raw, "BTC/USDT")
        self.assertEqual(result["symbol"], "BTC/USDT")
        self.assertEqual(result["fundingRate"], 0.0001)
        self.assertEqual(result["interval"], "8h")
        self.assertIn("_raw", result)


# ── Exchange Allowlist ──


class TestExchangeAllowlist(unittest.TestCase):
    def test_allowlist_contains_required(self):
        for ex in {"binance", "okx", "bybit"}:
            self.assertIn(ex, ALLOWLISTED_EXCHANGES)

    def test_rejects_non_allowed(self):
        adapter = CcxtPublicMarketAdapter()
        adapter._ccxt_available = True
        result = adapter.fetch("kraken", "ticker", "BTC/USDT")
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "exchange_not_allowed")


# ── Unsupported Operations / Capabilities ──


class TestUnsupportedOperation(unittest.TestCase):
    def test_unsupported_operation(self):
        adapter = CcxtPublicMarketAdapter()
        adapter._ccxt_available = True
        result = adapter.fetch("binance", "unsupported_op", "BTC/USDT")
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "unsupported_operation")

    def test_unsupported_capability(self):
        adapter = CcxtPublicMarketAdapter()
        adapter._ccxt_available = True
        mock_ex = MagicMock()
        mock_ex.has = {"fetch_funding_rate": False}
        adapter._get_exchange = lambda ex_id: mock_ex

        result = adapter.fetch("binance", "funding_rate", "BTC/USDT")
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "unsupported_capability")


# ── Kwargs Support ──


class TestKwargsSupport(unittest.TestCase):
    def test_kwargs_passed_to_ticker(self):
        """If kwargs are provided for ticker, they should be forwarded to ccxt."""
        adapter = CcxtPublicMarketAdapter()
        adapter._ccxt_available = True
        mock_ex = MagicMock()
        mock_ex.has = {"fetch_ticker": True}
        mock_ex.fetch_ticker = MagicMock(return_value={"last": 50000})
        adapter._get_exchange = lambda ex_id: mock_ex

        result = adapter.fetch("binance", "ticker", "BTC/USDT", kwargs={"some_extra": True})
        mock_ex.fetch_ticker.assert_called_once_with("BTC/USDT", some_extra=True)
        self.assertTrue(result.ok)


class TestOHLCVKwargsOrder(unittest.TestCase):
    def test_ohlcv_timeframe_limit(self):
        """OHLCV should use the standard positional arg order: symbol, timeframe, limit."""
        adapter = CcxtPublicMarketAdapter()
        adapter._ccxt_available = True
        mock_ex = MagicMock()
        mock_ex.has = {"fetch_ohlcv": True}
        mock_ex.fetch_ohlcv = MagicMock(return_value=[])
        adapter._get_exchange = lambda ex_id: mock_ex

        result = adapter.fetch("binance", "ohlcv", "BTC/USDT",
                               kwargs={"timeframe": "15m", "limit": 5})
        mock_ex.fetch_ohlcv.assert_called_once_with("BTC/USDT", "15m", 5)
        self.assertTrue(result.ok)


# ── Normalization in Fetch ──


class TestNormalizationApplied(unittest.TestCase):
    def test_ticker_normalized(self):
        """A successful ticker fetch should return normalized data (not raw)."""
        adapter = CcxtPublicMarketAdapter()
        adapter._ccxt_available = True
        mock_ex = MagicMock()
        mock_ex.has = {"fetch_ticker": True}
        mock_ex.fetch_ticker = MagicMock(return_value={
            "last": 50000.0, "bid": 49900.0, "ask": 50100.0,
            "baseVolume": 1000.0, "quoteVolume": 50_000_000.0,
            "high": 51000.0, "low": 49000.0, "percentage": -1.23,
        })
        adapter._get_exchange = lambda ex_id: mock_ex

        result = adapter.fetch("binance", "ticker", "BTC/USDT")
        self.assertTrue(result.ok)
        self.assertIn("last", result.data)
        self.assertIn("_raw", result.data)
        self.assertEqual(result.data["symbol"], "BTC/USDT")

    def test_ohlcv_normalized(self):
        adapter = CcxtPublicMarketAdapter()
        adapter._ccxt_available = True
        mock_ex = MagicMock()
        mock_ex.has = {"fetch_ohlcv": True}
        mock_ex.fetch_ohlcv = MagicMock(return_value=[[1700000000000, 100.0, 110.0, 90.0, 105.0, 500.0]])
        adapter._get_exchange = lambda ex_id: mock_ex

        result = adapter.fetch("binance", "ohlcv", "ETH/USDT")
        self.assertTrue(result.ok)
        self.assertIsInstance(result.data, list)
        self.assertEqual(result.data[0]["close"], 105.0)
        self.assertIn("_raw", result.data[0])


# ── No Private Endpoints ──


class TestNoPrivateEndpoints(unittest.TestCase):
    def test_no_order_withdraw_transfer_methods(self):
        import market_radar.external_adapters.ccxt_public_market_adapter as mod
        with open(mod.__file__, "r", encoding="utf-8") as f:
            source = f.read()
        import ast
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for term in ["create_order", "cancel_order", "withdraw", "transfer"]:
                    if term in node.name.lower():
                        self.fail(f"Prohibited function found: {node.name}")
        for term in ["apiKey", "api_key", "apiSecret", "api_secret", "password", "private_key"]:
            if term + "=" in source or term + ":" in source:
                self.assertNotIn(term + "=", source.replace('"', '').replace("'", ''), f"Credential term found: {term}")


# ── No Credential Parameters ──


class TestAdapterPublicAPI(unittest.TestCase):
    def test_fetch_has_no_credential_params(self):
        import inspect
        sig = inspect.signature(CcxtPublicMarketAdapter.fetch)
        param_names = [p.lower() for p in sig.parameters]
        for name in ["apikey", "secret", "password", "credential"]:
            self.assertNotIn(name, param_names)


# ── Dependency Missing ──


class TestDependencyMissing(unittest.TestCase):
    def test_ccxt_not_installed_graceful(self):
        adapter = CcxtPublicMarketAdapter()
        adapter._ccxt_available = False
        result = adapter.fetch("binance", "ticker", "BTC/USDT")
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "dependency_missing")


# ── AdapterHealth ──


class TestAdapterHealthPresence(unittest.TestCase):
    def test_health_on_success(self):
        adapter = CcxtPublicMarketAdapter()
        adapter._ccxt_available = True
        mock_ex = MagicMock()
        mock_ex.has = {"fetch_ticker": True}
        mock_ex.fetch_ticker = MagicMock(return_value={"last": 50000.0})
        adapter._get_exchange = lambda ex_id: mock_ex
        result = adapter.fetch("binance", "ticker", "BTC/USDT")
        self.assertIsNotNone(result.health)
        self.assertTrue(result.health.available)

    def test_health_on_failure(self):
        adapter = CcxtPublicMarketAdapter()
        adapter._ccxt_available = True
        result = adapter.fetch("unknown_exchange", "ticker", "BTC/USDT")
        self.assertIsNotNone(result.health)
        self.assertFalse(result.health.available)


if __name__ == "__main__":
    unittest.main()
