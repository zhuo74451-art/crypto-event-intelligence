#!/usr/bin/env python3
"""MVP+ Lane 1 — Hyperliquid Whale Position Provider.

Fetches current positions from Hyperliquid's public Info API
for tracked whale addresses. Outputs WhalePosition[] as JSON
matching contracts/mvpplus/v1/whale_position.schema.json.

One-shot read-only. No API key required. No trading.
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

HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
USER_AGENT = "MVPPlus-Lane1/1.0 (read-only; no-key public data)"
REQUEST_TIMEOUT = 20
MAX_RETRIES = 2
RETRY_DELAY_S = 1.0

PROJECT_ROOT = os.path.abspath(os.path.join(__file__, *[os.pardir] * 4))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "results", "mvpplus")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Tracked addresses with labels
TRACKED_ADDRESSES: list[dict[str, Any]] = [
    {
        "address": "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
        "label": "Matrixport Related",
        "entity_type": "fund_wallet",
        "label_confidence": "medium",
    },
    {
        "address": "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
        "label": "loraclexyz",
        "entity_type": "high_leverage_trader",
        "label_confidence": "medium",
    },
    {
        "address": "0x082e843a431aef031264dc232693dd710aedca88",
        "label": "Unknown HYPE Whale",
        "entity_type": "unknown_whale",
        "label_confidence": "low",
    },
    {
        "address": "0x50b309f78e774a756a2230e1769729094cac9f20",
        "label": "Unknown Hyperliquid Whale",
        "entity_type": "unknown_whale",
        "label_confidence": "low",
    },
]


# ── Hyperliquid API Helpers ────────────────────────────────────────────────


def _hl_post(payload: dict) -> Optional[Any]:
    """POST JSON to Hyperliquid Info API. Returns parsed JSON or None."""
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
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = resp.read().decode("utf-8")
        return json.loads(data)
    except (URLError, HTTPError, OSError, ValueError, json.JSONDecodeError) as e:
        print(f"  [WARN] Hyperliquid API call failed: {e}", file=sys.stderr)
        return None


def _hl_post_with_retry(payload: dict) -> Optional[Any]:
    """POST with exponential backoff retry."""
    last_error: Optional[str] = None
    for attempt in range(1 + MAX_RETRIES):
        result = _hl_post(payload)
        if result is not None:
            return result
        last_error = f"attempt {attempt + 1} failed"
        if attempt < MAX_RETRIES:
            delay = RETRY_DELAY_S * (2 ** attempt)
            print(f"  [RETRY] retrying in {delay:.1f}s...", file=sys.stderr)
            time.sleep(delay)
    print(f"  [ERROR] All {1 + MAX_RETRIES} attempts failed: {last_error}", file=sys.stderr)
    return None


def _fetch_all_mids() -> Optional[dict[str, str]]:
    """Fetch all mid prices from Hyperliquid."""
    result = _hl_post_with_retry({"type": "allMids"})
    if isinstance(result, dict):
        return result
    return None


def _fetch_clearinghouse_state(address: str) -> Optional[dict]:
    """Fetch clearinghouse state for a single address."""
    return _hl_post_with_retry({
        "type": "clearinghouseState",
        "user": address,
    })


def utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_source_health(
    source: str,
    status: str,
    occurred_at_utc: str,
    error_type: Optional[str] = None,
    retryable: Optional[bool] = None,
    message_summary: Optional[str] = None,
) -> dict:
    entry: dict[str, Any] = {
        "status": status,
        "source": source,
        "occurred_at_utc": occurred_at_utc,
    }
    if error_type is not None:
        entry["error_type"] = error_type
    if retryable is not None:
        entry["retryable"] = retryable
    if message_summary is not None:
        entry["message_summary"] = message_summary
    return entry


# ── Position Parsing ───────────────────────────────────────────────────────


def parse_asset_positions(
    state: dict,
    address_info: dict,
    mids: dict[str, str],
    snapshot_time: str,
) -> list[dict]:
    """Parse assetPositions from clearinghouseState into WhalePosition[]."""
    positions_raw = state.get("assetPositions", [])
    if not positions_raw:
        return []

    results: list[dict] = []
    for entry in positions_raw:
        pos = entry.get("position", {})
        if not pos:
            continue

        coin = pos.get("coin", "")
        if not coin:
            continue

        szi_str = pos.get("szi", "0")
        try:
            szi = float(szi_str)
        except (ValueError, TypeError):
            continue

        if szi == 0:
            continue

        entry_px_str = pos.get("entryPx", "0")
        try:
            entry_price = float(entry_px_str)
        except (ValueError, TypeError):
            entry_price = 0.0

        if entry_price <= 0:
            continue

        # Mark price from allMids
        mid_str = mids.get(coin, "0")
        try:
            mark_price = float(mid_str)
        except (ValueError, TypeError):
            mark_price = 0.0

        if mark_price <= 0:
            continue

        # Leverage
        lev_obj = pos.get("leverage", {})
        if isinstance(lev_obj, dict):
            try:
                leverage = float(lev_obj.get("value", 0))
            except (ValueError, TypeError):
                leverage = 0.0
        else:
            leverage = 0.0

        # Position value
        pv_str = pos.get("positionValue", "0")
        try:
            position_value = float(pv_str)
        except (ValueError, TypeError):
            position_value = abs(szi) * mark_price

        if position_value <= 0:
            position_value = abs(szi) * mark_price

        abs_size = abs(szi)
        direction = "long" if szi > 0 else "short"

        # Unrealized PnL
        upnl_str = pos.get("unrealizedPnl", "0")
        try:
            unrealized_pnl = float(upnl_str)
        except (ValueError, TypeError):
            unrealized_pnl = None

        # Liquidation price
        liq_str = pos.get("liquidationPx")
        liquidation_price: Optional[float] = None
        liq_distance: Optional[float] = None
        if liq_str is not None:
            try:
                liquidation_price = float(liq_str)
                if liquidation_price > 0 and mark_price > 0:
                    liq_distance = (liquidation_price - mark_price) / mark_price * 100
            except (ValueError, TypeError):
                pass

        # Margin mode
        margin_mode: Optional[str] = None
        if isinstance(lev_obj, dict):
            margin_mode = lev_obj.get("type")

        # Source health
        source_health = make_source_health(
            source="hyperliquid_info_public",
            status="healthy",
            occurred_at_utc=snapshot_time,
        )

        position_record: dict[str, Any] = {
            "address": address_info["address"],
            "label": address_info.get("label"),
            "account_value_usd": None,
            "coin": coin,
            "direction": direction,
            "signed_size": szi,
            "absolute_size": abs_size,
            "position_value_usd": round(position_value, 2),
            "entry_price": round(entry_price, 2),
            "mark_price": round(mark_price, 2),
            "leverage": round(leverage, 2),
            "unrealized_pnl_usd": round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
            "liquidation_price": round(liquidation_price, 2) if liquidation_price is not None else None,
            "liquidation_distance_pct": round(liq_distance, 4) if liq_distance is not None else None,
            "funding_rate_pct": None,
            "margin_mode": margin_mode,
            "snapshot_time_utc": snapshot_time,
            "data_source": "hyperliquid_info_public",
            "source_health": source_health,
        }
        results.append(position_record)

    return results


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> int:
    start_time = time.time()
    run_id = f"mvpplus_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}_lane1"
    snapshot_time = utc_now_str()
    source = "hyperliquid_info_public"

    print(f"[{run_id}] Lane 1: Hyperliquid Whale Position Provider", file=sys.stderr)
    print(f"  Snapshot time: {snapshot_time}", file=sys.stderr)

    # Step 1: Fetch all mids
    print("  Fetching all mids...", file=sys.stderr)
    mids = _fetch_all_mids()
    if mids is None:
        print("  [DEGRADED] Failed to fetch mids. Cannot compute positions.", file=sys.stderr)
        # Output empty but mark degraded
        empty_result = {
            "run_id": run_id,
            "snapshot_time_utc": snapshot_time,
            "lane": "lane1_hyperliquid",
            "positions": [],
            "source_health": make_source_health(
                source=source,
                status="unavailable",
                occurred_at_utc=snapshot_time,
                error_type="api_failure",
                retryable=True,
                message_summary="Failed to fetch allMids from Hyperliquid API",
            ),
            "errors": [{"source": source, "error_type": "api_failure",
                         "message_summary": "allMids returned None after retries",
                         "occurred_at_utc": snapshot_time}],
        }
        output_path = os.path.join(OUTPUT_DIR, "lane1_whale_positions.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(empty_result, f, indent=2, ensure_ascii=False)
        print(f"  [DEGRADED] Wrote empty result to {output_path}", file=sys.stderr)
        return 1

    mids_count = len(mids)
    print(f"  Got {mids_count} mid prices", file=sys.stderr)

    # Step 2: For each tracked address, fetch positions
    all_positions: list[dict] = []
    errors: list[dict] = []
    healthy_count = 0
    degraded_count = 0

    for addr_info in TRACKED_ADDRESSES:
        address = addr_info["address"]
        label = addr_info.get("label", "Unknown Whale")
        short_addr = f"{address[:6]}...{address[-4:]}"
        print(f"  Fetching positions for {label} ({short_addr})...", file=sys.stderr)

        state = _fetch_clearinghouse_state(address)
        if state is None or not isinstance(state, dict):
            errors.append({
                "source": source,
                "error_type": "address_fetch_failed",
                "message_summary": f"clearinghouseState failed for {short_addr}",
                "occurred_at_utc": snapshot_time,
            })
            degraded_count += 1
            print(f"    [DEGRADED] No data for {label}", file=sys.stderr)
            continue

        positions = parse_asset_positions(state, addr_info, mids, snapshot_time)
        if positions:
            all_positions.extend(positions)
            healthy_count += 1
            for p in positions:
                print(f"    {p['direction']} {abs(p['signed_size']):.4f} {p['coin']} "
                      f"@ ${p['entry_price']:,.2f} | val=${p['position_value_usd']:,.0f} "
                      f"| PnL=${p['unrealized_pnl_usd']:+,.0f}" if p.get('unrealized_pnl_usd') is not None
                      else f"    {p['direction']} {abs(p['signed_size']):.4f} {p['coin']}", file=sys.stderr)
        else:
            print(f"    No active positions for {label}", file=sys.stderr)
            degraded_count += 1

    overall_status = "healthy" if healthy_count > 0 and healthy_count >= len(TRACKED_ADDRESSES) // 2 else "degraded"

    # Step 3: Build output
    output = {
        "run_id": run_id,
        "snapshot_time_utc": snapshot_time,
        "lane": "lane1_hyperliquid",
        "positions": all_positions,
        "source_health": make_source_health(
            source=source,
            status=overall_status,
            occurred_at_utc=snapshot_time,
            error_type=None if overall_status == "healthy" else "partial_degraded",
            retryable=True if overall_status == "degraded" else None,
            message_summary=f"{healthy_count}/{len(TRACKED_ADDRESSES)} addresses OK, "
                           f"{len(all_positions)} positions found" if overall_status == "healthy"
                           else f"{degraded_count}/{len(TRACKED_ADDRESSES)} addresses degraded",
        ),
        "errors": errors if errors else None,
    }
    if not errors:
        del output["errors"]

    output_path = os.path.join(OUTPUT_DIR, "lane1_whale_positions.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - start_time
    print(f"  Done in {elapsed:.1f}s. {len(all_positions)} positions from "
          f"{healthy_count}/{len(TRACKED_ADDRESSES)} addresses.", file=sys.stderr)
    print(f"  Output: {output_path}", file=sys.stderr)

    return 0 if overall_status == "healthy" else 1


if __name__ == "__main__":
    sys.exit(main())
