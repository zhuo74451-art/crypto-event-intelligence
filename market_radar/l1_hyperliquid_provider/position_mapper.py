"""L1 — Whale Position Mapper.

Maps raw Hyperliquid API position data → WhalePosition dict
matching contracts/mvpplus/v1/whale_position.schema.json.

Key formulas:
  Liquidation distance (long):  (mark - liq) / mark * 100
  Liquidation distance (short): (liq - mark) / mark * 100
  Null when no valid mark or liq.
"""

from __future__ import annotations

from typing import Any, Optional

from market_radar.l1_hyperliquid_provider.provenance import (
    DataMode, ProvenanceRecord, make_source_health, utc_now_str,
)


def compute_liquidation_distance(
    direction: str,
    mark_price: Optional[float],
    liquidation_price: Optional[float],
) -> Optional[float]:
    """Compute liquidation distance percentage.

    Long:  (mark - liq) / mark * 100  → negative means below entry
    Short: (liq - mark) / mark * 100  → positive means above entry

    Returns None if either price is missing or invalid.
    """
    if mark_price is None or liquidation_price is None:
        return None
    if mark_price <= 0:
        return None

    if direction == "long":
        # Long: (mark - liq) / mark * 100 → positive when liq is below mark (normal)
        return (mark_price - liquidation_price) / mark_price * 100
    elif direction == "short":
        # Short: (liq - mark) / mark * 100 → positive when liq is above mark (normal)
        return (liquidation_price - mark_price) / mark_price * 100


def map_raw_position(
    position: dict,
    address: str,
    label: Optional[str],
    entity_type: Optional[str],
    label_confidence: Optional[str],
    mids: dict[str, str],
    snapshot_time_utc: str,
    provenance: Optional[ProvenanceRecord] = None,
) -> Optional[dict]:
    """Map a single raw Hyperliquid position dict → WhalePosition dict.

    Returns None if position is unparseable (szi=0, missing required fields).
    """
    coin = position.get("coin", "")
    if not coin:
        return None

    # ── Signed size ──
    szi_str = position.get("szi", "0")
    try:
        szi = float(szi_str)
    except (ValueError, TypeError):
        return None

    if szi == 0:
        return None

    # ── Direction ──
    direction = "long" if szi > 0 else "short"
    abs_size = abs(szi)

    # ── Entry price ──
    entry_px_str = position.get("entryPx", "0")
    try:
        entry_price = float(entry_px_str)
    except (ValueError, TypeError):
        entry_price = 0.0

    if entry_price <= 0:
        return None

    # ── Mark price (from allMids, NOT from Binance) ──
    mid_str = mids.get(coin)
    if mid_str is None:
        return None
    try:
        mark_price = float(mid_str)
    except (ValueError, TypeError):
        return None

    if mark_price <= 0:
        return None

    # ── Leverage ──
    lev_obj = position.get("leverage", {})
    if isinstance(lev_obj, dict):
        try:
            leverage = float(lev_obj.get("value", 0))
        except (ValueError, TypeError):
            leverage = 0.0
    else:
        leverage = 0.0

    if leverage == 0:
        # Compute approximate leverage from margin if available
        margin_str = position.get("marginUsed", "0")
        try:
            margin = float(margin_str)
        except (ValueError, TypeError):
            margin = 0.0

        pos_val = abs_size * mark_price
        if margin > 0 and pos_val > 0:
            leverage = round(pos_val / margin, 2)

    # ── Position value ──
    pv_str = position.get("positionValue", "")
    if pv_str:
        try:
            position_value = float(pv_str)
        except (ValueError, TypeError):
            position_value = abs_size * mark_price
    else:
        position_value = abs_size * mark_price

    if position_value <= 0:
        position_value = abs_size * mark_price

    # ── Unrealized PnL ──
    upnl_str = position.get("unrealizedPnl", "0")
    try:
        unrealized_pnl = float(upnl_str)
    except (ValueError, TypeError):
        unrealized_pnl = None

    # ── Liquidation price ──
    liq_str = position.get("liquidationPx")
    liquidation_price: Optional[float] = None
    if liq_str is not None and liq_str != "" and liq_str != "0":
        try:
            liq_val = float(liq_str)
            if liq_val > 0:
                liquidation_price = liq_val
        except (ValueError, TypeError):
            pass

    # ── Liquidation distance ──
    liq_distance = compute_liquidation_distance(
        direction, mark_price, liquidation_price,
    )

    # ── Margin mode ──
    margin_mode: Optional[str] = None
    if isinstance(lev_obj, dict):
        margin_mode = lev_obj.get("type", None)

    # ── Funding rate ──
    cum_funding = position.get("cumFunding", {})
    funding_since_open: Optional[float] = None
    if isinstance(cum_funding, dict):
        try:
            funding_since_open = float(cum_funding.get("sinceOpen", 0))
        except (ValueError, TypeError):
            pass

    # ── Source health ──
    source_health = make_source_health(
        source="hyperliquid_info_public",
        status="healthy",
        occurred_at_utc=snapshot_time_utc,
    )

    result: dict = {
        "address": address,
        "label": label,
        "account_value_usd": None,
        "coin": coin,
        "direction": direction,
        "signed_size": round(szi, 6),
        "absolute_size": round(abs_size, 6),
        "position_value_usd": round(position_value, 2),
        "entry_price": round(entry_price, 2),
        "mark_price": round(mark_price, 2),
        "leverage": round(leverage, 2),
        "unrealized_pnl_usd": round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
        "liquidation_price": round(liquidation_price, 2) if liquidation_price is not None else None,
        "liquidation_distance_pct": round(liq_distance, 4) if liq_distance is not None else None,
        "funding_rate_pct": None,
        "margin_mode": margin_mode,
        "snapshot_time_utc": snapshot_time_utc,
        "data_source": "hyperliquid_info_public",
        "source_health": source_health,
    }

    # Attach provenance if provided
    if provenance is not None:
        result["_provenance"] = provenance.as_dict()

    return result


def validate_position(position: dict) -> list[str]:
    """Validate a mapped WhalePosition against contract rules.

    Returns list of violation strings (empty = valid).
    """
    violations: list[str] = []

    # Required fields (non-null)
    for field in ["address", "coin", "direction", "signed_size",
                  "absolute_size", "position_value_usd", "entry_price",
                  "mark_price", "leverage", "snapshot_time_utc"]:
        if field not in position or position[field] is None:
            violations.append(f"Missing required field: {field}")

    # Direction
    if position.get("direction") not in ("long", "short"):
        violations.append(f"Invalid direction: {position.get('direction')}")

    # Positive prices
    for price_field in ["entry_price", "mark_price"]:
        val = position.get(price_field)
        if val is not None and val <= 0:
            violations.append(f"Non-positive {price_field}: {val}")

    # Leverage
    lev = position.get("leverage")
    if lev is not None and lev < 0:
        violations.append(f"Negative leverage: {lev}")

    # Liquidation consistency
    liq = position.get("liquidation_price")
    liq_dist = position.get("liquidation_distance_pct")
    if liq is None and liq_dist is not None:
        violations.append("liquidation_price is null but liquidation_distance_pct is not null")
    if liq is not None and liq_dist is None:
        # Allow — computation might not be possible
        pass

    # Size consistency
    signed = position.get("signed_size")
    absolute = position.get("absolute_size")
    if signed is not None and absolute is not None:
        if abs(signed) != absolute:
            violations.append(f"signed_size ({signed}) != absolute_size ({absolute}) in magnitude")
        if (signed > 0) != (position.get("direction") == "long"):
            violations.append("Direction inconsistent with signed_size sign")

    return violations


def validate_positions_batch(positions: list[dict]) -> dict:
    """Validate a batch of WhalePositions.

    Returns summary dict with pass/fail counts.
    """
    total = len(positions)
    passed = 0
    all_violations: list[str] = []
    for p in positions:
        v = validate_position(p)
        if not v:
            passed += 1
        else:
            coin = p.get("coin", "?")
            addr = p.get("address", "?")[:10]
            all_violations.append(f"{addr}... {coin}: {'; '.join(v)}")
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "violations": all_violations,
    }
