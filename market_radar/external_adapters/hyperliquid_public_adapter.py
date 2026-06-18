"""Hyperliquid public read-only adapter.

Official Hyperliquid Python SDK preferred path. Lazy import with safe fallback
to raw HTTP POST via HttpxTransport.

Public operations only — no wallet, signing, order, or transfer capability.

Exposes five parameterized read-only methods:
  - fetch_all_mids()
  - fetch_meta()
  - fetch_clearinghouse_state(user_address)
  - fetch_spot_clearinghouse_state(user_address)
  - fetch_funding_history(coin, start_time_ms, end_time_ms=None)

Each returns AdapterResult with an explicit AdapterHealth object.
"""
from __future__ import annotations

import re
import time
from typing import Any, Optional

from market_radar.external_adapters.adapter_models import AdapterResult, AdapterError, AdapterProvenance
from market_radar.external_adapters.httpx_transport import HttpxTransport

HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"

# ── Validation ──

# Standard Ethereum address: 0x-prefixed, 40 hex chars (0x + 40 hex = 42 total).
# We accept both EIP-55 mixed-case and all-lowercase.
ETH_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


def validate_ethereum_address(address: str) -> Optional[str]:
    """Return an error message if *address* is not a valid Ethereum address, else None."""
    if not isinstance(address, str) or not address.strip():
        return "address must be a non-empty string"
    if not ETH_ADDRESS_RE.match(address):
        return f"invalid Ethereum address format: {address!r}"
    return None


def validate_coin(coin: str) -> Optional[str]:
    """Return an error message if *coin* is empty or not a string, else None."""
    if not isinstance(coin, str) or not coin.strip():
        return "coin must be a non-empty string"
    return None


def validate_time_range(start_time_ms: int, end_time_ms: Optional[int] = None) -> Optional[str]:
    """Return an error message if time range is invalid, else None.

    Both values must be non-negative integers. If end is supplied, start <= end.
    """
    if not isinstance(start_time_ms, int) or start_time_ms < 0:
        return "start_time_ms must be a non-negative integer"
    if end_time_ms is not None:
        if not isinstance(end_time_ms, int) or end_time_ms < 0:
            return "end_time_ms must be a non-negative integer when supplied"
        if start_time_ms > end_time_ms:
            return "start_time_ms must be <= end_time_ms"
    return None


# ── Read-Only Adapter ──


class HyperliquidPublicAdapter:
    """Public read-only Hyperliquid data adapter.

    Usage:
        adapter = HyperliquidPublicAdapter()
        mids = adapter.fetch_all_mids()
        meta = adapter.fetch_meta()
        state = adapter.fetch_clearinghouse_state("0x1234...")
        funding = adapter.fetch_funding_history("BTC", 1700000000000, 1700086400000)
        print(mids.as_dict())
    """

    def __init__(self, transport: Optional[HttpxTransport] = None):
        self._transport = transport or HttpxTransport()
        self._sdk_available: Optional[bool] = None
        self._sdk_info: Optional[Any] = None
        self._saved_ccxt: Any = None

    # ── Import isolation helpers ──

    def _save_ccxt(self) -> None:
        """Snapshot current sys.modules['ccxt'] if it's the real third-party CCXT.

        The hyperliquid SDK's ``__init__.py`` overrides ``sys.modules['ccxt']``
        with its own ``hyperliquid.ccxt`` shim.  We snapshot the real module
        before importing hyperliquid so we can restore it after.
        """
        import sys as _sys
        existing = _sys.modules.get("ccxt")
        if existing is not None:
            name = getattr(existing, "__name__", "")
            fpath = getattr(existing, "__file__", "")
            if "hyperliquid" not in fpath.replace("\\", "/").split("/") and name == "ccxt":
                self._saved_ccxt = existing

    def _restore_ccxt(self) -> None:
        """Restore the real ccxt in sys.modules if hyperliquid shadowed it.

        Called right after any operation that imports hyperliquid.
        The restoration is scoped to this adapter instance and leaves no
        global order dependency for callers.
        """
        import sys as _sys
        if self._saved_ccxt is not None:
            current = _sys.modules.get("ccxt")
            current_name = getattr(current, "__name__", "") if current else ""
            if current_name != "ccxt" or "hyperliquid" in str(getattr(current, "__file__", "")):
                _sys.modules["ccxt"] = self._saved_ccxt

    # ── Internal helpers ──

    def _check_sdk(self) -> bool:
        """Check whether the hyperliquid SDK is installed and importable."""
        if self._sdk_available is not None:
            return self._sdk_available
        self._save_ccxt()
        try:
            import hyperliquid  # noqa: F401
            from hyperliquid.info import Info  # noqa: F401
            self._sdk_available = True
        except ImportError:
            self._sdk_available = False
        finally:
            self._restore_ccxt()
        return self._sdk_available

    def _get_info(self) -> Optional[Any]:
        """Lazy-init an Info instance when SDK is available."""
        if not self._check_sdk():
            return None
        if self._sdk_info is not None:
            return self._sdk_info
        self._save_ccxt()
        try:
            from hyperliquid.info import Info
            self._sdk_info = Info(skip_ws=True)
            return self._sdk_info
        except Exception:
            self._sdk_available = False
            return None
        finally:
            self._restore_ccxt()

    def _sdk_call(self, method_name: str, *args: Any) -> Optional[dict]:
        """Call *method_name* on the Info SDK, returning a result dict or None."""
        info = self._get_info()
        if info is None:
            return None
        try:
            method = getattr(info, method_name, None)
            if method is None:
                return None
            start = time.monotonic()
            data = method(*args)
            elapsed = (time.monotonic() - start) * 1000
            return {"data": data, "latency_ms": round(elapsed, 1), "source": "sdk"}
        except Exception:
            return None

    def _raw_post(self, payload: dict, method_label: str) -> AdapterResult:
        """Raw HTTP POST fallback via HttpxTransport."""
        start = time.monotonic()
        transport_result = self._transport.post(HYPERLIQUID_INFO_URL, json_body=payload)
        elapsed = (time.monotonic() - start) * 1000

        if not transport_result.ok:
            err = transport_result.error
            return AdapterResult(
                ok=False,
                error=AdapterError(
                    code=err.kind if err else "network",
                    message=err.message if err else "no response",
                    source="raw_http_fallback",
                ),
                provenance=AdapterProvenance(
                    source="raw_http_fallback",
                    method=method_label,
                    endpoint=HYPERLIQUID_INFO_URL,
                    latency_ms=round(elapsed, 1),
                    healthy=False,
                    detail=f"HTTP {transport_result.status_code}" if transport_result.status_code else None,
                ),
            )

        return AdapterResult(
            ok=True,
            data=transport_result.data,
            provenance=AdapterProvenance(
                source="raw_http_fallback",
                method=method_label,
                endpoint=HYPERLIQUID_INFO_URL,
                latency_ms=round(elapsed, 1),
                detail="SDK method unavailable for this operation — raw HTTP fallback used",
            ),
        )

    def _sdk_or_raw(self, sdk_method: str, sdk_args: tuple,
                    payload: dict, method_label: str) -> AdapterResult:
        """Try SDK then raw HTTP, returning AdapterResult with provenance."""
        # SDK path
        if self._check_sdk():
            sdk_result = self._sdk_call(sdk_method, *sdk_args)
            if sdk_result is not None:
                return AdapterResult(
                    ok=True,
                    data=sdk_result["data"],
                    provenance=AdapterProvenance(
                        source="sdk",
                        method=method_label,
                        latency_ms=sdk_result["latency_ms"],
                    ),
                )

        # Raw HTTP fallback
        raw = self._raw_post(payload, method_label)
        if raw.ok:
            return raw

        return AdapterResult(
            ok=False,
            error=AdapterError(
                "unavailable",
                f"SDK and raw HTTP both failed for '{method_label}'",
                source="unavailable",
            ),
            provenance=AdapterProvenance(source="unavailable", method=method_label, healthy=False),
        )

    # ── Public parameterized methods ──

    def fetch_all_mids(self) -> AdapterResult:
        """Fetch all mid prices from Hyperliquid.

        SDK: Info.all_mids()  |  Fallback: {"type": "allMids"}
        """
        return self._sdk_or_raw(
            sdk_method="all_mids",
            sdk_args=(),
            payload={"type": "allMids"},
            method_label="allMids",
        )

    def fetch_meta(self) -> AdapterResult:
        """Fetch Hyperliquid asset metadata (universe list).

        SDK: Info.meta()  |  Fallback: {"type": "meta"}
        """
        return self._sdk_or_raw(
            sdk_method="meta",
            sdk_args=(),
            payload={"type": "meta"},
            method_label="meta",
        )

    def fetch_clearinghouse_state(self, user_address: str) -> AdapterResult:
        """Fetch perpetual clearinghouse state for *user_address*.

        Validates address format before making any network call.
        """
        err = validate_ethereum_address(user_address)
        if err:
            return AdapterResult(
                ok=False,
                error=AdapterError("validation_error", err, source="input"),
                provenance=AdapterProvenance(source="unavailable", method="clearinghouseState", healthy=False),
            )

        return self._sdk_or_raw(
            sdk_method="clearinghouse_state",
            sdk_args=(user_address,),
            payload={"type": "clearinghouseState", "user": user_address},
            method_label="clearinghouseState",
        )

    def fetch_spot_clearinghouse_state(self, user_address: str) -> AdapterResult:
        """Fetch spot clearinghouse state for *user_address*.

        Validates address format before making any network call.
        """
        err = validate_ethereum_address(user_address)
        if err:
            return AdapterResult(
                ok=False,
                error=AdapterError("validation_error", err, source="input"),
                provenance=AdapterProvenance(source="unavailable", method="spotClearinghouseState", healthy=False),
            )

        return self._sdk_or_raw(
            sdk_method="spot_clearinghouse_state",
            sdk_args=(user_address,),
            payload={"type": "spotClearinghouseState", "user": user_address},
            method_label="spotClearinghouseState",
        )

    def fetch_funding_history(self, coin: str, start_time_ms: int,
                              end_time_ms: Optional[int] = None) -> AdapterResult:
        """Fetch funding history for *coin* in the given time range.

        Args:
            coin: Non-empty asset name, e.g. "BTC".
            start_time_ms: Start of range in milliseconds since epoch.
            end_time_ms: End of range (optional). If omitted, returns latest.

        Validates coin and time range before making any network call.
        """
        # Input validation
        err = validate_coin(coin)
        if err:
            return AdapterResult(
                ok=False,
                error=AdapterError("validation_error", err, source="input"),
                provenance=AdapterProvenance(source="unavailable", method="fundingHistory", healthy=False),
            )

        err = validate_time_range(start_time_ms, end_time_ms)
        if err:
            return AdapterResult(
                ok=False,
                error=AdapterError("validation_error", err, source="input"),
                provenance=AdapterProvenance(source="unavailable", method="fundingHistory", healthy=False),
            )

        payload: dict[str, Any] = {"type": "fundingHistory", "coin": coin}
        if start_time_ms is not None:
            payload["startTime"] = start_time_ms
        if end_time_ms is not None:
            payload["endTime"] = end_time_ms

        return self._sdk_or_raw(
            sdk_method="funding_history",
            sdk_args=(coin, start_time_ms, end_time_ms),
            payload=payload,
            method_label="fundingHistory",
        )

    # ── Lifecycle ──

    def close(self) -> None:
        self._transport.close()
