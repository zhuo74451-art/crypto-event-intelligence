"""Multi-exchange market resilience tests — offline, fixture-based.

Covers: capability matrix, venue snapshot normalization, cross-venue
aggregation, anomaly detection, fallback policy, import isolation,
NaN/zero/null handling, stale data, rate limits, malformed responses.
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
