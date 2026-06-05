"""Tests for Market Radar v1.11-O — Sender Runtime Readiness

Covers:
  - Missing env → readiness=false
  - Env present → readiness=true, but no send
  - No token/chat_id values output
  - No .env reading
  - No Read-Host usage
  - No network calls
  - ARB H6-07 readiness check passes
  - ETH does not enter readiness
  - v1.11-N blocked → post_send_review_stub outputs skipped
  - Result JSON contains no secret patterns

Run:
    python scripts/test_market_radar_sender_runtime_v111o.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CN_TZ = timezone(timedelta(hours=8))


# ── Helper: scan for secret patterns ──────────────────────────────────────────────


def _contains_token_or_chat_id_value(text: str) -> bool:
    """Check if text contains anything that looks like a token or chat_id value.

    This is intentionally aggressive — false positives are better than leaks.
    Checks for:
      - Numeric IDs that look like chat IDs (long digit sequences)
      - Token-like strings (long alphanumeric sequences with colons)

    BUT we must be careful not to flag legitimate IDs like signal_id (H6-07),
    message_id, or other non-secret fields.

    We only flag if the context suggests a BOT TOKEN (format: digits:alphanumeric)
    or a chat_id that is a standalone long digit sequence NOT part of a structured
    field name.
    """
    # Bot token pattern: NNNNNNNNNN:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    # This is the Telegram bot token format
    bot_token_pattern = re.compile(r'\b\d{8,12}:[a-zA-Z0-9_-]{30,50}\b')
    if bot_token_pattern.search(text):
        return True

    # chat_id: a negative number with 10+ digits (Telegram chat IDs are typically
    # negative for groups/channels) or very long positive digit sequences
    # We look for standalone negative 10+ digit numbers
    chat_id_neg_pattern = re.compile(r'(?<!["\w])-?\d{13,20}(?!["\w])')
    if chat_id_neg_pattern.search(text):
        return True

    return False


# ── Helper: check for .env reading ────────────────────────────────────────────────


def _source_contains_dotenv_reading(source_code: str) -> bool:
    """Check if source code actually reads .env files (not just mentions them).

    Only flags actual dotenv usage: imports, load_dotenv calls, or opening .env files.
    Does NOT flag comments/docstrings that say 'no .env reading'.
    """
    # Only flag actual import/use of dotenv, not comments
    patterns = [
        r'from\s+dotenv\s+import',
        r'import\s+dotenv',
        r'load_dotenv\s*\(',
        r'python-dotenv',
    ]
    for p in patterns:
        if re.search(p, source_code, re.IGNORECASE):
            return True

    # Check for actual .env file opening (not in comments)
    # Look for open() calls with .env path
    if re.search(r'open\s*\(.*\.env[\'"]', source_code):
        return True
    if re.search(r'Path\(.*\.env[\'"]', source_code):
        if re.search(r'\.read|\.open|with\s+open', source_code):
            return True

    return False


def _source_contains_read_host(source_code: str) -> bool:
    """Check if source code uses Read-Host or input() for credentials.

    Only flags actual PowerShell Read-Host or Python input() calls,
    NOT mentions in comments/docstrings.
    """
    # PowerShell Read-Host (must be an actual command, not in a comment)
    # Check for Read-Host used as a command (with parameters)
    if re.search(r'Read-Host\s+', source_code):
        return True

    # Python input() used for credentials
    if re.search(r'input\s*\(\s*[\'"].*token', source_code, re.IGNORECASE):
        return True
    if re.search(r'input\s*\(\s*[\'"].*chat', source_code, re.IGNORECASE):
        return True
    if re.search(r'input\s*\(\s*[\'"].*credential', source_code, re.IGNORECASE):
        return True

    # getpass
    if re.search(r'from\s+getpass\s+import|import\s+getpass', source_code):
        return True

    return False


# ── Tests ─────────────────────────────────────────────────────────────────────────


class TestEnvReadiness(unittest.TestCase):
    """Test environment credential readiness checks."""

    def setUp(self):
        """Import the check module."""
        sys.path.insert(0, str(ROOT / "scripts"))
        import check_market_radar_sender_runtime_v111o as mod
        self.mod = mod

    def test_missing_env_readiness_false(self):
        """When both env vars are missing, readiness should be false."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure vars are NOT set
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)
            os.environ.pop("TELEGRAM_CHAT_ID", None)

            env = self.mod._check_env_readiness()
            self.assertFalse(env["telegram_bot_token_present"])
            self.assertFalse(env["telegram_chat_id_present"])
            self.assertFalse(env["values_printed"])

    def test_env_present_readiness_true_but_no_send(self):
        """When env vars are present, readiness=true but the check script
        does NOT send — real_tg_sent is always false."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "1234567890:test_token_for_unit_test_only",
            "TELEGRAM_CHAT_ID": "-1001234567890",
        }):
            env = self.mod._check_env_readiness()
            self.assertTrue(env["telegram_bot_token_present"])
            self.assertTrue(env["telegram_chat_id_present"])
            self.assertFalse(env["values_printed"])

            # Build a full result and verify real_tg_sent is false
            result = self.mod.run_readiness_check()
            self.assertFalse(result["real_tg_sent"])
            self.assertFalse(result["telegram_api_called"])

    def test_no_token_value_in_output(self):
        """Token value must never appear in any output."""
        real_token = "1234567890:test_token_value_abc123"
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": real_token,
            "TELEGRAM_CHAT_ID": "-1001234567890",
        }):
            result = self.mod.run_readiness_check()
            result_json = json.dumps(result, ensure_ascii=False)
            # The actual token value should NOT be in the JSON
            self.assertNotIn(real_token, result_json)
            # Even partial token
            self.assertNotIn("test_token_value_abc123", result_json)

    def test_no_chat_id_value_in_output(self):
        """chat_id value must never appear in any output."""
        real_chat_id = "-1001234567890"
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "1234567890:test_token",
            "TELEGRAM_CHAT_ID": real_chat_id,
        }):
            result = self.mod.run_readiness_check()
            result_json = json.dumps(result, ensure_ascii=False)
            # The actual chat_id value should NOT be in the JSON
            self.assertNotIn(real_chat_id, result_json)
            # Masked info should be in env_readiness
            env_r = result.get("env_readiness", {})
            masked = env_r.get("telegram_chat_id_masked", {})
            self.assertIn("present_masked", masked)
            self.assertIn("length_bucket", masked)

    def test_masked_chat_id_info(self):
        """chat_id should only be reported as present_masked + length_bucket."""
        info = self.mod._masked_chat_id_info("-1001234567890")
        self.assertTrue(info["present_masked"])
        self.assertIn(info["length_bucket"], ["short", "medium", "long"])
        self.assertEqual(info["length_bucket"], "medium")

        # Short
        info_short = self.mod._masked_chat_id_info("12345")
        self.assertTrue(info_short["present_masked"])
        self.assertEqual(info_short["length_bucket"], "short")

        # Long
        info_long = self.mod._masked_chat_id_info("-100123456789012345")
        self.assertTrue(info_long["present_masked"])
        self.assertEqual(info_long["length_bucket"], "long")

        # Empty
        info_empty = self.mod._masked_chat_id_info("")
        self.assertFalse(info_empty["present_masked"])
        self.assertEqual(info_empty["length_bucket"], "empty")

        # None
        info_none = self.mod._masked_chat_id_info("")
        self.assertFalse(info_none["present_masked"])

    def test_no_dotenv_reading(self):
        """The check script must not read .env files."""
        check_path = ROOT / "scripts" / "check_market_radar_sender_runtime_v111o.py"
        source = check_path.read_text(encoding="utf-8")
        self.assertFalse(
            _source_contains_dotenv_reading(source),
            "check script should not read .env files"
        )

    def test_no_read_host(self):
        """The check script must not use Read-Host or interactive input."""
        check_path = ROOT / "scripts" / "check_market_radar_sender_runtime_v111o.py"
        source = check_path.read_text(encoding="utf-8")
        self.assertFalse(
            _source_contains_read_host(source),
            "check script should not use Read-Host or interactive input"
        )


class TestArbH607Readiness(unittest.TestCase):
    """Test ARB H6-07 candidate readiness checks."""

    def setUp(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import check_market_radar_sender_runtime_v111o as mod
        self.mod = mod

    def test_arb_h607_readiness_check_passes(self):
        """ARB H6-07 should be found ready from v1.11-L result."""
        candidate = self.mod._check_arb_h607_readiness()
        self.assertEqual(candidate["signal_id"], "H6-07")
        self.assertEqual(candidate["asset"], "ARB")
        self.assertTrue(candidate["public_card_ready"])
        self.assertEqual(candidate["debug_leak_count"], 0)
        self.assertTrue(candidate["v111l_result_found"])

    def test_eth_does_not_enter_readiness(self):
        """ETH must never enter readiness — always false."""
        candidate = self.mod._check_arb_h607_readiness()
        self.assertFalse(
            candidate["eth_enters_readiness"],
            "ETH must never enter readiness"
        )
        # ETH should not be best candidate
        self.assertFalse(candidate.get("eth_in_best_candidate", True))


class TestV111NBlockedCheck(unittest.TestCase):
    """Test v1.11-N blocked status checks."""

    def setUp(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import check_market_radar_sender_runtime_v111o as mod
        self.mod = mod

    def test_v111n_blocked_detected(self):
        """v1.11-N should be detected as blocked by credentials."""
        v111n = self.mod._check_v111n_blocked()
        self.assertTrue(v111n["v111n_result_exists"])
        self.assertTrue(v111n["v111n_blocked"])
        self.assertTrue(v111n["v111n_blocked_by_credentials"])
        self.assertEqual(v111n["v111n_status"], "blocked")


class TestPostSendReviewStub(unittest.TestCase):
    """Test the post-send review stub behavior."""

    def setUp(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import run_market_radar_v111o_post_send_review_stub as stub_mod
        self.stub_mod = stub_mod

    def test_v111n_blocked_stub_skipped(self):
        """When v1.11-N is blocked, post_send_review_stub outputs skipped."""
        result = self.stub_mod.run_review()
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "no_real_message_id_available")
        self.assertIn("blocked", result.get("detail", "").lower() or
                      result.get("v111n_reason", "").lower() or "true")

    def test_no_telegram_api_in_stub_source(self):
        """Post-send review stub must not call Telegram API."""
        stub_path = ROOT / "scripts" / "run_market_radar_v111o_post_send_review_stub.py"
        source = stub_path.read_text(encoding="utf-8")
        # No telegram API calls
        api_patterns = [
            r'requests\.(get|post|put).*telegram',
            r'urllib.*telegram',
            r'bot\.send',
            r'sendMessage',
            r'send_message',
        ]
        for p in api_patterns:
            self.assertNotRegex(source, p,
                f"post_send_review_stub should not call Telegram API")

    def test_no_dotenv_in_stub_source(self):
        """Post-send review stub must not read .env."""
        stub_path = ROOT / "scripts" / "run_market_radar_v111o_post_send_review_stub.py"
        source = stub_path.read_text(encoding="utf-8")
        self.assertFalse(_source_contains_dotenv_reading(source))

    def test_no_read_host_in_stub_source(self):
        """Post-send review stub must not use interactive input."""
        stub_path = ROOT / "scripts" / "run_market_radar_v111o_post_send_review_stub.py"
        source = stub_path.read_text(encoding="utf-8")
        self.assertFalse(_source_contains_read_host(source))


class TestResultJsonSafety(unittest.TestCase):
    """Test that result JSON contains no secret patterns."""

    def setUp(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import check_market_radar_sender_runtime_v111o as mod
        self.mod = mod

    def test_result_json_no_secret_patterns(self):
        """Result JSON must not contain token, chat_id, api_key, password VALUES.

        Field names like 'telegram_bot_token_present' (boolean flags) are
        metadata keys — they are NOT secret values. Only string values
        that contain actual secrets should be flagged.
        """
        result_path = ROOT / "results" / "market_radar_v111o_sender_runtime_readiness_result.json"
        if not result_path.exists():
            self.skipTest("Result JSON not yet generated — run check script first")

        with open(result_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        # Scan only VALUES (not keys) for secret-like patterns
        def _scan_values(obj):
            """Recursively scan values for secret patterns."""
            if isinstance(obj, str):
                obj_lower = obj.lower()
                # Bot token pattern (digits:alphanumeric long string)
                if re.search(r'\b\d{8,12}:[A-Za-z0-9_-]{30,50}\b', obj):
                    return False, f"bot_token value found: {obj[:30]}..."
                # Chat ID pattern (negative 10+ digit number)
                if re.search(r'(?<!\w)-?\d{13,20}(?!\w)', obj):
                    return False, f"chat_id value found: {obj[:30]}..."
                # Explicit api_key or password values
                if re.search(r'sk-[A-Za-z0-9]{20,}', obj_lower):
                    return False, f"api_key pattern found: {obj[:30]}..."
                return True, None
            elif isinstance(obj, dict):
                for v in obj.values():
                    ok, reason = _scan_values(v)
                    if not ok:
                        return False, reason
                return True, None
            elif isinstance(obj, list):
                for item in obj:
                    ok, reason = _scan_values(item)
                    if not ok:
                        return False, reason
                return True, None
            return True, None

        clean, reason = _scan_values(data)
        self.assertTrue(clean, f"Result JSON contains secret value: {reason}")

    def test_result_json_has_expected_structure(self):
        """Result JSON must have the expected top-level fields."""
        result_path = ROOT / "results" / "market_radar_v111o_sender_runtime_readiness_result.json"
        if not result_path.exists():
            self.skipTest("Result JSON not yet generated — run check script first")

        with open(result_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        required_fields = [
            "version", "mode", "real_tg_sent", "telegram_api_called",
            "secrets_printed", "env_readiness", "candidate_readiness",
            "ready_to_attempt_real_test_send",
        ]
        for field in required_fields:
            self.assertIn(field, data, f"Result JSON missing required field: '{field}'")

        self.assertEqual(data["version"], "v1.11-O")
        self.assertEqual(data["real_tg_sent"], False)
        self.assertEqual(data["telegram_api_called"], False)

    def test_result_json_no_token_value_leak(self):
        """Result JSON must not contain anything that looks like a bot token."""
        result_path = ROOT / "results" / "market_radar_v111o_sender_runtime_readiness_result.json"
        if not result_path.exists():
            self.skipTest("Result JSON not yet generated — run check script first")

        with open(result_path, "r", encoding="utf-8-sig") as f:
            json_str = f.read()

        self.assertFalse(
            _contains_token_or_chat_id_value(json_str),
            "Result JSON appears to contain a token or chat_id value"
        )


class TestNoNetworkCalls(unittest.TestCase):
    """Verify that v1.11-O scripts make no network calls."""

    def test_check_script_no_network_imports(self):
        """Check script should not import network libraries for Telegram."""
        check_path = ROOT / "scripts" / "check_market_radar_sender_runtime_v111o.py"
        source = check_path.read_text(encoding="utf-8")

        # Should not import TG transport or HTTP client for sending
        self.assertNotIn("TGTransport", source)
        self.assertNotIn("RealHttpClient", source)
        # Should not import the sender module (check for actual import statement)
        self.assertNotRegex(source, r'from\s+scripts\.market_radar_sender\s+import')
        self.assertNotRegex(source, r'import\s+scripts\.market_radar_sender')

    def test_stub_no_network_imports(self):
        """Post-send review stub should not import network libraries."""
        stub_path = ROOT / "scripts" / "run_market_radar_v111o_post_send_review_stub.py"
        source = stub_path.read_text(encoding="utf-8")

        self.assertNotIn("TGTransport", source)
        self.assertNotIn("RealHttpClient", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("urllib", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
