#!/usr/bin/env python3
"""MVP+ Window 3 — Existing Feeds + Market Context + Workbench.

Orchestrates:
  L3: Market Context (CCXT + Hyperliquid)
  L4: Existing Feeds (truth-audited)
  L5: Secure Workbench HTML (9 sections)
  + Market Regime, Watchlists, Event Journal, Downstream Candidates
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Ensure project root — prefer CWD for CLI runs, fallback to file-hierarchy
_HERE = Path(__file__).resolve().parent
_PROJECT = Path.cwd()  # Use CWD for CLI; data/ and market_radar/ are relative to CWD
if not (_PROJECT / "market_radar").is_dir():
    _PROJECT = _HERE.parents[3]  # fallback
sys.path.insert(0, str(_PROJECT))

from market_radar.shared.contracts import (
    SourceHealth, SourceStatus, ChangeType, CONTRACTS_VERSION, CONTRACTS_SEALED_AT,
)
from market_radar.l5_workbench_ui.workbench_renderer import WorkbenchBundle, render_workbench


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _compute_market_regime(contexts: list) -> dict:
    """Rule-based market regime classification."""
    if not contexts:
        return {"state": "insufficient_data", "rules": ["no market context data available"]}

    rules = []
    btc = next((c for c in contexts if c.get("symbol") == "BTC"), None)
    eth = next((c for c in contexts if c.get("symbol") == "ETH"), None)

    if btc:
        chg = btc.get("price_change_24h_pct")
        oi = btc.get("open_interest")
        if chg is not None and oi is not None:
            if chg < -2 and oi > 1e9:
                rules.append("BTC price down + OI elevated: potential leverage building into dip")
            elif chg > 2 and oi > 1e9:
                rules.append("BTC price up + OI elevated: potential crowded long")
            elif chg < -2:
                rules.append("BTC price declining")
            elif chg > 2:
                rules.append("BTC price rising")
        funding = btc.get("funding_rate")
        if funding is not None:
            if funding > 0.0005:
                rules.append("Funding rate elevated: longs paying premium")
            elif funding < -0.0005:
                rules.append("Negative funding: shorts paying premium")

    if not rules:
        rules.append("No regime signals detected from available data")

    state = "mixed"
    if any("crowded" in r for r in rules):
        state = "crowded_long" if "crowded long" in " ".join(rules).lower() else "crowded_short"
    elif any("leverage building" in r for r in rules):
        state = "leverage_building"
    elif any("declining" in r for r in rules):
        state = "deleveraging" if any("deleveraging" in r for r in rules) else "mixed"

    return {"state": state, "rules": rules}


def _generate_downstream_candidates(changes: list, feed_items: list, contexts: list) -> list[dict]:
    """Generate alert/topic candidates (no sending)."""
    candidates = []
    meaningful = [c for c in changes if c.get("change_type") and c["change_type"] != "NO_CHANGE"]
    for c in meaningful[:5]:
        candidates.append({
            "type": "whale_alert",
            "channel": "telegram_candidate",
            "title": f"Whale {c.get('change_type','')}: {c.get('asset','')}",
            "rationale": f"{c.get('label','Unknown')} {c.get('change_type','')} {c.get('asset','')} (${c.get('current_position_size_usd',0):,.0f})",
            "source": "whale_engine",
            "send": False,
            "_note": "Candidate only — requires Window 1 review before sending",
        })
    return candidates


def run(project_root: Optional[str] = None) -> dict:
    """Run Window 3 pipeline: L3 -> L4 -> L5 -> outputs."""
    root = Path(project_root or _PROJECT)
    run_id = uuid.uuid4().hex[:12]
    started_at = _utc_now()
    warnings: list[str] = []
    degraded_paths: list[str] = []

    # ── L3: Market Context ──
    from market_radar.l3_market_context.market_context_provider import run as l3_run
    l3_result = l3_run()
    if l3_result.total_failed > 0:
        warnings.append(f"L3: {l3_result.total_failed} assets failed")
        degraded_paths.append("L3:market_context")
    contexts = [c.as_dict() for c in l3_result.contexts]

    # ── L4: Existing Feeds ──
    from market_radar.l4_existing_feeds.existing_feeds_adapter import run as l4_run
    l4_result = l4_run(str(root))
    if l4_result.sources_failed > 0:
        warnings.append(f"L4: {l4_result.sources_failed}/{l4_result.sources_checked} sources failed")
        degraded_paths.append("L4:existing_feeds")
    feed_items = [f.as_dict() for f in l4_result.feed_items]

    # ── Watchlists (config-driven) ──
    watchlists = {
        "priority_assets": ["BTC", "ETH", "SOL", "HYPE"],
        "priority_whales": ["Matrixport Related", "loraclexyz", "Unknown HYPE Whale"],
        "priority_sources": ["coindesk", "cointelegraph", "hyperliquid"],
        "priority_topics": ["ETF", "regulatory", "whale", "liquidation", "listing"],
    }

    # ── Market Regime ──
    market_regime = _compute_market_regime(contexts)

    # ── Downstream Candidates ──
    downstream_candidates = _generate_downstream_candidates(
        [], feed_items, contexts
    )

    # ── Event Journal ──
    event_journal = [{
        "timestamp": _utc_now(),
        "summary": f"Window 3 run: {l4_result.total_items} feed items, {len(contexts)} market contexts",
        "feed_count": l4_result.total_items,
        "market_count": len(contexts),
        "health_ok": l4_result.sources_ok,
    }]

    # ── Build Bundle ──
    all_health = []
    all_health.extend(l3_result.source_health)
    all_health.extend(l4_result.source_health)

    bundle = WorkbenchBundle(
        run_id=run_id,
        generated_at=_utc_now(),
        positions=[],  # Populated by Window 1 integration
        changes=[],    # Populated by Window 1 integration
        market_contexts=l3_result.contexts,
        feed_items=l4_result.feed_items,
        source_health=all_health,
        alert_candidates=[],
        watchlists=watchlists,
        event_journal=event_journal,
        market_regime=market_regime,
        downstream_candidates=downstream_candidates,
        warnings=warnings,
        degraded_paths=degraded_paths,
        contracts_version=CONTRACTS_VERSION,
        contracts_sealed_at=CONTRACTS_SEALED_AT,
    )

    # ── Generate Workbench ──
    wb_path = root / "artifacts" / "reports" / "workbench.html"
    wb_json_path = root / "artifacts" / "reports" / "workbench_bundle.json"
    print(f"  Writing workbench to: {wb_path}")
    print(f"  Root is: {root}")
    render_workbench(bundle, str(wb_path))

    # Save bundle as JSON
    wb_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(wb_json_path, "w", encoding="utf-8") as f:
        json.dump(bundle.as_dict(), f, ensure_ascii=False, indent=2)

    # Save evidence
    evidence = {
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": _utc_now(),
        "feed_truth": l4_result.truth.as_dict(),
        "market_succeeded": l3_result.total_succeeded,
        "market_failed": l3_result.total_failed,
        "feed_items": l4_result.total_items,
        "workbench": str(wb_path),
        "warnings": warnings,
        "degraded_paths": degraded_paths,
    }
    ev_path = root / "artifacts" / "evidence" / "window3_evidence.json"
    ev_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ev_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)

    return {
        "run_id": run_id,
        "status": "OK" if not degraded_paths else "DEGRADED",
        "feed_items": l4_result.total_items,
        "market_contexts": len(contexts),
        "workbench": str(wb_path),
        "evidence": str(ev_path),
        "warnings": warnings,
        "degraded_paths": degraded_paths,
        "truth": l4_result.truth.as_dict(),
    }


def main():
    result = run()
    print(f"Window 3 Run: {result['run_id']}")
    print(f"  Status: {result['status']}")
    t = result.get("truth", {})
    print(f"  Feed truth: flash={t.get('flash_count')} news={t.get('news_count')} live={t.get('live_count')}")
    print(f"  Market: {result['market_contexts']} assets")
    print(f"  Feed items: {result['feed_items']}")
    print(f"  Workbench: {result['workbench']}")
    print(f"  Evidence: {result['evidence']}")
    for w in result.get("warnings", []):
        print(f"  WARN: {w}")
    return 0 if result["status"] == "OK" else 1


if __name__ == "__main__":
    main()
