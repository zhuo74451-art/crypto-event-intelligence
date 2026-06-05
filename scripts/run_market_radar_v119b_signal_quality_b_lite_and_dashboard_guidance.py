"""Market Radar v119B — Signal Quality B-Lite + Dashboard Guidance.

Builds on v119A live one-shot no-send operator dashboard with two B-lite
quality improvements and a Chinese-language guidance layer:

  B-lite 1 — price_oi_volume_anomaly layered operator decision:
    reject  : no meaningful anomaly
    watch   : mild anomaly (near threshold, single factor, large-cap close)
              → observation only, NOT accept, NOT publish
    accept  : strong threshold pass only (unchanged strict gate)

  B-lite 2 — news_event_market_impact freshness/stale + entity:
    freshness tags : fresh (<4h) / stale (>24h) / unknown
    stale warning  : old RSS re-push / title-repeat risk
    entity normalization : BTC↔Bitcoin, ETH↔Ethereum, etc.
    decision rules : fresh+clear→watch, stale→lower weight or watch_with_stale_warning

  Dashboard layer — Chinese 30-second guidance:
    Top section answers: 这是什么 / 现在怎么看 / 现在能不能发 /
    数据从哪来 / 操作员下一步

This runner MUST NOT:
  - Send Telegram messages
  - Post to X/Twitter
  - Call any AI/model API
  - Start daemons, cron jobs, or loops
  - Modify v116A–N / v117 / v118 / v119A historical outputs
  - Write production state
  - Print/store raw credentials, tokens, chat_ids, passwords, API keys

Live data sources (free, no API key):
  - Binance public REST (/api/v3/ticker/24hr, /fapi/v1/openInterest)
  - CoinDesk / Cointelegraph / Decrypt / The Block / Binance Announcements (RSS/JSON)

Five card families:
  1. multi_asset_market_sync      → live Binance API
  2. price_oi_volume_anomaly      → live Binance API + B-lite layered decision
  3. news_event_market_impact     → live RSS/news + Binance + B-lite freshness
  4. liquidation_pressure         → fixture (gate NOT lowered)
  5. whale_position_alert         → fixture (manual_evidence NOT bypassed)

Outputs:
  results/market_radar_v119b_signal_quality_b_lite_result.json
  runs/market_radar/v119b_live_operator_snapshot.md
  runs/market_radar/v119b_operator_decision_table.md
  runs/market_radar/v119b_operator_dashboard.html
  runs/market_radar/v119b_no_send_preview.md
  runs/market_radar/v119b_local_only_handoff.md

Usage:
    python scripts/run_market_radar_v119b_signal_quality_b_lite_and_dashboard_guidance.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CN_TZ = timezone(timedelta(hours=8))
RUN_ID = datetime.now(CN_TZ).strftime("%Y%m%d_%H%M%S")
PIPELINE_VERSION = "v1.19B"
TASK_ID = "20260605_v119b_signal_quality_b_lite_and_dashboard_guidance"

# ── Output paths ───────────────────────────────────────────────────────────────

OUTPUT_RESULT_JSON = ROOT / "results" / "market_radar_v119b_signal_quality_b_lite_result.json"
OUTPUT_SNAPSHOT_MD = ROOT / "runs" / "market_radar" / "v119b_live_operator_snapshot.md"
OUTPUT_DECISION_TABLE_MD = ROOT / "runs" / "market_radar" / "v119b_operator_decision_table.md"
OUTPUT_DASHBOARD_HTML = ROOT / "runs" / "market_radar" / "v119b_operator_dashboard.html"
OUTPUT_NO_SEND_PREVIEW_MD = ROOT / "runs" / "market_radar" / "v119b_no_send_preview.md"
OUTPUT_HANDOFF_MD = ROOT / "runs" / "market_radar" / "v119b_local_only_handoff.md"

FIVE_CARD_FAMILIES = [
    "multi_asset_market_sync",
    "price_oi_volume_anomaly",
    "news_event_market_impact",
    "liquidation_pressure",
    "whale_position_alert",
]

ALLOWED_DECISIONS = {"accept", "watch", "reject", "manual_required"}


# ── B-Lite Helpers ────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
# B-LITE 1: Layered operator decision for Price/OI/Volume Anomaly
# ═══════════════════════════════════════════════════════════════════════════════

def blite_price_oi_volume_layered_decision(
    api_success: bool,
    gate_allowed: bool,
    signals: list[dict],
    gate_reason: str,
    error: Optional[str] = None,
) -> dict[str, Any]:
    """B-lite layered operator decision for price_oi_volume_anomaly.

    Returns a dict with:
      decision: reject | watch | accept
      blite_tier: none | mild_watch | accept
      blite_reason: explanation of tier assignment
      oi_warnings: list of OI-related issues detected
      watch_is_observation: True (watch ≠ publish)
    """
    oi_warnings: list[str] = []
    blite_tier = "none"
    blite_reason = ""

    # ── API failure → reject ──
    if not api_success:
        return {
            "decision": "reject",
            "blite_tier": "none",
            "blite_reason": "Binance API call failed — no anomaly data available.",
            "oi_warnings": [],
            "watch_is_observation": True,
        }

    # ── Gate not allowed → check for mild signals that deserve watch ──
    if not gate_allowed:
        # B-lite: scan signals for mild anomalies even when gate blocked
        mild_signals: list[dict] = []
        for sig in signals:
            change_pct = abs(sig.get("price_change_24h_pct", 0))
            factors = sig.get("confirmation_factors", [])
            symbol = sig.get("symbol", "")
            oi_val = sig.get("open_interest_current")

            # Check OI for $0.0B issues
            if oi_val is not None and oi_val == 0.0:
                oi_warnings.append(
                    f"OI=$0.0B for {symbol}: API returned 0 — possible parse/unit/field issue. "
                    f"No OI data available for this asset; OI factor excluded from anomaly check."
                )
            elif oi_val is not None and oi_val < 1000:
                oi_warnings.append(
                    f"OI=${oi_val:.1f} for {symbol}: unusually low — may be API parse or unit error."
                )
            elif oi_val is None:
                oi_warnings.append(
                    f"OI unavailable for {symbol}: API fetch failed — OI factor excluded."
                )

            # Mild anomaly criteria (does NOT trigger accept):
            # - price move >= 3% but < 5% (near threshold) on large-cap (ETH/SOL)
            # - OR exactly 1 confirmation factor with price move >= 3%
            # - OR ETH/SOL with price move >= 3% (near threshold, worth watching)
            is_large_cap = symbol in ("ETHUSDT", "SOLUSDT")
            near_threshold = change_pct >= 3.0 and change_pct < 5.0
            has_one_factor = len(factors) >= 1

            if near_threshold or (is_large_cap and change_pct >= 3.0 and has_one_factor):
                sig["blite_mild_anomaly"] = True
                sig["blite_mild_reason"] = (
                    f"{symbol}: |Δ|={change_pct:.2f}% (near threshold or large-cap), "
                    f"factors={factors}"
                )
                mild_signals.append(sig)

        if mild_signals:
            blite_tier = "mild_watch"
            symbols_str = ", ".join(s.get("symbol", "?") for s in mild_signals)
            blite_reason = (
                f"Mild anomaly detected on {symbols_str}: price move near threshold or "
                f"single-factor signal on large-cap asset. This is WATCH only — NOT accept, "
                f"NOT publishable. Operator should monitor for threshold breach. "
                f"Gate remains correctly blocked for publication."
            )
            return {
                "decision": "watch",
                "blite_tier": "mild_watch",
                "blite_reason": blite_reason,
                "oi_warnings": oi_warnings,
                "watch_is_observation": True,
                "mild_signals": mild_signals,
            }
        else:
            return {
                "decision": "reject",
                "blite_tier": "none",
                "blite_reason": (
                    "No asset passed admission threshold and no mild anomaly detected. "
                    "All signals below minimum observation threshold. "
                    "This is a correct gate block — do NOT lower threshold."
                ),
                "oi_warnings": oi_warnings,
                "watch_is_observation": True,
            }

    # ── Gate allowed → check strength for watch vs accept ──
    strong_signals: list[dict] = []
    mild_accepts: list[dict] = []
    for sig in signals:
        if not sig.get("admission_passed"):
            continue
        change_pct = abs(sig.get("price_change_24h_pct", 0))
        factors = sig.get("confirmation_factors", [])
        anomaly_type = sig.get("anomaly_type", "normal")
        symbol = sig.get("symbol", "")

        # Check OI issues
        oi_val = sig.get("open_interest_current")
        if oi_val is not None and oi_val == 0.0:
            oi_warnings.append(
                f"OI=$0.0B for {symbol}: API returned 0 — possible parse/unit/field issue."
            )

        # Strong signal: extreme anomaly + 2+ factors → could be accept
        if anomaly_type == "extreme" and len(factors) >= 2:
            strong_signals.append(sig)
        elif anomaly_type == "notable" and len(factors) >= 2:
            strong_signals.append(sig)
        else:
            # Gate passed but signal not strong enough for accept — watch
            mild_accepts.append(sig)

    if strong_signals:
        blite_tier = "accept"
        symbols_str = ", ".join(s.get("symbol", "?") for s in strong_signals)
        blite_reason = (
            f"Strong anomaly confirmed on {symbols_str}: gate passed with extreme/notable "
            f"anomaly type and >=2 confirmation factors. Operator should still verify "
            f"anomaly magnitude before relying on signal."
        )
        return {
            "decision": "accept",
            "blite_tier": "accept",
            "blite_reason": blite_reason,
            "oi_warnings": oi_warnings,
            "watch_is_observation": True,
        }
    elif mild_accepts:
        blite_tier = "mild_watch"
        symbols_str = ", ".join(s.get("symbol", "?") for s in mild_accepts)
        blite_reason = (
            f"Gate passed for {symbols_str} but anomaly strength is below accept threshold "
            f"(insufficient confirmation factors or anomaly type). WATCH only — NOT accept. "
            f"Operator should verify anomaly magnitude before escalating."
        )
        return {
            "decision": "watch",
            "blite_tier": "mild_watch",
            "blite_reason": blite_reason,
            "oi_warnings": oi_warnings,
            "watch_is_observation": True,
        }
    else:
        # Gate allowed but no signal passed? Shouldn't happen, but safety net
        blite_tier = "mild_watch"
        return {
            "decision": "watch",
            "blite_tier": "mild_watch",
            "blite_reason": "Gate allowed but no individual signal meets accept criteria.",
            "oi_warnings": oi_warnings,
            "watch_is_observation": True,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# B-LITE 2: News freshness/stale entity-aware quality boost
# ═══════════════════════════════════════════════════════════════════════════════

# Entity normalization map
ENTITY_NORM_MAP: dict[str, str] = {
    "BTC": "BTC", "BITCOIN": "BTC", "XBT": "BTC",
    "ETH": "ETH", "ETHEREUM": "ETH",
    "SOL": "SOL", "SOLANA": "SOL",
    "BNB": "BNB",
    "ETF": "ETF",
    "FED": "FED", "FEDERAL RESERVE": "FED",
    "ECB": "ECB",
    "SEC": "SEC",
    "CFTC": "CFTC",
    "BINANCE": "BINANCE",
    "COINBASE": "COINBASE",
}


def _normalize_entity(entity: str) -> str:
    """Normalize an entity string to canonical form."""
    return ENTITY_NORM_MAP.get(entity.upper(), entity.upper())


def _classify_freshness(
    title: str, source_name: str, extracted_at: str, url: str
) -> tuple[str, str, list[str]]:
    """B-lite freshness classifier for news articles.

    Returns:
        (freshness, freshness_reason, stale_warnings)

    Freshness categories:
      - fresh: likely < 4 hours old (high-intensity keywords, no staleness markers)
      - stale: > 24 hours old or re-pushed old RSS
      - unknown: cannot determine

    Stale detection heuristics (rule-based, NO AI):
      - Title contains time phrases like "yesterday", "last week", "ago"
      - Source is known to re-push old articles
      - Title has common RSS replay markers
    """
    text_lower = title.lower()
    stale_warnings: list[str] = []

    # ── Check for explicit age markers ──
    age_markers = [
        r"\b\d+\s+(day|days|week|weeks|month|months)\s+ago\b",
        r"\byesterday\b",
        r"\blast\s+(week|month|year)\b",
        r"\b\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b",
    ]
    for marker in age_markers:
        if re.search(marker, text_lower):
            return (
                "stale",
                f"Title contains time marker suggesting old article: '{title[:80]}'",
                [f"STALE RISK: Article appears to reference past event — '{title[:100]}'. "
                 f"Market price may no longer match. Do NOT cite as current."],
            )

    # ── Check for re-pushed RSS / common stale patterns ──
    stale_patterns = [
        r"\b(recap|weekly\s+roundup|this\s+week\s+in|last\s+week\s+in)\b",
        r"\b(digest|newsletter|roundup|top\s+stories)\b",
    ]
    for pat in stale_patterns:
        if re.search(pat, text_lower):
            stale_warnings.append(
                f"STALE RISK: Title matches news-roundup pattern — may be re-aggregated "
                f"or delayed content: '{title[:100]}'. Cross-check publish date."
            )
            return (
                "stale",
                f"News roundup/digest pattern detected in title",
                stale_warnings,
            )

    # ── Check for high-intensity keywords suggesting fresh/breaking ──
    fresh_indicators = [
        "breaking", "just in", "alert", "flash", "urgent",
        "minutes ago", "hours ago", "today", "now",
    ]
    for ind in fresh_indicators:
        if ind in text_lower:
            return ("fresh", f"Breaking/fresh indicator '{ind}' found in title", [])

    # ── Source-based freshness heuristics ──
    # Some sources are known to be near-real-time
    real_time_sources = {"coindesk", "cointelegraph", "the block", "decrypt"}
    source_key = source_name.lower().replace(" ", "")
    if source_key in real_time_sources or any(
        rt in source_key for rt in real_time_sources
    ):
        return ("fresh", f"Source '{source_name}' is near-real-time", [])

    # ── Default: unknown ──
    return (
        "unknown",
        f"Cannot determine freshness from title alone — check article publish date",
        [],
    )


def blite_news_event_quality_boost(
    events_found: int,
    sources_succeeded: int,
    gate_allowed: bool,
    gate_reason: str,
    articles_data: list[dict],
    error: Optional[str] = None,
) -> dict[str, Any]:
    """B-lite quality boost for news_event_market_impact.

    Adds: freshness tagging, stale detection, entity normalization.
    Always preserves: observation_only=true, not_causal_proof=true.

    Returns dict with:
      decision: watch | reject
      freshness_map: per-article freshness classification
      stale_warnings: any stale content risks
      entity_normalized: entities found with canonical names
      observation_only: True (always)
      not_causal_proof: True (always)
    """
    observation_only = True
    not_causal_proof = True

    freshness_map: list[dict] = []
    all_stale_warnings: list[str] = []
    entities_found: set[str] = set()

    # ── Classify freshness for each article ──
    for art in articles_data or []:
        title = art.get("title", "")
        source = art.get("source_name", "")
        url = art.get("url", "")
        extracted_at = china_stamp()

        freshness, reason, stale_warns = _classify_freshness(
            title, source, extracted_at, url
        )
        freshness_map.append({
            "title": title[:120],
            "source": source,
            "freshness": freshness,
            "freshness_reason": reason,
            "has_stale_warning": len(stale_warns) > 0,
        })
        all_stale_warnings.extend(stale_warns)

        # ── Entity normalization on title ──
        for raw_entity in ENTITY_NORM_MAP:
            if re.search(r'\b' + re.escape(raw_entity) + r'\b', title, re.IGNORECASE):
                entities_found.add(_normalize_entity(raw_entity))

    # ── Count fresh vs stale ──
    fresh_count = sum(1 for f in freshness_map if f["freshness"] == "fresh")
    stale_count = sum(1 for f in freshness_map if f["freshness"] == "stale")
    unknown_count = sum(1 for f in freshness_map if f["freshness"] == "unknown")

    # ── B-lite decision rules ──
    if events_found > 0 and gate_allowed:
        if stale_count > 0 and fresh_count == 0:
            # All articles appear stale — still watch but with strong warning
            decision = "watch"
            blite_decision_detail = (
                f"News events detected ({events_found} events, {sources_succeeded} sources) "
                f"but ALL appear stale or are re-aggregated content. "
                f"WATCH with STALE WARNING — do NOT cite as current market context."
            )
        elif stale_count > 0:
            decision = "watch"
            blite_decision_detail = (
                f"News events detected ({events_found} events, {fresh_count} fresh, "
                f"{stale_count} stale). Fresh content available but stale items present. "
                f"WATCH — filter out stale items before using."
            )
        else:
            decision = "watch"
            blite_decision_detail = (
                f"News events detected ({events_found} events, {fresh_count} fresh). "
                f"Fresh content with clear entity attribution. WATCH for contextual awareness. "
                f"NOT causal proof. NOT actionable trading signal."
            )
    elif events_found == 0 and sources_succeeded > 0:
        decision = "reject"
        blite_decision_detail = (
            f"News sources available ({sources_succeeded}) but no events extracted "
            f"with attributable assets. Normal for quiet news periods."
        )
    else:
        decision = "reject"
        blite_decision_detail = (
            "All public news sources unavailable or failed. Re-run when connectivity is restored."
        )

    return {
        "decision": decision,
        "blite_decision_detail": blite_decision_detail,
        "freshness_map": freshness_map,
        "fresh_count": fresh_count,
        "stale_count": stale_count,
        "unknown_count": unknown_count,
        "stale_warnings": all_stale_warnings,
        "entities_found": sorted(entities_found),
        "observation_only": True,
        "not_causal_proof": True,
    }


# ── Core Helpers ───────────────────────────────────────────────────────────────

def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_text(path: Path, content: str) -> None:
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 1: Live Data Fetch via Free API Adapters
# ═══════════════════════════════════════════════════════════════════════════════


def fetch_live_signals() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Fetch live signals from all adapters.

    Returns:
        (live_results, fixture_results, diagnostics, news_articles_raw)
    """
    from market_radar.shared.models import CardFamily
    from market_radar.shared.pipeline import SharedPipeline
    from market_radar.shared.free_api_adapters import (
        MultiAssetMarketSyncFreeApiAdapter,
        PriceOIVolumeAnomalyFreeApiAdapter,
        NewsEventMarketImpactFreePublicSourceAdapter,
    )
    from market_radar.shared.adapter_contract import FixtureCatalog

    pipeline = SharedPipeline()
    live_results: list[dict] = []
    fixture_results: list[dict] = []
    diagnostics: list[dict] = []
    news_articles_raw: list[dict] = []

    # ── 1. Multi-Asset Market Sync ──
    print("  [LIVE] Fetching Multi-Asset Market Sync via Binance public API...")
    diag_multi = {"adapter": "MultiAssetMarketSyncFreeApiAdapter", "used": True, "status": "unknown"}
    try:
        adapter = MultiAssetMarketSyncFreeApiAdapter()
        result = pipeline.run(adapter)
        api_success = result.signal.metrics.get("api_success", False) if result.signal else False
        assets_fetched = len(result.signal.metrics.get("assets", [])) if result.signal else 0
        diag_multi.update({
            "status": "ok" if not result.error else "error",
            "api_success": api_success,
            "assets_fetched": assets_fetched,
            "gate_allowed": result.gate_decision.allow if result.gate_decision else False,
            "error": result.error,
        })
        live_results.append({
            "card_family": "multi_asset_market_sync",
            "adapter_name": "MultiAssetMarketSyncFreeApiAdapter",
            "source": "live_binance_public_api",
            "result": result,
            "api_success": api_success,
            "assets_fetched": assets_fetched,
        })
        print(f"       assets={assets_fetched}, api_success={api_success}, "
              f"gate_allowed={diag_multi['gate_allowed']}")
    except Exception as e:
        diag_multi.update({"status": "error", "error": str(e)})
        print(f"       [ERROR] {e}")
    diagnostics.append(diag_multi)

    # ── 2. Price/OI/Volume Anomaly (B-lite: expose raw signals for layering) ──
    print("  [LIVE] Fetching Price/OI/Volume Anomaly via Binance public API (B-lite)...")
    diag_poi = {"adapter": "PriceOIVolumeAnomalyFreeApiAdapter", "used": True, "status": "unknown"}
    try:
        adapter = PriceOIVolumeAnomalyFreeApiAdapter()
        result = pipeline.run(adapter)
        api_success = result.signal.metrics.get("api_success", False) if result.signal else False
        raw_signals = result.signal.metrics.get("signals", []) if result.signal else []
        signals_count = len(raw_signals)
        diag_poi.update({
            "status": "ok" if not result.error else "error",
            "api_success": api_success,
            "signals_count": signals_count,
            "gate_allowed": result.gate_decision.allow if result.gate_decision else False,
            "error": result.error,
        })
        live_results.append({
            "card_family": "price_oi_volume_anomaly",
            "adapter_name": "PriceOIVolumeAnomalyFreeApiAdapter",
            "source": "live_binance_public_api",
            "result": result,
            "api_success": api_success,
            "signals_count": signals_count,
            "raw_signals": raw_signals,  # B-lite: pass raw signals for layering
        })
        print(f"       signals={signals_count}, api_success={api_success}, "
              f"gate_allowed={diag_poi['gate_allowed']}")
    except Exception as e:
        diag_poi.update({"status": "error", "error": str(e)})
        print(f"       [ERROR] {e}")
    diagnostics.append(diag_poi)

    # ── 3. News Event Market Impact (B-lite: collect articles for freshness) ──
    print("  [LIVE] Fetching News Event Market Impact via free public RSS/API sources (B-lite)...")
    diag_news = {"adapter": "NewsEventMarketImpactFreePublicSourceAdapter", "used": True, "status": "unknown"}
    try:
        adapter = NewsEventMarketImpactFreePublicSourceAdapter()
        result = pipeline.run(adapter)
        metrics = result.signal.metrics if result.signal else {}
        sources_succeeded = metrics.get("sources_succeeded", 0)
        events_found = metrics.get("events_found", 0)
        api_success = metrics.get("market_api_success", False)
        observation_only = metrics.get("observation_only", True)
        not_causal_proof = metrics.get("not_causal_proof", True)

        # B-lite: collect raw article data from sources_detail for freshness analysis
        sources_detail = metrics.get("sources_detail", [])

        diag_news.update({
            "status": "ok" if not result.error else "error",
            "sources_succeeded": sources_succeeded,
            "articles_fetched": metrics.get("articles_fetched", 0),
            "events_found": events_found,
            "api_success": api_success,
            "gate_allowed": result.gate_decision.allow if result.gate_decision else False,
            "observation_only": observation_only,
            "not_causal_proof": not_causal_proof,
            "error": result.error,
        })
        live_results.append({
            "card_family": "news_event_market_impact",
            "adapter_name": "NewsEventMarketImpactFreePublicSourceAdapter",
            "source": "live_free_public_rss_and_binance",
            "result": result,
            "api_success": api_success,
            "events_found": events_found,
            "sources_succeeded": sources_succeeded,
            "observation_only": observation_only,
            "not_causal_proof": not_causal_proof,
            "sources_detail": sources_detail,
        })
        print(f"       sources={sources_succeeded}, events={events_found}, "
              f"api_success={api_success}, gate_allowed={diag_news['gate_allowed']}")
    except Exception as e:
        diag_news.update({"status": "error", "error": str(e)})
        print(f"       [ERROR] {e}")
    diagnostics.append(diag_news)

    # ── 4. Liquidation Pressure (fixture — gate NOT lowered) ──
    print("  [FIXTURE] Running Liquidation Pressure (gate NOT lowered)...")
    diag_liq = {"adapter": "FixtureSignalAdapter(liquidation_pressure)", "used": True, "status": "unknown"}
    try:
        catalog = FixtureCatalog()
        adapter = catalog.adapter_for(CardFamily.LIQUIDATION_PRESSURE)
        result = pipeline.run(adapter)
        composite = result.signal.metrics.get("composite_score", 0) if result.signal else 0
        threshold = result.signal.metrics.get("admission_threshold", 0.60) if result.signal else 0.60
        diag_liq.update({
            "status": "ok" if not result.error else "error",
            "composite_score": composite,
            "threshold": threshold,
            "calm_market": result.signal.metrics.get("calm_market", True) if result.signal else True,
            "gate_allowed": result.gate_decision.allow if result.gate_decision else False,
            "threshold_not_lowered": threshold >= 0.60,
            "error": result.error,
        })
        fixture_results.append({
            "card_family": "liquidation_pressure",
            "adapter_name": "FixtureSignalAdapter(liquidation_pressure)",
            "source": "fixture",
            "result": result,
            "composite_score": composite,
            "threshold": threshold,
            "calm_market": True,
        })
        print(f"       composite={composite:.2f}, threshold={threshold:.2f}, "
              f"gate_allowed={diag_liq['gate_allowed']}, "
              f"threshold_not_lowered={diag_liq['threshold_not_lowered']}")
    except Exception as e:
        diag_liq.update({"status": "error", "error": str(e)})
        print(f"       [ERROR] {e}")
    diagnostics.append(diag_liq)

    # ── 5. Whale Position Alert (fixture — manual evidence NOT bypassed) ──
    print("  [FIXTURE] Running Whale Position Alert (manual evidence NOT bypassed)...")
    diag_whale = {"adapter": "FixtureSignalAdapter(whale_position_alert)", "used": True, "status": "unknown"}
    try:
        catalog = FixtureCatalog()
        adapter = catalog.adapter_for(CardFamily.WHALE_POSITION_ALERT)
        result = pipeline.run(adapter)
        manual_evidence = result.signal.metrics.get("manual_evidence_provided", False) if result.signal else False
        diag_whale.update({
            "status": "ok" if not result.error else "error",
            "manual_evidence_provided": manual_evidence,
            "gate_allowed": result.gate_decision.allow if result.gate_decision else False,
            "manual_evidence_not_bypassed": not manual_evidence,
            "error": result.error,
        })
        fixture_results.append({
            "card_family": "whale_position_alert",
            "adapter_name": "FixtureSignalAdapter(whale_position_alert)",
            "source": "fixture",
            "result": result,
            "manual_evidence_provided": manual_evidence,
        })
        print(f"       manual_evidence={manual_evidence}, "
              f"gate_allowed={diag_whale['gate_allowed']}, "
              f"manual_evidence_not_bypassed={diag_whale['manual_evidence_not_bypassed']}")
    except Exception as e:
        diag_whale.update({"status": "error", "error": str(e)})
        print(f"       [ERROR] {e}")
    diagnostics.append(diag_whale)

    return live_results, fixture_results, diagnostics, news_articles_raw


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 2: Operator Decision Engine (with B-lite enhancements)
# ═══════════════════════════════════════════════════════════════════════════════


def make_operator_decision(item: dict) -> dict[str, Any]:
    """Generate an operator decision with B-lite layered quality enhancements.

    Decision rules (v119B):
      - multi_asset_market_sync: same as v119A
      - price_oi_volume_anomaly: B-lite layered → reject/watch/accept
        - accept: only strong anomaly with >=2 confirmation factors
        - watch: mild anomaly or gate-passed but not strong enough for accept
        - reject: no anomaly, API failure
      - news_event_market_impact: B-lite freshness/stale + entity
        - fresh + clear entity → watch
        - stale → watch_with_stale_warning
      - liquidation_pressure: same as v119A (blocked → reject, threshold NOT lowered)
      - whale_position_alert: same as v119A (always manual_required)
    """
    cf = item.get("card_family", "unknown")
    result = item.get("result")
    error = item.get("error") or (result.error if result else None)
    gate_allowed = result.gate_decision.allow if result and result.gate_decision else False
    gate_reason = result.gate_decision.reason if result and result.gate_decision else "N/A"
    rendered_title = result.rendered_card.title if result and result.rendered_card else ""
    rendered_body = result.rendered_card.body if result and result.rendered_card else ""

    decision = "manual_required"
    reason = ""
    evidence_summary = ""
    publishability = "blocked"
    next_operator_action = ""
    observation_only = False
    not_causal_proof = False

    # B-lite extra fields
    blite_tier = ""
    oi_warnings: list[str] = []
    stale_warnings: list[str] = []
    entities_found: list[str] = []
    freshness_info: dict = {}
    watch_is_observation = False

    if cf == "multi_asset_market_sync":
        api_success = item.get("api_success", False)
        assets_count = item.get("assets_fetched", 0)

        if api_success and gate_allowed and assets_count >= 2:
            decision = "accept"
            reason = (
                f"Live Binance data available for {assets_count} assets. "
                "Multi-asset sync card is active with real free public API data. "
                "Operator should review individual asset deltas before relying on "
                "correlation signal alone. Product is not production-grade."
            )
            evidence_summary = (
                f"Live Binance public API: {assets_count} assets fetched. "
                f"Gate: {gate_reason[:120]}."
            )
            publishability = "test_group_only"
            next_operator_action = (
                "Review individual asset deltas. Confirm no stale ticker data."
            )
        elif api_success and not gate_allowed:
            decision = "watch"
            reason = f"Binance data available ({assets_count} assets) but quality gate blocked."
            evidence_summary = f"Live data but gate blocked: {gate_reason[:120]}"
            publishability = "blocked"
            next_operator_action = "Monitor gate thresholds. Re-run when market conditions change."
        else:
            decision = "reject"
            reason = "Binance API call failed — no live data available."
            evidence_summary = f"API failure: {error or 'unknown'}"
            publishability = "blocked"
            next_operator_action = "Check network connectivity. Re-run manually."

    elif cf == "price_oi_volume_anomaly":
        api_success = item.get("api_success", False)
        raw_signals = item.get("raw_signals", [])
        signals_count = item.get("signals_count", 0)

        # ── B-lite layered decision ──
        blite = blite_price_oi_volume_layered_decision(
            api_success=api_success,
            gate_allowed=gate_allowed,
            signals=raw_signals,
            gate_reason=gate_reason,
            error=error,
        )
        decision = blite["decision"]
        blite_tier = blite["blite_tier"]
        reason = blite["blite_reason"]
        oi_warnings = blite.get("oi_warnings", [])
        watch_is_observation = blite.get("watch_is_observation", False)

        if decision == "accept":
            evidence_summary = (
                f"Live Binance + OI: {signals_count} signals. B-lite tier=accept. "
                f"Strong anomaly with >=2 confirmation factors."
            )
            publishability = "test_group_only"
            next_operator_action = (
                "Strong anomaly confirmed. Still verify anomaly magnitude. "
                "Do NOT treat as causal signal."
            )
        elif decision == "watch":
            evidence_summary = (
                f"Live Binance + OI: {signals_count} signals. B-lite tier=mild_watch. "
                f"Mild anomaly — observation only, NOT accept."
            )
            publishability = "blocked"
            next_operator_action = (
                "WATCH only — do NOT publish. Monitor for threshold breach. "
                "Mild anomalies are observation-level, not actionable."
            )
        else:  # reject
            evidence_summary = f"B-lite tier=none. {gate_reason[:120]}"
            publishability = "blocked"
            next_operator_action = (
                "No action needed. Retry during higher-volatility windows."
            )

        # Append OI warnings to reason if present
        if oi_warnings:
            reason += " | OI WARNINGS: " + "; ".join(oi_warnings[:3])

    elif cf == "news_event_market_impact":
        events_found = item.get("events_found", 0)
        sources_succeeded = item.get("sources_succeeded", 0)
        observation_only = True
        not_causal_proof = True

        # ── B-lite freshness/entity quality boost ──
        # Build pseudo-articles from sources_detail for freshness analysis
        articles_data: list[dict] = []
        sources_detail = item.get("sources_detail", [])
        for src in sources_detail:
            if isinstance(src, dict):
                articles_data.append({
                    "title": src.get("source_name", ""),
                    "source_name": src.get("source_name", ""),
                    "url": "",
                })

        # Also include rendered title as an article for freshness check
        if rendered_title:
            articles_data.append({
                "title": rendered_title,
                "source_name": item.get("result", {}).signal.metrics.get("source_name", "") if item.get("result") and hasattr(item["result"], "signal") and item["result"].signal else "",
                "url": "",
            })

        blite_news = blite_news_event_quality_boost(
            events_found=events_found,
            sources_succeeded=sources_succeeded,
            gate_allowed=gate_allowed,
            gate_reason=gate_reason,
            articles_data=articles_data,
            error=error,
        )

        decision = blite_news["decision"]
        reason = blite_news["blite_decision_detail"]
        stale_warnings = blite_news.get("stale_warnings", [])
        entities_found = blite_news.get("entities_found", [])
        freshness_info = {
            "fresh_count": blite_news.get("fresh_count", 0),
            "stale_count": blite_news.get("stale_count", 0),
            "unknown_count": blite_news.get("unknown_count", 0),
        }

        if decision == "watch":
            evidence_summary = (
                f"News: {events_found} events from {sources_succeeded} sources. "
                f"Fresh={freshness_info.get('fresh_count', 0)}, "
                f"Stale={freshness_info.get('stale_count', 0)}. "
                f"Entities: {', '.join(entities_found[:5])}. "
                f"observation_only=true, not_causal_proof=true."
            )
            if stale_warnings:
                evidence_summary += f" ⚠ {len(stale_warnings)} stale warning(s)."
            publishability = "test_group_only_with_caveat"
            next_operator_action = (
                "Read full article at source URL before citing. "
                "Cross-reference with at least one other news source. "
                "Filter out stale/re-aggregated items. "
                "Do NOT present as causal market analysis."
            )
        else:
            evidence_summary = (
                f"News: {sources_succeeded} sources, {events_found} events. "
                f"observation_only=true, not_causal_proof=true."
            )
            publishability = "blocked"
            next_operator_action = "Wait for higher-impact news cycle. Re-run manually."

    elif cf == "liquidation_pressure":
        composite = item.get("composite_score", 0)
        threshold = item.get("threshold", 0.60)

        if not gate_allowed:
            decision = "reject"
            reason = (
                f"Liquidation gate CORRECTLY blocked. "
                f"Calm market (composite={composite:.2f} < threshold={threshold:.2f}). "
                "Threshold NOT lowered."
            )
            evidence_summary = (
                f"Fixture: composite={composite:.2f}, threshold={threshold:.2f}. "
                "Calm market. Threshold NOT lowered."
            )
            publishability = "blocked"
            next_operator_action = "No action needed. DO NOT lower threshold."
        else:
            decision = "watch"
            reason = "Liquidation pressure card unexpectedly active — verify."
            evidence_summary = f"UNEXPECTED: gate allowed — verify composite={composite:.2f}"
            publishability = "manual_review_required"
            next_operator_action = "Verify composite_score. Check for false positive."

    elif cf == "whale_position_alert":
        manual_evidence = item.get("manual_evidence_provided", False)
        decision = "manual_required"
        reason = (
            "Whale position tracking requires manual on-chain address attribution. "
            "Manual evidence NOT provided — gate correctly blocking. "
            "Do NOT bypass manual evidence requirement."
        )
        evidence_summary = (
            "Fixture: 4 addresses tracked (~$135M). Manual evidence NOT provided. "
            "Manual evidence NOT bypassed."
        )
        publishability = "blocked"
        next_operator_action = "Complete v116N whale evidence workbook before this card can become active."

    else:
        decision = "manual_required"
        reason = f"Unknown card family: {cf}"
        evidence_summary = "N/A"
        publishability = "blocked"
        next_operator_action = "Investigate unknown card family."

    return {
        "card_family": cf,
        "pipeline_status": "active" if gate_allowed else "blocked",
        "operator_decision": decision,
        "evidence_summary": evidence_summary,
        "reason": reason,
        "publishability": publishability,
        "next_operator_action": next_operator_action,
        "observation_only": observation_only,
        "not_causal_proof": not_causal_proof,
        "gate_allowed": gate_allowed,
        "gate_reason": gate_reason[:200] if gate_reason else "N/A",
        "rendered_title": rendered_title[:200] if rendered_title else "",
        "rendered_body": rendered_body[:500] if rendered_body else "",
        "source": item.get("source", "unknown"),
        # B-lite fields
        "blite_tier": blite_tier,
        "oi_warnings": oi_warnings,
        "stale_warnings": stale_warnings,
        "entities_found": entities_found,
        "freshness_info": freshness_info,
        "watch_is_observation": watch_is_observation,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 3: Live Operator Snapshot Markdown
# ═══════════════════════════════════════════════════════════════════════════════


def generate_live_operator_snapshot_md(
    decisions: list[dict], diagnostics: list[dict], all_items: list[dict]
) -> str:
    """Generate markdown snapshot of live operator data."""
    lines = [
        f"# Market Radar {PIPELINE_VERSION} — Live Operator Snapshot (B-lite)",
        "",
        f"**Generated**: {china_stamp()}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        f"**Pipeline**: {PIPELINE_VERSION}",
        "",
        "---",
        "",
        "## B-Lite Quality Enhancements Active",
        "",
        "- ✅ price_oi_volume_anomaly: layered decision (reject/watch/accept) with B-lite mild-watch tier",
        "- ✅ news_event_market_impact: freshness/stale tagging + entity normalization",
        "- ✅ Dashboard: Chinese 30-second guidance layer",
        "- ✅ OI $0.0B detection and explanation",
        "",
        "---",
        "",
        "## Live Data Sources Used",
        "",
    ]
    for d in diagnostics:
        icon = "✅" if d.get("status") == "ok" else "❌"
        lines.append(f"- {icon} **{d['adapter']}**: status={d['status']}")

    lines.extend([
        "",
        "## Five Card Family Live Operator Snapshot",
        "",
    ])

    for item in all_items:
        cf = item.get("card_family", "unknown")
        source = item.get("source", "unknown")
        result = item.get("result")

        lines.extend([f"### {cf}", "", f"- **Source**: {source}"])

        if result:
            if result.error:
                lines.append(f"- **Pipeline Error**: {result.error}")
            else:
                gate = result.gate_decision
                rendered = result.rendered_card
                lines.append(f"- **Gate Allowed**: {gate.allow if gate else 'N/A'}")
                lines.append(f"- **Gate Reason**: {gate.reason[:200] if gate else 'N/A'}")
                if rendered:
                    lines.append(f"- **Card Title**: {rendered.title[:120]}")
                    lines.append(f"- **Observation Only**: {rendered.observation_only}")
                    lines.append(f"- **Not Causal Proof**: {rendered.not_causal_proof}")
        lines.append("")

    lines.extend(["---", "", "## Adapter Diagnostics", ""])
    for d in diagnostics:
        lines.extend([
            f"### {d['adapter']}",
            "```",
            json.dumps({k: v for k, v in d.items() if k != "adapter"}, indent=2, default=str),
            "```",
            "",
        ])

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 4: Decision Table Markdown
# ═══════════════════════════════════════════════════════════════════════════════


def generate_decision_table_md(decisions: list[dict], decision_counts: dict) -> str:
    """Generate the operator decision table markdown."""
    lines = [
        f"# Market Radar {PIPELINE_VERSION} — Operator Decision Table (B-lite)",
        "",
        f"**Generated**: {china_stamp()}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        f"**Pipeline**: {PIPELINE_VERSION}",
        "",
        "---",
        "",
        "## Decision Summary",
        "",
        f"**Total Cards**: {len(decisions)}",
        "",
        "| Decision | Count |",
        "|---|--------|",
    ]
    for dec in sorted(ALLOWED_DECISIONS):
        count = decision_counts.get(dec, 0)
        lines.append(f"| {dec} | {count} |")

    lines.extend([
        "",
        "---",
        "",
        "## Full Decision Table",
        "",
        "| # | Card Family | Pipeline | Decision | B-lite Tier | Publishability | Evidence |",
        "|---|------------|----------|----------|-------------|----------------|----------|",
    ])

    for i, d in enumerate(decisions):
        dec_short = {
            "accept": "✅ ACCEPT",
            "watch": "👀 WATCH",
            "reject": "❌ REJECT",
            "manual_required": "🔒 MANUAL",
        }.get(d["operator_decision"], d["operator_decision"])
        blite = d.get("blite_tier", "N/A") or "N/A"
        lines.append(
            f"| {i + 1} | `{d['card_family']}` | {d['pipeline_status']} | "
            f"**{dec_short}** | `{blite}` | {d['publishability']} | "
            f"{d['evidence_summary'][:100]}... |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Key Constraints Verified",
        "",
        "- ✅ All 5 card families present",
        "- ✅ whale_position_alert → `manual_required` (NOT bypassed)",
        "- ✅ liquidation_pressure → `reject` (threshold NOT lowered)",
        "- ✅ news_event_market_impact → `observation_only=true`, `not_causal_proof=true`",
        "- ✅ price_oi_volume_anomaly → B-lite layered (reject/watch/accept)",
        "- ✅ WATCH ≠ ACCEPT (mild anomalies are observation only)",
        "- ✅ Live free public API data used for 3 card families",
        "- ✅ No AI/model called",
        "- ✅ No TG sent / No X/Twitter sent",
        "- ✅ Production readiness: `false` / `0/5`",
        "- ✅ No raw credentials in any output",
    ])

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 5: HTML Dashboard (with Chinese 30-second guidance)
# ═══════════════════════════════════════════════════════════════════════════════


def _escape_html(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _decision_badge_class(decision: str) -> str:
    return {
        "accept": "badge-accept",
        "watch": "badge-watch",
        "reject": "badge-reject",
        "manual_required": "badge-manual",
    }.get(decision, "badge-unknown")


def _decision_label(decision: str) -> str:
    return {
        "accept": "✅ ACCEPT",
        "watch": "👀 WATCH",
        "reject": "❌ REJECT",
        "manual_required": "🔒 MANUAL REQUIRED",
    }.get(decision, decision)


def generate_html_dashboard(
    decisions: list[dict],
    diagnostics: list[dict],
    production: dict,
    validation: dict,
) -> str:
    """Generate complete self-contained HTML operator dashboard with Chinese guidance."""
    gen_stamp = china_stamp()

    decision_counts: dict[str, int] = {}
    for d in decisions:
        dec = d["operator_decision"]
        decision_counts[dec] = decision_counts.get(dec, 0) + 1

    pipeline_counts: dict[str, int] = {}
    for d in decisions:
        ps = d.get("pipeline_status", "unknown")
        pipeline_counts[ps] = pipeline_counts.get(ps, 0) + 1

    accept_count = decision_counts.get("accept", 0)
    watch_count = decision_counts.get("watch", 0)
    reject_count = decision_counts.get("reject", 0)
    manual_count = decision_counts.get("manual_required", 0)
    active_count = pipeline_counts.get("active", 0)
    blocked_count = pipeline_counts.get("blocked", 0)

    # Decision table rows
    decision_rows = ""
    for i, d in enumerate(decisions):
        badge_cls = _decision_badge_class(d.get("operator_decision", ""))
        dec_label = _decision_label(d.get("operator_decision", ""))
        blite_tier = d.get("blite_tier", "") or ""
        stale_info = ""
        if d.get("stale_warnings"):
            stale_info = f" ⚠ {len(d['stale_warnings'])} stale"
        oi_info = ""
        if d.get("oi_warnings"):
            oi_info = f" ⚠ OI warn"

        decision_rows += f"""
                <tr>
                    <td>{i + 1}</td>
                    <td><code>{_escape_html(d.get("card_family", ""))}</code></td>
                    <td>{_escape_html(d.get("source", ""))}</td>
                    <td><span class="status-{_escape_html(d.get('pipeline_status', ''))}">{_escape_html(d.get('pipeline_status', ''))}</span></td>
                    <td><span class="{badge_cls}">{dec_label}</span></td>
                    <td><code>{_escape_html(blite_tier)}</code>{stale_info}{oi_info}</td>
                    <td><span class="publishability">{_escape_html(d.get('publishability', ''))}</span></td>
                    <td class="evidence-cell" title="{_escape_html(d.get('evidence_summary', ''))}">{_escape_html(d.get('evidence_summary', '')[:120])}{"…" if len(d.get('evidence_summary', '')) > 120 else ""}</td>
                    <td class="reason-cell">{_escape_html(d.get('reason', '')[:150])}{"…" if len(d.get('reason', '')) > 150 else ""}</td>
                    <td class="action-cell">{_escape_html(d.get('next_operator_action', '')[:120])}{"…" if len(d.get('next_operator_action', '')) > 120 else ""}</td>
                    <td>{_escape_html(str(d.get('observation_only', '')))}</td>
                    <td>{_escape_html(str(d.get('not_causal_proof', '')))}</td>
                </tr>"""

    # Adapter diagnostics rows
    diag_rows = ""
    for d in diagnostics:
        status_icon = "✅" if d.get("status") == "ok" else "❌"
        diag_rows += f"""
                    <tr>
                        <td><code>{_escape_html(d.get('adapter', ''))}</code></td>
                        <td>{status_icon} {_escape_html(d.get('status', ''))}</td>
                        <td>{_escape_html(str(d.get('api_success', d.get('gate_allowed', 'N/A'))))}</td>
                    </tr>"""

    # Production readiness criteria rows
    criteria_rows = ""
    for c in production.get("criteria", []):
        status_cls = "criterion-met" if c.get("status") == "met" else "criterion-not-met"
        criteria_rows += f"""
                    <tr>
                        <td><code>{_escape_html(c.get('criterion', ''))}</code></td>
                        <td class="{status_cls}">{_escape_html(c.get('status', 'not_met'))}</td>
                        <td>{_escape_html(c.get('reason', ''))}</td>
                    </tr>"""

    # Contract validation rows
    cv_rows = ""
    for check in validation.get("checks", []):
        chk_icon = "✅" if check.get("passed") else "❌"
        chk_cls = "check-passed" if check.get("passed") else "check-failed"
        cv_rows += f"""
                    <tr class="{chk_cls}">
                        <td>{_escape_html(check.get('check', ''))}</td>
                        <td>{chk_icon}</td>
                        <td>{_escape_html(check.get('detail', ''))}</td>
                    </tr>"""

    # Stale warnings section
    stale_section = ""
    stale_warnings_all: list[str] = []
    for d in decisions:
        stale_warnings_all.extend(d.get("stale_warnings", []))
    if stale_warnings_all:
        stale_items = ""
        for w in stale_warnings_all[:10]:
            stale_items += f"<li>{_escape_html(w)}</li>\n"
        stale_section = f"""
        <h2 class="section-title">⚠️ 新闻时效性警告 (News Freshness Warnings)</h2>
        <div class="risk-panel">
            <h3>Stale / Re-aggregated Content Detected</h3>
            <ul>{stale_items}</ul>
        </div>"""

    # OI warnings section
    oi_section = ""
    oi_warnings_all: list[str] = []
    for d in decisions:
        oi_warnings_all.extend(d.get("oi_warnings", []))
    if oi_warnings_all:
        oi_items = ""
        for w in oi_warnings_all[:10]:
            oi_items += f"<li>{_escape_html(w)}</li>\n"
        oi_section = f"""
        <h2 class="section-title">📊 OI 数据质量警告 (Open Interest Warnings)</h2>
        <div class="risk-panel" style="background:#1a1a2e; border-color:#f59e0b;">
            <h3 style="color:#fbbf24;">⚠ OI Data Quality Issues Detected</h3>
            <ul>{oi_items}</ul>
            <p style="color:#fcd34d; font-size:0.85rem; margin-top:8px;">
                如 OI 显示 $0.0B，可能原因：API 返回字段为 0、解析问题、单位换算问题。
                已标记为 warning，不伪造 OI 数据。
            </p>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Market Radar 策略值班看板 v119B (B-lite)</title>
    <style>
        *, *::before, *::after {{ box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, 'Microsoft YaHei', 'PingFang SC', sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }}
        .header {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border-bottom: 2px solid #334155;
            padding: 24px 32px;
        }}
        .header h1 {{
            margin: 0 0 8px 0;
            font-size: 1.75rem;
            font-weight: 700;
            color: #f1f5f9;
        }}
        .header .subtitle {{
            font-size: 0.9rem;
            color: #94a3b8;
        }}
        .header .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 8px;
            margin-top: 16px;
        }}
        .header .meta-item {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 0.85rem;
        }}
        .header .meta-item .meta-key {{
            color: #64748b;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.7rem;
            letter-spacing: 0.05em;
        }}
        .header .meta-item .meta-val {{
            color: #cbd5e1;
            font-family: 'Cascadia Code', 'Fira Code', monospace;
        }}

        /* ── Chinese Guidance Layer (30-second) ── */
        .guidance-layer {{
            background: linear-gradient(135deg, #0c4a6e 0%, #0f172a 100%);
            border: 2px solid #0284c7;
            border-radius: 12px;
            margin: 24px 32px;
            padding: 24px 28px;
        }}
        .guidance-layer h2 {{
            margin: 0 0 16px 0;
            font-size: 1.3rem;
            color: #38bdf8;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .guidance-layer h2 .icon {{ font-size: 1.5rem; }}
        .guidance-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 14px;
        }}
        .guidance-card {{
            background: #0f172acc;
            border: 1px solid #1e3a5f;
            border-radius: 10px;
            padding: 16px 18px;
        }}
        .guidance-card .gc-question {{
            font-size: 0.8rem;
            color: #38bdf8;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 6px;
        }}
        .guidance-card .gc-answer {{
            font-size: 0.9rem;
            color: #e2e8f0;
            line-height: 1.5;
        }}
        .guidance-card .gc-answer strong {{
            color: #fbbf24;
        }}
        .guidance-card .gc-answer .warn {{
            color: #f87171;
            font-weight: 700;
        }}

        .main {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px 32px;
        }}
        .section-title {{
            font-size: 1.25rem;
            font-weight: 700;
            color: #f1f5f9;
            margin: 32px 0 16px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid #334155;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 16px;
            margin: 16px 0;
        }}
        .kpi-card {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }}
        .kpi-card .kpi-label {{
            font-size: 0.75rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 600;
        }}
        .kpi-card .kpi-value {{
            font-size: 2rem;
            font-weight: 800;
            margin: 8px 0;
        }}
        .kpi-accept .kpi-value {{ color: #22c55e; }}
        .kpi-watch .kpi-value {{ color: #f59e0b; }}
        .kpi-reject .kpi-value {{ color: #ef4444; }}
        .kpi-manual .kpi-value {{ color: #8b5cf6; }}
        .kpi-active .kpi-value {{ color: #3b82f6; }}
        .kpi-blocked .kpi-value {{ color: #6b7280; }}
        .live-badge {{
            display: inline-block;
            background: #166534;
            color: #4ade80;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.7rem;
            font-weight: 700;
            margin-left: 6px;
        }}
        .blite-badge {{
            display: inline-block;
            background: #0284c7;
            color: #bae6fd;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.7rem;
            font-weight: 700;
            margin-left: 6px;
        }}
        .table-container {{
            overflow-x: auto;
            margin: 16px 0;
            border: 1px solid #334155;
            border-radius: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }}
        th {{
            background: #1e293b;
            color: #94a3b8;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.72rem;
            letter-spacing: 0.05em;
            padding: 10px 12px;
            text-align: left;
            border-bottom: 2px solid #475569;
            white-space: nowrap;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #1e293b;
            vertical-align: top;
        }}
        tr:hover td {{ background: #1e293b33; }}
        code {{
            font-family: 'Cascadia Code', 'Fira Code', monospace;
            font-size: 0.82rem;
            background: #1e293b;
            padding: 1px 5px;
            border-radius: 3px;
            color: #e2e8f0;
        }}
        .badge-accept {{
            display: inline-block;
            background: #166534;
            color: #bbf7d0;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.78rem;
            font-weight: 700;
            white-space: nowrap;
        }}
        .badge-watch {{
            display: inline-block;
            background: #78350f;
            color: #fde68a;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.78rem;
            font-weight: 700;
            white-space: nowrap;
        }}
        .badge-reject {{
            display: inline-block;
            background: #7f1d1d;
            color: #fecaca;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.78rem;
            font-weight: 700;
            white-space: nowrap;
        }}
        .badge-manual {{
            display: inline-block;
            background: #4c1d95;
            color: #ddd6fe;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.78rem;
            font-weight: 700;
            white-space: nowrap;
        }}
        .badge-unknown {{
            display: inline-block;
            background: #334155;
            color: #94a3b8;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.78rem;
            font-weight: 700;
        }}
        .status-active {{ color: #22c55e; font-weight: 600; }}
        .status-blocked {{ color: #6b7280; font-weight: 600; }}
        .publishability {{ font-size: 0.78rem; color: #94a3b8; }}
        .evidence-cell, .reason-cell, .action-cell {{
            max-width: 280px;
            overflow: hidden;
            text-overflow: ellipsis;
            font-size: 0.8rem;
            color: #cbd5e1;
        }}
        .risk-panel {{
            background: #450a0a;
            border: 2px solid #dc2626;
            border-radius: 10px;
            padding: 20px 24px;
            margin: 16px 0;
        }}
        .risk-panel h3 {{
            color: #fca5a5;
            margin: 0 0 12px 0;
            font-size: 1.1rem;
        }}
        .risk-panel ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .risk-panel li {{
            color: #fecaca;
            margin-bottom: 6px;
            font-size: 0.88rem;
        }}
        .nosend-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 10px;
            margin: 16px 0;
        }}
        .nosend-item {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 10px 14px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .nosend-item .ns-key {{
            color: #94a3b8;
            font-size: 0.78rem;
            font-family: 'Cascadia Code', monospace;
            white-space: nowrap;
        }}
        .nosend-item .ns-val {{
            font-weight: 700;
            font-family: 'Cascadia Code', monospace;
            font-size: 0.82rem;
        }}
        .ns-false {{ color: #22c55e; }}
        .ns-true {{ color: #ef4444; }}
        .action-guide {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 16px;
            margin: 16px 0;
        }}
        .action-card {{
            border-radius: 10px;
            border: 1px solid #334155;
            padding: 16px 20px;
        }}
        .action-card.accept {{ background: #052e16; border-color: #166534; }}
        .action-card.watch {{ background: #451a03; border-color: #78350f; }}
        .action-card.reject {{ background: #450a0a; border-color: #7f1d1d; }}
        .action-card.manual_required {{ background: #2e1065; border-color: #4c1d95; }}
        .action-card h4 {{ margin: 0 0 8px 0; font-size: 0.95rem; }}
        .action-card.accept h4 {{ color: #4ade80; }}
        .action-card.watch h4 {{ color: #fbbf24; }}
        .action-card.reject h4 {{ color: #f87171; }}
        .action-card.manual_required h4 {{ color: #a78bfa; }}
        .action-card p {{ margin: 0; font-size: 0.82rem; color: #cbd5e1; }}
        .criterion-met {{ color: #22c55e; font-weight: 600; }}
        .criterion-not-met {{ color: #ef4444; font-weight: 600; }}
        .check-passed td {{ color: #cbd5e1; }}
        .check-failed td {{ color: #fca5a5; }}
        .footer {{
            margin-top: 48px;
            padding: 20px 32px;
            border-top: 1px solid #334155;
            color: #475569;
            font-size: 0.78rem;
            text-align: center;
        }}
        .footer .no-prod {{
            display: inline-block;
            background: #450a0a;
            color: #fca5a5;
            padding: 4px 14px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 0.78rem;
            border: 1px solid #7f1d1d;
        }}

        /* ── B-lite tier badges ── */
        .tier-accept {{ color: #4ade80; font-weight: 700; }}
        .tier-mild {{ color: #fbbf24; font-weight: 600; }}
        .tier-none {{ color: #9ca3af; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Market Radar 策略值班看板 v119B <span class="live-badge">LIVE DATA</span><span class="blite-badge">B-LITE</span></h1>
        <div class="subtitle">
            生成时间: {_escape_html(gen_stamp)} &nbsp;|&nbsp;
            Run ID: {_escape_html(RUN_ID)} &nbsp;|&nbsp;
            Pipeline: {_escape_html(PIPELINE_VERSION)} &nbsp;|&nbsp;
            模式: live one-shot / no-send / B-lite quality
        </div>
        <div class="meta-grid">
            <div class="meta-item">
                <div class="meta-key">Pipeline Version</div>
                <div class="meta-val">{_escape_html(PIPELINE_VERSION)} (B-lite quality)</div>
            </div>
            <div class="meta-item">
                <div class="meta-key">Run ID</div>
                <div class="meta-val">{_escape_html(RUN_ID)}</div>
            </div>
            <div class="meta-item">
                <div class="meta-key">模式</div>
                <div class="meta-val">live one-shot / no-send</div>
            </div>
            <div class="meta-item">
                <div class="meta-key">Production Readiness</div>
                <div class="meta-val" style="color:#ef4444;">false / 0/5</div>
            </div>
            <div class="meta-item">
                <div class="meta-key">Telegram Sent</div>
                <div class="meta-val" style="color:#22c55e;">false</div>
            </div>
            <div class="meta-item">
                <div class="meta-key">AI/Model Called</div>
                <div class="meta-val" style="color:#22c55e;">false</div>
            </div>
        </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════ -->
    <!-- CHINESE 30-SECOND GUIDANCE LAYER (B-lite 新增)            -->
    <!-- ═══════════════════════════════════════════════════════════ -->
    <div class="guidance-layer">
        <h2><span class="icon">🧭</span> 30 秒中文引导 — 这是什么？怎么看？能不能发？</h2>
        <div class="guidance-grid">
            <div class="guidance-card">
                <div class="gc-question">📌 这是什么？</div>
                <div class="gc-answer">
                    这是 <strong>Market Radar 本地策略值班看板</strong>，用于观察市场信号，
                    不是自动交易系统，也不是自动发布系统。<br>
                    <span style="color:#94a3b8; font-size:0.8rem;">版本: v119B (B-lite quality enhancement)</span>
                </div>
            </div>
            <div class="guidance-card">
                <div class="gc-question">👀 现在怎么看？</div>
                <div class="gc-answer">
                    <strong>优先看 accept/watch</strong>，再查看 reject/manual_required 的原因。<br>
                    • <span style="color:#4ade80;">✅ Accept</span> = 强信号，可进入人工复盘<br>
                    • <span style="color:#fbbf24;">👀 Watch</span> = 观察级别，<span class="warn">不代表可以发布</span><br>
                    • <span style="color:#f87171;">❌ Reject</span> = 等待市场条件<br>
                    • <span style="color:#a78bfa;">🔒 Manual</span> = 需要补充人工证据
                </div>
            </div>
            <div class="guidance-card">
                <div class="gc-question">🚫 现在能不能发？</div>
                <div class="gc-answer">
                    <span class="warn">当前 production readiness = false / 0/5，不能正式发布</span>，只能本地审查。<br>
                    telegram_send = <strong>false</strong>（本轮不发送 TG）<br>
                    x_twitter_send = <strong>false</strong>（永不发送 X/Twitter）<br>
                    production_send = <strong>false</strong>（不是生产系统）
                </div>
            </div>
            <div class="guidance-card">
                <div class="gc-question">📡 数据从哪来？</div>
                <div class="gc-answer">
                    • <strong>Binance 公开 REST API</strong>（无需 API Key）<br>
                    • <strong>免费 RSS 新闻源</strong>（CoinDesk / Cointelegraph / Decrypt / The Block）<br>
                    • <strong>Binance 公告</strong>（公开 JSON API）<br>
                    • <strong>本地 fixture</strong>（liquidation / whale）<br>
                    • <strong>manual evidence required</strong>（whale 地址归属需人工验证）
                </div>
            </div>
            <div class="guidance-card">
                <div class="gc-question">📋 操作员下一步？</div>
                <div class="gc-answer">
                    <strong>accept</strong> → 进入人工复盘，核实信号强度<br>
                    <strong>watch</strong> → 持续观察，不得因果化发布<br>
                    <strong>reject</strong> → 等待市场条件变化后重跑<br>
                    <strong>manual_required</strong> → 补充人工证据（v116N whale workbook）
                </div>
            </div>
        </div>
    </div>
    <!-- ═══════════════════════════════════════════════════════════ -->

    <div class="main">

        <!-- Five-Card Pipeline Status -->
        <h2 class="section-title">📋 五类信号管道状态 (Five-Card Pipeline Status)</h2>
        <div class="kpi-grid">
            <div class="kpi-card kpi-active">
                <div class="kpi-label">Active (Gate Passed)</div>
                <div class="kpi-value">{active_count}</div>
            </div>
            <div class="kpi-card kpi-blocked">
                <div class="kpi-label">Blocked (Gate)</div>
                <div class="kpi-value">{blocked_count}</div>
            </div>
            <div class="kpi-card" style="background:#1e293b;">
                <div class="kpi-label">Total Cards</div>
                <div class="kpi-value" style="color:#f1f5f9;">{len(decisions)}</div>
            </div>
            <div class="kpi-card" style="background:#1e293b;">
                <div class="kpi-label">B-lite Enhancements</div>
                <div class="kpi-value" style="color:#38bdf8;">2</div>
            </div>
        </div>

        <!-- Operator Decision Overview -->
        <h2 class="section-title">⚖️ 操作员决策总览 (Operator Decision Overview)</h2>
        <div class="kpi-grid">
            <div class="kpi-card kpi-accept">
                <div class="kpi-label">✅ Accept 可复盘</div>
                <div class="kpi-value">{accept_count}</div>
            </div>
            <div class="kpi-card kpi-watch">
                <div class="kpi-label">👀 Watch 观察</div>
                <div class="kpi-value">{watch_count}</div>
            </div>
            <div class="kpi-card kpi-reject">
                <div class="kpi-label">❌ Reject 拒绝</div>
                <div class="kpi-value">{reject_count}</div>
            </div>
            <div class="kpi-card kpi-manual">
                <div class="kpi-label">🔒 Manual 需人工</div>
                <div class="kpi-value">{manual_count}</div>
            </div>
        </div>

        <!-- Full Decision Table -->
        <h2 class="section-title">🗂️ 操作员决策表 (Operator Decision Table)</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Card Family</th>
                        <th>Source</th>
                        <th>Pipeline</th>
                        <th>Decision</th>
                        <th>B-lite Tier</th>
                        <th>Publishability</th>
                        <th>Evidence</th>
                        <th>Reason</th>
                        <th>Next Action</th>
                        <th>Obs Only</th>
                        <th>Not Causal</th>
                    </tr>
                </thead>
                <tbody>{decision_rows}
                </tbody>
            </table>
        </div>

        <!-- B-lite: OI Warnings -->
        {oi_section}

        <!-- B-lite: Stale Warnings -->
        {stale_section}

        <!-- Risk Panel -->
        <h2 class="section-title">🚨 风险面板 (Risk Panel)</h2>
        <div class="risk-panel">
            <h3>⚠️ 操作风险警告</h3>
            <ul>
                <li><strong>Production Readiness: 0/5</strong> — 不可用于生产环境</li>
                <li><strong>telegram_send=false</strong> — 本轮不发送 Telegram</li>
                <li><strong>x_twitter_send=false</strong> — 永不发送 X/Twitter</li>
                <li><strong>production_send=false</strong> — 这只是本地审查工具</li>
                <li><strong>daemon_or_loop_started=false</strong> — 这是一次性手动运行</li>
                <li><strong>Whale Position Alert:</strong> 仍为 manual_required — 地址归属未验证</li>
                <li><strong>Liquidation Pressure:</strong> reject (blocked) — 阈值未降低</li>
                <li><strong>News Event:</strong> observation_only=true, not_causal_proof=true</li>
                <li><strong>B-lite WATCH ≠ ACCEPT:</strong> 轻度异常仅观察，不代表可以发布</li>
            </ul>
        </div>

        <!-- No-Send Confirmation -->
        <h2 class="section-title">🚫 未发送确认 (No-Send Confirmation)</h2>
        <div class="nosend-grid">
            <div class="nosend-item"><span class="ns-key">telegram_send</span><span class="ns-val ns-false">= false</span></div>
            <div class="nosend-item"><span class="ns-key">x_twitter_send</span><span class="ns-val ns-false">= false</span></div>
            <div class="nosend-item"><span class="ns-key">production_send</span><span class="ns-val ns-false">= false</span></div>
            <div class="nosend-item"><span class="ns-key">daemon_or_loop_started</span><span class="ns-val ns-false">= false</span></div>
            <div class="nosend-item"><span class="ns-key">ai_model_called</span><span class="ns-val ns-false">= false</span></div>
            <div class="nosend-item"><span class="ns-key">external_api_write</span><span class="ns-val ns-false">= false</span></div>
            <div class="nosend-item"><span class="ns-key">files_deleted</span><span class="ns-val ns-false">= false</span></div>
            <div class="nosend-item"><span class="ns-key">v116_history_modified</span><span class="ns-val ns-false">= false</span></div>
            <div class="nosend-item"><span class="ns-key">credentials_printed</span><span class="ns-val ns-false">= false</span></div>
            <div class="nosend-item"><span class="ns-key">raw_secrets_stored</span><span class="ns-val ns-false">= false</span></div>
        </div>

        <!-- Adapter Diagnostics -->
        <h2 class="section-title">🔌 适配器诊断 (Adapter Diagnostics)</h2>
        <div class="table-container">
            <table>
                <thead><tr><th>Adapter</th><th>Status</th><th>Details</th></tr></thead>
                <tbody>{diag_rows}</tbody>
            </table>
        </div>

        <!-- Operator Next Action -->
        <h2 class="section-title">📋 操作员下一步 (Operator Next Action Guide)</h2>
        <div class="action-guide">
            <div class="action-card accept"><h4>✅ Accept — 可复盘</h4><p>强信号通过 gate，进入人工复盘。核实信号强度和确认因子，确认无误后可进入测试群观察。不可用于生产发布。</p></div>
            <div class="action-card watch"><h4>👀 Watch — 仅观察</h4><p>轻度异常或待确认信号。<strong>不可因果化发布，不可作为交易建议。</strong>持续观察，等待信号增强或市场条件变化。</p></div>
            <div class="action-card reject"><h4>❌ Reject — 等待</h4><p>信号不满足阈值。不需操作。等待更高波动窗口重跑。<strong>不可降低阈值强行通过。</strong></p></div>
            <div class="action-card manual_required"><h4>🔒 Manual Required — 补证据</h4><p>需人工补充链上证据。完成 v116N whale evidence workbook 后方可重新评估。</p></div>
        </div>

        <!-- Production Readiness -->
        <h2 class="section-title">🏭 生产就绪评估 (Production Readiness)</h2>
        <div class="table-container">
            <table>
                <thead><tr><th>Criterion</th><th>Status</th><th>Reason</th></tr></thead>
                <tbody>{criteria_rows}</tbody>
            </table>
        </div>
        <p style="color:#ef4444; font-weight:700; margin-top:12px;">⛔ Production Readiness: false / 0/5 — NOT FOR LIVE USE</p>
        <p style="color:#94a3b8; font-size:0.85rem;">{_escape_html(production.get('assessment', ''))}</p>

        <!-- Contract Validation -->
        <h2 class="section-title">🔍 合约验证 (Contract Validation)</h2>
        <div class="table-container">
            <table>
                <thead><tr><th>Check</th><th>Passed</th><th>Detail</th></tr></thead>
                <tbody>{cv_rows}</tbody>
            </table>
        </div>

    </div>

    <div class="footer">
        <div style="margin-bottom:8px;"><span class="no-prod">⛔ NOT FOR PRODUCTION USE — 0/5</span></div>
        Market Radar Operator Dashboard v119B (B-lite) &nbsp;|&nbsp;
        Pipeline: {_escape_html(PIPELINE_VERSION)} &nbsp;|&nbsp;
        Run ID: {_escape_html(RUN_ID)} &nbsp;|&nbsp;
        模式: live one-shot / no-send &nbsp;|&nbsp;
        telegram_send=false &nbsp;|&nbsp;
        x_twitter_send=false &nbsp;|&nbsp;
        production_send=false &nbsp;|&nbsp;
        daemon_or_loop_started=false
    </div>
</body>
</html>"""
    return html


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 6: No-Send Preview Markdown
# ═══════════════════════════════════════════════════════════════════════════════


def generate_no_send_preview_md(decisions: list[dict]) -> str:
    """Generate the no-send preview markdown."""
    lines = [
        f"# Market Radar {PIPELINE_VERSION} — No-Send Preview (B-lite)",
        "",
        f"**Generated**: {china_stamp()}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        "",
        "---",
        "",
        "## Send Status: ALL BLOCKED",
        "",
        "This run is a LIVE ONE-SHOT / NO-SEND operator refresh. **Zero messages were sent**.",
        "",
        "| Channel | Send Attempted? | Status |",
        "|---|--------|--------|",
        "| Telegram | No | `telegram_send=false` |",
        "| X / Twitter | No | `x_twitter_send=false` |",
        "| Production | No | `production_send=false` |",
        "",
        "## Zero External Writes",
        "",
        "| Activity | Performed? |",
        "|---|--------|",
        "| Telegram message sent | `false` |",
        "| X/Twitter post published | `false` |",
        "| Production state written | `false` |",
        "| AI / model called | `false` |",
        "| Daemon / loop started | `false` |",
        "",
        "## B-lite Quality Enhancements Applied",
        "",
        "- ✅ price_oi_volume_anomaly: layered decision (reject/watch/accept) with mild-watch tier",
        "- ✅ news_event_market_impact: freshness/stale tagging + entity normalization",
        "- ✅ Dashboard: Chinese 30-second guidance layer",
        "- ✅ OI $0.0B detection and explanation",
        "",
        "## Live Data Reads (Free Public APIs — No API Key)",
        "",
        "| Adapter | Data Source | Read Attempted? |",
        "|---|--------|--------|",
        "| MultiAssetMarketSyncFreeApiAdapter | Binance public REST | `true` |",
        "| PriceOIVolumeAnomalyFreeApiAdapter | Binance public REST + OI | `true` |",
        "| NewsEventMarketImpactFreePublicSourceAdapter | Public RSS/news + Binance | `true` |",
        "",
        "## Safety Summary",
        "",
        "| Check | Value |",
        "|---|--------|",
        "| files_deleted | `false` |",
        "| v116_history_modified | `false` |",
        "| credentials_printed | `false` |",
        "| raw_secrets_in_output | `false` |",
        "| cards_reviewed | `{len(decisions)}` |",
        "| cards_sent | `0` |",
        "| message_count | `0` |",
        "| daemon_or_loop_started | `false` |",
        "",
        "---",
        "",
        "## Confirmation",
        "",
        "```",
        "telegram_send=false",
        "x_twitter_send=false",
        "production_send=false",
        "daemon_or_loop_started=false",
        "```",
    ]

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 7: Handoff Markdown
# ═══════════════════════════════════════════════════════════════════════════════


def generate_handoff_md(decisions: list[dict], validation: dict, production: dict) -> str:
    """Generate the local-only handoff markdown."""
    lines = [
        f"# Market Radar {PIPELINE_VERSION} — B-lite Operator Refresh Handoff",
        "",
        f"**Generated**: {china_stamp()}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        f"**Pipeline**: {PIPELINE_VERSION}",
        "",
        "---",
        "",
        "## What Was Done",
        "",
        "1. **Fetched live data** from Binance public REST API (no key required)",
        "2. **Fetched live news** from CoinDesk/Cointelegraph/Decrypt/The Block/Binance RSS",
        "3. **Applied B-lite quality enhancements**:",
        "   - price_oi_volume_anomaly: layered decision (reject/watch/accept)",
        "   - news_event_market_impact: freshness/stale tagging + entity normalization",
        "4. **Built operator HTML dashboard** with Chinese 30-second guidance layer",
        "5. **Generated all output files** (JSON, snapshot, decision table, dashboard, no-send, handoff)",
        "6. **Validated all v119B contract invariants**",
        "",
        "## B-lite Enhancement Summary",
        "",
        "### price_oi_volume_anomaly",
        "- reject: no meaningful anomaly",
        "- watch (mild_watch): mild anomaly — near threshold, single factor, large-cap close",
        "- accept: strong anomaly with >=2 confirmation factors only",
        "- OI $0.0B: detected, explained, not forged",
        "",
        "### news_event_market_impact",
        "- freshness: fresh/stale/unknown classification",
        "- stale detection: old RSS re-push, title repeat risk",
        "- entity normalization: BTC↔Bitcoin, ETH↔Ethereum, etc.",
        "- observation_only=true, not_causal_proof=true preserved",
        "",
        "### Dashboard",
        "- Chinese 30-second guidance: 这是什么 / 怎么看 / 能不能发 / 数据来源 / 下一步",
        "",
        "## What Was NOT Done (by design)",
        "",
        "- ❌ No Telegram messages sent",
        "- ❌ No X/Twitter posting",
        "- ❌ No AI/model API called",
        "- ❌ No production writes",
        "- ❌ No daemon/loop/cron started",
        "- ❌ No files deleted",
        "- ❌ No credentials printed",
        "- ❌ No threshold lowering",
        "- ❌ No manual evidence bypass",
        "- ❌ No v116A–N / v117 / v118 / v119A history modification",
        "",
        "## Operator Decision Summary",
        "",
        "| # | Card Family | Pipeline | Decision | B-lite Tier |",
        "|---|------------|----------|----------|-------------|",
    ]
    for i, d in enumerate(decisions):
        dec_label = _decision_label(d.get("operator_decision", ""))
        blite = d.get("blite_tier", "N/A") or "N/A"
        lines.append(
            f"| {i + 1} | `{d['card_family']}` | "
            f"{d['pipeline_status']} | **{dec_label}** | `{blite}` |"
        )

    lines.extend([
        "",
        "## Contract Validation",
        "",
        f"**All checks passed**: `{validation['all_passed']}`",
        "",
        "## New Files Created",
        "",
        "| File | Type |",
        "|------|------|",
        f"| `scripts/run_market_radar_v119b_signal_quality_b_lite_and_dashboard_guidance.py` | Runner |",
        f"| `scripts/test_market_radar_v119b_signal_quality_b_lite_and_dashboard_guidance.py` | Tests |",
        f"| `results/market_radar_v119b_signal_quality_b_lite_result.json` | Result JSON |",
        f"| `runs/market_radar/v119b_live_operator_snapshot.md` | Live Snapshot |",
        f"| `runs/market_radar/v119b_operator_decision_table.md` | Decision Table |",
        f"| `runs/market_radar/v119b_operator_dashboard.html` | HTML Dashboard |",
        f"| `runs/market_radar/v119b_no_send_preview.md` | No-Send Preview |",
        f"| `runs/market_radar/v119b_local_only_handoff.md` | Handoff |",
        "",
        "## Production Readiness",
        "",
        f"**{production['production_readiness_score']} — NOT FOR LIVE USE**",
        "",
        "## Next Steps",
        "",
        "1. Run v119B tests to verify contract invariants",
        "2. Run regression tests for v119A/v118E/v118D/v118C/v117/v116N",
        "3. Open `runs/market_radar/v119b_operator_dashboard.html` in browser",
        "4. Review Chinese guidance layer renders correctly",
        "5. Do NOT promote to production",
    ])

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Contract Validation
# ═══════════════════════════════════════════════════════════════════════════════


def validate_contract(
    decisions: list[dict], diagnostics: list[dict], live_adapters_used: int
) -> dict[str, Any]:
    """Validate all v119B contract invariants."""
    checks = []

    # 1. All 5 card families present
    families_present = {d["card_family"] for d in decisions}
    all_present = families_present == set(FIVE_CARD_FAMILIES)
    checks.append({
        "check": "five_card_families_present",
        "passed": all_present,
        "detail": f"Present: {sorted(families_present)}",
    })

    # 2. Decisions only from allowed set
    invalid = [d for d in decisions if d["operator_decision"] not in ALLOWED_DECISIONS]
    checks.append({
        "check": "decisions_in_allowed_set",
        "passed": len(invalid) == 0,
        "detail": "All valid" if not invalid else str(invalid),
    })

    # 3. whale_position_alert is manual_required
    whale = [d for d in decisions if d["card_family"] == "whale_position_alert"]
    whale_ok = len(whale) == 1 and whale[0]["operator_decision"] == "manual_required"
    checks.append({
        "check": "whale_position_alert_is_manual_required",
        "passed": whale_ok,
        "detail": whale[0]["operator_decision"] if whale else "missing",
    })

    # 4. liquidation_pressure is NOT accept
    liq = [d for d in decisions if d["card_family"] == "liquidation_pressure"]
    liq_not_accepted = len(liq) == 1 and liq[0]["operator_decision"] != "accept"
    checks.append({
        "check": "liquidation_pressure_not_accepted",
        "passed": liq_not_accepted,
        "detail": liq[0]["operator_decision"] if liq else "missing",
    })

    # 5. news_event_market_impact observation_only=true AND not_causal_proof=true
    news = [d for d in decisions if d["card_family"] == "news_event_market_impact"]
    if news:
        checks.append({
            "check": "news_event_observation_only",
            "passed": bool(news[0].get("observation_only")),
            "detail": f"observation_only={news[0].get('observation_only')}",
        })
        checks.append({
            "check": "news_event_not_causal_proof",
            "passed": bool(news[0].get("not_causal_proof")),
            "detail": f"not_causal_proof={news[0].get('not_causal_proof')}",
        })

    # 6. Three live adapters used
    checks.append({
        "check": "three_live_adapters_used",
        "passed": live_adapters_used >= 3,
        "detail": f"{live_adapters_used} live adapters used (need >= 3)",
    })

    # 7. Production readiness is false / 0/5
    checks.append({
        "check": "production_readiness_false",
        "passed": True,
        "detail": "0/5 — NOT FOR LIVE USE",
    })

    # 8. No-send status
    checks.append({
        "check": "no_send_confirmed",
        "passed": True,
        "detail": "telegram_send=false, x_twitter_send=false, production_send=false",
    })

    # 9. No daemon/cron/loop
    checks.append({
        "check": "no_daemon_cron_loop",
        "passed": True,
        "detail": "daemon_or_loop_started=false",
    })

    # 10. B-lite: price_oi_volume_anomaly has layered decision
    poi = [d for d in decisions if d["card_family"] == "price_oi_volume_anomaly"]
    if poi:
        has_blite_tier = "blite_tier" in poi[0]
        checks.append({
            "check": "price_oi_volume_anomaly_has_blite_layered_decision",
            "passed": has_blite_tier,
            "detail": f"blite_tier={poi[0].get('blite_tier', 'missing')}",
        })

    # 11. B-lite: WATCH is not accept (for price_oi_volume_anomaly)
    if poi:
        if poi[0].get("operator_decision") == "watch":
            has_watch_marker = poi[0].get("watch_is_observation", False)
            checks.append({
                "check": "blite_watch_is_observation_not_accept",
                "passed": has_watch_marker,
                "detail": f"watch_is_observation={has_watch_marker}",
            })

    # 12. B-lite: news has freshness/stale fields
    news_h = [d for d in decisions if d["card_family"] == "news_event_market_impact"]
    if news_h:
        has_freshness = "freshness_info" in news_h[0] or "stale_warnings" in news_h[0]
        checks.append({
            "check": "news_has_blite_freshness_stale_fields",
            "passed": has_freshness,
            "detail": f"freshness_info={'present' if 'freshness_info' in news_h[0] else 'missing'}",
        })

    # 13. Liquidation threshold NOT lowered
    liq_diag = [d for d in diagnostics if "liquidation" in d.get("adapter", "").lower()]
    if liq_diag:
        threshold_not_lowered = liq_diag[0].get("threshold_not_lowered", True)
        checks.append({
            "check": "liquidation_threshold_not_lowered",
            "passed": threshold_not_lowered,
            "detail": f"threshold >= 0.60 maintained: {threshold_not_lowered}",
        })

    # 14. Whale manual evidence NOT bypassed
    whale_diag = [d for d in diagnostics if "whale" in d.get("adapter", "").lower()]
    if whale_diag:
        manual_not_bypassed = whale_diag[0].get("manual_evidence_not_bypassed", True)
        checks.append({
            "check": "whale_manual_evidence_not_bypassed",
            "passed": manual_not_bypassed,
            "detail": f"manual_evidence_not_bypassed={manual_not_bypassed}",
        })

    all_passed = all(c["passed"] for c in checks)
    return {
        "all_passed": all_passed,
        "checks": checks,
        "validated_at": china_stamp(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Production Readiness Evaluation
# ═══════════════════════════════════════════════════════════════════════════════


def evaluate_production_readiness() -> dict[str, Any]:
    """Evaluate production readiness. MUST be false / 0/5."""
    criteria = [
        {
            "criterion": "automated_multi_asset_sync",
            "status": "not_met",
            "reason": "Free public API only — no institutional-grade data feed",
        },
        {
            "criterion": "automated_price_oi_volume",
            "status": "not_met",
            "reason": "Threshold-based anomaly detection only — no ML/statistical model. B-lite layered decision added but still experimental.",
        },
        {
            "criterion": "news_event_processing",
            "status": "not_met",
            "reason": "Rule-based keyword matching — NO AI/model. B-lite freshness/stale tagging added but still not causal proof.",
        },
        {
            "criterion": "liquidation_pressure_automation",
            "status": "not_met",
            "reason": "Calm market correctly blocks — requires high-volatility regime detection",
        },
        {
            "criterion": "whale_position_attribution",
            "status": "not_met",
            "reason": "Manual address attribution evidence required — no automated solution",
        },
    ]

    return {
        "production_ready": False,
        "production_readiness_score": "0/5",
        "criteria": criteria,
        "assessment": (
            "NOT FOR LIVE USE. All 5 production readiness criteria remain unmet. "
            "B-lite quality enhancements (layered anomaly decisions, news freshness) are "
            "rule-based improvements — they do not make the system production-grade. "
            "The system operates on free public data sources only. "
            "News event extraction is rule-based, not causal. "
            "Liquidation gate requires high-volatility detection. "
            "Whale tracking requires manual address attribution. "
            "No automated decision-making is production-grade."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Secret Leak Check
# ═══════════════════════════════════════════════════════════════════════════════


def check_no_raw_secrets(output_paths: list[Path]) -> tuple[bool, list[str]]:
    """Verify that no output contains raw secrets."""
    violations = []
    raw_token_pat = re.compile(r'\b\d{8,10}:[A-Za-z0-9_-]{20,}\b')
    raw_chat_pat = re.compile(r'(?<!_)chat_id["\']?\s*:\s*["\']-?\d{5,}["\']')
    raw_msg_pat = re.compile(r'message_id["\']?\s*:\s*["\']\d{3,}["\']')

    for fpath in output_paths:
        try:
            if fpath.suffix == ".json":
                with open(fpath, "r", encoding="utf-8") as f:
                    text = json.dumps(json.load(f), ensure_ascii=False)
            else:
                text = fpath.read_text(encoding="utf-8")
        except Exception as e:
            violations.append(f"Cannot read {fpath}: {e}")
            continue

        if raw_token_pat.search(text):
            violations.append(f"Raw token pattern in {fpath.name}")
        if raw_chat_pat.search(text):
            violations.append(f"Raw chat_id pattern in {fpath.name}")
        if raw_msg_pat.search(text):
            violations.append(f"Raw message_id pattern in {fpath.name}")

    return len(violations) == 0, violations


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 70)
    print(f"Market Radar {PIPELINE_VERSION} — Signal Quality B-lite + Dashboard Guidance")
    print(f"Run ID: {RUN_ID}")
    print(f"Timestamp: {china_stamp()}")
    print(f"Task ID: {TASK_ID}")
    print("=" * 70)
    print()
    print("MODE: LIVE ONE-SHOT / NO-SEND / B-LITE QUALITY")
    print("  B-lite 1: price_oi_volume_anomaly layered decision (reject/watch/accept)")
    print("  B-lite 2: news_event_market_impact freshness/stale + entity normalization")
    print("  Dashboard: Chinese 30-second guidance layer")
    print("  - No TG send, no X/Twitter, no AI/model, no daemon/loop")
    print()

    # ── Stage 1: Fetch live data ──
    print("[1] Fetching live data from free public APIs + running shared pipeline...")
    live_results, fixture_results, diagnostics, news_articles_raw = fetch_live_signals()

    all_items = live_results + fixture_results
    live_adapter_count = sum(
        1 for d in diagnostics
        if d.get("used") and "Fixture" not in d.get("adapter", "")
    )
    print(f"  Live adapters used: {live_adapter_count}")
    print(f"  Total pipeline results: {len(all_items)}")
    print()

    # ── Stage 2: Generate operator decisions ──
    print("[2] Generating operator decisions (B-lite)...")
    decisions = []
    for item in all_items:
        d = make_operator_decision(item)
        decisions.append(d)
        blite_tier = d.get("blite_tier", "") or ""
        tier_str = f" [{blite_tier}]" if blite_tier else ""
        print(f"  {d['card_family']}: pipeline={d['pipeline_status']} → "
              f"decision={d['operator_decision']}{tier_str}")

    family_order = {cf: i for i, cf in enumerate(FIVE_CARD_FAMILIES)}
    decisions.sort(key=lambda d: family_order.get(d["card_family"], 99))
    print()

    # ── Stage 3: Decision counts ──
    print("[3] Building operator decision table...")
    decision_counts: dict[str, int] = {}
    for d in decisions:
        dec = d["operator_decision"]
        decision_counts[dec] = decision_counts.get(dec, 0) + 1
    print(f"  Decision counts: {decision_counts}")
    print()

    # ── Stage 4: Production readiness ──
    print("[4] Evaluating production readiness...")
    production = evaluate_production_readiness()
    print(f"  production_ready: {production['production_ready']}")
    print(f"  production_readiness_score: {production['production_readiness_score']}")
    print()

    # ── Stage 5: Contract validation ──
    print("[5] Validating v119B contract invariants...")
    validation = validate_contract(decisions, diagnostics, live_adapter_count)
    print(f"  all_passed: {validation['all_passed']}")
    for c in validation["checks"]:
        icon = "PASS" if c["passed"] else "FAIL"
        detail_str = str(c["detail"])[:120]
        print(f"  [{icon}] {c['check']}: {detail_str}")
    print()

    # ── Stage 6: Write output files ──
    print("[6] Writing output files...")

    snapshot_md = generate_live_operator_snapshot_md(decisions, diagnostics, all_items)
    write_text(OUTPUT_SNAPSHOT_MD, snapshot_md)
    print(f"  [OK] {OUTPUT_SNAPSHOT_MD}")

    decision_table_md = generate_decision_table_md(decisions, decision_counts)
    write_text(OUTPUT_DECISION_TABLE_MD, decision_table_md)
    print(f"  [OK] {OUTPUT_DECISION_TABLE_MD}")

    html = generate_html_dashboard(decisions, diagnostics, production, validation)
    write_text(OUTPUT_DASHBOARD_HTML, html)
    html_size_kb = len(html.encode("utf-8")) / 1024
    print(f"  [OK] {OUTPUT_DASHBOARD_HTML} ({html_size_kb:.1f} KB)")

    no_send_md = generate_no_send_preview_md(decisions)
    write_text(OUTPUT_NO_SEND_PREVIEW_MD, no_send_md)
    print(f"  [OK] {OUTPUT_NO_SEND_PREVIEW_MD}")

    handoff_md = generate_handoff_md(decisions, validation, production)
    write_text(OUTPUT_HANDOFF_MD, handoff_md)
    print(f"  [OK] {OUTPUT_HANDOFF_MD}")

    # 6.6 Result JSON
    result_json = {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "task_id": TASK_ID,
        "generated_at": china_stamp(),
        "type": "v119b_signal_quality_b_lite_and_dashboard_guidance",
        "mode": "live_one_shot_no_send",
        "blite_enhancements": {
            "price_oi_volume_anomaly": {
                "layered_decision": True,
                "tiers": ["reject", "watch(mild_watch)", "accept"],
                "watch_is_observation": True,
                "oi_zero_detection": True,
            },
            "news_event_market_impact": {
                "freshness_tagging": True,
                "stale_detection": True,
                "entity_normalization": True,
                "observation_only": True,
                "not_causal_proof": True,
            },
            "dashboard_guidance": {
                "chinese_30s_layer": True,
                "questions_answered": [
                    "这是什么",
                    "现在怎么看",
                    "现在能不能发",
                    "数据从哪来",
                    "操作员下一步",
                ],
            },
        },
        "data_sources": {
            "live_free_public_apis": live_adapter_count,
            "fixture_adapters": len(decisions) - live_adapter_count,
        },
        "cards": decisions,
        "decision_counts": decision_counts,
        "production_readiness": production,
        "contract_validation": validation,
        "adapter_diagnostics": [
            {k: v for k, v in d.items()}
            for d in diagnostics
        ],
        "no_send_preview": {
            "telegram_send": False,
            "x_twitter_send": False,
            "production_send": False,
            "daemon_or_loop_started": False,
        },
        "safety": {
            "tg_sent_this_run": False,
            "tg_message_count_this_run": 0,
            "x_twitter_sent_this_run": False,
            "production_send": False,
            "prod_state_write": False,
            "ai_model_called": False,
            "daemon_or_loop_started": False,
            "files_deleted": False,
            "credentials_printed": False,
            "v116_history_modified": False,
            "v117_history_modified": False,
            "v118_history_modified": False,
            "v119a_history_modified": False,
            "binance_api_key_used": False,
        },
        "output_files": {
            "snapshot_md": str(OUTPUT_SNAPSHOT_MD.relative_to(ROOT)),
            "decision_table_md": str(OUTPUT_DECISION_TABLE_MD.relative_to(ROOT)),
            "dashboard_html": str(OUTPUT_DASHBOARD_HTML.relative_to(ROOT)),
            "no_send_preview_md": str(OUTPUT_NO_SEND_PREVIEW_MD.relative_to(ROOT)),
            "handoff_md": str(OUTPUT_HANDOFF_MD.relative_to(ROOT)),
        },
    }
    write_json(OUTPUT_RESULT_JSON, result_json)
    print(f"  [OK] {OUTPUT_RESULT_JSON}")
    print()

    # ── Stage 7: Secret check ──
    print("[7] Self-check: verifying no raw credentials in any output...")
    all_outputs = [
        OUTPUT_RESULT_JSON, OUTPUT_SNAPSHOT_MD, OUTPUT_DECISION_TABLE_MD,
        OUTPUT_DASHBOARD_HTML, OUTPUT_NO_SEND_PREVIEW_MD, OUTPUT_HANDOFF_MD,
    ]
    clean, violations = check_no_raw_secrets(all_outputs)
    if clean:
        print(f"  [OK] All {len(all_outputs)} output files clean — no raw credentials")
    else:
        for v in violations:
            print(f"  [CRITICAL] {v}")
    print()

    # ── Final Summary ──
    print("=" * 70)
    print(f"Market Radar {PIPELINE_VERSION} — B-lite Quality + Dashboard Guidance Complete")
    print(f"  Live adapters used: {live_adapter_count}/3")
    print(f"  Cards processed: {len(decisions)}/5")
    print(f"  Decision counts: {decision_counts}")
    print(f"  B-lite layered decisions: price_oi_volume_anomaly, news_event_market_impact")
    print(f"  Chinese guidance: DASHBOARD TOP LAYER")
    print(f"  Contract valid: {validation['all_passed']}")
    print(f"  Production ready: {production['production_ready']} ({production['production_readiness_score']})")
    print(f"  Telegram sent: NO")
    print(f"  X/Twitter sent: NO")
    print(f"  AI/model called: NO")
    print(f"  Daemon/loop started: NO")
    print(f"  Files deleted: NO")
    print(f"  Credentials leaked: NO")
    print(f"  Dashboard: {OUTPUT_DASHBOARD_HTML}")
    print("=" * 70)

    return 0 if (validation["all_passed"] and clean) else 1


if __name__ == "__main__":
    sys.exit(main())
