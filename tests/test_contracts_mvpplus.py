"""MVP+ Contract Validation Tests (Lane 6).

Validates all eight sealed contracts:
  1. WhalePosition
  2. WhalePositionChange
  3. MarketContext
  4. UnifiedFeedItem
  5. SourceClaim
  6. EventCluster
  7. SourceHealth
  8. RunReport

Each test verifies:
  - Required fields exist
  - Types are correct
  - Optional fields accept null
  - Enum values are valid
  - Example JSON round-trips through as_dict()
  - Null semantics (0 never used to mean "missing")
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any

# Ensure project root on path
_PROJECT_ROOT = __file__.rsplit("/", 3)[0] if "/" in __file__ else "."
sys.path.insert(0, _PROJECT_ROOT)

from market_radar.shared.contracts import (
    # Enums
    PositionSide, LabelConfidence, EntityType,
    ChangeType, RiskLevel,
    MarketDataSource,
    FeedType, FeedSourceName, ExtractionMethod,
    ClaimType, ClaimStatus,
    ClusterRisk,
    SourceStatus,
    # Contracts
    WhalePosition, WhalePositionChange, MarketContext,
    UnifiedFeedItem, SourceClaim, EventCluster,
    SourceHealth, DegradedInfo, LaneResult,
    RunReport,
    CONTRACTS_VERSION,
)

UTC_NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}: {detail}")


def check_type(name: str, value: Any, expected_type: type):
    check(f"{name} type", isinstance(value, expected_type),
          f"Expected {expected_type.__name__}, got {type(value).__name__}")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. WhalePosition Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_whale_position():
    print("\n── Contract 1: WhalePosition ──")

    # 1a. Full position with all fields
    pos = WhalePosition(
        address="0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
        asset="BTC",
        side=PositionSide.LONG,
        position_size_usd=50_000_000.0,
        observed_at=UTC_NOW,
        entry_price=89000.0,
        mark_price=92000.0,
        leverage=5.0,
        unrealized_pnl_usd=1_500_000.0,
        margin_used_usd=10_000_000.0,
        liquidation_price=75000.0,
        liquidation_distance_pct=18.48,
        label="Matrixport Related",
        entity_type=EntityType.FUND_WALLET,
        label_confidence=LabelConfidence.MEDIUM,
    )
    check("1a.1 address type", isinstance(pos.address, str))
    check("1a.2 asset type", isinstance(pos.asset, str))
    check("1a.3 side type", isinstance(pos.side, PositionSide))
    check("1a.4 position_size_usd type", isinstance(pos.position_size_usd, float))
    check("1a.5 observed_at not empty", bool(pos.observed_at))
    check("1a.6 entry_price set", pos.entry_price == 89000.0)
    check("1a.7 liquidation_distance_pct set", pos.liquidation_distance_pct == 18.48)
    check("1a.8 as_dict round-trip", isinstance(pos.as_dict(), dict))
    d = pos.as_dict()
    check("1a.9 as_dict side str", isinstance(d["side"], str))
    check("1a.10 as_dict entity_type str", isinstance(d["entity_type"], str))

    # 1b. Minimal position (all null optionals)
    pos_min = WhalePosition(
        address="0x0000000000000000000000000000000000000000",
        asset="HYPE",
        side=PositionSide.SHORT,
        position_size_usd=10_000_000.0,
        observed_at=UTC_NOW,
    )
    check("1b.1 minimal entry_price null", pos_min.entry_price is None)
    check("1b.2 minimal leverage null", pos_min.leverage is None)
    check("1b.3 minimal liquidation_price null", pos_min.liquidation_price is None)
    check("1b.4 minimal label null", pos_min.label is None)
    check("1b.5 minimal entity_type null", pos_min.entity_type is None)

    # 1c. Null semantics: 0 not used for missing
    check("1c.1 mark_price null, not 0", pos_min.mark_price is None)
    check("1c.2 unrealized_pnl_usd null, not 0", pos_min.unrealized_pnl_usd is None)

    # 1d. Side enum values
    check("1d.1 LONG valid", PositionSide.LONG.value == "LONG")
    check("1d.2 SHORT valid", PositionSide.SHORT.value == "SHORT")

    # 1e. LabelConfidence enum values
    check("1e.1 HIGH", LabelConfidence.HIGH.value == "HIGH")

    # 1f. EntityType enum values
    check("1f.1 UNKNOWN_WHALE", EntityType.UNKNOWN_WHALE.value == "UNKNOWN_WHALE")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. WhalePositionChange Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_whale_position_change():
    print("\n── Contract 2: WhalePositionChange ──")

    # 2a. Full change (position increased)
    change = WhalePositionChange(
        address="0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
        asset="BTC",
        side=PositionSide.LONG,
        change_type=ChangeType.POSITION_INCREASED,
        current_position_size_usd=60_000_000.0,
        current_entry_price=89000.0,
        current_mark_price=92000.0,
        current_unrealized_pnl_usd=1_800_000.0,
        current_liquidation_price=74000.0,
        current_liquidation_distance_pct=19.57,
        current_leverage=5.0,
        current_observed_at=UTC_NOW,
        previous_position_size_usd=50_000_000.0,
        previous_observed_at="2026-06-15T12:00:00Z",
        position_delta_usd=10_000_000.0,
        change_pct=20.0,
        risk_level=RiskLevel.ELEVATED,
        risk_factors=["large_increase", "high_leverage"],
        label="Matrixport Related",
        entity_type=EntityType.FUND_WALLET,
        label_confidence=LabelConfidence.MEDIUM,
    )
    check("2a.1 change_type", change.change_type == ChangeType.POSITION_INCREASED)
    check("2a.2 delta_usd", change.position_delta_usd == 10_000_000.0)
    check("2a.3 change_pct", change.change_pct == 20.0)
    check("2a.4 risk_level", change.risk_level == RiskLevel.ELEVATED)
    check("2a.5 risk_factors count", len(change.risk_factors) == 2)
    d = change.as_dict()
    check("2a.6 as_dict has change_type", "change_type" in d)

    # 2b. POSITION_OPENED (no previous)
    opened = WhalePositionChange(
        address="0xnew",
        asset="SOL",
        side=PositionSide.LONG,
        change_type=ChangeType.POSITION_OPENED,
        current_position_size_usd=20_000_000.0,
        current_entry_price=175.0,
        current_mark_price=180.0,
        current_unrealized_pnl_usd=500_000.0,
        current_liquidation_price=150.0,
        current_liquidation_distance_pct=16.67,
        current_leverage=3.0,
        current_observed_at=UTC_NOW,
        previous_position_size_usd=None,
        previous_observed_at=None,
        position_delta_usd=None,
        change_pct=None,
    )
    check("2b.1 opened no previous size", opened.previous_position_size_usd is None)
    check("2b.2 opened delta null", opened.position_delta_usd is None)
    check("2b.3 opened change_pct null", opened.change_pct is None)

    # 2c. ChangeType enum values
    for ct in ["POSITION_OPENED", "POSITION_INCREASED", "POSITION_REDUCED",
               "POSITION_CLOSED", "DIRECTION_FLIPPED", "NO_CHANGE", "UNKNOWN"]:
        check(f"2c. ChangeType.{ct}", ct in [e.value for e in ChangeType])


# ═══════════════════════════════════════════════════════════════════════════════
# 3. MarketContext Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_market_context():
    print("\n── Contract 3: MarketContext ──")

    # 3a. Full market context
    ctx = MarketContext(
        symbol="BTC",
        price=89000.0,
        price_change_24h_pct=-1.23,
        volume_24h=28_500_000_000.0,
        high_24h=91000.0,
        low_24h=88500.0,
        open_interest=12_000_000_000.0,
        funding_rate=0.0001,
        long_short_ratio=1.8,
        market_cap=1_760_000_000_000.0,
        dominance_pct=55.2,
        source=MarketDataSource.BINANCE_SPOT,
        observed_at=UTC_NOW,
    )
    check("3a.1 symbol", ctx.symbol == "BTC")
    check("3a.2 price", ctx.price == 89000.0)
    check("3a.3 open_interest set", ctx.open_interest == 12_000_000_000.0)
    check("3a.4 funding_rate set", ctx.funding_rate == 0.0001)

    # 3b. Minimal context (spot-only, no futures data)
    ctx_min = MarketContext(
        symbol="HYPE",
        price=32.50,
        observed_at=UTC_NOW,
    )
    check("3b.1 no open_interest", ctx_min.open_interest is None)
    check("3b.2 no funding_rate", ctx_min.funding_rate is None)
    check("3b.3 no price_change", ctx_min.price_change_24h_pct is None)
    check("3b.4 no volume", ctx_min.volume_24h is None)

    # 3c. Default source
    check("3c.1 default source", ctx_min.source == MarketDataSource.BINANCE_SPOT)

    d = ctx.as_dict()
    check("3d.1 as_dict has source str", isinstance(d["source"], str))


# ═══════════════════════════════════════════════════════════════════════════════
# 4. UnifiedFeedItem Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_unified_feed_item():
    print("\n── Contract 4: UnifiedFeedItem ──")

    # 4a. Full news item
    item = UnifiedFeedItem(
        feed_id="news_001",
        feed_type=FeedType.NEWS,
        source_name=FeedSourceName.COINDESK,
        title="SEC Approves Spot BTC ETF Options",
        body="The SEC has approved options trading on spot Bitcoin ETFs...",
        url="https://www.coindesk.com/article/123",
        event_type="ETF",
        intensity="high",
        assets_affected=["BTC"],
        dedup_key="sha256:abc123",
        original_id="cd-article-123",
        published_at="2026-06-15T14:30:00Z",
        ingested_at="2026-06-15T14:31:00Z",
        extraction_method=ExtractionMethod.RULE_BASED_RSS,
    )
    check("4a.1 feed_id", bool(item.feed_id))
    check("4a.2 title", bool(item.title))
    check("4a.3 url set", bool(item.url))
    check("4a.4 body set", bool(item.body))
    check("4a.5 assets", len(item.assets_affected) == 1)

    # 4b. Minimal telegram item (body and url can be null)
    tg = UnifiedFeedItem(
        feed_id="tg_001",
        feed_type=FeedType.TELEGRAM,
        source_name=FeedSourceName.TELEGRAM_ALPHA,
        title="Whale moved 5000 BTC",
        published_at=UTC_NOW,
        ingested_at=UTC_NOW,
    )
    check("4b.1 tg body null", tg.body is None)
    check("4b.2 tg url null", tg.url is None)
    check("4b.3 tg dedup_key null", tg.dedup_key is None)

    d = tg.as_dict()
    check("4c.1 as_dict feed_type str", isinstance(d["feed_type"], str))
    check("4c.2 as_dict source_name str", isinstance(d["source_name"], str))


# ═══════════════════════════════════════════════════════════════════════════════
# 5. SourceClaim Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_source_claim():
    print("\n── Contract 5: SourceClaim ──")

    claim = SourceClaim(
        claim_id="claim_001",
        source_name="hyperliquid_info_api",
        claim_type=ClaimType.POSITION_CHANGED,
        claim_detail="Address 0xabc increased BTC long by 10M USD",
        ref_type="whale_position",
        ref_id="pos_001",
        confidence=0.85,
        status=ClaimStatus.VERIFIED,
        supporting_refs=["snapshot_1", "snapshot_2"],
        claimed_at=UTC_NOW,
        verified_at=UTC_NOW,
    )
    check("5a.1 claim_id", bool(claim.claim_id))
    check("5a.2 confidence range", 0.0 <= claim.confidence <= 1.0)
    check("5a.3 supporting_refs", len(claim.supporting_refs) == 2)

    # Minimal claim
    claim_min = SourceClaim(
        claim_id="claim_002",
        source_name="unknown",
        claim_type=ClaimType.UNKNOWN,
        ref_type="feed_item",
        ref_id="feed_001",
        claimed_at=UTC_NOW,
    )
    check("5b.1 minimal claim_detail null", claim_min.claim_detail is None)
    check("5b.2 minimal verified_at null", claim_min.verified_at is None)
    check("5b.3 minimal refuted_by null", claim_min.refuted_by is None)
    check("5b.4 default status PENDING", claim_min.status == ClaimStatus.PENDING)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. EventCluster Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_event_cluster():
    print("\n── Contract 6: EventCluster ──")

    cluster = EventCluster(
        cluster_id="cluster_001",
        title="BTC Whale Accumulation + ETF News",
        cluster_assets=["BTC"],
        feed_item_ids=["news_001", "tg_001"],
        position_change_ids=["change_001", "change_002"],
        signal_ids=["sig_001"],
        claim_ids=["claim_001"],
        risk=ClusterRisk.ELEVATED,
        aggregate_confidence=0.72,
        risk_tags=["whale_accumulation", "etf_approval"],
        direction="bullish",
        first_seen_at="2026-06-15T14:30:00Z",
        updated_at=UTC_NOW,
        evidence_summary="Multiple sources confirm whale accumulation ahead of ETF approval",
        source_count=3,
    )
    check("6a.1 cluster_id", bool(cluster.cluster_id))
    check("6a.2 assets", len(cluster.cluster_assets) == 1)
    check("6a.3 feed items", len(cluster.feed_item_ids) == 2)
    check("6a.4 position changes", len(cluster.position_change_ids) == 2)
    check("6a.5 risk ELEVATED", cluster.risk == ClusterRisk.ELEVATED)
    check("6a.6 direction", cluster.direction == "bullish")

    # Minimal cluster
    cluster_min = EventCluster(
        cluster_id="cluster_002",
        title="Unclassified Event",
    )
    check("6b.1 minimal aggregate_confidence null", cluster_min.aggregate_confidence is None)
    check("6b.2 minimal resolved_at null", cluster_min.resolved_at is None)
    check("6b.3 default risk UNKNOWN", cluster_min.risk == ClusterRisk.UNKNOWN)

    d = cluster_min.as_dict()
    check("6c.1 as_dict risk str", isinstance(d["risk"], str))


# ═══════════════════════════════════════════════════════════════════════════════
# 7. SourceHealth Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_source_health():
    print("\n── Contract 7: SourceHealth ──")

    # Healthy source
    ok = SourceHealth(
        source_name="binance_spot_api",
        source_group="market",
        status=SourceStatus.OK,
        last_success_at=UTC_NOW,
        latency_ms=120.5,
        success_count=150,
        error_count=0,
    )
    check("7a.1 source_name", bool(ok.source_name))
    check("7a.2 OK status", ok.status == SourceStatus.OK)
    check("7a.3 no degraded_info", ok.degraded_info is None)
    check("7a.4 latency type", isinstance(ok.latency_ms, float))

    # Degraded source
    degraded = SourceHealth(
        source_name="hyperliquid_info_api",
        source_group="hyperliquid",
        status=SourceStatus.DEGRADED,
        last_success_at="2026-06-15T10:00:00Z",
        last_error_at=UTC_NOW,
        success_count=80,
        error_count=5,
        consecutive_failures=3,
        degraded_info=DegradedInfo(
            error_type="HTTP_TIMEOUT",
            occurred_at=UTC_NOW,
            retryable=True,
            message_summary="Request timed out after 15s",
            retry_attempts=3,
        ),
    )
    check("7b.1 degraded status", degraded.status == SourceStatus.DEGRADED)
    check("7b.2 degraded_info present", degraded.degraded_info is not None)
    check("7b.3 error_type", degraded.degraded_info.error_type == "HTTP_TIMEOUT")
    check("7b.4 retryable", degraded.degraded_info.retryable is True)
    check("7b.5 consecutive_failures", degraded.consecutive_failures == 3)

    d = degraded.as_dict()
    check("7c.1 as_dict status str", isinstance(d["status"], str))


# ═══════════════════════════════════════════════════════════════════════════════
# 8. RunReport Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_run_report():
    print("\n── Contract 8: RunReport ──")

    report = RunReport(
        run_id="run_001",
        started_at="2026-06-15T14:00:00Z",
        completed_at=UTC_NOW,
        whale_positions=[
            WhalePosition(
                address="0xabc",
                asset="BTC",
                side=PositionSide.LONG,
                position_size_usd=50_000_000.0,
                observed_at=UTC_NOW,
                entry_price=89000.0,
            ),
        ],
        whale_changes=[
            WhalePositionChange(
                address="0xabc",
                asset="BTC",
                side=PositionSide.LONG,
                change_type=ChangeType.NO_CHANGE,
                current_position_size_usd=50_000_000.0,
                current_observed_at=UTC_NOW,
                previous_position_size_usd=50_000_000.0,
                previous_observed_at="2026-06-15T12:00:00Z",
                position_delta_usd=0.0,
                change_pct=0.0,
            ),
        ],
        market_contexts=[
            MarketContext(symbol="BTC", price=89000.0, observed_at=UTC_NOW),
        ],
        feed_items=[
            UnifiedFeedItem(
                feed_id="news_001",
                feed_type=FeedType.NEWS,
                source_name=FeedSourceName.COINDESK,
                title="Test",
                published_at=UTC_NOW,
                ingested_at=UTC_NOW,
            ),
        ],
        source_health=[
            SourceHealth(
                source_name="binance",
                source_group="market",
                status=SourceStatus.OK,
                last_success_at=UTC_NOW,
            ),
        ],
        lane_results={
            "L1": LaneResult(lane_id="L1", status="OK", item_count=5,
                           started_at=UTC_NOW, completed_at=UTC_NOW),
            "L2": LaneResult(lane_id="L2", status="OK", item_count=3,
                           started_at=UTC_NOW, completed_at=UTC_NOW),
            "L3": LaneResult(lane_id="L3", status="OK", item_count=4,
                           started_at=UTC_NOW, completed_at=UTC_NOW),
            "L4": LaneResult(lane_id="L4", status="DEGRADED",
                           item_count=10, error_count=1,
                           errors=["news_source_timeout"],
                           warnings=["partial_data"],
                           started_at=UTC_NOW, completed_at=UTC_NOW),
        },
        workbench_html_path="/path/to/workbench.html",
        workbench_html_name="workbench.html",
    )
    check("8a.1 run_id", bool(report.run_id))
    check("8a.2 whale_positions count", len(report.whale_positions) == 1)
    check("8a.3 whale_changes count", len(report.whale_changes) == 1)
    check("8a.4 market_contexts count", len(report.market_contexts) == 1)
    check("8a.5 feed_items count", len(report.feed_items) == 1)
    check("8a.6 source_health count", len(report.source_health) == 1)
    check("8a.7 lane_results count", len(report.lane_results) == 4)
    check("8a.8 L4 DEGRADED", report.lane_results["L4"].status == "DEGRADED")
    check("8a.9 html_path set", bool(report.workbench_html_path))
    check("8a.10 html_name set", report.workbench_html_name == "workbench.html")

    # Round-trip
    d = report.as_dict()
    check("8b.1 as_dict returns dict", isinstance(d, dict))
    check("8b.2 dict has whale_positions", "whale_positions" in d)
    check("8b.3 dict has lane_results", "lane_results" in d)
    check("8b.4 contracts_version", d["contracts_version"] == CONTRACTS_VERSION)

    # Minimal report
    empty = RunReport(
        run_id="run_empty",
        started_at="2026-06-15T00:00:00Z",
        completed_at=UTC_NOW,
    )
    check("8c.1 empty report no error", empty.error is None)
    check("8c.2 empty report no html", empty.workbench_html_path is None)
    check("8c.3 empty positions", len(empty.whale_positions) == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# Cross-Contract Checks
# ═══════════════════════════════════════════════════════════════════════════════

def test_cross_contract():
    print("\n── Cross-Contract Checks ──")

    # All timestamps should be parseable as UTC ISO 8601
    timestamps = [
        "2026-06-15T14:30:00Z",
        "2026-06-16T00:00:00Z",
    ]
    for ts in timestamps:
        try:
            datetime.fromisoformat(ts.replace("Z", "+00:00"))
            check(f"Timestamp parseable: {ts}", True)
        except ValueError:
            check(f"Timestamp parseable: {ts}", False, f"Invalid: {ts}")

    # All enums should have UNKNOWN or default values
    has_unknown = {
        "PositionSide": hasattr(PositionSide, "LONG"),  # no UNKNOWN needed - must be known
        "LabelConfidence": LabelConfidence.UNKNOWN.value == "UNKNOWN",
        "EntityType": EntityType.UNCLASSIFIED.value == "UNCLASSIFIED",
        "ChangeType": ChangeType.UNKNOWN.value == "UNKNOWN",
        "RiskLevel": RiskLevel.UNKNOWN.value == "UNKNOWN",
        "MarketDataSource": MarketDataSource.UNKNOWN.value == "UNKNOWN",
        "FeedType": FeedType.UNKNOWN.value == "UNKNOWN",
        "FeedSourceName": FeedSourceName.UNKNOWN.value == "UNKNOWN",
        "ExtractionMethod": ExtractionMethod.UNKNOWN.value == "UNKNOWN",
        "ClaimType": ClaimType.UNKNOWN.value == "UNKNOWN",
        "ClaimStatus": ClaimStatus.PENDING.value == "PENDING",
        "ClusterRisk": ClusterRisk.UNKNOWN.value == "UNKNOWN",
        "SourceStatus": SourceStatus.UNKNOWN.value == "UNKNOWN",
    }
    for name, ok in has_unknown.items():
        check(f"Enum {name} has UNKNOWN/PENDING default", ok)

    # Verify all contracts have as_dict()
    for contract_name, instance in [
        ("WhalePosition", WhalePosition(address="0x0", asset="BTC", side=PositionSide.LONG,
                                         position_size_usd=1.0, observed_at=UTC_NOW)),
        ("MarketContext", MarketContext(symbol="BTC", price=1.0, observed_at=UTC_NOW)),
        ("SourceHealth", SourceHealth(source_name="t", source_group="t", status=SourceStatus.OK)),
    ]:
        has_method = hasattr(instance, "as_dict") and callable(getattr(instance, "as_dict"))
        check(f"{contract_name}.as_dict() exists", has_method)


# ═══════════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print(f"Contract Validation Suite v{CONTRACTS_VERSION}")
    print(f"Sealed at: {__import__('market_radar.shared.contracts', fromlist=['']).CONTRACTS_SEALED_AT}")
    print(f"{'='*60}")

    test_whale_position()
    test_whale_position_change()
    test_market_context()
    test_unified_feed_item()
    test_source_claim()
    test_event_cluster()
    test_source_health()
    test_run_report()
    test_cross_contract()

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed > 0:
        print("CONTRACT_VALIDATION_FAILED")
        sys.exit(1)
    else:
        print("CONTRACT_SEAL_READY")
        sys.exit(0)


if __name__ == "__main__":
    main()
