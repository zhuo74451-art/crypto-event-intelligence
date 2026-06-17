"""CCXT public market adapter — read-only access to allowlisted exchanges.

Exchange allowlist for v1: binance, okx, bybit.
Public data only — no apiKey, secret, password, or credential parameters.

Normalizes ticker, OHLCV, open interest, and funding rate responses
with structured unsupported-capability handling.
"""
from __future__ import annotations

import time
import importlib
from typing import Any, Optional

from market_radar.external_adapters.adapter_models import AdapterResult, AdapterError, AdapterProvenance

ALLOWLISTED_EXCHANGES = {"binance", "okx", "bybit"}

SUPPORTED_OPERATIONS = {"ticker", "ohlcv", "open_interest", "funding_rate"}


class CcxtPublicMarketAdapter:
    """Public market data adapter via CCXT.

    Usage:
        adapter = CcxtPublicMarketAdapter()
        result = adapter.fetch("binance", "ticker", "BTC/USDT")
        print(result.as_dict())
    """

    def __init__(self):
        self._ccxt_available: Optional[bool] = None
        self._exchanges: dict[str, Any] = {}

    def _check_ccxt(self) -> bool:
        if self._ccxt_available is not None:
            return self._ccxt_available
        try:
            import ccxt  # noqa: F401
            self._ccxt_available = True
        except ImportError:
            self._ccxt_available = False
        return self._ccxt_available

    def _get_exchange(self, exchange_id: str) -> Any:
        if exchange_id in self._exchanges:
            return self._exchanges[exchange_id]
        try:
            import ccxt
            ex_class = getattr(ccxt, exchange_id)
            ex = ex_class({
                "enableRateLimit": True,
            })
            self._exchanges[exchange_id] = ex
            return ex
        except (AttributeError, ImportError) as e:
            return None

    def _has_method(self, exchange: Any, method: str) -> bool:
        if not hasattr(exchange, method):
            return False
        # Check if exchange has the capability flag
        caps = getattr(exchange, "has", {})
        if isinstance(caps, dict):
            return caps.get(method, False)
        return True

    def fetch(self, exchange_id: str, operation: str, symbol: str) -> AdapterResult:
        """Fetch public market data.

        Args:
            exchange_id: One of "binance", "okx", "bybit".
            operation: "ticker", "ohlcv", "open_interest", "funding_rate".
            symbol: Symbol string, e.g. "BTC/USDT".

        Returns:
            AdapterResult with normalized data or error.
        """
        if not self._check_ccxt():
            return AdapterResult(
                ok=False,
                error=AdapterError("dependency_missing", "ccxt package not installed"),
                provenance=AdapterProvenance(source="unavailable", method=operation, healthy=False),
            )

        if exchange_id not in ALLOWLISTED_EXCHANGES:
            return AdapterResult(
                ok=False,
                error=AdapterError("exchange_not_allowed",
                                   f"'{exchange_id}' not in allowlist: {ALLOWLISTED_EXCHANGES}"),
                provenance=AdapterProvenance(source="unavailable", method=operation, healthy=False),
            )

        if operation not in SUPPORTED_OPERATIONS:
            return AdapterResult(
                ok=False,
                error=AdapterError("unsupported_operation", f"'{operation}' not supported"),
                provenance=AdapterProvenance(source="unavailable", method=operation, healthy=False),
            )

        exchange = self._get_exchange(exchange_id)
        if exchange is None:
            return AdapterResult(
                ok=False,
                error=AdapterError("exchange_init_failed", f"could not initialize '{exchange_id}'"),
                provenance=AdapterProvenance(source="unavailable", method=operation, healthy=False),
            )

        # Map operation to CCXT method
        ccxt_methods = {
            "ticker": "fetch_ticker",
            "ohlcv": "fetch_ohlcv",
            "open_interest": "fetch_open_interest",
            "funding_rate": "fetch_funding_rate",
        }
        ccxt_method = ccxt_methods.get(operation, "")

        if not self._has_method(exchange, ccxt_method):
            return AdapterResult(
                ok=False,
                error=AdapterError("unsupported_capability",
                                   f"'{exchange_id}' does not support '{operation}'"),
                provenance=AdapterProvenance(source="unavailable", method=operation, healthy=False),
            )

        start = time.monotonic()
        try:
            method_fn = getattr(exchange, ccxt_method)
            result_data = method_fn(symbol)
            elapsed = (time.monotonic() - start) * 1000

            return AdapterResult(
                ok=True,
                data=result_data,
                provenance=AdapterProvenance(source="sdk", method=operation,
                                             endpoint=exchange_id,
                                             latency_ms=round(elapsed, 1)),
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return AdapterResult(
                ok=False,
                error=AdapterError("ccxt_error", f"{type(e).__name__}: {e}", source=exchange_id),
                provenance=AdapterProvenance(source="unavailable", method=operation,
                                             endpoint=exchange_id,
                                             latency_ms=round(elapsed, 1), healthy=False),
            )

    def close(self) -> None:
        for ex in self._exchanges.values():
            try:
                ex.close()
            except Exception:
                pass
