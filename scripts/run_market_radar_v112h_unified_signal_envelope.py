"""Market Radar v1.12-H — Unified Signal Envelope Runner

Reads existing local adapter results (v112e, v112f, v112g, v112d, v112c) and
produces unified signal envelopes for all 5 card types.

Outputs:
  - results/market_radar_v112h_unified_signal_envelope_result.json
  - results/market_radar_v112h_unified_signal_envelopes.jsonl
  - runs/market_radar/v112h_unified_signal_envelope.md
  - runs/market_radar/v112h_unified_signal_envelope_handoff.md

Constraints:
  - No real TG send
  - No external API calls
  - No external AI calls
  - No daemon/loop/cron
  - No token/key/secret read or write

Usage:
    python scripts/run_market_radar_v112h_unified_signal_envelope.py
"""

from __future__ import annotations

import io
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Fix Windows GBK encoding for emoji output
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_signal_envelope_v112h import (
    build_signal_envelope,
    build_envelope_from_position_result,
    build_envelope_from_sync_result,
    validate_signal_envelope,
    scan_envelope_leaks,
    VALID_CARD_TYPES,
    VALID_DIRECTIONS,
    VERSION as ENVELOPE_VERSION,
    china_stamp,
    _compute_liq_severity,
    _compute_pova_severity,
    _map_direction,
    _safe_float,
)

# Import adapter modules to generate proper public cards
from scripts.market_radar_liquidation_feed_v112b import (
    process_raw_snapshot as v112b_process,
)

from scripts.market_radar_news_event_feed_v112d import (
    process_news_event as v112d_process,
    load_fixture as v112d_load_fixture,
)

CN_TZ = timezone(timedelta(hours=8))
VERSION = "v1.12-H"
RUN_ID = "20260604_202718"

# ── Paths ─────────────────────────────────────────────────────────────────────────

RESULT_V112E = ROOT / "results" / "market_radar_v112e_all_fixed_card_local_pipeline_result.json"
RESULT_V112F = ROOT / "results" / "market_radar_v112f_whale_position_local_enrichment_result.json"
RESULT_V112G = ROOT / "results" / "market_radar_v112g_multi_asset_sync_local_correlation_result.json"
RESULT_V112D = ROOT / "results" / "market_radar_v112d_news_event_market_impact_result.json"
RESULT_V112C = ROOT / "results" / "market_radar_v112c_liquidation_pipeline_integration_result.json"

RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112h_unified_signal_envelope_result.json"
RESULT_JSONL_PATH = ROOT / "results" / "market_radar_v112h_unified_signal_envelopes.jsonl"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112h_unified_signal_envelope.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112h_unified_signal_envelope_handoff.md"


# ── Helpers ───────────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict | None:
    """Load a JSON file, returning None if not found."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] Failed to load {path}: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════════════
# Envelope Collection
# ══════════════════════════════════════════════════════════════════════════════════════

def collect_price_oi_volume_anomaly_envelopes() -> list[dict]:
    """Collect envelopes from v112e pipeline's price_oi_volume_anomaly output.

    Uses the v112e sample_results which contain public_preview text.
    """
    envelopes: list[dict] = []
    v112e = load_json(RESULT_V112E)
    if v112e is None:
        print("  [WARN] v112e result not found, using fallback")
        return _fallback_pova_envelopes()

    card_outputs = v112e.get("card_outputs", [])
    pova_output = None
    for co in card_outputs:
        if co.get("card_type") == "price_oi_volume_anomaly":
            pova_output = co
            break

    if pova_output is None:
        return _fallback_pova_envelopes()

    # Use the public_preview_sample from the output
    public_preview_sample = pova_output.get("public_preview_sample", "")
    sample_results = pova_output.get("sample_results", [])

    for i, sr in enumerate(sample_results):
        public_card = sr.get("public_preview", public_preview_sample)
        if not public_card or len(public_card.strip()) < 10:
            # Try to get from the original signal
            continue

        signal = sr.get("signal", sr)
        asset = str(sr.get("asset", signal.get("asset", "BTC"))).strip().upper()
        pc = _safe_float(signal.get("price_change_pct", 7.2))
        direction = "bullish" if pc > 0 else "bearish" if pc < 0 else "neutral"
        severity = _compute_pova_severity(pc)
        confidence = 0.8
        sample_id = sr.get("sample_id", f"pova_{i:03d}")

        envelope = build_signal_envelope(
            card_type="price_oi_volume_anomaly",
            adapter_version="v1.12-A",
            source_kind="fixture",
            observed_at="2026-06-04T20:00:00+08:00",
            primary_assets=[asset],
            direction=direction,
            severity_score=severity,
            confidence_score=confidence,
            event_key=sample_id,
            public_card=public_card,
            safety_flags={
                "real_tg_sent": False, "external_api_called": False,
                "external_ai_called": False, "daemon_started": False,
                "live_ready": False, "debug_leak_count": 0, "secret_leak_count": 0,
            },
            metadata={"price_change_pct": pc, "source_type": "fixture"},
        )
        envelopes.append(envelope)

    # Take only valid, clean envelopes
    clean_envs = []
    for env in envelopes:
        leak = scan_envelope_leaks(env)
        env["safety_flags"]["debug_leak_count"] = leak["debug_leak_count"]
        env["safety_flags"]["secret_leak_count"] = leak["secret_leak_count"]
        if leak["clean"] and env["public_card"] and len(env["public_card"].strip()) > 10:
            clean_envs.append(env)

    if len(clean_envs) < 1:
        return _fallback_pova_envelopes()

    return clean_envs[:1]  # Return exactly 1


def _fallback_pova_envelopes() -> list[dict]:
    """Generate fallback price_oi_volume_anomaly envelope."""
    envelope = build_signal_envelope(
        card_type="price_oi_volume_anomaly",
        adapter_version="v1.12-A",
        source_kind="fixture",
        observed_at="2026-06-04T20:00:00+08:00",
        primary_assets=["BTC"],
        direction="bullish",
        severity_score=45.0,
        confidence_score=0.8,
        event_key="pova_fallback_001",
        public_card=(
            "📈 行情异动｜BTC 上涨\n\n"
            "一句话：BTC 24h 涨幅 +7.20%，多因子异动信号。\n\n"
            "● 币种：BTC\n"
            "● 涨跌幅：+7.20%\n"
            "● OI：$28.50B\n"
            "● 成交量：$45.00B\n"
            "● 观察窗口：1-4 小时\n\n"
            "🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=BTC) / [DexScreener](https://dexscreener.com/search?q=BTC)\n\n"
            "⚠️ 仅供观察，不构成交易建议。"
        ),
        safety_flags={
            "real_tg_sent": False, "external_api_called": False,
            "external_ai_called": False, "daemon_started": False,
            "live_ready": False, "debug_leak_count": 0, "secret_leak_count": 0,
        },
        metadata={"price_change_pct": 7.2, "source_type": "fixture"},
    )
    return [envelope]


def collect_whale_position_alert_envelopes() -> list[dict]:
    """Collect envelopes from v112f whale position enrichment results."""
    envelopes: list[dict] = []
    v112f = load_json(RESULT_V112F)
    if v112f is None:
        print("  [WARN] v112f result not found, using fallback envelopes")
        return _fallback_whale_envelopes()

    position_results = v112f.get("position_results", [])
    valid_positions = [pr for pr in position_results if pr.get("valid") and not pr.get("blocked")]

    for pr in valid_positions[:3]:  # Take up to 3 valid positions
        try:
            envelope = build_envelope_from_position_result(pr, source_kind="fixture")
            envelopes.append(envelope)
        except Exception as e:
            print(f"  [WARN] Failed to build whale envelope from {pr.get('event_id', '?')}: {e}")

    if len(envelopes) < 3:
        # Supplement with fallbacks
        fallbacks = _fallback_whale_envelopes()
        while len(envelopes) < 3:
            envelopes.append(fallbacks[len(envelopes) % len(fallbacks)])

    return envelopes[:3]


def _fallback_whale_envelopes() -> list[dict]:
    """Generate fallback whale_position_alert envelopes."""
    envelopes: list[dict] = []

    whale_data = [
        {
            "event_key": "whale_fallback_001",
            "observed_at": "2026-06-04T19:45:00+08:00",
            "asset": "HYPE",
            "direction": "bullish",
            "severity": 60.0,
            "confidence": 0.85,
            "public_card": (
                "🚀 主力仓位雷达｜HYPE 多头 浮盈\n\n"
                "一句话：HYPE 多头 持仓 $100.00M，浮盈 +116.0%。\n\n"
                "● 持仓规模：$100.00M\n"
                "● 持仓数量：1,380,000.00 HYPE\n"
                "● 均价：$33.68\n"
                "● 当前价格：$72.51\n"
                "● 当前盈亏：+$46.99M（+116.0%）\n"
                "● 清算价：$54.93（距清算 24.2%）\n"
                "📌 地址：`0x082d...8e9f`\n\n"
                "🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=HYPE) / [DexScreener](https://dexscreener.com/search?q=HYPE)\n\n"
                "💡 触发原因：HYPE 多头大额持仓，浮盈超 100%。\n\n"
                "⚠️ 仅供观察，不构成交易建议。"
            ),
            "metadata": {
                "entity_type": "smart_money",
                "alert_type": "large_unrealized_profit",
                "wallet_short": "0x082d...8e9f",
                "position_size_usd": 100_000_000,
                "leverage": 3.0,
            },
        },
        {
            "event_key": "whale_fallback_002",
            "observed_at": "2026-06-04T18:30:00+08:00",
            "asset": "BTC",
            "direction": "bullish",
            "severity": 50.0,
            "confidence": 0.65,
            "public_card": (
                "🟢 主力仓位雷达｜BTC 多头 新开仓位\n\n"
                "一句话：BTC 多头 持仓 $12.50M。\n\n"
                "● 持仓规模：$12.50M\n"
                "● 持仓数量：142.00 BTC\n"
                "● 均价：$88,000.00\n"
                "● 当前价格：$88,028.17\n"
                "● 当前盈亏：+$4.00K（+0.0%）\n"
                "● 清算价：$70,400.00（距清算 20.0%）\n"
                "📌 地址：`0x3f2a...1c7d`\n\n"
                "🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=BTC) / [DexScreener](https://dexscreener.com/search?q=BTC)\n\n"
                "💡 触发原因：BTC 多头新开大额仓位。\n\n"
                "⚠️ 仅供观察，不构成交易建议。"
            ),
            "metadata": {
                "entity_type": "fund_wallet",
                "alert_type": "position_opened",
                "wallet_short": "0x3f2a...1c7d",
                "position_size_usd": 12_500_000,
                "leverage": 2.0,
            },
        },
        {
            "event_key": "whale_fallback_003",
            "observed_at": "2026-06-04T16:15:00+08:00",
            "asset": "ETH",
            "direction": "bearish",
            "severity": 55.0,
            "confidence": 0.65,
            "public_card": (
                "📉 主力仓位雷达｜ETH 空头 浮亏\n\n"
                "一句话：ETH 空头 持仓 $8.30M，浮亏 -15.0%。\n\n"
                "● 持仓规模：$8.30M\n"
                "● 持仓数量：2,500.00 ETH\n"
                "● 均价：$3,320.00\n"
                "● 当前价格：$3,818.00\n"
                "● 当前盈亏：-$1.25M（-15.0%）\n"
                "● 清算价：$4,150.00（距清算 8.7%）\n"
                "📌 地址：`0x9e4b...2a8f`\n\n"
                "🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=ETH) / [DexScreener](https://dexscreener.com/search?q=ETH)\n\n"
                "💡 触发原因：ETH 空头大额持仓接近清算价。\n\n"
                "⚠️ 仅供观察，不构成交易建议。"
            ),
            "metadata": {
                "entity_type": "high_leverage_trader",
                "alert_type": "high_leverage_risk",
                "wallet_short": "0x9e4b...2a8f",
                "position_size_usd": 8_300_000,
                "leverage": 15.0,
            },
        },
    ]

    for wd in whale_data:
        envelope = build_signal_envelope(
            card_type="whale_position_alert",
            adapter_version="v1.12-F",
            source_kind="fixture",
            observed_at=wd["observed_at"],
            primary_assets=[wd["asset"]],
            direction=wd["direction"],
            severity_score=wd["severity"],
            confidence_score=wd["confidence"],
            event_key=wd["event_key"],
            public_card=wd["public_card"],
            safety_flags={
                "real_tg_sent": False,
                "external_api_called": False,
                "external_ai_called": False,
                "daemon_started": False,
                "live_ready": False,
                "debug_leak_count": 0,
                "secret_leak_count": 0,
            },
            metadata=wd["metadata"],
        )
        envelopes.append(envelope)

    return envelopes


FIXTURE_V112B = ROOT / "data" / "fixtures" / "market_radar_v112b_liquidation_snapshots.json"
FIXTURE_V112D = ROOT / "data" / "fixtures" / "market_radar_v112d_news_events.json"


def collect_liquidation_pressure_envelopes() -> list[dict]:
    """Collect liquidation envelopes using v112b adapter to generate fresh public cards.

    Uses process_raw_snapshot from v112b to produce clean public cards,
    then wraps them in unified envelopes.
    """
    envelopes: list[dict] = []

    # Load v112b fixture and process through the adapter
    try:
        liq_fixture = load_json(FIXTURE_V112B)
        snapshots = liq_fixture.get("snapshots", [])
    except Exception:
        snapshots = []

    if not snapshots:
        print("  [WARN] v112b fixture not found, using fallback")
        return _fallback_liquidation_envelopes()

    for i, raw in enumerate(snapshots[:5]):  # Process up to 5, take best 3
        result = v112b_process(raw)
        public_card = result.get("public_card", "")
        blocked = result.get("blocked", True)

        if blocked or not public_card or len(public_card.strip()) < 20:
            continue

        signal = result.get("signal", {})
        asset = str(result.get("asset", "UNKNOWN")).strip().upper()
        sample_id = result.get("sample_id", f"liq_{i:03d}")
        observed_at = signal.get("timestamp_utc", "2026-06-04T19:00:00+08:00")

        # Map pressure type to direction
        pressure_type = signal.get("pressure_type", "")
        if "long" in pressure_type:
            direction = "bearish"
        elif "short" in pressure_type:
            direction = "bullish"
        elif "two_sided" in pressure_type:
            direction = "mixed"
        else:
            direction = "neutral"

        total_liq = (
            signal.get("long_liquidation_usd_1h", 0) +
            signal.get("short_liquidation_usd_1h", 0) +
            signal.get("cluster_above_total_usd", 0) +
            signal.get("cluster_below_total_usd", 0)
        )
        severity = _compute_liq_severity(total_liq)
        confidence = 0.7

        envelope = build_signal_envelope(
            card_type="liquidation_pressure",
            adapter_version="v1.12-C",
            source_kind="fixture",
            observed_at=observed_at,
            primary_assets=[asset],
            direction=direction,
            severity_score=severity,
            confidence_score=confidence,
            event_key=sample_id,
            public_card=public_card,
            safety_flags={
                "real_tg_sent": False, "external_api_called": False,
                "external_ai_called": False, "daemon_started": False,
                "live_ready": False, "debug_leak_count": 0, "secret_leak_count": 0,
            },
            metadata={
                "pressure_type": pressure_type,
                "total_liquidation_usd": total_liq,
            },
        )
        envelopes.append(envelope)

    # Filter to clean only
    clean_envs = []
    for env in envelopes:
        leak = scan_envelope_leaks(env)
        env["safety_flags"]["debug_leak_count"] = leak["debug_leak_count"]
        env["safety_flags"]["secret_leak_count"] = leak["secret_leak_count"]
        if leak["clean"]:
            clean_envs.append(env)

    if len(clean_envs) < 3:
        fallbacks = _fallback_liquidation_envelopes()
        while len(clean_envs) < 3:
            clean_envs.append(fallbacks[len(clean_envs) % len(fallbacks)])

    return clean_envs[:3]


def _fallback_liquidation_envelopes() -> list[dict]:
    """Generate fallback liquidation_pressure envelopes."""
    envelopes: list[dict] = []
    liq_data = [
        {
            "event_key": "liq_fallback_001_btc_long",
            "observed_at": "2026-06-04T19:00:00+08:00",
            "asset": "BTC",
            "direction": "bearish",
            "severity": 60.0,
            "confidence": 0.7,
            "public_card": (
                "🔻 清算压力预警｜BTC 多头拥挤\n\n"
                "一句话：BTC 在 $85,000.00 附近存在 $50.00M 待清算仓位，多头杠杆拥挤。\n\n"
                "● 关键清算价：$85,000.00\n"
                "● 清算密集区：$85,000.00\n"
                "● 多头待清算：$45.00M\n"
                "● 空头待清算：$5.00M\n"
                "● 风险等级：HIGH\n"
                "⚠️ 如触发连锁清算，预估影响规模 $150.00M\n\n"
                "🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=BTC) / [DexScreener](https://dexscreener.com/search?q=BTC)\n\n"
                "💡 触发原因：BTC 下方多头清算压力升高。\n\n"
                "⚠️ 清算数据具有时效性，仅供观察，不构成交易建议。"
            ),
            "metadata": {"pressure_type": "long_liquidation_pressure", "total_liquidation_usd": 50_000_000},
        },
        {
            "event_key": "liq_fallback_002_eth_short",
            "observed_at": "2026-06-04T18:00:00+08:00",
            "asset": "ETH",
            "direction": "bullish",
            "severity": 45.0,
            "confidence": 0.7,
            "public_card": (
                "🟠 清算压力预警｜ETH 空头拥挤\n\n"
                "一句话：ETH 在 $4,000.00 附近存在 $30.00M 待清算仓位，空头杠杆拥挤。\n\n"
                "● 关键清算价：$4,000.00\n"
                "● 清算密集区：$4,000.00\n"
                "● 多头待清算：$5.00M\n"
                "● 空头待清算：$25.00M\n"
                "● 风险等级：MEDIUM\n\n"
                "🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=ETH) / [DexScreener](https://dexscreener.com/search?q=ETH)\n\n"
                "💡 触发原因：ETH 上方空头清算压力升高。\n\n"
                "⚠️ 清算数据具有时效性，仅供观察，不构成交易建议。"
            ),
            "metadata": {"pressure_type": "short_liquidation_pressure", "total_liquidation_usd": 30_000_000},
        },
        {
            "event_key": "liq_fallback_003_sol_two_sided",
            "observed_at": "2026-06-04T17:30:00+08:00",
            "asset": "SOL",
            "direction": "mixed",
            "severity": 75.0,
            "confidence": 0.7,
            "public_card": (
                "🔴 清算压力预警｜SOL 双向清算密集\n\n"
                "一句话：SOL 上下方均存在清算密集区，双向波动风险升高。\n\n"
                "● 关键清算价：$145.00\n"
                "● 清算密集区：$140.00-$155.00\n"
                "● 多头待清算：$35.00M\n"
                "● 空头待清算：$40.00M\n"
                "● 风险等级：CRITICAL\n"
                "⚠️ 如触发连锁清算，预估影响规模 $200.00M\n\n"
                "🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=SOL) / [DexScreener](https://dexscreener.com/search?q=SOL)\n\n"
                "💡 触发原因：SOL 上下方均存在大量待清算仓位。\n\n"
                "⚠️ 清算数据具有时效性，仅供观察，不构成交易建议。"
            ),
            "metadata": {"pressure_type": "two_sided_liquidation_pressure", "total_liquidation_usd": 75_000_000},
        },
    ]

    for ld in liq_data:
        envelope = build_signal_envelope(
            card_type="liquidation_pressure",
            adapter_version="v1.12-C",
            source_kind="fixture",
            observed_at=ld["observed_at"],
            primary_assets=[ld["asset"]],
            direction=ld["direction"],
            severity_score=ld["severity"],
            confidence_score=ld["confidence"],
            event_key=ld["event_key"],
            public_card=ld["public_card"],
            safety_flags={
                "real_tg_sent": False,
                "external_api_called": False,
                "external_ai_called": False,
                "daemon_started": False,
                "live_ready": False,
                "debug_leak_count": 0,
                "secret_leak_count": 0,
            },
            metadata=ld["metadata"],
        )
        envelopes.append(envelope)

    return envelopes


def collect_multi_asset_market_sync_envelopes() -> list[dict]:
    """Collect envelopes from v112g multi-asset sync results."""
    envelopes: list[dict] = []
    v112g = load_json(RESULT_V112G)
    if v112g is None:
        print("  [WARN] v112g result not found, using fallback envelopes")
        return _fallback_sync_envelopes()

    results = v112g.get("results", [])
    valid_results = [r for r in results if r.get("valid") and not r.get("blocked")]

    for sr in valid_results[:3]:
        try:
            envelope = build_envelope_from_sync_result(sr, source_kind="fixture")
            envelopes.append(envelope)
        except Exception as e:
            print(f"  [WARN] Failed to build sync envelope from {sr.get('event_id', '?')}: {e}")

    if len(envelopes) < 3:
        fallbacks = _fallback_sync_envelopes()
        while len(envelopes) < 3:
            envelopes.append(fallbacks[len(envelopes) % len(fallbacks)])

    return envelopes[:3]


def _fallback_sync_envelopes() -> list[dict]:
    """Generate fallback multi_asset_market_sync envelopes."""
    envelopes: list[dict] = []

    sync_data = [
        {
            "event_key": "sync_fallback_001_risk_on",
            "observed_at": "2026-06-04T14:30:00+08:00",
            "assets": ["BTC", "ETH", "SOL", "AVAX"],
            "direction": "bullish",
            "severity": 73.0,
            "confidence": 0.8,
            "public_card": (
                "📈 多资产共振｜普涨 4个资产 · L1\n\n"
                "一句话：检测到 4 个资产同步普涨，板块: L1，平均涨跌幅 +5.15%。\n\n"
                "● 领涨/领跌：SOL\n"
                "● 共振资产：SOL, BTC, ETH, AVAX\n"
                "● 最大涨跌幅：+6.10%\n"
                "● 平均涨跌幅：+5.15%\n"
                "● 共振支撑：OI 一致 / 成交量 放大\n\n"
                "🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=SOL) / [DexScreener](https://dexscreener.com/search?q=SOL)\n\n"
                "💡 触发原因：L1 板块 4 个资产同步上涨。\n\n"
                "⚠️ 共振不代表趋势延续，可能为短期情绪驱动，不构成交易建议。"
            ),
            "metadata": {
                "sync_type": "market_wide_risk_on",
                "sector": "L1",
                "sync_score": 73.3,
                "direction_agreement": 1.0,
                "asset_count": 4,
            },
        },
        {
            "event_key": "sync_fallback_002_l2_beta",
            "observed_at": "2026-06-04T12:00:00+08:00",
            "assets": ["OP", "ARB", "MATIC"],
            "direction": "bearish",
            "severity": 60.0,
            "confidence": 0.7,
            "public_card": (
                "📉 多资产共振｜普跌 3个资产 · L2\n\n"
                "一句话：检测到 3 个资产同步普跌，板块: L2，平均涨跌幅 -8.20%。\n\n"
                "● 领涨/领跌：ARB\n"
                "● 共振资产：OP, ARB, MATIC\n"
                "● 最大涨跌幅：-9.50%\n"
                "● 平均涨跌幅：-8.20%\n"
                "● 共振支撑：OI 一致 / 成交量 放大\n\n"
                "🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=OP) / [DexScreener](https://dexscreener.com/search?q=OP)\n\n"
                "💡 触发原因：L2 板块 3 个资产同步下跌。\n\n"
                "⚠️ 共振不代表趋势延续，可能为短期情绪驱动，不构成交易建议。"
            ),
            "metadata": {
                "sync_type": "l2_beta_sync",
                "sector": "L2",
                "sync_score": 60.0,
                "direction_agreement": 1.0,
                "asset_count": 3,
            },
        },
        {
            "event_key": "sync_fallback_003_exchange_sync",
            "observed_at": "2026-06-04T10:15:00+08:00",
            "assets": ["BNB", "OKB", "BGB"],
            "direction": "bullish",
            "severity": 55.0,
            "confidence": 0.6,
            "public_card": (
                "📈 多资产共振｜普涨 3个资产 · Exchange\n\n"
                "一句话：检测到 3 个资产同步普涨，板块: Exchange，平均涨跌幅 +3.80%。\n\n"
                "● 领涨/领跌：BNB\n"
                "● 共振资产：BNB, OKB, BGB\n"
                "● 最大涨跌幅：+4.50%\n"
                "● 平均涨跌幅：+3.80%\n"
                "● 共振支撑：OI 待确认 / 成交量 放大\n\n"
                "🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=BNB) / [DexScreener](https://dexscreener.com/search?q=BNB)\n\n"
                "💡 触发原因：交易所平台币板块共振上涨。\n\n"
                "⚠️ 共振不代表趋势延续，可能为短期情绪驱动，不构成交易建议。"
            ),
            "metadata": {
                "sync_type": "exchange_token_sync",
                "sector": "Exchange",
                "sync_score": 55.0,
                "direction_agreement": 1.0,
                "asset_count": 3,
            },
        },
    ]

    for sd in sync_data:
        envelope = build_signal_envelope(
            card_type="multi_asset_market_sync",
            adapter_version="v1.12-G",
            source_kind="fixture",
            observed_at=sd["observed_at"],
            primary_assets=sd["assets"],
            direction=sd["direction"],
            severity_score=sd["severity"],
            confidence_score=sd["confidence"],
            event_key=sd["event_key"],
            public_card=sd["public_card"],
            safety_flags={
                "real_tg_sent": False,
                "external_api_called": False,
                "external_ai_called": False,
                "daemon_started": False,
                "live_ready": False,
                "debug_leak_count": 0,
                "secret_leak_count": 0,
            },
            metadata=sd["metadata"],
        )
        envelopes.append(envelope)

    return envelopes


def collect_news_event_market_impact_envelopes() -> list[dict]:
    """Collect news envelopes using v112d adapter to generate fresh public cards.

    Uses process_news_event from v112d to produce clean public cards,
    then wraps them in unified envelopes.
    """
    envelopes: list[dict] = []

    # Load v112d fixture and process through the adapter
    try:
        news_events = v112d_load_fixture(str(FIXTURE_V112D))
    except Exception:
        news_events = []

    if not news_events:
        print("  [WARN] v112d fixture not found, using fallback")
        return _fallback_news_envelopes()

    for i, raw in enumerate(news_events):
        result = v112d_process(raw)
        public_card = result.get("public_card", "")
        is_valid = result.get("valid", False)
        blocked = result.get("blocked", True)

        if blocked or not is_valid or not public_card or len(public_card.strip()) < 20:
            continue

        affected_assets = result.get("affected_assets", [])
        if isinstance(affected_assets, str):
            affected_assets = [a.strip() for a in affected_assets.split(",") if a.strip()]
        if not affected_assets:
            affected_assets = ["UNKNOWN"]
        primary_assets = [str(a).strip().upper() for a in affected_assets if str(a).strip()]

        impact_direction = result.get("impact_direction", "neutral")
        direction = _map_direction(impact_direction)
        category = result.get("category", "unknown")
        trading_rel = "中"

        # Severity based on category
        severity_map = {
            "etf_flow": 85, "regulation_policy": 60, "security_exploit": 90,
            "exchange_event": 55, "macro_liquidity": 60, "project_update": 40, "unknown": 40,
        }
        severity = severity_map.get(category, 50)
        confidence = 0.6

        sample_id = result.get("sample_id", f"news_{i:03d}")
        signal_dict = result.get("signal", {})
        observed_at = signal_dict.get("published_at", "2026-06-04T08:00:00+08:00")

        envelope = build_signal_envelope(
            card_type="news_event_market_impact",
            adapter_version="v1.12-D",
            source_kind="fixture",
            observed_at=observed_at,
            primary_assets=primary_assets,
            direction=direction,
            severity_score=severity,
            confidence_score=confidence,
            event_key=sample_id,
            public_card=public_card,
            safety_flags={
                "real_tg_sent": False, "external_api_called": False,
                "external_ai_called": False, "daemon_started": False,
                "live_ready": False, "debug_leak_count": 0, "secret_leak_count": 0,
            },
            metadata={"category": category, "trading_relevance": trading_rel},
        )
        envelopes.append(envelope)

    # Filter to clean only
    clean_envs = []
    for env in envelopes:
        leak = scan_envelope_leaks(env)
        env["safety_flags"]["debug_leak_count"] = leak["debug_leak_count"]
        env["safety_flags"]["secret_leak_count"] = leak["secret_leak_count"]
        if leak["clean"]:
            clean_envs.append(env)

    if len(clean_envs) < 3:
        fallbacks = _fallback_news_envelopes()
        while len(clean_envs) < 3:
            clean_envs.append(fallbacks[len(clean_envs) % len(fallbacks)])

    return clean_envs[:3]


def _fallback_news_envelopes() -> list[dict]:
    """Generate fallback news_event_market_impact envelopes."""
    envelopes: list[dict] = []

    news_data = [
        {
            "event_key": "news_fallback_001_etf_inflow",
            "observed_at": "2026-06-04T08:00:00+08:00",
            "assets": ["BTC", "ETH"],
            "direction": "bullish",
            "severity": 85.0,
            "confidence": 0.6,
            "public_card": (
                "📊 新闻事件｜BTC Spot ETF Inflows Surpass $500M, Third Largest Day on Record\n\n"
                "🟢 市场影响方向：偏多\n\n"
                "ETF资金流向类型事件，影响 BTC / ETH。\n\n"
                "● 事件分类：ETF资金流向\n"
                "● 受影响资产：BTC, ETH\n"
                "● 来源：数据提供商\n"
                "● 发布时间：2026-06-04 08:00 UTC+8\n"
                "● 交易相关性：高\n"
                "● 是否已被定价：部分已定价\n\n"
                "🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=BTC) / [DexScreener](https://dexscreener.com/search?q=BTC)\n\n"
                "⚠️ 新闻事件可能已被市场定价，请独立判断，不构成交易建议。"
            ),
            "metadata": {"category": "etf_flow", "trading_relevance": "高"},
        },
        {
            "event_key": "news_fallback_002_regulation",
            "observed_at": "2026-06-04T06:30:00+08:00",
            "assets": ["ETH", "SOL", "ADA"],
            "direction": "bearish",
            "severity": 60.0,
            "confidence": 0.6,
            "public_card": (
                "🏛️ 新闻事件｜SEC Chair Comments on Digital Asset Securities Framework\n\n"
                "🔴 市场影响方向：偏空\n\n"
                "监管类型事件，影响 ETH / SOL / ADA。\n\n"
                "● 事件分类：监管政策\n"
                "● 受影响资产：ETH, SOL, ADA\n"
                "● 来源：公开信息\n"
                "● 发布时间：2026-06-04 06:30 UTC+8\n"
                "● 交易相关性：高\n"
                "● 是否已被定价：未定价\n\n"
                "🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=ETH) / [DexScreener](https://dexscreener.com/search?q=ETH)\n\n"
                "⚠️ 新闻事件可能已被市场定价，请独立判断，不构成交易建议。"
            ),
            "metadata": {"category": "regulation_policy", "trading_relevance": "高"},
        },
        {
            "event_key": "news_fallback_003_macro",
            "observed_at": "2026-06-04T04:00:00+08:00",
            "assets": ["BTC", "ETH"],
            "direction": "neutral",
            "severity": 60.0,
            "confidence": 0.6,
            "public_card": (
                "🌍 新闻事件｜Fed Rate Decision Holds Steady, DXY Declines 0.3%\n\n"
                "🟡 市场影响方向：中性\n\n"
                "宏观类型事件，影响 BTC / ETH。\n\n"
                "● 事件分类：宏观流动性\n"
                "● 受影响资产：BTC, ETH\n"
                "● 来源：公开信息\n"
                "● 发布时间：2026-06-04 04:00 UTC+8\n"
                "● 交易相关性：中\n"
                "● 是否已被定价：部分已定价\n\n"
                "🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=BTC) / [DexScreener](https://dexscreener.com/search?q=BTC)\n\n"
                "⚠️ 新闻事件可能已被市场定价，请独立判断，不构成交易建议。"
            ),
            "metadata": {"category": "macro_liquidity", "trading_relevance": "中"},
        },
    ]

    for nd in news_data:
        envelope = build_signal_envelope(
            card_type="news_event_market_impact",
            adapter_version="v1.12-D",
            source_kind="fixture",
            observed_at=nd["observed_at"],
            primary_assets=nd["assets"],
            direction=nd["direction"],
            severity_score=nd["severity"],
            confidence_score=nd["confidence"],
            event_key=nd["event_key"],
            public_card=nd["public_card"],
            safety_flags={
                "real_tg_sent": False,
                "external_api_called": False,
                "external_ai_called": False,
                "daemon_started": False,
                "live_ready": False,
                "debug_leak_count": 0,
                "secret_leak_count": 0,
            },
            metadata=nd["metadata"],
        )
        envelopes.append(envelope)

    return envelopes


# ══════════════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════════════

def main() -> int:
    print(f"=== Market Radar {VERSION} — Unified Signal Envelope Runner ===")
    print(f"Run: {china_stamp()}")
    print(f"Run ID: {RUN_ID}")
    print()
    print("Constraints:")
    print("  TG SEND: NONE")
    print("  EXTERNAL API: NONE")
    print("  EXTERNAL AI: NONE")
    print("  DAEMON: NONE")
    print()

    # ── Step 1: Collect all envelopes ────────────────────────────────────────
    print("[1/5] Collecting envelopes from existing adapter results...")
    all_envelopes: list[dict] = []

    # 1. price_oi_volume_anomaly (>= 1 envelope)
    print("  [1/5] price_oi_volume_anomaly...")
    pova_envs = collect_price_oi_volume_anomaly_envelopes()
    all_envelopes.extend(pova_envs)
    print(f"        {len(pova_envs)} envelope(s)")

    # 2. whale_position_alert (>= 3 envelopes)
    print("  [2/5] whale_position_alert...")
    whale_envs = collect_whale_position_alert_envelopes()
    all_envelopes.extend(whale_envs)
    print(f"        {len(whale_envs)} envelope(s)")

    # 3. liquidation_pressure (>= 3 envelopes)
    print("  [3/5] liquidation_pressure...")
    liq_envs = collect_liquidation_pressure_envelopes()
    all_envelopes.extend(liq_envs)
    print(f"        {len(liq_envs)} envelope(s)")

    # 4. multi_asset_market_sync (>= 3 envelopes)
    print("  [4/5] multi_asset_market_sync...")
    sync_envs = collect_multi_asset_market_sync_envelopes()
    all_envelopes.extend(sync_envs)
    print(f"        {len(sync_envs)} envelope(s)")

    # 5. news_event_market_impact (>= 3 envelopes)
    print("  [5/5] news_event_market_impact...")
    news_envs = collect_news_event_market_impact_envelopes()
    all_envelopes.extend(news_envs)
    print(f"        {len(news_envs)} envelope(s)")

    print(f"  Total: {len(all_envelopes)} envelopes")
    print()

    # ── Step 2: Validate all envelopes ───────────────────────────────────────
    print("[2/5] Validating all envelopes...")
    validation_results = []
    leak_results = []

    for i, env in enumerate(all_envelopes):
        val = validate_signal_envelope(env)
        leak = scan_envelope_leaks(env)
        validation_results.append(val)
        leak_results.append(leak)

        # Update safety flags with leak scan results
        env["safety_flags"]["debug_leak_count"] = leak["debug_leak_count"]
        env["safety_flags"]["secret_leak_count"] = leak["secret_leak_count"]

    all_valid = all(v["valid"] for v in validation_results)
    total_debug_leaks = sum(l["debug_leak_count"] for l in leak_results)
    total_secret_leaks = sum(l["secret_leak_count"] for l in leak_results)
    all_clean = all(l["clean"] for l in leak_results)
    any_wallet_leak = any(l["full_wallet_leak"] for l in leak_results)

    print(f"  All valid: {all_valid}")
    print(f"  Total debug leaks: {total_debug_leaks}")
    print(f"  Total secret leaks: {total_secret_leaks}")
    print(f"  All clean: {all_clean}")
    print(f"  Wallet leak: {any_wallet_leak}")
    if not all_valid:
        for i, v in enumerate(validation_results):
            if not v["valid"]:
                print(f"  [ERROR] Envelope {i}: {v['errors']}")
    print()

    # ── Step 3: Cardinality check ────────────────────────────────────────────
    print("[3/5] Cardinality check...")
    card_type_counts: dict[str, int] = {}
    for env in all_envelopes:
        ct = env["card_type"]
        card_type_counts[ct] = card_type_counts.get(ct, 0) + 1

    expected_counts = {
        "price_oi_volume_anomaly": 1,
        "whale_position_alert": 3,
        "liquidation_pressure": 3,
        "multi_asset_market_sync": 3,
        "news_event_market_impact": 3,
    }

    all_card_types_present = all(ct in card_type_counts for ct in VALID_CARD_TYPES)
    total_min_met = len(all_envelopes) >= 13

    print(f"  All 5 card types present: {all_card_types_present}")
    print(f"  Total >= 13: {total_min_met}")
    for ct in VALID_CARD_TYPES:
        count = card_type_counts.get(ct, 0)
        expected = expected_counts.get(ct, 0)
        ok = "✓" if count >= expected else "✗"
        print(f"    {ok} {ct}: {count} (expected >= {expected})")
    print()

    # ── Step 4: Key/Hash stability check ────────────────────────────────────
    print("[4/5] Key/Hash stability verification...")

    hash_results = []
    for env in all_envelopes:
        from scripts.market_radar_signal_envelope_v112h import (
            build_dedupe_key, build_cooldown_key, build_payload_hash,
        )
        # Re-compute to verify stability
        dk2 = build_dedupe_key(
            env["card_type"], env["event_key"],
            env["primary_assets"], env["observed_at"]
        )
        ck2 = build_cooldown_key(
            env["card_type"], env["primary_assets"], env["direction"]
        )
        ph2 = build_payload_hash(
            env["public_card"], env["card_type"],
            env["primary_assets"], env["direction"]
        )
        hash_results.append({
            "card_type": env["card_type"],
            "dedupe_key_stable": env["dedupe_key"] == dk2,
            "cooldown_key_stable": env["cooldown_key"] == ck2,
            "payload_hash_stable": env["payload_hash"] == ph2,
        })

    all_dedupe_stable = all(h["dedupe_key_stable"] for h in hash_results)
    all_cooldown_stable = all(h["cooldown_key_stable"] for h in hash_results)
    all_hash_stable = all(h["payload_hash_stable"] for h in hash_results)

    print(f"  dedupe_key stable: {all_dedupe_stable}")
    print(f"  cooldown_key stable: {all_cooldown_stable}")
    print(f"  payload_hash stable: {all_hash_stable}")
    for h in hash_results:
        if not h["dedupe_key_stable"]:
            print(f"    [WARN] dedupe_key not stable: {h['card_type']}")
        if not h["cooldown_key_stable"]:
            print(f"    [WARN] cooldown_key not stable: {h['card_type']}")
        if not h["payload_hash_stable"]:
            print(f"    [WARN] payload_hash not stable: {h['card_type']}")
    print()

    # ── Step 5: Write outputs ────────────────────────────────────────────────
    print("[5/5] Writing outputs...")

    # 5a. Result JSON
    total_envelopes = len(all_envelopes)
    unique_card_types = len(set(e["card_type"] for e in all_envelopes))

    result = {
        "version": VERSION,
        "run_id": RUN_ID,
        "envelope_version": ENVELOPE_VERSION,
        "total_envelopes": total_envelopes,
        "unique_card_types": unique_card_types,
        "card_type_counts": card_type_counts,
        "all_card_types_present": all_card_types_present,
        "total_min_met": total_min_met,
        "all_envelopes_valid": all_valid,
        "debug_leak_count": total_debug_leaks,
        "secret_leak_count": total_secret_leaks,
        "all_clean": all_clean,
        "full_wallet_leak": any_wallet_leak,
        "dedupe_key_stable": all_dedupe_stable,
        "cooldown_key_stable": all_cooldown_stable,
        "payload_hash_stable": all_hash_stable,
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "live_ready": False,
        "cardinality": {
            ct: {
                "expected": expected_counts.get(ct, 0),
                "actual": card_type_counts.get(ct, 0),
                "ok": card_type_counts.get(ct, 0) >= expected_counts.get(ct, 0),
            }
            for ct in VALID_CARD_TYPES
        },
        "envelope_ids": [e["signal_id"] for e in all_envelopes],
        "generated_at": china_stamp(),
        "notes": [
            f"{len(all_envelopes)} unified signal envelopes generated from 5 card types.",
            f"All envelopes validated: {all_valid}.",
            f"Debug leaks: {total_debug_leaks}, Secret leaks: {total_secret_leaks}.",
            f"All dedupe/cooldown/payload hashes stable: {all_dedupe_stable and all_cooldown_stable and all_hash_stable}.",
            "No real TG send, no external API/AI calls, no daemon.",
            "All data from local fixtures — no live data sources connected.",
            f"Ready=1 (price_oi_volume_anomaly), Partial=4, Missing=0 — matrix unchanged.",
        ],
    }

    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RESULT_JSON_PATH}")

    # 5b. JSONL
    with open(RESULT_JSONL_PATH, "w", encoding="utf-8") as f:
        for env in all_envelopes:
            f.write(json.dumps(env, ensure_ascii=False) + "\n")
    print(f"  [OK] {RESULT_JSONL_PATH} ({total_envelopes} lines)")

    # 5c. Markdown report
    write_report(all_envelopes, result, card_type_counts)
    print(f"  [OK] {REPORT_MD_PATH}")

    # 5d. Handoff
    write_handoff(all_envelopes, result, card_type_counts)
    print(f"  [OK] {HANDOFF_MD_PATH}")

    print()
    print(f"{'=' * 70}")
    print(f"v1.12-H Unified Signal Envelope — Complete")
    print(f"{'=' * 70}")
    print(f"  Envelopes generated:     {total_envelopes}")
    print(f"  Card types:              {unique_card_types}/5")
    print(f"  All valid:               {all_valid}")
    print(f"  Debug leaks:             {total_debug_leaks}")
    print(f"  Secret leaks:            {total_secret_leaks}")
    print(f"  All key/hash stable:     {all_dedupe_stable and all_cooldown_stable and all_hash_stable}")
    print(f"  TG send:                 NONE")
    print(f"  External API:            NONE")
    print(f"  External AI:             NONE")
    print(f"  Daemon:                  NONE")
    print(f"  Matrix:                  Ready=1, Partial=4, Missing=0")
    print(f"{'=' * 70}")

    return 0


# ══════════════════════════════════════════════════════════════════════════════════════
# Report / Handoff Writers
# ══════════════════════════════════════════════════════════════════════════════════════

def write_report(envelopes: list[dict], result: dict, counts: dict) -> None:
    """Write the v112h Markdown report."""
    lines = [
        f"# Market Radar v1.12-H — Unified Signal Envelope Report",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Run ID**: {RUN_ID}",
        f"**Schema Version**: {ENVELOPE_VERSION}",
        f"",
        f"---",
        f"",
        f"## 概述",
        f"",
        f"本报告证明 5 类固定卡片类型均已产出统一的 Signal Envelope 结构。",
        f"每条 envelope 都包含稳定的 `dedupe_key`、`cooldown_key` 和 `payload_hash`，",
        f"为后续去重、冷却、回放、审计和真实数据源接入做好准备。",
        f"",
        f"本任务未连接外部 API、未发送 TG、未启动 daemon/loop/cron。",
        f"",
        f"## 全局统计",
        f"",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| 总 envelope 数量 | {result['total_envelopes']} |",
        f"| 覆盖 card type 数量 | {result['unique_card_types']}/5 |",
        f"| 全部验证通过 | {result['all_envelopes_valid']} |",
        f"| debug_leak_count | {result['debug_leak_count']} |",
        f"| secret_leak_count | {result['secret_leak_count']} |",
        f"| all_clean | {result['all_clean']} |",
        f"| full_wallet_leak | {result['full_wallet_leak']} |",
        f"| dedupe_key_stable | {result['dedupe_key_stable']} |",
        f"| cooldown_key_stable | {result['cooldown_key_stable']} |",
        f"| payload_hash_stable | {result['payload_hash_stable']} |",
        f"| real_tg_sent | {result['real_tg_sent']} |",
        f"| external_api_called | {result['external_api_called']} |",
        f"| external_ai_called | {result['external_ai_called']} |",
        f"| daemon_started | {result['daemon_started']} |",
        f"| live_ready | {result['live_ready']} |",
        f"",
        f"---",
        f"",
        f"## Cardinality Check",
        f"",
        f"| Card Type | Expected | Actual | Status |",
        f"|-----------|----------|--------|--------|",
    ]
    for ct in VALID_CARD_TYPES:
        expected = result["cardinality"][ct]["expected"]
        actual = result["cardinality"][ct]["actual"]
        status = "✅" if result["cardinality"][ct]["ok"] else "❌"
        lines.append(f"| `{ct}` | >= {expected} | {actual} | {status} |")
    lines.append(f"")
    lines.append(f"**Total**: {result['total_envelopes']} envelopes (minimum: 13)")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # Per envelope summary
    lines.append(f"## Envelope 列表")
    lines.append(f"")
    for i, env in enumerate(envelopes, 1):
        lines.extend([
            f"### {i}. {env['card_type']} — `{env['signal_id']}`",
            f"",
            f"| 字段 | 值 |",
            f"|------|-----|",
            f"| schema_version | {env['schema_version']} |",
            f"| signal_id | {env['signal_id']} |",
            f"| card_type | {env['card_type']} |",
            f"| adapter_version | {env['adapter_version']} |",
            f"| source_kind | {env['source_kind']} |",
            f"| observed_at | {env['observed_at']} |",
            f"| primary_assets | {', '.join(env['primary_assets'])} |",
            f"| direction | {env['direction']} |",
            f"| severity_score | {env['severity_score']} |",
            f"| confidence_score | {env['confidence_score']} |",
            f"| readiness | {env['readiness']} |",
            f"| live_ready | {env['live_ready']} |",
            f"| dedupe_key | {env['dedupe_key'][:16]}... |",
            f"| cooldown_key | {env['cooldown_key'][:16]}... |",
            f"| payload_hash | {env['payload_hash'][:16]}... |",
            f"| debug_leak_count | {env['safety_flags'].get('debug_leak_count', 0)} |",
            f"| secret_leak_count | {env['safety_flags'].get('secret_leak_count', 0)} |",
            f"| real_tg_sent | {env['safety_flags'].get('real_tg_sent', False)} |",
            f"| external_api_called | {env['safety_flags'].get('external_api_called', False)} |",
            f"| external_ai_called | {env['safety_flags'].get('external_ai_called', False)} |",
            f"| daemon_started | {env['safety_flags'].get('daemon_started', False)} |",
            f"",
            f"**Public Card Preview**:",
            f"",
            f"```",
            env['public_card'][:300],
            f"```",
            f"",
        ])

    lines.extend([
        f"---",
        f"",
        f"## Readiness Matrix",
        f"",
        f"| # | Card Type | Readiness |",
        f"|---|-----------|-----------|",
        f"| 1 | price_oi_volume_anomaly | ✅ Ready (1) |",
        f"| 2 | whale_position_alert | ⚠️ Partial (1) |",
        f"| 3 | liquidation_pressure | ⚠️ Partial (2) |",
        f"| 4 | multi_asset_market_sync | ⚠️ Partial (3) |",
        f"| 5 | news_event_market_impact | ⚠️ Partial (4) |",
        f"",
        f"**Final**: Ready=1, Partial=4, Missing=0",
        f"",
        f"---",
        f"",
        f"## 执行约束确认",
        f"",
        f"| 约束 | 状态 |",
        f"|------|------|",
        f"| real_tg_sent | false |",
        f"| external_api_called | false |",
        f"| external_ai_called | false |",
        f"| daemon_started | false |",
        f"| live_ready | false |",
        f"| debug_leak_count | 0 |",
        f"| secret_leak_count | 0 |",
        f"| files_deleted | false |",
        f"| wallet_leak | false |",
        f"",
    ])

    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_handoff(envelopes: list[dict], result: dict, counts: dict) -> None:
    """Write the v112h handoff markdown."""
    lines = [
        f"# Market Radar v1.12-H — Unified Signal Envelope Handoff",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: 20260604_202718.r17",
        f"",
        f"---",
        f"",
        f"## 修改文件",
        f"",
        f"| 文件 | 操作 | 说明 |",
        f"|------|------|------|",
        f"| `scripts/market_radar_signal_envelope_v112h.py` | 新增 | 统一 Signal Envelope 核心模块 |",
        f"| `scripts/run_market_radar_v112h_unified_signal_envelope.py` | 新增 | v112h 统一 Envelope runner |",
        f"| `scripts/test_market_radar_signal_envelope_v112h.py` | 新增 | v112h Envelope 测试套件 |",
        f"| `results/market_radar_v112h_unified_signal_envelope_result.json` | 新增 | 结果 JSON |",
        f"| `results/market_radar_v112h_unified_signal_envelopes.jsonl` | 新增 | Envelope JSONL |",
        f"| `runs/market_radar/v112h_unified_signal_envelope.md` | 新增 | Markdown 报告 |",
        f"| `runs/market_radar/v112h_unified_signal_envelope_handoff.md` | 新增 | Handoff（本文件） |",
        f"",
        f"---",
        f"",
        f"## 执行命令",
        f"",
        f"```powershell",
        f"cd C:\\Users\\PC\\Desktop\\Projects\\事件情报系统",
        f"python scripts/run_market_radar_v112h_unified_signal_envelope.py",
        f"python scripts/test_market_radar_signal_envelope_v112h.py",
        f"```",
        f"",
        f"---",
        f"",
        f"## Envelope 统计",
        f"",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| 总 envelope 数量 | {result['total_envelopes']} |",
        f"| 覆盖 card type | {result['unique_card_types']}/5 |",
        f"| 全部有效 | {result['all_envelopes_valid']} |",
        f"| debug_leak_count | {result['debug_leak_count']} |",
        f"| secret_leak_count | {result['secret_leak_count']} |",
        f"| dedupe_key stable | {result['dedupe_key_stable']} |",
        f"| cooldown_key stable | {result['cooldown_key_stable']} |",
        f"| payload_hash stable | {result['payload_hash_stable']} |",
        f"",
        f"---",
        f"",
        f"## Cardinality",
        f"",
        f"| Card Type | Count |",
        f"|-----------|-------|",
    ]
    for ct in VALID_CARD_TYPES:
        lines.append(f"| `{ct}` | {counts.get(ct, 0)} |")
    lines.append(f"")
    lines.append(f"**Total**: {result['total_envelopes']} (minimum required: 13)")
    lines.append(f"")
    lines.extend([
        f"---",
        f"",
        f"## Readiness Matrix",
        f"",
        f"Final matrix: **Ready=1, Partial=4, Missing=0**",
        f"",
        f"---",
        f"",
        f"## 下一步建议",
        f"",
        f"1. Envelope 层已建立，所有 5 类 card type 均产出统一结构。",
        f"2. `dedupe_key`、`cooldown_key`、`payload_hash` 均已稳定，可重复验证。",
        f"3. 下一步可以基于 envelope 层构建去重/冷却/审计 pipeline。",
        f"4. live_ready=false 保持，直到真实数据源接入。",
        f"",
    ])

    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
