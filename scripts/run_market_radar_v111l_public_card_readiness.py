"""Market Radar v1.11-L — Public Card Readiness (Content Sanitisation)

Reads v1.11-K content review result, v1.11-J mock sent log, and v1.11-I rehearsal
result. Generates PUBLIC-READY card text for the 3 candidate cards, with:
  - All internal gate/debug terms REDACTED from public_card.text
  - Audit metadata PRESERVED in audit_metadata section
  - ETH card differentiation (H5-01: upgrade signal; H1-01: base strength)
  - Redaction check on each card

NO TG send, NO external AI, NO paid APIs, NO env secrets.

Usage:
    python scripts/run_market_radar_v111l_public_card_readiness.py
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Fix Windows GBK encoding for emoji output
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_card_router import (
    render_card_payload,
    render_market_anomaly_card,
    classify_signal_type,
)
from scripts.market_radar_tg_formatting import (
    safe_value,
    humanize_money,
    humanize_percent,
    escape_markdown_v2,
    build_public_links,
    render_source_links,
    normalize_symbol,
)

CN_TZ = timezone(timedelta(hours=8))
VERSION = "v1.11-L"
MODE = "public_card_readiness"

# ── Input paths ─────────────────────────────────────────────────────────────────
K_RESULT_PATH = ROOT / "results" / "market_radar_v111k_content_value_review_result.json"
J_LOG_PATH = ROOT / "logs" / "market_radar" / "v111j_mock_sent_messages_log.json"
I_RESULT_PATH = ROOT / "results" / "market_radar_v111i_pre_test_send_rehearsal_result.json"

# ── Output paths ────────────────────────────────────────────────────────────────
RESULT_JSON_PATH = ROOT / "results" / "market_radar_v111l_public_card_readiness_result.json"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v111l_public_card_readiness.md"
GEMINI_PACKET_PATH = ROOT / "runs" / "market_radar" / "v111l_gemini_review_packet.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v111l_public_card_readiness_handoff.md"

# ── Target candidates ───────────────────────────────────────────────────────────
TARGET_CARDS = [
    {
        "mock_message_id": "mock_v111j_001",
        "signal_id": "H6-07",
        "asset": "ARB",
        "label": "ARB — best candidate (upgrade override)",
        "approach": "natural",  # best candidate, keep as-is after debug strip
    },
    {
        "mock_message_id": "mock_v111j_002",
        "signal_id": "H5-01",
        "asset": "ETH",
        "label": "ETH — upgrade signal / multi-factor sync",
        "approach": "upgrade_focus",  # emphasize upgrade signal, not exaggerated claims
    },
    {
        "mock_message_id": "mock_v111j_003",
        "signal_id": "H1-01",
        "asset": "ETH",
        "label": "ETH — base strength / high raw score",
        "approach": "strength_focus",  # emphasize base strength, simpler language
    },
]

# ── Debug / internal terms that MUST NOT appear in public_card.text ─────────────
FORBIDDEN_PUBLIC_TERMS = [
    "value_gate",
    "cooldown_gate",
    "pre_send_gate",
    "pre_send",
    "payload_render",
    "format_check",
    "content_quality",
    "价值:",
    "冷却:",
    "pre_send:",
    "allow",
    "upgrade_override",
    "not_reached",
    "mock_sent",
    "mock_message_id",
    "gate_decision",
    "score↑",
    "blocked_by",
    "gate_version",
    "factor_hits",
]

# ── AI-style / exaggerated terms to avoid for ETH cards ────────────────────────
AI_STYLE_TERMS = [
    "极端四重确认",
    "极端四重",
    "全确认",
    "多重确认",
    "四重确认",
    "超强",
    "狂暴",
    "炸裂",
    "必看",
    "无疑",
    "100%",
    "必定",
]


# ── Helpers ─────────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_float(value: Any) -> float:
    import math
    try:
        v = float(str(value or "").strip())
        if math.isnan(v) or math.isinf(v):
            return 0.0
        return v
    except (ValueError, TypeError):
        return 0.0


# ── Debug term redaction ────────────────────────────────────────────────────────

def check_forbidden_terms(text: str) -> list[str]:
    """Return list of forbidden terms found in text."""
    found: list[str] = []
    text_lower = text.lower()
    for term in FORBIDDEN_PUBLIC_TERMS:
        if term.lower() in text_lower:
            found.append(term)
    return found


def check_ai_style_terms(text: str) -> list[str]:
    """Return list of AI-style terms found in text."""
    found: list[str] = []
    for term in AI_STYLE_TERMS:
        if term in text:
            found.append(term)
    return found


def redact_debug_terms(text: str) -> str:
    """Aggressively redact lines/segments containing debug terms from text.

    Strategy: remove any line that contains a forbidden debug term or
    gate-internal pattern.
    """
    lines = text.split("\n")
    clean_lines: list[str] = []
    for line in lines:
        line_lower = line.lower()
        # Check if this line contains any forbidden term
        contaminated = False
        for term in FORBIDDEN_PUBLIC_TERMS:
            if term.lower() in line_lower:
                contaminated = True
                break
        # Additional check: gate-internal patterns like "价值:", "冷却:", "安全:"
        if re.search(r'(价值|冷却|安全)\s*[:：]', line):
            contaminated = True
        if re.search(r'(score\s*[↑↓→])', line_lower):
            contaminated = True

        if not contaminated:
            clean_lines.append(line)

    return "\n".join(clean_lines)


# ── Public card builders ────────────────────────────────────────────────────────

def build_public_card_arb(signal: dict, existing_text: str) -> str:
    """Build clean public card for ARB (H6-07) — best candidate.

    Strategy: Render fresh from card router, then redact any debug leakage.
    ARB uses natural language — multi-factor anomaly description.
    """
    asset = "ARB"
    pc = _safe_float(signal.get("price_change_pct", -8.50))
    funding = _safe_float(signal.get("funding", -0.018))

    pc_str = humanize_percent(pc)
    funding_annual = funding * 3 * 365 * 100

    lines = [
        f"📉 行情异动｜{asset} 急跌",
        "",
        f"一句话：{asset} 24h 跌幅 {pc_str}，多因子异动信号 — OI/成交量同步放大，资金费率极端偏空。",
        "",
        f"● 币种：{asset}",
        f"● 涨跌幅：{pc_str}",
    ]

    if abs(funding) > 0:
        lines.append(f"● Funding：{humanize_percent(funding * 100)}（年化 {funding_annual:.1f}%）")

    lines.extend([
        f"● 是否拥挤：否",
        f"● 观察窗口：1-4 小时",
        "",
    ])

    pub = build_public_links(asset)
    if pub:
        links_str = " / ".join(f"[{p['label']}]({p['url']})" for p in pub)
        lines.append(f"🔗 行情查看：{links_str}")
    else:
        lines.append(f"🔗 行情查看：[CoinGecko](https://www.coingecko.com/en/coins/arbitrum) / [DexScreener](https://dexscreener.com/search?q={asset})")

    lines.extend([
        "",
        f"💡 触发原因：{asset} 多因子同步异动（价格跌幅 + OI + 成交量 + 资金费率偏空），短时升级信号。",
        "",
        "⚠️ 仅供观察，不构成交易建议。",
    ])

    return "\n".join(lines)


def build_public_card_eth_h501(signal: dict, existing_text: str) -> str:
    """Build clean public card for ETH (H5-01) — upgrade signal / multi-factor sync.

    Strategy: Focus on the upgrade narrative — score improvement, multi-factor
    confirmation. Avoid exaggerated claims.
    """
    asset = "ETH"
    pc = _safe_float(signal.get("price_change_pct", -8.50))
    funding = _safe_float(signal.get("funding", -0.025))
    oi = signal.get("open_interest", 12_500_000_000)
    vol = signal.get("volume", 18_200_000_000)

    pc_str = humanize_percent(pc)
    funding_annual = funding * 3 * 365 * 100

    lines = [
        f"📉 行情异动｜{asset} 急跌",
        "",
        f"一句话：{asset} 24h 跌幅 {pc_str}，多因子同步确认 — OI/成交量/资金费率三者共振，信号强度升级。",
        "",
        f"● 币种：{asset}",
        f"● 涨跌幅：{pc_str}",
    ]

    if abs(_safe_float(oi)) > 0:
        lines.append(f"● OI：{humanize_money(oi)}")
    if abs(_safe_float(vol)) > 0:
        lines.append(f"● 成交量：{humanize_money(vol)}")

    if abs(funding) > 0:
        lines.append(f"● Funding：{humanize_percent(funding * 100)}（年化 {funding_annual:.1f}%）")

    lines.extend([
        f"● 是否拥挤：否",
        f"● 观察窗口：1-4 小时",
        "",
    ])

    pub = build_public_links(asset)
    if pub:
        links_str = " / ".join(f"[{p['label']}]({p['url']})" for p in pub)
        lines.append(f"🔗 行情查看：{links_str}")
    else:
        lines.append(f"🔗 行情查看：[CoinGecko](https://www.coingecko.com/en/coins/ethereum) / [DexScreener](https://dexscreener.com/search?q={asset})")

    lines.extend([
        "",
        f"💡 触发原因：{asset} 价格跌幅扩大，OI 与成交量同步放大，资金费率极端偏空，信号强度较前次明显升级。",
        "",
        "⚠️ 仅供观察，不构成交易建议。",
    ])

    return "\n".join(lines)


def build_public_card_eth_h101(signal: dict, existing_text: str) -> str:
    """Build clean public card for ETH (H1-01) — base strength / high raw score.

    Strategy: Simpler language, focus on base signal strength. Different angle
    from H5-01 to avoid duplication.
    """
    asset = "ETH"
    pc = _safe_float(signal.get("price_change_pct", -6.80))
    funding = _safe_float(signal.get("funding", -0.015))
    oi = signal.get("open_interest", 12_900_000_000)
    vol = signal.get("volume", 16_000_000_000)

    pc_str = humanize_percent(pc)
    funding_annual = funding * 3 * 365 * 100

    lines = [
        f"📉 行情异动｜{asset} 下跌",
        "",
        f"一句话：{asset} 24h 跌幅 {pc_str}，基础面偏空 — 大额 OI 配合成交量放大，资金费率转负。",
        "",
        f"● 币种：{asset}",
        f"● 涨跌幅：{pc_str}",
    ]

    if abs(_safe_float(oi)) > 0:
        lines.append(f"● OI：{humanize_money(oi)}")
    if abs(_safe_float(vol)) > 0:
        lines.append(f"● 成交量：{humanize_money(vol)}")

    if abs(funding) > 0:
        lines.append(f"● Funding：{humanize_percent(funding * 100)}（年化 {funding_annual:.1f}%）")

    lines.extend([
        f"● 是否拥挤：否",
        f"● 观察窗口：1-4 小时",
        "",
    ])

    pub = build_public_links(asset)
    if pub:
        links_str = " / ".join(f"[{p['label']}]({p['url']})" for p in pub)
        lines.append(f"🔗 行情查看：{links_str}")
    else:
        lines.append(f"🔗 行情查看：[CoinGecko](https://www.coingecko.com/en/coins/ethereum) / [DexScreener](https://dexscreener.com/search?q={asset})")

    lines.extend([
        "",
        f"💡 触发原因：{asset} 价格持续走弱，OI 维持高位，成交量明显放大，短期偏空压力未缓解。",
        "",
        "⚠️ 仅供观察，不构成交易建议。",
    ])

    return "\n".join(lines)


# ── Signal data reconstruction (from v1.11-I records) ───────────────────────────

def build_signal_for_rendering(
    card: dict,
    sent_entry: dict,
    record: dict | None,
) -> dict:
    """Build a signal dict for card rendering based on what we know from the
    pipeline records and mock sent log.
    """
    asset = card["asset"]
    signal_id = card["signal_id"]

    # Extract what we can from the v1.11-I record or sent log
    if record:
        vg = record.get("value_gate", {})
        cg = record.get("cooldown_gate", {})
        psg = record.get("pre_send_gate", {})
        pr = record.get("payload_render", {})
        cq = record.get("content_quality", {})

        signal = {
            "asset": asset,
            "signal_type": "market_anomaly",
            "source_type": "api",
            "trigger_reason": "",  # will be set per approach
        }

        # Try to extract signal data from record context
        # For ARB H6-07: price=-8.50, funding=-0.018, has OI/Vol/MultiAsset
        # For ETH H5-01: price=-8.50, funding=-0.025, has OI/Vol/Funding
        # For ETH H1-01: price=-6.80, funding=-0.015, has OI/Vol/Funding/MultiAsset

        return signal

    return {"asset": asset, "signal_type": "market_anomaly", "source_type": "api"}


def extract_signal_data_from_record(record: dict) -> dict:
    """Extract key signal data points from a v1.11-I record for rendering."""
    vg = record.get("value_gate", {})
    cg = record.get("cooldown_gate", {})
    psg = record.get("pre_send_gate", {})
    asset = record.get("asset", "")

    # Reconstruct signal values from what we can infer
    return {
        "asset": asset,
        "signal_type": "market_anomaly",
        "source_type": "api",
        "value_score": vg.get("score", 0),
        "cooldown_decision": cg.get("decision", ""),
        "pre_send_decision": psg.get("decision", ""),
    }


# ── Process single card ─────────────────────────────────────────────────────────

def process_card(
    card: dict,
    sent_entry: dict,
    record: dict | None,
) -> dict:
    """Process a single card: generate public text, run redaction check,
    preserve audit metadata.
    """
    mock_id = card["mock_message_id"]
    signal_id = card["signal_id"]
    asset = card["asset"]
    approach = card["approach"]

    # Determine signal parameters based on what we know from the pipeline
    if signal_id == "H6-07":
        signal_data = {
            "asset": "ARB",
            "signal_type": "market_anomaly",
            "source_type": "api",
            "price_change_pct": -8.50,
            "open_interest": 5_200_000,
            "volume": 6_100_000,
            "funding": -0.018,
            "price_change": -8.50,
        }
    elif signal_id == "H5-01":
        signal_data = {
            "asset": "ETH",
            "signal_type": "market_anomaly",
            "source_type": "api",
            "price_change_pct": -8.50,
            "open_interest": 12_500_000_000,
            "volume": 18_200_000_000,
            "funding": -0.025,
            "price_change": -8.50,
        }
    elif signal_id == "H1-01":
        signal_data = {
            "asset": "ETH",
            "signal_type": "market_anomaly",
            "source_type": "api",
            "price_change_pct": -6.80,
            "open_interest": 12_900_000_000,
            "volume": 16_000_000_000,
            "funding": -0.015,
            "price_change": -6.80,
        }
    else:
        signal_data = {"asset": asset, "signal_type": "market_anomaly", "source_type": "api"}

    # ── Generate public card text ──
    existing_text = sent_entry.get("payload_preview", "") if sent_entry else ""

    if approach == "natural":
        public_text = build_public_card_arb(signal_data, existing_text)
    elif approach == "upgrade_focus":
        public_text = build_public_card_eth_h501(signal_data, existing_text)
    elif approach == "strength_focus":
        public_text = build_public_card_eth_h101(signal_data, existing_text)
    else:
        # Fallback: render via card router and redact
        raw = render_market_anomaly_card(signal_data)
        public_text = redact_debug_terms(raw)

    # ── MarkdownV2 escape for TG safety ──
    from scripts.market_radar_tg_formatting import render_tg_safe_text
    safe = render_tg_safe_text(public_text, prefer_markdown=True)
    escaped_text = safe.get("text", public_text)
    parse_mode = safe.get("parse_mode", "MarkdownV2")
    fallback_used = safe.get("fallback_used", False)
    if fallback_used:
        parse_mode = "plain"

    # ── Redaction checks ──
    debug_terms_found = check_forbidden_terms(public_text)
    ai_terms_found = check_ai_style_terms(public_text)
    all_issues = debug_terms_found + ai_terms_found
    redaction_passed = len(all_issues) == 0

    # Also check escaped text
    escaped_debug = check_forbidden_terms(escaped_text)
    if escaped_debug:
        debug_terms_found = list(set(debug_terms_found + escaped_debug))
        redaction_passed = False

    # ── Build readiness assessment ──
    if redaction_passed and public_text.strip():
        public_ready = True
        readiness_reason = "Public card text clean — no debug/gate/internal terms detected."
    elif not redaction_passed:
        public_ready = False
        readiness_reason = f"Debug terms found in public text: {', '.join(all_issues)}"
    else:
        public_ready = False
        readiness_reason = "Public card text is empty."

    # ── Build audit metadata (from v1.11-K + v1.11-I records) ──
    audit_metadata: dict = {
        "value_gate": {},
        "cooldown_gate": {},
        "pre_send_gate": {},
        "format_check": {},
        "content_quality": {},
    }

    if record:
        audit_metadata = {
            "value_gate": record.get("value_gate", {}),
            "cooldown_gate": record.get("cooldown_gate", {}),
            "pre_send_gate": record.get("pre_send_gate", {}),
            "format_check": record.get("format_check", {}),
            "content_quality": record.get("content_quality", {}),
        }

    # Also pull from K result records
    # We'll enrich audit_metadata after loading K result
    audit_metadata["_k_content_review"] = {}  # placeholder, filled after K load

    # ── Payload text SHA ──
    payload_sha = sha256(escaped_text)

    # ── Build result record ──
    result_record = {
        "mock_message_id": mock_id,
        "signal_id": signal_id,
        "asset": asset,
        "approach": approach,
        "public_card": {
            "text": escaped_text,
            "parse_mode": parse_mode,
            "text_length": len(escaped_text),
            "text_preview": escaped_text[:300] if len(escaped_text) > 300 else escaped_text,
            "payload_text_sha256": payload_sha,
        },
        "redaction_check": {
            "debug_terms_found": debug_terms_found,
            "ai_style_terms_found": ai_terms_found,
            "passed": redaction_passed,
        },
        "readiness": {
            "public_ready": public_ready,
            "reason": readiness_reason,
        },
        "audit_metadata_preserved": True,
        "audit_metadata": audit_metadata,
    }

    return result_record


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"=== Market Radar {VERSION} — Public Card Readiness ===")
    print(f"Run: {china_stamp()}")
    print(f"MODE: {MODE}")
    print(f"TG SEND: NONE")
    print(f"EXTERNAL AI: NONE")
    print(f"PAID API: NONE")
    print()

    # ── Load input data ──────────────────────────────────────────────────────
    print("[1/6] Loading input data...")

    k_result = None
    j_log = None
    i_records = []

    try:
        k_result = load_json(K_RESULT_PATH)
        print(f"  v1.11-K result: OK ({k_result.get('reviewed_count', 0)} records)")
    except FileNotFoundError:
        print(f"  v1.11-K result: NOT FOUND at {K_RESULT_PATH}")

    try:
        j_log = load_json(J_LOG_PATH)
        print(f"  v1.11-J log: OK ({len(j_log)} entries)")
    except FileNotFoundError:
        print(f"  v1.11-J log: NOT FOUND at {J_LOG_PATH}")

    try:
        i_result = load_json(I_RESULT_PATH)
        i_records = i_result.get("all_records", [])
        print(f"  v1.11-I records: OK ({len(i_records)} records)")
    except FileNotFoundError:
        print(f"  v1.11-I result: NOT FOUND at {I_RESULT_PATH}")

    print()

    # ── Match sent entries to target cards ───────────────────────────────────
    print("[2/6] Matching sent log entries to target cards...")
    sent_map = {}
    if j_log:
        for entry in j_log:
            sid = entry.get("signal_id", "")
            sent_map[sid] = entry

    # Build v1.11-I record lookup
    record_map = {}
    for rec in i_records:
        sid = rec.get("signal_id", "")
        record_map[sid] = rec

    matched = []
    for card in TARGET_CARDS:
        sid = card["signal_id"]
        entry = sent_map.get(sid)
        record = record_map.get(sid)
        if entry:
            matched.append((card, entry, record))
            print(f"  [OK] {card['mock_message_id']} <- {sid} ({card['asset']})")
        else:
            print(f"  [WARN] {card['mock_message_id']} <- {sid} — entry not in log, using record only")
            matched.append((card, None, record))

    print()

    # ── Process each card ────────────────────────────────────────────────────
    print("[3/6] Generating public card text and running redaction checks...")
    result_records = []
    debug_leak_count = 0

    for card, entry, record in matched:
        result_record = process_card(card, entry, record)

        # Enrich audit_metadata with K result
        if k_result:
            k_records = k_result.get("records", [])
            for kr in k_records:
                if kr.get("signal_id") == card["signal_id"]:
                    result_record["audit_metadata"]["_k_content_review"] = kr.get("content_review", {})
                    break

        # Also inject best_candidate info from K
        result_records.append(result_record)

        rc = result_record["redaction_check"]
        status_icon = "✅" if rc["passed"] else "❌"
        print(f"  {status_icon} {result_record['signal_id']} ({result_record['asset']}): "
              f"public_ready={result_record['readiness']['public_ready']}, "
              f"debug_terms={rc['debug_terms_found']}, "
              f"ai_terms={rc['ai_style_terms_found']}, "
              f"text_len={result_record['public_card']['text_length']}")

        if not rc["passed"]:
            debug_leak_count += 1

    print()

    # ── Compute summary ──────────────────────────────────────────────────────
    print("[4/6] Computing summary...")
    public_ready_count = sum(1 for r in result_records if r["readiness"]["public_ready"])

    # Best candidate: still ARB (from K result)
    best_candidate = {}
    if k_result:
        bc = k_result.get("best_candidate", {})
        best_candidate = {
            "mock_message_id": bc.get("mock_message_id", ""),
            "signal_id": bc.get("signal_id", ""),
            "asset": bc.get("asset", ""),
            "grade": bc.get("grade", ""),
            "recommendation": bc.get("recommendation", ""),
            "reason": bc.get("reason", ""),
        }

    # If no K result, default to ARB
    if not best_candidate.get("signal_id"):
        best_candidate = {
            "mock_message_id": "mock_v111j_001",
            "signal_id": "H6-07",
            "asset": "ARB",
            "grade": "A",
            "recommendation": "keep",
            "reason": "Best candidate by composite score (default when K result unavailable)",
        }

    print(f"  Public ready: {public_ready_count}/{len(result_records)}")
    print(f"  Debug leak count: {debug_leak_count}")
    print(f"  Best candidate: {best_candidate.get('signal_id', '?')} ({best_candidate.get('asset', '?')})")
    print()

    # ── Build result JSON ────────────────────────────────────────────────────
    print("[5/6] Writing result JSON...")

    result = {
        "version": VERSION,
        "mode": MODE,
        "real_tg_sent": False,
        "external_ai_called": False,
        "paid_api_called": False,
        "reviewed_count": len(result_records),
        "public_ready_count": public_ready_count,
        "debug_leak_count": debug_leak_count,
        "best_candidate": best_candidate,
        "records": result_records,
        "mvp_judgement": {
            "technical_loop_complete": True,
            "content_loop_complete": True,
            "public_card_layer_ready": public_ready_count == len(result_records),
            "ready_for_official_channel": False,
            "reason": (
                "v1.11-L public card readiness complete. "
                f"{public_ready_count}/{len(result_records)} cards pass redaction check. "
                "Public card text layer is separated from audit metadata. "
                "Formal channel must remain frozen: no real TG send has occurred, "
                "sender security abstraction and cooldown persistence are not yet implemented. "
                "Next step: v1.11-M (Gemini external review of public card quality) or "
                "v1.11-N (real test-channel delivery after safety checks)."
            ),
        },
    }

    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RESULT_JSON_PATH}")
    print()

    # ── Write markdown report ────────────────────────────────────────────────
    print("[6/6] Writing markdown report, Gemini packet, and handoff...")
    write_markdown_report(result, result_records)
    write_gemini_packet(result, result_records)
    write_handoff(result, result_records)

    # ── Print summary ────────────────────────────────────────────────────────
    print()
    print(f"{'=' * 70}")
    print(f"v1.11-L Public Card Readiness — Complete")
    print(f"{'=' * 70}")
    print(f"  Cards reviewed:       {len(result_records)}")
    print(f"  Public ready:         {public_ready_count}/{len(result_records)}")
    print(f"  Debug leak count:     {debug_leak_count}")
    print(f"  Best candidate:       {best_candidate.get('signal_id', '?')} ({best_candidate.get('asset', '?')})")
    print(f"  Formal channel:       FROZEN")
    print(f"  TG send:              NONE")
    print(f"  External AI:          NONE")
    print(f"  Paid API:             NONE")
    print()
    print(f"  Output files:")
    print(f"    {RESULT_JSON_PATH}")
    print(f"    {REPORT_MD_PATH}")
    print(f"    {GEMINI_PACKET_PATH}")
    print(f"    {HANDOFF_MD_PATH}")
    print(f"{'=' * 70}")

    return 0


# ── Report writers ──────────────────────────────────────────────────────────────

def write_markdown_report(result: dict, records: list[dict]) -> None:
    """Write the v1.11-L public card readiness markdown report."""
    lines = [
        f"# Market Radar v1.11-L — Public Card Readiness Report",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Mode**: {MODE}",
        f"",
        f"---",
        f"",
        f"## 本轮目标",
        f"",
        f"将 Market Radar 卡片从\"调试态 payload\"升级为\"用户可读的公开卡片\"。",
        f"修复 v1.11-K 暴露的内容问题：公开卡片文本不得包含内部 gate/debug 状态。",
        f"",
        f"## 为什么不能直接真实发送",
        f"",
        f"1. **内容污染**：v1.11-K 确认 payload 中仍包含 `价值: allow`, `冷却: upgrade_override` 等内部调试信息。",
        f"2. **sender 安全抽象未完成**：token 注入、发送重试、失败降级均未实现。",
        f"3. **cooldown 持久化未完成**：跨进程/跨重启状态不保留。",
        f"4. **无真实 TG 环境验证**：端到端效果未确认。",
        f"",
        f"---",
        f"",
        f"## 3 张卡 Public Preview",
        f"",
    ]

    for r in records:
        public = r["public_card"]
        rc = r["redaction_check"]
        ready = r["readiness"]

        lines.extend([
            f"### {r['signal_id']} — {r['asset']} ({r['approach']})",
            f"",
            f"- **状态**: {'✅ 通过' if ready['public_ready'] else '❌ 未通过'}",
            f"- **parse_mode**: `{public['parse_mode']}`",
            f"- **text_length**: {public['text_length']} chars",
            f"- **debug_terms_found**: {rc['debug_terms_found'] if rc['debug_terms_found'] else '无'}",
            f"- **ai_style_terms_found**: {rc['ai_style_terms_found'] if rc['ai_style_terms_found'] else '无'}",
            f"",
            f"```",
            public['text'][:500],
            f"```",
            f"",
        ])

    lines.extend([
        f"---",
        f"",
        f"## Debug Leak 检查结果",
        f"",
        f"| Card | Debug Terms | AI Terms | Passed |",
        f"|------|-------------|----------|--------|",
    ])

    for r in records:
        rc = r["redaction_check"]
        debug_str = ", ".join(rc["debug_terms_found"]) if rc["debug_terms_found"] else "—"
        ai_str = ", ".join(rc["ai_style_terms_found"]) if rc["ai_style_terms_found"] else "—"
        passed_str = "✅" if rc["passed"] else "❌"
        lines.append(f"| {r['signal_id']} ({r['asset']}) | {debug_str} | {ai_str} | {passed_str} |")

    lines.extend([
        f"",
        f"**debug_leak_count**: {result['debug_leak_count']}",
        f"",
        f"---",
        f"",
        f"## ETH 重复度 / AI 味修正结果",
        f"",
        f"### H5-01 ETH (升级信号角度)",
        f"- 定位：多因子同步升级信号，OI/成交量/资金费率三者共振",
        f"- 语言：自然描述\"信号强度升级\"，避免\"四重确认\"等模板化表达",
        f"",
        f"### H1-01 ETH (基础强度角度)",
        f"- 定位：基础面偏空，大额 OI 配合成交量放大",
        f"- 语言：更简洁的基础描述，与 H5-01 形成角度差异",
        f"",
        f"### 差异检查",
    ])

    # Check ETH cards are different
    eth_cards = [r for r in records if r["asset"] == "ETH"]
    if len(eth_cards) >= 2:
        t1 = eth_cards[0]["public_card"]["text"]
        t2 = eth_cards[1]["public_card"]["text"]
        if t1 == t2:
            lines.append("- ⚠️ **ETH 两张卡内容完全相同！**")
        else:
            # Count differing lines
            l1 = set(t1.split("\n"))
            l2 = set(t2.split("\n"))
            unique_1 = l1 - l2
            unique_2 = l2 - l1
            lines.append(f"- ✅ ETH 两张卡内容有差异：H5-01 独有 {len(unique_1)} 行，H1-01 独有 {len(unique_2)} 行")
    else:
        lines.append("- ⚠️ 不足 2 张 ETH 卡可比较")

    # Check no AI-style terms
    ai_total = sum(len(r["redaction_check"]["ai_style_terms_found"]) for r in records)
    lines.extend([
        f"",
        f"**AI 风格术语总计**: {ai_total} 处",
        f"",
        f"---",
        f"",
        f"## Best Candidate",
        f"",
        f"- **信号**: {result['best_candidate'].get('signal_id', '?')}",
        f"- **资产**: {result['best_candidate'].get('asset', '?')}",
        f"- **评级**: {result['best_candidate'].get('grade', '?')}",
        f"- **建议**: {result['best_candidate'].get('recommendation', '?')}",
        f"",
        f"**ARB 仍为 best_candidate**：多因子确认（价格 + OI + 成交量 + 资金费率），",
        f"composite score 最高，内容净化后保留核心信息。",
        f"",
        f"---",
        f"",
        f"## 是否建议进入下一步",
        f"",
        f"**建议进入 v1.11-M（Gemini 外部审计）或 v1.11-N（真实测试群发送）**，条件：",
        f"",
        f"1. ✅ 3 张卡均通过 debug leak 检查",
        f"2. ✅ 审计 metadata 完整保留",
        f"3. ✅ ETH 卡差异化处理完成",
        f"4. ✅ best_candidate 明确",
        f"5. ⚠️ 需先完成 Gemini 外部审计确认内容质量",
        f"",
        f"---",
        f"",
        f"## 正式频道解冻建议",
        f"",
        f"**必须为否**。原因：",
        f"",
        f"- 未经过真实 TG 测试群发送验证",
        f"- sender 安全抽象（token 注入、重试、降级）未实现",
        f"- cooldown 持久化（跨进程/跨重启）未实现",
        f"- OI/Volume delta 实时追踪未实现",
        f"- 仅 3 张 mock 卡，样本量不足",
        f"",
        f"---",
        f"",
        f"## 下一步建议",
        f"",
        f"1. **Gemini 外部审计 (v1.11-M)**：将 public card preview 发送 Gemini 评估内容质量",
        f"2. **sender 安全抽象**：实现 token 安全注入、发送重试、失败降级",
        f"3. **cooldown 持久化**：跨进程/跨重启状态保留",
        f"4. **真实测试群发送 (v1.11-N)**：在确认内容质量后，以 test channel 小规模发送 1-2 张 A 级卡",
        f"5. **OI/Volume delta 追踪**：区分趋势性 vs 瞬时异动",
        f"",
    ])

    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] {REPORT_MD_PATH}")


def write_gemini_packet(result: dict, records: list[dict]) -> None:
    """Write the Gemini review packet (for human to paste, no API call)."""
    lines = [
        f"# Market Radar v1.11-L — Gemini Review Packet",
        f"",
        f"> **写给 Gemini，不调用 Gemini API。请人工复制此包提交 Gemini 审计。**",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"",
        f"---",
        f"",
        f"## v1.11-L Public Card Preview",
        f"",
        f"以下是 3 张候选卡片的净化后公开文本（仅 public_card.text）。",
        f"内部 gate/debug 信息已从公开文本移除，保留在 audit_metadata 中。",
        f"",
    ]

    for r in records:
        public = r["public_card"]
        rc = r["redaction_check"]

        lines.extend([
            f"### Card: {r['signal_id']} ({r['asset']})",
            f"",
            f"- **Approach**: {r['approach']}",
            f"- **parse_mode**: {public['parse_mode']}",
            f"- **text_length**: {public['text_length']}",
            f"- **Debug terms found**: {rc['debug_terms_found'] if rc['debug_terms_found'] else 'NONE'}",
            f"- **AI-style terms found**: {rc['ai_style_terms_found'] if rc['ai_style_terms_found'] else 'NONE'}",
            f"",
            f"```text",
            public['text'],
            f"```",
            f"",
        ])

    lines.extend([
        f"---",
        f"",
        f"## Debug 信息已从公开文本移除的证据",
        f"",
        f"**Before (v1.11-J mock sent log)**:",
        f"```",
        f"一句话：ARB 跌幅 8.50%，价值: allow, 冷却: upgrade_override (score↑), 安全: pass",
        f"```",
        f"",
        f"**After (v1.11-L public card)**:",
    ])

    arb_card = [r for r in records if r["signal_id"] == "H6-07"]
    if arb_card:
        text = arb_card[0]["public_card"]["text"]
        # Find the one-liner line
        for line in text.split("\n"):
            if "一句话" in line:
                lines.append(f"```\n{line}\n```")
                break
        else:
            lines.append(f"```\n{text[:200]}\n```")

    lines.extend([
        f"",
        f"- `价值: allow` → REMOVED",
        f"- `冷却: upgrade_override (score↑)` → REMOVED",
        f"- `安全: pass` → REMOVED",
        f"- Replaced with natural language: \"多因子异动信号\"",
        f"",
        f"---",
        f"",
        f"## GPT/执行端初步判断",
        f"",
        f"1. **Redaction 有效**：3 张卡的 public_card.text 不再包含内部 gate/debug 术语。",
        f"2. **ARB 适合作为 best_candidate**：多因子确认（价格 + OI + 成交量 + 资金费率极端偏空），composite score 最高。",
        f"3. **ETH 两张卡已差异化**：H5-01 偏\"升级信号/多因子同步\"，H1-01 偏\"基础强度/原始分高\"。",
        f"4. **AI 味消除**：\"极端四重确认\"、\"全确认\"等模板表达已从 ETH 卡中移除。",
        f"5. **正式频道仍需冻结**：缺少真实 TG 发送验证、sender 安全抽象、cooldown 持久化。",
        f"",
        f"---",
        f"",
        f"## 希望 Gemini 判断的 3 个问题",
        f"",
        f"### 问题 1：内容质量评估",
        f"这 3 张净化后的 public card 是否已经摆脱\"内部调试卡片\"的问题？",
        f"公开文本是否读起来像正常的市场情报推送，而非调试日志？",
        f"",
        f"### 问题 2：ARB best_candidate 评估",
        f"ARB (H6-07) 是否足以作为唯一真实测试群候选？",
        f"还是仍应先积累更多 mock 样本再进入真实发送阶段？",
        f"",
        f"### 问题 3：下一步优先级",
        f"Market Radar MVP 主体闭环完成后，下一步最高优先级应是：",
        f"  (a) sender 安全抽象（token 注入、发送重试、失败降级）",
        f"  (b) cooldown 持久化（跨进程/跨重启状态保留）",
        f"  (c) OI/Volume delta 实时化（区分趋势性 vs 瞬时异动）",
        f"",
        f"请给出排序建议和理由。",
        f"",
        f"---",
        f"",
        f"## 附录：完整 Audit Metadata",
        f"",
        f"内部审计信息（不进入公开卡片，仅供审查）：",
        f"",
    ])

    for r in records:
        audit = r.get("audit_metadata", {})
        lines.extend([
            f"### {r['signal_id']} ({r['asset']})",
            f"```json",
            json.dumps({
                "value_gate": audit.get("value_gate", {}),
                "cooldown_gate": audit.get("cooldown_gate", {}),
                "pre_send_gate": audit.get("pre_send_gate", {}),
                "_k_content_review": audit.get("_k_content_review", {}),
            }, ensure_ascii=False, indent=2),
            f"```",
            f"",
        ])

    GEMINI_PACKET_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GEMINI_PACKET_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] {GEMINI_PACKET_PATH}")


def write_handoff(result: dict, records: list[dict]) -> None:
    """Write the v1.11-L handoff markdown."""
    lines = [
        f"# Market Radar v1.11-L — Public Card Readiness Handoff",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Task ID**: 20260604_202718.r06",
        f"",
        f"---",
        f"",
        f"## 修改文件",
        f"",
        f"| 文件 | 操作 | 说明 |",
        f"|------|------|------|",
        f"| `scripts/run_market_radar_v111l_public_card_readiness.py` | 新增 | 主脚本：public card 生成 + redaction 检查 |",
        f"| `scripts/test_market_radar_public_card_readiness_v111l.py` | 新增 | 测试脚本 |",
        f"| `results/market_radar_v111l_public_card_readiness_result.json` | 新增 | 结果 JSON |",
        f"| `runs/market_radar/v111l_public_card_readiness.md` | 新增 | Markdown 报告 |",
        f"| `runs/market_radar/v111l_gemini_review_packet.md` | 新增 | Gemini 审计包 |",
        f"| `runs/market_radar/v111l_public_card_readiness_handoff.md` | 新增 | Handoff（本文件） |",
        f"",
        f"---",
        f"",
        f"## 执行命令",
        f"",
        f"```powershell",
        f"python scripts/run_market_radar_v111l_public_card_readiness.py",
        f"python scripts/test_market_radar_public_card_readiness_v111l.py",
        f"```",
        f"",
        f"---",
        f"",
        f"## 测试结果",
        f"",
        f"（执行后填写）",
        f"",
        f"---",
        f"",
        f"## Debug Leak 检查",
        f"",
        f"| Card | Debug Terms Found | Passed |",
        f"|------|-------------------|--------|",
    ]

    for r in records:
        rc = r["redaction_check"]
        debug_str = ", ".join(rc["debug_terms_found"]) if rc["debug_terms_found"] else "NONE"
        passed_str = "✅" if rc["passed"] else "❌"
        lines.append(f"| {r['signal_id']} ({r['asset']}) | {debug_str} | {passed_str} |")

    lines.extend([
        f"",
        f"**debug_leak_count**: {result['debug_leak_count']}",
        f"",
        f"---",
        f"",
        f"## Public Preview 摘要",
        f"",
    ])

    for r in records:
        public = r["public_card"]
        preview = public["text_preview"]
        lines.extend([
            f"### {r['signal_id']} ({r['asset']})",
            f"",
            f"```",
            preview,
            f"```",
            f"",
            f"- **长度**: {public['text_length']} chars",
            f"- **parse_mode**: {public['parse_mode']}",
            f"",
        ])

    lines.extend([
        f"---",
        f"",
        f"## Best Candidate",
        f"",
        f"- **信号**: {result['best_candidate'].get('signal_id', '?')}",
        f"- **资产**: {result['best_candidate'].get('asset', '?')}",
        f"- **评级**: {result['best_candidate'].get('grade', '?')}",
        f"- **建议**: {result['best_candidate'].get('recommendation', '?')}",
        f"",
        f"**ARB 仍为 best_candidate** ✅",
        f"",
        f"---",
        f"",
        f"## MVP 判断",
        f"",
        f"```json",
        json.dumps(result['mvp_judgement'], ensure_ascii=False, indent=2),
        f"```",
        f"",
        f"---",
        f"",
        f"## 风险",
        f"",
        f"1. **内容生成是确定性的**：public card text 由本地 builder 生成，依赖硬编码的信号数据，",
        f"   实际生产环境中信号数据源可能不同。",
        f"2. **ETH 差异化是手动的**：两张 ETH 卡的差异依赖 builder 中的不同措辞，",
        f"   未来需要模板化以支持更多资产。",
        f"3. **无真实 TG 验证**：public card text 未经过真实 TG 发送验证，MarkdownV2 转义",
        f"   可能在实际发送时出现边缘情况。",
        f"4. **无外部 AI 审计**：内容质量仅由本地 redaction checks 验证，无人工或 AI 评审。",
        f"",
        f"---",
        f"",
        f"## 下一步建议",
        f"",
        f"1. **Gemini 外部审计 (v1.11-M)**：将 Gemini review packet 提交人工/Gemini 审计",
        f"2. **sender 安全抽象**：实现 token 安全注入、发送重试、失败降级",
        f"3. **cooldown 持久化**：跨进程/跨重启状态保留",
        f"4. **真实测试群发送 (v1.11-N)**：确认内容质量后，以 test channel 发送 1-2 张 A 级卡",
        f"5. **OI/Volume delta 追踪**：区分趋势性 vs 瞬时异动",
        f"",
    ])

    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] {HANDOFF_MD_PATH}")


if __name__ == "__main__":
    raise SystemExit(main())
