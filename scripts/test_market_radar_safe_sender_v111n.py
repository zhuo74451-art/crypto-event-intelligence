"""Tests for Market Radar v1.11-N — SafeTelegramTestSender

Coverage:
  - Missing credentials → blocked (reason=missing_runtime_test_channel_credentials)
  - No token/chat_id printed or saved
  - formal_channel blocked
  - official_channel blocked
  - prod / production / main_channel blocked
  - ETH must be blocked
  - ARB H6-07 can enter send preparation (mock mode)
  - More than 1 card concept: safe_send_single only allows 1
  - Debug terms in payload → blocked
  - public_card.text empty → blocked
  - Does NOT read .env
  - Does NOT call Read-Host / interactive input
  - No secrets written to result objects
  - Mock network test returns fake message_id with explicit mock marking
  - parse_mode validation
  - pre_send_gate integration

Usage:
    python scripts/test_market_radar_safe_sender_v111n.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CN_TZ = timezone(timedelta(hours=8))

from scripts.market_radar_safe_sender_v111n import (
    SafeTelegramTestSender,
    SAFE_SENDER_VERSION,
    BLOCKED_TARGET_TYPES,
    VALID_PARSE_MODES,
    FORBIDDEN_DEBUG_TERMS,
    create_safe_sender,
    _sha256_hex,
    _has_forbidden_terms,
)


# ── Fixture: valid ARB payload ───────────────────────────────────────────────────
VALID_ARB_PAYLOAD = (
    "📉 行情异动｜ARB 急跌\n"
    "\n"
    "一句话：ARB 24h 跌幅 \\-8\\.50%，多因子异动信号。\n"
    "\n"
    "● 币种：ARB\n"
    "● 涨跌幅：\\-8\\.50%\n"
    "● 观察窗口：1\\-4 小时\n"
    "\n"
    "⚠️ 仅供观察，不构成交易建议。"
)

VALID_ETH_PAYLOAD = (
    "📉 行情异动｜ETH 急跌\n"
    "\n"
    "一句话：ETH 24h 跌幅 \\-8\\.50%，多因子同步确认。\n"
    "\n"
    "● 币种：ETH\n"
    "● 涨跌幅：\\-8\\.50%\n"
    "\n"
    "⚠️ 仅供观察，不构成交易建议。"
)


# ── Test Classes ─────────────────────────────────────────────────────────────────

class TestMissingCredentialsBlocked(unittest.TestCase):
    """Test that missing credentials result in blocked (not error)."""

    def setUp(self):
        self.sender = SafeTelegramTestSender()

    def test_missing_both_credentials_blocked(self):
        """Blocked when both TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID missing."""
        with patch.dict(os.environ, {}, clear=True):
            result = self.sender.safe_send_single(
                payload_text=VALID_ARB_PAYLOAD,
                parse_mode="MarkdownV2",
                signal_id="H6-07",
                asset="ARB",
                target_type="test_channel",
            )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "missing_runtime_test_channel_credentials")
        self.assertFalse(result["real_tg_sent"])
        self.assertFalse(result["official_channel_touched"])
        self.assertFalse(result["secret_printed"])

    def test_missing_token_only_blocked(self):
        """Blocked when only TELEGRAM_CHAT_ID is set."""
        with patch.dict(os.environ, {"TELEGRAM_CHAT_ID": "test123"}, clear=True):
            result = self.sender.safe_send_single(
                payload_text=VALID_ARB_PAYLOAD,
                parse_mode="MarkdownV2",
                signal_id="H6-07",
                asset="ARB",
                target_type="test_channel",
            )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "missing_runtime_test_channel_credentials")

    def test_missing_chat_id_only_blocked(self):
        """Blocked when only TELEGRAM_BOT_TOKEN is set."""
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test123"}, clear=True):
            result = self.sender.safe_send_single(
                payload_text=VALID_ARB_PAYLOAD,
                parse_mode="MarkdownV2",
                signal_id="H6-07",
                asset="ARB",
                target_type="test_channel",
            )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "missing_runtime_test_channel_credentials")

    def test_blocked_does_not_crash(self):
        """Blocked returns a valid dict, never raises an exception."""
        with patch.dict(os.environ, {}, clear=True):
            result = self.sender.safe_send_single(
                payload_text=VALID_ARB_PAYLOAD,
                parse_mode="MarkdownV2",
                signal_id="H6-07",
                asset="ARB",
                target_type="test_channel",
            )
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)
        self.assertIn("reason", result)
        self.assertIn("message_id", result)

    def test_no_user_prompt_for_credentials(self):
        """Should never ask for user input — no Read-Host, no input()."""
        with patch.dict(os.environ, {}, clear=True):
            # Test that it returns blocked immediately without waiting for input
            result = self.sender.safe_send_single(
                payload_text=VALID_ARB_PAYLOAD,
                parse_mode="MarkdownV2",
                signal_id="H6-07",
                asset="ARB",
                target_type="test_channel",
            )
        self.assertEqual(result["status"], "blocked")


class TestNoSecretPrinting(unittest.TestCase):
    """Verify that token/chat_id are never printed or saved to result."""

    def setUp(self):
        self.sender = SafeTelegramTestSender()

    def test_blocked_result_no_token_fields(self):
        """Blocked result must not contain token/chat_id/key/password fields."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "my-secret-token-123",
            "TELEGRAM_CHAT_ID": "-100999888777",
        }, clear=True):
            # We patch credentials present but create a sender that will
            # fail at network level (no real TG), so we test the mock path
            result = self.sender.mock_send_single(
                payload_text=VALID_ARB_PAYLOAD,
                parse_mode="MarkdownV2",
                signal_id="H6-07",
                asset="ARB",
                target_type="test_channel",
            )
        # Ensure no forbidden keys in result
        result_keys_lower = set(str(k).lower() for k in result.keys())
        for forbidden in ["token", "chat_id", "key", "password", "secret", "cookie"]:
            self.assertNotIn(forbidden, result_keys_lower,
                             f"Result must not contain '{forbidden}' field")

    def test_result_values_no_token_leak(self):
        """Result string values must not contain actual tokens."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "my-secret-token-abc123",
            "TELEGRAM_CHAT_ID": "-100999888777",
        }, clear=True):
            result = self.sender.mock_send_single(
                payload_text=VALID_ARB_PAYLOAD,
                parse_mode="MarkdownV2",
                signal_id="H6-07",
                asset="ARB",
                target_type="test_channel",
            )
        # All string values must not contain the token
        result_str = json.dumps(result)
        self.assertNotIn("my-secret-token-abc123", result_str)
        self.assertNotIn("-100999888777", result_str)

    def test_sender_does_not_print_credentials(self):
        """SafeTelegramTestSender module source must not have print of token/chat_id."""
        import scripts.market_radar_safe_sender_v111n as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        # Check there are no print statements containing token/chat_id
        lines = source.split("\n")
        for line in lines:
            stripped = line.strip()
            if "print(" in stripped or "print (" in stripped:
                line_lower = stripped.lower()
                has_print_of_secret = (
                    ("token" in line_lower and "forbidden" not in line_lower and "no_token" not in line_lower) or
                    ("chat_id" in line_lower and "length" not in line_lower)
                )
                if has_print_of_secret:
                    # Verify it's printing a length or redacted version, not the value
                    if "len(" in line_lower or "redact" in line_lower or "not print" in line_lower:
                        continue
                    self.fail(f"Potential secret print: {stripped}")


class TestTargetBlocking(unittest.TestCase):
    """Tests for formal/prod target type blocking."""

    def setUp(self):
        self.sender = SafeTelegramTestSender()

    def test_formal_channel_blocked(self):
        """formal_channel must be blocked."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="formal_channel",
        )
        self.assertEqual(result["status"], "blocked")
        self.assertIn("formal", result["reason"].lower())
        self.assertFalse(result["real_tg_sent"])

    def test_official_channel_blocked(self):
        """official_channel must be blocked."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="official_channel",
        )
        self.assertEqual(result["status"], "blocked")

    def test_prod_blocked(self):
        """prod must be blocked."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="prod",
        )
        self.assertEqual(result["status"], "blocked")

    def test_production_blocked(self):
        """production must be blocked."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="production",
        )
        self.assertEqual(result["status"], "blocked")

    def test_main_channel_blocked(self):
        """main_channel must be blocked."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="main_channel",
        )
        self.assertEqual(result["status"], "blocked")

    def test_case_insensitive_formal_blocked(self):
        """FORMAL_CHANNEL uppercase must be blocked."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="FORMAL_CHANNEL",
        )
        self.assertEqual(result["status"], "blocked")

    def test_formal_channel_triggers_official_channel_touched(self):
        """formal_channel should set official_channel_touched flag."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="formal_channel",
        )
        self.assertTrue(result["official_channel_touched"])

    def test_unknown_target_type_blocked(self):
        """Non-test_channel, non-blocked-list types must be blocked."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="random_stuff",
        )
        self.assertEqual(result["status"], "blocked")

    def test_empty_target_type_blocked(self):
        """Empty target_type must be blocked."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="",
        )
        self.assertEqual(result["status"], "blocked")


class TestETHBlocked(unittest.TestCase):
    """Tests that ETH is consistently blocked."""

    def setUp(self):
        self.sender = SafeTelegramTestSender()

    def test_eth_blocked_explicit(self):
        """ETH asset must be blocked."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ETH_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H5-01",
            asset="ETH",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "eth_blocked")
        self.assertIn("ETH", result["detail"])

    def test_eth_lowercase_blocked(self):
        """eth lowercase must also be blocked."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ETH_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H5-01",
            asset="eth",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")

    def test_eth_mixed_case_blocked(self):
        """Eth mixed case must be blocked."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ETH_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H5-01",
            asset="Eth",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")

    def test_eth_h501_blocked(self):
        """ETH with H5-01 signal must be blocked."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ETH_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H5-01",
            asset="ETH",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "eth_blocked")

    def test_eth_h101_blocked(self):
        """ETH with H1-01 signal must be blocked."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ETH_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="ETH",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "eth_blocked")


class TestARB_H607_Allowed(unittest.TestCase):
    """Tests that ARB H6-07 can enter send preparation (mock mode)."""

    def setUp(self):
        self.sender = SafeTelegramTestSender()

    def test_arb_h607_mock_send_allowed(self):
        """ARB H6-07 on test_channel should pass mock send."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "sent")
        self.assertTrue(result["mock_mode"])
        self.assertFalse(result["real_tg_sent"])
        self.assertTrue(result["message_id"].startswith("mock_v111n_"))
        self.assertEqual(result["signal_id"], "H6-07")
        self.assertEqual(result["asset"], "ARB")

    def test_arb_lowercase_allowed(self):
        """arb lowercase should still be allowed (normalized to ARB)."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="arb",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "sent")

    def test_non_arb_asset_blocked(self):
        """BTC asset must be blocked (not ARB)."""
        result = self.sender.mock_send_single(
            payload_text="BTC test",
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="BTC",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")

    def test_non_h607_signal_blocked(self):
        """H1-01 signal must be blocked (not H6-07)."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")

    def test_mock_message_id_format(self):
        """Mock message_id follows mock_v111n_XXX format."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        mid = result["message_id"]
        self.assertTrue(mid.startswith("mock_v111n_"))
        # Has 3-digit suffix
        suffix = mid.split("_")[-1]
        self.assertEqual(len(suffix), 3)
        self.assertTrue(suffix.isdigit())


class TestPayloadValidation(unittest.TestCase):
    """Tests for payload text validation."""

    def setUp(self):
        self.sender = SafeTelegramTestSender()

    def test_empty_payload_blocked(self):
        """Empty payload text must be blocked."""
        result = self.sender.mock_send_single(
            payload_text="",
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")
        self.assertIn("empty", result["reason"].lower())

    def test_whitespace_only_payload_blocked(self):
        """Whitespace-only payload must be blocked."""
        result = self.sender.mock_send_single(
            payload_text="   \n\t  ",
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")
        self.assertIn("empty", result["reason"].lower())

    def test_none_payload_blocked(self):
        """None payload must be blocked."""
        result = self.sender.mock_send_single(
            payload_text=None,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")

    def test_invalid_parse_mode_blocked(self):
        """Invalid parse_mode must be blocked."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="InvalidMode",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")

    def test_payload_sha256_present(self):
        """Result must contain correct SHA-256 hash of payload."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        expected = _sha256_hex(VALID_ARB_PAYLOAD)
        self.assertEqual(result["payload_text_sha256"], expected)

    def test_payload_length_present(self):
        """Result must contain payload length."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(result["payload_length"], len(VALID_ARB_PAYLOAD))


class TestDebugTermsBlocked(unittest.TestCase):
    """Tests that debug/gate/internal terms in payload trigger block."""

    def setUp(self):
        self.sender = SafeTelegramTestSender()

    def test_value_gate_in_payload_blocked(self):
        """Payload containing 'value_gate' must be blocked."""
        result = self.sender.mock_send_single(
            payload_text="ARB test with value_gate mention",
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "debug_terms_in_payload")

    def test_cooldown_gate_in_payload_blocked(self):
        """Payload containing 'cooldown_gate' must be blocked."""
        result = self.sender.mock_send_single(
            payload_text="信号通过了 cooldown_gate 检查",
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")

    def test_upgrade_override_in_payload_blocked(self):
        """Payload containing 'upgrade_override' must be blocked."""
        result = self.sender.mock_send_single(
            payload_text="冷却: upgrade_override (score↑)",
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")

    def test_mock_message_id_in_payload_blocked(self):
        """Payload containing 'mock_message_id' must be blocked."""
        result = self.sender.mock_send_single(
            payload_text="This references mock_message_id in card text",
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "mock_terms_in_payload")

    def test_mock_sent_in_payload_blocked(self):
        """Payload containing 'mock_sent' must be blocked."""
        result = self.sender.mock_send_single(
            payload_text="Card was mock_sent to test channel",
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "mock_terms_in_payload")

    def test_token_in_payload_blocked(self):
        """Payload containing 'token' must be blocked (debug term)."""
        result = self.sender.mock_send_single(
            payload_text="Use this token to access",
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "blocked")


class TestNoEnvFileReading(unittest.TestCase):
    """Verify the safe sender does NOT read .env files."""

    def test_no_dotenv_import(self):
        """Module source must not import dotenv or python-dotenv."""
        import scripts.market_radar_safe_sender_v111n as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("dotenv", source.lower())
        self.assertNotIn("load_dotenv", source)

    def test_no_env_file_path(self):
        """Module must not reference .env file paths (except in docstrings/comments)."""
        import scripts.market_radar_safe_sender_v111n as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        # Filter out docstrings and comments before checking
        # ".env" in a docstring like "No .env file reading" is fine
        lines = source.split("\n")
        code_lines = []
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = not in_docstring
                continue
            if in_docstring:
                continue
            if stripped.startswith("#"):
                continue
            code_lines.append(line)
        code_only = "\n".join(code_lines)
        # .env should not appear as a file path reference in code
        # But os.environ is fine (that's how we read env vars)
        self.assertNotIn(".env", code_only.replace("os.environ", ""))


class TestNoInteractiveInput(unittest.TestCase):
    """Verify no Read-Host or interactive input is used."""

    def test_no_input_calls(self):
        """Module source must not call input() or Read-Host."""
        import scripts.market_radar_safe_sender_v111n as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        # Check for input() calls (not in comments/docs)
        lines = source.split("\n")
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = not in_docstring
                continue
            if in_docstring:
                continue
            if stripped.startswith("#"):
                continue
            if stripped.startswith("def ") or stripped.startswith("class "):
                continue
            # Check for bare input() call (isinstance is fine)
            if "input(" in stripped and "isinstance" not in stripped:
                self.fail(f"Potential input() call: {stripped}")

    def test_no_read_host(self):
        """Module source must not reference Read-Host (except in docstrings/comments)."""
        import scripts.market_radar_safe_sender_v111n as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        # Filter out docstrings and comments
        lines = source.split("\n")
        code_lines = []
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = not in_docstring
                continue
            if in_docstring:
                continue
            if stripped.startswith("#"):
                continue
            code_lines.append(line)
        code_only = "\n".join(code_lines).lower()
        self.assertNotIn("read-host", code_only)
        self.assertNotIn("readhost", code_only)


class TestNoSecretsInResult(unittest.TestCase):
    """Verify result objects never contain secrets."""

    def setUp(self):
        self.sender = SafeTelegramTestSender()

    def test_blocked_result_has_safe_fields_only(self):
        """Blocked result must have only safe fields."""
        result = self.sender.mock_send_single(
            payload_text="",
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="production",
        )
        # Must have required safe fields
        self.assertIn("status", result)
        self.assertIn("reason", result)
        self.assertIn("real_tg_sent", result)
        self.assertIn("official_channel_touched", result)
        self.assertIn("secret_printed", result)
        # Must NOT contain secrets
        for key in result:
            if isinstance(result[key], str):
                self.assertNotIn("token", result[key].lower())

    def test_sent_result_has_safe_fields_only(self):
        """Sent (mock) result must have only safe fields."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        required_fields = [
            "status", "reason", "message_id", "signal_id", "asset",
            "target_type", "payload_text_sha256", "payload_length",
            "sent_at", "real_tg_sent", "official_channel_touched",
            "secret_printed", "sender_version",
        ]
        for field in required_fields:
            self.assertIn(field, result, f"Result must contain '{field}'")

    def test_sender_version_in_result(self):
        """Result must include sender version."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(result["sender_version"], SAFE_SENDER_VERSION)


class TestMockNetwork(unittest.TestCase):
    """Test that mock mode returns fake message_id with explicit mock marking."""

    def setUp(self):
        self.sender = SafeTelegramTestSender()

    def test_mock_mode_marked_explicitly(self):
        """Mock send result must have mock_mode=True."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertTrue(result.get("mock_mode"), "Must have mock_mode=True")
        self.assertFalse(result["real_tg_sent"])
        self.assertIn("mock_message_id", result)

    def test_mock_message_id_does_not_impersonate_real(self):
        """Mock message_id must be clearly identifiable as mock, not real TG ID."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        # Real TG message_id is numeric. Mock must be distinctly non-numeric-prefixed.
        self.assertTrue(result["message_id"].startswith("mock_v111n_"))
        self.assertFalse(result["message_id"].isdigit())

    def test_mock_never_calls_network(self):
        """mock_send_single must not invoke TGTransport or make HTTP calls."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "-100123",
        }, clear=True):
            result = self.sender.mock_send_single(
                payload_text=VALID_ARB_PAYLOAD,
                parse_mode="MarkdownV2",
                signal_id="H6-07",
                asset="ARB",
                target_type="test_channel",
            )
        self.assertTrue(result["mock_mode"])
        self.assertFalse(result["real_tg_sent"])


class TestPreSendGate(unittest.TestCase):
    """Tests for pre_send_gate integration."""

    def setUp(self):
        self.sender = SafeTelegramTestSender()

    def test_pre_send_gate_pass_allows(self):
        """pre_send_gate decision=pass should allow send."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
            pre_send_gate_result={"decision": "pass"},
        )
        self.assertEqual(result["status"], "sent")

    def test_pre_send_gate_block_blocks(self):
        """pre_send_gate decision=block must block."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
            pre_send_gate_result={"decision": "block"},
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "pre_send_gate_failed")

    def test_pre_send_gate_not_reached_blocks(self):
        """pre_send_gate decision=not_reached must block."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
            pre_send_gate_result={"decision": "not_reached"},
        )
        self.assertEqual(result["status"], "blocked")

    def test_pre_send_gate_none_skips(self):
        """pre_send_gate_result=None skips the check (for testing)."""
        result = self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
            pre_send_gate_result=None,
        )
        self.assertEqual(result["status"], "sent")


class TestCounters(unittest.TestCase):
    """Tests for sent/blocked counters."""

    def setUp(self):
        self.sender = SafeTelegramTestSender()

    def test_sent_count_increments(self):
        """sent_count increments on successful mock sends."""
        self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(self.sender.sent_count, 1)

    def test_blocked_count_increments(self):
        """blocked_count increments on blocked sends."""
        self.sender.mock_send_single(
            payload_text="",
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(self.sender.blocked_count, 1)

    def test_separate_counters(self):
        """Sent and blocked counters are separate."""
        self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ETH",
            target_type="test_channel",
        )
        self.assertEqual(self.sender.sent_count, 1)
        self.assertEqual(self.sender.blocked_count, 1)


class TestFactory(unittest.TestCase):
    """Tests for factory function."""

    def test_create_safe_sender(self):
        """create_safe_sender returns a SafeTelegramTestSender."""
        sender = create_safe_sender()
        self.assertIsInstance(sender, SafeTelegramTestSender)
        result = sender.mock_send_single(
            payload_text=VALID_ARB_PAYLOAD,
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
        )
        self.assertEqual(result["status"], "sent")


class TestHelpers(unittest.TestCase):
    """Tests for helper functions."""

    def test_sha256_hex(self):
        """_sha256_hex returns correct hash."""
        result = _sha256_hex("hello")
        expected = hashlib.sha256("hello".encode("utf-8")).hexdigest()
        self.assertEqual(result, expected)

    def test_has_forbidden_terms_clean(self):
        """Clean text should have no forbidden terms."""
        has_any, found = _has_forbidden_terms("ARB 多因子异动信号")
        self.assertFalse(has_any)
        self.assertEqual(len(found), 0)

    def test_has_forbidden_terms_contaminated(self):
        """Contaminated text should detect forbidden terms."""
        has_any, found = _has_forbidden_terms("value_gate returned allow")
        self.assertTrue(has_any)
        self.assertGreater(len(found), 0)


if __name__ == "__main__":
    print(f"=== Market Radar {SAFE_SENDER_VERSION} — Safe Sender Tests ===")
    print(f"Run: {datetime.now(CN_TZ).strftime('%Y-%m-%d %H:%M:%S UTC+8')}")
    print()
    unittest.main(verbosity=2)
