"""MVP+ L1 — Hyperliquid Whale Position Fetcher.

Fetches current positions for tracked whale addresses from Hyperliquid's
public Info API via the hyperliquid-python-sdk (no API key required).

Outputs list[WhalePosition] contracts. All errors become degraded results,
never exceptions.

Design:
  - Reads tracked addresses from config or defaults
  - Uses Info.user_state() (clearinghouseState) per address
  - Normalizes raw HL data into WhalePosition contracts
  - Provides fixture fallback on network failure
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from market_radar.shared.contracts import (
    WhalePosition,
    PositionSide,
    EntityType,
    LabelConfidence,
    DegradedInfo,
    SourceHealth,
    SourceStatus,
)

# ── Constants ────────────────────────────────────────────────────────────────

L1_SOURCE_NAME = "hyperliquid_whale_fetcher"
L1_SOURCE_GROUP = "hyperliquid"
USER_AGENT = "MVPPlus-L1/1.0 (read-only whale position fetcher)"

# Tracked whale addresses (from v112w field mapping config)
DEFAULT_WHALE_ADDRESSES: list[dict] = [
    {
        "address": "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
        "label": "Matrixport Related",
        "entity_type": "fund_wallet",
        "confidence": "MEDIUM",
    },
    {
        "address": "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
        "label": "loraclexyz",
        "entity_type": "high_leverage_trader",
        "confidence": "MEDIUM",
    },
    {
        "address": "0x082e843a431aef031264dc232693dd710aedca88",
        "label": "Unknown HYPE Whale",
        "entity_type": "unknown_whale",
        "confidence": "LOW",
    },
    {
        "address": "0x50b309f78e774a756a2230e1769729094cac9f20",
        "label": "Unknown Hyperliquid Whale",
        "entity_type": "unknown_whale",
        "confidence": "LOW",
    },
]

# ── Helpers ──────────────────────────────────────────────────────────────────


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(val: Any) -> Optional[float]:
    """Safely convert a value to float. Returns None if not possible."""
    if val is None:
        return None
    try:
        return float(str(val).strip())
    except (ValueError, TypeError, AttributeError):
        return None


def _parse_hl_position(
    raw_position: dict,
    address: str,
    label_info: dict | None,
    observed_at: str,
) -> WhalePosition | None:
    """Parse a raw Hyperliquid assetPosition into a WhalePosition contract.

    Returns None if the position is empty or unparseable.
    """
    pos = raw_position.get("position", {})
    if not pos:
        return None

    # Coin/asset
    coin = pos.get("coin", "")
    if not coin:
        return None

    # Side determination: positive szi = LONG, negative = SHORT
    szi_raw = _safe_float(pos.get("szi"))
    if szi_raw is None or szi_raw == 0.0:
        return None  # No position or zero size
    side = PositionSide.LONG if szi_raw > 0 else PositionSide.SHORT

    position_value = _safe_float(pos.get("positionValue"))
    if position_value is None or position_value == 0.0:
        position_value = abs(szi_raw) * (_safe_float(pos.get("entryPx")) or 0)
    if position_value == 0.0:
        return None

    # Entry price
    entry_price = _safe_float(pos.get("entryPx"))

    # Mark price (from positionValue / abs(szi))
    mark_price = None
    abs_szi = abs(szi_raw)
    if abs_szi > 0 and position_value > 0:
        mark_price = position_value / abs_szi

    # Leverage
    leverage = None
    leverage_raw = pos.get("leverage")
    if isinstance(leverage_raw, dict):
        leverage = _safe_float(leverage_raw.get("value"))
    elif leverage_raw is not None:
        leverage = _safe_float(leverage_raw)

    # PnL
    unrealized_pnl = _safe_float(pos.get("unrealizedPnl"))

    # Margin
    margin_used = _safe_float(pos.get("marginUsed"))

    # Liquidation
    liquidation_price = _safe_float(pos.get("liquidationPx"))

    # Liquidation distance %
    liquidation_distance_pct = None
    if liquidation_price is not None and mark_price is not None and mark_price > 0:
        liquidation_distance_pct = abs(mark_price - liquidation_price) / mark_price * 100

    # Label info
    label = None
    entity_type = None
    label_confidence = None
    if label_info:
        label = label_info.get("label")
        et = label_info.get("entity_type")
        if et:
            try:
                entity_type = EntityType(et.upper())
            except ValueError:
                entity_type = EntityType.UNCLASSIFIED
        lc = label_info.get("confidence", "").upper()
        if lc in ("HIGH", "MEDIUM", "LOW"):
            label_confidence = LabelConfidence(lc)

    return WhalePosition(
        address=address.lower(),
        asset=coin.upper(),
        side=side,
        position_size_usd=round(position_value, 2),
        observed_at=observed_at,
        entry_price=round(entry_price, 2) if entry_price else None,
        mark_price=round(mark_price, 2) if mark_price else None,
        leverage=round(leverage, 2) if leverage else None,
        unrealized_pnl_usd=round(unrealized_pnl, 2) if unrealized_pnl else None,
        margin_used_usd=round(margin_used, 2) if margin_used else None,
        liquidation_price=round(liquidation_price, 2) if liquidation_price else None,
        liquidation_distance_pct=round(liquidation_distance_pct, 4) if liquidation_distance_pct else None,
        label=label,
        entity_type=entity_type,
        label_confidence=label_confidence,
        data_origin="live",
        source=L1_SOURCE_NAME,
    )


# ── Main Fetcher ─────────────────────────────────────────────────────────────


class WhalePositionFetcher:
    """Fetches current positions for tracked Hyperliquid whale addresses.

    Uses hyperliquid-python-sdk Info.user_state() (read-only, no API key).
    Falls back to fixture data on network failure.
    """

    def __init__(
        self,
        addresses: Optional[list[dict]] = None,
        use_fixture: bool = False,
    ):
        self.addresses = addresses or DEFAULT_WHALE_ADDRESSES
        self.use_fixture = use_fixture
        self.health = SourceHealth(
            source_name=L1_SOURCE_NAME,
            source_group=L1_SOURCE_GROUP,
            status=SourceStatus.UNKNOWN,
        )
        self._info = None  # Lazy init

    def _get_info(self):
        """Lazy-init Hyperliquid Info client."""
        if self._info is None:
            try:
                from hyperliquid.info import Info
                self._info = Info(timeout=15)
            except Exception:
                self._info = None
        return self._info

    def fetch(self) -> tuple[list[WhalePosition], SourceHealth]:
        """Fetch whale positions from Hyperliquid + label enrichment.

        Returns (positions, source_health).
        Never raises — all errors captured in source_health.
        """
        observed_at = _utc_now()
        positions: list[WhalePosition] = []
        errors: list[str] = []
        api_success_count = 0
        api_error_count = 0
        start_time = time.time()

        if self.use_fixture:
            return self._fetch_fixture(observed_at)

        info = self._get_info()
        if info is None:
            errors.append("hyperliquid_sdk_init_failed: could not create Info client")
            self.health = SourceHealth(
                source_name=L1_SOURCE_NAME,
                source_group=L1_SOURCE_GROUP,
                status=SourceStatus.DEGRADED,
                last_error_at=observed_at,
                error_count=1,
                consecutive_failures=1,
                degraded_info=DegradedInfo(
                    error_type="SDK_INIT_FAILURE",
                    occurred_at=observed_at,
                    retryable=True,
                    message_summary="Could not initialize hyperliquid SDK Info client",
                ),
            )
            # Fall back to fixture
            return self._fetch_fixture(observed_at)

        for entry in self.addresses:
            address = entry.get("address", "").strip().lower()
            if not address:
                continue

            try:
                state = info.user_state(address)
                asset_positions = state.get("assetPositions", []) if isinstance(state, dict) else []

                if not asset_positions:
                    api_success_count += 1
                    continue

                for raw_pos in asset_positions:
                    wp = _parse_hl_position(raw_pos, address, entry, observed_at)
                    if wp is not None:
                        positions.append(wp)

                api_success_count += 1

            except Exception as e:
                api_error_count += 1
                errors.append(f"fetch_failed:{address[:12]}:{type(e).__name__}")

        elapsed_ms = round((time.time() - start_time) * 1000, 1)

        # Build source health
        total_attempts = len(self.addresses)
        if api_success_count == total_attempts:
            status = SourceStatus.OK
        elif api_success_count > 0:
            status = SourceStatus.DEGRADED
        else:
            status = SourceStatus.DEGRADED

        degraded_info = None
        if errors:
            degraded_info = DegradedInfo(
                error_type="PARTIAL_FETCH_FAILURE",
                occurred_at=observed_at,
                retryable=True,
                message_summary=f"{len(errors)}/{total_attempts} address fetches failed",
                retry_attempts=0,
            )

        self.health = SourceHealth(
            source_name=L1_SOURCE_NAME,
            source_group=L1_SOURCE_GROUP,
            status=status,
            last_success_at=observed_at if api_success_count > 0 else None,
            last_error_at=observed_at if errors else None,
            latency_ms=elapsed_ms,
            success_count=api_success_count,
            error_count=api_error_count,
            consecutive_failures=api_error_count,
            degraded_info=degraded_info,
        )

        return positions, self.health

    def _fetch_fixture(self, observed_at: str) -> tuple[list[WhalePosition], SourceHealth]:
        """Load fixture positions for testing/demonstration."""
        fixtures_path = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "market_radar_v112f_whale_positions.json"
        if fixtures_path.exists():
            try:
                with open(fixtures_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                raw_list = data.get("positions", [])
            except Exception:
                raw_list = []
        else:
            raw_list = []

        positions = []
        address_map = {e["address"].lower(): e for e in self.addresses if e.get("address")}

        for raw in raw_list:
            if not raw.get("valid", False) or raw.get("blocked", False):
                continue
            wallet = raw.get("wallet", "").lower()
            label_entry = address_map.get(wallet, {})
            asset = raw.get("asset", "").upper()
            side_str = raw.get("side", "").lower()

            side = PositionSide.LONG if side_str == "long" else PositionSide.SHORT if side_str == "short" else None
            if side is None:
                continue

            entry_price = _safe_float(raw.get("entry_price"))
            mark_price = _safe_float(raw.get("mark_price"))
            position_size = _safe_float(raw.get("position_size_usd"))
            leverage = _safe_float(raw.get("leverage"))
            unrealized_pnl = _safe_float(raw.get("unrealized_pnl_usd"))
            margin_used = _safe_float(raw.get("margin_used_usd"))
            liquidation_price = _safe_float(raw.get("liquidation_price"))

            liquidation_distance_pct = None
            if liquidation_price is not None and mark_price is not None and mark_price > 0:
                liquidation_distance_pct = abs(mark_price - liquidation_price) / mark_price * 100

            label = label_entry.get("label") or raw.get("label")
            et_str = (label_entry.get("entity_type") or raw.get("entity_type") or "").upper()
            entity_type = None
            try:
                entity_type = EntityType(et_str)
            except ValueError:
                entity_type = EntityType.UNKNOWN_WHALE
            lc_str = (label_entry.get("confidence") or "").upper()
            label_confidence = None
            if lc_str in ("HIGH", "MEDIUM", "LOW"):
                label_confidence = LabelConfidence(lc_str)

            positions.append(WhalePosition(
                address=wallet,
                asset=asset,
                side=side,
                position_size_usd=round(position_size, 2) if position_size else 0.0,
                observed_at=observed_at,
                entry_price=round(entry_price, 2) if entry_price else None,
                mark_price=round(mark_price, 2) if mark_price else None,
                leverage=round(leverage, 2) if leverage else None,
                unrealized_pnl_usd=round(unrealized_pnl, 2) if unrealized_pnl else None,
                margin_used_usd=round(margin_used, 2) if margin_used else None,
                liquidation_price=round(liquidation_price, 2) if liquidation_price else None,
                liquidation_distance_pct=round(liquidation_distance_pct, 4) if liquidation_distance_pct else None,
                label=label,
                entity_type=entity_type,
                label_confidence=label_confidence,
                data_origin="fixture",
                source="fixture_v112f",
            ))

        self.health = SourceHealth(
            source_name=L1_SOURCE_NAME,
            source_group=L1_SOURCE_GROUP,
            status=SourceStatus.DEGRADED,
            last_error_at=observed_at,
            success_count=0,
            error_count=0,
            consecutive_failures=0,
            degraded_info=DegradedInfo(
                error_type="FIXTURE_FALLBACK",
                occurred_at=observed_at,
                retryable=True,
                message_summary="Using fixture data — live API unavailable or fixture mode enabled",
            ),
        )
        return positions, self.health
