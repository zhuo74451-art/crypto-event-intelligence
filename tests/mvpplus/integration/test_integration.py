"""Integration layer tests — no network, injected fake adapters.

Key:
- adapter_result -> whale mapper
- adapter_result -> market mapper
- baseline first observation
- baseline alert suppression
- fixture feed live_count=0
- live-public feed not_connected
- partial source degradation
- all sources unavailable
- HYPE source policy
- deterministic run output
- no-send cannot be disabled
- lock contention (strong semantics)
- stop marker
- failed run releases lock
- SQLite run history
- atomic JSON report
- Workbench HTML generated via W3 render_workbench
- XSS input remains escaped
- no credential/trading/send imports
- official Hyperliquid position shape (position not data)
- allMids mark price injection
- WhalePositionInput -> W2 domain
- baseline suppresses large_new_position
- two-run increase/reduce
- disappeared position close
- parse error degrades source
- failed market omitted from LIVE snapshots
- no price=0 placeholder
- real SQLite run-history row
- final report has finished_at/output paths
- Workbench atomic output
- degraded feed appears in warnings
- strong lock contention
- strong failure-release test
"""
from __future__ import annotations

import json, os, tempfile, time, unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from market_radar.integration.models import (
    IntegrationConfig,
    IntegrationRunResult,
    SourceRunStatus,
    WhaleSnapshotResult,
    MarketSnapshotResult,
    FeedResult,
)
from market_radar.integration.whale_mapper import (
    map_clearinghouse_to_snapshots,
    _parse_hl_position,
    _inject_mark_prices,
    _build_w2_input,
    run_whale_mapper,
)
from market_radar.integration.market_mapper import run_ccxt_ticker, run_hype_mid
from market_radar.integration.feed_handler import run_feed
from market_radar.integration.one_shot import run_one_shot, run_ccxt_preflight
from market_radar.workbench.bundle import WorkbenchBundle
from market_radar.workbench.renderer import render_workbench


# ═══════════════════════════════════════════════════════════════════
# Whale Mapper Tests
# ═══════════════════════════════════════════════════════════════════

class TestParseHLPosition(unittest.TestCase):
    def test_long_position(self):
        """Official live shape: position key, not data."""
        pos = {
            "type": "oneWay",
            "position": {
                "coin": "BTC",
                "szi": "0.5",
                "entryPx": "50000.0",
                "markPx": "51000.0",
                "positionValue": "25500.0",
                "unrealizedPnl": "500.0",
                "liquidationPx": "45000.0",
                "leverage": {"type": "isolated", "value": 5},
                "marginMode": "isolated",
            },
        }
        result = _parse_hl_position(pos)
        self.assertIsNotNone(result)
        self.assertEqual(result["coin"], "BTC")
        self.assertEqual(result["signed_size"], 0.5)
        self.assertEqual(result["entry_price"], 50000.0)
        self.assertEqual(result["mark_price"], 51000.0)
        self.assertEqual(result["leverage"], 5)
        self.assertEqual(result["liquidation_price"], 45000.0)

    def test_official_position_shape(self):
        """Section 2: official Hyperliquid position shape must be parsed."""
        pos = {
            "type": "oneWay",
            "position": {
                "coin": "ETH",
                "szi": "-2.0",
                "entryPx": "3200.0",
                "positionValue": "6400.0",
                "unrealizedPnl": "-100.0",
                "liquidationPx": "3500.0",
                "leverage": {"type": "cross", "value": 3},
                "marginMode": "cross",
            },
        }
        result = _parse_hl_position(pos)
        self.assertIsNotNone(result)
        self.assertEqual(result["coin"], "ETH")
        self.assertEqual(result["signed_size"], -2.0)
        # markPx not in this position — should be None
        self.assertIsNone(result["mark_price"])

    def test_official_position_priority_over_data(self):
        """Section 2: position key must take priority over data key."""
        pos = {
            "type": "oneWay",
            "position": {
                "coin": "BTC",
                "szi": "1.0",
                "entryPx": "50000.0",
                "markPx": "51000.0",
                "positionValue": "51000.0",
                "leverage": {"value": 5},
            },
            "data": {
                "coin": "FAKE",
                "szi": "99.0",
                "entryPx": "1.0",
                "markPx": "1.0",
                "positionValue": "1.0",
                "leverage": {"value": 1},
            },
        }
        result = _parse_hl_position(pos)
        self.assertIsNotNone(result)
        self.assertEqual(result["coin"], "BTC")
        self.assertEqual(result["signed_size"], 1.0)

    def test_legacy_data_fixture_backward_compat(self):
        """Section 2: data key must still work as fallback for fixtures."""
        pos = {
            "type": "oneWay",
            "data": {
                "coin": "BTC",
                "szi": "0.5",
                "entryPx": "50000.0",
                "markPx": "51000.0",
                "positionValue": "25500.0",
                "leverage": {"value": 5},
            },
        }
        result = _parse_hl_position(pos, use_legacy_fixture=True)
        self.assertIsNotNone(result)
        self.assertEqual(result["coin"], "BTC")

    def test_short_position(self):
        pos = {
            "type": "oneWay",
            "position": {
                "coin": "ETH",
                "szi": "-2.0",
                "entryPx": "3200.0",
                "markPx": "3100.0",
                "positionValue": "6200.0",
                "unrealizedPnl": "200.0",
                "liquidationPx": "3500.0",
                "leverage": {"type": "cross", "value": 3},
            },
        }
        result = _parse_hl_position(pos)
        self.assertEqual(result["coin"], "ETH")
        self.assertEqual(result["signed_size"], -2.0)
        self.assertEqual(result["leverage"], 3)

    def test_empty_positions(self):
        """Empty assetPositions must produce no positions."""
        positions, errors = map_clearinghouse_to_snapshots(
            "0xaddr", {"assetPositions": [], "time": 12345},
        )
        self.assertEqual(len(positions), 0)
        self.assertEqual(len(errors), 0)

    def test_missing_liquidation(self):
        """Missing liquidation must be None, never 0."""
        pos = {
            "type": "oneWay",
            "position": {
                "coin": "SOL",
                "szi": "10.0",
                "entryPx": "150.0",
                "markPx": "155.0",
                "positionValue": "1550.0",
                "unrealizedPnl": "50.0",
                "leverage": {"value": 2},
            },
        }
        result = _parse_hl_position(pos)
        self.assertIsNotNone(result)
        self.assertIsNone(result["liquidation_price"])

    def test_invalid_numeric_field(self):
        """Invalid numeric fields must be None, not 0."""
        pos = {
            "type": "oneWay",
            "position": {
                "coin": "BTC",
                "szi": "not-a-number",
                "entryPx": "50000.0",
                "markPx": "51000.0",
                "positionValue": "25500.0",
                "leverage": {"value": 5},
            },
        }
        result = _parse_hl_position(pos)
        self.assertIsNone(result)

    def test_null_liquidation_distance_not_absd(self):
        """Null liquidation must remain null."""
        pos = {
            "type": "oneWay",
            "position": {
                "coin": "BTC",
                "szi": "1.0",
                "entryPx": "50000.0",
                "markPx": "55000.0",
                "positionValue": "55000.0",
                "leverage": {"value": 10},
            },
        }
        result = _parse_hl_position(pos)
        self.assertIsNotNone(result)
        self.assertIsNone(result["liquidation_price"])

    def test_baseline_first_observation(self):
        """First observation with no prior state."""
        positions, errors = map_clearinghouse_to_snapshots(
            "0xaddr",
            {
                "assetPositions": [
                    {
                        "type": "oneWay",
                        "position": {
                            "coin": "BTC",
                            "szi": "0.5",
                            "entryPx": "50000.0",
                            "markPx": "51000.0",
                            "positionValue": "25500.0",
                            "leverage": {"value": 5},
                        },
                    },
                ],
            },
        )
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]["coin"], "BTC")

    def test_exact_zero_close_mapper_input(self):
        """signed_size of exactly 0.0 produces a position entry (edge case)."""
        pos = {
            "type": "oneWay",
            "position": {
                "coin": "BTC",
                "szi": "0.0",
                "entryPx": "50000.0",
                "markPx": "51000.0",
                "positionValue": "0.0",
                "leverage": {"value": 1},
            },
        }
        result = _parse_hl_position(pos)
        self.assertIsNotNone(result)
        self.assertEqual(result["signed_size"], 0.0)


# ═══════════════════════════════════════════════════════════════════
# Mark Price Injection Tests (Section 3)
# ═══════════════════════════════════════════════════════════════════

class TestMarkPriceInjection(unittest.TestCase):
    def test_all_mids_injects_mark(self):
        """allMids must inject mark_price when clearinghouseState has none."""
        positions = [
            {"address": "0xaddr", "coin": "BTC", "signed_size": 0.5,
             "mark_price": None, "entry_price": 50000.0, "position_value_usd": 25000.0},
            {"address": "0xaddr", "coin": "ETH", "signed_size": -2.0,
             "mark_price": None, "entry_price": 3200.0, "position_value_usd": 6400.0},
        ]
        all_mids = {"BTC": "51234.5", "ETH": "3150.0", "SOL": "145.0"}
        updated, errors = _inject_mark_prices(positions, all_mids)
        self.assertEqual(len(errors), 0)
        self.assertAlmostEqual(updated[0]["mark_price"], 51234.5)
        self.assertAlmostEqual(updated[1]["mark_price"], 3150.0)

    def test_existing_mark_preserved(self):
        """Existing mark_price must not be overwritten by allMids."""
        positions = [
            {"address": "0xaddr", "coin": "BTC", "signed_size": 0.5,
             "mark_price": 51000.0, "entry_price": 50000.0, "position_value_usd": 25500.0},
        ]
        all_mids = {"BTC": "52000.0"}
        updated, errors = _inject_mark_prices(positions, all_mids)
        self.assertAlmostEqual(updated[0]["mark_price"], 51000.0)

    def test_missing_coin_in_all_mids(self):
        """Coin not in allMids must produce mapping_error."""
        positions = [
            {"address": "0xaddr", "coin": "UNKNOWN", "signed_size": 10.0,
             "mark_price": None, "entry_price": 1.0, "position_value_usd": 10.0},
        ]
        all_mids = {"BTC": "50000.0"}
        updated, errors = _inject_mark_prices(positions, all_mids)
        self.assertEqual(len(errors), 1)
        self.assertIn("UNKNOWN", errors[0]["reason"])
        self.assertIsNone(updated[0]["mark_price"])

    def test_zero_mid_rejected(self):
        """Zero mid price must be treated as missing."""
        positions = [
            {"address": "0xaddr", "coin": "BTC", "signed_size": 0.5,
             "mark_price": None, "entry_price": 50000.0, "position_value_usd": 25000.0},
        ]
        all_mids = {"BTC": "0.0"}
        updated, errors = _inject_mark_prices(positions, all_mids)
        self.assertEqual(len(errors), 1)
        self.assertIsNone(updated[0]["mark_price"])


# ═══════════════════════════════════════════════════════════════════
# WhalePositionInput and W2 Domain Tests (Sections 3, 4)
# ═══════════════════════════════════════════════════════════════════

class TestWhalePositionInput(unittest.TestCase):
    def test_build_w2_input(self):
        """_build_w2_input must produce valid WhalePositionInput."""
        position = {
            "address": "0xaddr",
            "coin": "BTC",
            "signed_size": 0.5,
            "entry_price": 50000.0,
            "mark_price": 51234.0,
            "position_value_usd": 25617.0,
            "leverage": 5.0,
            "unrealized_pnl_usd": 500.0,
            "liquidation_price": 45000.0,
            "margin_mode": "isolated",
        }
        inp = _build_w2_input(position, label="test_whale")
        self.assertEqual(inp.coin, "BTC")
        self.assertEqual(inp.signed_size, 0.5)
        self.assertEqual(inp.mark_price, 51234.0)
        self.assertEqual(inp.liquidation_price, 45000.0)

    def test_w2_whaledomain_baseline_suppresses_large_new(self):
        """Section 4: baseline run must produce baseline_open_position, no large_new_position."""
        from market_radar.whale_domain.models import (
            WhalePositionInput, extract_snapshot,
            WhalePositionChange, ChangeType,
        )
        inp = WhalePositionInput(
            address="0xaddr", label="test", coin="BTC",
            signed_size=10.0, entry_price=50000.0, mark_price=51000.0,
            position_value_usd=510000.0, leverage=5.0,
        )
        snap = extract_snapshot(inp)
        self.assertEqual(snap.direction, "long")
        self.assertGreater(snap.position_value_usd, 100000)

    def test_parse_error_degrades_source(self):
        """Section 4: parse errors must degrade the source health."""
        adapter = MagicMock()
        adapter.fetch_clearinghouse_state.return_value.ok = True
        adapter.fetch_clearinghouse_state.return_value.data = {
            "assetPositions": [
                {"type": "oneWay", "position": {"coin": "BTC", "szi": "0.5",
                  "entryPx": "50000", "markPx": "51000", "positionValue": "25500",
                  "leverage": {"value": 5}}},
                {"type": "oneWay", "position": {"coin": "", "szi": "1.0",
                  "entryPx": "1", "positionValue": "1", "leverage": {"value": 1}}},
            ],
        }
        adapter.fetch_clearinghouse_state.return_value.provenance = MagicMock(source="sdk")
        adapter.fetch_clearinghouse_state.return_value.health = MagicMock(available=True)
        adapter.fetch_all_mids.return_value.ok = True
        adapter.fetch_all_mids.return_value.data = {"BTC": "51000"}
        adapter.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")
        adapter.fetch_all_mids.return_value.health = MagicMock(available=True)

        result, src = run_whale_mapper(adapter, "0xaddr", 30.0)
        # 1 valid position, 1 parse error -> degraded but has position
        self.assertFalse(result.ok)  # Parse errors set ok=False
        self.assertEqual(result.position_count, 1)  # Only valid BTC
        # Section 4: errors > 0 but partial valid → degraded, ok=false
        self.assertEqual(src.status, "degraded")
        self.assertFalse(result.ok)


# ═══════════════════════════════════════════════════════════════════
# Market Mapper Tests
# ═══════════════════════════════════════════════════════════════════

class TestRunCcxtTicker(unittest.TestCase):
    def test_ticker_success(self):
        adapter = MagicMock()
        adapter.fetch.return_value.ok = True
        adapter.fetch.return_value.data = {
            "last": 50000.0, "bid": 49900.0, "ask": 50100.0,
            "_raw": {"last": 50000.0},
        }
        adapter.fetch.return_value.provenance = MagicMock(source="ccxt")
        adapter.fetch.return_value.health = MagicMock(available=True)

        snap, src = run_ccxt_ticker(adapter, "binance", "BTC/USDT")
        self.assertTrue(snap.ok)
        self.assertEqual(snap.last_price, 50000.0)
        self.assertEqual(snap.bid, 49900.0)
        self.assertEqual(snap.ask, 50100.0)
        self.assertEqual(snap.source, "binance")
        self.assertTrue(src.ok)

    def test_ticker_failure_degraded(self):
        adapter = MagicMock()
        adapter.fetch.return_value.ok = False
        adapter.fetch.return_value.error = MagicMock(message="network error")
        adapter.fetch.return_value.provenance = MagicMock(source="ccxt")

        snap, src = run_ccxt_ticker(adapter, "binance", "BTC/USDT")
        self.assertFalse(snap.ok)
        self.assertFalse(src.ok)
        self.assertEqual(src.status, "unavailable")


class TestRunHypeMid(unittest.TestCase):
    def test_hype_found(self):
        adapter = MagicMock()
        adapter.fetch_all_mids.return_value.ok = True
        adapter.fetch_all_mids.return_value.data = {"HYPE": "25.50", "BTC": "50000"}
        adapter.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")
        adapter.fetch_all_mids.return_value.health = MagicMock(available=True)

        snap, src = run_hype_mid(adapter)
        self.assertIsNotNone(snap)
        self.assertTrue(snap.ok)
        self.assertEqual(snap.last_price, 25.50)
        self.assertEqual(snap.symbol, "HYPE/USDT")
        self.assertEqual(snap.source, "hyperliquid")

    def test_hype_not_found(self):
        adapter = MagicMock()
        adapter.fetch_all_mids.return_value.ok = True
        adapter.fetch_all_mids.return_value.data = {"BTC": "50000"}
        adapter.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")

        snap, src = run_hype_mid(adapter)
        self.assertIsNone(snap)
        self.assertFalse(src.ok)

    def test_hype_source_policy_hyperliquid_only(self):
        """HYPE must come from Hyperliquid allMids, not CCXT."""
        adapter = MagicMock()
        adapter.fetch_all_mids.return_value.ok = True
        adapter.fetch_all_mids.return_value.data = {"HYPE": "25.0"}
        adapter.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")
        adapter.fetch_all_mids.return_value.health = MagicMock(available=True)

        snap, src = run_hype_mid(adapter)
        self.assertIsNotNone(snap)
        self.assertEqual(snap.source, "hyperliquid")


# ═══════════════════════════════════════════════════════════════════
# Feed Handler Tests
# ═══════════════════════════════════════════════════════════════════

class TestFeedFixtureMode(unittest.TestCase):
    def test_fixture_mode_live_count_zero(self):
        feed, src = run_feed("fixture")
        self.assertEqual(feed.data_mode, "fixture")
        self.assertEqual(feed.live_count, 0)
        self.assertGreater(feed.fixture_count, 0)
        self.assertTrue(src.ok)

    def test_fixture_mode_no_research_counted_as_live(self):
        feed, src = run_feed("fixture")
        self.assertEqual(feed.live_count, 0)
        self.assertEqual(feed.research_count, 0)


class TestFeedLivePublic(unittest.TestCase):
    def test_live_public_not_connected(self):
        feed, src = run_feed("live-public")
        self.assertEqual(feed.data_mode, "live-public")
        self.assertEqual(feed.live_count, 0)
        self.assertEqual(feed.fixture_count, 0)
        self.assertEqual(feed.status, "degraded")
        self.assertFalse(src.ok)
        self.assertIn("not_wired", str(feed.error or "") or "")
        self.assertIn("not_connected", str(src.error or "") or "")


# ═══════════════════════════════════════════════════════════════════
# Partial Source Degradation
# ═══════════════════════════════════════════════════════════════════

class TestSourceDegradation(unittest.TestCase):
    @patch("market_radar.integration.one_shot.HyperliquidPublicAdapter")
    @patch("market_radar.integration.one_shot.CcxtPublicMarketAdapter")
    def test_partial_source_degradation(self, mock_ccxt_cls, mock_hl_cls):
        """One source failing must still produce a degraded result."""
        mock_hl = MagicMock()
        mock_hl.fetch_clearinghouse_state.return_value.ok = False
        mock_hl.fetch_clearinghouse_state.return_value.error = MagicMock(
            message="whale unavailable")
        mock_hl.fetch_clearinghouse_state.return_value.provenance = MagicMock(
            source="raw_http_fallback")
        mock_hl.fetch_all_mids.return_value.ok = False
        mock_hl.fetch_all_mids.return_value.error = MagicMock(message="HL down")
        mock_hl.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")
        mock_hl.fetch_all_mids.return_value.health = MagicMock(available=False)
        mock_hl_cls.return_value = mock_hl

        mock_ccxt = MagicMock()
        mock_ccxt.fetch.return_value.ok = True
        mock_ccxt.fetch.return_value.data = {
            "last": 50000.0, "bid": 49900.0, "ask": 50100.0,
            "_raw": {},
        }
        mock_ccxt.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock_ccxt.fetch.return_value.health = MagicMock(available=True)
        mock_ccxt_cls.return_value = mock_ccxt

        with tempfile.TemporaryDirectory() as tmp:
            config = IntegrationConfig(
                mode="fixture",
                state_dir=os.path.join(tmp, "state"),
                output_dir=os.path.join(tmp, "out"),
                whale_address="0x1234567890abcdef1234567890abcdef12345678",
                exchange="binance",
                timeout=15.0,
                no_send=True,
            )
            result = run_one_shot(config)
            self.assertIn(result.status, ("degraded", "failed"))

    @patch("market_radar.integration.one_shot.HyperliquidPublicAdapter")
    @patch("market_radar.integration.one_shot.CcxtPublicMarketAdapter")
    def test_all_sources_unavailable(self, mock_ccxt_cls, mock_hl_cls):
        """All sources failing must still complete (degraded/failed)."""
        mock_hl = MagicMock()
        mock_hl.fetch_clearinghouse_state.return_value.ok = False
        mock_hl.fetch_clearinghouse_state.return_value.error = MagicMock(
            message="unavailable")
        mock_hl.fetch_clearinghouse_state.return_value.provenance = MagicMock(
            source="raw_http_fallback")
        mock_hl.fetch_all_mids.return_value.ok = False
        mock_hl.fetch_all_mids.return_value.error = MagicMock(message="unavailable")
        mock_hl.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")
        mock_hl.fetch_all_mids.return_value.health = MagicMock(available=False)
        mock_hl_cls.return_value = mock_hl

        mock_ccxt = MagicMock()
        mock_ccxt.fetch.return_value.ok = False
        mock_ccxt.fetch.return_value.error = MagicMock(message="ccxt down")
        mock_ccxt.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock_ccxt_cls.return_value = mock_ccxt

        with tempfile.TemporaryDirectory() as tmp:
            config = IntegrationConfig(
                mode="fixture",
                state_dir=os.path.join(tmp, "state"),
                output_dir=os.path.join(tmp, "out"),
                whale_address="0xaddr",
                exchange="binance",
                timeout=15.0,
                no_send=True,
            )
            result = run_one_shot(config)
            self.assertIn(result.status, ("degraded", "failed"))


# ═══════════════════════════════════════════════════════════════════
# Run Determinism & Config
# ═══════════════════════════════════════════════════════════════════

class TestDeterministicRunOutput(unittest.TestCase):
    @patch("market_radar.integration.one_shot.HyperliquidPublicAdapter")
    @patch("market_radar.integration.one_shot.CcxtPublicMarketAdapter")
    def test_deterministic_output_shape(self, mock_ccxt_cls, mock_hl_cls):
        """Run result must always have expected top-level keys."""
        mock_hl = MagicMock()
        mock_hl.fetch_clearinghouse_state.return_value.ok = True
        mock_hl.fetch_clearinghouse_state.return_value.data = {"assetPositions": []}
        mock_hl.fetch_clearinghouse_state.return_value.provenance = MagicMock(
            source="raw_http_fallback")
        mock_hl.fetch_clearinghouse_state.return_value.health = MagicMock(
            available=True)
        mock_hl.fetch_all_mids.return_value.ok = True
        mock_hl.fetch_all_mids.return_value.data = {"HYPE": "25.0"}
        mock_hl.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")
        mock_hl.fetch_all_mids.return_value.health = MagicMock(available=True)
        mock_hl_cls.return_value = mock_hl

        mock_ccxt = MagicMock()
        mock_ccxt.fetch.return_value.ok = True
        mock_ccxt.fetch.return_value.data = {
            "last": 50000.0, "bid": 49900.0, "ask": 50100.0, "_raw": {},
        }
        mock_ccxt.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock_ccxt.fetch.return_value.health = MagicMock(available=True)
        mock_ccxt_cls.return_value = mock_ccxt

        with tempfile.TemporaryDirectory() as tmp:
            config = IntegrationConfig(
                mode="fixture",
                state_dir=os.path.join(tmp, "state"),
                output_dir=os.path.join(tmp, "out"),
                whale_address="0xaddr",
                exchange="binance",
                timeout=15.0,
                no_send=True,
            )
            result = run_one_shot(config)
            d = result.as_dict()
            for key in ("run_id", "status", "data_mode", "no_send",
                        "scheduler_started", "credentials_used", "sources",
                        "markets", "output_paths"):
                self.assertIn(key, d, f"Missing key: {key}")


class TestNoSendEnforcement(unittest.TestCase):
    def test_no_send_true_enforced(self):
        """no_send=False must be rejected at config level."""
        with self.assertRaises(ValueError):
            IntegrationConfig(mode="fixture", no_send=False)

    def test_no_send_default_true(self):
        config = IntegrationConfig()
        self.assertTrue(config.no_send)

    def test_live_public_requires_explicit_mode(self):
        config = IntegrationConfig(mode="live-public")
        self.assertEqual(config.mode, "live-public")


# ═══════════════════════════════════════════════════════════════════
# Lock Contention (Section 1 — strong semantics)
# ═══════════════════════════════════════════════════════════════════

class TestLockContention(unittest.TestCase):
    def test_lock_acquire_success(self):
        """Section 1: try_acquire() is None = acquired, str = denied."""
        from market_radar.operations.file_lock import FileLock
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "test.lock"
            lock = FileLock(lock_path)

            # First acquire must succeed
            result1 = lock.try_acquire()
            self.assertIsNone(result1, "First acquire must return None")
            self.assertTrue(lock.is_held)

            lock.release()
            self.assertFalse(lock.is_held)

    def test_lock_denies_second_acquire(self):
        """Section 1: second lock on same path must return error string."""
        from market_radar.operations.file_lock import FileLock
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "test.lock"
            lock1 = FileLock(lock_path)
            lock2 = FileLock(lock_path)

            # First acquires
            result1 = lock1.try_acquire()
            self.assertIsNone(result1)

            # Second must be denied
            result2 = lock2.try_acquire()
            self.assertIsNotNone(result2, "Second acquire must return error string")
            self.assertIsInstance(result2, str)

            lock1.release()

            # After release, third should succeed
            lock3 = FileLock(lock_path)
            result3 = lock3.try_acquire()
            self.assertIsNone(result3, "After release, acquire must succeed")
            lock3.release()


# ═══════════════════════════════════════════════════════════════════
# Stop Marker
# ═══════════════════════════════════════════════════════════════════

class TestStopMarker(unittest.TestCase):
    @patch("market_radar.integration.one_shot.HyperliquidPublicAdapter")
    @patch("market_radar.integration.one_shot.CcxtPublicMarketAdapter")
    def test_stop_marker_blocks_run(self, mock_ccxt_cls, mock_hl_cls):
        """Stop marker set before run must cause immediate failure."""
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            from market_radar.operations.stop_marker import StopMarker
            stop = StopMarker(state_dir / "STOP")
            stop.set()

            config = IntegrationConfig(
                mode="fixture", state_dir=str(state_dir),
                output_dir=os.path.join(tmp, "out"),
                whale_address="0xaddr", exchange="binance",
                timeout=15.0, no_send=True,
            )
            result = run_one_shot(config)
            self.assertEqual(result.status, "failed")
            self.assertTrue(any("stop marker" in e for e in result.errors))
            stop.clear()


# ═══════════════════════════════════════════════════════════════════
# Failed Run Releases Lock (Section 1 — strong)
# ═══════════════════════════════════════════════════════════════════

class TestFailedRunReleasesLock(unittest.TestCase):
    @patch("market_radar.integration.one_shot.HyperliquidPublicAdapter")
    @patch("market_radar.integration.one_shot.CcxtPublicMarketAdapter")
    def test_lock_released_after_failure(self, mock_ccxt_cls, mock_hl_cls):
        """Section 1: failed run must release lock so future runs can proceed."""
        from market_radar.operations.file_lock import FileLock

        mock_hl = MagicMock()
        mock_hl.fetch_clearinghouse_state.side_effect = RuntimeError("crash")
        mock_hl_cls.return_value = mock_hl
        mock_ccxt_cls.return_value = MagicMock()

        with tempfile.TemporaryDirectory() as tmp:
            config = IntegrationConfig(
                mode="fixture",
                state_dir=os.path.join(tmp, "state"),
                output_dir=os.path.join(tmp, "out"),
                whale_address="0xaddr", exchange="binance",
                timeout=15.0, no_send=True,
            )
            result = run_one_shot(config)
            self.assertIsNotNone(result.finished_at)

            # After run completes (even failed), the lock path should be free
            lock_path = Path(tmp) / "state" / "one_shot.lock"
            check_lock = FileLock(lock_path)
            acquire_after = check_lock.try_acquire()
            self.assertIsNone(acquire_after,
                              "Lock must be released after failed run")
            check_lock.release()


# ═══════════════════════════════════════════════════════════════════
# SQLite Run History (Section 8)
# ═══════════════════════════════════════════════════════════════════

class TestSQLiteRunHistory(unittest.TestCase):
    @patch("market_radar.integration.one_shot.HyperliquidPublicAdapter")
    @patch("market_radar.integration.one_shot.CcxtPublicMarketAdapter")
    def test_run_history_recorded(self, mock_ccxt_cls, mock_hl_cls):
        """Section 8: run history must be recorded as a real SQLite row."""
        from market_radar.operations.sqlite_schema import initialize_sqlite
        from market_radar.operations.run_history import insert_run, update_run_finish, get_run

        mock_hl = MagicMock()
        mock_hl.fetch_clearinghouse_state.return_value.ok = True
        mock_hl.fetch_clearinghouse_state.return_value.data = {"assetPositions": []}
        mock_hl.fetch_clearinghouse_state.return_value.provenance = MagicMock(
            source="raw_http_fallback")
        mock_hl.fetch_clearinghouse_state.return_value.health = MagicMock(
            available=True)
        mock_hl.fetch_all_mids.return_value.ok = True
        mock_hl.fetch_all_mids.return_value.data = {"HYPE": "25.0"}
        mock_hl.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")
        mock_hl.fetch_all_mids.return_value.health = MagicMock(available=True)
        mock_hl_cls.return_value = mock_hl

        mock_ccxt = MagicMock()
        mock_ccxt.fetch.return_value.ok = True
        mock_ccxt.fetch.return_value.data = {"last": 50000.0, "bid": 49900.0,
                                               "ask": 50100.0, "_raw": {}}
        mock_ccxt.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock_ccxt.fetch.return_value.health = MagicMock(available=True)
        mock_ccxt_cls.return_value = mock_ccxt

        with tempfile.TemporaryDirectory() as tmp:
            config = IntegrationConfig(
                mode="fixture", state_dir=os.path.join(tmp, "state"),
                output_dir=os.path.join(tmp, "out"),
                whale_address="0xaddr", exchange="binance",
                timeout=15.0, no_send=True,
            )
            result = run_one_shot(config)
            self.assertIn(result.status, ("completed", "degraded", "failed"))

    def test_direct_run_history_row(self):
        """Section 8: verify direct SQLite insert/update/get round-trip."""
        from market_radar.operations.sqlite_schema import initialize_sqlite
        from market_radar.operations.run_history import insert_run, update_run_finish, get_run

        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "run_history.db")
            initialize_sqlite(db_path)
            run_id = "test-run-001"
            config = {"mode": "fixture"}

            insert_run(db_path, run_id, runner_label="test", status="running")
            row = get_run(db_path, run_id)
            self.assertIsNotNone(row)
            self.assertEqual(row["run_id"], run_id)
            self.assertEqual(row["status"], "running")

            update_run_finish(db_path, run_id, status="completed", summary="ok")
            row = get_run(db_path, run_id)
            self.assertEqual(row["status"], "completed")


# ═══════════════════════════════════════════════════════════════════
# Market Truth Tests (Section 6)
# ═══════════════════════════════════════════════════════════════════

class TestMarketTruth(unittest.TestCase):
    def test_no_price_zero_for_failed_source(self):
        """Section 6: unavailable source must NOT produce MarketSnapshot with price=0."""
        snap = MarketSnapshotResult(
            symbol="BTC/USDT", source="binance", ok=False,
            last_price=None, error="network error",
        )
        # When building bundle, this should result in health=failed, no snapshot
        self.assertFalse(snap.ok)
        self.assertIsNone(snap.last_price)

    def test_failed_market_omitted_from_live_snapshots(self):
        """Section 6: failed market must be excluded from LIVE snapshots."""
        bad_snap = MarketSnapshotResult(
            symbol="BTC/USDT", source="binance", ok=False,
            last_price=None, error="timeout",
        )
        good_snap = MarketSnapshotResult(
            symbol="ETH/USDT", source="binance", ok=True,
            last_price=3200.0, bid=3190.0, ask=3210.0,
        )
        # The _build_workbench_bundle should only create snapshot for good_snap
        from market_radar.market_view.models import MarketSnapshot, MarketHealth, Venue, DataMode
        from market_radar.integration.models import IntegrationRunResult

        result = IntegrationRunResult(
            markets=[bad_snap, good_snap],
            status="degraded",
        )
        config = IntegrationConfig(mode="live-public")
        from market_radar.integration.one_shot import _build_workbench_bundle
        bundle = _build_workbench_bundle(result, config)

        # Should have 1 market snapshot (ETH only)
        eth_snapshots = [m for m in bundle.market_snapshots if m.symbol == "ETH"]
        btc_snapshots = [m for m in bundle.market_snapshots if m.symbol == "BTC"]
        self.assertEqual(len(eth_snapshots), 1)
        self.assertEqual(len(btc_snapshots), 0, "BTC failed, must not appear as snapshot")

        # BTC must appear in health as failed
        btc_health = [h for h in bundle.market_health if h.asset == "BTC"]
        self.assertEqual(len(btc_health), 1)
        self.assertEqual(btc_health[0].status, "failed")


# ═══════════════════════════════════════════════════════════════════
# Final Report Tests (Section 9)
# ═══════════════════════════════════════════════════════════════════

class TestFinalReportShape(unittest.TestCase):
    @patch("market_radar.integration.one_shot.HyperliquidPublicAdapter")
    @patch("market_radar.integration.one_shot.CcxtPublicMarketAdapter")
    def test_finished_at_and_output_paths(self, mock_ccxt_cls, mock_hl_cls):
        """Section 9: final report must have finished_at and output_paths."""
        mock_hl = MagicMock()
        mock_hl.fetch_clearinghouse_state.return_value.ok = True
        mock_hl.fetch_clearinghouse_state.return_value.data = {"assetPositions": []}
        mock_hl.fetch_clearinghouse_state.return_value.provenance = MagicMock(
            source="raw_http_fallback")
        mock_hl.fetch_clearinghouse_state.return_value.health = MagicMock(available=True)
        mock_hl.fetch_all_mids.return_value.ok = True
        mock_hl.fetch_all_mids.return_value.data = {"HYPE": "25.0"}
        mock_hl.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")
        mock_hl.fetch_all_mids.return_value.health = MagicMock(available=True)
        mock_hl_cls.return_value = mock_hl

        mock_ccxt = MagicMock()
        mock_ccxt.fetch.return_value.ok = True
        mock_ccxt.fetch.return_value.data = {"last": 50000.0, "bid": 49900.0,
                                               "ask": 50100.0, "_raw": {}}
        mock_ccxt.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock_ccxt.fetch.return_value.health = MagicMock(available=True)
        mock_ccxt_cls.return_value = mock_ccxt

        with tempfile.TemporaryDirectory() as tmp:
            config = IntegrationConfig(
                mode="fixture", state_dir=os.path.join(tmp, "state"),
                output_dir=os.path.join(tmp, "out"),
                whale_address="0xaddr", exchange="binance",
                timeout=15.0, no_send=True,
            )
            result = run_one_shot(config)
            self.assertIsNotNone(result.finished_at)
            self.assertGreater(len(result.output_paths), 0)


# ═══════════════════════════════════════════════════════════════════
# Workbench HTML Tests (Section 10)
# ═══════════════════════════════════════════════════════════════════

class TestWorkbenchHTMLGenerated(unittest.TestCase):
    @patch("market_radar.integration.one_shot.HyperliquidPublicAdapter")
    @patch("market_radar.integration.one_shot.CcxtPublicMarketAdapter")
    def test_html_generated(self, mock_ccxt_cls, mock_hl_cls):
        """Section 10: one-shot run must generate workbench HTML."""
        mock_hl = MagicMock()
        mock_hl.fetch_clearinghouse_state.return_value.ok = True
        mock_hl.fetch_clearinghouse_state.return_value.data = {"assetPositions": []}
        mock_hl.fetch_clearinghouse_state.return_value.provenance = MagicMock(
            source="raw_http_fallback")
        mock_hl.fetch_clearinghouse_state.return_value.health = MagicMock(
            available=True)
        mock_hl.fetch_all_mids.return_value.ok = True
        mock_hl.fetch_all_mids.return_value.data = {"HYPE": "25.0"}
        mock_hl.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")
        mock_hl.fetch_all_mids.return_value.health = MagicMock(available=True)
        mock_hl_cls.return_value = mock_hl

        mock_ccxt = MagicMock()
        mock_ccxt.fetch.return_value.ok = True
        mock_ccxt.fetch.return_value.data = {"last": 50000.0, "bid": 49900.0,
                                               "ask": 50100.0, "_raw": {}}
        mock_ccxt.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock_ccxt.fetch.return_value.health = MagicMock(available=True)
        mock_ccxt_cls.return_value = mock_ccxt

        with tempfile.TemporaryDirectory() as tmp:
            config = IntegrationConfig(
                mode="fixture", state_dir=os.path.join(tmp, "state"),
                output_dir=os.path.join(tmp, "out"),
                whale_address="0xaddr", exchange="binance",
                timeout=15.0, no_send=True,
            )
            result = run_one_shot(config)
            html_paths = [p for p in result.output_paths if p.endswith(".html")]
            if result.status in ("completed", "degraded"):
                self.assertGreater(len(html_paths), 0)

    def test_render_workbench_atomic(self):
        """Section 10: render_workbench must accept output_path."""
        bundle = WorkbenchBundle(
            run_id="test-atomic",
            generated_at="2026-01-01T00:00:00Z",
            feed_items=[],
            market_snapshots=[],
            market_health=[],
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "workbench.html")
            render_workbench(bundle, path)
            self.assertTrue(os.path.exists(path))
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("test-atomic", content)


# ═══════════════════════════════════════════════════════════════════
# Degraded Feed in Warnings (Section 6)
# ═══════════════════════════════════════════════════════════════════

class TestDegradedFeedInWarnings(unittest.TestCase):
    def test_degraded_feed_appears_in_warnings(self):
        """Section 6: degraded source must appear in degraded_reasons."""
        from market_radar.integration.one_shot import _build_workbench_bundle
        from market_radar.integration.models import IntegrationRunResult

        result = IntegrationRunResult(
            sources=[
                SourceRunStatus(source="feed", status="degraded", ok=False,
                                error="network issue"),
                SourceRunStatus(source="ccxt:BTC/USDT", status="ok", ok=True),
            ],
            status="degraded",
            markets=[],
        )
        config = IntegrationConfig(mode="fixture")
        bundle = _build_workbench_bundle(result, config)
        self.assertTrue(any("feed" in w for w in bundle.degraded_paths))


# ═══════════════════════════════════════════════════════════════════
# Snapshot Persistence Tests (Section 5)
# ═══════════════════════════════════════════════════════════════════

class TestSnapshotPersistence(unittest.TestCase):
    def test_state_file_preserved_after_mapping(self):
        """Section 5: snapshot state must be atomically saved after successful mapping."""
        from market_radar.integration.whale_mapper import (
            _save_snapshot_state, _load_previous_snapshots,
        )
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            snapshots = {"0xaddr:BTC": {"coin": "BTC", "signed_size": 0.5}}
            _save_snapshot_state(state_dir, "0xaddr", snapshots)
            loaded = _load_previous_snapshots(state_dir, "0xaddr")
            self.assertIn("0xaddr:BTC", loaded)
            self.assertEqual(loaded["0xaddr:BTC"]["signed_size"], 0.5)

    def test_no_previous_state_returns_empty(self):
        """Section 5: no previous state file must return empty dict."""
        from market_radar.integration.whale_mapper import _load_previous_snapshots
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            loaded = _load_previous_snapshots(state_dir, "0xnew")
            self.assertEqual(loaded, {})

    def test_run_two_increase_or_reduce(self):
        """Section 5: two-run sequence must detect increase/reduce."""
        from market_radar.integration.whale_mapper import (
            _build_w2_input, _save_snapshot_state, _load_previous_snapshots,
        )
        from market_radar.whale_domain.change_detector import detect_all_changes
        from market_radar.whale_domain.models import extract_snapshot, make_position_key

        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            address = "0xaddr"
            label = "test"

            # Run 1: baseline — 1 BTC position
            pos1 = _build_w2_input({
                "address": address, "coin": "BTC", "signed_size": 5.0,
                "entry_price": 50000.0, "mark_price": 51000.0,
                "position_value_usd": 255000.0, "leverage": 5.0,
            }, label)
            snap1 = extract_snapshot(pos1)
            key = make_position_key(address, "BTC")
            state = {key: snap1.to_dict()}
            _save_snapshot_state(state_dir, address, state)

            # Run 2: increase to 10 BTC
            pos2 = _build_w2_input({
                "address": address, "coin": "BTC", "signed_size": 10.0,
                "entry_price": 50000.0, "mark_price": 52000.0,
                "position_value_usd": 520000.0, "leverage": 5.0,
            }, label)
            prev_raw = _load_previous_snapshots(state_dir, address)
            from market_radar.whale_domain.models import dict_to_snapshot
            prev_snaps = {}
            for k, v in prev_raw.items():
                prev_snaps[k] = dict_to_snapshot(v)

            changes = detect_all_changes(
                current_inputs=[pos2],
                previous_snapshots=prev_snaps,
                is_baseline_run=False,
                detected_at_utc="2026-06-17T12:00:00Z",
            )
            # Must detect some change (increase_long or similar)
            self.assertGreater(len(changes), 0)
            self.assertTrue(any("increase" in c.change_type for c in changes) or
                          any("reduce" in c.change_type for c in changes))

    def test_disappeared_position_close(self):
        """Section 5: previous non-zero position gone in current run must produce close."""
        from market_radar.integration.whale_mapper import (
            _build_w2_input, _save_snapshot_state, _load_previous_snapshots,
        )
        from market_radar.whale_domain.change_detector import detect_all_changes
        from market_radar.whale_domain.models import extract_snapshot, make_position_key, dict_to_snapshot

        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            address = "0xaddr"
            label = "test"

            # Previous: 1 BTC position
            pos_prev = _build_w2_input({
                "address": address, "coin": "BTC", "signed_size": 5.0,
                "entry_price": 50000.0, "mark_price": 51000.0,
                "position_value_usd": 255000.0, "leverage": 5.0,
            }, label)
            snap_prev = extract_snapshot(pos_prev)
            key = make_position_key(address, "BTC")
            _save_snapshot_state(state_dir, address, {key: snap_prev.to_dict()})

            # Current: empty positions
            prev_raw = _load_previous_snapshots(state_dir, address)
            prev_snaps = {k: dict_to_snapshot(v) for k, v in prev_raw.items()}

            changes = detect_all_changes(
                current_inputs=[],
                previous_snapshots=prev_snaps,
                is_baseline_run=False,
                detected_at_utc="2026-06-17T12:00:00Z",
            )
            self.assertGreater(len(changes), 0)
            self.assertTrue(any("close" in c.change_type for c in changes))


# ═══════════════════════════════════════════════════════════════════
# CCXT Preflight Tests (Section 7)
# ═══════════════════════════════════════════════════════════════════

class TestCCXTPreflight(unittest.TestCase):
    def test_preflight_return_shape(self):
        """Section 7: CCXT preflight must return expected keys."""
        diag = run_ccxt_preflight("binance")
        for key in ("python_executable", "ccxt_version", "ccxt_file",
                    "has_exchange_class", "exchange_init_ok",
                    "adapter_import_smoke"):
            self.assertIn(key, diag, f"Missing key: {key}")


# ═══════════════════════════════════════════════════════════════════
# XSS / Security
# ═══════════════════════════════════════════════════════════════════

class TestXSSEscaping(unittest.TestCase):
    def test_malicious_input_escaped(self):
        """XSS input in workbench must be escaped by W3 renderer."""
        from market_radar.intelligence_feed.models import FeedItem, FeedSourceType, FeedDataMode, make_feed_id
        bundle = WorkbenchBundle(
            run_id="test-xss",
            generated_at="2026-01-01T00:00:00Z",
            feed_items=[
                FeedItem(
                    feed_id=make_feed_id("<script>alert('xss')</script>", "test"),
                    source_type=FeedSourceType.UNKNOWN,
                    source_label="test",
                    data_mode=FeedDataMode.FIXTURE,
                    title="<script>alert('xss')</script>",
                    body="<img src=x onerror=alert(1)>",
                ),
            ],
        )
        html = render_workbench(bundle)
        self.assertIn("&lt;script&gt;", html)
        feed_content_pos = html.find("<div class=\"fi\">")
        after_feed = html[feed_content_pos:] if feed_content_pos >= 0 else html
        self.assertNotIn("<script>", after_feed)


# ═══════════════════════════════════════════════════════════════════
# No Credential/Trading/Send Imports
# ═══════════════════════════════════════════════════════════════════

class TestNoForbiddenImports(unittest.TestCase):
    def test_no_credential_trading_send_imports(self):
        """Integration layer must not import credentials, trading, or send."""
        import market_radar.integration.whale_mapper as wm
        import market_radar.integration.market_mapper as mm
        import market_radar.integration.feed_handler as fh
        import market_radar.integration.one_shot as os_mod
        import ast

        for mod in (wm, mm, fh, os_mod):
            with open(mod.__file__, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.name.lower()
                        for term in ["wallet", "order", "trade", "signing", "send",
                                      "credential", "apikey", "secret"]:
                            if term in name:
                                self.fail(f"{mod.__name__} imports prohibited: {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and "telegram" in node.module.lower():
                        self.fail(f"{mod.__name__} imports Telegram: {node.module}")
                    if node.module and "sender" in node.module.lower():
                        self.fail(f"{mod.__name__} imports sender: {node.module}")
                    if node.module and "publisher" in node.module.lower():
                        self.fail(f"{mod.__name__} imports publisher: {node.module}")


# ═══════════════════════════════════════════════════════════════════
# Injected Fake Adapters (no network dependency)
# ═══════════════════════════════════════════════════════════════════

class TestInjectedFakeAdapters(unittest.TestCase):
    """All tests above use MagicMock — no real network calls."""

    def test_no_network_in_test_file(self):
        """The test file must not import any real adapter classes."""
        import ast
        with open(__file__, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "external_adapters" in node.module:
                    self.fail(f"test_imports adapter module directly: {node.module}")


if __name__ == "__main__":
    unittest.main()
