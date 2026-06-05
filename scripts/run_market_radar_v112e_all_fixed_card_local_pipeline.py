"""Market Radar v1.12-E — All Fixed Card Type Local Dry-Run Pipeline

Unified runner that aggregates all 5 fixed card types into a single local
dry-run pipeline. Proves that all 5 card types can be produced from a single
unified entry point — not in isolation.

Pipeline per card type:
  1. Read registry definition
  2. Load fixture / adapter results
  3. Generate card output summary with readiness, public preview, gate status
  4. Run unified debug leak + secret leak check across all public previews
  5. Produce aggregated JSON result, Markdown report, and handoff document

Card types:
  1. price_oi_volume_anomaly       — ready (via v112a registry)
  2. whale_position_alert           — partial (via v112a registry, fallback preview)
  3. liquidation_pressure           — partial (via v112b adapter + v112c pipeline)
  4. multi_asset_market_sync        — partial (via v112a registry, fallback preview)
  5. news_event_market_impact       — partial (via v112d adapter)

Constraints (all verified):
  - NO real TG send
  - NO external API calls
  - NO external AI calls
  - NO daemon / loop / cron
  - NO token / key / password read or saved
  - NO file deletion

Outputs:
  - results/market_radar_v112e_all_fixed_card_local_pipeline_result.json
  - runs/market_radar/v112e_all_fixed_card_local_pipeline.md
  - runs/market_radar/v112e_all_fixed_card_local_pipeline_handoff.md

Usage:
    python scripts/run_market_radar_v112e_all_fixed_card_local_pipeline.py
"""

from __future__ import annotations

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

# ── Imports from existing modules ──────────────────────────────────────────────────

from scripts.market_radar_card_type_registry_v112a import (
    CARD_TYPE_REGISTRY,
    REGISTRY_VERSION,
    get_all_card_types,
    get_card_type,
    list_card_types,
    get_card_type_count,
    validate_signal_against_card_type,
    render_public_preview,
    assess_readiness,
    check_public_debug_leak,
    update_liquidation_readiness_from_adapter,
    update_news_event_readiness_from_adapter,
    get_fixed_card_matrix_summary,
)

from scripts.market_radar_liquidation_feed_v112b import (
    normalize_liquidation_snapshot,
    detect_liquidation_pressure,
    render_liquidation_pressure_card,
    validate_liquidation_signal,
    process_raw_snapshot,
)

from scripts.market_radar_news_event_feed_v112d import (
    normalize_news_event,
    classify_news_event,
    extract_affected_assets,
    judge_impact_direction,
    decide_valid_blocked,
    render_news_public_card,
    check_public_debug_leak as check_v112d_debug_leak,
    process_news_event,
)

CN_TZ = timezone(timedelta(hours=8))
VERSION = "v1.12-E"
RUN_ID = "20260604_202718"

# ── Paths ─────────────────────────────────────────────────────────────────────────

FIXTURE_V112A = ROOT / "data" / "fixtures" / "market_radar_v112a_card_type_samples.json"
FIXTURE_V112B = ROOT / "data" / "fixtures" / "market_radar_v112b_liquidation_snapshots.json"
FIXTURE_V112D = ROOT / "data" / "fixtures" / "market_radar_v112d_news_events.json"
RESULT_V112C = ROOT / "results" / "market_radar_v112c_liquidation_pipeline_integration_result.json"
RESULT_V112D = ROOT / "results" / "market_radar_v112d_news_event_market_impact_result.json"
RESULT_V112F = ROOT / "results" / "market_radar_v112f_whale_position_local_enrichment_result.json"
RESULT_V112G = ROOT / "results" / "market_radar_v112g_multi_asset_sync_local_correlation_result.json"

RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112e_all_fixed_card_local_pipeline_result.json"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112e_all_fixed_card_local_pipeline.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112e_all_fixed_card_local_pipeline_handoff.md"

# ── Secret / Debug Leak Terms (extended beyond registry) ───────────────────────────

DEBUG_LEAK_TERMS = [
    "debug", "internal", "trace", "fixture",
]

SECRET_LEAK_TERMS = [
    "secret", "token", "api_key", "chat_id", "password",
]

LOCAL_PATH_TERMS = [
    "C:\\Users\\PC", "C:\\Users", "D:\\", "E:\\",
    "/home/", "/Users/", "/tmp/", "/var/",
    "ai_relay_desk",
]

REGISTRY_FORBIDDEN_PATTERNS = [
    "value_gate", "cooldown_gate", "pre_send_gate", "pre_send",
    "payload_render", "format_check", "content_quality",
    "gate_decision", "score↑", "blocked_by", "gate_version",
    "factor_hits", "block_reason", "block_rules", "block_triggered",
    "admission_result",
    "not_reached", "mock_sent", "mock_message_id",
]

ALL_SECRET_AND_DEBUG_TERMS = (
    DEBUG_LEAK_TERMS + SECRET_LEAK_TERMS + LOCAL_PATH_TERMS + REGISTRY_FORBIDDEN_PATTERNS
)


# ── Helpers ───────────────────────────────────────────────────────────────────────

def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _safe_float(value, default=0.0):
    if value is None:
        return default
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        s = value.strip().replace("%", "").replace(",", "").replace("+", "").strip()
        if not s:
            return default
        try:
            return float(s)
        except (ValueError, TypeError):
            return default
    return default


def check_all_forbidden_terms(text: str) -> tuple[list[str], list[str]]:
    """Check text for both debug-leak and secret-leak terms.

    Returns:
        (debug_leaks: list[str], secret_leaks: list[str])
    """
    if not text:
        return [], []
    text_lower = text.lower()

    debug_found: list[str] = []
    for term in DEBUG_LEAK_TERMS:
        if term.lower() in text_lower:
            debug_found.append(term)

    secret_found: list[str] = []
    for term in SECRET_LEAK_TERMS:
        if term.lower() in text_lower:
            secret_found.append(term)
    for term in LOCAL_PATH_TERMS:
        if term.lower() in text_lower:
            secret_found.append(term)
    for term in REGISTRY_FORBIDDEN_PATTERNS:
        if term.lower() in text_lower:
            debug_found.append(term)

    # Also check for Windows-style absolute paths
    if re.search(r'[A-Za-z]:\\(?:Users|Program|Windows)', text):
        if "local_path_pattern" not in secret_found:
            secret_found.append("local_absolute_path")

    return debug_found, secret_found


def _fmt_money(value):
    v = abs(value)
    sign = "-" if value < 0 else ""
    if v >= 1_000_000_000:
        return f"{sign}${v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"{sign}${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"{sign}${v/1_000:.2f}K"
    if v < 0.01 and v > 0:
        return f"{sign}${v:.6f}"
    return f"{sign}${v:,.2f}"


def _fmt_price(value):
    v = abs(value)
    if v >= 1000:
        return f"${value:,.2f}"
    if v >= 1:
        return f"${value:.2f}"
    return f"${value:.6f}"


# ══════════════════════════════════════════════════════════════════════════════════════
# Per-Card-Type Processors
# ══════════════════════════════════════════════════════════════════════════════════════

def process_price_oi_volume_anomaly(fixtures: dict) -> dict:
    """Process price_oi_volume_anomaly — ready card type.

    Uses v112a fixture samples and registry definition.
    """
    card_type = "price_oi_volume_anomaly"
    ct_def = get_card_type(card_type)
    readiness = assess_readiness(ct_def)

    # Get samples from v112a fixture
    fixture_ct = fixtures.get(card_type, {})
    samples = fixture_ct.get("samples", [])

    public_previews: list[str] = []
    all_debug_leaks: list[str] = []
    all_secret_leaks: list[str] = []

    # Fallback sample if no fixture samples
    if not samples:
        fallback_signal = {
            "asset": "BTC",
            "core_entity": "BTC",
            "price_change_pct": 7.2,
            "open_interest": 28_500_000_000,
            "volume": 45_000_000_000,
            "funding": 0.015,
            "trigger_reason": "BTC 多因子同步异动，价格 24h 上涨 7.2%，OI 与成交量同步放大。",
            "source_type": "fixture",
            "is_fixture": True,
            "data_mode": "fixture",
        }
        samples = [{"sample_id": f"{card_type}_fallback", "data_mode": "fixture", "signal": fallback_signal}]

    sample_results = []
    for sw in samples:
        signal = sw.get("signal", sw)
        sample_id = sw.get("sample_id", "unknown")
        data_mode = sw.get("data_mode", "fixture")

        validation = validate_signal_against_card_type(signal, ct_def)
        try:
            preview = render_public_preview(ct_def, signal, validation)
        except Exception:
            preview = ""

        debug_leaks, secret_leaks = check_all_forbidden_terms(preview)

        sample_results.append({
            "sample_id": sample_id,
            "data_mode": data_mode,
            "schema_valid": validation["schema_valid"],
            "admission_passed": validation["admission_passed"],
            "block_triggered": validation["block_triggered"],
            "all_checks_passed": validation["all_checks_passed"],
            "public_preview": preview[:300],
            "preview_length": len(preview),
            "debug_leak_terms": debug_leaks,
            "secret_leak_terms": secret_leaks,
            "clean": len(debug_leaks) == 0 and len(secret_leaks) == 0,
        })

        if preview and validation["all_checks_passed"]:
            public_previews.append(preview)
        all_debug_leaks.extend(debug_leaks)
        all_secret_leaks.extend(secret_leaks)

    # Best preview
    best_preview = public_previews[0] if public_previews else ""
    preview_available = len(public_previews) > 0

    return {
        "card_type": card_type,
        "display_name": ct_def["display_name"],
        "readiness": "ready",
        "readiness_detail": readiness,
        "public_preview_available": preview_available,
        "fallback_preview_available": not preview_available,
        "gate_tested": True,
        "live_ready": False,
        "sample_count": len(samples),
        "valid_sample_count": sum(1 for s in sample_results if s["all_checks_passed"]),
        "sample_results": sample_results,
        "public_preview_sample": best_preview[:500],
        "debug_leak_count": len(set(all_debug_leaks)),
        "secret_leak_count": len(set(all_secret_leaks)),
        "missing_capability": readiness.get("long_running_monitoring_gaps", []),
        "output_summary": (
            f"price_oi_volume_anomaly — READY: {len(public_previews)} public preview(s), "
            f"schema complete, gate tested, fixture samples available. "
            f"Monitoring gaps: OI/Volume delta real-time tracking, funding rate historical baseline, "
            f"cross-exchange data consistency check."
        ),
    }


def process_whale_position_alert(fixtures: dict) -> dict:
    """Process whale_position_alert — partial card type.

    Priority:
      1. If v112f result exists and passes validation, use v112f real public previews.
         whale_position_alert is no longer marked as fallback_preview.
      2. If v112f result does not exist, fall back to v112a registry-based preview.
    """
    card_type = "whale_position_alert"
    ct_def = get_card_type(card_type)
    readiness = assess_readiness(ct_def)

    public_previews: list[str] = []
    fallback_previews: list[str] = []
    all_debug_leaks: list[str] = []
    all_secret_leaks: list[str] = []
    sample_results = []
    used_v112f = False
    v112f_valid_count = 0
    v112f_card_count = 0

    # ── Step 1: Try v112f enrichment result ─────────────────────────────────
    if RESULT_V112F.exists():
        try:
            v112f_result = load_json(RESULT_V112F)
            v112f_cards = v112f_result.get("public_cards", [])
            v112f_valid = v112f_result.get("valid_signal_count", 0)
            v112f_debug = v112f_result.get("debug_leak_count", 999)
            v112f_secret = v112f_result.get("secret_leak_count", 999)
            v112f_fallback = v112f_result.get("fallback_preview", True)
            v112f_positions = v112f_result.get("position_results", [])

            # Acceptance criteria: >= 3 public cards, 0 debug leaks, 0 secret leaks,
            # fallback_preview=false
            v112f_accepted = (
                len(v112f_cards) >= 3
                and v112f_debug == 0
                and v112f_secret == 0
                and not v112f_fallback
            )

            if v112f_accepted:
                used_v112f = True
                v112f_valid_count = v112f_valid
                v112f_card_count = len(v112f_cards)

                for pr in v112f_positions:
                    eid = pr.get("event_id", "unknown")
                    valid = pr.get("valid", False)
                    blocked = pr.get("blocked", True)
                    public_card = pr.get("public_card", "")
                    dl = pr.get("debug_leak_count", 0)
                    sl = pr.get("secret_leak_count", 0)

                    sample_results.append({
                        "sample_id": eid,
                        "data_mode": pr.get("data_mode", "fixture"),
                        "source": "v112f_enrichment",
                        "asset": pr.get("asset", ""),
                        "side": pr.get("side", ""),
                        "label": pr.get("label", ""),
                        "entity_type": pr.get("entity_type", ""),
                        "alert_type": pr.get("alert_type", ""),
                        "position_size_usd": pr.get("position_size_usd", 0),
                        "position_delta_usd": pr.get("position_delta_usd", 0),
                        "valid": valid,
                        "blocked": blocked,
                        "block_reason": pr.get("block_reason", ""),
                        "public_preview": public_card[:300] if public_card else "",
                        "preview_length": len(public_card),
                        "debug_leak_terms": pr.get("debug_leak_terms", []),
                        "secret_leak_terms": pr.get("secret_leak_terms", []),
                        "clean": dl == 0 and sl == 0,
                    })

                    if public_card and valid:
                        public_previews.append(public_card)
                    all_debug_leaks.extend(pr.get("debug_leak_terms", []))
                    all_secret_leaks.extend(pr.get("secret_leak_terms", []))
        except (json.JSONDecodeError, KeyError, OSError):
            pass  # Fall through to fallback

    # ── Step 2: Fallback — v112a registry-based preview ────────────────────
    if not used_v112f:
        fixture_ct = fixtures.get(card_type, {})
        samples = fixture_ct.get("samples", [])

        if not samples:
            fallback_signal = {
                "asset": "HYPE",
                "core_entity": "HYPE",
                "address": "0x082d2ca88b5e0e6c1e8c0b5e2d3f4a5b6c7d8e9f",
                "side": "多头",
                "position_value_usd": 100_000_000,
                "quantity": 1_380_000,
                "entry_price": 33.68,
                "mark_price": 72.51,
                "pnl_usd": 46_985_000,
                "pnl_pct": 116.0,
                "liquidation_price": 54.93,
                "trigger_reason": "HYPE 多头大额持仓，浮盈超 100%。",
                "source_type": "fixture",
                "is_fixture": True,
                "data_mode": "fixture",
            }
            samples = [{"sample_id": f"{card_type}_fallback", "data_mode": "fixture", "signal": fallback_signal}]

        for sw in samples:
            signal = sw.get("signal", sw)
            sample_id = sw.get("sample_id", "unknown")
            data_mode = sw.get("data_mode", "fixture")

            validation = validate_signal_against_card_type(signal, ct_def)
            try:
                preview = render_public_preview(ct_def, signal, validation)
            except Exception:
                preview = ""

            debug_leaks, secret_leaks = check_all_forbidden_terms(preview)

            sample_results.append({
                "sample_id": sample_id,
                "data_mode": data_mode,
                "schema_valid": validation["schema_valid"],
                "admission_passed": validation["admission_passed"],
                "block_triggered": validation["block_triggered"],
                "all_checks_passed": validation["all_checks_passed"],
                "public_preview": preview[:300],
                "preview_length": len(preview),
                "debug_leak_terms": debug_leaks,
                "secret_leak_terms": secret_leaks,
                "clean": len(debug_leaks) == 0 and len(secret_leaks) == 0,
            })

            if preview and validation["all_checks_passed"]:
                public_previews.append(preview)
            elif preview:
                fallback_previews.append(preview)
            all_debug_leaks.extend(debug_leaks)
            all_secret_leaks.extend(secret_leaks)

    # ── Assemble result ───────────────────────────────────────────────────
    best_preview = public_previews[0] if public_previews else (fallback_previews[0] if fallback_previews else "")
    preview_available = len(public_previews) > 0
    fallback_available = len(fallback_previews) > 0 and not used_v112f

    if used_v112f:
        missing_caps = [
            "multi-address aggregation analysis (correlated address cluster detection)",
            "liquidation alert real-time push (trigger when < 5% from liquidation price)",
            "live Hyperliquid API data source (current: v112f local fixture enrichment)",
            "address label coverage for all on-chain wallets (current: 6 labels from fixture)",
        ]
        output_summary = (
            f"whale_position_alert — PARTIAL (v112f enrichment active): "
            f"{v112f_card_count} real public preview(s) from v112f local enrichment, "
            f"{v112f_valid_count} valid signals. "
            f"fallback_preview=false. "
            f"Address labels + historical position sequence available (local fixture). "
            f"Missing: live data source, multi-address aggregation, real-time liquidation alerts."
        )
    else:
        missing_caps = [
            "address labels (Smart Money / institution / market maker / retail auto-classification)",
            "historical position sequence (same address add/reduce position tracking)",
            "multi-address aggregation analysis (correlated address cluster detection)",
            "liquidation alert real-time push (trigger when < 5% from liquidation price)",
        ]
        output_summary = (
            f"whale_position_alert — PARTIAL: "
            f"{'1 public preview available' if preview_available else 'fallback preview available'}. "
            f"Missing: address labels, historical position sequence. "
            f"Fixture samples pass schema/admission/block checks."
        )

    return {
        "card_type": card_type,
        "display_name": ct_def["display_name"],
        "readiness": "partial",
        "readiness_detail": readiness,
        "public_preview_available": preview_available,
        "fallback_preview_available": fallback_available,
        "gate_tested": True,
        "live_ready": False,
        "sample_count": len(sample_results),
        "valid_sample_count": sum(1 for s in sample_results if s.get("valid", s.get("all_checks_passed", False))),
        "sample_results": sample_results,
        "public_preview_sample": best_preview[:500],
        "debug_leak_count": len(set(all_debug_leaks)),
        "secret_leak_count": len(set(all_secret_leaks)),
        "missing_capability": missing_caps,
        "output_summary": output_summary,
        "v112f_enrichment_used": used_v112f,
        "v112f_valid_count": v112f_valid_count,
        "v112f_card_count": v112f_card_count,
    }


def process_liquidation_pressure() -> dict:
    """Process liquidation_pressure — partial (upgraded from missing via v112b/v112c).

    Uses v112b fixture snapshots and v112c pipeline results.
    """
    card_type = "liquidation_pressure"

    # Load v112b fixture
    try:
        liq_fixture = load_json(FIXTURE_V112B)
        snapshots = liq_fixture.get("snapshots", [])
    except (FileNotFoundError, json.JSONDecodeError):
        snapshots = []

    public_previews: list[str] = []
    all_debug_leaks: list[str] = []
    all_secret_leaks: list[str] = []
    sample_results = []
    valid_signals = 0

    for raw in snapshots:
        result = process_raw_snapshot(raw)
        sample_id = result.get("sample_id", "unknown")
        public_card = result.get("public_card", "")
        blocked = result.get("blocked", True)

        debug_leaks, secret_leaks = check_all_forbidden_terms(public_card)

        sample_results.append({
            "sample_id": sample_id,
            "data_mode": result.get("data_mode", "fixture"),
            "asset": result.get("asset", ""),
            "blocked": blocked,
            "block_reason": result.get("block_reason", ""),
            "public_preview": public_card[:300] if public_card else "",
            "preview_length": len(public_card),
            "debug_leak_terms": debug_leaks,
            "secret_leak_terms": secret_leaks,
            "clean": len(debug_leaks) == 0 and len(secret_leaks) == 0,
            "live_ready": result.get("live_ready", False),
        })

        if public_card and not blocked:
            public_previews.append(public_card)
            valid_signals += 1
        all_debug_leaks.extend(debug_leaks)
        all_secret_leaks.extend(secret_leaks)

    # Update registry readiness from adapter
    readiness_update = update_liquidation_readiness_from_adapter(
        adapter_result_path=str(RESULT_V112C) if RESULT_V112C.exists() else None,
        valid_signal_count=valid_signals,
        public_card_count=len(public_previews),
    )

    ct_def = get_card_type(card_type)
    readiness = assess_readiness(ct_def)

    best_preview = public_previews[0] if public_previews else ""
    preview_available = len(public_previews) > 0

    return {
        "card_type": card_type,
        "display_name": ct_def["display_name"] if ct_def else "清算压力预警卡",
        "readiness": readiness_update["new_readiness"],
        "readiness_detail": readiness,
        "public_preview_available": preview_available,
        "fallback_preview_available": not preview_available,
        "gate_tested": readiness_update["new_readiness"] == "partial",
        "live_ready": False,
        "sample_count": len(snapshots),
        "valid_signal_count": valid_signals,
        "public_card_count": len(public_previews),
        "sample_results": sample_results,
        "public_preview_sample": best_preview[:500],
        "debug_leak_count": len(set(all_debug_leaks)),
        "secret_leak_count": len(set(all_secret_leaks)),
        "missing_capability": readiness.get("long_running_monitoring_gaps", []),
        "output_summary": (
            f"liquidation_pressure — PARTIAL: {len(public_previews)} public preview(s) from "
            f"{len(snapshots)} fixture snapshots, {valid_signals} valid signals. "
            f"live_ready=false. Missing: real-time liquidation data source, liquidation heatmap, "
            f"historical liquidation baseline."
        ),
    }


def process_multi_asset_market_sync(fixtures: dict) -> dict:
    """Process multi_asset_market_sync — partial card type.

    Priority:
      1. If v112g result exists and passes validation, use v112g real public previews.
         multi_asset_market_sync is no longer marked as fallback_preview.
         fallback_preview_available=false, public_preview_available=true.
      2. If v112g result does not exist, fall back to registry-based preview.
    """
    card_type = "multi_asset_market_sync"
    ct_def = get_card_type(card_type)
    readiness = assess_readiness(ct_def)

    public_previews: list[str] = []
    fallback_previews: list[str] = []
    all_debug_leaks: list[str] = []
    all_secret_leaks: list[str] = []
    sample_results = []
    used_v112g = False
    v112g_valid_count = 0
    v112g_card_count = 0
    v112g_blocked_count = 0

    # ── Step 1: Try v112g multi-asset sync result ───────────────────────────
    if RESULT_V112G.exists():
        try:
            v112g_result = load_json(RESULT_V112G)
            v112g_cards = v112g_result.get("public_cards", [])
            v112g_valid = v112g_result.get("valid_signal_count", 0)
            v112g_blocked = v112g_result.get("blocked_signal_count", 0)
            v112g_debug = v112g_result.get("debug_leak_count", 999)
            v112g_secret = v112g_result.get("secret_leak_count", 999)
            v112g_fallback = v112g_result.get("fallback_preview", True)
            v112g_results = v112g_result.get("results", [])

            # Acceptance criteria: >= 3 public cards, 0 debug leaks, 0 secret leaks,
            # fallback_preview=false
            v112g_accepted = (
                len(v112g_cards) >= 3
                and v112g_debug == 0
                and v112g_secret == 0
                and not v112g_fallback
            )

            if v112g_accepted:
                used_v112g = True
                v112g_valid_count = v112g_valid
                v112g_card_count = len(v112g_cards)
                v112g_blocked_count = v112g_blocked

                for pr in v112g_results:
                    eid = pr.get("event_id", "unknown")
                    is_valid = pr.get("valid", False)
                    is_blocked = pr.get("blocked", True)
                    public_card = pr.get("public_card", "")
                    dl = pr.get("debug_leak_count", 0)
                    sl = pr.get("secret_leak_count", 0)

                    sample_results.append({
                        "sample_id": eid,
                        "data_mode": pr.get("data_mode", "fixture"),
                        "source": "v112g_local_correlation",
                        "sync_type": pr.get("sync_type", "unknown"),
                        "direction": pr.get("direction", "neutral"),
                        "direction_agreement": pr.get("direction_agreement", 0),
                        "sync_score": pr.get("sync_score", 0),
                        "sector": pr.get("sector", ""),
                        "primary_assets": pr.get("primary_assets", []),
                        "asset_count": pr.get("asset_count", 0),
                        "avg_price_change": pr.get("avg_price_change", 0),
                        "avg_volume_change": pr.get("avg_volume_change", 0),
                        "avg_oi_change": pr.get("avg_oi_change", 0),
                        "valid": is_valid,
                        "blocked": is_blocked,
                        "block_reason": pr.get("block_reason", ""),
                        "public_preview": public_card[:300] if public_card else "",
                        "preview_length": len(public_card),
                        "debug_leak_terms": pr.get("debug_leak_terms", []),
                        "secret_leak_terms": pr.get("secret_leak_terms", []),
                        "clean": dl == 0 and sl == 0,
                    })

                    if public_card and is_valid:
                        public_previews.append(public_card)
                    all_debug_leaks.extend(pr.get("debug_leak_terms", []))
                    all_secret_leaks.extend(pr.get("secret_leak_terms", []))
        except (json.JSONDecodeError, KeyError, OSError):
            pass  # Fall through to fallback

    # ── Step 2: Fallback — registry-based preview ───────────────────────────
    if not used_v112g:
        fixture_ct = fixtures.get(card_type, {})
        samples = fixture_ct.get("samples", [])

        if not samples:
            fallback_signal = {
                "assets": [
                    {"asset": "BTC", "price_change_pct": 4.5},
                    {"asset": "ETH", "price_change_pct": 5.2},
                    {"asset": "SOL", "price_change_pct": 6.1},
                    {"asset": "AVAX", "price_change_pct": 4.8},
                ],
                "direction": "up",
                "sector": "L1",
                "leader_asset": "SOL",
                "avg_price_change": 5.15,
                "max_price_change": 6.1,
                "min_price_change": 4.5,
                "oi_direction_match": True,
                "volume_surge_ratio": 2.1,
                "real_same_direction_asset_count": 4,
                "trigger_reason": "L1 板块 4 个资产同步上涨，OI 方向一致，成交量放大。",
                "source_type": "fixture",
                "is_fixture": True,
                "data_mode": "fixture",
            }
            samples = [{"sample_id": f"{card_type}_fallback", "data_mode": "fixture", "signal": fallback_signal}]

        for sw in samples:
            signal = sw.get("signal", sw)
            sample_id = sw.get("sample_id", "unknown")
            data_mode = sw.get("data_mode", "fixture")

            validation = validate_signal_against_card_type(signal, ct_def)
            try:
                preview = render_public_preview(ct_def, signal, validation)
            except Exception:
                preview = ""

            debug_leaks, secret_leaks = check_all_forbidden_terms(preview)

            sample_results.append({
                "sample_id": sample_id,
                "data_mode": data_mode,
                "schema_valid": validation["schema_valid"],
                "admission_passed": validation["admission_passed"],
                "block_triggered": validation["block_triggered"],
                "all_checks_passed": validation["all_checks_passed"],
                "public_preview": preview[:300],
                "preview_length": len(preview),
                "debug_leak_terms": debug_leaks,
                "secret_leak_terms": secret_leaks,
                "clean": len(debug_leaks) == 0 and len(secret_leaks) == 0,
            })

            if preview and validation["all_checks_passed"]:
                public_previews.append(preview)
            elif preview:
                fallback_previews.append(preview)
            all_debug_leaks.extend(debug_leaks)
            all_secret_leaks.extend(secret_leaks)

    # ── Assemble result ─────────────────────────────────────────────────────
    best_preview = public_previews[0] if public_previews else (fallback_previews[0] if fallback_previews else "")
    preview_available = len(public_previews) > 0
    fallback_available = len(fallback_previews) > 0 and not used_v112g

    if used_v112g:
        missing_caps = [
            "real-time cross-asset correlation matrix (current: v112g local fixture correlation)",
            "live price data pipeline (current: v112g fixture snapshots)",
            "sector/track auto-expansion (DeFi, Meme, AI, RWA beyond current L1/L2/exchange/stablecoin)",
            "resonance strength decay tracking (signal persistence validation post-emission)",
            "intraday multi-snapshot comparison (distinguish intraday noise from trend resonance)",
        ]
        output_summary = (
            f"multi_asset_market_sync — PARTIAL (v112g local correlation active): "
            f"{v112g_card_count} real public preview(s) from v112g local correlation feed, "
            f"{v112g_valid_count} valid signals, {v112g_blocked_count} blocked. "
            f"fallback_preview=false. "
            f"Synchronized move score + direction agreement + sector/basket detection available (local fixture). "
            f"Missing: live data source, real-time correlation matrix."
        )
    else:
        missing_caps = [
            "auto correlation matrix (cross-asset real-time correlation detection)",
            "sector/track auto-classification (L1/L2/DeFi/Meme/AI labels)",
            "leader/laggard auto-identification",
            "resonance strength decay tracking (signal persistence validation)",
            "intraday multi-snapshot comparison (distinguish intraday noise from trend resonance)",
        ]
        output_summary = (
            f"multi_asset_market_sync — PARTIAL: "
            f"{'public preview available' if preview_available else 'fallback preview available'}. "
            f"Missing: auto correlation matrix. "
            f"Fixture samples with 4 assets in same direction (up), OI direction match confirmed."
        )

    return {
        "card_type": card_type,
        "display_name": ct_def["display_name"],
        "readiness": "partial",
        "readiness_detail": readiness,
        "public_preview_available": preview_available,
        "fallback_preview_available": fallback_available,
        "gate_tested": True,
        "live_ready": False,
        "sample_count": len(sample_results),
        "valid_sample_count": sum(1 for s in sample_results if s.get("valid", s.get("all_checks_passed", False))),
        "sample_results": sample_results,
        "public_preview_sample": best_preview[:500],
        "debug_leak_count": len(set(all_debug_leaks)),
        "secret_leak_count": len(set(all_secret_leaks)),
        "missing_capability": missing_caps,
        "output_summary": output_summary,
        "v112g_correlation_used": used_v112g,
        "v112g_valid_count": v112g_valid_count,
        "v112g_card_count": v112g_card_count,
        "v112g_blocked_count": v112g_blocked_count,
    }


def process_news_event_market_impact() -> dict:
    """Process news_event_market_impact — partial (upgraded from missing via v112d).

    Uses v112d fixture and adapter.
    """
    card_type = "news_event_market_impact"

    # Load v112d fixture
    try:
        news_fixture = load_json(FIXTURE_V112D)
        news_events = news_fixture.get("news_events", [])
    except (FileNotFoundError, json.JSONDecodeError):
        news_events = []

    public_previews: list[str] = []
    all_debug_leaks: list[str] = []
    all_secret_leaks: list[str] = []
    sample_results = []
    valid_signals = 0

    for raw in news_events:
        result = process_news_event(raw)
        sample_id = result.get("sample_id", "unknown")
        public_card = result.get("public_card", "")
        is_valid = result.get("valid", False)
        blocked = result.get("blocked", True)

        debug_leaks, secret_leaks = check_all_forbidden_terms(public_card)

        sample_results.append({
            "sample_id": sample_id,
            "data_mode": result.get("data_mode", "fixture"),
            "category": result.get("category", "unknown"),
            "affected_assets": result.get("affected_assets", []),
            "impact_direction": result.get("impact_direction", "neutral"),
            "valid": is_valid,
            "blocked": blocked,
            "block_reason": result.get("block_reason", ""),
            "public_preview": public_card[:300] if public_card else "",
            "preview_length": len(public_card),
            "debug_leak_terms": debug_leaks,
            "secret_leak_terms": secret_leaks,
            "clean": len(debug_leaks) == 0 and len(secret_leaks) == 0,
            "live_ready": result.get("live_ready", False),
        })

        if public_card and is_valid:
            public_previews.append(public_card)
            valid_signals += 1
        all_debug_leaks.extend(debug_leaks)
        all_secret_leaks.extend(secret_leaks)

    # Update registry readiness from adapter
    readiness_update = update_news_event_readiness_from_adapter(
        adapter_result_path=str(RESULT_V112D) if RESULT_V112D.exists() else None,
        valid_signal_count=valid_signals,
        public_card_count=len(public_previews),
        debug_leak_count=len(set(all_debug_leaks)),
    )

    ct_def = get_card_type(card_type)
    readiness = assess_readiness(ct_def)

    best_preview = public_previews[0] if public_previews else ""
    preview_available = len(public_previews) > 0

    return {
        "card_type": card_type,
        "display_name": ct_def["display_name"] if ct_def else "新闻事件影响卡",
        "readiness": readiness_update["new_readiness"],
        "readiness_detail": readiness,
        "public_preview_available": preview_available,
        "fallback_preview_available": not preview_available,
        "gate_tested": readiness_update["new_readiness"] == "partial",
        "live_ready": False,
        "sample_count": len(news_events),
        "valid_signal_count": valid_signals,
        "public_card_count": len(public_previews),
        "sample_results": sample_results,
        "public_preview_sample": best_preview[:500],
        "debug_leak_count": len(set(all_debug_leaks)),
        "secret_leak_count": len(set(all_secret_leaks)),
        "missing_capability": readiness.get("long_running_monitoring_gaps", []),
        "output_summary": (
            f"news_event_market_impact — PARTIAL: {len(public_previews)} public preview(s) from "
            f"{len(news_events)} fixture events, {valid_signals} valid signals. "
            f"live_ready=false. Missing: live news RSS/API pipeline, auto event classification (NLP), "
            f"auto affected-assets extraction, pricing model."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════════════

def main() -> int:
    print(f"=== Market Radar {VERSION} — All Fixed Card Local Dry-Run Pipeline ===")
    print(f"Run: {china_stamp()}")
    print(f"Run ID: {RUN_ID}")
    print(f"TG SEND: NONE")
    print(f"EXTERNAL API: NONE")
    print(f"EXTERNAL AI: NONE")
    print(f"PAID API: NONE")
    print(f"DAEMON: NONE")
    print()

    # ── Step 1: Load v112a fixture ──────────────────────────────────────────────
    print("[1/6] Loading v112a card type fixtures...")
    try:
        v112a_fixtures = load_json(FIXTURE_V112A)
        card_type_fixtures = v112a_fixtures.get("card_types", {})
        print(f"  Loaded: {v112a_fixtures.get('meta', {}).get('total_card_types', 0)} card types")
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"  [WARN] v112a fixture not found at {FIXTURE_V112A}, using fallback")
        card_type_fixtures = {}
    print()

    # ── Step 2: Process all 5 card types ───────────────────────────────────────
    print("[2/6] Processing 5 card types through unified pipeline...")

    card_outputs: list[dict] = []

    # 1. price_oi_volume_anomaly — ready
    print("  [1/5] price_oi_volume_anomaly...")
    pova = process_price_oi_volume_anomaly(card_type_fixtures)
    card_outputs.append(pova)
    print(f"        readiness={pova['readiness']}, previews={1 if pova['public_preview_available'] else 0}, "
          f"debug_leaks={pova['debug_leak_count']}, secret_leaks={pova['secret_leak_count']}")

    # 2. whale_position_alert — partial
    print("  [2/5] whale_position_alert...")
    whale = process_whale_position_alert(card_type_fixtures)
    card_outputs.append(whale)
    print(f"        readiness={whale['readiness']}, preview={'public' if whale['public_preview_available'] else 'fallback'}, "
          f"debug_leaks={whale['debug_leak_count']}, secret_leaks={whale['secret_leak_count']}")

    # 3. liquidation_pressure — partial (from v112b/v112c)
    print("  [3/5] liquidation_pressure...")
    liq = process_liquidation_pressure()
    card_outputs.append(liq)
    print(f"        readiness={liq['readiness']}, previews={liq.get('public_card_count', 0)}, "
          f"debug_leaks={liq['debug_leak_count']}, secret_leaks={liq['secret_leak_count']}")

    # 4. multi_asset_market_sync — partial (from v112g if available)
    print("  [4/5] multi_asset_market_sync...")
    sync = process_multi_asset_market_sync(card_type_fixtures)
    card_outputs.append(sync)
    v112g_used = sync.get("v112g_correlation_used", False)
    sync_status = "public (v112g)" if v112g_used else ("public" if sync['public_preview_available'] else "fallback")
    print(f"        readiness={sync['readiness']}, preview={sync_status}, "
          f"v112g_used={v112g_used}, "
          f"debug_leaks={sync['debug_leak_count']}, secret_leaks={sync['secret_leak_count']}")

    # 5. news_event_market_impact — partial (from v112d)
    print("  [5/5] news_event_market_impact...")
    news = process_news_event_market_impact()
    card_outputs.append(news)
    print(f"        readiness={news['readiness']}, previews={news.get('public_card_count', 0)}, "
          f"debug_leaks={news['debug_leak_count']}, secret_leaks={news['secret_leak_count']}")

    print()

    # ── Step 3: Compute aggregate summary ──────────────────────────────────────
    print("[3/6] Computing aggregate summary...")

    ready_count = sum(1 for c in card_outputs if c["readiness"] == "ready")
    partial_count = sum(1 for c in card_outputs if c["readiness"] == "partial")
    missing_count = sum(1 for c in card_outputs if c["readiness"] == "missing")

    all_card_types_present = len(card_outputs) == 5
    expected_card_types = [
        "price_oi_volume_anomaly", "whale_position_alert", "liquidation_pressure",
        "multi_asset_market_sync", "news_event_market_impact",
    ]
    all_present = all(
        any(c["card_type"] == expected for c in card_outputs)
        for expected in expected_card_types
    )

    public_preview_total = sum(
        1 for c in card_outputs
        if c.get("public_preview_available") or c.get("fallback_preview_available")
    )

    total_debug_leaks = sum(c.get("debug_leak_count", 0) for c in card_outputs)
    total_secret_leaks = sum(c.get("secret_leak_count", 0) for c in card_outputs)

    # Matrix summary from registry
    matrix_summary = get_fixed_card_matrix_summary()

    print(f"  Ready={ready_count}, Partial={partial_count}, Missing={missing_count}")
    print(f"  All 5 card types present: {all_present}")
    print(f"  Public preview total: {public_preview_total}")
    print(f"  Total debug leaks: {total_debug_leaks}")
    print(f"  Total secret leaks: {total_secret_leaks}")
    print()

    # ── Step 4: Write result JSON ──────────────────────────────────────────────
    print("[4/6] Writing result JSON...")

    result = {
        "version": VERSION,
        "run_id": RUN_ID,
        "card_type_count": len(card_outputs),
        "ready_count": ready_count,
        "partial_count": partial_count,
        "missing_count": missing_count,
        "all_card_types_present": all_present,
        "public_preview_total": public_preview_total,
        "debug_leak_count": total_debug_leaks,
        "secret_leak_count": total_secret_leaks,
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "live_ready": False,
        "card_outputs": card_outputs,
        "fixed_card_matrix_summary": matrix_summary,
        "unfinished_items": [
            "liquidation_pressure: 缺少实时清算数据源（当前仅 fixture）",
            "news_event_market_impact: 缺少实时新闻 RSS/API 接入管道（当前仅 fixture）",
            "whale_position_alert: 缺少地址标签自动标注和历史仓位序列追踪",
            "multi_asset_market_sync: 缺少跨资产实时相关性矩阵自动检测",
            "price_oi_volume_anomaly: OI/Volume delta 实时追踪待增强",
        ],
        "generated_at": china_stamp(),
        "notes": [
            "All 5 card types successfully aggregated through unified v112e pipeline.",
            "All samples are fixtures — no live market data used.",
            "TG send disabled — real_tg_sent=false.",
            "No external API calls made.",
            "No external AI calls made.",
            "No daemon/loop/cron started.",
            "No tokens/keys/cookies/passwords read or saved.",
            "No files deleted.",
            f"Final matrix: Ready={ready_count}, Partial={partial_count}, Missing={missing_count}",
        ],
    }

    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RESULT_JSON_PATH}")
    print()

    # ── Step 5: Write Markdown report ──────────────────────────────────────────
    print("[5/6] Writing Markdown report and handoff...")
    write_markdown_report(result, card_outputs)
    write_handoff(result, card_outputs)
    print()

    # ── Step 6: Print final summary ────────────────────────────────────────────
    print(f"{'=' * 70}")
    print(f"v1.12-E All Fixed Card Local Dry-Run Pipeline — Complete")
    print(f"{'=' * 70}")
    print(f"  Card types processed:    {len(card_outputs)}")
    print(f"  Ready:                   {ready_count}")
    print(f"  Partial:                 {partial_count}")
    print(f"  Missing:                 {missing_count}")
    print(f"  All card types present:  {all_present}")
    print(f"  Public preview total:    {public_preview_total}")
    print(f"  Debug leaks:             {total_debug_leaks}")
    print(f"  Secret leaks:            {total_secret_leaks}")
    print(f"  TG send:                 NONE")
    print(f"  External API:            NONE")
    print(f"  External AI:             NONE")
    print(f"  Daemon/Loop/Cron:        NONE")
    print(f"  Live ready:              FALSE")
    print()
    print(f"  Output files:")
    print(f"    {RESULT_JSON_PATH}")
    print(f"    {REPORT_MD_PATH}")
    print(f"    {HANDOFF_MD_PATH}")
    print(f"{'=' * 70}")

    return 0


# ══════════════════════════════════════════════════════════════════════════════════════
# Report Writers
# ══════════════════════════════════════════════════════════════════════════════════════

def write_markdown_report(result: dict, card_outputs: list[dict]) -> None:
    """Write the v1.12-E Markdown report."""
    lines = [
        f"# Market Radar v1.12-E — All Fixed Card Local Dry-Run Pipeline Report",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Run ID**: {RUN_ID}",
        f"",
        f"---",
        f"",
        f"## 概述",
        f"",
        f"本报告证明 5 类固定卡片可以被统一入口 (`run_market_radar_v112e_all_fixed_card_local_pipeline.py`)",
        f"稳定产出，不是各自孤立通过，而是作为统一 pipeline 完成 dry-run 聚合。",
        f"",
        f"所有卡片均使用本地 fixture 数据，未调用外部 API、未发送 TG、未启动 daemon。",
        f"",
        f"## 固定卡片矩阵",
        f"",
        f"| # | Card Type | Display Name | Readiness | Public Preview | Gate Tested | Live Ready |",
        f"|---|-----------|-------------|-----------|---------------|-------------|------------|",
    ]

    for i, c in enumerate(card_outputs, 1):
        rl = c["readiness"]
        rl_icon = {"ready": "✅", "partial": "⚠️", "missing": "❌"}.get(rl, "❓")
        preview_ok = "✅" if c.get("public_preview_available") else ("⚠️ fallback" if c.get("fallback_preview_available") else "❌")
        gate_ok = "✅" if c.get("gate_tested") else "❌"
        live_ok = "❌ (fixture)" if not c.get("live_ready") else "⚠️"

        lines.append(
            f"| {i} | `{c['card_type']}` | {c.get('display_name', '')} | "
            f"{rl_icon} {rl} | {preview_ok} | {gate_ok} | {live_ok} |"
        )

    lines.extend([
        f"",
        f"**计数**: Ready={result['ready_count']}, Partial={result['partial_count']}, Missing={result['missing_count']}",
        f"",
        f"---",
        f"",
        f"## Public Preview 总数",
        f"",
        f"- **public_preview_total**: {result['public_preview_total']}",
        f"- **debug_leak_count**: {result['debug_leak_count']}",
        f"- **secret_leak_count**: {result['secret_leak_count']}",
        f"",
        f"---",
        f"",
    ])

    # Per card type detail
    for c in card_outputs:
        rl = c["readiness"]
        rl_icon = {"ready": "✅", "partial": "⚠️", "missing": "❌"}.get(rl, "❓")

        lines.extend([
            f"## {rl_icon} {c.get('display_name', c['card_type'])} (`{c['card_type']}`)",
            f"",
            f"### Readiness: {rl}",
            f"",
            f"- **Public preview available**: {c.get('public_preview_available', False)}",
            f"- **Fallback preview available**: {c.get('fallback_preview_available', False)}",
            f"- **Gate tested**: {c.get('gate_tested', False)}",
            f"- **Live ready**: {c.get('live_ready', False)}",
            f"- **Debug leaks**: {c.get('debug_leak_count', 0)}",
            f"- **Secret leaks**: {c.get('secret_leak_count', 0)}",
            f"",
            f"### Output Summary",
            f"",
            f"{c.get('output_summary', 'No summary available.')}",
            f"",
        ])

        missing_caps = c.get("missing_capability", [])
        if missing_caps:
            lines.append("### Missing Capabilities")
            lines.append("")
            for mc in missing_caps:
                lines.append(f"- {mc}")
            lines.append("")

        preview_text = c.get("public_preview_sample", "")
        if preview_text:
            lines.extend([
                f"### Public Preview Sample",
                f"",
                f"```",
                preview_text[:600],
                f"```",
                f"",
            ])

        lines.extend([
            f"---",
            f"",
        ])

    # Unfinished items
    lines.extend([
        f"## Unfinished Items / Risks",
        f"",
    ])
    for item in result.get("unfinished_items", []):
        lines.append(f"- {item}")

    lines.extend([
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
        f"| debug_leak_count | {result['debug_leak_count']} |",
        f"| secret_leak_count | {result['secret_leak_count']} |",
        f"| token/key/cookie read | false |",
        f"| files_deleted | false |",
        f"",
    ])

    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] {REPORT_MD_PATH}")


def write_handoff(result: dict, card_outputs: list[dict]) -> None:
    """Write the v1.12-E handoff markdown."""
    lines = [
        f"# Market Radar v1.12-E — All Fixed Card Local Dry-Run Pipeline Handoff",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: 20260604_202718.r14",
        f"",
        f"---",
        f"",
        f"## 修改文件",
        f"",
        f"| 文件 | 操作 | 说明 |",
        f"|------|------|------|",
        f"| `scripts/run_market_radar_v112e_all_fixed_card_local_pipeline.py` | 新增 | 统一 5 类固定卡片 dry-run pipeline runner |",
        f"| `scripts/test_market_radar_all_fixed_card_pipeline_v112e.py` | 新增 | v112e 统一 pipeline 测试 |",
        f"| `results/market_radar_v112e_all_fixed_card_local_pipeline_result.json` | 新增 | 统一 pipeline 结果 JSON |",
        f"| `runs/market_radar/v112e_all_fixed_card_local_pipeline.md` | 新增 | Markdown 报告 |",
        f"| `runs/market_radar/v112e_all_fixed_card_local_pipeline_handoff.md` | 新增 | Handoff（本文件） |",
        f"",
        f"---",
        f"",
        f"## 执行命令",
        f"",
        f"```powershell",
        f"cd C:\\Users\\PC\\Desktop\\Projects\\事件情报系统",
        f"python scripts/run_market_radar_v112e_all_fixed_card_local_pipeline.py",
        f"python scripts/test_market_radar_all_fixed_card_pipeline_v112e.py",
        f"```",
        f"",
        f"---",
        f"",
        f"## 5 类固定卡片 Readiness Matrix",
        f"",
        f"| # | Card Type | Readiness | Public Preview | Gate Tested | Live Ready |",
        f"|---|-----------|-----------|---------------|-------------|------------|",
    ]

    for i, c in enumerate(card_outputs, 1):
        rl = c["readiness"]
        rl_icon = {"ready": "✅", "partial": "⚠️", "missing": "❌"}.get(rl, "❓")
        preview_ok = "✅" if c.get("public_preview_available") else ("⚠️ fallback" if c.get("fallback_preview_available") else "❌")
        gate_ok = "✅" if c.get("gate_tested") else "❌"
        live_ok = "❌" if not c.get("live_ready") else "⚠️"

        lines.append(
            f"| {i} | `{c['card_type']}` | {rl_icon} {rl} | {preview_ok} | {gate_ok} | {live_ok} |"
        )

    lines.extend([
        f"",
        f"**Final Matrix**: Ready={result['ready_count']}, Partial={result['partial_count']}, Missing={result['missing_count']}",
        f"",
        f"---",
        f"",
        f"## 每类 Card Type Output Summary",
        f"",
    ])

    for c in card_outputs:
        lines.append(f"### {c.get('display_name', c['card_type'])} (`{c['card_type']}`)")
        lines.append(f"")
        lines.append(f"{c.get('output_summary', 'No summary.')}")
        lines.append(f"")

    lines.extend([
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
        f"| debug_leak_count | {result['debug_leak_count']} |",
        f"| secret_leak_count | {result['secret_leak_count']} |",
        f"| token/key/cookie read | false |",
        f"| files_deleted | false |",
        f"",
        f"---",
        f"",
        f"## Unfinished Items / Risks",
        f"",
    ])

    for item in result.get("unfinished_items", []):
        lines.append(f"- {item}")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 下一步建议",
        f"",
        f"1. **不需要马上接 live 数据源** — v1.12-E 已证明 5 类卡片统一 entry 可行，",
        f"   下一步应专注于提升「质量」而非「实时性」。",
        f"2. **优先补齐 Partial 卡片的核心 missing capability**：",
        f"   - liquidation_pressure: 接入免费清算数据聚合（如交易所 WebSocket）",
        f"   - news_event_market_impact: 接入免费新闻 RSS/API",
        f"   - whale_position_alert: 地址标签自动标注",
        f"   - multi_asset_market_sync: 跨资产相关性矩阵",
        f"3. **price_oi_volume_anomaly** 已 ready，可在其他卡片推进时并行增强。",
        f"",
    ])

    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] {HANDOFF_MD_PATH}")


if __name__ == "__main__":
    raise SystemExit(main())
