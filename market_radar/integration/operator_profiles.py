"""Operator Profiles — stable configuration presets for internal operators.

Each profile defines exact bounds, risk level, and allowed network access.
No profile enables sending, daemons, schedulers, or infinite loops.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional
import hashlib
import json


@dataclass
class OperatorProfile:
    """Internal operator profile for Integration runs.

    Profiles are validated at construction and rejected if unsafe.
    """
    name: str
    mode: str = "fixture"
    no_send: bool = True
    max_runs: int = 1
    interval_seconds: float = 0.0
    feed_limit: int = 100
    feed_max_pages: int = 5
    feed_max_items: int = 500
    feed_timeout_seconds: float = 15.0
    feed_enabled: bool = True
    whale_enabled: bool = True
    markets_enabled: bool = True
    network_allowed: bool = False
    timeout: float = 30.0
    output_verbosity: str = "normal"
    risk_level: str = "low"
    description: str = ""
    expected_max_requests: int = 10
    expected_max_runtime_seconds: float = 120.0

    def __post_init__(self) -> None:
        valid_modes = {"fixture", "live-public"}
        if self.mode not in valid_modes:
            raise ValueError(f"Invalid mode '{self.mode}'; must be one of {valid_modes}")
        if not self.no_send:
            raise ValueError("no_send must be True for all operator profiles")
        if self.max_runs < 1:
            raise ValueError(f"max_runs must be >= 1, got {self.max_runs}")
        if self.max_runs > 2:
            raise ValueError(f"default operator profiles max_runs <= 2, got {self.max_runs}")
        if self.timeout <= 0 or not isinstance(self.timeout, (int, float)):
            raise ValueError(f"timeout must be a positive number, got {self.timeout}")
        if self.feed_timeout_seconds <= 0:
            raise ValueError(f"feed_timeout_seconds must be > 0, got {self.feed_timeout_seconds}")
        if not self.name:
            raise ValueError("profile name must be non-empty")
        if self.mode == "live-public" and not self.network_allowed:
            raise ValueError("live-public mode requires network_allowed=True")
        if self.output_verbosity not in ("minimal", "normal", "verbose"):
            raise ValueError(f"output_verbosity must be minimal/normal/verbose, got {self.output_verbosity}")
        if self.risk_level not in ("low", "medium", "high"):
            raise ValueError(f"risk_level must be low/medium/high, got {self.risk_level}")

    def profile_hash(self) -> str:
        """Deterministic hash of profile config (excluding name/description)."""
        d = {k: v for k, v in asdict(self).items() if k not in ("name", "description")}
        raw = json.dumps(d, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["profile_hash"] = self.profile_hash()
        return d


# ── Built-in profiles ────────────────────────────────────────────────

FIXTURE_SMOKE = OperatorProfile(
    name="fixture-smoke",
    mode="fixture",
    no_send=True,
    max_runs=1,
    feed_enabled=False,
    whale_enabled=False,
    markets_enabled=True,
    network_allowed=False,
    feed_limit=10,
    feed_max_pages=1,
    feed_max_items=50,
    timeout=15.0,
    output_verbosity="minimal",
    risk_level="low",
    description="Quick fixture-mode smoke test — no network, no whale, minimal feed",
    expected_max_requests=3,
    expected_max_runtime_seconds=10.0,
)

LIVE_ONE_SHOT = OperatorProfile(
    name="live-one-shot",
    mode="live-public",
    no_send=True,
    max_runs=1,
    feed_enabled=True,
    whale_enabled=True,
    markets_enabled=True,
    network_allowed=True,
    feed_limit=100,
    feed_max_pages=5,
    feed_max_items=500,
    feed_timeout_seconds=15.0,
    timeout=30.0,
    output_verbosity="normal",
    risk_level="medium",
    description="Single live one-shot — Curated Feed, Whale, and Markets",
    expected_max_requests=15,
    expected_max_runtime_seconds=180.0,
)

LIVE_SHADOW_2 = OperatorProfile(
    name="live-shadow-2",
    mode="live-public",
    no_send=True,
    max_runs=2,
    interval_seconds=0.0,
    feed_enabled=True,
    whale_enabled=True,
    markets_enabled=True,
    network_allowed=True,
    feed_limit=100,
    feed_max_pages=5,
    feed_max_items=500,
    feed_timeout_seconds=15.0,
    timeout=30.0,
    output_verbosity="normal",
    risk_level="medium",
    description="Two-round bounded shadow — cursor reuse, baseline + change detection",
    expected_max_requests=30,
    expected_max_runtime_seconds=360.0,
)

FEED_DIAGNOSTIC = OperatorProfile(
    name="feed-diagnostic",
    mode="live-public",
    no_send=True,
    max_runs=1,
    feed_enabled=True,
    whale_enabled=False,
    markets_enabled=False,
    network_allowed=True,
    feed_limit=200,
    feed_max_pages=3,
    feed_max_items=200,
    feed_timeout_seconds=20.0,
    timeout=30.0,
    output_verbosity="verbose",
    risk_level="low",
    description="Feed-only diagnostic — fetch Curated Feed, inspect source health",
    expected_max_requests=3,
    expected_max_runtime_seconds=60.0,
)

MARKET_DIAGNOSTIC = OperatorProfile(
    name="market-diagnostic",
    mode="live-public",
    no_send=True,
    max_runs=1,
    feed_enabled=False,
    whale_enabled=False,
    markets_enabled=True,
    network_allowed=True,
    timeout=30.0,
    output_verbosity="verbose",
    risk_level="low",
    description="Market-only diagnostic — CCXT BTC/ETH/SOL + Hyperliquid HYPE",
    expected_max_requests=4,
    expected_max_runtime_seconds=60.0,
)

WHALE_DIAGNOSTIC = OperatorProfile(
    name="whale-diagnostic",
    mode="live-public",
    no_send=True,
    max_runs=1,
    feed_enabled=False,
    whale_enabled=True,
    markets_enabled=False,
    network_allowed=True,
    timeout=30.0,
    output_verbosity="verbose",
    risk_level="medium",
    description="Whale-only diagnostic — clearinghouseState, mark price, W2 domain",
    expected_max_requests=3,
    expected_max_runtime_seconds=60.0,
)

FULL_INTERNAL_REVIEW = OperatorProfile(
    name="full-internal-review",
    mode="live-public",
    no_send=True,
    max_runs=2,
    interval_seconds=0.0,
    feed_enabled=True,
    whale_enabled=True,
    markets_enabled=True,
    network_allowed=True,
    feed_limit=100,
    feed_max_pages=5,
    feed_max_items=500,
    feed_timeout_seconds=15.0,
    timeout=30.0,
    output_verbosity="verbose",
    risk_level="high",
    description="Full internal review — all sources, two rounds, verbose output",
    expected_max_requests=30,
    expected_max_runtime_seconds=360.0,
)

# Registry
BUILTIN_PROFILES: dict[str, OperatorProfile] = {
    "fixture-smoke": FIXTURE_SMOKE,
    "live-one-shot": LIVE_ONE_SHOT,
    "live-shadow-2": LIVE_SHADOW_2,
    "feed-diagnostic": FEED_DIAGNOSTIC,
    "market-diagnostic": MARKET_DIAGNOSTIC,
    "whale-diagnostic": WHALE_DIAGNOSTIC,
    "full-internal-review": FULL_INTERNAL_REVIEW,
}


def get_profile(name: str) -> OperatorProfile:
    """Get a built-in profile by name. Raises ValueError for unknown profiles."""
    if name not in BUILTIN_PROFILES:
        raise ValueError(
            f"Unknown profile '{name}'. Available: {', '.join(sorted(BUILTIN_PROFILES))}"
        )
    return BUILTIN_PROFILES[name]
