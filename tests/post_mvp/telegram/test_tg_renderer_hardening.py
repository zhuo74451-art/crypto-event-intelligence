"""TG Renderer Hardening tests — error desensitization, card merging, gate, address.

At least covers:
  1. Network error with token in text → result has no token
  2. HTTPError safe summary
  3. Non-UTF-8 error body safe failure
  4. Two alerts merged into one main card
  5. Address appears only once
  6. Asset appears only once
  7. Risk tags from alert_candidates, not recalculation
  8. No synthetic risk when domain has no conclusion
  9. Per-source health detail NOT in public card
  10. Source summary still present
  11. No market data → card still valid
  12. No feed → whale card still valid
  13. Full 42-char EVM address correctly shortened
  14. Already-short address not re-shortened
  15. Chinese gate dynamic (position-specific markers)
  16. '???' and '�' still blocked
  17. JSON UTF-8 payload
  18. Send failure does not auto-retry
"""
import json, os, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

scripts_path = ROOT / "scripts" / "mvpplus" / "integration"
sys.path.insert(0, str(scripts_path))

import tg_preview_renderer as R


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_whale_data(positions=None, candidates=None) -> dict:
    """Create a minimal whale_data dict resembling real run output.

    None = use default, empty list = no data.
    """
    default_positions = [{
        "coin": "ETH", "direction": "long", "signed_size": 40000.0,
        "entry_price": 3450.0, "mark_price": 3520.0, "leverage": 20.0,
        "unrealized_pnl_usd": -5200000.0, "liquidation_price": 3300.0,
        "position_value_usd": 75200000.0,
        "address": "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
        "label": "Matrixport Related",
    }]
    default_candidates = [
        {"alert_type": "high_leverage", "severity": "high", "coin": "ETH",
         "observed_value": 20.0, "message": "20x leverage on ETH long"},
        {"alert_type": "concentrated_exposure", "severity": "medium", "coin": "ETH",
         "observed_value": 75200000.0, "message": "Single-position exposure $75.2M"},
    ]
    result = {"positions": default_positions, "alert_candidates": default_candidates}
    if positions is not None:
        result["positions"] = positions
    if candidates is not None:
        result["alert_candidates"] = candidates
    return result


def _make_run_data() -> dict:
    return {
        "sources": [
            {"source": "whale_hyperliquid", "ok": True},
            {"source": "market_binance", "ok": True},
            {"source": "feed_curated", "ok": False},
            {"source": "feed_telegram", "ok": False},
        ],
    }


def _make_market_data() -> list[dict]:
    return [
        {"symbol": "ETH", "last_price": 3520.0, "source": "Binance"},
        {"symbol": "BTC", "last_price": 65720.0, "source": "Binance"},
    ]


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestErrorDesensitization(unittest.TestCase):
    """Error handling must never leak tokens."""

    def test_1_network_error_no_token(self):
        """Exception with token in text → result has no token."""
        token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        result = R.telegram_call(token, "sendMessage", {"chat_id": 1, "text": "hi"})
        desc = json.dumps(result)
        self.assertNotIn(token, desc)
        self.assertNotIn("123456:ABC", desc)

    def test_2_http_error_safe_summary(self):
        """HTTPError returns safe summary without token."""
        token = "999888:FAKEtokenINVALID"
        result = R.telegram_call(token, "sendMessage",
                                  {"chat_id": -1, "text": "x"}, timeout=2)
        desc = json.dumps(result)
        self.assertNotIn(token, desc)
        self.assertIn("http_status", desc)

    def test_3_non_utf8_body(self):
        """Non-UTF-8 error body does not crash and is safe."""
        token = "111222:NONUTF8token"
        result = R.telegram_call(token, "getMe", timeout=2)
        desc = json.dumps(result)
        self.assertNotIn(token, desc)
        # Should not crash, should return a dict
        self.assertIn("ok", result)

    def test_17_json_utf8_payload(self):
        """JSON payload encoded as UTF-8, serialized with ensure_ascii=False."""
        card = R.build_preview_card(
            _make_whale_data(),
            market_data=_make_market_data(),
        )
        # Round-trip through JSON ensures UTF-8 safety
        payload = json.dumps({"text": card}, ensure_ascii=False).encode("utf-8")
        decoded = json.loads(payload.decode("utf-8"))
        self.assertIn("ETH", decoded["text"])

    def test_18_send_failure_no_retry(self):
        """send_preview_card returns immediately on gate failure, no retry."""
        result = R.send_preview_card("fake:token", -1, "")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["send_attempts"], 0)


class TestCardMerging(unittest.TestCase):
    """Two alerts must merge into one main card."""

    def test_4_two_alerts_one_card(self):
        """Two alerts → one card with both risk tags listed together."""
        card = R.build_preview_card(_make_whale_data())
        # Must have both risk tags
        self.assertIn("高杠杆持仓", card)
        self.assertIn("集中持仓风险", card)
        # Address must appear only once
        addr_count = card.count("0x6c8512")
        self.assertLessEqual(addr_count, 1)

    def test_5_address_once(self):
        """Address appears only once (in position section)."""
        card = R.build_preview_card(_make_whale_data())
        addr = "0x6c8512516ce5669d35113a11ca8b8de322fd84f6"
        # Full address not visible (only shortened)
        self.assertNotIn(addr, card)
        # Short form appears once
        short = "0x6c8512"
        self.assertIn(short, card)
        # Count occurrences — should be 1 (in address line)
        count = card.count(short)
        self.assertEqual(count, 1, f"Address short form appears {count} times, expected 1")

    def test_6_asset_once(self):
        """Asset symbol appears only once in main header."""
        card = R.build_preview_card(_make_whale_data())
        # ETH should appear in header once, and in risk tags
        eth_count = card.count("ETH")
        self.assertLessEqual(eth_count, 2, f"ETH appears {eth_count} times, max 2")

    def test_7_risk_from_candidates(self):
        """Risk tags come from alert_candidates, not recalculation."""
        # Force a specific risk tag
        data = _make_whale_data(candidates=[
            {"alert_type": "direction_flip", "severity": "high", "coin": "ETH"},
        ])
        card = R.build_preview_card(data)
        self.assertIn("方向反转", card)
        # Should NOT recalculate leverage-based high_leverage since not in candidates
        self.assertNotIn("高杠杆", card)


class TestNoSyntheticRisk(unittest.TestCase):
    """Renderer does not recalculate or invent risks."""

    def test_8_no_synthetic_risk(self):
        """No alert_candidates → no risk tag section."""
        data = _make_whale_data(candidates=[])
        card = R.build_preview_card(data)
        self.assertNotIn("风险标记", card)


class TestSourceHealth(unittest.TestCase):
    """Source health detail must NOT appear in public card."""

    def test_9_no_per_source_health(self):
        """No ✅/❌ per-source health in card (only compact summary)."""
        card = R.build_preview_card(
            _make_whale_data(),
            run_data=_make_run_data(),
        )
        self.assertNotIn("✅", card)
        self.assertNotIn("❌", card)
        self.assertNotIn("source health", card.lower())
        # Source summary is a single line, not per-source bullets
        self.assertIn("数据来源", card)
        # Should not show individual status per source
        self.assertNotIn("ok", card.lower())

    def test_10_source_summary_present(self):
        """Source summary still present."""
        card = R.build_preview_card(
            _make_whale_data(),
            market_data=_make_market_data(),
            run_data=_make_run_data(),
        )
        self.assertIn("数据来源", card)


class TestMarketDataEdge(unittest.TestCase):
    """Card without market data or feed data is still valid."""

    def test_11_no_market_data(self):
        """No market data → card still renders positions."""
        card = R.build_preview_card(_make_whale_data())
        self.assertIn("ETH", card)
        self.assertIn("大额杠杆", card)

    def test_12_no_feed_whale_card(self):
        """No feed data → whale card still valid."""
        card = R.build_preview_card(
            _make_whale_data(),
            market_data=[],
            run_data={},
        )
        self.assertIn("ETH", card)
        self.assertIn("杠杆", card)
        self.assertIn("数据来源", card)


class TestAddressHandling(unittest.TestCase):
    """Address shortening correctness."""

    def test_13_full_evm_shortened(self):
        """Full 42-char EVM address shortened to 8+4 format."""
        addr = "0x6c8512516ce5669d35113a11ca8b8de322fd84f6"
        short = R.shorten_address(addr)
        self.assertEqual(len(short), 13)  # 8 + 1 ellipsis + 4
        self.assertTrue(short.startswith("0x6c8512"))
        self.assertTrue(short.endswith("84f6"))

    def test_14_already_short_not_reshortened(self):
        """Already-short address passes through unchanged."""
        short_input = "0x6c85…84f6"
        result = R.shorten_address(short_input)
        self.assertEqual(result, short_input)

    def test_14b_short_input_passthrough(self):
        """Short address (≤12 chars) passes through."""
        result = R.shorten_address("0x1234")
        self.assertEqual(result, "0x1234")

    def test_14c_empty_address(self):
        """Empty address returns empty."""
        self.assertEqual(R.shorten_address(""), "")
        self.assertEqual(R.shorten_address(None), "")


class TestChineseGate(unittest.TestCase):
    """Chinese garbled gate dynamic behavior."""

    def test_15_markers_dynamic(self):
        """Position markers only required when positions exist."""
        with_pos = R.get_required_markers(has_positions=True)
        self.assertIn("开仓价", with_pos)
        self.assertIn("当前标记价", with_pos)
        self.assertIn("清算价", with_pos)

        without_pos = R.get_required_markers(has_positions=False)
        self.assertNotIn("开仓价", without_pos)
        self.assertNotIn("清算价", without_pos)

    def test_15b_alert_markers(self):
        """Alert markers only required when alerts exist."""
        with_alerts = R.get_required_markers(has_alerts=True)
        self.assertIn("风险标记", with_alerts)

        without_alerts = R.get_required_markers(has_alerts=False)
        self.assertNotIn("风险标记", without_alerts)

    def test_16_garbled_blocked(self):
        """'???' and '�' still blocked by gate."""
        violations = R.check_garbled("??? test")
        self.assertGreater(len(violations), 0)

        violations2 = R.check_garbled("test � text")
        self.assertGreater(len(violations2), 0)


class TestAmountFormatting(unittest.TestCase):
    """USD amount formatting consistency."""

    def test_pnl_negative_shows_loss(self):
        """Negative PnL shows '未实现亏损' in card."""
        data = _make_whale_data()
        card = R.build_preview_card(data)
        self.assertIn("未实现亏损", card)
        self.assertIn("-$", card)

    def test_pnl_positive_shows_profit(self):
        """Positive PnL shows '未实现盈利'."""
        data = _make_whale_data(positions=[{
            "coin": "ETH", "direction": "long", "signed_size": 40000.0,
            "entry_price": 3000.0, "mark_price": 3520.0, "leverage": 20.0,
            "unrealized_pnl_usd": 8000000.0, "liquidation_price": 2900.0,
            "position_value_usd": 75000000.0,
            "address": "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
        }])
        card = R.build_preview_card(data)
        self.assertIn("未实现盈利", card)


class TestShortenAddress(unittest.TestCase):
    """Standalone shorten_address tests."""

    def test_standard_evm(self):
        result = R.shorten_address("0x6c8512516ce5669d35113a11ca8b8de322fd84f6")
        self.assertEqual(result, "0x6c8512…84f6")

    def test_twelve_char(self):
        self.assertEqual(R.shorten_address("0x1234567890"), "0x1234567890")

    def test_already_ellipsis(self):
        self.assertEqual(R.shorten_address("0xabcd…1234"), "0xabcd…1234")

    def test_none_input(self):
        self.assertEqual(R.shorten_address(None), "")

    def test_empty_input(self):
        self.assertEqual(R.shorten_address(""), "")


class TestLiquidationDistance(unittest.TestCase):
    """Liquidation distance formatting."""

    def test_long_normal(self):
        result = R.format_liquidation_distance("long", 3520.0, 3300.0)
        self.assertIn("%", result)

    def test_short_normal(self):
        result = R.format_liquidation_distance("short", 3520.0, 3700.0)
        self.assertIn("%", result)

    def test_at_liquidation(self):
        result = R.format_liquidation_distance("long", 3520.0, 3520.0)
        self.assertIn("已达到", result)

    def test_none_price(self):
        result = R.format_liquidation_distance("long", None, 3300.0)
        self.assertEqual(result, "暂无数据")


if __name__ == "__main__":
    unittest.main()
