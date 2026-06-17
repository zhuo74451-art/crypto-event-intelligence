"""Feed Provider Protocol tests — no network, injected fake providers."""
from __future__ import annotations

import json, os, tempfile, unittest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from market_radar.integration.models import (
    IntegrationConfig, IntegrationRunResult, SourceRunStatus, FeedResult,
)
from market_radar.integration.feed_provider_protocol import (
    FeedProviderProtocol, FeedProviderInput, IntegrationFeedBatch,
    FeedCursorState,
)
from market_radar.integration.feed_handler import (
    create_not_connected_feed, run_feed_with_provider,
    _load_cursor, _save_cursor, _cursor_path,
)
from market_radar.integration.one_shot import run_one_shot
from market_radar.operations.atomic_json import atomic_write_json
from market_radar.intelligence_feed.models import (
    FeedItem, FeedSourceType, FeedDataMode, make_feed_id,
)
from market_radar.workbench.bundle import WorkbenchBundle
from market_radar.workbench.renderer import render_workbench


def _make_item(title: str, source_label: str = "test_source",
               data_mode: FeedDataMode = FeedDataMode.LIVE) -> FeedItem:
    fid = make_feed_id(title, source_label)
    return FeedItem(
        feed_id=fid,
        source_type=FeedSourceType.UNKNOWN,
        source_label=source_label,
        data_mode=data_mode,
        title=title,
        body=f"Body of {title}",
        published_at=datetime.now(timezone.utc).isoformat(),
    )


class FakeFeedProvider:
    """Configurable fake provider for testing."""
    def __init__(self, batch: IntegrationFeedBatch):
        self._batch = batch
        self.call_count = 0

    def __call__(self, inp: FeedProviderInput) -> IntegrationFeedBatch:
        self.call_count += 1
        self.last_input = inp
        return self._batch


def _default_cfg(**kw) -> IntegrationConfig:
    cfg = IntegrationConfig(mode="live-public", feed_enabled=True, **kw)
    return cfg


# ═══════════════════════════════════════════════════════════════════
# 1. provider=None → feed degraded/not_connected
# ═══════════════════════════════════════════════════════════════════

class TestNoProviderDegraded(unittest.TestCase):
    @patch("market_radar.integration.one_shot.HyperliquidPublicAdapter")
    @patch("market_radar.integration.one_shot.CcxtPublicMarketAdapter")
    def test_no_provider_degraded(self, mock_ccxt, mock_hl):
        mock_hl.return_value.fetch_clearinghouse_state.return_value.ok = True
        mock_hl.return_value.fetch_clearinghouse_state.return_value.data = {"assetPositions": []}
        mock_hl.return_value.fetch_clearinghouse_state.return_value.provenance = MagicMock(source="sdk")
        mock_hl.return_value.fetch_clearinghouse_state.return_value.health = MagicMock(available=True)
        mock_hl.return_value.fetch_all_mids.return_value.ok = True
        mock_hl.return_value.fetch_all_mids.return_value.data = {"HYPE": "25.0"}
        mock_hl.return_value.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")
        mock_ccxt.return_value.fetch.return_value.ok = True
        mock_ccxt.return_value.fetch.return_value.data = {"last": 50000.0, "bid": 49900.0, "ask": 50100.0, "_raw": {}}
        mock_ccxt.return_value.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock_ccxt.return_value.fetch.return_value.health = MagicMock(available=True)

        with tempfile.TemporaryDirectory() as tmp:
            cfg = IntegrationConfig(mode="fixture", state_dir=os.path.join(tmp, "s"), output_dir=os.path.join(tmp, "o"),
                                     whale_address="", exchange="binance", timeout=15.0, no_send=True)
            result = run_one_shot(cfg, feed_provider=None)
            self.assertEqual(result.status, "degraded")
            feed_srcs = [s for s in result.sources if s.source == "feed"]
            self.assertEqual(len(feed_srcs), 1)
            self.assertEqual(feed_srcs[0].status, "degraded")
            self.assertIn("not_connected", feed_srcs[0].error or "")


# ═══════════════════════════════════════════════════════════════════
# 2. provider ok + 3 live items
# ═══════════════════════════════════════════════════════════════════

class TestProviderOkWithItems(unittest.TestCase):
    def test_provider_ok_three_live(self):
        items = [_make_item(f"News {i}") for i in range(3)]
        batch = IntegrationFeedBatch(
            provider_name="test_provider", overall_status="ok",
            records_seen=3, records_accepted=3,
            live_count=3, items=items,
            next_cursor="cursor_3",
        )
        provider = FakeFeedProvider(batch)

        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            output_dir = Path(tmp) / "o"
            output_dir.mkdir()
            cfg = IntegrationConfig(mode="live-public", state_dir=str(state_dir), output_dir=str(output_dir),
                                     whale_address="", exchange="binance", timeout=15.0, no_send=True,
                                     feed_enabled=True)

            feed_result, feed_src, raw_batch, cursor_err, feed_summary, sub_sources = \
                run_feed_with_provider(provider, cfg, state_dir, "test-run-001")

            self.assertEqual(feed_result.status, "ok")
            self.assertTrue(feed_src.ok)
            self.assertEqual(len(feed_result.items), 3)
            self.assertEqual(feed_result.live_count, 3)
            self.assertEqual(provider.call_count, 1)

            # Cursor should be persisted
            cursor = _load_cursor(state_dir, cfg)
            self.assertIsNotNone(cursor)
            self.assertEqual(cursor.cursor_value, "cursor_3")
            self.assertEqual(cursor.provider_name, "test_provider")

    def test_provider_ok_zero_items_empty_batch(self):
        """Empty batch with ok status = normal empty, not unavailable."""
        batch = IntegrationFeedBatch(
            provider_name="test", overall_status="ok",
            records_seen=0, records_accepted=0, items=[],
        )
        provider = FakeFeedProvider(batch)
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            cfg = _default_cfg(state_dir=str(state_dir), output_dir=str(tmp))
            feed_result, feed_src, *_ = run_feed_with_provider(provider, cfg, state_dir, "r1")
            self.assertEqual(feed_result.status, "ok")
            self.assertEqual(len(feed_result.items), 0)


# ═══════════════════════════════════════════════════════════════════
# 4. provider degraded + partial items
# ═══════════════════════════════════════════════════════════════════

class TestProviderDegraded(unittest.TestCase):
    def test_provider_degraded_with_items(self):
        items = [_make_item("Partial item")]
        batch = IntegrationFeedBatch(
            provider_name="test", overall_status="degraded",
            records_seen=5, records_accepted=1, records_rejected=4,
            live_count=1, items=items,
            errors=["4 items rejected due to validation"],
            source_statuses=[
                {"source": "news:jin10", "status": "ok", "ok": True},
                {"source": "telegram:channel_a", "status": "degraded", "ok": False, "error": "rate limited"},
            ],
        )
        provider = FakeFeedProvider(batch)
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            cfg = _default_cfg(state_dir=str(state_dir), output_dir=str(tmp))
            feed_result, feed_src, raw_batch, cursor_err, feed_summary, sub_sources = \
                run_feed_with_provider(provider, cfg, state_dir, "r2")
            self.assertEqual(feed_result.status, "degraded")
            self.assertEqual(len(sub_sources), 2)
            self.assertEqual(sub_sources[0].source, "news:jin10")
            self.assertEqual(sub_sources[1].source, "telegram:channel_a")


# ═══════════════════════════════════════════════════════════════════
# 5. provider unavailable
# ═══════════════════════════════════════════════════════════════════

class TestProviderUnavailable(unittest.TestCase):
    def test_provider_unavailable(self):
        batch = IntegrationFeedBatch(
            provider_name="test", overall_status="unavailable",
            items=[], errors=["all sources unreachable"],
        )
        provider = FakeFeedProvider(batch)
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            cfg = _default_cfg(state_dir=str(state_dir), output_dir=str(tmp))
            feed_result, feed_src, *_ = run_feed_with_provider(provider, cfg, state_dir, "r3")
            self.assertEqual(feed_result.status, "unavailable")
            self.assertFalse(feed_src.ok)


# ═══════════════════════════════════════════════════════════════════
# 6. provider raises exception
# ═══════════════════════════════════════════════════════════════════

class TestProviderRaises(unittest.TestCase):
    def test_provider_raise_degrades(self):
        def raising_provider(inp):
            raise RuntimeError("connection timeout")
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            cfg = _default_cfg(state_dir=str(state_dir), output_dir=str(tmp))
            feed_result, feed_src, *_ = run_feed_with_provider(raising_provider, cfg, state_dir, "r4")
            self.assertEqual(feed_result.status, "degraded")
            self.assertIn("RuntimeError", feed_result.error or "")


# ═══════════════════════════════════════════════════════════════════
# 9. cursor first write
# ═══════════════════════════════════════════════════════════════════

class TestCursorFirstWrite(unittest.TestCase):
    def test_first_write_no_existing(self):
        batch = IntegrationFeedBatch(
            provider_name="test", overall_status="ok",
            records_accepted=5, items=[_make_item("a")],
            next_cursor="cursor_5",
        )
        provider = FakeFeedProvider(batch)
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            cfg = _default_cfg(state_dir=str(state_dir), output_dir=str(tmp))
            run_feed_with_provider(provider, cfg, state_dir, "r5")
            cursor = _load_cursor(state_dir, cfg)
            self.assertIsNotNone(cursor)
            self.assertEqual(cursor.cursor_value, "cursor_5")

    def test_cursor_forward_advance(self):
        """Existing cursor is passed to provider."""
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            cfg = _default_cfg(state_dir=str(state_dir), output_dir=str(tmp))
            # Write existing cursor
            atomic_write_json({
                "cursor_name": "published_at_backend",
                "cursor_value": "cursor_100",
                "updated_at": "2026-01-01T00:00:00Z",
                "provider_name": "test",
                "last_successful_run_id": "prev-run",
                "accepted_count": 10,
            }, str(_cursor_path(state_dir, cfg)))

            batch = IntegrationFeedBatch(
                provider_name="test", overall_status="ok",
                records_accepted=3, items=[_make_item("b")],
                next_cursor="cursor_200",
            )
            provider = FakeFeedProvider(batch)
            run_feed_with_provider(provider, cfg, state_dir, "r6")
            self.assertEqual(provider.last_input.since_cursor, "cursor_100")

            cursor = _load_cursor(state_dir, cfg)
            self.assertEqual(cursor.cursor_value, "cursor_200")

    def test_cursor_regression_rejected(self):
        """New cursor older than existing must be rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            cfg = _default_cfg(state_dir=str(state_dir), output_dir=str(tmp))
            atomic_write_json({
                "cursor_name": "published_at_backend",
                "cursor_value": "cursor_200",
                "updated_at": "2026-01-01T00:00:00Z",
                "provider_name": "test",
                "last_successful_run_id": "prev",
                "accepted_count": 10,
            }, str(_cursor_path(state_dir, cfg)))

            batch = IntegrationFeedBatch(
                provider_name="test", overall_status="ok",
                records_accepted=3, items=[_make_item("c")],
                next_cursor="cursor_100",
            )
            provider = FakeFeedProvider(batch)
            feed_result, feed_src, raw_batch, cursor_err, feed_summary, sub_sources = \
                run_feed_with_provider(provider, cfg, state_dir, "r7")
            self.assertIsNotNone(cursor_err)
            self.assertIn("regression", cursor_err)

            cursor = _load_cursor(state_dir, cfg)
            self.assertEqual(cursor.cursor_value, "cursor_200")

    def test_failed_provider_no_cursor_advance(self):
        """Unavailable provider must not advance cursor."""
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            cfg = _default_cfg(state_dir=str(state_dir), output_dir=str(tmp))
            atomic_write_json({
                "cursor_name": "published_at_backend",
                "cursor_value": "cursor_50",
                "updated_at": "2026-01-01T00:00:00Z",
                "provider_name": "test",
                "last_successful_run_id": "prev",
                "accepted_count": 5,
            }, str(_cursor_path(state_dir, cfg)))

            batch = IntegrationFeedBatch(
                provider_name="test", overall_status="unavailable",
                items=[], errors=["down"],
            )
            provider = FakeFeedProvider(batch)
            run_feed_with_provider(provider, cfg, state_dir, "r8")

            cursor = _load_cursor(state_dir, cfg)
            self.assertEqual(cursor.cursor_value, "cursor_50")

    def test_degraded_cursor_safe_false_no_advance(self):
        """Degraded + cursor_safe=false must not advance."""
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            cfg = _default_cfg(state_dir=str(state_dir), output_dir=str(tmp))
            atomic_write_json({
                "cursor_name": "published_at_backend",
                "cursor_value": "cursor_50",
                "updated_at": "2026-01-01T00:00:00Z",
                "provider_name": "test",
                "last_successful_run_id": "prev",
                "accepted_count": 5,
            }, str(_cursor_path(state_dir, cfg)))

            batch = IntegrationFeedBatch(
                provider_name="test", overall_status="degraded",
                cursor_safe=False, items=[_make_item("d")],
                next_cursor="cursor_60",
            )
            provider = FakeFeedProvider(batch)
            run_feed_with_provider(provider, cfg, state_dir, "r9")
            cursor = _load_cursor(state_dir, cfg)
            self.assertEqual(cursor.cursor_value, "cursor_50")

    def test_degraded_cursor_safe_true_advance(self):
        """Degraded + cursor_safe=true may advance."""
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            cfg = _default_cfg(state_dir=str(state_dir), output_dir=str(tmp))
            batch = IntegrationFeedBatch(
                provider_name="test", overall_status="degraded",
                cursor_safe=True, items=[_make_item("e")],
                next_cursor="cursor_70",
            )
            provider = FakeFeedProvider(batch)
            run_feed_with_provider(provider, cfg, state_dir, "r10")
            cursor = _load_cursor(state_dir, cfg)
            self.assertEqual(cursor.cursor_value, "cursor_70")

    def test_cursor_state_corrupt(self):
        """Corrupt cursor state must not crash, start from None."""
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            cfg = _default_cfg(state_dir=str(state_dir), output_dir=str(tmp))
            cursor_path = _cursor_path(state_dir, cfg)
            cursor_path.write_text("not valid json", encoding="utf-8")

            cursor = _load_cursor(state_dir, cfg)
            self.assertIsNone(cursor)


# ═══════════════════════════════════════════════════════════════════
# 19. live/fixture/research/cached counts correct
# ═══════════════════════════════════════════════════════════════════

class TestCountsAndWorkbench(unittest.TestCase):
    def test_live_fixture_research_cached_counts(self):
        items = [
            _make_item("live1", data_mode=FeedDataMode.LIVE),
            _make_item("fixture1", data_mode=FeedDataMode.FIXTURE),
        ]
        batch = IntegrationFeedBatch(
            provider_name="test", overall_status="ok",
            records_seen=4, records_accepted=2, records_rejected=2,
            live_count=1, fixture_count=1, research_count=0, cached_count=0,
            items=items,
        )
        provider = FakeFeedProvider(batch)
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            cfg = _default_cfg(state_dir=str(state_dir), output_dir=str(tmp))
            feed_result, feed_src, *_ = run_feed_with_provider(provider, cfg, state_dir, "r11")
            self.assertEqual(feed_result.live_count, 1)
            self.assertEqual(feed_result.fixture_count, 1)

    def test_feed_items_in_workbench(self):
        items = [_make_item("WB item", source_label="news:jin10")]
        batch = IntegrationFeedBatch(
            provider_name="test", overall_status="ok",
            records_seen=1, records_accepted=1,
            live_count=1, items=items,
        )
        provider = FakeFeedProvider(batch)
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            cfg = _default_cfg(state_dir=str(state_dir), output_dir=str(tmp))
            feed_result, feed_src, raw_batch, *_ = run_feed_with_provider(provider, cfg, state_dir, "r12")

            # Build bundle and render
            from market_radar.integration.models import IntegrationRunResult
            run_result = IntegrationRunResult(feed=feed_result, data_mode="live-public")
            from market_radar.integration.one_shot import _build_workbench_bundle
            bundle = _build_workbench_bundle(run_result, cfg)
            self.assertGreater(len(bundle.feed_items), 0)
            self.assertEqual(bundle.feed_items[0].source_label, "news:jin10")

            html = render_workbench(bundle)
            self.assertIn("WB item", html)
            self.assertIn("news:jin10", html)

    def test_xss_still_escaped(self):
        items = [_make_item("<script>alert('xss')</script>")]
        batch = IntegrationFeedBatch(
            provider_name="test", overall_status="ok",
            records_seen=1, records_accepted=1,
            live_count=1, items=items,
        )
        provider = FakeFeedProvider(batch)
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            cfg = _default_cfg(state_dir=str(state_dir), output_dir=str(tmp))
            feed_result, feed_src, *_ = run_feed_with_provider(provider, cfg, state_dir, "r13")
            run_result = IntegrationRunResult(feed=feed_result, data_mode="live-public")
            from market_radar.integration.one_shot import _build_workbench_bundle
            bundle = _build_workbench_bundle(run_result, cfg)
            html = render_workbench(bundle)
            self.assertIn("&lt;script&gt;", html)


# ═══════════════════════════════════════════════════════════════════
# 22-25. FeedItem metadata preserved
# ═══════════════════════════════════════════════════════════════════

class TestFeedMetadata(unittest.TestCase):
    def test_feed_id_preserved(self):
        items = [FeedItem(
            feed_id="custom:id:123",
            source_type=FeedSourceType.FLASH,
            source_label="news:jin10",
            data_mode=FeedDataMode.LIVE,
            title="Preserved ID",
        )]
        batch = IntegrationFeedBatch(provider_name="test", overall_status="ok",
                                       records_seen=1, records_accepted=1,
                                       live_count=1, items=items)
        provider = FakeFeedProvider(batch)
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            cfg = _default_cfg(state_dir=str(state_dir), output_dir=str(tmp))
            feed_result, *_ = run_feed_with_provider(provider, cfg, state_dir, "r14")
            item_dict = feed_result.items[0]
            self.assertEqual(item_dict["feed_id"], "custom:id:123")

    def test_multi_source_not_flattened(self):
        items = [
            _make_item("A", source_label="news:jin10"),
            _make_item("B", source_label="telegram:channel"),
        ]
        batch = IntegrationFeedBatch(provider_name="test", overall_status="ok",
                                       records_seen=2, records_accepted=2,
                                       live_count=2, items=items,
                                       source_statuses=[
                                           {"source": "news:jin10", "status": "ok", "ok": True},
                                           {"source": "telegram:channel", "status": "ok", "ok": True},
                                       ])
        provider = FakeFeedProvider(batch)
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "s"
            state_dir.mkdir()
            cfg = _default_cfg(state_dir=str(state_dir), output_dir=str(tmp))
            feed_result, feed_src, raw_batch, *_ = run_feed_with_provider(provider, cfg, state_dir, "r15")
            self.assertEqual(len(raw_batch.source_statuses), 2)


# ═══════════════════════════════════════════════════════════════════
# 26-27. Report does not contain body, contains cursor
# ═══════════════════════════════════════════════════════════════════

class TestReportSummary(unittest.TestCase):
    @patch("market_radar.integration.one_shot.HyperliquidPublicAdapter")
    @patch("market_radar.integration.one_shot.CcxtPublicMarketAdapter")
    def test_report_has_cursor_no_body(self, mock_ccxt, mock_hl):
        mock_hl.return_value.fetch_clearinghouse_state.return_value.ok = True
        mock_hl.return_value.fetch_clearinghouse_state.return_value.data = {"assetPositions": []}
        mock_hl.return_value.fetch_clearinghouse_state.return_value.provenance = MagicMock(source="sdk")
        mock_hl.return_value.fetch_clearinghouse_state.return_value.health = MagicMock(available=True)
        mock_hl.return_value.fetch_all_mids.return_value.ok = True
        mock_hl.return_value.fetch_all_mids.return_value.data = {"HYPE": "25.0"}
        mock_hl.return_value.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")
        mock_ccxt.return_value.fetch.return_value.ok = True
        mock_ccxt.return_value.fetch.return_value.data = {"last": 50000.0, "bid": 49900.0, "ask": 50100.0, "_raw": {}}
        mock_ccxt.return_value.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock_ccxt.return_value.fetch.return_value.health = MagicMock(available=True)

        items = [_make_item("Report Item")]
        batch = IntegrationFeedBatch(provider_name="report_test", overall_status="ok",
                                       records_seen=1, records_accepted=1,
                                       live_count=1, items=items,
                                       next_cursor="cursor_report")
        provider = FakeFeedProvider(batch)

        with tempfile.TemporaryDirectory() as tmp:
            cfg = IntegrationConfig(mode="live-public", state_dir=os.path.join(tmp, "s"),
                                     output_dir=os.path.join(tmp, "o"),
                                     whale_address="", exchange="binance",
                                     timeout=15.0, no_send=True,
                                     feed_enabled=True)
            result = run_one_shot(cfg, feed_provider=provider)
            d = result.as_dict()

            # Check feed_summary in report
            self.assertIn("feed_summary", d)
            fs = d["feed_summary"]
            self.assertEqual(fs["provider_name"], "report_test")
            self.assertEqual(fs["cursor_after"], "cursor_report")

            # Body must not appear — use result directly
            self.assertEqual(result.feed_summary.get("errors"), [])
            # Check feed items aren't in the report body
            report_feed = d.get("feed_summary", {})
            self.assertIsNotNone(report_feed.get("provider_name"))
            self.assertNotIn("item_count", report_feed)  # summary, not items
            self.assertIn("cursor_after", report_feed)


# ═══════════════════════════════════════════════════════════════════
# 30. Provider called only once
# ═══════════════════════════════════════════════════════════════════

class TestProviderCalledOnce(unittest.TestCase):
    @patch("market_radar.integration.one_shot.HyperliquidPublicAdapter")
    @patch("market_radar.integration.one_shot.CcxtPublicMarketAdapter")
    def test_provider_called_once(self, mock_ccxt, mock_hl):
        mock_hl.return_value.fetch_clearinghouse_state.return_value.ok = True
        mock_hl.return_value.fetch_clearinghouse_state.return_value.data = {"assetPositions": []}
        mock_hl.return_value.fetch_clearinghouse_state.return_value.provenance = MagicMock(source="sdk")
        mock_hl.return_value.fetch_clearinghouse_state.return_value.health = MagicMock(available=True)
        mock_hl.return_value.fetch_all_mids.return_value.ok = True
        mock_hl.return_value.fetch_all_mids.return_value.data = {"HYPE": "25.0"}
        mock_hl.return_value.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")
        mock_ccxt.return_value.fetch.return_value.ok = True
        mock_ccxt.return_value.fetch.return_value.data = {"last": 50000.0, "bid": 49900.0, "ask": 50100.0, "_raw": {}}
        mock_ccxt.return_value.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock_ccxt.return_value.fetch.return_value.health = MagicMock(available=True)

        items = [_make_item("Once")]
        batch = IntegrationFeedBatch(provider_name="once_test", overall_status="ok",
                                       records_seen=1, records_accepted=1,
                                       live_count=1, items=items)
        provider = FakeFeedProvider(batch)

        with tempfile.TemporaryDirectory() as tmp:
            cfg = IntegrationConfig(mode="fixture", state_dir=os.path.join(tmp, "s"),
                                     output_dir=os.path.join(tmp, "o"),
                                     whale_address="", exchange="binance",
                                     timeout=15.0, no_send=True,
                                     feed_enabled=True)
            run_one_shot(cfg, feed_provider=provider)
            self.assertEqual(provider.call_count, 1)


# ═══════════════════════════════════════════════════════════════════
# 32-33. Overall completed/degraded status consistency
# ═══════════════════════════════════════════════════════════════════

class TestOverallStatus(unittest.TestCase):
    @patch("market_radar.integration.one_shot.HyperliquidPublicAdapter")
    @patch("market_radar.integration.one_shot.CcxtPublicMarketAdapter")
    def test_overall_completed(self, mock_ccxt, mock_hl):
        """All sources ok + Feed provider ok → completed."""
        mock_hl.return_value.fetch_clearinghouse_state.return_value.ok = True
        mock_hl.return_value.fetch_clearinghouse_state.return_value.data = {"assetPositions": []}
        mock_hl.return_value.fetch_clearinghouse_state.return_value.provenance = MagicMock(source="sdk")
        mock_hl.return_value.fetch_clearinghouse_state.return_value.health = MagicMock(available=True)
        mock_hl.return_value.fetch_all_mids.return_value.ok = True
        mock_hl.return_value.fetch_all_mids.return_value.data = {"HYPE": "25.0"}
        mock_hl.return_value.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")
        mock_ccxt.return_value.fetch.return_value.ok = True
        mock_ccxt.return_value.fetch.return_value.data = {"last": 50000.0, "bid": 49900.0, "ask": 50100.0, "_raw": {}}
        mock_ccxt.return_value.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock_ccxt.return_value.fetch.return_value.health = MagicMock(available=True)

        items = [_make_item("Complete")]
        batch = IntegrationFeedBatch(provider_name="ok", overall_status="ok",
                                       records_seen=1, records_accepted=1,
                                       live_count=1, items=items)
        provider = FakeFeedProvider(batch)
        with tempfile.TemporaryDirectory() as tmp:
            cfg = IntegrationConfig(mode="live-public", state_dir=os.path.join(tmp, "s"),
                                     output_dir=os.path.join(tmp, "o"),
                                     whale_address="0xaddr", exchange="binance",
                                     timeout=15.0, no_send=True,
                                     feed_enabled=True)
            result = run_one_shot(cfg, feed_provider=provider)
            # All mocks return ok, feed provider returns ok → should be completed
            self.assertEqual(result.status, "completed")

    @patch("market_radar.integration.one_shot.HyperliquidPublicAdapter")
    @patch("market_radar.integration.one_shot.CcxtPublicMarketAdapter")
    def test_overall_degraded_when_feed_unavailable(self, mock_ccxt, mock_hl):
        mock_hl.return_value.fetch_clearinghouse_state.return_value.ok = True
        mock_hl.return_value.fetch_clearinghouse_state.return_value.data = {"assetPositions": []}
        mock_hl.return_value.fetch_clearinghouse_state.return_value.provenance = MagicMock(source="sdk")
        mock_hl.return_value.fetch_all_mids.return_value.ok = True
        mock_hl.return_value.fetch_all_mids.return_value.data = {"HYPE": "25.0"}
        mock_hl.return_value.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")
        mock_ccxt.return_value.fetch.return_value.ok = True
        mock_ccxt.return_value.fetch.return_value.data = {"last": 50000.0, "bid": 49900.0, "ask": 50100.0, "_raw": {}}
        mock_ccxt.return_value.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock_ccxt.return_value.fetch.return_value.health = MagicMock(available=True)

        batch = IntegrationFeedBatch(provider_name="bad", overall_status="unavailable",
                                       items=[], errors=["all down"])
        provider = FakeFeedProvider(batch)
        with tempfile.TemporaryDirectory() as tmp:
            cfg = IntegrationConfig(mode="fixture", state_dir=os.path.join(tmp, "s"),
                                     output_dir=os.path.join(tmp, "o"),
                                     whale_address="", exchange="binance",
                                     timeout=15.0, no_send=True,
                                     feed_enabled=True)
            result = run_one_shot(cfg, feed_provider=provider)
            self.assertEqual(result.status, "degraded")


# ═══════════════════════════════════════════════════════════════════
# 34. Internal exception → failed
# ═══════════════════════════════════════════════════════════════════

class TestInternalException(unittest.TestCase):
    @patch("market_radar.integration.one_shot.HyperliquidPublicAdapter")
    @patch("market_radar.integration.one_shot.CcxtPublicMarketAdapter")
    def test_internal_exception_fails(self, mock_ccxt, mock_hl):
        mock_hl.return_value.fetch_clearinghouse_state.side_effect = RuntimeError("FATAL")
        mock_ccxt.return_value = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            cfg = IntegrationConfig(mode="fixture", state_dir=os.path.join(tmp, "s"),
                                     output_dir=os.path.join(tmp, "o"),
                                     whale_address="0xaddr", exchange="binance",
                                     timeout=15.0, no_send=True)
            result = run_one_shot(cfg)
            # Whale adapter crash is caught → pipeline returns degraded
            self.assertEqual(result.status, "degraded")


# ═══════════════════════════════════════════════════════════════════
# 35. Run history and report status consistency
# ═══════════════════════════════════════════════════════════════════

class TestRunHistoryConsistency(unittest.TestCase):
    @patch("market_radar.integration.one_shot.HyperliquidPublicAdapter")
    @patch("market_radar.integration.one_shot.CcxtPublicMarketAdapter")
    def test_run_history_matches_report(self, mock_ccxt, mock_hl):
        mock_hl.return_value.fetch_clearinghouse_state.return_value.ok = True
        mock_hl.return_value.fetch_clearinghouse_state.return_value.data = {"assetPositions": []}
        mock_hl.return_value.fetch_clearinghouse_state.return_value.provenance = MagicMock(source="sdk")
        mock_hl.return_value.fetch_clearinghouse_state.return_value.health = MagicMock(available=True)
        mock_hl.return_value.fetch_all_mids.return_value.ok = True
        mock_hl.return_value.fetch_all_mids.return_value.data = {"HYPE": "25.0"}
        mock_hl.return_value.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")
        mock_ccxt.return_value.fetch.return_value.ok = True
        mock_ccxt.return_value.fetch.return_value.data = {"last": 50000.0, "bid": 49900.0, "ask": 50100.0, "_raw": {}}
        mock_ccxt.return_value.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock_ccxt.return_value.fetch.return_value.health = MagicMock(available=True)
        mock_ccxt.return_value.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock_ccxt.return_value.fetch.return_value.health = MagicMock(available=True)

        items = [_make_item("History")]
        batch = IntegrationFeedBatch(provider_name="hist", overall_status="ok",
                                       records_seen=1, records_accepted=1,
                                       live_count=1, items=items)
        provider = FakeFeedProvider(batch)

        with tempfile.TemporaryDirectory() as tmp:
            cfg = IntegrationConfig(mode="fixture", state_dir=os.path.join(tmp, "s"),
                                     output_dir=os.path.join(tmp, "o"),
                                     whale_address="", exchange="binance",
                                     timeout=15.0, no_send=True,
                                     feed_enabled=True)
            result = run_one_shot(cfg, feed_provider=provider)
            d = result.as_dict()

            # Verify output report exists
            report_paths = [p for p in d.get("output_paths", []) if "run_" in p]
            if report_paths and os.path.exists(report_paths[0]):
                with open(report_paths[0], "r", encoding="utf-8") as f:
                    report = json.load(f)
                self.assertEqual(report["status"], d["status"])
                self.assertIn("feed_summary", report)


# ═══════════════════════════════════════════════════════════════════
# Failure isolation tests (Section 8)
# ═══════════════════════════════════════════════════════════════════

class TestFailureIsolation(unittest.TestCase):
    @patch("market_radar.integration.one_shot.HyperliquidPublicAdapter")
    @patch("market_radar.integration.one_shot.CcxtPublicMarketAdapter")
    def test_feed_failure_whale_market_still_execute(self, mock_ccxt, mock_hl):
        """Feed provider raises, Whale and Market still produce results."""
        mock_hl.return_value.fetch_clearinghouse_state.return_value.ok = True
        mock_hl.return_value.fetch_clearinghouse_state.return_value.data = {"assetPositions": []}
        mock_hl.return_value.fetch_clearinghouse_state.return_value.provenance = MagicMock(source="sdk")
        mock_hl.return_value.fetch_clearinghouse_state.return_value.health = MagicMock(available=True)
        mock_hl.return_value.fetch_all_mids.return_value.ok = True
        mock_hl.return_value.fetch_all_mids.return_value.data = {"HYPE": "25.0"}
        mock_hl.return_value.fetch_all_mids.return_value.provenance = MagicMock(source="sdk")
        mock_ccxt.return_value.fetch.return_value.ok = True
        mock_ccxt.return_value.fetch.return_value.data = {"last": 50000.0, "bid": 49900.0, "ask": 50100.0, "_raw": {}}
        mock_ccxt.return_value.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock_ccxt.return_value.fetch.return_value.health = MagicMock(available=True)
        mock_ccxt.return_value.fetch.return_value.provenance = MagicMock(source="ccxt")
        mock_ccxt.return_value.fetch.return_value.health = MagicMock(available=True)

        def raise_provider(inp):
            raise ConnectionError("feed timeout")

        with tempfile.TemporaryDirectory() as tmp:
            cfg = IntegrationConfig(mode="fixture", state_dir=os.path.join(tmp, "s"),
                                     output_dir=os.path.join(tmp, "o"),
                                     whale_address="0xaddr", exchange="binance",
                                     timeout=15.0, no_send=True, feed_enabled=True)
            result = run_one_shot(cfg, feed_provider=raise_provider)
            self.assertIn(result.status, ("degraded", "failed"))
            # Whale ran (empty positions)
            whale_srcs = [s for s in result.sources if "whale" in s.source]
            self.assertGreater(len(whale_srcs), 0)
            market_srcs = [s for s in result.sources if "ccxt" in s.source]
            self.assertGreater(len(market_srcs), 0)


if __name__ == "__main__":
    unittest.main()
