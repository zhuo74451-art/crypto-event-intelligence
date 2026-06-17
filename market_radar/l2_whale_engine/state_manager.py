"""L2 — Atomic State Manager for whale position snapshots.

Persists previous snapshot state and loads it for change detection.
Uses atomic write (write to .tmp → os.replace) to prevent corruption.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from market_radar.l1_hyperliquid_provider.provenance import utc_now_str


def make_position_key(address: str, coin: str) -> str:
    return f"{address.lower()}:{coin.upper()}"


def extract_snapshot(position: dict, with_provenance: bool = False) -> dict:
    """Extract comparison-relevant fields from a WhalePosition dict."""
    snap = {
        "signed_size": position.get("signed_size"),
        "position_value_usd": position.get("position_value_usd"),
        "entry_price": position.get("entry_price"),
        "mark_price": position.get("mark_price"),
        "unrealized_pnl_usd": position.get("unrealized_pnl_usd"),
        "leverage": position.get("leverage"),
        "liquidation_price": position.get("liquidation_price"),
        "liquidation_distance_pct": position.get("liquidation_distance_pct"),
        "snapshot_time_utc": position.get("snapshot_time_utc"),
    }
    if with_provenance and "_provenance" in position:
        snap["_provenance"] = position["_provenance"]
    return snap


class StateManager:
    """Manages previous state for change detection.

    Thread-safe for sequential use (no concurrent writers).
    """

    def __init__(self, state_dir: str):
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)
        self.state_path = os.path.join(state_dir, "previous_whale_positions.json")
        self._loaded: Optional[dict] = None

    def load_previous(self) -> dict[str, dict]:
        """Load previous position state keyed by address:coin.

        Returns empty dict if no previous state or file is corrupt.
        """
        if self._loaded is not None:
            return self._loaded

        if not os.path.isfile(self.state_path):
            self._loaded = {}
            return self._loaded

        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw = data.get("positions_by_key", {})
            self._loaded = raw
            return raw
        except (IOError, json.JSONDecodeError):
            self._loaded = {}
            return {}

    def save_current(self, positions: list[dict]) -> None:
        """Atomically save current positions as previous state."""
        by_key: dict[str, dict] = {}
        for p in positions:
            key = make_position_key(p.get("address", ""), p.get("coin", ""))
            by_key[key] = extract_snapshot(p)

        state = {
            "saved_at_utc": utc_now_str(),
            "count": len(positions),
            "positions_by_key": by_key,
        }

        # Atomic write
        tmp_path = self.state_path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.state_path)
        except IOError:
            # Cleanup temp file
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise

    @property
    def is_first_run(self) -> bool:
        return not os.path.isfile(self.state_path)

    def get_previous_for(self, address: str, coin: str) -> Optional[dict]:
        """Get previous snapshot for a specific position."""
        key = make_position_key(address, coin)
        return self.load_previous().get(key)

    def clear(self) -> None:
        """Clear previous state (for testing)."""
        self._loaded = {}
        if os.path.isfile(self.state_path):
            os.remove(self.state_path)
