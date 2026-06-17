"""Hyperliquid public read-only adapter.

Official Hyperliquid Python SDK preferred path. Lazy import with safe fallback
to raw HTTP POST via HttpxTransport.

Public operations only — no wallet, signing, order, or transfer capability.
"""
from __future__ import annotations

import time
import importlib
from typing import Any, Optional
from dataclasses import dataclass

from market_radar.external_adapters.adapter_models import AdapterResult, AdapterError, AdapterProvenance
from market_radar.external_adapters.httpx_transport import HttpxTransport

HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
SDK_PACKAGE = "hyperliquid"


# ── Operation Payloads ──

OPERATIONS = {
    "allMids":               {"type": "allMids"},
    "meta":                  {"type": "meta"},
    "clearinghouseState":    {"type": "clearinghouseState", "user": "0x0000000000000000000000000000000000000000"},
    "spotClearinghouseState": {"type": "spotClearinghouseState", "user": "0x0000000000000000000000000000000000000000"},
    "fundingHistory":        {"type": "fundingHistory", "coin": "BTC"},
}

PUBLIC_OPERATIONS = {"allMids", "meta"}


class HyperliquidPublicAdapter:
    """Public read-only Hyperliquid data adapter.

    Usage:
        adapter = HyperliquidPublicAdapter()
        result = adapter.fetch("allMids")
        print(result.as_dict())
    """

    def __init__(self, transport: Optional[HttpxTransport] = None):
        self._transport = transport or HttpxTransport()
        self._sdk_available: Optional[bool] = None

    def _check_sdk(self) -> bool:
        if self._sdk_available is not None:
            return self._sdk_available
        try:
            import hyperliquid  # noqa: F401
            self._sdk_available = True
        except ImportError:
            self._sdk_available = False
        return self._sdk_available

    def _sdk_fetch(self, operation: str) -> Optional[Any]:
        """Attempt SDK call for public operations only."""
        if operation not in PUBLIC_OPERATIONS:
            return None
        try:
            import hyperliquid
            from hyperliquid.info import Info
            info = Info(skip_ws=True)
            start = time.monotonic()
            if operation == "allMids":
                data = info.all_mids()
            elif operation == "meta":
                data = info.meta()
            else:
                return None
            elapsed = (time.monotonic() - start) * 1000
            return {"data": data, "latency_ms": round(elapsed, 1), "source": "sdk"}
        except Exception:
            return None

    def _raw_fetch(self, operation: str) -> AdapterResult:
        """Fallback using raw HTTP POST."""
        payload = OPERATIONS.get(operation)
        if payload is None:
            return AdapterResult(
                ok=False,
                error=AdapterError("unknown_operation", f"no payload for '{operation}'"),
                provenance=AdapterProvenance(source="unavailable", method=operation),
            )

        start = time.monotonic()
        result = self._transport.post(HYPERLIQUID_INFO_URL, json_body=payload)
        elapsed = (time.monotonic() - start) * 1000

        if not result.ok:
            err = result.error
            return AdapterResult(
                ok=False,
                error=AdapterError(err.kind if err else "unknown", err.message if err else "no response",
                                   source="raw_http_fallback"),
                provenance=AdapterProvenance(source="unavailable" if not result.ok else "raw_http_fallback",
                                             method=operation, endpoint=HYPERLIQUID_INFO_URL,
                                             latency_ms=round(elapsed, 1), healthy=False),
            )

        return AdapterResult(
            ok=True,
            data=result.data,
            provenance=AdapterProvenance(source="raw_http_fallback", method=operation,
                                         endpoint=HYPERLIQUID_INFO_URL,
                                         latency_ms=round(elapsed, 1)),
        )

    def fetch(self, operation: str) -> AdapterResult:
        """Fetch data for *operation*.

        Returns AdapterResult with provenance indicating
        sdk / raw_http_fallback / unavailable.
        """
        # Try SDK first for public operations
        if self._check_sdk():
            sdk_result = self._sdk_fetch(operation)
            if sdk_result is not None:
                return AdapterResult(
                    ok=True,
                    data=sdk_result["data"],
                    provenance=AdapterProvenance(source="sdk", method=operation,
                                                 latency_ms=sdk_result["latency_ms"]),
                )

        # Fallback to raw HTTP
        raw = self._raw_fetch(operation)
        if raw.ok:
            return raw

        # Both failed
        return AdapterResult(
            ok=False,
            error=AdapterError("unavailable", f"SDK and raw HTTP both failed for '{operation}'",
                               source="unavailable"),
            provenance=AdapterProvenance(source="unavailable", method=operation, healthy=False),
        )

    def close(self) -> None:
        self._transport.close()
