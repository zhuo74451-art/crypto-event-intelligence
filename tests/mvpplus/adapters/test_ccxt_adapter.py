"""Unit tests for CcxtPublicMarketAdapter — no live network."""
import unittest, json
from unittest.mock import MagicMock, patch

from market_radar.external_adapters.ccxt_public_market_adapter import (
    CcxtPublicMarketAdapter, ALLOWLISTED_EXCHANGES, SUPPORTED_OPERATIONS,
)


class TestExchangeAllowlist(unittest.TestCase):
    def test_allowlist_contains_required(self):
        for ex in {"binance", "okx", "bybit"}:
            self.assertIn(ex, ALLOWLISTED_EXCHANGES)

    def test_rejects_non_allowed(self):
        adapter = CcxtPublicMarketAdapter()
        # Without CCXT installed, this will fail with dependency_missing, not exchange_not_allowed
        # Test the rejection logic directly
        adapter._ccxt_available = True
        result = adapter.fetch("kraken", "ticker", "BTC/USDT")
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "exchange_not_allowed")


class TestUnsupportedCapability(unittest.TestCase):
    def test_unsupported_operation(self):
        adapter = CcxtPublicMarketAdapter()
        adapter._ccxt_available = True
        result = adapter.fetch("binance", "unsupported_op", "BTC/USDT")
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "unsupported_operation")

    def test_unsupported_capability(self):
        """Simulate exchange that doesn't support a method."""
        adapter = CcxtPublicMarketAdapter()
        adapter._ccxt_available = True
        # Mock an exchange without the method
        mock_ex = MagicMock()
        mock_ex.has = {"fetch_funding_rate": False}
        adapter._get_exchange = lambda ex_id: mock_ex

        result = adapter.fetch("binance", "funding_rate", "BTC/USDT")
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "unsupported_capability")


class TestNoPrivateEndpoints(unittest.TestCase):
    def test_no_order_withdraw_transfer_methods(self):
        import market_radar.external_adapters.ccxt_public_market_adapter as mod
        with open(mod.__file__, "r", encoding="utf-8") as f:
            source = f.read()
        # Scan for code-level patterns (not docstring words)
        import ast
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for term in ["create_order", "cancel_order", "withdraw", "transfer"]:
                    if term in node.name.lower():
                        self.fail(f"Prohibited function found: {node.name}")
        # Check no credential parameter names
        for term in ["apiKey", "api_key", "apiSecret", "api_secret", "password", "private_key"]:
            # Only check in function signatures and class attributes, not docstrings
            if f'"{term}"' in source or f"'{term}'" in source:
                pass  # string literal in docstring is OK
            if term + "=" in source or term + ":" in source:
                self.assertNotIn(term + "=", source.replace('"', '').replace("'", ''), f"Credential term found: {term}")


class TestAdapterPublicAPI(unittest.TestCase):
    def test_fetch_has_no_credential_params(self):
        import inspect
        sig = inspect.signature(CcxtPublicMarketAdapter.fetch)
        param_names = [p.lower() for p in sig.parameters]
        for name in ["apikey", "secret", "password", "credential"]:
            self.assertNotIn(name, param_names)


class TestDependencyMissing(unittest.TestCase):
    def test_ccxt_not_installed_graceful(self):
        adapter = CcxtPublicMarketAdapter()
        adapter._ccxt_available = False
        result = adapter.fetch("binance", "ticker", "BTC/USDT")
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "dependency_missing")


if __name__ == "__main__":
    unittest.main()
