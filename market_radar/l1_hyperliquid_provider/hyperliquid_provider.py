"""MVP+ Lane 1 — Hyperliquid Provider.

Fetches current whale positions from Hyperliquid public Info API
using the clearinghouseState endpoint. No API key required.

Output: list[WhalePosition] per the sealed contract.

Design:
  - One-shot: single run, no daemon/cron
  - Bounded concurrency: max 4 simultaneous requests
  - Per-address retry: 2 attempts with exponential backoff
  - Graceful degradation: failed addresses return degraded SourceHealth
  - No secret/credential handling
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from market_radar.shared.contracts import (
    WhalePosition,
    PositionSide,
    EntityType,
    LabelConfidence,
    SourceHealth,
    SourceStatus,
    DegradedInfo,
)

# ── Constants ─────────────────────────────────────────────────────────────────

HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
USER_AGENT = "MVPPlus-L1-HyperliquidProvider/1.0 (read-only; public data)"
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 15
MAX_RETRIES = 2
RETRY_BACKOFF = [2.0, 4.0]  # seconds
MAX_CONCURRENCY = 4

VERSION = "mvp+v1.0-l1"

# ── Tracked Addresses ─────────────────────────────────────────────────────────

TRACKED_ADDRESSES: list[dict[str, Any]] = [
    {
        "address": "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
        "label": "Matrixport Related",
        "entity_type": EntityType.FUND_WALLET,
        "confidence": LabelConfidence.MEDIUM,
    },
    {
        "address": "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
        "label": "loraclexyz",
        "entity_type": EntityType.HIGH_LEVERAGE_TRADER,
        "confidence": LabelConfidence.MEDIUM,
    },
    {
        "address": "0x082e843a431aef031264dc232693dd710aedca88",
        "label": "Unknown HYPE Whale",
        "entity_type": EntityType.UNKNOWN_WHALE,
        "confidence": LabelConfidence.LOW,
    },
    {
        "address": "0x50b309f78e774a756a2230e1769729094cac9f20",
        "label": "Unknown Hyperliquid Whale",
        "entity_type": EntityType.UNKNOWN_WHALE,
        "confidence": LabelConfidence.LOW,
    },
]


# ── API Client ────────────────────────────────────────────────────────────────


def _utc_now() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _post_clearinghouse(user: str, attempt: int = 1) -> Optional[dict]:
    """POST to Hyperliquid clearinghouseState for one address.

    Returns parsed dict or None on failure after retries.
    """
    payload = json.dumps({"type": "clearinghouseState", "user": user}).encode("utf-8")
    req = Request(
        HYPERLIQUID_INFO_URL,
        data=payload,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)) as resp:
            data = resp.read().decode("utf-8")
        result = json.loads(data)
        if isinstance(result, dict):
            return result
        return None
    except (URLError, HTTPError, OSError, ValueError, json.JSONDecodeError) as e:
        if attempt < MAX_RETRIES:
            delay = RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)]
            time.sleep(delay)
            return _post_clearinghouse(user, attempt + 1)
        return None


def _parse_hl_clearinghouse_response(
    raw: dict,
    address: str,
    address_meta: dict[str, Any],
    observed_at: str,
) -> list[WhalePosition]:
    """Parse Hyperliquid clearinghouseState response into WhalePosition list.

    The response shape is:
      {
        "assetPositions": [
          {
            "position": {
              "coin": "BTC",
              "szi": "1.234",        # signed size (positive=long, negative=short)
              "leverage": {"type": "isolated", "value": 5.0},
              "entryPx": "89000.0",
              "liquidationPx": "75000.0",
              "unrealizedPnl": "150000.0",
              "positionValue": "50000000.0",
              "marginUsed": "10000000.0",
              "cumFunding": "-1234.5"
            },
            "type": "oneWay"
          }
        ],
        "crossMarginSummary": {...},
        "marginSummary": {...},
        "time": 1234567890,
        ...
      }

    Returns empty list if no positions or parse error.
    """
    positions_raw = raw.get("assetPositions", [])
    if not isinstance(positions_raw, list):
        return []

    results: list[WhalePosition] = []
    label = address_meta.get("label")
    entity_type = address_meta.get("entity_type")
    confidence = address_meta.get("confidence")

    for entry in positions_raw:
        pos = entry.get("position", {}) if isinstance(entry, dict) else {}
        if not isinstance(pos, dict):
            continue

        coin = str(pos.get("coin", "")).strip().upper()
        szi_raw = pos.get("szi")
        if not coin or szi_raw is None:
            continue

        # Parse signed size
        try:
            szi = float(szi_raw)
        except (ValueError, TypeError):
            continue
        if szi == 0.0:
            continue

        side = PositionSide.LONG if szi > 0 else PositionSide.SHORT
        szi_abs = abs(szi)

        # Position value
        position_value = _safe_float(pos.get("positionValue")) or 0.0
        if position_value <= 0:
            # Fallback: compute from szi * mark
            mark = _safe_float(pos.get("markPx"))
            if mark > 0:
                position_value = szi_abs * mark

        # Entry price
        entry_px = _safe_float(pos.get("entryPx")) or None

        # Mark price (compute from position_value / szi_abs)
        mark_px: Optional[float] = None
        if szi_abs > 0 and position_value > 0:
            mark_px = position_value / szi_abs
        else:
            mark_px = _safe_float(pos.get("markPx")) or None

        # Leverage
        leverage_raw = pos.get("leverage", {})
        leverage: Optional[float] = None
        if isinstance(leverage_raw, dict):
            leverage = _safe_float(leverage_raw.get("value"))
        elif isinstance(leverage_raw, (int, float)):
            leverage = float(leverage_raw)

        # Unrealized PnL
        unrealized_pnl = _safe_float(pos.get("unrealizedPnl")) or None

        # Margin used
        margin_used = _safe_float(pos.get("marginUsed")) or None

        # Liquidation price
        liquidation_px = _safe_float(pos.get("liquidationPx")) or None

        # Liquidation distance %
        liquidation_distance: Optional[float] = None
        if mark_px and mark_px > 0 and liquidation_px and liquidation_px > 0:
            liquidation_distance = abs(mark_px - liquidation_px) / mark_px * 100.0

        # Build position (all null for missing data)
        pos_obj = WhalePosition(
            address=address.lower(),
            asset=coin,
            side=side,
            position_size_usd=position_value,
            observed_at=observed_at,
            entry_price=entry_px,
            mark_price=mark_px,
            leverage=leverage,
            unrealized_pnl_usd=unrealized_pnl,
            margin_used_usd=margin_used,
            liquidation_price=liquidation_px,
            liquidation_distance_pct=liquidation_distance,
            label=label,
            entity_type=entity_type,
            label_confidence=confidence,
            data_origin="live",
            source="hyperliquid_info_api",
        )
        results.append(pos_obj)

    return results


def _safe_float(value: Any) -> Optional[float]:
    """Safely parse a float from various types."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# ── Main Provider ─────────────────────────────────────────────────────────────


@dataclass
class L1Result:
    """Aggregated result from a single L1 run."""
    positions: list[WhalePosition] = field(default_factory=list)
    source_health: list[SourceHealth] = field(default_factory=list)
    total_requested: int = 0
    total_succeeded: int = 0
    total_failed: int = 0
    run_id: str = ""
    started_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "lane": "L1",
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_requested": self.total_requested,
            "total_succeeded": self.total_succeeded,
            "total_failed": self.total_failed,
            "position_count": len(self.positions),
            "error": self.error,
        }


def run(
    addresses: Optional[list[dict[str, Any]]] = None,
) -> L1Result:
    """Run the Hyperliquid Provider: fetch all tracked addresses.

    Args:
        addresses: Optional override for tracked addresses.
                   Each entry: {"address": str, "label": str,
                                "entity_type": EntityType, "confidence": LabelConfidence}

    Returns:
        L1Result with positions and per-address source health.
    """
    run_id = uuid.uuid4().hex[:12]
    started_at = _utc_now()
    targets = addresses or TRACKED_ADDRESSES

    positions: list[WhalePosition] = []
    health_records: list[SourceHealth] = []
    succeeded = 0
    failed = 0

    for addr_meta in targets:
        addr = addr_meta.get("address", "")
        if not addr:
            continue

        label = addr_meta.get("label")
        entity_type = addr_meta.get("entity_type")
        confidence = addr_meta.get("confidence")
        source_name = f"hyperliquid_clearinghouse:{addr[:10]}..."

        try:
            observed_at = _utc_now()
            raw = _post_clearinghouse(addr)

            if raw is None:
                # Failed after retries
                failed += 1
                health_records.append(SourceHealth(
                    source_name=source_name,
                    source_group="hyperliquid",
                    status=SourceStatus.FAILED,
                    last_error_at=_utc_now(),
                    success_count=0,
                    error_count=1,
                    consecutive_failures=1,
                    degraded_info=DegradedInfo(
                        error_type="API_REQUEST_FAILED",
                        occurred_at=_utc_now(),
                        retryable=True,
                        message_summary=f"clearinghouseState failed for {addr[:10]}... after {MAX_RETRIES} retries",
                        retry_attempts=MAX_RETRIES,
                    ),
                ))
                continue

            parsed = _parse_hl_clearinghouse_response(raw, addr, addr_meta, observed_at)
            positions.extend(parsed)
            succeeded += 1

            health_records.append(SourceHealth(
                source_name=source_name,
                source_group="hyperliquid",
                status=SourceStatus.OK,
                last_success_at=_utc_now(),
                success_count=1,
                error_count=0,
            ))

        except Exception as e:
            failed += 1
            health_records.append(SourceHealth(
                source_name=source_name,
                source_group="hyperliquid",
                status=SourceStatus.FAILED,
                last_error_at=_utc_now(),
                success_count=0,
                error_count=1,
                consecutive_failures=1,
                degraded_info=DegradedInfo(
                    error_type="UNEXPECTED_ERROR",
                    occurred_at=_utc_now(),
                    retryable=True,
                    message_summary=f"Unexpected error: {type(e).__name__}",
                    retry_attempts=0,
                ),
            ))

    completed_at = _utc_now()

    result = L1Result(
        positions=positions,
        source_health=health_records,
        total_requested=len(targets),
        total_succeeded=succeeded,
        total_failed=failed,
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
    )

    if failed > 0 and succeeded == 0:
        result.error = "All Hyperliquid requests failed — provider fully degraded"

    return result


# ── CLI entry point ───────────────────────────────────────────────────────────


def main():
    """CLI entry: run L1 once and print summary."""
    result = run()
    print(f"L1 Run: {result.run_id}")
    print(f"  Status: {result.total_succeeded}/{result.total_requested} addresses succeeded")
    print(f"  Positions found: {len(result.positions)}")
    for pos in result.positions:
        d = pos.as_dict()
        print(f"    {d['address'][:10]}... | {d['asset']:5s} | {d['side']:5s} | "
              f"${d['position_size_usd']:>12,.0f} | entry=${d.get('entry_price') or 'N/A'} | "
              f"liq_dist={d.get('liquidation_distance_pct') or 'N/A'}")
    if result.error:
        print(f"  ERROR: {result.error}")
    print(f"  Completed at: {result.completed_at}")
    return 0 if result.total_failed == 0 else 1


if __name__ == "__main__":
    main()
