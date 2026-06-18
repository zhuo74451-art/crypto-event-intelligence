#!/usr/bin/env python3
"""W3v2 — Feeds + Market + Workbench orchestration.

Loads fixtures, builds bundle, renders workbench, captures evidence.
No network access.
"""
import json, os, sys, uuid
from datetime import timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.chdir(str(ROOT))

from market_radar.intelligence_feed import FeedDataMode
from market_radar.intelligence_feed.feed_loader import load_feed
from market_radar.market_view import load_market_view
from market_radar.workbench import WorkbenchBundle, render_workbench


def main():
    run_id = "w3_" + uuid.uuid4().hex[:8]

    # L3: Feed
    feed_result = load_feed()
    feed_truth = feed_result.truth.as_dict()
    feed_items = feed_result.items

    # L4: Market
    market_result = load_market_view()

    # Build bundle
    bundle = WorkbenchBundle(
        run_id=run_id,
        generated_at=__import__("datetime").datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        feed_items=feed_items,
        market_snapshots=market_result.snapshots,
        market_health=market_result.health,
        feed_truth=feed_truth,
        watchlists={
            "priority_assets": ["BTC", "ETH", "SOL", "HYPE"],
            "priority_sources": ["coindesk", "cointelegraph", "theblock", "hl_watcher"],
            "priority_topics": ["whale", "ETF", "liquidation"],
        },
        event_journal=[{
            "timestamp": __import__("datetime").datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": f"W3 run: {len(feed_items)} feed items, {len(market_result.snapshots)} market assets",
        }],
    )

    # Render workbench
    wb_path = ROOT / "artifacts" / "reports" / "workbench.html"
    render_workbench(bundle, str(wb_path))

    # Evidence
    evidence = {
        "run_id": run_id,
        "feed_truth": feed_truth,
        "market_snapshots": [s.as_dict() for s in market_result.snapshots],
        "market_health": [{"venue": h.venue.value, "asset": h.asset, "status": h.status}
                          for h in market_result.health],
        "workbench_path": str(wb_path),
    }
    ev_path = ROOT / "artifacts" / "evidence" / "w3_feeds_market_ui_report.json"
    ev_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ev_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)

    # Summary
    ft = feed_truth
    print(f"W3v2 Run: {run_id}")
    print(f"  Feed: flash={ft.get('flash_live')} news={ft.get('news_live')} tg={ft.get('telegram_live')} "
          f"live_total={ft.get('live_total')} fixture={ft.get('fixture')} research={ft.get('research_sample')}")
    print(f"  Market: {len(market_result.snapshots)} assets ({market_result.live_sources} live, {market_result.degraded_sources} degraded)")
    for s in market_result.snapshots:
        print(f"    {s.symbol:5s} ${s.price:>8,.2f} OI={_usd(s.open_interest)} fund={s.funding_rate}")
    print(f"  Workbench: {wb_path}")
    print(f"  Evidence: {ev_path}")


def _usd(v):
    if v is None: return "N/A"
    try:
        x = float(v)
        if abs(x) >= 1e9: return f"${x/1e9:.2f}B"
        if abs(x) >= 1e6: return f"${x/1e6:.2f}M"
        if abs(x) >= 1e3: return f"${x/1e3:.1f}K"
        return f"${x:.2f}"
    except: return str(v)


if __name__ == "__main__":
    main()
