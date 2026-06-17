"""CCXT public market adapter — read-only access to allowlisted exchanges.

Exchange allowlist for v1: binance, okx, bybit.
Public data only — no apiKey, secret, password, or credential parameters.

Normalizes ticker, OHLCV, open interest, and funding rate responses
into stable Adapter-owned dictionaries. Raw CCXT data preserved only as
optional debug metadata (``_raw`` key).

Supports per-operation kwargs such as timeframe and limit.
"""
from __future__ import annotations

import time
from typing import Any, Optional

from market_radar.external_adapters.adapter_models import AdapterResult, AdapterError, AdapterProvenance

ALLOWLISTED_EXCHANGES = {"binance", "okx", "bybit"}

SUPPORTED_OPERATIONS = {"ticker", "ohlcv", "open_interest", "funding_rate"}
SUPPORTED_OPERATIONS_DESC = ", ".join(sorted(SUPPORTED_OPERATIONS))

# Default exchange-level timeout (seconds). Passed to ccxt as 'timeout'.
# This bounds the total HTTP wait per exchange call.
DEFAULT_EXCHANGE_TIMEOUT = 15.0


# ── Normalizers ──


def _normalize_ticker(raw: dict, symbol: str) -> dict:
    """Normalize CCXT ticker response into a stable Adapter-owned dict."""
    return {
        "symbol": symbol,
        "last": raw.get("last"),
        "bid": raw.get("bid"),
        "ask": raw.get("ask"),
        "baseVolume": raw.get("baseVolume"),
        "quoteVolume": raw.get("quoteVolume"),
        "high24h": raw.get("high"),
        "low24h": raw.get("low"),
        "changePct24h": raw.get("percentage"),
        "_raw": raw,
    }


def _normalize_ohlcv(raw: list, symbol: str) -> list[dict]:
    """Normalize CCXT OHLCV response into stable Adapter-owned dicts.

    CCXT returns a list of lists: [timestamp, open, high, low, close, volume, ...]
    """
    results = []
    for row in raw:
        if not isinstance(row, (list, tuple)) or len(row) < 5:
            continue
        results.append({
            "symbol": symbol,
            "timestamp": int(row[0]),
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
            "volume": float(row[5]) if len(row) > 5 else None,
            "_raw": list(row),
        })
    return results


def _normalize_open_interest(raw: dict, symbol: str) -> dict:
    """Normalize CCXT open interest response into a stable Adapter-owned dict."""
    return {
        "symbol": symbol,
        "openInterest": raw.get("openInterest"),
        "timestamp": raw.get("timestamp"),
        "baseVolume": raw.get("baseVolume"),
        "quoteVolume": raw.get("quoteVolume"),
        "_raw": raw,
    }


def _normalize_funding_rate(raw: dict, symbol: str) -> dict:
    """Normalize CCXT funding rate response into a stable Adapter-owned dict."""
    return {
        "symbol": symbol,
        "fundingRate": raw.get("fundingRate"),
        "fundingTimestamp": raw.get("fundingTimestamp"),
        "nextFundingRate": raw.get("nextFundingRate"),
        "nextFundingTimestamp": raw.get("nextFundingTimestamp"),
        "interval": raw.get("interval"),
        "_raw": raw,
    }


NORMALIZERS = {
    "ticker": _normalize_ticker,
    "ohlcv": _normalize_ohlcv,
    "open_interest": _normalize_open_interest,
    "funding_rate": _normalize_funding_rate,
}


# ── Adapter ──


class CcxtPublicMarketAdapter:
    """Public market data adapter via CCXT.

    Usage:
        adapter = CcxtPublicMarketAdapter()
        result = adapter.fetch("binance", "ticker", "BTC/USDT")
        print(result.as_dict())

        # With operation kwargs (timeframe, limit):
        result = adapter.fetch("binance", "ohlcv", "BTC/USDT",
                               kwargs={"timeframe": "1h", "limit": 5})
    """

    def __init__(self, exchange_timeout: float = DEFAULT_EXCHANGE_TIMEOUT):
        self._exchange_timeout = max(1.0, min(exchange_timeout, 60.0))
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
                "timeout": int(self._exchange_timeout * 1000),  # ccxt expects ms
            })
            self._exchanges[exchange_id] = ex
            return ex
        except (AttributeError, ImportError) as e:
            return None

    def _has_method(self, exchange: Any, method: str) -> bool:
        if not hasattr(exchange, method):
            return False
        caps = getattr(exchange, "has", {})
        if isinstance(caps, dict):
            return caps.get(method, False)
        return True

    def fetch(self, exchange_id: str, operation: str, symbol: str,
              kwargs: Optional[dict[str, Any]] = None) -> AdapterResult:
        """Fetch public market data.

        Args:
            exchange_id: One of "binance", "okx", "bybit".
            operation: "ticker", "ohlcv", "open_interest", "funding_rate".
            symbol: Symbol string, e.g. "BTC/USDT".
            kwargs: Optional operation-specific parameters, e.g.
                    {"timeframe": "1h", "limit": 100} for ohlcv.

        Returns:
            AdapterResult with normalized data (stable dict keys).
            Raw CCXT data is preserved as the ``_raw`` key inside each
            normalized record for debugging.
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
                error=AdapterError("unsupported_operation",
                                   f"'{operation}' not supported. Use one of: {SUPPORTED_OPERATIONS_DESC}"),
                provenance=AdapterProvenance(source="unavailable", method=operation, healthy=False),
            )

        exchange = self._get_exchange(exchange_id)
        if exchange is None:
            return AdapterResult(
                ok=False,
                error=AdapterError("exchange_init_failed",
                                   f"could not initialize '{exchange_id}'"),
                provenance=AdapterProvenance(source="unavailable", method=operation, healthy=False),
            )

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
            merged_kwargs = dict(kwargs or {})
            # CCXT ohlcv uses positional args, not kwargs, for timeframe/limit
            if operation == "ohlcv":
                tf = merged_kwargs.pop("timeframe", "1h")
                lim = merged_kwargs.pop("limit", None)
                if lim is not None:
                    result_data = method_fn(symbol, tf, lim)
                else:
                    result_data = method_fn(symbol, tf)
            else:
                result_data = method_fn(symbol, **merged_kwargs)

            elapsed = (time.monotonic() - start) * 1000

            # Normalize into stable Adapter-owned dicts
            normalizer = NORMALIZERS.get(operation)
            if normalizer:
                data = normalizer(result_data, symbol)
            else:
                data = result_data

            return AdapterResult(
                ok=True,
                data=data,
                provenance=AdapterProvenance(
                    source="sdk",  # ccxt is the SDK here
                    method=operation,
                    endpoint=exchange_id,
                    latency_ms=round(elapsed, 1),
                    detail=f"ccxt {ccxt_method} normalized via stable adapter dict",
                ),
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
