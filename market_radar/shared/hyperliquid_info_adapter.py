"""Signal Spine IO v1 — Hyperliquid Info API Minimal Read-Only Adapter.

Free public adapter using Hyperliquid's public Info API (no API key required).
Endpoint: https://api.hyperliquid.xyz/info (POST with JSON body).

Only fetches market metadata and mid prices — no trading, no positions, no auth.

Design constraints:
  - Read-only: never submits transactions, never signs payloads
  - No API key: uses only the free public Info endpoint
  - Error-safe: network failures return degraded result with risk_notes
  - Fixture fallback: if network fails, returns fixture data marked as fixture

Integration note: This adapter is designed to slot into the existing SignalAdapter
contract. When the core Spine/Registry is implemented, this adapter will be
registered via REAL_FREE_API_ADAPTERS (see free_api_adapters.py) using:

    from market_radar.shared.hyperliquid_info_adapter import HyperliquidInfoFreeApiAdapter
    REAL_FREE_API_ADAPTERS["hyperliquid_market_sync"] = HyperliquidInfoFreeApiAdapter
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from market_radar.shared.models import (
    CardFamily,
    DataSourceType,
    NormalizedSignal,
    china_now,
    PIPELINE_VERSION,
)

CN_TZ = timezone(timedelta(hours=8))
HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
USER_AGENT = "SignalSpineIO-v1/1.0 (read-only; no-key public data)"

# Hyperliquid asset names we track (internal HL names → ticker)
HL_ASSET_MAP: dict[str, str] = {
    "BTC": "BTC",
    "ETH": "ETH",
    "SOL": "SOL",
    "ARB": "ARB",
    "OP": "OP",
    "AVAX": "AVAX",
    "LINK": "LINK",
    "DOGE": "DOGE",
    "SUI": "SUI",
    "PEPE": "PEPE",
    "HYPE": "HYPE",
}

# Target assets for market sync
TARGET_HL_ASSETS = ["BTC", "ETH", "SOL"]


def _hl_post(payload: dict, timeout: int = 15) -> Optional[dict | list]:
    """POST JSON to Hyperliquid Info API. Returns parsed JSON or None on failure."""
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        HYPERLIQUID_INFO_URL,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
        return json.loads(data)
    except (URLError, HTTPError, OSError, ValueError, json.JSONDecodeError):
        return None


def _fetch_hl_all_mids() -> Optional[dict[str, str]]:
    """Fetch all mid prices from Hyperliquid Info API.

    Returns dict of {asset_name: mid_price_str} or None on failure.
    """
    result = _hl_post({"type": "allMids"})
    if isinstance(result, dict):
        return result
    return None


def _fetch_hl_metadata() -> Optional[list[dict]]:
    """Fetch Hyperliquid asset metadata (universe).

    Returns list of asset info dicts or None on failure.
    """
    result = _hl_post({"type": "meta"})
    if isinstance(result, list):
        return result
    return None


class HyperliquidInfoFreeApiAdapter:
    """Minimal read-only adapter for Hyperliquid public Info API.

    Fetches mid prices and metadata from Hyperliquid's free public endpoint.
    No API key, no authentication, no trading.

    Output card family: MULTI_ASSET_MARKET_SYNC (compatible with existing renderer).

    Interface notes for core integration:
      - Implements the same `fetch() -> NormalizedSignal` pattern as SignalAdapter
      - Does NOT extend SignalAdapter class to avoid modifying existing contract
      - When core Registry is ready, wrap via adapter_contract.SignalAdapter
    """

    def __init__(self):
        self.card_family = CardFamily.MULTI_ASSET_MARKET_SYNC
        self.source_type = DataSourceType.FREE_PUBLIC_API

    @property
    def adapter_label(self) -> str:
        return f"HyperliquidInfoFreeApiAdapter({self.card_family.value}, {self.source_type.value})"

    def fetch(self) -> NormalizedSignal:
        """Fetch mid prices from Hyperliquid Info API.

        Network failure → returns fixture-like degraded signal with data_source=fixture.

        Never raises — all errors become risk_notes.
        """
        risk_notes: list[str] = []
        source_refs: list[str] = []
        assets: list[dict] = []
        api_success = False
        fetch_error: Optional[str] = None
        data_source = DataSourceType.FREE_PUBLIC_API

        # ── Attempt real Hyperliquid API call ──
        try:
            mids = _fetch_hl_all_mids()
            if mids is None:
                raise RuntimeError("Hyperliquid allMids returned None")

            source_refs.append("hyperliquid_info_api:/info?type=allMids")
            api_success = True

            for hl_name in TARGET_HL_ASSETS:
                mid_str = mids.get(hl_name)
                if mid_str is not None:
                    try:
                        mid_price = float(mid_str)
                    except (ValueError, TypeError):
                        mid_price = 0.0

                    ticker = HL_ASSET_MAP.get(hl_name, hl_name)
                    assets.append({
                        "symbol": f"{ticker}USDT",
                        "price": mid_price,
                        "source": "hyperliquid_public_info",
                        "hl_asset": hl_name,
                    })
                else:
                    risk_notes.append(f"Hyperliquid mid price not found for {hl_name}")

        except (URLError, HTTPError, OSError, ValueError, RuntimeError) as e:
            fetch_error = f"Hyperliquid API call failed: {type(e).__name__}: {e}"
            risk_notes.append(fetch_error)
        except Exception as e:
            fetch_error = f"Unexpected error during Hyperliquid fetch: {type(e).__name__}: {e}"
            risk_notes.append(fetch_error)

        # ── Fallback: if no assets fetched, mark as fixture fallback ──
        if not assets:
            risk_notes.append("data_source=fixture: Hyperliquid API unavailable, using fixture fallback")
            data_source = DataSourceType.FIXTURE
            # Provide fixture fallback data
            assets = [
                {"symbol": "BTCUSDT", "price": 89000.0, "source": "fixture_fallback"},
                {"symbol": "ETHUSDT", "price": 3200.0, "source": "fixture_fallback"},
                {"symbol": "SOLUSDT", "price": 175.0, "source": "fixture_fallback"},
            ]
            source_refs.append("fixture_fallback:hyperliquid_unavailable")

        # ── Build sync observation ──
        sync_observation = ""
        if len(assets) >= 2:
            btc_asset = next((a for a in assets if a["symbol"] == "BTCUSDT"), None)
            alt_assets = [a for a in assets if a["symbol"] != "BTCUSDT"]
            btc_price = btc_asset["price"] if btc_asset else 0
            alt_prices = [a["price"] for a in alt_assets if a["price"] > 0]

            if btc_price > 90000 and any(p > btc_price * 0.04 for p in alt_prices):
                sync_observation = "BTC elevated — monitor alt rotation"
            elif btc_price > 0 and alt_prices:
                sync_observation = f"Multi-asset sync from Hyperliquid: {len(assets)} assets tracked"
            else:
                sync_observation = "Insufficient data for sync observation"

        return NormalizedSignal(
            source_type=data_source,
            card_family=self.card_family,
            asset_or_topic="/".join(TARGET_HL_ASSETS),
            timestamp=china_now(),
            metrics={
                "assets": assets,
                "asset_count": len(assets),
                "sync_observation": sync_observation,
                "api_success": api_success,
                "fetch_error": fetch_error,
                "data_source": data_source.value,
                "source": "hyperliquid_public_info",
                "fixture_fallback": not api_success,
            },
            source_refs=source_refs,
            risk_notes=risk_notes,
            pipeline_version=PIPELINE_VERSION,
        )


class HyperliquidInfoAdapterFactory:
    """Factory for creating Hyperliquid Info adapters.

    When the core Registry is ready, this factory should be replaced by
    create_real_free_api_adapter() in free_api_adapters.py.
    """

    @staticmethod
    def create() -> HyperliquidInfoFreeApiAdapter:
        return HyperliquidInfoFreeApiAdapter()
