"""Tests for Market Radar v1.11-J-Mock — MockTelegramSender

Coverage:
  - test_channel can mock send
  - formal_channel must block
  - prod / production must block
  - empty payload must block
  - missing parse_mode or invalid parse_mode must block
  - single send over 3 images must block
  - mock_message_id deterministic
  - no environment variable reading
  - no real network requests

Usage:
    python scripts/test_market_radar_mock_sender_v111j.py
    python -m pytest scripts/test_market_radar_mock_sender_v111j.py -v
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_mock_sender_v111j import (
    MockTelegramSender,
    MOCK_SENDER_VERSION,
    BLOCKED_TARGET_TYPES,
    VALID_PARSE_MODES,
    MAX_CARDS_PER_SEND,
    MAX_PREVIEW_CHARS,
    create_mock_sender,
    validate_mock_send_input,
)


class TestMockTelegramSenderBasic(unittest.TestCase):
    """Basic functionality tests."""

    def setUp(self):
        self.sender = MockTelegramSender(counter_start=1)

    def test_test_channel_mock_send_succeeds(self):
        """test_channel can mock send successfully."""
        result = self.sender.mock_send(
            payload_text="Hello World",
            parse_mode="MarkdownV2",
            signal_id="H6-07",
            asset="ARB",
            target_type="test_channel",
            target_alias="market_radar_test_channel",
            pre_send_gate_result={"decision": "pass"},
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["send_status"], "mock_sent")
        self.assertEqual(result["mock_message_id"], "mock_v111j_001")
        self.assertFalse(result["network_called"])
        self.assertFalse(result["real_tg_sent"])

    def test_mock_message_id_deterministic(self):
        """mock_message_id is deterministic and sequential."""
        sender = MockTelegramSender(counter_start=1)

        ids = []
        for i in range(3):
            result = sender.mock_send(
                payload_text=f"Card {i + 1}",
                parse_mode="MarkdownV2",
                signal_id=f"H{i}-01",
                asset="ETH",
            )
            ids.append(result["mock_message_id"])

        self.assertEqual(ids, ["mock_v111j_001", "mock_v111j_002", "mock_v111j_003"])

    def test_mock_message_id_format(self):
        """mock_message_id follows the expected format."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
        )
        mid = result["mock_message_id"]
        self.assertTrue(mid.startswith("mock_v111j_"))
        self.assertEqual(len(mid), len("mock_v111j_001"))
        # Sequence number should be 3-digit zero-padded
        seq = mid.split("_")[-1]
        self.assertEqual(len(seq), 3)
        self.assertTrue(seq.isdigit())

    def test_sent_log_records_messages(self):
        """Sent log correctly tracks all sent messages."""
        self.sender.mock_send(
            payload_text="Card A",
            parse_mode="MarkdownV2",
            signal_id="A-01",
            asset="ETH",
        )
        self.sender.mock_send(
            payload_text="Card B",
            parse_mode="MarkdownV2",
            signal_id="B-01",
            asset="BTC",
        )
        self.assertEqual(len(self.sender.sent_log), 2)
        self.assertEqual(self.sender.sent_count, 2)

    def test_payload_preview_truncated(self):
        """Payload preview is truncated to MAX_PREVIEW_CHARS."""
        long_text = "x" * 500
        result = self.sender.mock_send(
            payload_text=long_text,
            parse_mode="MarkdownV2",
            signal_id="X-01",
            asset="BTC",
        )
        self.assertLessEqual(len(result["payload_preview"]), MAX_PREVIEW_CHARS)
        self.assertEqual(result["payload_length"], 500)

    def test_payload_sha256_correct(self):
        """Payload SHA-256 hash is correct."""
        text = "Hello World"
        expected_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        result = self.sender.mock_send(
            payload_text=text,
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
        )
        self.assertEqual(result["payload_text_sha256"], expected_hash)

    def test_sender_version_in_result(self):
        """Result includes the sender version."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
        )
        self.assertEqual(result["sender_version"], MOCK_SENDER_VERSION)


class TestTargetBlocking(unittest.TestCase):
    """Tests for target_type blocking."""

    def setUp(self):
        self.sender = MockTelegramSender(counter_start=1)

    def test_formal_channel_blocked(self):
        """formal_channel must be blocked."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="formal_channel",
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["send_status"], "blocked")
        self.assertIn("blocked", result["blocked_reason"].lower())
        self.assertEqual(self.sender.blocked_count, 1)

    def test_official_channel_blocked(self):
        """official_channel must be blocked."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="official_channel",
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["send_status"], "blocked")

    def test_prod_blocked(self):
        """prod must be blocked."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="prod",
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["send_status"], "blocked")

    def test_production_blocked(self):
        """production must be blocked."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="production",
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["send_status"], "blocked")

    def test_main_channel_blocked(self):
        """main_channel must be blocked."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="main_channel",
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["send_status"], "blocked")

    def test_empty_target_type_blocked(self):
        """Empty target_type must be blocked."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="",
        )
        self.assertFalse(result["success"])

    def test_unknown_target_type_blocked(self):
        """Unknown target_type (not test_channel, not blocked list) should be blocked."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="random_channel",
        )
        self.assertFalse(result["success"])
        self.assertIn("not", result["blocked_reason"].lower())

    def test_case_insensitive_prod_blocked(self):
        """PRODUCTION (uppercase) must be blocked."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="PRODUCTION",
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["send_status"], "blocked")


class TestPayloadValidation(unittest.TestCase):
    """Tests for payload validation."""

    def setUp(self):
        self.sender = MockTelegramSender(counter_start=1)

    def test_empty_payload_blocked(self):
        """Empty payload text must be blocked."""
        result = self.sender.mock_send(
            payload_text="",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="test_channel",
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["send_status"], "blocked")
        self.assertIn("empty", result["blocked_reason"].lower())

    def test_whitespace_only_payload_blocked(self):
        """Whitespace-only payload must be blocked."""
        result = self.sender.mock_send(
            payload_text="   \n\t  ",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="test_channel",
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["send_status"], "blocked")

    def test_none_payload_blocked(self):
        """None payload text must be blocked."""
        result = self.sender.mock_send(
            payload_text=None,
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="test_channel",
        )
        self.assertFalse(result["success"])

    def test_valid_parse_modes_accepted(self):
        """Valid parse_modes (MarkdownV2, Markdown, HTML, None) are accepted."""
        for mode in ["MarkdownV2", "Markdown", "HTML", None]:
            result = self.sender.mock_send(
                payload_text="Test",
                parse_mode=mode,
                signal_id="H1-01",
                asset="BTC",
                target_type="test_channel",
            )
            self.assertTrue(result["success"], f"parse_mode={mode} should be accepted")

    def test_invalid_parse_mode_blocked(self):
        """Invalid parse_mode must be blocked."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="InvalidMode",
            signal_id="H1-01",
            asset="BTC",
            target_type="test_channel",
        )
        self.assertFalse(result["success"])
        self.assertIn("parse_mode", result["blocked_reason"].lower())

    def test_pre_send_gate_fail_blocked(self):
        """pre_send_gate decision != 'pass' must block."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="test_channel",
            pre_send_gate_result={"decision": "block"},
        )
        self.assertFalse(result["success"])
        self.assertIn("pre_send_gate", result["blocked_reason"].lower())

    def test_pre_send_gate_pass_succeeds(self):
        """pre_send_gate decision == 'pass' allows send."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="test_channel",
            pre_send_gate_result={"decision": "pass"},
        )
        self.assertTrue(result["success"])

    def test_pre_send_gate_none_skips_check(self):
        """pre_send_gate_result=None skips the gate check (lenient for testing)."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="test_channel",
            pre_send_gate_result=None,
        )
        self.assertTrue(result["success"])

    def test_pre_send_gate_not_reached_blocked(self):
        """pre_send_gate decision='not_reached' must block."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="test_channel",
            pre_send_gate_result={"decision": "not_reached"},
        )
        self.assertFalse(result["success"])


class TestImageCountLimit(unittest.TestCase):
    """Tests for image count limits."""

    def setUp(self):
        self.sender = MockTelegramSender(counter_start=1)

    def test_four_images_blocked(self):
        """Single send with 4 images must be blocked."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="test_channel",
            image_count=4,
        )
        self.assertFalse(result["success"])
        self.assertIn("image_count", result["blocked_reason"].lower())

    def test_three_images_allowed(self):
        """Single send with exactly 3 images should pass."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="test_channel",
            image_count=3,
        )
        self.assertTrue(result["success"])

    def test_zero_images_allowed(self):
        """Zero images should be allowed (text-only card)."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
            target_type="test_channel",
            image_count=0,
        )
        self.assertTrue(result["success"])


class TestBatchSend(unittest.TestCase):
    """Tests for batch send functionality."""

    def setUp(self):
        self.sender = MockTelegramSender(counter_start=1)

    def test_batch_three_cards_succeeds(self):
        """Batch of 3 cards should succeed."""
        cards = [
            {"payload_text": f"Card {i}", "parse_mode": "MarkdownV2",
             "signal_id": f"H{i}-01", "asset": "BTC"}
            for i in range(3)
        ]
        result = self.sender.mock_send_batch(cards)
        self.assertTrue(result["success"])
        self.assertEqual(result["sent_count"], 3)
        self.assertEqual(result["blocked_count"], 0)
        self.assertFalse(result["network_called"])

    def test_batch_four_cards_blocked(self):
        """Batch of 4 cards should be blocked entirely."""
        cards = [
            {"payload_text": f"Card {i}", "parse_mode": "MarkdownV2",
             "signal_id": f"H{i}-01", "asset": "BTC"}
            for i in range(4)
        ]
        result = self.sender.mock_send_batch(cards)
        self.assertFalse(result["success"])
        self.assertIn("batch size", result["blocked_reason"].lower())

    def test_batch_empty_cards_ok(self):
        """Empty batch is fine (0 cards <= max)."""
        result = self.sender.mock_send_batch([])
        self.assertTrue(result["success"])
        self.assertEqual(result["sent_count"], 0)


class TestNoSecretsOrNetwork(unittest.TestCase):
    """Verify no secrets are read, no network calls are made."""

    def setUp(self):
        self.sender = MockTelegramSender(counter_start=1)

    def test_no_environment_variable_read(self):
        """MockTelegramSender never reads env vars."""
        with patch.dict(os.environ, {}, clear=True):
            result = self.sender.mock_send(
                payload_text="Test",
                parse_mode="MarkdownV2",
                signal_id="H1-01",
                asset="BTC",
                target_type="test_channel",
            )
        self.assertTrue(result["success"])
        self.assertFalse(result["network_called"])

    def test_network_called_always_false(self):
        """network_called is always False in all result types."""
        # Success case
        r1 = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
        )
        self.assertFalse(r1["network_called"])

        # Blocked case
        r2 = self.sender.mock_send(
            payload_text="",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
        )
        self.assertFalse(r2["network_called"])

    def test_real_tg_sent_always_false(self):
        """real_tg_sent is always False."""
        result = self.sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
        )
        self.assertFalse(result["real_tg_sent"])

    def test_no_token_or_key_in_result(self):
        """Result never contains token, key, password fields."""
        result = self.sender.mock_send(
            payload_text="Test with token=abc123",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
        )
        result_keys = set(str(k).lower() for k in result.keys())
        for forbidden in ["token", "key", "password", "secret", "cookie", "chat_id"]:
            self.assertNotIn(forbidden, result_keys,
                             f"Result should not contain '{forbidden}' field")


class TestFactoryAndHelpers(unittest.TestCase):
    """Tests for factory function and standalone helpers."""

    def test_create_mock_sender(self):
        """create_mock_sender returns a fresh MockTelegramSender."""
        sender = create_mock_sender(counter_start=5)
        result = sender.mock_send(
            payload_text="Test",
            parse_mode="MarkdownV2",
            signal_id="H1-01",
            asset="BTC",
        )
        self.assertEqual(result["mock_message_id"], "mock_v111j_005")

    def test_validate_mock_send_input_valid(self):
        """validate_mock_send_input returns valid=True for good input."""
        result = validate_mock_send_input(
            payload_text="Test",
            parse_mode="MarkdownV2",
            target_type="test_channel",
            pre_send_gate_result={"decision": "pass"},
        )
        self.assertTrue(result["valid"])

    def test_validate_mock_send_input_blocked_target(self):
        """validate_mock_send_input blocks formal_channel."""
        result = validate_mock_send_input(
            payload_text="Test",
            parse_mode="MarkdownV2",
            target_type="formal_channel",
        )
        self.assertFalse(result["valid"])

    def test_validate_mock_send_input_empty_payload(self):
        """validate_mock_send_input blocks empty payload."""
        result = validate_mock_send_input(
            payload_text="",
            parse_mode="MarkdownV2",
            target_type="test_channel",
        )
        self.assertFalse(result["valid"])

    def test_validate_mock_send_input_invalid_parse_mode(self):
        """validate_mock_send_input blocks invalid parse_mode."""
        result = validate_mock_send_input(
            payload_text="Test",
            parse_mode="BadMode",
            target_type="test_channel",
        )
        self.assertFalse(result["valid"])

    def test_validate_mock_send_input_too_many_images(self):
        """validate_mock_send_input blocks too many images."""
        result = validate_mock_send_input(
            payload_text="Test",
            parse_mode="MarkdownV2",
            target_type="test_channel",
            image_count=5,
        )
        self.assertFalse(result["valid"])

    def test_validate_mock_send_input_gate_fail(self):
        """validate_mock_send_input blocks on gate failure."""
        result = validate_mock_send_input(
            payload_text="Test",
            parse_mode="MarkdownV2",
            target_type="test_channel",
            pre_send_gate_result={"decision": "block"},
        )
        self.assertFalse(result["valid"])


class TestCounterAndState(unittest.TestCase):
    """Tests for counter management and state."""

    def setUp(self):
        self.sender = MockTelegramSender(counter_start=1)

    def test_reset_counter(self):
        """reset_counter resets the message_id sequence."""
        self.sender.mock_send(
            payload_text="A", parse_mode="MarkdownV2",
            signal_id="A-01", asset="BTC",
        )
        self.sender.mock_send(
            payload_text="B", parse_mode="MarkdownV2",
            signal_id="B-01", asset="BTC",
        )
        self.assertEqual(self.sender.sent_count, 2)

        self.sender.reset_counter(start=1)
        result = self.sender.mock_send(
            payload_text="C", parse_mode="MarkdownV2",
            signal_id="C-01", asset="BTC",
        )
        self.assertEqual(result["mock_message_id"], "mock_v111j_001")

    def test_sent_count_and_blocked_count(self):
        """Counters correctly track sent vs blocked."""
        # 2 sent
        self.sender.mock_send(
            payload_text="A", parse_mode="MarkdownV2",
            signal_id="A-01", asset="BTC",
        )
        self.sender.mock_send(
            payload_text="B", parse_mode="MarkdownV2",
            signal_id="B-01", asset="BTC",
        )
        # 2 blocked
        self.sender.mock_send(
            payload_text="", parse_mode="MarkdownV2",
            signal_id="C-01", asset="BTC",
        )
        self.sender.mock_send(
            payload_text="D", parse_mode="MarkdownV2",
            signal_id="D-01", asset="BTC",
            target_type="prod",
        )
        self.assertEqual(self.sender.sent_count, 2)
        self.assertEqual(self.sender.blocked_count, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
