"""Market Radar v1.17 — Unified Renderer Contract

Abstract renderer interface that takes a NormalizedSnapshot and produces
a clean, public-ready card text. Each card type has its own renderer
implementation that follows the public template rules from v112a.

This is the FOURTH layer in the v117 pipeline:
  ... → NormalizedSnapshot → Renderer → public_card → ...

Design:
  - Abstract CardRenderer base class with render(snapshot) -> str
  - Five concrete renderers (one per card type)
  - Each renderer reuses the v112a card_type_registry template rules
  - Post-render: mandatory debug leak scan
  - Renderers are stateless and pure functions

Constraints:
  - No external API calls
  - No TG send
  - No daemon/cron/loop
  - No token/key/secret read or print

Usage:
    from scripts.market_radar_renderer_contract_v117 import (
        CardRenderer, RendererRegistry, render_card,
    )

    registry = RendererRegistry()
    renderer = registry.get_renderer("price_oi_volume_anomaly")
    public_card = renderer.render(snapshot)
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Any

CN_TZ = timezone(timedelta(hours=8))
RENDERER_VERSION = "v1.17"

# Import the existing card type registry for template rules
try:
    from scripts.market_radar_card_type_registry_v112a import (
        CARD_TYPE_REGISTRY,
        get_card_type,
        render_public_preview,
        check_public_debug_leak,
    )
except ImportError:
    import sys
    import os
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    if _script_dir not in sys.path:
        sys.path.insert(0, _script_dir)
    from market_radar_card_type_registry_v112a import (
        CARD_TYPE_REGISTRY,
        get_card_type,
        render_public_preview,
        check_public_debug_leak,
    )


def china_stamp() -> str:
    """Return current time in UTC+8 format."""
    return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


# ══════════════════════════════════════════════════════════════════════════════════════
# Abstract Renderer Base
# ══════════════════════════════════════════════════════════════════════════════════════

class CardRenderer(ABC):
    """Abstract base class for all card renderers.

    Subclasses must implement:
      - card_type (str): The card type key.
      - _render(snapshot) -> str: Produce the public card text.

    The public render() method runs:
      _render() → leak_scan() → verify() → return clean public_card.
    """

    card_type: str

    def __init__(self):
        if not hasattr(self, "card_type") or not self.card_type:
            raise ValueError(f"{self.__class__.__name__} must define card_type")

    @abstractmethod
    def _render(self, snapshot) -> str:
        """Produce the public card text from a NormalizedSnapshot."""
        ...

    def _leak_scan(self, public_card: str) -> list[str]:
        """Scan rendered card for forbidden debug/internal terms.

        Returns list of forbidden terms found.
        """
        card_type_def = get_card_type(self.card_type)
        if card_type_def is None:
            return []
        return check_public_debug_leak(public_card, card_type_def)

    def render(self, snapshot) -> str:
        """Public entry point: render → leak_scan → return.

        Args:
            snapshot: NormalizedSnapshot from an adapter.

        Returns:
            Clean public card text string.

        Raises:
            ValueError if leak scan finds forbidden terms.
        """
        public_card = self._render(snapshot)
        leaks = self._leak_scan(public_card)
        if leaks:
            raise ValueError(
                f"Renderer leak detected for {self.card_type}: {leaks}. "
                f"Public card must not contain internal terms."
            )
        return public_card

    @property
    def renderer_info(self) -> dict:
        """Return renderer metadata."""
        return {
            "renderer_class": self.__class__.__name__,
            "card_type": self.card_type,
            "renderer_version": RENDERER_VERSION,
        }


# ══════════════════════════════════════════════════════════════════════════════════════
# Concrete Renderers — one per card type (delegates to v112a renderers)
# ══════════════════════════════════════════════════════════════════════════════════════

class PriceOIVolumeAnomalyRenderer(CardRenderer):
    """Renderer for price_oi_volume_anomaly cards."""

    card_type = "price_oi_volume_anomaly"

    def _render(self, snapshot) -> str:
        card_type_def = get_card_type(self.card_type)
        if card_type_def is None:
            return f"# Error: Unknown card type {self.card_type}"
        return render_public_preview(card_type_def, snapshot.signal_data)


class WhalePositionAlertRenderer(CardRenderer):
    """Renderer for whale_position_alert cards."""

    card_type = "whale_position_alert"

    def _render(self, snapshot) -> str:
        card_type_def = get_card_type(self.card_type)
        if card_type_def is None:
            return f"# Error: Unknown card type {self.card_type}"
        return render_public_preview(card_type_def, snapshot.signal_data)


class LiquidationPressureRenderer(CardRenderer):
    """Renderer for liquidation_pressure cards."""

    card_type = "liquidation_pressure"

    def _render(self, snapshot) -> str:
        card_type_def = get_card_type(self.card_type)
        if card_type_def is None:
            return f"# Error: Unknown card type {self.card_type}"
        return render_public_preview(card_type_def, snapshot.signal_data)


class MultiAssetMarketSyncRenderer(CardRenderer):
    """Renderer for multi_asset_market_sync cards."""

    card_type = "multi_asset_market_sync"

    def _render(self, snapshot) -> str:
        card_type_def = get_card_type(self.card_type)
        if card_type_def is None:
            return f"# Error: Unknown card type {self.card_type}"
        return render_public_preview(card_type_def, snapshot.signal_data)


class NewsEventMarketImpactRenderer(CardRenderer):
    """Renderer for news_event_market_impact cards."""

    card_type = "news_event_market_impact"

    def _render(self, snapshot) -> str:
        card_type_def = get_card_type(self.card_type)
        if card_type_def is None:
            return f"# Error: Unknown card type {self.card_type}"
        return render_public_preview(card_type_def, snapshot.signal_data)


# ══════════════════════════════════════════════════════════════════════════════════════
# Renderer Registry
# ══════════════════════════════════════════════════════════════════════════════════════

RENDERER_REGISTRY: dict[str, type[CardRenderer]] = {
    "price_oi_volume_anomaly": PriceOIVolumeAnomalyRenderer,
    "whale_position_alert": WhalePositionAlertRenderer,
    "liquidation_pressure": LiquidationPressureRenderer,
    "multi_asset_market_sync": MultiAssetMarketSyncRenderer,
    "news_event_market_impact": NewsEventMarketImpactRenderer,
}


class RendererRegistry:
    """Registry that provides renderer instances for card types."""

    def __init__(self):
        self._renderers: dict[str, CardRenderer] = {}

    def get_renderer(self, card_type: str) -> CardRenderer | None:
        """Get a renderer instance for a card type.

        Returns None if card_type not in registry.
        """
        if card_type in self._renderers:
            return self._renderers[card_type]

        renderer_cls = RENDERER_REGISTRY.get(card_type)
        if renderer_cls is None:
            return None

        renderer = renderer_cls()
        self._renderers[card_type] = renderer
        return renderer

    def list_card_types(self) -> list[str]:
        """Return sorted list of registered card types."""
        return sorted(RENDERER_REGISTRY.keys())


# ── Module-level convenience ────────────────────────────────────────────────────

def render_card(snapshot) -> str:
    """Render a public card from a NormalizedSnapshot (convenience function).

    Args:
        snapshot: NormalizedSnapshot from an adapter.

    Returns:
        Clean public card text string.

    Raises:
        ValueError if card_type not supported or leak scan fails.
    """
    registry = RendererRegistry()
    renderer = registry.get_renderer(snapshot.card_type)
    if renderer is None:
        raise ValueError(f"No renderer for card_type: {snapshot.card_type}")
    return renderer.render(snapshot)


def render_cards(snapshots: list) -> list[str]:
    """Render multiple snapshots to public cards.

    Returns list of public card strings (same order).
    """
    return [render_card(s) for s in snapshots]
