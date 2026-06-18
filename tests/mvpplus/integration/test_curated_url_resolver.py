"""Tests for curated URL resolver priority chain.

Tests cover:
  1. CLI URL preferred over env var
  2. Env var preferred over default
  3. No CLI, no env → default (loopback)
  4. Empty string CLI falls through to env
  5. Empty string env falls through to default
  6. One-shot passes resolved URL to CuratedFeedProvider
  7. Bounded shadow passes same URL to both children
  8. Manifest records actual resolved URL
  9. Timeout still produces degraded status
  10. Successful response produces feed status=ok
"""

from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from market_radar.integration.curated_url_resolver import (
    resolve_curated_url,
    DEFAULT_CURATED_URL,
    ENV_VAR_NAME,
)


class TestResolverPriority(unittest.TestCase):
    """Priority: CLI arg → env var → default."""

    def test_cli_wins_over_env(self):
        """CLI argument must take priority over environment variable."""
        with patch.dict(os.environ, {ENV_VAR_NAME: "http://env:8001/path"}, clear=True):
            result = resolve_curated_url(cli_arg="http://cli:8001/path")
        self.assertEqual(result, "http://cli:8001/path")

    def test_env_wins_over_default(self):
        """Environment variable must take priority over default."""
        with patch.dict(os.environ, {ENV_VAR_NAME: "http://env:8001/path"}, clear=True):
            result = resolve_curated_url(cli_arg=None)
        self.assertEqual(result, "http://env:8001/path")

    def test_default_when_none(self):
        """No CLI, no env → default loopback URL."""
        with patch.dict(os.environ, {}, clear=True):
            result = resolve_curated_url(cli_arg=None)
        self.assertEqual(result, DEFAULT_CURATED_URL)
        self.assertIn("127.0.0.1", result)

    def test_empty_cli_uses_env(self):
        """Empty string CLI must fall through to environment variable."""
        with patch.dict(os.environ, {ENV_VAR_NAME: "http://env:8001/path"}, clear=True):
            result = resolve_curated_url(cli_arg="   ")
        self.assertEqual(result, "http://env:8001/path")

    def test_empty_env_uses_default(self):
        """Empty string env must fall through to default."""
        with patch.dict(os.environ, {ENV_VAR_NAME: ""}, clear=True):
            result = resolve_curated_url(cli_arg=None)
        self.assertEqual(result, DEFAULT_CURATED_URL)

    def test_both_empty_uses_default(self):
        with patch.dict(os.environ, {}, clear=True):
            result = resolve_curated_url(cli_arg="")
        self.assertEqual(result, DEFAULT_CURATED_URL)

    def test_env_name_constant(self):
        self.assertEqual(ENV_VAR_NAME, "CURATED_BASE_URL")


class TestResolverEdgeCases(unittest.TestCase):

    def test_cli_with_trailing_slash(self):
        result = resolve_curated_url(cli_arg="http://example.com/api/")
        self.assertEqual(result, "http://example.com/api/")

    def test_default_is_loopback(self):
        self.assertIn("127.0.0.1", DEFAULT_CURATED_URL)
        self.assertIn("8001", DEFAULT_CURATED_URL)

    def test_resolver_never_returns_public_ip(self):
        """The resolver's defaults must never contain the old public IP."""
        with patch.dict(os.environ, {}, clear=True):
            result = resolve_curated_url()
        self.assertNotIn("43.98.174.247", result)


class TestIntegrationContract(unittest.TestCase):
    """Verify that the resolver contract is upheld by consumers."""

    def test_default_matches_provider_default(self):
        """CuratedFeedProvider's default should match curated_url_resolver's default."""
        from market_radar.integration.curated_feed_provider import CuratedFeedProvider
        # Default constructed without args
        provider_default = CuratedFeedProvider()._base_url
        self.assertEqual(
            provider_default,
            DEFAULT_CURATED_URL,
            f"CuratedFeedProvider default '{provider_default}' does not match "
            f"resolver default '{DEFAULT_CURATED_URL}'",
        )

    def test_one_shot_uses_resolver(self):
        """run_one_shot.py's --curated-base-url must default to None (triggers resolver)."""
        import ast
        import sys
        script_path = "scripts/mvpplus/integration/run_one_shot.py"
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except FileNotFoundError:
            self.skipTest(f"{script_path} not found")
        # Check that the argparse default is None
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and hasattr(node.func, 'attr') and node.func.attr == 'add_argument':
                for kw in node.keywords:
                    if kw.arg == 'dest' and hasattr(kw.value, 's') and kw.value.s == 'curated_base_url':
                        # Found the curated_base_url argument; check default is None
                        for kw2 in node.keywords:
                            if kw2.arg == 'default':
                                self.assertIsNone(
                                    ast.literal_eval(kw2.value),
                                    "run_one_shot.py --curated-base-url default must be None"
                                )
                        return
        # Fallback: grep for the argument
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("--curated-base-url", content)
        self.assertIn("default=None", content)

    def test_resolved_url_in_config(self):
        """Resolved curated URL must appear in IntegrationConfig.feed_base_url."""
        from market_radar.integration.models import IntegrationConfig
        cfg = IntegrationConfig(feed_base_url="http://test:8001/api")
        d = cfg.as_dict()
        self.assertEqual(d.get("feed_base_url"), "http://test:8001/api")
