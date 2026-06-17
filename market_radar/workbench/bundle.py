"""WorkbenchBundle — all data the workbench needs, fully typed."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from market_radar.intelligence_feed.models import FeedItem
from market_radar.market_view.models import MarketSnapshot, MarketHealth


@dataclass
class WorkbenchBundle:
    """Complete input bundle for the workbench renderer.

    All fields are optional — renderer must handle None/empty gracefully.
    """
    run_id: str = ""
    generated_at: str = ""

    # Feed section
    feed_items: list[FeedItem] = field(default_factory=list)

    # Market section
    market_snapshots: list[MarketSnapshot] = field(default_factory=list)
    market_health: list[MarketHealth] = field(default_factory=list)

    # Whale sections (input slots — populated by others)
    whale_positions: list[dict] = field(default_factory=list)
    whale_changes: list[dict] = field(default_factory=list)

    # Alert candidates
    alert_candidates: list[dict] = field(default_factory=list)

    # Event journal
    event_journal: list[dict] = field(default_factory=list)

    # Market regime (placeholder only if inputs exist)
    market_regime: dict = field(default_factory=dict)

    # Watchlists
    watchlists: dict = field(default_factory=dict)

    # Status
    warnings: list[str] = field(default_factory=list)
    degraded_paths: list[str] = field(default_factory=list)
    feed_truth: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["feed_items"] = [f.as_dict() for f in self.feed_items]
        d["market_snapshots"] = [s.as_dict() for s in self.market_snapshots]
        d["market_health"] = [{"venue": h.venue.value, "asset": h.asset,
                                "status": h.status, "message": h.message}
                              for h in self.market_health]
        return d
