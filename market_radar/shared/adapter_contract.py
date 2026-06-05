"""Market Radar v117 — Adapter Contract (Shared Pipeline).

Unified adapter interface that converts fixture/local payload or free public
API payload into a NormalizedSignal.

Input:
  - fixture/local payload (dict or structured data)
  - or free public API payload (dict or structured data)

Output: NormalizedSignal

Required signal fields:
  source_type, card_family, asset_or_topic, timestamp,
  metrics, source_refs, risk_notes
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from market_radar.shared.models import (
    CardFamily,
    DataSourceType,
    NormalizedSignal,
    china_now,
    PIPELINE_VERSION,
)


# ── Adapter Contract ───────────────────────────────────────────────────────


class SignalAdapter(ABC):
    """Abstract adapter: converts source data → NormalizedSignal."""

    def __init__(self, card_family: CardFamily, source_type: DataSourceType):
        self.card_family = (
            card_family if isinstance(card_family, CardFamily) else CardFamily(card_family)
        )
        self.source_type = (
            source_type if isinstance(source_type, DataSourceType) else DataSourceType(source_type)
        )

    @abstractmethod
    def fetch(self) -> NormalizedSignal:
        """Fetch data from source and return a NormalizedSignal.

        Subclasses should:
          1. Acquire data (fixture dict, local file, or free public API response)
          2. Normalize into a NormalizedSignal
          3. Return the signal

        If data acquisition fails, return a signal with empty metrics and
        a risk_note indicating the failure reason. Never raise unhandled
        exceptions — errors become risk_notes.
        """
        ...

    @property
    def adapter_label(self) -> str:
        return f"{self.__class__.__name__}({self.card_family.value}, {self.source_type.value})"


# ── Fixture Adapter ────────────────────────────────────────────────────────


class FixtureSignalAdapter(SignalAdapter):
    """Adapter that produces NormalizedSignal from a pre-defined fixture dict.

    This is NOT a real data adapter — it provides deterministic fixture data
    for pipeline testing and card rendering validation.
    """

    def __init__(
        self,
        card_family: CardFamily,
        fixture: dict[str, Any],
        source_type: DataSourceType = DataSourceType.FIXTURE,
    ):
        super().__init__(card_family, source_type)
        self.fixture = fixture

    def fetch(self) -> NormalizedSignal:
        """Return a NormalizedSignal built from the fixture dict."""
        return NormalizedSignal(
            source_type=self.source_type,
            card_family=self.card_family,
            asset_or_topic=self.fixture.get("asset_or_topic", self.card_family.value),
            timestamp=china_now(),
            metrics=self.fixture.get("metrics", {}),
            source_refs=self.fixture.get("source_refs", ["fixture"]),
            risk_notes=self.fixture.get("risk_notes", ["fixture data — not real"]),
            pipeline_version=PIPELINE_VERSION,
        )


# ── Fixture Definitions for Five Card Families ─────────────────────────────


@dataclass
class FixtureCatalog:
    """Pre-built fixtures for all five card families."""
    fixtures: dict[str, dict] = field(default_factory=dict)

    def __post_init__(self):
        if not self.fixtures:
            self.fixtures = _build_all_fixtures()

    def get(self, card_family: str | CardFamily) -> dict:
        if isinstance(card_family, CardFamily):
            card_family = card_family.value
        return self.fixtures.get(card_family, {})

    def adapter_for(self, card_family: str | CardFamily) -> FixtureSignalAdapter:
        return FixtureSignalAdapter(
            card_family=CardFamily(card_family) if isinstance(card_family, str) else card_family,
            fixture=self.get(card_family),
        )


def _build_all_fixtures() -> dict[str, dict]:
    """Build fixture data for all five card families."""
    return {
        CardFamily.MULTI_ASSET_MARKET_SYNC.value: {
            "asset_or_topic": "BTC/ETH/SOL",
            "metrics": {
                "assets": [
                    {"symbol": "BTCUSDT", "price": 89000.0, "price_change_pct": -1.23, "volume_24h": 28_500_000_000},
                    {"symbol": "ETHUSDT", "price": 3200.0, "price_change_pct": 2.45, "volume_24h": 12_300_000_000},
                    {"symbol": "SOLUSDT", "price": 175.0, "price_change_pct": 5.67, "volume_24h": 3_100_000_000},
                ],
                "correlation_score": 0.72,
                "sync_observation": "ETH and SOL outperforming BTC — risk-on rotation signal",
            },
            "source_refs": [
                "fixture:binance_spot_24hr",
                "fixture:cross_asset_correlation",
            ],
            "risk_notes": [
                "Fixture data — not real market data",
                "Correlation score is simulated",
            ],
        },
        CardFamily.PRICE_OI_VOLUME_ANOMALY.value: {
            "asset_or_topic": "ETHUSDT",
            "metrics": {
                "symbol": "ETHUSDT",
                "price": 3200.0,
                "price_change_24h_pct": 2.45,
                "quote_volume_24h": 12_300_000_000,
                "open_interest_current": 8_200_000_000,
                "oi_delta_pct": 8.5,
                "anomaly_type": "price_oi_divergence",
                "confirmation_factors": ["price_up", "oi_up", "volume_spike", "funding_positive"],
                "admission_passed": True,
                "oi_history_missing": False,
            },
            "source_refs": [
                "fixture:binance_spot_24hr",
                "fixture:binance_open_interest",
            ],
            "risk_notes": [
                "Fixture data — not real market data",
            ],
        },
        CardFamily.NEWS_EVENT_MARKET_IMPACT.value: {
            "asset_or_topic": "BTC regulatory development",
            "metrics": {
                "source_name": "CryptoNews",
                "title": "SEC Approves Spot BTC ETF Options — Market Impact Analysis",
                "url": "https://example.com/news/btc-etf-options",
                "event_type": "ETF",
                "intensity": "high",
                "attribution_risk": "direct",
                "extraction_method": "rule_based",
                "assets_affected": ["BTCUSDT"],
                "market_snapshot": {
                    "BTCUSDT_price": 89000.0,
                    "BTCUSDT_price_change_pct": -1.23,
                },
            },
            "source_refs": [
                "fixture:public_news_source",
                "fixture:binance_market_snapshot",
            ],
            "risk_notes": [
                "Fixture data — not real news",
                "Observation only — not causal proof",
            ],
        },
        CardFamily.LIQUIDATION_PRESSURE.value: {
            "asset_or_topic": "BTCUSDT/ETHUSDT/SOLUSDT",
            "metrics": {
                "assets": [
                    {
                        "symbol": "BTCUSDT",
                        "long_short_ratio": 1.8,
                        "long_liquidation_24h": 12_500_000,
                        "short_liquidation_24h": 8_300_000,
                        "funding_rate": 0.0001,
                    },
                    {
                        "symbol": "ETHUSDT",
                        "long_short_ratio": 2.1,
                        "long_liquidation_24h": 5_200_000,
                        "short_liquidation_24h": 4_100_000,
                        "funding_rate": 0.0003,
                    },
                    {
                        "symbol": "SOLUSDT",
                        "long_short_ratio": 2.5,
                        "long_liquidation_24h": 2_800_000,
                        "short_liquidation_24h": 1_900_000,
                        "funding_rate": 0.0005,
                    },
                ],
                "composite_score": 0.35,
                "admission_threshold": 0.60,
                "calm_market": True,
            },
            "source_refs": [
                "fixture:binance_liquidation_data",
                "fixture:binance_funding_rate",
            ],
            "risk_notes": [
                "Fixture data — not real liquidation data",
                "Liquidation gate NOT lowered — designed as event-triggered card",
            ],
        },
        CardFamily.WHALE_POSITION_ALERT.value: {
            "asset_or_topic": "Hyperliquid whale address tracking",
            "metrics": {
                "addresses_tracked": [
                    {"address": "0x1111...aaaa", "position_size_usd": 50_000_000, "direction": "long"},
                    {"address": "0x2222...bbbb", "position_size_usd": 35_000_000, "direction": "short"},
                    {"address": "0x3333...cccc", "position_size_usd": 28_000_000, "direction": "long"},
                    {"address": "0x4444...dddd", "position_size_usd": 22_000_000, "direction": "short"},
                ],
                "total_exposure_usd": 135_000_000,
                "manual_evidence_provided": False,
                "address_attribution_status": "empty — requires human verification",
            },
            "source_refs": [
                "fixture:hyperliquid_positions",
                "fixture:operator_workbook",
            ],
            "risk_notes": [
                "Fixture data — not real whale positions",
                "Manual evidence required — address attribution cannot be automated",
                "Do NOT bypass manual evidence requirement",
            ],
        },
    }
