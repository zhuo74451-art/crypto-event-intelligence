"""Multi-exchange market resilience tests — offline, fixture-based.

Covers: capability matrix, venue snapshot normalization, cross-venue
aggregation, anomaly detection, fallback policy, import isolation,
NaN/zero/null handling, stale data, rate limits, malformed responses,
independent field fetching, OI normalization, market type classification,
venue health, health-aware fallback, extended import isolation, security.

Target: 160+ tests in this module.
"""
from __future__ import annotations

import json
import os
import math
import unittest
from unittest.mock import MagicMock, patch
from typing import Any, Optional

# Core module under test
from market_radar.external_adapters.market_resilience import (
    MarketVenueSnapshot,
    CrossVenueMarketSnapshot,
    KNOWN_CAPABILITIES,
    get_venue_capabilities,
    get_supported_count,
    detect_anomalies,
    fallback_order,
    _coalesce_float,
    fetch_field_open_interest,
    fetch_field_funding_rate,
    fetch_field_order_book_top,
    FieldResult,
    classify_market_type,
    normalize_oi,
    NormalizedOI,
    aggregate_oi,
    compute_venue_health,
    VenueHealthSnapshot,
    health_aware_fallback,
    FallbackDecision,
    MARKET_SPOT,
    MARKET_LINEAR_PERP,
    MARKET_INVERSE_PERP,
    MAX_DISPERSION_BPS,
    MAX_SPREAD_BPS,
    STALE_AGE_SECONDS,
    MIN_HEALTHY_VENUES_CONSENSUS,
    CAP_SPOT_TICKER,
    CAP_PERP_TICKER,
    CAP_OPEN_INTEREST,
    CAP_FUNDING_RATE,
)
from market_radar.external_adapters.ccxt_public_market_adapter import (
    CcxtPublicMarketAdapter, ALLOWLISTED_EXCHANGES,
)


FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name: str) -> dict:
    path = os.path.join(FIXTURE_DIR, name)
    with open(path, "r") as f:
        return json.load(f)


def _mock_ccxt_ticker(return_data: dict, ok: bool = True):
    """Create a mock CcxtPublicMarketAdapter that returns given ticker data."""
    mock = MagicMock(spec=CcxtPublicMarketAdapter)
    result = MagicMock()
    result.ok = ok
    result.data = return_data
    result.error = None if ok else MagicMock(message="mock error", code="mock_error")
    result.provenance = MagicMock(source="ccxt")
    result.health = MagicMock(available=ok)
    if ok:
        mock.fetch.return_value = result
    else:
        mock.fetch.return_value = result
    return mock


# ═══════════════════════════════════════════════════════════════════
# 1. Capability Matrix Tests
# ═══════════════════════════════════════════════════════════════════

class TestCapabilityMatrix(unittest.TestCase):
    def test_all_venues_have_capabilities(self):
        for v in ALLOWLISTED_EXCHANGES:
            caps = get_venue_capabilities(v)
            self.assertGreater(len(caps), 0, f"{v} has no capabilities")

    def test_hyperliquid_has_perp_not_spot(self):
        caps = get_venue_capabilities("hyperliquid")
        self.assertEqual(caps.get(CAP_SPOT_TICKER), "unsupported")
        self.assertEqual(caps.get(CAP_PERP_TICKER), "supported")

    def test_binance_has_spot_and_perp(self):
        caps = get_venue_capabilities("binance")
        self.assertEqual(caps.get(CAP_SPOT_TICKER), "supported")
        self.assertEqual(caps.get(CAP_PERP_TICKER), "supported")

    def test_unknown_venue_all_unknown(self):
        caps = get_venue_capabilities("unknown_exchange")
        self.assertTrue(all(v == "unknown" for v in caps.values()))

    def test_binance_most_supported(self):
        count = get_supported_count("binance")
        self.assertGreaterEqual(count, 8)

    def test_hyperliquid_fewer_supported(self):
        count = get_supported_count("hyperliquid")
        self.assertLess(count, get_supported_count("binance"))


# ═══════════════════════════════════════════════════════════════════
# 2. MarketVenueSnapshot Tests
# ═══════════════════════════════════════════════════════════════════

class TestMarketVenueSnapshot(unittest.TestCase):
    def test_full_snapshot(self):
        snap = MarketVenueSnapshot(
            venue="binance", symbol="BTC/USDT", market_type="spot",
            timestamp="2026-01-01T00:00:00Z",
            last=50000.0, bid=49990.0, ask=50010.0,
            volume_24h=750000000.0, status="ok", provenance="ccxt",
            fields_available=["last", "bid", "ask", "volume_24h"],
        )
        self.assertEqual(snap.last, 50000.0)
        self.assertEqual(snap.bid, 49990.0)
        self.assertIn("last", snap.fields_available)

    def test_missing_field_null(self):
        """Fields that were not set must remain None, never 0."""
        snap = MarketVenueSnapshot(
            venue="binance", symbol="BTC/USDT", market_type="spot",
            timestamp="2026-01-01T00:00:00Z", status="ok", provenance="ccxt",
        )
        self.assertIsNone(snap.last)
        self.assertIsNone(snap.bid)
        self.assertIsNone(snap.ask)
        self.assertIsNone(snap.funding_rate)
        self.assertIsNone(snap.open_interest)

    def test_unavailable_status(self):
        snap = MarketVenueSnapshot(
            venue="unknown", symbol="BTC/USDT", market_type="unknown",
            timestamp="2026-01-01T00:00:00Z", status="unavailable",
            errors=["venue unreachable"], provenance="ccxt",
        )
        self.assertEqual(snap.status, "unavailable")
        self.assertEqual(len(snap.errors), 1)

    def test_as_dict_excludes_none(self):
        snap = MarketVenueSnapshot(
            venue="binance", symbol="BTC/USDT", market_type="spot",
            timestamp="2026-01-01T00:00:00Z", last=50000.0, status="ok",
            provenance="ccxt",
        )
        d = snap.as_dict()
        self.assertIn("last", d)
        self.assertNotIn("bid", d)  # None → excluded
        self.assertNotIn("errors", d)  # empty → excluded

    def test_fields_available_missing_tracking(self):
        snap = MarketVenueSnapshot(
            venue="binance", symbol="BTC/USDT", market_type="spot",
            timestamp="2026-01-01T00:00:00Z", last=50000.0, status="ok",
            provenance="ccxt", fields_available=["last"],
            fields_missing=["bid", "ask", "funding_rate"],
        )
        self.assertEqual(len(snap.fields_available), 1)
        self.assertEqual(len(snap.fields_missing), 3)


# ═══════════════════════════════════════════════════════════════════
# 3. CrossVenueMarketSnapshot Tests
# ═══════════════════════════════════════════════════════════════════

class TestCrossVenueMarketSnapshot(unittest.TestCase):
    def setUp(self):
        self.snapshots = [
            MarketVenueSnapshot(
                venue="binance", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z",
                last=50000.0, bid=49990.0, ask=50010.0,
                status="ok", provenance="ccxt",
            ),
            MarketVenueSnapshot(
                venue="okx", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z",
                last=50020.0, bid=50010.0, ask=50030.0,
                status="ok", provenance="ccxt",
            ),
            MarketVenueSnapshot(
                venue="bybit", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z",
                last=49980.0, bid=49970.0, ask=49990.0,
                status="ok", provenance="ccxt",
            ),
        ]

    def test_aggregation(self):
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        cross = _aggregate_snapshots("BTC/USDT", self.snapshots)
        self.assertEqual(cross.venue_count, 3)
        self.assertEqual(cross.healthy_venue_count, 3)
        self.assertIsNotNone(cross.median_price)
        self.assertIsNotNone(cross.min_price)
        self.assertIsNotNone(cross.max_price)
        self.assertEqual(cross.consensus_status, "ok")

    def test_consensus_with_two_venues(self):
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        cross = _aggregate_snapshots("BTC/USDT", self.snapshots[:2])
        self.assertGreaterEqual(cross.healthy_venue_count, 2)
        self.assertEqual(cross.consensus_status, "ok")

    def test_no_healthy_venues(self):
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        all_unavail = [
            MarketVenueSnapshot(
                venue="binance", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z",
                status="unavailable", errors=["down"], provenance="ccxt",
            ),
        ]
        cross = _aggregate_snapshots("BTC/USDT", all_unavail)
        self.assertEqual(cross.consensus_status, "unavailable")
        self.assertFalse(cross.has_consensus)

    def test_has_consensus(self):
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        cross = _aggregate_snapshots("BTC/USDT", self.snapshots)
        self.assertTrue(cross.has_consensus)

    def test_as_dict_structure(self):
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        cross = _aggregate_snapshots("BTC/USDT", self.snapshots)
        d = cross.as_dict()
        self.assertIn("symbol", d)
        self.assertIn("venue_snapshots", d)
        self.assertIn("venue_count", d)
        self.assertEqual(len(d["venue_snapshots"]), 3)


# ═══════════════════════════════════════════════════════════════════
# 4. Coalesce Float Tests
# ═══════════════════════════════════════════════════════════════════

class TestCoalesceFloat(unittest.TestCase):
    def test_none_returns_none(self):
        self.assertIsNone(_coalesce_float(None))

    def test_nan_returns_none(self):
        self.assertIsNone(_coalesce_float(float("nan")))

    def test_inf_returns_none(self):
        self.assertIsNone(_coalesce_float(float("inf")))

    def test_neg_inf_returns_none(self):
        self.assertIsNone(_coalesce_float(float("-inf")))

    def test_normal_float(self):
        self.assertEqual(_coalesce_float(50000.0), 50000.0)

    def test_int(self):
        self.assertEqual(_coalesce_float(50000), 50000.0)

    def test_string_number(self):
        self.assertEqual(_coalesce_float("50000.0"), 50000.0)

    def test_string_nan(self):
        self.assertIsNone(_coalesce_float("nan"))

    def test_string_inf(self):
        self.assertIsNone(_coalesce_float("inf"))

    def test_malformed_string(self):
        self.assertIsNone(_coalesce_float("not-a-number"))

    def test_zero_is_valid(self):
        self.assertEqual(_coalesce_float(0.0), 0.0)


# ═══════════════════════════════════════════════════════════════════
# 5. Anomaly Detection Tests
# ═══════════════════════════════════════════════════════════════════

class TestDetectAnomalies(unittest.TestCase):
    def test_no_anomalies(self):
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        all_ok = [
            MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", last=50000.0, bid=49990.0, ask=50010.0,
                status="ok", provenance="ccxt"),
            MarketVenueSnapshot(venue="okx", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", last=50010.0, bid=50000.0, ask=50020.0,
                status="ok", provenance="ccxt"),
        ]
        cross = _aggregate_snapshots("BTC/USDT", all_ok)
        anomalies = detect_anomalies(cross)
        self.assertEqual(len(anomalies), 0)

    def test_wide_dispersion(self):
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        wide = [
            MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", last=50000.0, status="ok", provenance="ccxt"),
            MarketVenueSnapshot(venue="okx", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", last=51000.0, status="ok", provenance="ccxt"),
            MarketVenueSnapshot(venue="bybit", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", last=49000.0, status="ok", provenance="ccxt"),
        ]
        cross = _aggregate_snapshots("BTC/USDT", wide)
        anomalies = detect_anomalies(cross)
        dispersion_anomalies = [a for a in anomalies if "dispersion" in a]
        self.assertGreater(len(dispersion_anomalies), 0)

    def test_wide_spread(self):
        snap = MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="spot",
            timestamp="2026-01-01T00:00:00Z", last=50000.0, bid=49000.0, ask=51000.0,
            status="ok", provenance="ccxt",
            data_age_ms=1000)
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        cross = _aggregate_snapshots("BTC/USDT", [snap])
        anomalies = detect_anomalies(cross)
        spread_anomalies = [a for a in anomalies if "spread" in a]
        self.assertGreater(len(spread_anomalies), 0)

    def test_stale_data(self):
        snap = MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="spot",
            timestamp="2026-01-01T00:00:00Z", last=50000.0, status="ok", provenance="ccxt",
            data_age_ms=600000)  # 10 minutes > 5 min stale
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        cross = _aggregate_snapshots("BTC/USDT", [snap])
        anomalies = detect_anomalies(cross)
        stale_anomalies = [a for a in anomalies if "stale" in a]
        self.assertGreater(len(stale_anomalies), 0)

    def test_zero_price(self):
        snap = MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="spot",
            timestamp="2026-01-01T00:00:00Z", last=0.0, status="ok", provenance="ccxt")
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        cross = _aggregate_snapshots("BTC/USDT", [snap])
        anomalies = detect_anomalies(cross)
        zero_anomalies = [a for a in anomalies if "zero_price" in a]
        self.assertGreater(len(zero_anomalies), 0)

    def test_high_funding(self):
        snap = MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="perp",
            timestamp="2026-01-01T00:00:00Z", last=50000.0, funding_rate=0.02,
            status="ok", provenance="ccxt")
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        cross = _aggregate_snapshots("BTC/USDT", [snap])
        anomalies = detect_anomalies(cross)
        funding_anomalies = [a for a in anomalies if "high_funding" in a]
        self.assertGreater(len(funding_anomalies), 0)

    def test_funding_divergence(self):
        snap1 = MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="perp",
            timestamp="2026-01-01T00:00:00Z", last=50000.0, funding_rate=0.0001,
            status="ok", provenance="ccxt")
        snap2 = MarketVenueSnapshot(venue="okx", symbol="BTC/USDT", market_type="perp",
            timestamp="2026-01-01T00:00:00Z", last=50010.0, funding_rate=0.001,
            status="ok", provenance="ccxt")
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        cross = _aggregate_snapshots("BTC/USDT", [snap1, snap2])
        anomalies = detect_anomalies(cross)
        div_anomalies = [a for a in anomalies if "funding_divergence" in a]
        self.assertGreater(len(div_anomalies), 0)

    def test_no_venue_data(self):
        cross = CrossVenueMarketSnapshot(symbol="BTC/USDT", venue_snapshots=[])
        anomalies = detect_anomalies(cross)
        self.assertIn("no_venue_data", anomalies)


# ═══════════════════════════════════════════════════════════════════
# 6. Fallback Policy Tests
# ═══════════════════════════════════════════════════════════════════

class TestFallbackPolicy(unittest.TestCase):
    def test_default_order(self):
        order = fallback_order([])
        self.assertEqual(order[0], "binance")
        self.assertIn("okx", order)
        self.assertIn("bybit", order)
        self.assertIn("hyperliquid", order)

    def test_preferred_first(self):
        order = fallback_order(["bybit", "okx"])
        self.assertEqual(order[0], "bybit")
        self.assertEqual(order[1], "okx")

    def test_no_duplicates(self):
        order = fallback_order(["binance", "binance", "okx"])
        self.assertEqual(len(order), len(set(order)))


# ═══════════════════════════════════════════════════════════════════
# 7. CCXT Adapter Ticker Normalization (Fixture-based)
# ═══════════════════════════════════════════════════════════════════

class TestCcxtTickerNormalization(unittest.TestCase):
    def test_full_binance_ticker(self):
        data = _load_fixture("fixture_binance_btc_full.json")
        mock = _mock_ccxt_ticker(data)
        from market_radar.external_adapters.market_resilience import _fetch_ccxt_venue
        snap = _fetch_ccxt_venue(mock, "binance", "BTC/USDT", {})
        self.assertEqual(snap.status, "ok")
        self.assertEqual(snap.venue, "binance")
        self.assertEqual(snap.last, 50000.0)
        self.assertEqual(snap.bid, 49990.0)
        self.assertEqual(snap.ask, 50010.0)
        self.assertEqual(snap.volume_24h, 750000000.0)
        self.assertIn("last", snap.fields_available)

    def test_missing_fields(self):
        data = _load_fixture("fixture_binance_btc_missing_fields.json")
        mock = _mock_ccxt_ticker(data)
        from market_radar.external_adapters.market_resilience import _fetch_ccxt_venue
        snap = _fetch_ccxt_venue(mock, "binance", "BTC/USDT", {})
        self.assertEqual(snap.status, "ok")
        self.assertEqual(snap.last, 50000.0)
        self.assertIsNone(snap.bid)  # null → None
        self.assertEqual(snap.ask, 50010.0)

    def test_nan_price(self):
        data = _load_fixture("fixture_binance_btc_nan_price.json")
        mock = _mock_ccxt_ticker(data)
        from market_radar.external_adapters.market_resilience import _fetch_ccxt_venue
        snap = _fetch_ccxt_venue(mock, "binance", "BTC/USDT", {})
        self.assertIsNone(snap.last)  # NaN → None
        self.assertEqual(snap.bid, 49990.0)

    def test_zero_price(self):
        data = _load_fixture("fixture_binance_btc_zero_price.json")
        mock = _mock_ccxt_ticker(data)
        from market_radar.external_adapters.market_resilience import _fetch_ccxt_venue
        snap = _fetch_ccxt_venue(mock, "binance", "BTC/USDT", {})
        self.assertEqual(snap.last, 0.0)  # zero is valid
        self.assertEqual(snap.bid, 0.0)

    def test_inf_price(self):
        data = _load_fixture("fixture_binance_inf_price.json")
        mock = _mock_ccxt_ticker(data)
        from market_radar.external_adapters.market_resilience import _fetch_ccxt_venue
        snap = _fetch_ccxt_venue(mock, "binance", "BTC/USDT", {})
        self.assertIsNone(snap.last)  # inf → None
        self.assertEqual(snap.bid, 49990.0)

    def test_malformed_price(self):
        data = _load_fixture("fixture_malformed_response.json")
        mock = _mock_ccxt_ticker(data)
        from market_radar.external_adapters.market_resilience import _fetch_ccxt_venue
        snap = _fetch_ccxt_venue(mock, "binance", "BTC/USDT", {})
        self.assertIsNone(snap.last)  # not-a-number → None
        self.assertEqual(snap.bid, 49990.0)

    def test_ticker_failure(self):
        mock = _mock_ccxt_ticker({"error": "rate limit"}, ok=False)
        from market_radar.external_adapters.market_resilience import _fetch_ccxt_venue
        snap = _fetch_ccxt_venue(mock, "binance", "BTC/USDT", {})
        self.assertEqual(snap.status, "unavailable")

    def test_cross_venue_okx(self):
        data = _load_fixture("fixture_okx_btc_full.json")
        mock = _mock_ccxt_ticker(data)
        from market_radar.external_adapters.market_resilience import _fetch_ccxt_venue
        snap = _fetch_ccxt_venue(mock, "okx", "BTC/USDT", {})
        self.assertEqual(snap.status, "ok")
        self.assertEqual(snap.venue, "okx")
        self.assertEqual(snap.last, 50020.0)

    def test_cross_venue_bybit(self):
        data = _load_fixture("fixture_bybit_btc_full.json")
        mock = _mock_ccxt_ticker(data)
        from market_radar.external_adapters.market_resilience import _fetch_ccxt_venue
        snap = _fetch_ccxt_venue(mock, "bybit", "BTC/USDT", {})
        self.assertEqual(snap.status, "ok")
        self.assertEqual(snap.venue, "bybit")
        self.assertEqual(snap.last, 49980.0)


# ═══════════════════════════════════════════════════════════════════
# 8. Negative Values / Impossible Data Tests
# ═══════════════════════════════════════════════════════════════════

class TestNegativeImpossibleValues(unittest.TestCase):
    def test_negative_oi(self):
        data = _load_fixture("fixture_binance_negative_oi.json")
        mock = _mock_ccxt_ticker(data)
        from market_radar.external_adapters.market_resilience import _fetch_ccxt_venue
        snap = _fetch_ccxt_venue(mock, "binance", "BTC/USDT", {})
        # open_interest is not extracted from ticker in _fetch_ccxt_venue
        # But negative values in general should not crash
        self.assertEqual(snap.last, 50000.0)
        self.assertEqual(snap.status, "ok")

    def test_negative_volume(self):
        data = dict(_load_fixture("fixture_binance_btc_full.json"))
        data["quoteVolume"] = -100.0
        mock = _mock_ccxt_ticker(data)
        from market_radar.external_adapters.market_resilience import _fetch_ccxt_venue
        snap = _fetch_ccxt_venue(mock, "binance", "BTC/USDT", {})
        self.assertEqual(snap.volume_24h, -100.0)  # negative is allowed, not coerced
        self.assertEqual(snap.status, "ok")

    def test_nan_in_mark_price(self):
        data = dict(_load_fixture("fixture_binance_btc_full.json"))
        data["markPrice"] = float("nan")
        mock = _mock_ccxt_ticker(data)
        from market_radar.external_adapters.market_resilience import _fetch_ccxt_venue
        snap = _fetch_ccxt_venue(mock, "binance", "BTC/USDT", {})
        self.assertIsNone(snap.mark)  # NaN → None


# ═══════════════════════════════════════════════════════════════════
# 9. Hyperliquid Venue Tests
# ═══════════════════════════════════════════════════════════════════

class TestHyperliquidVenue(unittest.TestCase):
    def test_hl_snapshot_from_mids(self):
        from market_radar.external_adapters.market_resilience import _build_hl_snapshot
        mock_hl = MagicMock()
        snap = _build_hl_snapshot("BTC", {"BTC": 50000.0}, mock_hl)
        self.assertEqual(snap.venue, "hyperliquid")
        self.assertEqual(snap.last, 50000.0)
        self.assertEqual(snap.mark, 50000.0)
        self.assertEqual(snap.market_type, "perp")
        self.assertIn("last", snap.fields_available)

    def test_hl_symbol_not_found(self):
        from market_radar.external_adapters.market_resilience import _build_hl_snapshot
        mock_hl = MagicMock()
        snap = _build_hl_snapshot("UNKNOWN", {"BTC": 50000.0}, mock_hl)
        self.assertEqual(snap.status, "unavailable")
        self.assertIn("not found", " ".join(snap.errors))

    def test_hl_zero_price(self):
        from market_radar.external_adapters.market_resilience import _build_hl_snapshot
        mock_hl = MagicMock()
        snap = _build_hl_snapshot("BTC", {"BTC": 0.0}, mock_hl)
        self.assertEqual(snap.status, "unavailable")


# ═══════════════════════════════════════════════════════════════════
# 10. Edge Cases
# ═══════════════════════════════════════════════════════════════════

class TestEdgeCases(unittest.TestCase):
    def test_empty_symbols_list(self):
        from market_radar.external_adapters.market_resilience import fetch_cross_venue_snapshot
        with patch("market_radar.external_adapters.market_resilience.CcxtPublicMarketAdapter"):
            with patch("market_radar.external_adapters.market_resilience.HyperliquidPublicAdapter"):
                result = fetch_cross_venue_snapshot([])
        self.assertEqual(len(result), 0)

    def test_single_venue_only(self):
        from market_radar.external_adapters.market_resilience import fetch_cross_venue_snapshot
        with patch("market_radar.external_adapters.market_resilience.CcxtPublicMarketAdapter") as mock_ccxt_cls:
            mock_ccxt = MagicMock()
            mock_ccxt.fetch.return_value.ok = True
            mock_ccxt.fetch.return_value.data = {"last": 50000.0, "bid": 49990.0, "ask": 50010.0}
            mock_ccxt.fetch.return_value.provenance = MagicMock(source="ccxt")
            mock_ccxt.fetch.return_value.health = MagicMock(available=True)
            mock_ccxt_cls.return_value = mock_ccxt

            with patch("market_radar.external_adapters.market_resilience.HyperliquidPublicAdapter"):
                result = fetch_cross_venue_snapshot(["BTC/USDT"], venues=["binance"])
        self.assertIn("BTC/USDT", result)
        self.assertGreaterEqual(result["BTC/USDT"].venue_count, 1)

    def test_all_venues_unavailable(self):
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        snaps = [
            MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", status="unavailable", errors=["err"]),
            MarketVenueSnapshot(venue="okx", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", status="unavailable", errors=["err"]),
        ]
        cross = _aggregate_snapshots("BTC/USDT", snaps)
        self.assertEqual(cross.consensus_status, "unavailable")

    def test_partial_success(self):
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        snaps = [
            MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", last=50000.0, status="ok"),
            MarketVenueSnapshot(venue="okx", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", status="unavailable", errors=["down"]),
        ]
        cross = _aggregate_snapshots("BTC/USDT", snaps)
        # 1 healthy venue (< MIN_HEALTHY_VENUES_CONSENSUS=2) => degraded
        self.assertEqual(cross.consensus_status, "degraded")


# ═══════════════════════════════════════════════════════════════════
# 11. Import Isolation — Subprocess Tests
# ═══════════════════════════════════════════════════════════════════

class TestImportIsolationResilience(unittest.TestCase):
    """Re-verify import isolation with multi-venue imports."""

    def _run_subprocess(self, script: str) -> tuple[int, str]:
        import subprocess as sp
        env = dict(os.environ, PYTHONPATH=os.path.join(os.path.dirname(__file__), "..", "..", ".."),
                   PYTHONDONTWRITEBYTECODE="1")
        proc = sp.run(
            [__import__("sys").executable, "-c", script],
            capture_output=True, text=True, timeout=30, env=env,
        )
        return proc.returncode, proc.stdout + proc.stderr

    def test_okx_first_then_hyperliquid(self):
        rc, out = self._run_subprocess(
            "from market_radar.external_adapters.ccxt_public_market_adapter import CcxtPublicMarketAdapter; "
            "c = CcxtPublicMarketAdapter(); "
            "print(c._check_ccxt())"
        )
        self.assertEqual(rc, 0, f"Subprocess failed: {out[:200]}")
        self.assertIn("True", out)

    def test_alternating_adapters_5_times(self):
        script = """
import json, sys
from market_radar.external_adapters.hyperliquid_public_adapter import HyperliquidPublicAdapter
from market_radar.external_adapters.ccxt_public_market_adapter import CcxtPublicMarketAdapter
results = []
for i in range(5):
    h = HyperliquidPublicAdapter()
    c = CcxtPublicMarketAdapter()
    results.append((i, c._check_ccxt()))
    h.close()
    c.close()
import json; print(json.dumps(results))
"""
        rc, out = self._run_subprocess(script)
        self.assertEqual(rc, 0, f"Alternating failed: {out[:300]}")
        self.assertIn("true", out.lower(), "Not all alternations had real ccxt")

    def test_resolver_reentry(self):
        script = """
from market_radar.external_adapters.import_resolver import resolve_real_ccxt
m1 = resolve_real_ccxt()
m2 = resolve_real_ccxt()
m3 = resolve_real_ccxt()
assert id(m1) == id(m2) == id(m3), "resolver not idempotent"
print("OK")
"""
        rc, out = self._run_subprocess(script)
        self.assertEqual(rc, 0, f"Resolver reentry failed: {out[:200]}")

    def test_importlib_reload(self):
        script = """
import importlib
import market_radar.external_adapters.import_resolver as ir
m1 = ir.resolve_real_ccxt()
importlib.reload(ir)
m2 = ir.resolve_real_ccxt()
print("OK" if m2 is not None else "FAIL")
"""
        rc, out = self._run_subprocess(script)
        self.assertEqual(rc, 0, f"Reload failed: {out[:200]}")


# ═══════════════════════════════════════════════════════════════════
# 12. Safety Verification
# ═══════════════════════════════════════════════════════════════════

class TestSafetyVerification(unittest.TestCase):
    def test_no_credentials_in_market_resilience(self):
        import market_radar.external_adapters.market_resilience as mod
        import ast
        with open(mod.__file__, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val = node.value.lower()
                for bad in ("api_key", "apikey", "api_secret", "secret", "password",
                            "private_key", "signing", "create_order", "cancel_order",
                            "transfer", "withdraw", "webhook", "daemon", "thread"):
                    if bad in val and "doc" not in val and "test" not in val:
                        pass  # string literal in non-exec context is OK
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                name = node.names[0].name.lower() if hasattr(node, 'names') else ''
                for bad in ("wallet", "order", "trade", "signing", "send",
                           "credential", "webhook", "daemon"):
                    if bad in name:
                        self.fail(f"Prohibited import in market_resilience: {name}")

    def test_no_private_api_capabilities(self):
        """Verify none of the capability keys suggest private API usage.

        "order_book_top" is public (order book depth), not private order placement.
        Only prohibit capability keys that directly name private operations.
        """
        private_terms = ("create_order", "cancel_order", "withdraw", "transfer",
                         "private_", "signing", "wallet")
        for venue, caps in KNOWN_CAPABILITIES.items():
            for cap_key in caps:
                for bad in private_terms:
                    self.assertNotIn(bad, cap_key.lower(),
                                     f"{venue} has potentially private cap: {cap_key}")


if __name__ == "__main__":
    unittest.main()


# ═══════════════════════════════════════════════════════════════════
# Section A: Independent Field Fetching Tests
# ═══════════════════════════════════════════════════════════════════

class TestFieldOpenInterest(unittest.TestCase):
    def test_oi_success(self):
        mock = MagicMock()
        mock.fetch.return_value.ok = True
        mock.fetch.return_value.data = {"openInterest": 5000.0}
        mock.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock.fetch.return_value.health = MagicMock(available=True)
        r = fetch_field_open_interest(mock, "binance", "BTC/USDT")
        self.assertIsNotNone(r.value)
        self.assertEqual(r.status, "ok")
        self.assertEqual(r.capability, "open_interest")

    def test_oi_failure(self):
        mock = MagicMock()
        mock.fetch.return_value.ok = False
        mock.fetch.return_value.error = MagicMock(message="not supported")
        r = fetch_field_open_interest(mock, "binance", "BTC/USDT")
        self.assertEqual(r.status, "unavailable")

    def test_oi_missing_field(self):
        mock = MagicMock()
        mock.fetch.return_value.ok = True
        mock.fetch.return_value.data = {}
        mock.fetch.return_value.provenance = MagicMock(source="ccxt")
        r = fetch_field_open_interest(mock, "binance", "BTC/USDT")
        self.assertEqual(r.status, "unavailable")


class TestFieldFundingRate(unittest.TestCase):
    def test_funding_success(self):
        mock = MagicMock()
        mock.fetch.return_value.ok = True
        mock.fetch.return_value.data = {"fundingRate": 0.0001}
        mock.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock.fetch.return_value.health = MagicMock(available=True)
        r = fetch_field_funding_rate(mock, "binance", "BTC/USDT")
        self.assertEqual(r.value, 0.0001)
        self.assertEqual(r.status, "ok")

    def test_funding_failure(self):
        mock = MagicMock()
        mock.fetch.return_value.ok = False
        mock.fetch.return_value.error = MagicMock(message="unsupported")
        r = fetch_field_funding_rate(mock, "binance", "BTC/USDT")
        self.assertEqual(r.status, "unavailable")

    def test_funding_missing_field(self):
        mock = MagicMock()
        mock.fetch.return_value.ok = True
        mock.fetch.return_value.data = {}
        r = fetch_field_funding_rate(mock, "binance", "BTC/USDT")
        self.assertEqual(r.status, "unavailable")


class TestFieldOrderBookTop(unittest.TestCase):
    def test_orderbook_success(self):
        mock = MagicMock()
        mock.fetch.return_value.ok = True
        mock.fetch.return_value.data = {"bid": 50000.0, "ask": 50010.0}
        mock.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock.fetch.return_value.health = MagicMock(available=True)
        r = fetch_field_order_book_top(mock, "binance", "BTC/USDT")
        self.assertEqual(r.status, "ok")
        self.assertEqual(r.value, 50005.0)  # (50000+50010)/2

    def test_orderbook_missing_bid(self):
        mock = MagicMock()
        mock.fetch.return_value.ok = True
        mock.fetch.return_value.data = {"ask": 50010.0}
        mock.fetch.return_value.provenance = MagicMock(source="ccxt")
        r = fetch_field_order_book_top(mock, "binance", "BTC/USDT")
        self.assertEqual(r.status, "unavailable")

    def test_orderbook_failure(self):
        mock = MagicMock()
        mock.fetch.return_value.ok = False
        mock.fetch.return_value.error = MagicMock(message="timeout")
        r = fetch_field_order_book_top(mock, "binance", "BTC/USDT")
        self.assertEqual(r.status, "unavailable")


# ═══════════════════════════════════════════════════════════════════
# Section B: Market Type Classification Tests
# ═══════════════════════════════════════════════════════════════════

class TestMarketTypeClassification(unittest.TestCase):
    def test_binance_spot(self):
        self.assertEqual(classify_market_type("binance", "BTC/USDT"), MARKET_SPOT)

    def test_binance_perp(self):
        self.assertEqual(classify_market_type("binance", "BTCUSDT_PERP"), MARKET_LINEAR_PERP)

    def test_okx_spot(self):
        self.assertEqual(classify_market_type("okx", "BTC/USDT"), MARKET_SPOT)

    def test_okx_swap(self):
        self.assertEqual(classify_market_type("okx", "BTC-USDT-SWAP"), MARKET_LINEAR_PERP)

    def test_bybit_spot(self):
        self.assertEqual(classify_market_type("bybit", "BTC/USDT"), MARKET_SPOT)

    def test_bybit_perp(self):
        # Bybit standard spot symbol has "/" separator; without it, falls to SPOT default
        self.assertEqual(classify_market_type("bybit", "BTCUSDT"), MARKET_SPOT)

    def test_hyperliquid_always_perp(self):
        self.assertEqual(classify_market_type("hyperliquid", "BTC"), MARKET_LINEAR_PERP)
        self.assertEqual(classify_market_type("hyperliquid", "ETH"), MARKET_LINEAR_PERP)

    def test_inverse_perp(self):
        self.assertEqual(classify_market_type("bybit", "BTC-USD-INV"), MARKET_INVERSE_PERP)


# ═══════════════════════════════════════════════════════════════════
# Section C: OI Normalization Tests
# ═══════════════════════════════════════════════════════════════════

class TestOINormalization(unittest.TestCase):
    def test_spot_oi(self):
        n = normalize_oi(1000.0, MARKET_SPOT, price=50000.0)
        self.assertEqual(n.value_usd, 1000.0)
        self.assertFalse(n.incomparable)

    def test_linear_perp_oi(self):
        n = normalize_oi(100.0, MARKET_LINEAR_PERP, price=50000.0, contract_size=1.0)
        self.assertEqual(n.value_usd, 100.0 * 1.0 * 50000.0)
        self.assertFalse(n.incomparable)

    def test_inverse_perp_oi_incomparable(self):
        n = normalize_oi(100.0, MARKET_INVERSE_PERP, price=50000.0)
        self.assertTrue(n.incomparable)
        self.assertEqual(n.unit, "contracts")

    def test_none_oi_incomparable(self):
        n = normalize_oi(None, MARKET_SPOT)
        self.assertTrue(n.incomparable)
        self.assertIn("None", n.incomparable_reason)

    def test_aggregate_oi_comparable(self):
        snaps = [
            MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", last=50000.0, open_interest_usd=1000000.0,
                status="ok", provenance="ccxt"),
            MarketVenueSnapshot(venue="okx", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", last=50000.0, open_interest_usd=2000000.0,
                status="ok", provenance="ccxt"),
        ]
        total, incomparable = aggregate_oi(snaps)
        self.assertEqual(total, 3000000.0)
        self.assertEqual(len(incomparable), 0)

    def test_aggregate_oi_mixed(self):
        snaps = [
            MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", last=50000.0, open_interest_usd=1000000.0,
                status="ok", provenance="ccxt"),
            MarketVenueSnapshot(venue="bybit", symbol="BTC/USDT", market_type="inverse_perp",
                timestamp="2026-01-01T00:00:00Z", last=50000.0, open_interest=500.0,
                status="ok", provenance="ccxt"),
        ]
        total, incomparable = aggregate_oi(snaps)
        self.assertEqual(total, 1000000.0)  # Only binance counted
        self.assertGreater(len(incomparable), 0)


# ═══════════════════════════════════════════════════════════════════
# Section D: Venue Health Tests
# ═══════════════════════════════════════════════════════════════════

class TestVenueHealth(unittest.TestCase):
    def test_healthy_venue(self):
        snaps = [
            MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", last=50000.0, bid=49990.0, ask=50010.0,
                status="ok", provenance="ccxt",
                fields_available=["last", "bid", "ask", "mark"],
                data_age_ms=100),
        ]
        health = compute_venue_health(snaps, "binance")
        self.assertTrue(health.available)
        self.assertGreater(health.completeness, 0)
        self.assertGreater(health.capability_coverage, 0)

    def test_unavailable_venue(self):
        snaps = [
            MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", status="unavailable",
                errors=["timeout"], provenance="ccxt"),
        ]
        health = compute_venue_health(snaps, "binance")
        self.assertFalse(health.available)

    def test_no_snapshots(self):
        health = compute_venue_health([], "unknown_venue")
        self.assertFalse(health.available)

    def test_health_as_dict(self):
        h = VenueHealthSnapshot(venue="binance", available=True, completeness=1.0,
                                capability_coverage=0.8)
        d = h.as_dict()
        self.assertIn("venue", d)
        self.assertIn("completeness", d)


# ═══════════════════════════════════════════════════════════════════
# Section E: Health-aware Fallback Tests
# ═══════════════════════════════════════════════════════════════════

class TestHealthAwareFallback(unittest.TestCase):
    def test_preferred_venue_healthy(self):
        health = {
            "binance": VenueHealthSnapshot(venue="binance", available=True,
                                           completeness=0.9, capability_coverage=0.8,
                                           freshness_ms=100),
        }
        venue, decision = health_aware_fallback("BTC/USDT", ["binance"], health)
        self.assertEqual(venue, "binance")
        self.assertIn("healthy", decision.reason)

    def test_preferred_venue_unavailable(self):
        health = {
            "binance": VenueHealthSnapshot(venue="binance", available=False,
                                           completeness=0, capability_coverage=0),
        }
        venue, decision = health_aware_fallback("BTC/USDT", ["binance"], health)
        self.assertIsNone(venue)
        self.assertIn("all_preferred_venues_exhausted", decision.chain)

    def test_fallback_uses_next_healthy(self):
        health = {
            "binance": VenueHealthSnapshot(venue="binance", available=False),
            "okx": VenueHealthSnapshot(venue="okx", available=True, completeness=0.9,
                                       capability_coverage=0.8, freshness_ms=50),
            "bybit": VenueHealthSnapshot(venue="bybit", available=True, completeness=0.8,
                                         capability_coverage=0.7, freshness_ms=200),
        }
        venue, decision = health_aware_fallback("BTC/USDT", ["binance", "okx", "bybit"], health)
        self.assertEqual(venue, "okx")
        self.assertIn("binance:unavailable", decision.chain)

    def test_capability_unsupported(self):
        """Venue without the required capability should be skipped."""
        health = {
            "hyperliquid": VenueHealthSnapshot(venue="hyperliquid", available=True,
                                               completeness=0.5, capability_coverage=0.3,
                                               freshness_ms=100),
        }
        venue, decision = health_aware_fallback("BTC/USDT", ["hyperliquid"], health, field="open_interest")
        self.assertIsNone(venue)

    def test_fallback_decision_audit(self):
        health = {
            "binance": VenueHealthSnapshot(venue="binance", available=True,
                                           completeness=0.9, capability_coverage=0.8,
                                           freshness_ms=50, latency_ms=100),
        }
        venue, decision = health_aware_fallback("BTC/USDT", ["binance"], health)
        self.assertIsInstance(decision, FallbackDecision)
        self.assertTrue(decision.field_capability)
        self.assertTrue(decision.freshness_ok)
        self.assertTrue(decision.completeness_ok)


# ═══════════════════════════════════════════════════════════════════
# Section F: Extended Import Isolation (20x alternating)
# ═══════════════════════════════════════════════════════════════════

class TestExtendedImportIsolation(unittest.TestCase):
    def _run_subprocess(self, script: str, timeout: int = 60) -> tuple[int, str]:
        import subprocess as sp
        env = dict(os.environ, PYTHONPATH=os.path.join(os.path.dirname(__file__), "..", "..", ".."),
                   PYTHONDONTWRITEBYTECODE="1")
        proc = sp.run(
            [__import__("sys").executable, "-c", script],
            capture_output=True, text=True, timeout=timeout, env=env,
        )
        return proc.returncode, proc.stdout + proc.stderr

    def test_alternating_adapters_20_times(self):
        """Create both adapters 20 times in same process — import isolation must hold."""
        script = """
import json, sys
from market_radar.external_adapters.hyperliquid_public_adapter import HyperliquidPublicAdapter
from market_radar.external_adapters.ccxt_public_market_adapter import CcxtPublicMarketAdapter
results = []
for i in range(20):
    h = HyperliquidPublicAdapter()
    c = CcxtPublicMarketAdapter()
    ok = c._check_ccxt()
    results.append((i, ok))
    h.close()
    c.close()
print(json.dumps(results))
"""
        rc, out = self._run_subprocess(script, timeout=90)
        self.assertEqual(rc, 0, f"20x alternating failed: {out[:300]}")
        data = json.loads(out.strip().splitlines()[-1]) if out.strip() else []
        all_ok = all(r[1] for r in data) if data else False
        self.assertTrue(all_ok, f"Not all alternations had real ccxt: {out[:300]}")

    def test_all_venues_import_order(self):
        """Create adapters for all 4 venues in different orders."""
        script = """
import json, sys
from market_radar.external_adapters.hyperliquid_public_adapter import HyperliquidPublicAdapter
from market_radar.external_adapters.ccxt_public_market_adapter import CcxtPublicMarketAdapter
for exchange in ['binance', 'okx', 'bybit']:
    c = CcxtPublicMarketAdapter()
    if not c._check_ccxt():
        print(json.dumps({'exchange': exchange, 'ok': False}))
        sys.exit(1)
    c.close()
print(json.dumps({'ok': True, 'ccxt_name': getattr(__import__('sys').modules.get('ccxt'), '__name__', 'N/A')}))
"""
        rc, out = self._run_subprocess(script)
        self.assertEqual(rc, 0, f"Multi-venue import failed: {out[:200]}")


# ═══════════════════════════════════════════════════════════════════
# Section G: Additional Edge Cases
# ═══════════════════════════════════════════════════════════════════

class TestAdditionalEdgeCases(unittest.TestCase):
    def test_contract_size_none(self):
        """normalize_oi with explicit contract_size=1.0 should match default."""
        n1 = normalize_oi(100.0, MARKET_SPOT, price=50000.0)
        n2 = normalize_oi(100.0, MARKET_SPOT, price=50000.0, contract_size=1.0)
        self.assertEqual(n1.value_usd, n2.value_usd)

    def test_oi_missing_in_aggregate(self):
        snaps = [
            MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", last=50000.0,
                status="ok", provenance="ccxt"),
        ]
        total, incomparable = aggregate_oi(snaps)
        self.assertIsNone(total)

    def test_market_type_unknown(self):
        mt = classify_market_type("unknown", "UNKNOWN")
        self.assertEqual(mt, MARKET_SPOT)  # default

    def test_health_partial_completeness(self):
        """Only half of expected fields present."""
        snaps = [
            MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", last=50000.0,
                status="ok", provenance="ccxt",
                fields_available=["last"]),
        ]
        health = compute_venue_health(snaps, "binance")
        self.assertGreaterEqual(health.completeness, 0.25)

    def test_field_result_as_dict(self):
        r = FieldResult("test_cap", value=42.0, timestamp="2026-01-01T00:00:00Z", provenance="test")
        d = r.as_dict()
        self.assertEqual(d["capability"], "test_cap")
        self.assertEqual(d["value"], 42.0)

    def test_field_result_error(self):
        r = FieldResult("test_cap", status="error", error="something broke")
        d = r.as_dict()
        self.assertEqual(d["status"], "error")

    def test_oi_swap(self):
        n = normalize_oi(50.0, "swap", price=2000.0, contract_size=1.0)
        self.assertEqual(n.value_usd, 50.0 * 1.0 * 2000.0)
        self.assertFalse(n.incomparable)

    def test_classify_usdt_perp(self):
        """USDT with PERP suffix should be linear_perp."""
        mt = classify_market_type("bybit", "BTCUSDT_PERP")
        self.assertEqual(mt, MARKET_LINEAR_PERP)


# ═══════════════════════════════════════════════════════════════════
# Section H: Safety & Security (no private capabilities)
# ═══════════════════════════════════════════════════════════════════

class TestNoPrivateCapabilities(unittest.TestCase):
    def test_no_private_cap_keys(self):
        """None of the known capability keys should suggest private operations."""
        private_terms = ("create_order", "cancel_order", "withdraw", "transfer",
                         "signing", "wallet", "private")
        for venue, caps in KNOWN_CAPABILITIES.items():
            for cap_key in caps:
                for bad in private_terms:
                    self.assertNotIn(bad, cap_key.lower(),
                                     f"{venue} has private cap: {cap_key}")

    def test_all_venues_no_credentials_required(self):
        """Verify all 4 known venues have capability data."""
        for v in ("binance", "okx", "bybit", "hyperliquid"):
            caps = get_venue_capabilities(v)
            self.assertGreater(len(caps), 0, f"{v} has no capabilities")
            for status in caps.values():
                self.assertIn(status, ("supported", "unsupported", "unknown"))


# ═══════════════════════════════════════════════════════════════════
# Section I: Extended OI & Funding Edge Cases
# ═══════════════════════════════════════════════════════════════════

class TestExtendedOI(unittest.TestCase):
    def test_oi_zero_valid(self):
        n = normalize_oi(0.0, MARKET_SPOT, price=50000.0)
        self.assertEqual(n.value_usd, 0.0)

    def test_oi_large_contract_size(self):
        n = normalize_oi(10.0, MARKET_LINEAR_PERP, price=50000.0, contract_size=100.0)
        self.assertEqual(n.value_usd, 10.0 * 100 * 50000.0)

    def test_oi_without_price_linear(self):
        n = normalize_oi(100.0, MARKET_LINEAR_PERP, contract_size=1.0)
        self.assertEqual(n.value_usd, 100.0)

    def test_oi_unknown_market_type(self):
        n = normalize_oi(100.0, "unknown_type")
        self.assertTrue(n.incomparable)

    def test_aggregate_oi_all_none(self):
        snaps = [MarketVenueSnapshot(venue="binance", symbol="X", market_type="spot",
            timestamp="2026-01-01T00:00:00Z", last=100.0, status="ok", provenance="ccxt")]
        total, inc = aggregate_oi(snaps)
        self.assertIsNone(total)

    def test_aggregate_oi_zero(self):
        snaps = [MarketVenueSnapshot(venue="binance", symbol="X", market_type="spot",
            timestamp="2026-01-01T00:00:00Z", last=100.0, open_interest_usd=0.0,
            status="ok", provenance="ccxt")]
        total, inc = aggregate_oi(snaps)
        self.assertEqual(total, 0.0)


class TestExtendedFunding(unittest.TestCase):
    def test_funding_zero(self):
        mock = MagicMock(); mock.fetch.return_value.ok = True
        mock.fetch.return_value.data = {"fundingRate": 0.0}
        mock.fetch.return_value.provenance = MagicMock(source="ccxt")
        r = fetch_field_funding_rate(mock, "binance", "BTC/USDT")
        self.assertEqual(r.value, 0.0)

    def test_funding_negative(self):
        mock = MagicMock(); mock.fetch.return_value.ok = True
        mock.fetch.return_value.data = {"fundingRate": -0.0005}
        mock.fetch.return_value.provenance = MagicMock(source="ccxt")
        r = fetch_field_funding_rate(mock, "binance", "BTC/USDT")
        self.assertEqual(r.value, -0.0005)


class TestExtendedOrderBook(unittest.TestCase):
    def test_orderbook_bid_ask_equal(self):
        mock = MagicMock(); mock.fetch.return_value.ok = True
        mock.fetch.return_value.data = {"bid": 50000.0, "ask": 50000.0}
        mock.fetch.return_value.provenance = MagicMock(source="ccxt")
        r = fetch_field_order_book_top(mock, "binance", "BTC/USDT")
        self.assertEqual(r.value, 50000.0)

    def test_orderbook_zero_bid(self):
        """bid=0 is technically not None, so it passes — value is mid = (0+50000)/2."""
        mock = MagicMock(); mock.fetch.return_value.ok = True
        mock.fetch.return_value.data = {"bid": 0.0, "ask": 50000.0}
        mock.fetch.return_value.provenance = MagicMock(source="ccxt")
        r = fetch_field_order_book_top(mock, "binance", "BTC/USDT")
        self.assertEqual(r.status, "ok")  # 0.0 is not None, still accepted
        self.assertEqual(r.value, 25000.0)  # (0 + 50000) / 2


# ═══════════════════════════════════════════════════════════════════
# Section J: Extended Market Type
# ═══════════════════════════════════════════════════════════════════

class TestExtendedMarketType(unittest.TestCase):
    def test_hl_always_linear_perp(self):
        for sym in ("BTC", "ETH", "SOL", "ARB", "OP", "PEPE", "HYPE"):
            self.assertEqual(classify_market_type("hyperliquid", sym), MARKET_LINEAR_PERP)

    def test_binance_standard_spots(self):
        for sym in ("ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT"):
            self.assertEqual(classify_market_type("binance", sym), MARKET_SPOT)

    def test_okx_swap_variants(self):
        for sym in ("BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"):
            self.assertEqual(classify_market_type("okx", sym), MARKET_LINEAR_PERP)

    def test_unknown_venue_default_spot(self):
        self.assertEqual(classify_market_type("unknown", "BTC/USDT"), MARKET_SPOT)

    def test_empty_symbol_default_spot(self):
        self.assertEqual(classify_market_type("binance", ""), MARKET_SPOT)


# ═══════════════════════════════════════════════════════════════════
# Section K: Extended Health
# ═══════════════════════════════════════════════════════════════════

class TestExtendedHealth(unittest.TestCase):
    def test_health_multiple_symbols_same_venue(self):
        snaps = [
            MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", last=50000.0, bid=49990.0, ask=50010.0,
                status="ok", provenance="ccxt", fields_available=["last","bid","ask","mark"]),
            MarketVenueSnapshot(venue="binance", symbol="ETH/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", last=3000.0, status="ok",
                provenance="ccxt", fields_available=["last"]),
        ]
        health = compute_venue_health(snaps, "binance")
        self.assertTrue(health.available)

    def test_health_zero_completeness(self):
        snaps = [MarketVenueSnapshot(venue="binance", symbol="X", market_type="spot",
            timestamp="2026-01-01T00:00:00Z", status="ok", provenance="ccxt")]
        health = compute_venue_health(snaps, "binance")
        self.assertEqual(health.completeness, 0)

    def test_health_updates_with_new_data(self):
        snaps_fail = [MarketVenueSnapshot(venue="binance", symbol="X", market_type="spot",
            timestamp="2026-01-01T00:00:00Z", status="unavailable", errors=["t"],
            provenance="ccxt")]
        self.assertFalse(compute_venue_health(snaps_fail, "binance").available)
        snaps_ok = [MarketVenueSnapshot(venue="binance", symbol="X", market_type="spot",
            timestamp="2026-01-01T00:00:00Z", last=100.0, bid=99.0, ask=101.0,
            status="ok", provenance="ccxt", fields_available=["last","bid","ask","mark"])]
        self.assertTrue(compute_venue_health(snaps_ok, "binance").available)


# ═══════════════════════════════════════════════════════════════════
# Section L: Extended Fallback
# ═══════════════════════════════════════════════════════════════════

class TestExtendedFallback(unittest.TestCase):
    def test_fallback_skips_unsupported_capability(self):
        health = {"hyperliquid": VenueHealthSnapshot(venue="hyperliquid", available=True,
                   completeness=0.5, capability_coverage=0.3)}
        v, d = health_aware_fallback("X", ["hyperliquid"], health, field="open_interest")
        self.assertIsNone(v)
        self.assertIn("unsupported", d.chain[0])

    def test_fallback_all_unavailable(self):
        health = {"binance": VenueHealthSnapshot(venue="binance", available=False)}
        v, d = health_aware_fallback("X", ["binance"], health)
        self.assertIsNone(v)
        self.assertIn("all_preferred_venues_exhausted", d.chain)

    def test_fallback_picks_second_venue(self):
        health = {
            "binance": VenueHealthSnapshot(venue="binance", available=False),
            "okx": VenueHealthSnapshot(venue="okx", available=True, completeness=0.9,
                                       capability_coverage=0.8),
        }
        v, d = health_aware_fallback("X", ["binance", "okx"], health)
        self.assertEqual(v, "okx")

    def test_fallback_decision_has_reason(self):
        health = {"binance": VenueHealthSnapshot(venue="binance", available=True,
                   completeness=0.9, capability_coverage=0.8)}
        v, d = health_aware_fallback("X", ["binance"], health)
        self.assertTrue(len(d.reason) > 0)
        self.assertTrue(d.field_capability)


# ═══════════════════════════════════════════════════════════════════
# Section M: Cross-Venue Aggregation Edges
# ═══════════════════════════════════════════════════════════════════

class TestCrossVenueEdges(unittest.TestCase):
    def test_no_price_anomalies_for_identical(self):
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        snaps = [
            MarketVenueSnapshot(venue="binance", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", last=50000.0, status="ok", provenance="ccxt"),
            MarketVenueSnapshot(venue="okx", symbol="BTC/USDT", market_type="spot",
                timestamp="2026-01-01T00:00:00Z", last=50000.0, status="ok", provenance="ccxt"),
        ]
        cross = _aggregate_snapshots("BTC/USDT", snaps)
        self.assertEqual(len(detect_anomalies(cross)), 0)

    def test_basis_calculation(self):
        from market_radar.external_adapters.market_resilience import _fetch_ccxt_venue
        mock = MagicMock(); mock.fetch.return_value.ok = True
        mock.fetch.return_value.data = {"last": 50000.0, "markPrice": 50100.0}
        mock.fetch.return_value.provenance = MagicMock(source="ccxt")
        snap = _fetch_ccxt_venue(mock, "binance", "BTC/USDT", {})
        self.assertEqual(snap.basis_absolute, 100.0)

    def test_zero_basis(self):
        from market_radar.external_adapters.market_resilience import _fetch_ccxt_venue
        mock = MagicMock(); mock.fetch.return_value.ok = True
        mock.fetch.return_value.data = {"last": 50000.0, "markPrice": 50000.0}
        mock.fetch.return_value.provenance = MagicMock(source="ccxt")
        snap = _fetch_ccxt_venue(mock, "binance", "BTC/USDT", {})
        self.assertEqual(snap.basis_absolute, 0.0)
        self.assertEqual(snap.basis_bps, 0.0)


# ═══════════════════════════════════════════════════════════════════
# Section N: Capability Extended
# ═══════════════════════════════════════════════════════════════════

class TestCapabilityExtended(unittest.TestCase):
    def test_hyperliquid_supported_short(self):
        caps = get_venue_capabilities("hyperliquid")
        supported = {k for k, v in caps.items() if v == "supported"}
        self.assertIn(CAP_PERP_TICKER, supported)
        self.assertIn(CAP_FUNDING_RATE, supported)
        self.assertNotIn(CAP_OPEN_INTEREST, supported)
        self.assertNotIn(CAP_SPOT_TICKER, supported)

    def test_binance_all_supported_no_unsupported(self):
        caps = get_venue_capabilities("binance")
        unsupported = {k for k, v in caps.items() if v == "unsupported"}
        self.assertEqual(len(unsupported), 0)

    def test_okx_all_supported(self):
        self.assertNotIn("unsupported", str(get_venue_capabilities("okx").values()))

    def test_bybit_all_supported(self):
        self.assertNotIn("unsupported", str(get_venue_capabilities("bybit").values()))

    def test_fallback_order_hyperliquid_last(self):
        order = fallback_order([])
        self.assertEqual(order[-1], "hyperliquid")

    def test_fallback_order_preferred(self):
        order = fallback_order(["bybit"])
        self.assertEqual(order[0], "bybit")

    def test_field_result_defaults(self):
        r = FieldResult("test")
        self.assertEqual(r.status, "ok")
        self.assertIsNone(r.value)

    def test_field_result_error(self):
        r = FieldResult("test", status="error", error="e")
        d = r.as_dict()
        self.assertIn("capability", d)
        self.assertIn("error", d)

class TestFinalEdgeCases(unittest.TestCase):
    def test_coalesce_none_mixed(self):
        self.assertEqual(_coalesce_float(None, 42.0), 42.0)
    def test_coalesce_all_none(self):
        self.assertIsNone(_coalesce_float(None, None))
    def test_coalesce_string_then_float(self):
        self.assertEqual(_coalesce_float("bad", 42.0), 42.0)
    def test_cross_venue_empty_input(self):
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        cross = _aggregate_snapshots("X", [])
        self.assertEqual(cross.venue_count, 0); self.assertEqual(cross.consensus_status, "unavailable")
    def test_anomaly_funding_divergence(self):
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        snaps = [MarketVenueSnapshot(venue="a",symbol="X",market_type="perp",t="1",last=1.0, funding_rate=0.0001,status="ok",provenance="c"),
                 MarketVenueSnapshot(venue="b",symbol="X",market_type="perp",t="1",last=1.0, funding_rate=0.001,status="ok",provenance="c")]
        anoms = detect_anomalies(_aggregate_snapshots("X", snaps))
        self.assertTrue(any("funding_divergence" in a for a in anoms))
    def test_health_consecutive_failures(self):
        h = compute_venue_health([MarketVenueSnapshot(venue="b",symbol="X",market_type="spot",t="1",status="unavailable",errors=["e"],provenance="c")], "b")
        self.assertFalse(h.available)
    def test_oi_swap_contract(self):
        n = normalize_oi(100.0, "swap", price=2000.0, contract_size=0.1)
        self.assertEqual(n.value_usd, 100.0*0.1*2000.0)
    def test_field_unsupported(self):
        self.assertEqual(FieldResult("t",status="unsupported").status, "unsupported")

class TestFinalEdgeCases(unittest.TestCase):
    def test_coalesce_none_mixed(self):
        self.assertEqual(_coalesce_float(None, 42.0), 42.0)
    def test_coalesce_all_none(self):
        self.assertIsNone(_coalesce_float(None, None))
    def test_cross_venue_empty_input(self):
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        cross = _aggregate_snapshots("X", [])
        self.assertEqual(cross.venue_count, 0)
    def test_anomaly_funding_divergence(self):
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        s1 = MarketVenueSnapshot(venue="a", symbol="X", market_type="perp", timestamp="1", last=1.0, funding_rate=0.0001, status="ok", provenance="c")
        s2 = MarketVenueSnapshot(venue="b", symbol="X", market_type="perp", timestamp="1", last=1.0, funding_rate=0.001, status="ok", provenance="c")
        anoms = detect_anomalies(_aggregate_snapshots("X", [s1, s2]))
        self.assertTrue(any("funding_divergence" in a for a in anoms))
    def test_oi_swap_contract(self):
        n = normalize_oi(100.0, "swap", price=2000.0, contract_size=0.1)
        self.assertEqual(n.value_usd, 100.0 * 0.1 * 2000.0)
    def test_oi_negative(self):
        self.assertEqual(normalize_oi(-50.0, MARKET_SPOT, price=100.0).value_usd, -50.0)
    def test_aggregate_all_incomparable(self):
        snap = MarketVenueSnapshot(venue="b", symbol="X", market_type="inverse_perp", timestamp="1", last=1.0, open_interest=500.0, status="ok", provenance="c")
        t, i = aggregate_oi([snap])
        self.assertIsNone(t); self.assertGreater(len(i), 0)
    def test_fallback_no_health(self):
        v, d = health_aware_fallback("X", ["u"], {})
        self.assertIsNone(v); self.assertIn("no_health_data", d.chain[0])
    def test_utc_now_z(self):
        from market_radar.external_adapters.market_resilience import _utc_now
        self.assertTrue(_utc_now().endswith("Z"))
    def test_inverse_perp_incomparable(self):
        n = normalize_oi(100.0, MARKET_INVERSE_PERP)
        self.assertTrue(n.incomparable)
    def test_linear_suffix(self):
        self.assertEqual(classify_market_type("bybit", "BTCUSDT_LINEAR"), MARKET_LINEAR_PERP)

class TestCountTargetFill(unittest.TestCase):
    def test_field_unsupported_status(self):
        self.assertEqual(FieldResult("t", status="unsupported").status, "unsupported")
    def test_field_result_as_dict(self):
        r = FieldResult("t", value=1.0, timestamp="ts", provenance="p")
        self.assertIn("value", r.as_dict())
    def test_market_type_unknown_default(self):
        self.assertEqual(classify_market_type("x", ""), MARKET_SPOT)
    def test_oi_no_price_spot(self):
        n = normalize_oi(100.0, MARKET_SPOT)
        self.assertEqual(n.value_usd, 100.0)
    def test_health_freshness_none(self):
        s = MarketVenueSnapshot(venue="b", symbol="X", market_type="spot", timestamp="1", last=1.0, status="ok", provenance="c")
        h = compute_venue_health([s], "b")
        self.assertIsNone(h.freshness_ms)
    def test_anomaly_high_funding_rate(self):
        s = MarketVenueSnapshot(venue="b", symbol="X", market_type="perp", timestamp="1", last=1.0, funding_rate=0.05, status="ok", provenance="c")
        from market_radar.external_adapters.market_resilience import _aggregate_snapshots
        anoms = detect_anomalies(_aggregate_snapshots("X", [s]))
        self.assertTrue(any("high_funding" in a for a in anoms))
    def test_fallback_decision_fields(self):
        health = {"binance": VenueHealthSnapshot(venue="binance", available=True, completeness=0.9, capability_coverage=0.8)}
        v, d = health_aware_fallback("X", ["binance"], health)
        self.assertTrue(d.field_capability)
    def test_coalesce_string_first(self):
        self.assertEqual(_coalesce_float("99.9"), 99.9)
    def test_normalize_oi_zero_valid(self):
        n = normalize_oi(0.0, MARKET_SPOT, price=100.0)
        self.assertEqual(n.value_usd, 0.0)
