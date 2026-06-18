"""Post-MVP Multi-Lane Acceptance Pack — updated path contracts for R02."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


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
    integration_risk: str


@dataclass
class LaneSnapshot:
    branch: str
    head: Optional[str]
    exists: bool
    evidence_files: list[str]
    contract: LaneContract


W1_OPERATOR = LaneContract(
    name="W1 Operator",
    allowed_paths=["market_radar/integration/**", "scripts/post_mvp/operator/**",
                   "tests/post_mvp/operator/**", "docs/operator/**", "artifacts/evidence/w1_*.json"],
    forbidden_paths=["market_radar/whale_domain/**", "market_radar/feeds_market_ui/**",
                     "market_radar/external_adapters/**", "market_radar/operations/**"],
    public_models=["IntegrationConfig", "IntegrationRunResult", "CuratedFeedProvider"],
    test_commands=["python -X utf8 -m pytest tests/mvpplus/integration -v"],
    min_tests=109, safety_checks=["no_send", "no_credentials", "no_daemon", "no_trading"],
    cross_lane_deps=["W5 BoundedShadow", "W3 CuratedFeedProvider"], integration_risk="medium")

W2_WHALE = LaneContract(
    name="W2 Whale Portfolio",
    allowed_paths=["market_radar/whale_domain/**", "tests/mvpplus/whale_domain/**",
                   "tests/post_mvp/whale_intelligence/**", "docs/whale_intelligence/**",
                   "artifacts/evidence/w2_*.json"],
    forbidden_paths=["market_radar/integration/**", "market_radar/operations/**"],
    public_models=["WhalePositionInput", "WhaleSnapshot", "WhaleChange", "AlertCandidate"],
    test_commands=["python -X utf8 -m pytest tests/mvpplus/whale_domain -v"],
    min_tests=127, safety_checks=["no_network", "no_send", "no_trading"],
    cross_lane_deps=["W4 HyperliquidPublicAdapter"], integration_risk="low")

W3_EVENTS = LaneContract(
    name="W3 Event Clustering",
    allowed_paths=["market_radar/intelligence_feed/event_intelligence/**",
                   "tests/post_mvp/event_intelligence/**", "docs/event_intelligence/**",
                   "artifacts/evidence/w3_*.json"],
    forbidden_paths=["market_radar/whale_domain/**", "market_radar/operations/**"],
    public_models=["FeedItem", "FeedDataMode", "CuratedApiReader"],
    test_commands=["python -X utf8 -m pytest tests/mvpplus/feeds_market_ui -v"],
    min_tests=170, safety_checks=["xss_escaping", "url_rejection", "no_network_imports"],
    cross_lane_deps=["W4 MarketSnapshot"], integration_risk="medium")

W4_MARKET = LaneContract(
    name="W4 Market Resilience",
    allowed_paths=["market_radar/external_adapters/**", "tests/mvpplus/adapters/**",
                   "tests/post_mvp/market_resilience/**", "docs/adapters/**",
                   "artifacts/evidence/w4_*.json"],
    forbidden_paths=["market_radar/whale_domain/**", "market_radar/operations/**"],
    public_models=["HyperliquidPublicAdapter", "CcxtPublicMarketAdapter", "AdapterHealth"],
    test_commands=["python -m unittest discover -s tests/mvpplus/adapters -v"],
    min_tests=96, safety_checks=["no_credentials", "no_wallet", "no_trading", "bounded_timeout"],
    cross_lane_deps=[], integration_risk="low")

W5_OPS = LaneContract(
    name="W5 Ops Hardening",
    allowed_paths=["market_radar/operations/**", "tests/post_mvp/operations/**",
                   "tests/mvpplus/operations/**", "docs/operations/**",
                   "artifacts/evidence/w5_*.json"],
    forbidden_paths=["market_radar/whale_domain/**", "market_radar/external_adapters/**"],
    public_models=["FileLock", "run_bounded_shadow", "StopMarker", "atomic_write_json"],
    test_commands=["python -X utf8 -m pytest tests/mvpplus/operations -v"],
    min_tests=151, safety_checks=["no_daemon", "no_scheduler", "no_send", "atomic_io"],
    cross_lane_deps=["W1 Integration runner"], integration_risk="medium")

ALL_LANES = [W1_OPERATOR, W2_WHALE, W3_EVENTS, W4_MARKET, W5_OPS]


@dataclass
class AcceptanceVerdict:
    lane: str; head: Optional[str]; evidence_exists: bool
    tests_pass: bool; safety_pass: bool
    overall: str = "WAITING"; blocking_reason: str = ""


def verify_lane_contract(contract: LaneContract, head: Optional[str],
                         test_count: int, evidence_ok: bool) -> AcceptanceVerdict:
    if not head:
        return AcceptanceVerdict(contract.name, head, False, False, False,
                                 "WAITING", "Branch not found")
    violations = []
    if test_count < contract.min_tests:
        violations.append(f"Only {test_count} tests, needed {contract.min_tests}")
    if not evidence_ok:
        violations.append("Evidence binding failed")
    overall = "PASS" if not violations else "FAIL"
    return AcceptanceVerdict(contract.name, head, evidence_ok,
                             test_count >= contract.min_tests, True,
                             overall, "; ".join(violations) if violations else "")
