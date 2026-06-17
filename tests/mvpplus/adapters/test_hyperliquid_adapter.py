"""Unit tests for HyperliquidPublicAdapter — no live network.

Tests the five parameterized read-only methods, input validation,
SDK/HTTP fallback, and AdapterHealth presence.
"""
import json, unittest
from unittest.mock import MagicMock, patch

from market_radar.external_adapters.hyperliquid_public_adapter import (
    HyperliquidPublicAdapter,
    validate_ethereum_address,
    validate_coin,
    validate_time_range,
)
from market_radar.external_adapters.adapter_models import AdapterResult


# ── Validation Unit Tests ──


class TestValidateEthereumAddress(unittest.TestCase):
    def test_valid_hex_address(self):
        addr = "0x1234567890abcdef1234567890abcdef12345678"
        self.assertIsNone(validate_ethereum_address(addr))

    def test_valid_mixed_case(self):
        addr = "0xAbCdEf1234567890AbCdEf1234567890AbCdEf12"
        self.assertIsNone(validate_ethereum_address(addr))

    def test_empty_string(self):
        self.assertIsNotNone(validate_ethereum_address(""))

    def test_short_address(self):
        self.assertIsNotNone(validate_ethereum_address("0x1234"))

    def test_no_prefix(self):
        self.assertIsNotNone(validate_ethereum_address("1234567890abcdef1234567890abcdef12345678"))

    def test_non_string(self):
        self.assertIsNotNone(validate_ethereum_address(123))


class TestValidateCoin(unittest.TestCase):
    def test_valid_coin(self):
        self.assertIsNone(validate_coin("BTC"))

    def test_empty_string(self):
        self.assertIsNotNone(validate_coin(""))

    def test_non_string(self):
        self.assertIsNotNone(validate_coin(123))


class TestValidateTimeRange(unittest.TestCase):
    def test_valid_range(self):
        self.assertIsNone(validate_time_range(1700000000000, 1700086400000))

    def test_without_end(self):
        self.assertIsNone(validate_time_range(1700000000000))

    def test_negative_start(self):
        self.assertIsNotNone(validate_time_range(-1, 1700086400000))

    def test_start_gt_end(self):
        self.assertIsNotNone(validate_time_range(1700086400000, 1700000000000))

    def test_equal_start_end(self):
        self.assertIsNone(validate_time_range(1700000000000, 1700000000000))

    def test_negative_end(self):
        self.assertIsNotNone(validate_time_range(1700000000000, -1))

    def test_non_integer_start(self):
        self.assertIsNotNone(validate_time_range("abc", 1700086400000))


# ── SDK Mock Helpers ──


def _make_sdk_result(data, latency=15.0):
    return {"data": data, "latency_ms": latency, "source": "sdk"}


# ── SDK Success Path ──


class TestFetchAllMidsSDK(unittest.TestCase):
    @patch.object(HyperliquidPublicAdapter, "_check_sdk")
    @patch.object(HyperliquidPublicAdapter, "_sdk_call")
    def test_all_mids_from_sdk(self, mock_sdk_call, mock_check_sdk):
        mock_check_sdk.return_value = True
        mock_sdk_call.return_value = _make_sdk_result({"BTC": 50000.0, "ETH": 3200.0})

        adapter = HyperliquidPublicAdapter()
        result = adapter.fetch_all_mids()
        self.assertTrue(result.ok)
        self.assertEqual(result.data, {"BTC": 50000.0, "ETH": 3200.0})
        self.assertEqual(result.provenance.source, "sdk")
        self.assertIsNotNone(result.health)
        self.assertTrue(result.health.available)
        adapter.close()


class TestFetchMetaSDK(unittest.TestCase):
    @patch.object(HyperliquidPublicAdapter, "_check_sdk")
    @patch.object(HyperliquidPublicAdapter, "_sdk_call")
    def test_meta_from_sdk(self, mock_sdk_call, mock_check_sdk):
        mock_check_sdk.return_value = True
        mock_sdk_call.return_value = _make_sdk_result([{"name": "BTC", "szDecimal": 5}])

        adapter = HyperliquidPublicAdapter()
        result = adapter.fetch_meta()
        self.assertTrue(result.ok)
        self.assertEqual(result.data[0]["name"], "BTC")
        self.assertEqual(result.provenance.source, "sdk")
        self.assertTrue(result.health.available)
        adapter.close()


# ── Clearinghouse State Tests ──


class TestClearinghouseStateValidation(unittest.TestCase):
    def test_invalid_address_rejected(self):
        adapter = HyperliquidPublicAdapter()
        result = adapter.fetch_clearinghouse_state("not-an-address")
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "validation_error")
        self.assertFalse(result.health.available)
        adapter.close()

    def test_valid_address_propagated(self):
        """With no SDK, a valid address should attempt raw HTTP fallback."""
        adapter = HyperliquidPublicAdapter()
        adapter._check_sdk = MagicMock(return_value=False)
        adapter._raw_post = MagicMock(return_value=AdapterResult(ok=False, error=MagicMock()))

        result = adapter.fetch_clearinghouse_state(
            "0x1234567890abcdef1234567890abcdef12345678"
        )
        adapter._raw_post.assert_called_once()
        adapter.close()


class TestSpotClearinghouseStateValidation(unittest.TestCase):
    def test_invalid_address_rejected(self):
        adapter = HyperliquidPublicAdapter()
        result = adapter.fetch_spot_clearinghouse_state("bad-addr")
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "validation_error")
        adapter.close()


# ── Funding History ──


class TestFundingHistoryValidation(unittest.TestCase):
    def test_empty_coin_rejected(self):
        adapter = HyperliquidPublicAdapter()
        result = adapter.fetch_funding_history("", 1700000000000)
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "validation_error")

    def test_start_before_end_rejected(self):
        adapter = HyperliquidPublicAdapter()
        result = adapter.fetch_funding_history("BTC", 1700086400000, 1700000000000)
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "validation_error")

    def test_negative_start_rejected(self):
        adapter = HyperliquidPublicAdapter()
        result = adapter.fetch_funding_history("BTC", -1, 1700086400000)
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "validation_error")

    def test_valid_funding_history(self):
        adapter = HyperliquidPublicAdapter()
        adapter._check_sdk = MagicMock(return_value=False)
        adapter._raw_post = MagicMock(return_value=AdapterResult(ok=False, error=MagicMock()))

        result = adapter.fetch_funding_history("ETH", 1700000000000, 1700086400000)
        adapter._raw_post.assert_called_once()
        adapter.close()

    def test_valid_funding_history_no_end(self):
        adapter = HyperliquidPublicAdapter()
        adapter._check_sdk = MagicMock(return_value=False)
        adapter._raw_post = MagicMock(return_value=AdapterResult(ok=False, error=MagicMock()))

        result = adapter.fetch_funding_history("SOL", 1700000000000)
        adapter._raw_post.assert_called_once()
        adapter.close()


# ── SDK Unavailable / Raw Fallback ──


class TestSDKUnavailableRawFallback(unittest.TestCase):
    @patch.object(HyperliquidPublicAdapter, "_check_sdk")
    @patch.object(HyperliquidPublicAdapter, "_raw_post")
    def test_sdk_unavailable_falls_back(self, mock_raw, mock_check_sdk):
        mock_check_sdk.return_value = False
        from market_radar.external_adapters.adapter_models import AdapterProvenance
        mock_raw.return_value = AdapterResult(
            ok=True, data={"mids": {"BTC": "50000"}},
            provenance=AdapterProvenance(source="raw_http_fallback", method="allMids"),
        )

        adapter = HyperliquidPublicAdapter()
        result = adapter.fetch_all_mids()
        self.assertTrue(result.ok)
        self.assertEqual(result.provenance.source, "raw_http_fallback")
        adapter.close()


class TestBothFail(unittest.TestCase):
    @patch.object(HyperliquidPublicAdapter, "_check_sdk")
    @patch.object(HyperliquidPublicAdapter, "_raw_post")
    def test_both_fail(self, mock_raw, mock_check_sdk):
        mock_check_sdk.return_value = False
        mock_raw.return_value = AdapterResult(
            ok=False,
            error=MagicMock(code="network", message="timeout"),
        )

        adapter = HyperliquidPublicAdapter()
        result = adapter.fetch_all_mids()
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "unavailable")
        adapter.close()


# ── No Wallet / Exchange / Trading Imports ──


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
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                for term in ["Wallet", "Exchange", "Signing", "Order", "Trade"]:
                    if term in node.name:
                        self.fail(f"Prohibited definition: {node.name}")


# ── No Credential Parameters ──


class TestAdapterPublicAPI(unittest.TestCase):
    def test_no_credential_params(self):
        """No fetch_* method should accept key/secret/password."""
        import inspect
        for method_name in ["fetch_all_mids", "fetch_meta",
                            "fetch_clearinghouse_state", "fetch_spot_clearinghouse_state",
                            "fetch_funding_history"]:
            method = getattr(HyperliquidPublicAdapter, method_name, None)
            if method is not None:
                sig = inspect.signature(method)
                param_names = [p.lower() for p in sig.parameters]
                for bad in ["key", "secret", "password", "credential"]:
                    self.assertNotIn(bad, param_names, f"{method_name} has prohibited param: {bad}")


# ── AdapterHealth Presence ──


class TestAdapterHealthPresence(unittest.TestCase):
    def test_health_on_success(self):
        adapter = HyperliquidPublicAdapter()
        adapter._check_sdk = MagicMock(return_value=False)
        from market_radar.external_adapters.adapter_models import AdapterProvenance
        adapter._raw_post = MagicMock(return_value=AdapterResult(
            ok=True, data={"BTC": 50000},
            provenance=AdapterProvenance(source="raw_http_fallback", method="allMids",
                                         latency_ms=10.0),
        ))
        result = adapter.fetch_all_mids()
        self.assertIsNotNone(result.health)
        self.assertTrue(result.health.available)
        self.assertEqual(result.health.source, "raw_http_fallback")

    def test_health_on_failure(self):
        adapter = HyperliquidPublicAdapter()
        adapter._check_sdk = MagicMock(return_value=False)
        adapter._raw_post = MagicMock(return_value=AdapterResult(
            ok=False,
            error=MagicMock(code="network", message="connection failed"),
        ))
        result = adapter.fetch_all_mids()
        self.assertIsNotNone(result.health)
        self.assertFalse(result.health.available)


if __name__ == "__main__":
    unittest.main()
