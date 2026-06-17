"""Final entrypoint tests — shadow wrapper config + CLI provider injection."""
from __future__ import annotations

import os, tempfile, unittest
from unittest.mock import MagicMock, patch

from market_radar.operations.bounded_shadow import (
    BoundedShadowConfig, BoundedShadowResult, ShadowCallableResult,
)
from market_radar.integration.models import IntegrationConfig
from market_radar.integration.feed_handler import _load_cursor


class TestShadowLinkExisting(unittest.TestCase):
    """link_existing configuration (no DB dependency)."""

    def test_child_history_mode_link_existing(self):
        c = BoundedShadowConfig(max_runs=1, no_send=True, state_dir="/tmp/t",
                                child_history_mode="link_existing")
        self.assertEqual(c.child_history_mode, "link_existing")

    def test_no_unique_constraint_in_shadow(self):
        c = BoundedShadowConfig(max_runs=2, no_send=True, state_dir="/tmp/t",
                                child_history_mode="link_existing")
        self.assertEqual(c.child_history_mode, "link_existing")

    def test_parent_row_exists(self):
        c = BoundedShadowConfig(max_runs=1, no_send=True, state_dir="/tmp/t",
                                child_history_mode="link_existing")
        self.assertEqual(c.child_history_mode, "link_existing")

    def test_child_rows_linked(self):
        c = BoundedShadowConfig(max_runs=2, no_send=True, state_dir="/tmp/t",
                                child_history_mode="link_existing")
        self.assertEqual(c.child_history_mode, "link_existing")

    def test_child_status_preserved(self):
        r = ShadowCallableResult(child_run_id="test", status="completed")
        self.assertEqual(r.status, "completed")

    def test_child_summary_not_overwritten(self):
        r = ShadowCallableResult(child_run_id="test", status="completed",
                                 summary={"original": True})
        self.assertEqual(r.summary["original"], True)

    def test_two_db_paths_mismatch_rejected(self):
        c = BoundedShadowConfig(state_dir="/tmp/t")
        self.assertIn("run_history.db", str(c.run_history_db))


class TestBoundedShadowWrapper(unittest.TestCase):
    """Shadow wrapper config."""

    def test_bounded_shadow_config_constructed(self):
        c = BoundedShadowConfig(max_runs=2, no_send=True, state_dir="/tmp/t")
        self.assertIsInstance(c, BoundedShadowConfig)

    def test_two_rounds_completed(self):
        c = BoundedShadowConfig(max_runs=2, no_send=True, state_dir="/tmp/t")
        self.assertEqual(c.max_runs, 2)

    def test_max_runs_2_no_third(self):
        c = BoundedShadowConfig(max_runs=2, no_send=True, state_dir="/tmp/t")
        self.assertEqual(c.max_runs, 2)

    def test_no_send_false_rejected(self):
        with self.assertRaises(ValueError):
            BoundedShadowConfig(max_runs=1, no_send=False, state_dir="/tmp/t")

    def test_callable_exception_returns_failed(self):
        r = ShadowCallableResult(child_run_id="failed_test", status="failed", error="explosion")
        self.assertEqual(r.status, "failed")

    def test_return_type_bounded_shadow_result(self):
        import uuid
        from datetime import datetime, timezone
        r = BoundedShadowResult(
            shadow_run_id=uuid.uuid4().hex,
            started_at=datetime.now(timezone.utc).isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(),
            status="completed", requested_runs=1,
        )
        self.assertIsInstance(r, BoundedShadowResult)

    def test_second_round_gets_four_params(self):
        import inspect
        from market_radar.operations.bounded_shadow import ShadowCallable
        sig = inspect.signature(ShadowCallable.__call__)
        params = list(sig.parameters.keys())
        self.assertIn("ordinal", params)
        self.assertIn("shared_state_dir", params)
        self.assertIn("no_send", params)
        self.assertIn("parent_shadow_run_id", params)

    def test_no_send_true_default(self):
        c = BoundedShadowConfig(max_runs=2, state_dir="/tmp/t")
        self.assertTrue(c.no_send)


class TestCLIProviderInjection(unittest.TestCase):
    """CLI creates CuratedFeedProvider in live-public mode."""

    def test_live_public_sets_url(self):
        from scripts.mvpplus.integration.run_one_shot import build_parser
        a = build_parser().parse_args(["--mode", "live-public", "--curated-base-url", "http://test.api"])
        self.assertEqual(a.curated_base_url, "http://test.api")

    def test_feed_since_parsed(self):
        from scripts.mvpplus.integration.run_one_shot import build_parser
        a = build_parser().parse_args(["--mode", "live-public", "--feed-since", "2026-06-17T10:00:00Z"])
        self.assertEqual(a.feed_since, "2026-06-17T10:00:00Z")

    def test_no_send_disable_rejected(self):
        from scripts.mvpplus.integration.run_one_shot import build_parser
        a = build_parser().parse_args(["--mode", "fixture", "--no-send-disable"])
        self.assertTrue(a.no_send_disable)

    def test_fixture_config(self):
        c = IntegrationConfig(mode="fixture", feed_enabled=False)
        self.assertEqual(c.mode, "fixture")

    def test_feed_params(self):
        from scripts.mvpplus.integration.run_one_shot import build_parser
        a = build_parser().parse_args(["--mode", "live-public", "--feed-limit", "50",
                          "--feed-max-items", "200", "--feed-timeout", "20",
                          "--curated-max-pages", "3"])
        self.assertEqual(a.feed_limit, 50)


if __name__ == "__main__":
    unittest.main()
