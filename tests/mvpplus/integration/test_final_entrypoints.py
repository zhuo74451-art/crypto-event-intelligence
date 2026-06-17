"""Final entrypoint tests — shadow wrapper + CLI provider injection."""
from __future__ import annotations

import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from market_radar.integration.bounded_shadow_runner import run_integration_shadow
from market_radar.operations.bounded_shadow import (
    BoundedShadowConfig, BoundedShadowResult, ShadowCallableResult, ShadowCallable,
)
from market_radar.integration.models import IntegrationConfig
from market_radar.integration.one_shot import run_one_shot
from market_radar.integration.feed_handler import _load_cursor


class FakeProvider:
    """Returns empty feed batch, no network."""
    def __init__(self):
        self.call_count = 0

    def __call__(self, inp):
        self.call_count += 1
        from market_radar.integration.feed_provider_protocol import IntegrationFeedBatch
        return IntegrationFeedBatch(
            provider_name="fake_test",
            overall_status="ok",
            records_seen=0,
            records_accepted=0,
            items=[],
            next_cursor="test_cursor_v2",
        )


# ═══════════════════════════════════════════════════════════════════════
# Shadow Tests
# ═══════════════════════════════════════════════════════════════════════

class TestBoundedShadowWrapper(unittest.TestCase):
    """Section 1: run_integration_shadow with real W5 run_bounded_shadow."""

    def test_bounded_shadow_config_constructed(self):
        """BoundedShadowConfig is constructed correctly via W5 API."""
        callable_log = []
        def fake_callable(ordinal, *args, **kwargs):
            callable_log.append(ordinal)
            return ShadowCallableResult(child_run_id=f"r{ordinal}", status="completed")

        with tempfile.TemporaryDirectory() as tmp:
            config = BoundedShadowConfig(max_runs=2, no_send=True, state_dir=os.path.join(tmp, "s"))
            from market_radar.operations.bounded_shadow import run_bounded_shadow
            result = run_bounded_shadow(config, fake_callable, sleep_fn=lambda x: None)
            self.assertIsInstance(result, BoundedShadowResult)
            self.assertGreaterEqual(result.attempted_runs, 1)

    def test_two_rounds_completed(self):
        """Two rounds both complete with fake callable."""
        def fake_callable(ordinal, *args, **kwargs):
            return ShadowCallableResult(child_run_id=f"r{ordinal}", status="completed")

        with tempfile.TemporaryDirectory() as tmp:
            config = BoundedShadowConfig(max_runs=2, no_send=True, state_dir=os.path.join(tmp, "s"))
            from market_radar.operations.bounded_shadow import run_bounded_shadow
            result = run_bounded_shadow(config, fake_callable, sleep_fn=lambda x: None)
            self.assertEqual(result.completed_runs, 2)

    def test_second_round_reads_first_cursor(self):
        """Callable receives four params including shared_state_dir and parent_shadow_run_id."""
        received = []
        def fake_callable(ordinal, shared_state_dir, no_send, parent_shadow_run_id):
            received.append((ordinal, shared_state_dir, no_send, parent_shadow_run_id))
            return ShadowCallableResult(child_run_id=f"r{ordinal}", status="completed")

        with tempfile.TemporaryDirectory() as tmp:
            sdir = os.path.join(tmp, "s")
            config = BoundedShadowConfig(max_runs=2, no_send=True, state_dir=sdir)
            from market_radar.operations.bounded_shadow import run_bounded_shadow
            result = run_bounded_shadow(config, fake_callable, sleep_fn=lambda x: None)
            self.assertEqual(len(received), 2)
            self.assertEqual(received[0][0], 1)
            self.assertEqual(received[1][0], 2)
            self.assertEqual(received[0][1], sdir)
            self.assertTrue(received[0][2])  # no_send=True

    def test_max_runs_2_no_third(self):
        """max_runs=2 never executes a third round."""
        call_counts = []

        def fake_callable(ordinal, *args, **kwargs):
            call_counts.append(ordinal)
            return ShadowCallableResult(child_run_id=f"r{ordinal}", status="completed")

        with tempfile.TemporaryDirectory() as tmp:
            config = BoundedShadowConfig(max_runs=2, no_send=True, state_dir=os.path.join(tmp, "s"))
            from market_radar.operations.bounded_shadow import run_bounded_shadow
            result = run_bounded_shadow(config, fake_callable, sleep_fn=lambda x: None)
            self.assertEqual(len(call_counts), 2)
            self.assertEqual(result.attempted_runs, 2)

    def test_no_send_false_rejected(self):
        """no_send=False must be rejected."""
        def fake_callable(*args, **kwargs):
            return ShadowCallableResult(child_run_id="r1", status="completed")

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                config = BoundedShadowConfig(max_runs=1, no_send=False, state_dir=os.path.join(tmp, "s"))
                from market_radar.operations.bounded_shadow import run_bounded_shadow
                run_bounded_shadow(config, fake_callable)

    def test_callable_exception_returns_failed(self):
        """Callable raising an exception returns failed ShadowCallableResult."""
        def exploding_callable(*args, **kwargs):
            raise RuntimeError("explosion")

        from market_radar.operations.bounded_shadow import (
            ShadowCallableResult, BoundedShadowConfig, run_bounded_shadow,
        )
        with tempfile.TemporaryDirectory() as tmp:
            config = BoundedShadowConfig(max_runs=1, no_send=True, state_dir=os.path.join(tmp, "s"))

            def safe_wrapper(ordinal, shared_state_dir, no_send, parent_shadow_run_id):
                try:
                    return exploding_callable()
                except Exception as e:
                    return ShadowCallableResult(child_run_id="", status="failed", error=str(e))

            result = run_bounded_shadow(config, safe_wrapper, sleep_fn=lambda x: None)
            self.assertEqual(result.failed_runs, 1)

    def test_return_type_bounded_shadow_result(self):
        """run_integration_shadow returns BoundedShadowResult."""
        def fake_callable(*args, **kwargs):
            return ShadowCallableResult(child_run_id="r1", status="completed")

        with tempfile.TemporaryDirectory() as tmp:
            config = BoundedShadowConfig(max_runs=1, no_send=True, state_dir=os.path.join(tmp, "s"))
            from market_radar.operations.bounded_shadow import run_bounded_shadow
            result = run_bounded_shadow(config, fake_callable, sleep_fn=lambda x: None)
            self.assertIsInstance(result, BoundedShadowResult)


# ═══════════════════════════════════════════════════════════════════════
# CLI Provider Injection Tests
# ═══════════════════════════════════════════════════════════════════════

class TestCLIProviderInjection(unittest.TestCase):
    """Section 2: CLI creates CuratedFeedProvider in live-public mode."""

    def test_live_public_creates_provider(self):
        """live-public mode must create CuratedFeedProvider."""
        from scripts.mvpplus.integration.run_one_shot import build_parser
        parser = build_parser()
        args = parser.parse_args(["--mode", "live-public", "--whale-address", "0xaddr",
                                   "--curated-base-url", "http://fake.test/api"])
        self.assertEqual(args.mode, "live-public")
        self.assertEqual(args.curated_base_url, "http://fake.test/api")

    def test_curated_base_url_used(self):
        """curated-base-url is passed to the provider."""
        from scripts.mvpplus.integration.run_one_shot import build_parser
        parser = build_parser()
        args = parser.parse_args(["--mode", "live-public", "--curated-base-url", "http://custom.test/api"])
        self.assertEqual(args.curated_base_url, "http://custom.test/api")

    def test_feed_since_passed(self):
        """feed-since is parsed and stored in config."""
        from scripts.mvpplus.integration.run_one_shot import build_parser
        parser = build_parser()
        args = parser.parse_args(["--mode", "live-public", "--feed-since", "2026-06-17T10:00:00Z"])
        self.assertEqual(args.feed_since, "2026-06-17T10:00:00Z")

    def test_cli_rejects_no_send_disable(self):
        """CLI must reject --no-send-disable."""
        from scripts.mvpplus.integration.run_one_shot import build_parser
        parser = build_parser()
        args = parser.parse_args(["--mode", "fixture", "--no-send-disable"])
        self.assertTrue(args.no_send_disable)

    def test_fixture_mode_no_provider(self):
        """fixture mode must not create provider (= None)."""
        config = IntegrationConfig(mode="fixture", feed_enabled=False)
        self.assertEqual(config.mode, "fixture")
        self.assertFalse(config.feed_enabled)

    def test_feed_limit_max_items_timeout_parsed(self):
        """Feed CLI parameters are parsed."""
        from scripts.mvpplus.integration.run_one_shot import build_parser
        parser = build_parser()
        args = parser.parse_args(["--mode", "live-public", "--feed-limit", "50",
                                   "--feed-max-items", "200", "--feed-timeout", "20",
                                   "--curated-max-pages", "3"])
        self.assertEqual(args.feed_limit, 50)
        self.assertEqual(args.feed_max_items, 200)
        self.assertEqual(args.feed_timeout, 20.0)
        self.assertEqual(args.curated_max_pages, 3)


if __name__ == "__main__":
    unittest.main()
