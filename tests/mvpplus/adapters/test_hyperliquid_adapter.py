"""Unit tests for HyperliquidPublicAdapter — no live network."""
import json, unittest
from unittest.mock import MagicMock, patch

from market_radar.external_adapters.hyperliquid_public_adapter import (
    HyperliquidPublicAdapter, OPERATIONS, PUBLIC_OPERATIONS,
)


class FakeResponse:
    def __init__(self, json_data):
        self._json_data = json_data
        self.status_code = 200

    def json(self):
        return self._json_data


class TestSDKSuccessPath(unittest.TestCase):
    @patch("market_radar.external_adapters.hyperliquid_public_adapter.HyperliquidPublicAdapter._check_sdk")
    @patch("market_radar.external_adapters.hyperliquid_public_adapter.HyperliquidPublicAdapter._sdk_fetch")
    def test_sdk_all_mids(self, mock_sdk_fetch, mock_check_sdk):
        mock_check_sdk.return_value = True
        mock_sdk_fetch.return_value = {"data": {"BTC": 50000}, "latency_ms": 42.0, "source": "sdk"}

        adapter = HyperliquidPublicAdapter()
        result = adapter.fetch("allMids")
        self.assertTrue(result.ok)
        self.assertEqual(result.data, {"BTC": 50000})
        self.assertEqual(result.provenance.source, "sdk")
        adapter.close()


class TestSDKUnavailableRawFallback(unittest.TestCase):
    @patch("market_radar.external_adapters.hyperliquid_public_adapter.HyperliquidPublicAdapter._check_sdk")
    @patch("market_radar.external_adapters.hyperliquid_public_adapter.HyperliquidPublicAdapter._raw_fetch")
    def test_sdk_unavailable_falls_back(self, mock_raw, mock_check_sdk):
        mock_check_sdk.return_value = False
        mock_raw.return_value.ok = True
        mock_raw.return_value.data = {"mids": {"BTC": "50000"}}
        mock_raw.return_value.provenance = MagicMock(source="raw_http_fallback")

        adapter = HyperliquidPublicAdapter()
        # Force raw_fetch to return a proper result
        from market_radar.external_adapters.adapter_models import AdapterResult, AdapterProvenance
        mock_raw.return_value = AdapterResult(
            ok=True, data={"mids": {"BTC": "50000"}},
            provenance=AdapterProvenance(source="raw_http_fallback", method="allMids"),
        )

        result = adapter.fetch("allMids")
        self.assertTrue(result.ok)
        self.assertEqual(result.provenance.source, "raw_http_fallback")
        adapter.close()


class TestAllOperationPayloads(unittest.TestCase):
    def test_operations_defined(self):
        """All five required operations have payloads."""
        required = {"allMids", "meta", "clearinghouseState", "spotClearinghouseState", "fundingHistory"}
        for op in required:
            self.assertIn(op, OPERATIONS, f"Missing payload for {op}")
            self.assertIsNotNone(OPERATIONS[op])

    def test_public_operations_subset(self):
        for op in PUBLIC_OPERATIONS:
            self.assertIn(op, OPERATIONS)


class TestNoWalletOrTradingImports(unittest.TestCase):
    def test_no_wallet_or_exchange_class_imported(self):
        """HyperliquidPublicAdapter must not import wallet, exchange or signing."""
        import market_radar.external_adapters.hyperliquid_public_adapter as mod
        import ast
        with open(mod.__file__, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.lower()
                    for term in ["wallet", "exchange", "signing", "order"]:
                        if term in name:
                            self.fail(f"Prohibited import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    name = node.module.lower()
                    for term in ["wallet", "exchange", "signing", "order"]:
                        if term in name:
                            self.fail(f"Prohibited from-import: {node.module}")
        # Also check for prohibited class/function definitions
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                for term in ["Wallet", "Exchange", "Signing", "Order", "Trade"]:
                    if term in node.name:
                        self.fail(f"Prohibited definition: {node.name}")


class TestAdapterPublicAPI(unittest.TestCase):
    def test_fetch_has_no_credential_params(self):
        import inspect
        sig = inspect.signature(HyperliquidPublicAdapter.fetch)
        for p in sig.parameters:
            self.assertNotIn("key", p.lower())
            self.assertNotIn("secret", p.lower())
            self.assertNotIn("password", p.lower())
            self.assertNotIn("credential", p.lower())


if __name__ == "__main__":
    unittest.main()
