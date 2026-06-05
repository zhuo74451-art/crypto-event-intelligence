"""Market Radar v1.11-K — Content Value Review

Reads v1.11-J-Mock sent log and v1.11-I rehearsal results, performs content value
audit on the 3 mock_sent cards, and produces a structured review result.

This is a LOCAL-ONLY review: no TG send, no external AI call, no paid API.
The output is designed for human/Gemini review as the next step.

Usage:
    python scripts/run_market_radar_v111k_content_value_review.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CN_TZ = timezone(timedelta(hours=8))
RUN_ID = "20260604_202718"
TASK_ID = "20260604_202718.r05"
NOW_STR = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

# ── Constants ─────────────────────────────────────────────────────────────────
VERSION = "v1.11-K"
MODE = "content_value_review"

# Input paths
SENT_LOG_PATH = ROOT / "logs" / "market_radar" / "v111j_mock_sent_messages_log.json"
MOCK_REHEARSAL_PATH = ROOT / "results" / "market_radar_v111j_mock_sender_rehearsal_result.json"
PRE_TEST_SEND_PATH = ROOT / "results" / "market_radar_v111i_pre_test_send_rehearsal_result.json"

# Output paths
RESULT_JSON_PATH = ROOT / "results" / "market_radar_v111k_content_value_review_result.json"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v111k_content_value_review.md"
GEMINI_PACKET_PATH = ROOT / "runs" / "market_radar" / "v111k_gemini_review_packet.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v111k_content_value_review_handoff.md"

# Target 3 cards
TARGET_CARDS = [
    {"mock_message_id": "mock_v111j_001", "signal_id": "H6-07", "asset": "ARB"},
    {"mock_message_id": "mock_v111j_002", "signal_id": "H5-01", "asset": "ETH"},
    {"mock_message_id": "mock_v111j_003", "signal_id": "H1-01", "asset": "ETH"},
]

# Tier-1 assets (BTC, ETH, SOL — highest attention)
TIER_1_ASSETS = {"BTC", "ETH", "SOL"}
TIER_2_ASSETS = {"ARB", "SUI", "AVAX", "LINK", "DOT", "MATIC", "OP", "NEAR", "LTC"}


def load_json(path: Path) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_signal_record(signal_id: str, all_records: list[dict]) -> dict | None:
    """Find a signal record in the v1.11-I all_records by signal_id."""
    for r in all_records:
        if r.get("signal_id") == signal_id:
            return r
    return None


def compute_signal_value_score(
    record: dict,
    asset: str,
    has_upgrade: bool,
) -> int:
    """Compute signal_value_score (0-100) based on scoring rules.

    Rules:
      - Multi-factor support: +25
      - OI support: +15
      - Volume support: +15
      - Upgrade override: +20
      - Tier-1 / high-attention asset: +10
      - Not pure price move: +15
    """
    score = 0
    cq = record.get("content_quality", {})
    vg = record.get("value_gate", {})

    # Multi-factor support
    if cq.get("has_multi_factor_support", False):
        score += 25

    # OI support
    if cq.get("has_oi_or_volume_support", False):
        # Check specifically for OI
        reasons = vg.get("reasons", [])
        has_oi = any("oi_confirmation" in r for r in reasons)
        if has_oi:
            score += 15

    # Volume support
    if cq.get("has_oi_or_volume_support", False):
        reasons = vg.get("reasons", [])
        has_vol = any("volume_confirmation" in r for r in reasons)
        if has_vol:
            score += 15

    # Upgrade override
    if has_upgrade:
        score += 20

    # Tier-1 asset
    if asset in TIER_1_ASSETS:
        score += 10
    elif asset in TIER_2_ASSETS:
        score += 5  # partial credit for known mid-cap

    # Not pure price noise
    if not cq.get("is_price_only_noise", True):
        score += 15

    return min(score, 100)


def compute_risk_score(
    record: dict,
    asset: str,
    is_duplicate_asset: bool,
    payload_preview: str,
) -> int:
    """Compute risk_score (0-100).

    Rules:
      - Only price movement: +30
      - No OI / volume: +20
      - Expression like market broadcast: +15
      - Overclaiming / over-inference: +20
      - Duplicate with another card: +15
    """
    score = 0
    cq = record.get("content_quality", {})

    # Only price movement
    if cq.get("is_price_only_noise", False):
        score += 30

    # No OI / volume
    if not cq.get("has_oi_or_volume_support", False):
        score += 20

    # Expression like market broadcast — check language patterns
    broadcast_patterns = [
        "行情异动", "急跌", "急涨", "暴跌", "暴涨",
        "一句话", "触发原因",
    ]
    broadcast_hits = sum(1 for p in broadcast_patterns if p in payload_preview)
    if broadcast_hits >= 4:
        score += 15
    elif broadcast_hits >= 2:
        score += 8

    # Overclaiming / over-inference
    overclaim_patterns = [
        "极端", "超强", "狂暴", "炸裂", "必看",
        "无疑", "确定", "100%", "必定",
    ]
    overclaim_hits = sum(1 for p in overclaim_patterns if p in payload_preview)
    if overclaim_hits > 0:
        score += min(20, overclaim_hits * 10)

    # AI-style language patterns
    ai_style_patterns = [
        "全确认", "四重确认", "多重确认",
    ]
    ai_hits = sum(1 for p in ai_style_patterns if p in payload_preview)
    if ai_hits > 0:
        score += min(15, ai_hits * 8)

    # Duplicate asset
    if is_duplicate_asset:
        score += 15

    return min(score, 100)


def determine_grade(signal_score: int, risk_score: int) -> str:
    """Determine final grade: A, B, C, or D."""
    net = signal_score - risk_score
    if net >= 70 and risk_score <= 30:
        return "A"
    elif net >= 50 and risk_score <= 50:
        return "B"
    elif net >= 30:
        return "C"
    else:
        return "D"


def determine_recommendation(grade: str, risk_score: int, is_duplicate: bool) -> str:
    """Determine recommendation: keep, revise, observe, or drop."""
    if grade == "A":
        return "keep"
    elif grade == "B":
        if is_duplicate:
            return "revise"
        return "keep"
    elif grade == "C":
        if risk_score >= 60:
            return "observe"
        return "revise"
    else:
        return "drop"


def review_card(
    card: dict,
    sent_entry: dict,
    record: dict | None,
    all_cards: list[dict],
) -> dict:
    """Perform content review on a single mock_sent card."""
    mock_id = card["mock_message_id"]
    signal_id = card["signal_id"]
    asset = card["asset"]
    payload_preview = sent_entry.get("payload_preview", "")

    # Check if duplicate asset (another card has same asset)
    same_asset_cards = [c for c in all_cards if c["asset"] == asset and c["mock_message_id"] != mock_id]
    is_duplicate_asset = len(same_asset_cards) > 0

    if record is None:
        return {
            "mock_message_id": mock_id,
            "signal_id": signal_id,
            "asset": asset,
            "content_review": {
                "is_price_only_noise": True,
                "has_multi_factor_support": False,
                "has_oi_support": False,
                "has_volume_support": False,
                "has_upgrade_signal": False,
                "has_clear_trade_relevance": False,
                "has_overclaiming_risk": True,
                "has_ai_style_risk": True,
                "has_duplicate_risk": is_duplicate_asset,
                "readability_score": 0,
                "signal_value_score": 0,
                "risk_score": 80,
                "final_grade": "D",
                "recommendation": "drop",
                "reason": f"Signal record not found in v1.11-I data for {signal_id}",
            },
        }

    cq = record.get("content_quality", {})
    vg = record.get("value_gate", {})
    cd = record.get("cooldown_gate", {})
    reasons = vg.get("reasons", [])

    has_upgrade = cd.get("decision") == "upgrade_override"
    has_oi = any("oi_confirmation" in r for r in reasons)
    has_vol = any("volume_confirmation" in r for r in reasons)
    has_funding = any("funding_extreme" in r for r in reasons)
    has_multi_asset = any("multi_asset_sync" in r for r in reasons)
    is_price_only = cq.get("is_price_only_noise", False)
    has_multi_factor = cq.get("has_multi_factor_support", False)

    # Content-specific checks
    has_overclaiming = any(p in payload_preview for p in ["极端", "炸裂", "必看", "无疑", "100%", "必定"])
    has_ai_style = any(p in payload_preview for p in ["全确认", "四重确认", "多重确认", "极端四重"])

    # Readability: check structure
    readability = 70  # base
    if "币种" in payload_preview:
        readability += 5
    if "涨跌幅" in payload_preview:
        readability += 5
    if "观察窗口" in payload_preview:
        readability += 5
    if "行情查看" in payload_preview or "CoinGecko" in payload_preview:
        readability += 5
    if len(payload_preview) < 500:
        readability += 5
    if "不构成交易建议" in payload_preview or "不代表交易方向" in payload_preview:
        readability += 5
    readability = min(readability, 100)

    # Compute scores
    signal_score = compute_signal_value_score(record, asset, has_upgrade)
    risk_score = compute_risk_score(record, asset, is_duplicate_asset, payload_preview)
    grade = determine_grade(signal_score, risk_score)
    recommendation = determine_recommendation(grade, risk_score, is_duplicate_asset)

    # Build reason
    factor_count = sum([1 for x in [has_oi, has_vol, has_funding, has_multi_asset] if x])
    reason_parts = []
    reason_parts.append(f"value_score={vg.get('score', '?')}")
    reason_parts.append(f"cooldown={cd.get('decision', '?')}")
    reason_parts.append(f"factors={factor_count}/4 (OI={has_oi}, Vol={has_vol}, Funding={has_funding}, MultiAsset={has_multi_asset})")
    if has_upgrade:
        reason_parts.append("upgrade_override=yes")
    if is_duplicate_asset:
        reason_parts.append(f"duplicate_asset_with={same_asset_cards[0]['mock_message_id']}")
    if has_overclaiming:
        reason_parts.append("overclaiming_detected")
    if has_ai_style:
        reason_parts.append("ai_style_detected")
    reason_parts.append(f"signal_value_score={signal_score}, risk_score={risk_score}, grade={grade}")

    return {
        "mock_message_id": mock_id,
        "signal_id": signal_id,
        "asset": asset,
        "content_review": {
            "is_price_only_noise": is_price_only,
            "has_multi_factor_support": has_multi_factor,
            "has_oi_support": has_oi,
            "has_volume_support": has_vol,
            "has_upgrade_signal": has_upgrade,
            "has_clear_trade_relevance": has_multi_factor and not is_price_only,
            "has_overclaiming_risk": has_overclaiming,
            "has_ai_style_risk": has_ai_style,
            "has_duplicate_risk": is_duplicate_asset,
            "readability_score": readability,
            "signal_value_score": signal_score,
            "risk_score": risk_score,
            "final_grade": grade,
            "recommendation": recommendation,
            "reason": "; ".join(reason_parts),
        },
    }


def build_mvp_judgement(records: list[dict], summary: dict) -> dict:
    """Build MVP judgement section."""
    keep_count = summary.get("keep", 0)
    revise_count = summary.get("revise", 0)
    a_grade = sum(1 for r in records if r["content_review"]["final_grade"] == "A")
    b_grade = sum(1 for r in records if r["content_review"]["final_grade"] == "B")

    technical_loop_complete = True  # proven by v1.11-J
    content_loop_complete = len(records) == 3 and all(
        r["content_review"]["final_grade"] != "D" for r in records
    )

    # Ready for real test send only if we have A-grade keep signals
    ready_for_test = keep_count >= 1 and a_grade >= 1

    # Official channel NOT ready by default
    ready_for_official = False

    if a_grade >= 2 and keep_count >= 2:
        reason = (
            "Market Radar MVP 主体闭环完成: 技术链完整 (SignalValueGate → CooldownGate → "
            "payload render → pre_send_gate → mock_sender → sent log), "
            "内容审计完成 (3/3 张 mock_sent 卡内容可评估)。"
            "不建议正式频道解冻：当前只有 3 张 mock_sent 卡，缺乏真实 TG 发送验证、"
            "sender 安全抽象、cooldown 持久化、OI-volume delta 追踪。"
            "建议先进入真实测试群小规模发送 (1-2 张 A 级卡) 验证端到端效果。"
        )
    elif ready_for_test:
        reason = (
            "Market Radar MVP 技术链路闭环完成 (v1.11-J verified)。"
            "内容审计发现至少 1 张 A 级卡可进入测试发送候选。"
            "不建议正式频道解冻：需要 (1) 真实 TG 测试群小规模发送验证, "
            "(2) sender 安全抽象 (token 注入、发送重试、失败降级), "
            "(3) cooldown 持久化 (跨进程/跨重启), "
            "(4) OI-volume delta 追踪 (以区分趋势性 vs 瞬时异动)。"
        )
    else:
        reason = (
            "Market Radar MVP 技术链路闭环完成 (v1.11-J verified)。"
            "但内容审计未发现 A 级卡，3 张 mock_sent 卡均需 revise 或 observe。"
            "不建议正式频道解冻。建议优先改进卡片文案质量和信号筛选逻辑，"
            "再进入真实测试群发送阶段。"
        )

    return {
        "technical_loop_complete": technical_loop_complete,
        "content_loop_complete": content_loop_complete,
        "ready_for_real_test_channel_send": ready_for_test,
        "ready_for_official_channel": ready_for_official,
        "reason": reason,
    }


def main():
    print(f"=== Market Radar {VERSION} — Content Value Review ===")
    print(f"Run: {NOW_STR}")
    print()

    # ── Load input data ──────────────────────────────────────────────────────
    print("[1/5] Loading input data...")
    sent_log = load_json(SENT_LOG_PATH)
    mock_result = load_json(MOCK_REHEARSAL_PATH)
    pre_send_result = load_json(PRE_TEST_SEND_PATH)

    all_records = pre_send_result.get("all_records", [])
    print(f"  Sent log entries: {len(sent_log)}")
    print(f"  Mock rehearsal: {mock_result.get('mock_sent_count', 0)} mock_sent")
    print(f"  Pre-send rehearsal records: {len(all_records)}")
    print()

    # ── Match sent entries to cards ──────────────────────────────────────────
    print("[2/5] Matching mock_sent entries to target cards...")
    sent_map = {}
    for entry in sent_log:
        signal_id = entry.get("signal_id", "")
        sent_map[signal_id] = entry

    matched = []
    for card in TARGET_CARDS:
        sid = card["signal_id"]
        entry = sent_map.get(sid)
        if entry:
            matched.append((card, entry))
            print(f"  [OK] {card['mock_message_id']} <- {sid} ({card['asset']})")
        else:
            print(f"  [MISS] {card['mock_message_id']} <- {sid} -- NOT FOUND in sent log")

    print()

    # ── Content review per card ──────────────────────────────────────────────
    print("[3/5] Performing content review...")
    records = []
    for card, entry in matched:
        signal_id = card["signal_id"]
        record = find_signal_record(signal_id, all_records)
        review = review_card(card, entry, record, TARGET_CARDS)
        records.append(review)
        cr = review["content_review"]
        print(f"  {review['mock_message_id']} ({review['asset']}): "
              f"grade={cr['final_grade']}, "
              f"sig={cr['signal_value_score']}, "
              f"risk={cr['risk_score']}, "
              f"rec={cr['recommendation']}")

    print()

    # ── Summary ──────────────────────────────────────────────────────────────
    print("[4/5] Computing summary...")
    summary = {"keep": 0, "revise": 0, "observe": 0, "drop": 0}
    for r in records:
        rec = r["content_review"]["recommendation"]
        summary[rec] = summary.get(rec, 0) + 1

    print(f"  keep={summary['keep']}, revise={summary['revise']}, "
          f"observe={summary['observe']}, drop={summary['drop']}")

    # Best candidate: prefer grade A over B over C, then highest signal_value_score
    grade_order = {"A": 0, "B": 1, "C": 2, "D": 3}
    candidates = [r for r in records if r["content_review"]["recommendation"] in ("keep", "revise")]
    if candidates:
        best = min(candidates, key=lambda r: (
            grade_order.get(r["content_review"]["final_grade"], 99),
            -r["content_review"]["signal_value_score"]
        ))
    else:
        best = records[0] if records else {}

    best_candidate = {
        "mock_message_id": best.get("mock_message_id", ""),
        "signal_id": best.get("signal_id", ""),
        "asset": best.get("asset", ""),
        "grade": best.get("content_review", {}).get("final_grade", "?"),
        "recommendation": best.get("content_review", {}).get("recommendation", "?"),
        "reason": best.get("content_review", {}).get("reason", ""),
    }
    print(f"  Best candidate: {best_candidate['mock_message_id']} "
          f"({best_candidate['asset']}, grade={best_candidate['grade']})")

    mvp = build_mvp_judgement(records, summary)
    print()

    # ── Write result JSON ────────────────────────────────────────────────────
    print("[5/5] Writing output files...")
    result = {
        "version": VERSION,
        "mode": MODE,
        "real_tg_sent": False,
        "external_ai_called": False,
        "paid_api_called": False,
        "reviewed_count": len(records),
        "summary": summary,
        "best_candidate": best_candidate,
        "records": records,
        "mvp_judgement": mvp,
    }

    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RESULT_JSON_PATH}")

    print()
    print("=== Content Value Review Complete ===")
    print(f"Reviewed: {len(records)} mock_sent cards")
    print(f"Best candidate: {best_candidate['mock_message_id']} ({best_candidate['asset']})")
    print(f"MVP technical loop: {mvp['technical_loop_complete']}")
    print(f"MVP content loop: {mvp['content_loop_complete']}")
    print(f"Ready for test send: {mvp['ready_for_real_test_channel_send']}")
    print(f"Ready for official: {mvp['ready_for_official_channel']}")

    return result


if __name__ == "__main__":
    main()
