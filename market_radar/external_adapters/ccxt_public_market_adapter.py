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

# Use Adapter-owned import resolver instead of bare ``import ccxt``.
# This protects against hyperliquid.ccxt shadowing ``sys.modules['ccxt']``.
from market_radar.external_adapters.import_resolver import (
    resolve_real_ccxt,
    ccxt_resolution_error,
    CcxtResolutionError,
)

ALLOWLISTED_EXCHANGES = {"binance", "okx", "bybit"}

SUPPORTED_OPERATIONS = {"ticker", "ohlcv", "open_interest", "funding_rate"}
SUPPORTED_OPERATIONS_DESC = ", ".join(sorted(SUPPORTED_OPERATIONS))

# Default exchange-level timeout (seconds). Passed to ccxt as 'timeout'.
# This bounds the total HTTP wait per exchange call.
DEFAULT_EXCHANGE_TIMEOUT = 15.0

# ── Operation mapping: operation → (Python method name, CCXT has key) ──
# CCXT uses camelCase capability keys (e.g. fetchTicker) while Python
# adapter methods are snake_case (e.g. fetch_ticker).  We maintain the
# separation explicitly so capability lookups match CCXT's actual dict.
OPERATION_MAP: dict[str, dict[str, str]] = {
    "ticker":        {"method": "fetch_ticker",        "capability": "fetchTicker"},
    "ohlcv":         {"method": "fetch_ohlcv",         "capability": "fetchOHLCV"},
    "open_interest": {"method": "fetch_open_interest", "capability": "fetchOpenInterest"},
    "funding_rate":  {"method": "fetch_funding_rate",  "capability": "fetchFundingRate"},
}


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
        self._ccxt_resolution_error: Optional[str] = None
        self._exchanges: dict[str, Any] = {}

    def _check_ccxt(self) -> bool:
        """Check real CCXT availability via Adapter-owned resolver.

        Never uses bare ``import ccxt`` — always goes through
        ``resolve_real_ccxt()`` which is immune to ``hyperliquid.ccxt``
        shadowing.
        """
        if self._ccxt_available is not None:
            return self._ccxt_available
        try:
            resolve_real_ccxt()
            self._ccxt_available = True
        except CcxtResolutionError as e:
            self._ccxt_available = False
            self._ccxt_resolution_error = str(e)
        return self._ccxt_available

    def _get_exchange(self, exchange_id: str) -> Any:
        if exchange_id in self._exchanges:
            return self._exchanges[exchange_id]
        try:
            ccxt_mod = resolve_real_ccxt()
            ex_class = getattr(ccxt_mod, exchange_id)
            ex = ex_class({
                "enableRateLimit": True,
                "timeout": int(self._exchange_timeout * 1000),  # ccxt expects ms
            })
            self._exchanges[exchange_id] = ex
            return ex
        except CcxtResolutionError as e:
            self._ccxt_available = False
            self._ccxt_resolution_error = str(e)
            return None
        except (AttributeError, ImportError) as e:
            return None

    def _check_capability(self, exchange: Any, method_name: str, capability_key: str) -> bool:
        """Check that *exchange* has *method_name* and its *capability_key* is truthy.

        CCXT stores capabilities as camelCase keys (``fetchTicker``) in its
        ``has`` dict.  We check:
          1. The Python method exists on the exchange object.
          2. The capability value is ``True`` or ``'emulated'``.
        ``False``, ``None``, or a missing key means the operation is unsupported,
        even if the method happens to exist on the object.
        """
        if not hasattr(exchange, method_name):
            return False
        caps = getattr(exchange, "has", {})
        if not isinstance(caps, dict):
            return True  # no has dict → assume capable
        value = caps.get(capability_key)
        return value is True or value == "emulated"

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
            err_code = "ccxt_import_resolution_failed" if self._ccxt_resolution_error else "dependency_missing"
            err_msg = self._ccxt_resolution_error or "ccxt package not installed"
            return AdapterResult(
                ok=False,
                error=AdapterError(err_code, err_msg),
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

        op_cfg = OPERATION_MAP.get(operation)
        if op_cfg is None:
            return AdapterResult(
                ok=False,
                error=AdapterError("unsupported_operation", f"no mapping for '{operation}'"),
                provenance=AdapterProvenance(source="unavailable", method=operation, healthy=False),
            )

        method_name = op_cfg["method"]
        capability_key = op_cfg["capability"]

        if not self._check_capability(exchange, method_name, capability_key):
            return AdapterResult(
                ok=False,
                error=AdapterError("unsupported_capability",
                                   f"'{exchange_id}' does not support '{operation}' "
                                   f"(has['{capability_key}'] is false/missing)"),
                provenance=AdapterProvenance(source="unavailable", method=operation, healthy=False),
            )

        start = time.monotonic()
        try:
            method_fn = getattr(exchange, method_name)
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
                    source="ccxt",  # ccxt is the SDK here
                    method=operation,
                    endpoint=exchange_id,
                    latency_ms=round(elapsed, 1),
                    detail=f"ccxt.{method_name} normalized via stable adapter dict",
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
