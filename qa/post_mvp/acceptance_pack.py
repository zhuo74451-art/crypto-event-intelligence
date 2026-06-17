"""Post-MVP Multi-Lane Acceptance Pack Framework.

Supports contract-based verification for W1-W5 post-MVP branches.
Acceptance criteria are specified per lane and checked independently.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class LaneContract:
    name: str
    allowed_paths: list[str]
    forbidden_paths: list[str]
    public_models: list[str]
    test_commands: list[str]
    min_tests: int
    safety_checks: list[str]
    cross_lane_deps: list[str]
    integration_risk: str  # low | medium | high


@dataclass
class LaneSnapshot:
    branch: str
    head: Optional[str]
    exists: bool
    contract: LaneContract


# ── Lane Contracts ──────────────────────────────────────────────────────────

W1_OPERATOR = LaneContract(
    name="W1 Operator",
    allowed_paths=["market_radar/integration/**", "scripts/mvpplus/integration/**", "tests/mvpplus/integration/**"],
    forbidden_paths=["main", "market_radar/whale_domain/**", "market_radar/feeds_market_ui/**", "market_radar/adapters/**", "market_radar/operations/**"],
    public_models=["IntegrationConfig", "IntegrationRunResult", "ProviderProtocol", "CuratedFeedProvider"],
    test_commands=["python -X utf8 -m pytest tests/mvpplus/integration -v"],
    min_tests=109,
    safety_checks=["no_send", "no_credentials", "no_daemon", "no_scheduler", "no_trading"],
    cross_lane_deps=["W5 BoundedShadow", "W3 CuratedFeedProvider"],
    integration_risk="medium",
)

W2_WHALE = LaneContract(
    name="W2 Whale Portfolio",
    allowed_paths=["market_radar/whale_domain/**", "tests/mvpplus/whale_domain/**"],
    forbidden_paths=["market_radar/integration/**", "market_radar/operations/**", "main"],
    public_models=["WhalePositionInput", "WhaleSnapshot", "WhaleChange", "AlertCandidate"],
    test_commands=["python -X utf8 -m pytest tests/mvpplus/whale_domain -v"],
    min_tests=127,
    safety_checks=["no_network", "no_send", "no_trading", "deterministic"],
    cross_lane_deps=["W4 HyperliquidPublicAdapter"],
    integration_risk="low",
)

W3_EVENTS = LaneContract(
    name="W3 Event Clustering",
    allowed_paths=["market_radar/intelligence_feed/**", "market_radar/workbench/**", "market_radar/market_view/**", "tests/mvpplus/feeds_market_ui/**"],
    forbidden_paths=["market_radar/whale_domain/**", "market_radar/operations/**", "main"],
    public_models=["FeedItem", "FeedDataMode", "RenderWorkbench", "make_feed_id", "CuratedApiReader"],
    test_commands=["python -X utf8 -m pytest tests/mvpplus/feeds_market_ui -v"],
    min_tests=170,
    safety_checks=["xss_escaping", "url_rejection", "no_network_imports", "csp"],
    cross_lane_deps=["W4 MarketSnapshot"],
    integration_risk="medium",
)

W4_MARKET = LaneContract(
    name="W4 Market Resilience",
    allowed_paths=["market_radar/external_adapters/**", "tests/mvpplus/adapters/**"],
    forbidden_paths=["market_radar/whale_domain/**", "market_radar/operations/**", "main"],
    public_models=["HyperliquidPublicAdapter", "CcxtPublicMarketAdapter", "HttpxTransport", "AdapterHealth", "AdapterResult"],
    test_commands=["python -m unittest discover -s tests/mvpplus/adapters -v"],
    min_tests=96,
    safety_checks=["no_credentials", "no_wallet", "no_trading", "bounded_timeout"],
    cross_lane_deps=[],
    integration_risk="low",
)

W5_OPS = LaneContract(
    name="W5 Ops Hardening",
    allowed_paths=["market_radar/operations/**", "tests/mvpplus/operations/**"],
    forbidden_paths=["market_radar/whale_domain/**", "market_radar/adapters/**", "main"],
    public_models=["FileLock", "run_bounded_shadow", "BoundedShadowConfig", "BoundedShadowResult", "StopMarker", "atomic_write_json"],
    test_commands=["python -X utf8 -m pytest tests/mvpplus/operations -v"],
    min_tests=151,
    safety_checks=["no_daemon", "no_scheduler", "no_send", "atomic_io"],
    cross_lane_deps=["W1 Integration runner"],
    integration_risk="medium",
)

ALL_LANES = [W1_OPERATOR, W2_WHALE, W3_EVENTS, W4_MARKET, W5_OPS]


@dataclass
class AcceptanceVerdict:
    lane: str
    head: Optional[str]
    evidence_exists: bool
    tests_pass: bool
    safety_pass: bool
    overall: str  # PASS | FAIL | BLOCKED | WAITING
    blocking_reason: str = ""


def verify_lane_contract(lane: LaneContract, head: Optional[str], test_count: int) -> AcceptanceVerdict:
    """Verify a single lane's contract."""
    violations = []
    if not head:
        return AcceptanceVerdict(lane.name, head, False, False, False, "WAITING", "Branch not found")

    if test_count < lane.min_tests:
        violations.append(f"Only {test_count} tests, expected ≥{lane.min_tests}")

    overall = "PASS" if not violations else "FAIL"
    return AcceptanceVerdict(lane.name, head, True, len(violations)==0, True, overall,
                             "; ".join(violations) if violations else "")
