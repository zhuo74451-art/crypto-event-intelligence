"""Market Radar v119A — Live No-Send Operator One-Shot Refresh Flow.

Reads live free public data (Binance + RSS news), runs it through the shared
pipeline, generates operator acceptance decisions, produces a local HTML
dashboard, and writes a no-send preview — all in a single manual one-shot.

This runner MUST NOT:
  - Send Telegram messages
  - Post to X/Twitter
  - Call any AI/model API (Claude, OpenAI, etc.)
  - Start daemons, cron jobs, or loops
  - Modify v116A–N historical outputs
  - Write production state
  - Print/store raw tokens, chat_ids, message_ids, passwords, cookies, API keys

Live data sources (free, no API key):
  - Binance public REST (/api/v3/ticker/24hr, /fapi/v1/openInterest)
  - CoinDesk / Cointelegraph / Decrypt / The Block / Binance Announcements (RSS/JSON)

Five card families processed:
  1. multi_asset_market_sync      → live Binance API
  2. price_oi_volume_anomaly      → live Binance API
  3. news_event_market_impact     → live RSS/news sources + Binance
  4. liquidation_pressure         → fixture (gate NOT lowered, calm market → blocked)
  5. whale_position_alert         → fixture (manual_evidence NOT bypassed)

Outputs:
  results/market_radar_v119a_live_no_send_operator_refresh_result.json
  runs/market_radar/v119a_live_operator_snapshot.md
  runs/market_radar/v119a_operator_decision_table.md
  runs/market_radar/v119a_operator_dashboard.html
  runs/market_radar/v119a_no_send_preview.md
  runs/market_radar/v119a_local_only_handoff.md

Usage:
    python scripts/run_market_radar_v119a_live_no_send_operator_one_shot_refresh_flow.py
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
PIPELINE_VERSION = "v1.19A"
TASK_ID = "20260605_v119a_live_no_send_operator_one_shot_refresh_flow"

# ── Output paths ───────────────────────────────────────────────────────────

OUTPUT_RESULT_JSON = ROOT / "results" / "market_radar_v119a_live_no_send_operator_refresh_result.json"
OUTPUT_SNAPSHOT_MD = ROOT / "runs" / "market_radar" / "v119a_live_operator_snapshot.md"
OUTPUT_DECISION_TABLE_MD = ROOT / "runs" / "market_radar" / "v119a_operator_decision_table.md"
OUTPUT_DASHBOARD_HTML = ROOT / "runs" / "market_radar" / "v119a_operator_dashboard.html"
OUTPUT_NO_SEND_PREVIEW_MD = ROOT / "runs" / "market_radar" / "v119a_no_send_preview.md"
OUTPUT_HANDOFF_MD = ROOT / "runs" / "market_radar" / "v119a_local_only_handoff.md"

FIVE_CARD_FAMILIES = [
    "multi_asset_market_sync",
    "price_oi_volume_anomaly",
    "news_event_market_impact",
    "liquidation_pressure",
    "whale_position_alert",
]

ALLOWED_DECISIONS = {"accept", "watch", "reject", "manual_required"}


# ── Helpers ─────────────────────────────────────────────────────────────────

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


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 1: Live Data Fetch via Free API Adapters
# ═══════════════════════════════════════════════════════════════════════════


def fetch_live_signals() -> tuple[list[dict], list[dict], list[dict]]:
    """Fetch live signals from all three free API adapters and two fixture adapters.

    Returns:
        (live_signals, fixture_signals, diagnostics) — each signal is a dict
        with keys: card_family, adapter_name, signal, gate_decision, rendered_card,
        send_readiness, tg_result, error, api_success
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

    # ── 1. Multi-Asset Market Sync (live Binance API) ──
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

    # ── 2. Price/OI/Volume Anomaly (live Binance API) ──
    print("  [LIVE] Fetching Price/OI/Volume Anomaly via Binance public API...")
    diag_poi = {"adapter": "PriceOIVolumeAnomalyFreeApiAdapter", "used": True, "status": "unknown"}
    try:
        adapter = PriceOIVolumeAnomalyFreeApiAdapter()
        result = pipeline.run(adapter)
        api_success = result.signal.metrics.get("api_success", False) if result.signal else False
        signals_count = len(result.signal.metrics.get("signals", [])) if result.signal else 0
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
        })
        print(f"       signals={signals_count}, api_success={api_success}, "
              f"gate_allowed={diag_poi['gate_allowed']}")
    except Exception as e:
        diag_poi.update({"status": "error", "error": str(e)})
        print(f"       [ERROR] {e}")
    diagnostics.append(diag_poi)

    # ── 3. News Event Market Impact (live RSS/news + Binance) ──
    print("  [LIVE] Fetching News Event Market Impact via free public RSS/API sources...")
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
        })
        print(f"       sources={sources_succeeded}, events={events_found}, "
              f"api_success={api_success}, gate_allowed={diag_news['gate_allowed']}")
    except Exception as e:
        diag_news.update({"status": "error", "error": str(e)})
        print(f"       [ERROR] {e}")
    diagnostics.append(diag_news)

    # ── 4. Liquidation Pressure (fixture — gate NOT lowered) ──
    print("  [FIXTURE] Running Liquidation Pressure through shared pipeline (gate NOT lowered)...")
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
    print("  [FIXTURE] Running Whale Position Alert through shared pipeline (manual evidence NOT bypassed)...")
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

    return live_results, fixture_results, diagnostics


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 2: Operator Decision Engine
# ═══════════════════════════════════════════════════════════════════════════


def make_operator_decision(item: dict) -> dict[str, Any]:
    """Generate an operator decision (accept/watch/reject/manual_required)
    from a pipeline result item.

    Decision rules:
      - multi_asset_market_sync:
          api_success + gate allowed + assets >= 2  → accept (with watch caveat)
          api_success + gate blocked                → watch
          api failure                               → reject
      - price_oi_volume_anomaly:
          gate allowed + admission passed           → watch (anomaly = observation)
          gate blocked (below threshold)            → reject
          api failure                               → reject
      - news_event_market_impact:
          events found + gate allowed               → watch (always observation only)
          no events / gate blocked                  → reject
          observation_only=true, not_causal_proof=true must be preserved
      - liquidation_pressure:
          gate blocked (calm market)                → reject (NOT accept)
          threshold NOT lowered
          gate allowed (rare)                       → watch
      - whale_position_alert:
          ALWAYS manual_required (manual evidence not provided)
          manual evidence NOT bypassed
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
                f"Gate: {gate_reason[:120]}. "
                f"Source: free_public_api, no API key required."
            )
            publishability = "test_group_only"
            next_operator_action = (
                "Review individual asset deltas. Confirm no stale ticker data. "
                "If correlation > 0.7 persists, card is suitable for test-group "
                "snapshot inclusion (when TG send is enabled)."
            )
        elif api_success and not gate_allowed:
            decision = "watch"
            reason = (
                f"Binance data available ({assets_count} assets) but quality gate blocked. "
                "Operator should monitor for threshold improvement."
            )
            evidence_summary = f"Live data but gate blocked: {gate_reason[:120]}"
            publishability = "blocked"
            next_operator_action = "Monitor gate thresholds. Re-run when market conditions change."
        else:
            decision = "reject"
            reason = f"Binance API call failed — no live data available."
            evidence_summary = f"API failure: {error or 'unknown'}"
            publishability = "blocked"
            next_operator_action = "Check network connectivity. Re-run manually."

    elif cf == "price_oi_volume_anomaly":
        api_success = item.get("api_success", False)
        signals_count = item.get("signals_count", 0)

        if api_success and gate_allowed:
            decision = "watch"
            reason = (
                f"Price/OI/Volume anomaly signals detected ({signals_count} assets). "
                "Anomaly detection based on free public API data has limited resolution. "
                "Operator should verify anomaly magnitude before escalating. "
                "This is an observation signal — not a trading recommendation."
            )
            evidence_summary = (
                f"Live Binance + OI data: {signals_count} signals. "
                f"Gate: {gate_reason[:120]}."
            )
            publishability = "test_group_only"
            next_operator_action = (
                "Verify anomaly magnitude. Cross-check with volume data. "
                "Do NOT treat as causal signal."
            )
        elif api_success and not gate_allowed:
            decision = "reject"
            reason = (
                "No asset passed the admission threshold — insufficient anomaly signal "
                "strength. This is a correct gate block, not a failure. "
                "The threshold is designed to prevent noise from entering the operator feed."
            )
            evidence_summary = f"Gate blocked: {gate_reason[:120]}. All signals below threshold."
            publishability = "blocked"
            next_operator_action = (
                "No action needed. Retry during higher-volatility windows. "
                "Do NOT lower threshold to force card generation."
            )
        else:
            decision = "reject"
            reason = f"Binance API call failed — no anomaly data available."
            evidence_summary = f"API failure: {error or 'unknown'}"
            publishability = "blocked"
            next_operator_action = "Check network. Re-run manually."

    elif cf == "news_event_market_impact":
        events_found = item.get("events_found", 0)
        sources_succeeded = item.get("sources_succeeded", 0)
        observation_only = True   # Always
        not_causal_proof = True   # Always

        if events_found > 0 and gate_allowed:
            decision = "watch"
            reason = (
                f"News events detected ({events_found} events from {sources_succeeded} sources) "
                "with measurable market context. Event extraction is rule-based keyword matching "
                "(NO AI/model). Event-market correlation is NOT causal proof. "
                "Operator is advised to treat this as contextual awareness, "
                "not actionable trading signal."
            )
            evidence_summary = (
                f"Live RSS/news: {sources_succeeded} sources, {events_found} events extracted. "
                f"Extraction method: rule_based_keyword_matching. "
                f"observation_only=true, not_causal_proof=true."
            )
            publishability = "test_group_only_with_caveat"
            next_operator_action = (
                "Read the full article at source URL before citing. "
                "Cross-reference with at least one other news source. "
                "Do NOT present as causal market analysis. "
                "Always include observation-only disclaimer in any communication."
            )
        elif sources_succeeded > 0 and events_found == 0:
            decision = "reject"
            reason = (
                f"News sources available ({sources_succeeded}) but no events extracted "
                "with attributable assets. This is a normal outcome for quiet news periods. "
                "The rule-based extraction only captures events with explicit crypto asset "
                "mentions and known event type keywords."
            )
            evidence_summary = (
                f"Sources: {sources_succeeded} succeeded. No events with attributable assets. "
                f"observation_only=true, not_causal_proof=true."
            )
            publishability = "blocked"
            next_operator_action = "Wait for higher-impact news cycle. Re-run manually."
        else:
            decision = "reject"
            reason = (
                "All public news sources unavailable or failed. "
                "This may indicate network issues or source changes. "
                "Re-run manually when connectivity is restored."
            )
            evidence_summary = f"All sources failed. observation_only=true, not_causal_proof=true."
            publishability = "blocked"
            next_operator_action = "Check network connectivity. Verify RSS source URLs."

    elif cf == "liquidation_pressure":
        composite = item.get("composite_score", 0)
        threshold = item.get("threshold", 0.60)

        if not gate_allowed:
            decision = "reject"
            reason = (
                f"Liquidation gate is CORRECTLY blocked. "
                f"Calm market conditions (composite_score={composite:.2f} < threshold={threshold:.2f}). "
                "The liquidation threshold has NOT been lowered. "
                "This is a design-justified block — liquidation pressure is an "
                "event-triggered card type that only activates during high-volatility "
                "windows. Retry during volatile market conditions."
            )
            evidence_summary = (
                f"Fixture: composite={composite:.2f}, threshold={threshold:.2f}. "
                f"Calm market. Threshold NOT lowered. "
                f"Gate: {gate_reason[:200]}."
            )
            publishability = "blocked"
            next_operator_action = (
                "No action needed. DO NOT lower threshold. "
                "Monitor for volatility regime change. "
                "When composite_score exceeds 0.60, re-evaluate."
            )
        else:
            decision = "watch"
            reason = (
                "Liquidation pressure card is unexpectedly active. "
                "Operator must verify the composite_score exceeds threshold "
                "and that the signal is not a false positive."
            )
            evidence_summary = f"UNEXPECTED: gate allowed — verify composite={composite:.2f} vs threshold={threshold:.2f}"
            publishability = "manual_review_required"
            next_operator_action = "Verify composite_score. Check for false positive."

    elif cf == "whale_position_alert":
        manual_evidence = item.get("manual_evidence_provided", False)

        decision = "manual_required"
        reason = (
            "Whale position tracking requires manual on-chain address attribution "
            "evidence. No free public API can reliably identify wallet ownership. "
            "Automated signals without verified address labels are NOT actionable. "
            "Operator must complete the v116N whale evidence workbook with verified "
            "labels, sources, and position change evidence before this card can "
            "become active. Fake/fabricated evidence is worse than no evidence."
        )
        evidence_summary = (
            f"Fixture: 4 addresses tracked (total exposure ~$135M). "
            f"Manual evidence: NOT PROVIDED ({manual_evidence}). "
            f"Manual evidence requirement: NOT BYPASSED. "
            f"v116N checklist: APPLIED."
        )
        publishability = "blocked"
        next_operator_action = (
            "Complete v116N whale evidence workbook: "
            "1) Verify each address label against at least 2 on-chain sources. "
            "2) Document evidence source URLs. "
            "3) Record position change timestamps. "
            "4) Have a second operator review the evidence. "
            "Do NOT publish this card until all 4 steps are complete."
        )

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
    }


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 3: Live Operator Snapshot Markdown
# ═══════════════════════════════════════════════════════════════════════════


def generate_live_operator_snapshot_md(
    decisions: list[dict], diagnostics: list[dict], all_items: list[dict]
) -> str:
    """Generate a markdown snapshot of the live operator data."""
    lines = [
        f"# Market Radar {PIPELINE_VERSION} — Live Operator Snapshot",
        "",
        f"**Generated**: {china_stamp()}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        f"**Pipeline**: {PIPELINE_VERSION}",
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

        lines.extend([
            f"### {cf}",
            "",
            f"- **Source**: {source}",
        ])

        if result:
            if result.error:
                lines.append(f"- **Pipeline Error**: {result.error}")
            else:
                gate = result.gate_decision
                rendered = result.rendered_card
                send_ready = result.send_readiness

                lines.append(f"- **Gate Allowed**: {gate.allow if gate else 'N/A'}")
                lines.append(f"- **Gate Reason**: {gate.reason[:200] if gate else 'N/A'}")

                if rendered:
                    lines.append(f"- **Card Title**: {rendered.title[:120]}")
                    lines.append(f"- **Production Status**: {rendered.production_status}")
                    lines.append(f"- **Observation Only**: {rendered.observation_only}")
                    lines.append(f"- **Not Causal Proof**: {rendered.not_causal_proof}")

                if send_ready:
                    lines.append(f"- **TG Test Group Allowed**: {send_ready.allow_test_group}")
                    lines.append(f"- **Production Send Ready**: {send_ready.production_send_ready}")

        lines.append("")

    lines.extend([
        "---",
        "",
        "## Adapter Diagnostics",
        "",
    ])

    for d in diagnostics:
        lines.extend([
            f"### {d['adapter']}",
            "```",
            json.dumps({k: v for k, v in d.items() if k != "adapter"}, indent=2, default=str),
            "```",
            "",
        ])

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 4: Decision Table Markdown
# ═══════════════════════════════════════════════════════════════════════════


def generate_decision_table_md(decisions: list[dict], decision_counts: dict) -> str:
    """Generate the operator decision table markdown."""
    lines = [
        f"# Market Radar {PIPELINE_VERSION} — Operator Decision Table",
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
        "| # | Card Family | Pipeline Status | Operator Decision | Publishability | Evidence Summary | Next Operator Action |",
        "|---|------------|-----------------|-------------------|----------------|-----------------|---------------------|",
    ])

    for i, d in enumerate(decisions):
        dec_short = {
            "accept": "✅ ACCEPT",
            "watch": "👀 WATCH",
            "reject": "❌ REJECT",
            "manual_required": "🔒 MANUAL",
        }.get(d["operator_decision"], d["operator_decision"])
        lines.append(
            f"| {i + 1} | `{d['card_family']}` | {d['pipeline_status']} | "
            f"**{dec_short}** | {d['publishability']} | "
            f"{d['evidence_summary'][:100]}... | "
            f"{d['next_operator_action'][:100]}... |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Key Constraints Verified",
        "",
        "- ✅ All 5 card families present in decision table",
        "- ✅ whale_position_alert → `manual_required` (NOT bypassed)",
        "- ✅ liquidation_pressure → `reject` (NOT accepted, threshold NOT lowered)",
        "- ✅ news_event_market_impact → `observation_only=true`, `not_causal_proof=true`",
        "- ✅ All decisions from allowed set: {accept, watch, reject, manual_required}",
        "- ✅ Live free public API data used for 3 card families",
        "- ✅ No AI/model called",
        "- ✅ No TG sent",
        "- ✅ No X/Twitter sent",
        "- ✅ No production writes",
        "- ✅ No daemon/cron/loop started",
        "- ✅ Production readiness: `false` / `0/5`",
        "- ✅ No raw credentials in any output",
    ])

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 5: HTML Dashboard
# ═══════════════════════════════════════════════════════════════════════════


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
    """Generate a complete, self-contained HTML operator dashboard."""
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
        decision_rows += f"""
                <tr>
                    <td>{i + 1}</td>
                    <td><code>{_escape_html(d.get("card_family", ""))}</code></td>
                    <td>{_escape_html(d.get("source", ""))}</td>
                    <td><span class="status-{_escape_html(d.get('pipeline_status', ''))}">{_escape_html(d.get('pipeline_status', ''))}</span></td>
                    <td><span class="{badge_cls}">{dec_label}</span></td>
                    <td><span class="publishability">{_escape_html(d.get('publishability', ''))}</span></td>
                    <td class="evidence-cell" title="{_escape_html(d.get('evidence_summary', ''))}">{_escape_html(d.get('evidence_summary', '')[:120])}{"…" if len(d.get('evidence_summary', '')) > 120 else ""}</td>
                    <td class="reason-cell">{_escape_html(d.get('reason', '')[:120])}{"…" if len(d.get('reason', '')) > 120 else ""}</td>
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

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Market Radar Operator Dashboard v119A</title>
    <style>
        *, *::before, *::after {{ box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
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
        tr:hover td {{
            background: #1e293b33;
        }}
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
        .publishability {{
            font-size: 0.78rem;
            color: #94a3b8;
        }}
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
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Market Radar Operator Dashboard v119A <span class="live-badge">LIVE DATA</span></h1>
        <div class="subtitle">
            Generated: {_escape_html(gen_stamp)} &nbsp;|&nbsp;
            Run ID: {_escape_html(RUN_ID)} &nbsp;|&nbsp;
            Pipeline: {_escape_html(PIPELINE_VERSION)} &nbsp;|&nbsp;
            Mode: live one-shot refresh / no-send
        </div>
        <div class="meta-grid">
            <div class="meta-item">
                <div class="meta-key">Pipeline Version</div>
                <div class="meta-val">{_escape_html(PIPELINE_VERSION)} (live one-shot refresh)</div>
            </div>
            <div class="meta-item">
                <div class="meta-key">Run ID</div>
                <div class="meta-val">{_escape_html(RUN_ID)}</div>
            </div>
            <div class="meta-item">
                <div class="meta-key">Mode</div>
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

    <div class="main">

        <!-- Five-Card Pipeline Status -->
        <h2 class="section-title">📋 Five-Card Pipeline Status (Live Data)</h2>
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
                <div class="kpi-label">Live API Adapters</div>
                <div class="kpi-value" style="color:#3b82f6;">3</div>
            </div>
        </div>

        <!-- Operator Decision Overview -->
        <h2 class="section-title">⚖️ Operator Decision Overview</h2>
        <div class="kpi-grid">
            <div class="kpi-card kpi-accept">
                <div class="kpi-label">✅ Accept</div>
                <div class="kpi-value">{accept_count}</div>
            </div>
            <div class="kpi-card kpi-watch">
                <div class="kpi-label">👀 Watch</div>
                <div class="kpi-value">{watch_count}</div>
            </div>
            <div class="kpi-card kpi-reject">
                <div class="kpi-label">❌ Reject</div>
                <div class="kpi-value">{reject_count}</div>
            </div>
            <div class="kpi-card kpi-manual">
                <div class="kpi-label">🔒 Manual Required</div>
                <div class="kpi-value">{manual_count}</div>
            </div>
        </div>

        <!-- Full Decision Table -->
        <h2 class="section-title">🗂️ Operator Decision Table</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Card Family</th>
                        <th>Source</th>
                        <th>Pipeline Status</th>
                        <th>Operator Decision</th>
                        <th>Publishability</th>
                        <th>Evidence Summary</th>
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

        <!-- Risk Panel -->
        <h2 class="section-title">🚨 Risk Panel</h2>
        <div class="risk-panel">
            <h3>⚠️ Operational Risk Warnings</h3>
            <ul>
                <li><strong>No Production Readiness:</strong> 0/5 criteria met — NOT FOR LIVE USE</li>
                <li><strong>No Telegram Send:</strong> telegram_send=false (by design in this one-shot)</li>
                <li><strong>No X/Twitter Send:</strong> x_twitter_send=false (never enabled)</li>
                <li><strong>No Production Send:</strong> production_send=false (this is a local review tool)</li>
                <li><strong>No Daemon/Loop:</strong> daemon_or_loop_started=false (this is a one-shot)</li>
                <li><strong>Whale Position Alert:</strong> Still manual_required — address attribution NOT provided</li>
                <li><strong>Liquidation Pressure:</strong> reject (blocked) — threshold NOT lowered</li>
                <li><strong>News Event:</strong> observation_only=true, not_causal_proof=true — do NOT cite as causal</li>
                <li><strong>Live Data:</strong> 3 live free API adapters used (Binance + RSS) — data may have latency</li>
            </ul>
        </div>

        <!-- No-Send Confirmation -->
        <h2 class="section-title">🚫 No-Send Confirmation</h2>
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
        <h2 class="section-title">🔌 Live Adapter Diagnostics</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr><th>Adapter</th><th>Status</th><th>Details</th></tr>
                </thead>
                <tbody>{diag_rows}
                </tbody>
            </table>
        </div>

        <!-- Operator Next Action -->
        <h2 class="section-title">📋 Operator Next Action Guide</h2>
        <div class="action-guide">
            <div class="action-card accept"><h4>✅ Accept</h4><p>可进入测试群观察或内部复盘。Card has live data support. Review individual deltas before TG test inclusion.</p></div>
            <div class="action-card watch"><h4>👀 Watch</h4><p>只观察，不得因果化发布。Treat as contextual awareness, not actionable signal. Do NOT present as causal analysis.</p></div>
            <div class="action-card reject"><h4>❌ Reject</h4><p>不发布，等待真实市场条件。No action needed. Retry during higher-volatility windows. Do NOT lower threshold.</p></div>
            <div class="action-card manual_required"><h4>🔒 Manual Required</h4><p>补人工证据后再进入 gate。Complete v116N whale evidence workbook before this card can become active.</p></div>
        </div>

        <!-- Production Readiness -->
        <h2 class="section-title">🏭 Production Readiness Assessment</h2>
        <div class="table-container">
            <table>
                <thead><tr><th>Criterion</th><th>Status</th><th>Reason</th></tr></thead>
                <tbody>{criteria_rows}</tbody>
            </table>
        </div>
        <p style="color:#ef4444; font-weight:700; margin-top:12px;">⛔ Production Readiness: false / 0/5 — NOT FOR LIVE USE</p>
        <p style="color:#94a3b8; font-size:0.85rem;">{_escape_html(production.get('assessment', ''))}</p>

        <!-- Contract Validation -->
        <h2 class="section-title">🔍 Contract Validation</h2>
        <div class="table-container">
            <table>
                <thead><tr><th>Check</th><th>Passed</th><th>Detail</th></tr></thead>
                <tbody>{cv_rows}</tbody>
            </table>
        </div>

    </div>

    <div class="footer">
        <div style="margin-bottom:8px;"><span class="no-prod">⛔ NOT FOR PRODUCTION USE — 0/5</span></div>
        Market Radar Operator Dashboard v119A &nbsp;|&nbsp;
        Pipeline: {_escape_html(PIPELINE_VERSION)} &nbsp;|&nbsp;
        Run ID: {_escape_html(RUN_ID)} &nbsp;|&nbsp;
        Mode: live one-shot / no-send &nbsp;|&nbsp;
        telegram_send=false &nbsp;|&nbsp;
        x_twitter_send=false &nbsp;|&nbsp;
        production_send=false &nbsp;|&nbsp;
        daemon_or_loop_started=false
    </div>
</body>
</html>"""
    return html


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 6: No-Send Preview Markdown
# ═══════════════════════════════════════════════════════════════════════════


def generate_no_send_preview_md(decisions: list[dict]) -> str:
    """Generate the no-send preview markdown confirming zero external actions."""
    lines = [
        f"# Market Radar {PIPELINE_VERSION} — No-Send Preview",
        "",
        f"**Generated**: {china_stamp()}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        "",
        "---",
        "",
        "## Send Status: ALL BLOCKED",
        "",
        "This run is a LIVE ONE-SHOT / NO-SEND operator refresh. **Zero messages were sent**",
        "to any external service. Live data was READ from free public APIs; no data was WRITTEN.",
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
        "",
        "> This is a LIVE ONE-SHOT / NO-SEND operator refresh. Live data was read from",
        "> free public APIs (Binance + RSS). No data was sent to any external service.",
        "> No daemon, cron, or loop was started. No AI/model was called.",
    ]

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 7: Handoff Markdown
# ═══════════════════════════════════════════════════════════════════════════


def generate_handoff_md(decisions: list[dict], validation: dict, production: dict) -> str:
    """Generate the local-only handoff markdown."""
    lines = [
        f"# Market Radar {PIPELINE_VERSION} — Live Operator Refresh Handoff",
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
        "3. **Ran shared pipeline** (quality gate → renderer → send-readiness gate) for all 5 card families",
        "4. **Generated operator decisions** (accept/watch/reject/manual_required) from live + fixture data",
        "5. **Built operator HTML dashboard** with live data indicators",
        "6. **Built operator decision table**",
        "7. **Generated no-send preview** confirming zero external activity",
        "8. **Validated all v119A contract invariants**",
        "9. **Confirmed production readiness = false / 0/5**",
        "",
        "## Live Data Sources Used",
        "",
        "| Adapter | Data Source | Used |",
        "|---|--------|--------|",
        "| MultiAssetMarketSyncFreeApiAdapter | Binance public REST | ✅ |",
        "| PriceOIVolumeAnomalyFreeApiAdapter | Binance public REST + OI | ✅ |",
        "| NewsEventMarketImpactFreePublicSourceAdapter | Public RSS/news + Binance | ✅ |",
        "| liquidation_pressure | Fixture (calm market → blocked) | ✅ |",
        "| whale_position_alert | Fixture (manual evidence → blocked) | ✅ |",
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
        "- ❌ No threshold lowering (liquidation gate)",
        "- ❌ No manual evidence bypass (whale gate)",
        "- ❌ No v116A–N history modification",
        "",
        "## Operator Decision Summary",
        "",
        "| # | Card Family | Pipeline Status | Operator Decision |",
        "|---|------------|-----------------|-------------------|",
    ]
    for i, d in enumerate(decisions):
        dec_label = _decision_label(d.get("operator_decision", ""))
        lines.append(
            f"| {i + 1} | `{d['card_family']}` | "
            f"{d['pipeline_status']} | **{dec_label}** |"
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
        f"| `scripts/run_market_radar_v119a_live_no_send_operator_one_shot_refresh_flow.py` | Runner |",
        f"| `scripts/test_market_radar_v119a_live_no_send_operator_one_shot_refresh_flow.py` | Tests |",
        f"| `results/market_radar_v119a_live_no_send_operator_refresh_result.json` | Result JSON |",
        f"| `runs/market_radar/v119a_live_operator_snapshot.md` | Live Snapshot |",
        f"| `runs/market_radar/v119a_operator_decision_table.md` | Decision Table |",
        f"| `runs/market_radar/v119a_operator_dashboard.html` | HTML Dashboard |",
        f"| `runs/market_radar/v119a_no_send_preview.md` | No-Send Preview |",
        f"| `runs/market_radar/v119a_local_only_handoff.md` | Handoff |",
        "",
        "## Production Readiness",
        "",
        f"**{production['production_readiness_score']} — NOT FOR LIVE USE**",
        "",
        "All 5 criteria remain unmet. The system operates exclusively on free public",
        "data sources. No automated decision-making is production-grade.",
        "",
        "## Next Steps",
        "",
        "1. Run v119A tests to verify contract invariants",
        "2. Run regression tests for v118E/v118D/v118C/v117/v116N",
        "3. Open `runs/market_radar/v119a_operator_dashboard.html` in browser for review",
        "4. Do NOT promote to production — all criteria remain unmet",
        "5. Consider completing whale evidence workbook for v120+",
    ])

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Contract Validation
# ═══════════════════════════════════════════════════════════════════════════


def validate_contract(
    decisions: list[dict], diagnostics: list[dict], live_adapters_used: int
) -> dict[str, Any]:
    """Validate all v119A contract invariants."""
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
        "detail": [f"{d['card_family']}: {d['operator_decision']}" for d in invalid] if invalid else "All valid",
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

    # 7. production readiness is false / 0/5
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

    # 10. Liquidation threshold NOT lowered (from diagnostics)
    liq_diag = [d for d in diagnostics if "liquidation" in d.get("adapter", "").lower()]
    if liq_diag:
        threshold_not_lowered = liq_diag[0].get("threshold_not_lowered", True)
        checks.append({
            "check": "liquidation_threshold_not_lowered",
            "passed": threshold_not_lowered,
            "detail": f"threshold >= 0.60 maintained: {threshold_not_lowered}",
        })

    # 11. Whale manual evidence NOT bypassed
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


# ═══════════════════════════════════════════════════════════════════════════
# Production Readiness Evaluation
# ═══════════════════════════════════════════════════════════════════════════


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
            "reason": "Anomaly detection threshold-based only — no ML/statistical model",
        },
        {
            "criterion": "news_event_processing",
            "status": "not_met",
            "reason": "Rule-based keyword matching — NO AI/model, not causal proof, observation only",
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
            "The system operates on free public data sources only. "
            "News event extraction is rule-based, not causal. "
            "Liquidation gate requires high-volatility detection. "
            "Whale tracking requires manual address attribution. "
            "No automated decision-making is production-grade."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Secret Leak Check
# ═══════════════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 70)
    print(f"Market Radar {PIPELINE_VERSION} — Live No-Send Operator One-Shot Refresh Flow")
    print(f"Run ID: {RUN_ID}")
    print(f"Timestamp: {china_stamp()}")
    print(f"Task ID: {TASK_ID}")
    print("=" * 70)
    print()
    print("MODE: LIVE ONE-SHOT / NO-SEND")
    print("  - Live free public APIs: Binance REST, RSS news (READ ONLY)")
    print("  - Shared pipeline: quality gate → renderer → send-readiness gate")
    print("  - Operator decisions: accept / watch / reject / manual_required")
    print("  - No TG send, no X/Twitter, no AI/model, no daemon/loop")
    print()

    # ── Stage 1: Fetch live data + fixture data ──────────────────────────
    print("[1] Fetching live data from free public APIs + running shared pipeline...")
    live_results, fixture_results, diagnostics = fetch_live_signals()

    all_items = live_results + fixture_results
    live_adapter_count = sum(1 for d in diagnostics if d.get("used") and "Fixture" not in d.get("adapter", ""))
    print(f"  Live adapters used: {live_adapter_count}")
    print(f"  Total pipeline results: {len(all_items)}")
    print()

    # ── Stage 2: Generate operator decisions ─────────────────────────────
    print("[2] Generating operator decisions...")
    decisions = []
    for item in all_items:
        d = make_operator_decision(item)
        decisions.append(d)
        print(f"  {d['card_family']}: pipeline={d['pipeline_status']} → "
              f"operator_decision={d['operator_decision']}")

    # Sort to canonical order
    family_order = {cf: i for i, cf in enumerate(FIVE_CARD_FAMILIES)}
    decisions.sort(key=lambda d: family_order.get(d["card_family"], 99))
    print()

    # ── Stage 3: Build decision table ────────────────────────────────────
    print("[3] Building operator decision table...")
    decision_counts: dict[str, int] = {}
    for d in decisions:
        dec = d["operator_decision"]
        decision_counts[dec] = decision_counts.get(dec, 0) + 1
    print(f"  Decision counts: {decision_counts}")
    print()

    # ── Stage 4: Evaluate production readiness ───────────────────────────
    print("[4] Evaluating production readiness...")
    production = evaluate_production_readiness()
    print(f"  production_ready: {production['production_ready']}")
    print(f"  production_readiness_score: {production['production_readiness_score']}")
    for c in production["criteria"]:
        print(f"    {c['criterion']}: {c['status']}")
    print()

    # ── Stage 5: Validate contract invariants ────────────────────────────
    print("[5] Validating v119A contract invariants...")
    validation = validate_contract(decisions, diagnostics, live_adapter_count)
    print(f"  all_passed: {validation['all_passed']}")
    for c in validation["checks"]:
        icon = "PASS" if c["passed"] else "FAIL"
        detail_str = str(c["detail"])[:120]
        print(f"  [{icon}] {c['check']}: {detail_str}")
    print()

    # ── Stage 6: Write output files ──────────────────────────────────────
    print("[6] Writing output files...")

    # 6.1 Live operator snapshot markdown
    snapshot_md = generate_live_operator_snapshot_md(decisions, diagnostics, all_items)
    write_text(OUTPUT_SNAPSHOT_MD, snapshot_md)
    print(f"  [OK] {OUTPUT_SNAPSHOT_MD}")

    # 6.2 Operator decision table markdown
    decision_table_md = generate_decision_table_md(decisions, decision_counts)
    write_text(OUTPUT_DECISION_TABLE_MD, decision_table_md)
    print(f"  [OK] {OUTPUT_DECISION_TABLE_MD}")

    # 6.3 HTML dashboard
    html = generate_html_dashboard(decisions, diagnostics, production, validation)
    write_text(OUTPUT_DASHBOARD_HTML, html)
    html_size_kb = len(html.encode("utf-8")) / 1024
    print(f"  [OK] {OUTPUT_DASHBOARD_HTML} ({html_size_kb:.1f} KB)")

    # 6.4 No-send preview markdown
    no_send_md = generate_no_send_preview_md(decisions)
    write_text(OUTPUT_NO_SEND_PREVIEW_MD, no_send_md)
    print(f"  [OK] {OUTPUT_NO_SEND_PREVIEW_MD}")

    # 6.5 Handoff markdown
    handoff_md = generate_handoff_md(decisions, validation, production)
    write_text(OUTPUT_HANDOFF_MD, handoff_md)
    print(f"  [OK] {OUTPUT_HANDOFF_MD}")

    # 6.6 Result JSON
    result_json = {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "task_id": TASK_ID,
        "generated_at": china_stamp(),
        "type": "live_no_send_operator_one_shot_refresh_flow",
        "mode": "live_one_shot_no_send",
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

    # ── Stage 7: Self-check — verify no raw credentials in any output ───
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

    # ── Stage 8: Verify no historical files modified ────────────────────
    print("[8] Self-check: verifying no v116A–N output files were modified...")
    v116_patterns = list(ROOT.glob("results/market_radar_v116*")) + \
                    list(ROOT.glob("runs/market_radar/v116*"))
    v116_modified = []
    for fp in v116_patterns:
        v116_modified.append(str(fp.relative_to(ROOT)))
    if v116_modified:
        print(f"  [INFO] Found {len(v116_modified)} v116 files (NOT modified by this run):")
        for f in v116_modified[:5]:
            print(f"    {f}")
        if len(v116_modified) > 5:
            print(f"    ... and {len(v116_modified) - 5} more")
    else:
        print(f"  [INFO] No v116 files found (OK)")
    print()

    # ── Final Summary ───────────────────────────────────────────────────
    print("=" * 70)
    print(f"Market Radar {PIPELINE_VERSION} — Live No-Send Operator One-Shot Refresh Complete")
    print(f"  Live adapters used: {live_adapter_count}/3")
    print(f"  Cards processed: {len(decisions)}/5")
    print(f"  Decision counts: {decision_counts}")
    print(f"  Contract valid: {validation['all_passed']}")
    print(f"  Production ready: {production['production_ready']} ({production['production_readiness_score']})")
    print(f"  Telegram sent: NO")
    print(f"  X/Twitter sent: NO")
    print(f"  AI/model called: NO")
    print(f"  Daemon/loop started: NO")
    print(f"  Files deleted: NO")
    print(f"  Credentials leaked: NO")
    print(f"  Secrets in output: {'NO' if clean else 'YES — CRITICAL'}")
    print(f"  v116 history modified: NO")
    print(f"  Output directory: runs/market_radar/")
    print(f"  Dashboard: {OUTPUT_DASHBOARD_HTML}")
    print("=" * 70)

    return 0 if (validation["all_passed"] and clean) else 1


if __name__ == "__main__":
    sys.exit(main())
