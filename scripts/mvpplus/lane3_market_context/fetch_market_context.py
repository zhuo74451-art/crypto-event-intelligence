#!/usr/bin/env python3
"""MVP+ Lane 3 — Market Context Provider.

Fetches BTC, ETH, SOL, HYPE market data from Binance & Hyperliquid
public APIs. Outputs MarketContext[] matching
contracts/mvpplus/v1/market_context.schema.json.

One-shot read-only. No API key required.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ── Constants ──────────────────────────────────────────────────────────────

BINANCE_API_URL = "https://api.binance.com/api/v3"
HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
USER_AGENT = "MVPPlus-Lane3/1.0 (read-only)"
REQUEST_TIMEOUT = 15
MAX_RETRIES = 1
RETRY_DELAY_S = 0.5

PROJECT_ROOT = os.path.abspath(os.path.join(__file__, *[os.pardir] * 4))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "results", "mvpplus")
os.makedirs(OUTPUT_DIR, exist_ok=True)

TARGET_ASSETS = ["BTC", "ETH", "SOL", "HYPE"]

# Binance symbols for spot ticker
BINANCE_SYMBOLS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    # HYPE not on Binance
}

# HL asset name for Hyperliquid
HL_ASSETS = {
    "BTC": "BTC",
    "ETH": "ETH",
    "SOL": "SOL",
    "HYPE": "HYPE",
}


def utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_source_health(
    source: str, status: str, occurred_at_utc: str,
    error_type: Optional[str] = None, retryable: Optional[bool] = None,
    message_summary: Optional[str] = None,
) -> dict:
    entry: dict[str, Any] = {"status": status, "source": source, "occurred_at_utc": occurred_at_utc}
    if error_type is not None: entry["error_type"] = error_type
    if retryable is not None: entry["retryable"] = retryable
    if message_summary is not None: entry["message_summary"] = message_summary
    return entry


def _http_get(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[Any]:
    """GET a URL and return parsed JSON."""
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
        return json.loads(data)
    except (URLError, HTTPError, OSError, ValueError, json.JSONDecodeError) as e:
        print(f"    [WARN] HTTP GET failed: {url[:80]}... {e}", file=sys.stderr)
        return None


def _hl_post(payload: dict) -> Optional[Any]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        HYPERLIQUID_INFO_URL, data=body,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError, OSError, ValueError, json.JSONDecodeError) as e:
        print(f"    [WARN] HL POST failed: {e}", file=sys.stderr)
        return None


def _get_with_retry(url: str) -> Optional[Any]:
    for attempt in range(1 + MAX_RETRIES):
        result = _http_get(url)
        if result is not None:
            return result
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY_S)
    return None


def fetch_binance_ticker(symbol: str) -> Optional[dict]:
    """Fetch 24hr ticker from Binance."""
    return _get_with_retry(f"{BINANCE_API_URL}/ticker/24hr?symbol={symbol}")


def fetch_hl_mids() -> Optional[dict[str, str]]:
    """Fetch all mid prices from Hyperliquid."""
    result = _hl_post({"type": "allMids"})
    return result if isinstance(result, dict) else None


def fetch_hl_funding() -> Optional[list]:
    """Fetch funding from Hyperliquid."""
    result = _hl_post({"type": "fundingHistory", "coin": "HYPE"})
    return result if isinstance(result, list) else None


def fetch_hl_oi() -> Optional[Any]:
    """Fetch open interest from Hyperliquid."""
    return _hl_post({"type": "openInterests"})


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> int:
    start_time = time.time()
    run_id = f"mvpplus_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}_lane3"
    snapshot_time = utc_now_str()

    print(f"[{run_id}] Lane 3: Market Context Provider", file=sys.stderr)
    print(f"  Snapshot: {snapshot_time}", file=sys.stderr)

    # Fetch all data sources
    print("  Fetching Binance tickers...", file=sys.stderr)
    binance_results: dict[str, Optional[dict]] = {}
    for asset, symbol in BINANCE_SYMBOLS.items():
        binance_results[asset] = fetch_binance_ticker(symbol)
        if binance_results[asset] is not None:
            print(f"    {asset}: ${float(binance_results[asset].get('lastPrice', 0)):,.2f}", file=sys.stderr)
        else:
            print(f"    {asset}: FAILED", file=sys.stderr)

    print("  Fetching Hyperliquid mids...", file=sys.stderr)
    hl_mids = fetch_hl_mids()
    if hl_mids:
        for asset in HL_ASSETS:
            val = hl_mids.get(HL_ASSETS[asset])
            print(f"    HL-{asset}: ${float(val):,.2f}" if val else f"    HL-{asset}: N/A", file=sys.stderr)
    else:
        print("    HL mids: FAILED", file=sys.stderr)

    print("  Fetching Hyperliquid OI...", file=sys.stderr)
    hl_oi = fetch_hl_oi()

    # Build MarketContext per asset
    contexts: list[dict] = []
    errors: list[dict] = []
    sources_used: set[str] = set()

    for asset in TARGET_ASSETS:
        # Determine venue and price
        if asset == "HYPE":
            venue = "hyperliquid"
            hl_name = HL_ASSETS.get(asset)
            mid_str = hl_mids.get(hl_name) if hl_mids else None
            current_price = float(mid_str) if mid_str else None
            mark_price = current_price
            sources_used.add("hyperliquid_info_public")
        else:
            venue = "binance"
            symbol = BINANCE_SYMBOLS.get(asset)
            ticker = binance_results.get(asset)
            if ticker:
                current_price = float(ticker.get("lastPrice", 0))
                mark_price = current_price
                sources_used.add("binance_public")
            else:
                # Fallback to Hyperliquid
                hl_name = HL_ASSETS.get(asset)
                mid_str = hl_mids.get(hl_name) if hl_mids else None
                current_price = float(mid_str) if mid_str else 0.0
                mark_price = current_price
                venue = "hyperliquid"
                sources_used.add("hyperliquid_info_public")

        if current_price is None or current_price <= 0:
            errors.append({
                "source": venue,
                "error_type": "price_unavailable",
                "message_summary": f"No price data for {asset}",
                "occurred_at_utc": snapshot_time,
            })
            contexts.append({
                "asset": asset, "venue": venue, "snapshot_time_utc": snapshot_time,
                "current_price": None, "change_1h_pct": None, "change_24h_pct": None,
                "volume_24h_usd": None, "open_interest_usd": None, "funding_rate_pct": None,
                "mark_price": None, "oracle_price": None, "high_24h": None, "low_24h": None,
                "source_health": make_source_health(
                    source=venue, status="unavailable", occurred_at_utc=snapshot_time,
                    error_type="price_unavailable",
                    message_summary=f"No price data available for {asset}",
                ),
            })
            continue

        # Extract 24h data from Binance
        price_change_24h: Optional[float] = None
        volume_24h: Optional[float] = None
        high_24h: Optional[float] = None
        low_24h: Optional[float] = None

        if asset != "HYPE":
            ticker = binance_results.get(asset)
            if ticker:
                try:
                    price_change_24h = float(ticker.get("priceChangePercent", 0))
                except (ValueError, TypeError):
                    pass
                try:
                    volume_24h = float(ticker.get("quoteVolume", 0))
                except (ValueError, TypeError):
                    pass
                try:
                    high_24h = float(ticker.get("highPrice", 0))
                except (ValueError, TypeError):
                    pass
                try:
                    low_24h = float(ticker.get("lowPrice", 0))
                except (ValueError, TypeError):
                    pass

        # Funding rate (HYPE from Hyperliquid)
        funding_rate: Optional[float] = None
        if asset == "HYPE" and hl_mids:
            # Try to get current funding from allMids alternative or separate call
            pass

        # Open interest
        oi_value: Optional[float] = None
        if hl_oi and isinstance(hl_oi, list):
            for oi_entry in hl_oi:
                if oi_entry.get("coin") == HL_ASSETS.get(asset, asset):
                    try:
                        oi_value = float(oi_entry.get("oi", 0))
                    except (ValueError, TypeError):
                        pass
                    break

        ctx: dict[str, Any] = {
            "asset": asset,
            "venue": venue,
            "snapshot_time_utc": snapshot_time,
            "current_price": round(current_price, 2) if current_price else None,
            "change_1h_pct": None,
            "change_24h_pct": round(price_change_24h, 2) if price_change_24h is not None else None,
            "volume_24h_usd": round(volume_24h, 2) if volume_24h else None,
            "open_interest_usd": round(oi_value, 2) if oi_value else None,
            "funding_rate_pct": round(funding_rate, 6) if funding_rate is not None else None,
            "mark_price": round(mark_price, 2) if mark_price else None,
            "oracle_price": None,
            "high_24h": round(high_24h, 2) if high_24h else None,
            "low_24h": round(low_24h, 2) if low_24h else None,
            "source_health": make_source_health(
                source=venue, status="healthy", occurred_at_utc=snapshot_time,
            ),
        }
        contexts.append(ctx)

    overall_status = "healthy" if len([c for c in contexts if c["source_health"]["status"] == "healthy"]) >= 2 else "degraded"

    output = {
        "run_id": run_id,
        "snapshot_time_utc": snapshot_time,
        "lane": "lane3_market_context",
        "market_contexts": contexts,
        "source_health": make_source_health(
            source="binance_public,hyperliquid_info_public",
            status=overall_status,
            occurred_at_utc=snapshot_time,
            error_type=None if overall_status == "healthy" else "partial_degraded",
            message_summary=f"{len(contexts)} assets, "
                           f"{len([c for c in contexts if c['current_price'] is not None])} with prices"
                           if overall_status == "healthy" else "One or more sources degraded",
        ),
    }
    if errors:
        output["errors"] = errors

    output_path = os.path.join(OUTPUT_DIR, "lane3_market_context.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - start_time
    print(f"  Done in {elapsed:.1f}s. {len(contexts)} asset contexts.", file=sys.stderr)
    print(f"  Output: {output_path}", file=sys.stderr)

    return 0 if overall_status == "healthy" else 1


if __name__ == "__main__":
    sys.exit(main())
