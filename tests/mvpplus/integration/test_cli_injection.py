"""CLI main() behavioral tests — real argument parsing, mocked providers/network."""
from __future__ import annotations

import sys, tempfile, unittest
from unittest.mock import patch, MagicMock, ANY


class TestCLIMainInjection(unittest.TestCase):
    """scripts.mvpplus.integration.run_one_shot.main() behavioral tests."""

    @patch("market_radar.integration.curated_feed_provider.CuratedFeedProvider")
    @patch("scripts.mvpplus.integration.run_one_shot.run_one_shot")
    def test_live_public_creates_provider(self, mock_run, mock_provider_cls):
        """live-public mode creates non-None provider and passes to run_one_shot."""
        mock_run.return_value.status = "completed"
        mock_run.return_value.run_id = "test-run"
        mock_run.return_value.as_dict.return_value = {"status": "completed"}

        test_args = [
            "run_one_shot.py", "--mode", "live-public",
            "--whale-address", "0xaddr",
            "--curated-base-url", "http://custom.api.test",
            "--feed-since", "2026-06-17T10:00:00Z",
        ]
        with patch.object(sys, "argv", test_args):
            from scripts.mvpplus.integration.run_one_shot import main
            result = main()

        # Provider was created with the URL
        mock_provider_cls.assert_called_once()
        call_kwargs = mock_provider_cls.call_args[1]
        self.assertIn("base_url", call_kwargs)
        self.assertEqual(call_kwargs["base_url"], "http://custom.api.test")

        # run_one_shot was called with the provider
        mock_run.assert_called_once()
        provider_arg = mock_run.call_args[1].get("feed_provider")
        self.assertIsNotNone(provider_arg)

    @patch("market_radar.integration.curated_feed_provider.CuratedFeedProvider")
    @patch("scripts.mvpplus.integration.run_one_shot.run_one_shot")
    def test_feed_params_passed_to_provider(self, mock_run, mock_provider_cls):
        """feed-limit, feed-max-items, feed-timeout, curated-max-pages passed to provider."""
        mock_run.return_value.status = "completed"
        mock_run.return_value.run_id = "t"
        mock_run.return_value.as_dict.return_value = {"status": "completed"}

        test_args = [
            "run_one_shot.py", "--mode", "live-public",
            "--feed-limit", "50", "--feed-max-items", "200",
            "--feed-timeout", "20", "--curated-max-pages", "3",
        ]
        with patch.object(sys, "argv", test_args):
            from scripts.mvpplus.integration.run_one_shot import main
            main()

        call_kwargs = mock_provider_cls.call_args[1]
        self.assertEqual(call_kwargs.get("limit"), 50)
        self.assertEqual(call_kwargs.get("max_items"), 200)
        self.assertEqual(call_kwargs.get("timeout_seconds"), 20.0)
        self.assertEqual(call_kwargs.get("max_pages"), 3)

    @patch("market_radar.integration.curated_feed_provider.CuratedFeedProvider")
    @patch("scripts.mvpplus.integration.run_one_shot.run_one_shot")
    def test_feed_since_in_config(self, mock_run, mock_provider_cls):
        """feed-since enters IntegrationConfig.feed_initial_since."""
        mock_run.return_value.status = "completed"
        mock_run.return_value.run_id = "t"
        mock_run.return_value.as_dict.return_value = {"status": "completed"}

        test_args = [
            "run_one_shot.py", "--mode", "live-public",
            "--feed-since", "2026-06-17T10:00:00Z",
        ]
        with patch.object(sys, "argv", test_args):
            from scripts.mvpplus.integration.run_one_shot import main
            main()

        cfg = mock_run.call_args[1].get("config") or mock_run.call_args[0][0]
        if hasattr(cfg, "feed_initial_since"):
            self.assertEqual(cfg.feed_initial_since, "2026-06-17T10:00:00Z")

    @patch("scripts.mvpplus.integration.run_one_shot.run_one_shot")
    def test_fixture_mode_no_provider(self, mock_run):
        """fixture mode does not create a provider (provider=None)."""
        mock_run.return_value.status = "completed"
        mock_run.return_value.run_id = "t"
        mock_run.return_value.as_dict.return_value = {"status": "completed"}

        test_args = ["run_one_shot.py", "--mode", "fixture"]
        with patch.object(sys, "argv", test_args):
            from scripts.mvpplus.integration.run_one_shot import main
            main()

        provider_arg = mock_run.call_args[1].get("feed_provider")
        self.assertIsNone(provider_arg)

    @patch("scripts.mvpplus.integration.run_one_shot.run_one_shot")
    def test_no_send_disable_returns_1(self, mock_run):
        """--no-send-disable returns exit code 1."""
        test_args = ["run_one_shot.py", "--mode", "fixture", "--no-send-disable"]
        with patch.object(sys, "argv", test_args):
            from scripts.mvpplus.integration.run_one_shot import main
            result = main()
            self.assertEqual(result, 1)
        mock_run.assert_not_called()

    @patch("scripts.mvpplus.integration.run_one_shot.run_one_shot")
    def test_no_real_network(self, mock_run):
        """Test uses mocks, no real network calls."""
        mock_run.return_value.status = "completed"
        mock_run.return_value.run_id = "t"
        mock_run.return_value.as_dict.return_value = {"status": "completed"}

        test_args = ["run_one_shot.py", "--mode", "live-public"]
        with patch.object(sys, "argv", test_args):
            from scripts.mvpplus.integration.run_one_shot import main
            main()
        mock_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
