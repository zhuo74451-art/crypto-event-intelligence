"""Tests for Telegram preview renderer."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.mvpplus.integration.tg_preview_renderer import (
    build_preview_card, check_garbled, format_liquidation_distance,
    format_amount_usd, shorten_address, get_required_markers,
)

# Get expected markers for a whale card with positions and alerts
REQUIRED_CHINESE_MARKERS = get_required_markers(
    has_positions=True, has_alerts=True, has_whale_data=True,
)


class TestChineseIntegrity(unittest.TestCase):

    def setUp(self):
        self.whale_data = {"ok": True, "position_count": 1,
            "positions": [{"address": "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
                "coin": "ETH", "signed_size": 40000.0, "entry_price": 2265.44,
                "mark_price": 1749.75, "position_value_usd": 69992000.0,
                "leverage": 20.0, "unrealized_pnl_usd": -20625764.97,
                "liquidation_price": 1164.92,
                "snapshot_time_utc": "2026-06-18T08:47:49Z"}],
            "changes": [], "alert_candidates": [
                {"alert_id": "w2:b4709c3a89bf0724", "alert_type": "high_leverage",
                 "severity": "medium", "coin": "ETH", "label": "0x6c851251",
                 "address_short": "0x6c851251", "message": "HIGH LEVERAGE ETH: 20.0x",
                 "observed_value": 20.0, "generated_at_utc": "2026-06-18T08:47:49Z"}],
            "is_baseline": True}
        self.run_data = {"sources": [
            {"source": "whale:0x6c851251", "ok": True},
            {"source": "ccxt:BTC/USDT", "ok": True}]}

    def test_chinese_in_preview(self):
        card = build_preview_card(self.whale_data, [], self.run_data)
        for marker in REQUIRED_CHINESE_MARKERS:
            self.assertIn(marker, card)

    def test_utf8_roundtrip(self):
        card = build_preview_card(self.whale_data, [], self.run_data)
        self.assertEqual(card, card.encode("utf-8").decode("utf-8"))

    def test_json_roundtrip(self):
        card = build_preview_card(self.whale_data, [], self.run_data)
        self.assertEqual(card, json.loads(json.dumps(
            {"text": card}, ensure_ascii=False))["text"])

    def test_no_question_marks(self):
        card = build_preview_card(self.whale_data, [], self.run_data)
        self.assertNotIn("???", card)

    def test_no_replacement_char(self):
        card = build_preview_card(self.whale_data, [], self.run_data)
        self.assertNotIn(chr(65533), card)


class TestLiquidationDistance(unittest.TestCase):
    def test_long_normal(self):
        r = format_liquidation_distance("long", 1749.75, 1164.92)
        self.assertIn("33.4", r)
        self.assertNotIn("-", r)

    def test_short_normal(self):
        r = format_liquidation_distance("short", 100.0, 120.0)
        self.assertIn("20.0", r)
        self.assertNotIn("-", r)

    def test_past_long(self):
        self.assertIn("越过", format_liquidation_distance("long", 1000.0, 1200.0))

    def test_past_short(self):
        self.assertIn("越过", format_liquidation_distance("short", 1200.0, 1000.0))

    def test_no_mark(self):
        self.assertIn("暂无", format_liquidation_distance("long", None, 1164.92))

    def test_no_liq(self):
        self.assertIn("暂无", format_liquidation_distance("long", 1749.75, None))

    def test_zero_mark(self):
        self.assertIn("暂无", format_liquidation_distance("long", 0.0, 1164.92))


class TestGarbledGate(unittest.TestCase):
    def test_clean_passes(self):
        t = "\n".join(["head"] + REQUIRED_CHINESE_MARKERS + ["data: now"])
        self.assertEqual(check_garbled(t), [])

    def test_question_marks_fails(self):
        self.assertTrue(any("?" in v for v in check_garbled("??? bad")))

    def test_replacement_fails(self):
        self.assertTrue(any("FFFD" in v for v in check_garbled(chr(65533))))

    def test_empty_fails(self):
        self.assertTrue(any("empty" in v for v in check_garbled("")))

    def test_single_question_ok(self):
        t = "\n".join(["Sure?"] + REQUIRED_CHINESE_MARKERS + ["data"])
        self.assertEqual(check_garbled(t), [])


class TestFormatAmount(unittest.TestCase):
    def test_millions(self):
        self.assertIn("20.6M", format_amount_usd(-20625764.97))

    def test_billions(self):
        self.assertIn("1.5B", format_amount_usd(1500000000))

    def test_none(self):
        self.assertIn("暂无", format_amount_usd(None))

    def test_negative(self):
        self.assertTrue(format_amount_usd(-5000000).startswith("-"))


class TestShortenAddress(unittest.TestCase):
    def test_long(self):
        a = "0x6c8512516ce5669d35113a11ca8b8de322fd84f6"
        self.assertEqual(shorten_address(a), "0x6c8512…84f6")

    def test_short(self):
        self.assertEqual(shorten_address("0x1234"), "0x1234")
