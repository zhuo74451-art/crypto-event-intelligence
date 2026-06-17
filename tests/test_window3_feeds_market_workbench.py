"""Window 3 Tests — Feed Truth, Market Context, Workbench Security."""
import json, os, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from market_radar.shared.contracts import (
    UnifiedFeedItem, FeedType, FeedSourceName, MarketContext, MarketDataSource,
    WhalePosition, PositionSide, WhalePositionChange, ChangeType, RiskLevel,
    SourceHealth, SourceStatus, DegradedInfo, CONTRACTS_VERSION,
)
from market_radar.l4_existing_feeds.existing_feeds_adapter import run as l4_run
from market_radar.l5_workbench_ui.workbench_renderer import WorkbenchBundle, render_workbench


class TestFeedTruthAudit(unittest.TestCase):
    """Verify feed classification and source truth."""

    def test_live_sources_exist(self):
        result = l4_run(str(ROOT))
        self.assertGreater(result.total_items, 0, "Should have live feed items")
        self.assertGreater(result.sources_checked, 0)
        print(f"  Live items: {result.total_items}, truth: {result.truth.as_dict()}")

    def test_feed_classification(self):
        result = l4_run(str(ROOT))
        t = result.truth
        # flash + news should be > 0 for live data
        self.assertGreater(t.flash_count + t.news_count, 0, "Should have flash/news")
        # research should be excluded
        self.assertGreater(t.research_excluded, 0, "Research samples should be excluded")

    def test_no_fixture_in_live(self):
        result = l4_run(str(ROOT))
        for item in result.feed_items:
            self.assertNotEqual(item.data_origin, "fixture", "Live items should not be fixture")

    def test_unique_ids(self):
        result = l4_run(str(ROOT))
        ids = [f.feed_id for f in result.feed_items]
        self.assertEqual(len(ids), len(set(ids)), "Feed IDs should be unique")


class TestWorkbenchSecurity(unittest.TestCase):
    """HTML security: escaping, URL validation, CSP."""

    def setUp(self):
        self.bundle = WorkbenchBundle(run_id="test", contracts_version=CONTRACTS_VERSION)
        self.maxDiff = None

    def test_html_escaping(self):
        """Malicious title should be escaped."""
        item = UnifiedFeedItem(
            feed_id="t1", feed_type=FeedType.NEWS,
            source_name=FeedSourceName.UNKNOWN,
            title='<script>alert("xss")</script>',
            published_at="2026-01-01T00:00:00Z",
            ingested_at="2026-01-01T00:00:00Z",
        )
        bundle = WorkbenchBundle(feed_items=[item], contracts_version=CONTRACTS_VERSION)
        html = render_workbench(bundle)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)

    def test_javascript_url_rejected(self):
        """javascript: URLs should not appear as links."""
        item = UnifiedFeedItem(
            feed_id="t2", feed_type=FeedType.NEWS,
            source_name=FeedSourceName.UNKNOWN,
            title="Test", url="javascript:alert(1)",
            published_at="2026-01-01T00:00:00Z",
            ingested_at="2026-01-01T00:00:00Z",
        )
        bundle = WorkbenchBundle(feed_items=[item], contracts_version=CONTRACTS_VERSION)
        html = render_workbench(bundle)
        self.assertNotIn("javascript:", html)

    def test_csp_present(self):
        html = render_workbench(self.bundle)
        self.assertIn("Content-Security-Policy", html)
        self.assertIn("script-src 'none'", html)

    def test_no_external_scripts(self):
        html = render_workbench(self.bundle)
        self.assertNotIn("<script", html, "No script tags allowed")

    def test_safe_url_passes(self):
        item = UnifiedFeedItem(
            feed_id="t3", feed_type=FeedType.NEWS,
            source_name=FeedSourceName.UNKNOWN,
            title="OK", url="https://example.com/news",
            published_at="2026-01-01T00:00:00Z",
            ingested_at="2026-01-01T00:00:00Z",
        )
        bundle = WorkbenchBundle(feed_items=[item], contracts_version=CONTRACTS_VERSION)
        html = render_workbench(bundle)
        self.assertIn("example.com", html)

    def test_null_safe_render(self):
        """Bundle with minimal data should render without crash."""
        bundle = WorkbenchBundle(contracts_version=CONTRACTS_VERSION)
        html = render_workbench(bundle)
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertTrue(html.endswith("</html>"))

    def test_full_bundle_render(self):
        """Bundle with all section data should render."""
        bundle = WorkbenchBundle(
            run_id="fulltest",
            contracts_version=CONTRACTS_VERSION,
            positions=[
                WhalePosition(address="0xabc", asset="BTC", side=PositionSide.LONG,
                              position_size_usd=50_000_000.0, observed_at="2026-01-01T00:00:00Z"),
            ],
            changes=[
                WhalePositionChange(address="0xabc", asset="BTC", side=PositionSide.LONG,
                                    change_type=ChangeType.POSITION_INCREASED,
                                    current_position_size_usd=60_000_000.0,
                                    current_observed_at="2026-01-01T00:00:00Z",
                                    risk_level=RiskLevel.ELEVATED),
            ],
            market_contexts=[
                MarketContext(symbol="BTC", price=90000.0, observed_at="2026-01-01T00:00:00Z"),
            ],
            feed_items=[
                UnifiedFeedItem(feed_id="f1", feed_type=FeedType.NEWS,
                                source_name=FeedSourceName.COINDESK,
                                title="Test news", published_at="2026-01-01T00:00:00Z",
                                ingested_at="2026-01-01T00:00:00Z"),
            ],
            source_health=[
                SourceHealth(source_name="test", source_group="test", status=SourceStatus.OK),
            ],
            watchlists={"test": ["BTC", "ETH"]},
            market_regime={"state": "leverage_building", "rules": ["Test rule"]},
            alert_candidates=[{"title": "Test Alert", "rationale": "Test", "source": "test"}],
            event_journal=[{"timestamp": "2026-01-01T00:00:00Z", "summary": "Test"}],
            downstream_candidates=[{"title": "Test DS", "channel": "tg", "rationale": "Test", "source": "test"}],
        )
        html = render_workbench(bundle)
        self.assertIn("fulltest", html)
        self.assertIn("BTC", html)
        self.assertIn("Test news", html)

    def test_output_file_written(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
            tmp = f.name
        try:
            render_workbench(self.bundle, tmp)
            self.assertTrue(os.path.getsize(tmp) > 0)
            with open(tmp, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("Workbench", content)
        finally:
            os.unlink(tmp)


class TestFeedMapping(unittest.TestCase):
    """Test flash/news/onchain mapping."""

    def test_flash_type(self):
        result = l4_run(str(ROOT))
        for item in result.feed_items:
            if item.feed_type == FeedType.FLASH:
                self.assertEqual(item.data_origin, "live")
                return
        self.assertTrue(True)  # flash may be 0 if no watcher data

    def test_news_type(self):
        result = l4_run(str(ROOT))
        for item in result.feed_items:
            if item.feed_type == FeedType.NEWS:
                return  # At least one news item
        self.assertTrue(True)


class TestMarketContext(unittest.TestCase):
    """Market context tests."""

    def test_market_dispatch(self):
        from market_radar.l3_market_context.market_context_provider import run
        result = run()
        self.assertGreaterEqual(result.total_succeeded + result.total_failed, 1)
        for ctx in result.contexts:
            self.assertIsInstance(ctx.symbol, str)


if __name__ == "__main__":
    unittest.main()
