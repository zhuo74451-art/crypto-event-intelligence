"""MVP+ L6 — Integration Main Runner.

Orchestrates L1-L5 lanes into a single unified RunReport:

  1. L1: Fetch whale positions from Hyperliquid (or fixture)
  2. L2: Detect position changes vs previous snapshot
  3. L3: Fetch market context (Binance + CoinGecko)
  4. L4: Read existing feed data (CSV)
  5. Save state: persist current positions for next run
  6. L5: Generate HTML workbench

Outputs:
  - artifacts/reports/run_report.json     — Full RunReport as JSON
  - artifacts/reports/workbench.html      — Self-contained HTML dashboard
  - artifacts/evidence/whale_state.json   — Position state for next comparison
  - artifacts/evidence/run_evidence.json  — Run evidence summary
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from market_radar.shared.contracts import (
    RunReport,
    LaneResult,
    WhalePosition,
    WhalePositionChange,
    MarketContext,
    UnifiedFeedItem,
    SourceHealth,
    SourceStatus,
    CONTRACTS_VERSION,
    CONTRACTS_SEALED_AT,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find_project_root() -> Path:
    """Find the project root (where .git or market_radar/ exists)."""
    path = Path(__file__).resolve().parents[3]  # 4 levels up from l6_integration/
    if (path / "market_radar").is_dir():
        return path
    # Fall back to cwd
    return Path.cwd()


# ── State file paths ─────────────────────────────────────────────────────────

STATE_DIR = "artifacts/evidence"
REPORT_DIR = "artifacts/reports"
STATE_FILE = os.path.join(STATE_DIR, "whale_state.json")
REPORT_FILE = os.path.join(REPORT_DIR, "run_report.json")
WORKBENCH_FILE = os.path.join(REPORT_DIR, "workbench.html")
EVIDENCE_FILE = os.path.join(STATE_DIR, "run_evidence.json")


def run(project_root: str | None = None, use_fixture: bool = False) -> RunReport:
    """Execute full MVP+ pipeline: L1 -> L2 -> L3 -> L4 -> L5.

    Args:
        project_root: Override project root path (default: auto-detect).
        use_fixture: If True, use fixture data instead of live APIs.

    Returns:
        RunReport with all lane outputs.
    """
    run_id = uuid.uuid4().hex[:12]
    started_at = _utc_now()
    root = Path(project_root) if project_root else _find_project_root()
    warnings: list[str] = []
    known_limitations: list[str] = [
        "One-shot scan: data reflects single point in time",
        "Hyperliquid whale positions limited to tracked address list",
        "Liquidation distance computed from mark price approximation",
        "No persistent storage — previous state resets on each run",
    ]
    degraded_paths: list[str] = []
    lane_results: dict[str, LaneResult] = {}

    # ── L1: Whale Position Fetcher ──
    l1_start = _utc_now()
    l1_positions: list[WhalePosition] = []
    l1_health: Optional[SourceHealth] = None
    l1_error: Optional[str] = None
    try:
        from market_radar.l1_hyperliquid_provider.whale_position_fetcher import WhalePositionFetcher
        fetcher = WhalePositionFetcher(use_fixture=use_fixture)
        l1_positions, l1_health = fetcher.fetch()
        if not l1_positions:
            warnings.append("L1: No whale positions returned from fetcher")
            if l1_health and l1_health.status == SourceStatus.DEGRADED:
                degraded_paths.append("L1:whale_position_fetcher")
    except Exception as e:
        l1_error = f"L1 FETCH ERROR: {type(e).__name__}: {e}"
        warnings.append(l1_error)
        degraded_paths.append("L1:whale_position_fetcher")
    l1_completed = _utc_now()
    lane_results["L1"] = LaneResult(
        lane_id="L1", status="OK" if not l1_error else "DEGRADED",
        item_count=len(l1_positions), errors=[l1_error] if l1_error else [],
        warnings=[w for w in warnings if w.startswith("L1")],
        started_at=l1_start, completed_at=l1_completed,
    )

    # ── L2: Position Change Detection ──
    l2_start = _utc_now()
    l2_changes: list[WhalePositionChange] = []
    l2_health_list: list[SourceHealth] = []
    l2_error: Optional[str] = None
    try:
        from market_radar.l2_whale_engine.whale_engine import compute_changes

        # Load previous positions from state file
        state_path = root / STATE_FILE
        previous_positions: list[WhalePosition] = []
        if state_path.exists():
            try:
                with open(state_path, "r", encoding="utf-8") as f:
                    prev_data = json.load(f)
                for item in prev_data:
                    if all(k in item for k in ("address", "asset", "side", "position_size_usd", "observed_at")):
                        from market_radar.shared.contracts import PositionSide
                        previous_positions.append(WhalePosition(
                            address=item["address"],
                            asset=item["asset"],
                            side=PositionSide(item["side"]),
                            position_size_usd=item["position_size_usd"],
                            observed_at=item.get("observed_at", ""),
                            entry_price=item.get("entry_price"),
                            mark_price=item.get("mark_price"),
                            leverage=item.get("leverage"),
                            unrealized_pnl_usd=item.get("unrealized_pnl_usd"),
                            margin_used_usd=item.get("margin_used_usd"),
                            liquidation_price=item.get("liquidation_price"),
                            liquidation_distance_pct=item.get("liquidation_distance_pct"),
                            label=item.get("label"),
                            data_origin=item.get("data_origin", "previous"),
                            source=item.get("source", "previous_run"),
                        ))
            except (json.JSONDecodeError, OSError) as e:
                warnings.append(f"L2: Could not load previous state: {type(e).__name__}")

        l2_result = compute_changes(l1_positions, previous_positions)
        l2_changes = l2_result.changes
        l2_health_list = l2_result.source_health

        # Save current positions for next run
        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            pos_data = [p.as_dict() for p in l1_positions]
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(pos_data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            warnings.append(f"L2: Could not save state: {type(e).__name__}")

        if l2_result.total_changes == 0 and l1_positions:
            warnings.append("L2: No changes detected between snapshots")

    except Exception as e:
        l2_error = f"L2 ENGINE ERROR: {type(e).__name__}: {e}"
        warnings.append(l2_error)
        degraded_paths.append("L2:whale_engine")
    l2_completed = _utc_now()
    lane_results["L2"] = LaneResult(
        lane_id="L2", status="OK" if not l2_error else "DEGRADED",
        item_count=len(l2_changes), errors=[l2_error] if l2_error else [],
        warnings=[w for w in warnings if w.startswith("L2")],
        started_at=l2_start, completed_at=l2_completed,
    )

    # ── L3: Market Context ──
    l3_start = _utc_now()
    l3_contexts: list[MarketContext] = []
    l3_health_list: list[SourceHealth] = []
    l3_error: Optional[str] = None
    try:
        from market_radar.l3_market_context.market_context_provider import run as l3_run
        l3_result = l3_run()
        l3_contexts = l3_result.contexts
        l3_health_list = l3_result.source_health
        if l3_result.total_failed > 0:
            warnings.append(f"L3: {l3_result.total_failed}/{l3_result.total_requested} symbols failed")
            degraded_paths.append("L3:market_context")
        if l3_result.error:
            l3_error = l3_result.error
    except Exception as e:
        l3_error = f"L3 CONTEXT ERROR: {type(e).__name__}: {e}"
        warnings.append(l3_error)
        degraded_paths.append("L3:market_context")
    l3_completed = _utc_now()
    lane_results["L3"] = LaneResult(
        lane_id="L3", status="OK" if not l3_error else "DEGRADED",
        item_count=len(l3_contexts), errors=[l3_error] if l3_error else [],
        warnings=[w for w in warnings if w.startswith("L3")],
        started_at=l3_start, completed_at=l3_completed,
    )

    # ── L4: Existing Feeds ──
    l4_start = _utc_now()
    l4_items: list[UnifiedFeedItem] = []
    l4_health_list: list[SourceHealth] = []
    l4_error: Optional[str] = None
    try:
        from market_radar.l4_existing_feeds.existing_feeds_adapter import run as l4_run
        l4_result = l4_run(str(root))
        l4_items = l4_result.feed_items
        l4_health_list = l4_result.source_health
        if l4_result.sources_failed > 0:
            warnings.append(f"L4: {l4_result.sources_failed}/{l4_result.sources_checked} sources unavailable")
            degraded_paths.append("L4:existing_feeds")
    except Exception as e:
        l4_error = f"L4 FEEDS ERROR: {type(e).__name__}: {e}"
        warnings.append(l4_error)
        degraded_paths.append("L4:existing_feeds")
    l4_completed = _utc_now()
    lane_results["L4"] = LaneResult(
        lane_id="L4", status="OK" if not l4_error else "DEGRADED",
        item_count=len(l4_items), errors=[l4_error] if l4_error else [],
        warnings=[w for w in warnings if w.startswith("L4")],
        started_at=l4_start, completed_at=l4_completed,
    )

    # ── Build RunReport ──
    completed_at = _utc_now()

    # Collect all source health
    all_health: list[SourceHealth] = []
    if l1_health:
        all_health.append(l1_health)
    if l2_health_list:
        all_health.extend(l2_health_list)
    if l3_health_list:
        all_health.extend(l3_health_list)
    if l4_health_list:
        all_health.extend(l4_health_list)

    report = RunReport(
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
        whale_positions=l1_positions,
        whale_changes=l2_changes,
        market_contexts=l3_contexts,
        feed_items=l4_items,
        source_health=all_health,
        lane_results=lane_results,
        error=None,
        warnings=warnings,
        known_limitations=known_limitations,
        degraded_paths=degraded_paths,
        contracts_version=CONTRACTS_VERSION,
        contracts_sealed_at=CONTRACTS_SEALED_AT,
    )

    # ── L5: Workbench HTML ──
    l5_start = _utc_now()
    l5_error: Optional[str] = None
    try:
        from market_radar.l5_workbench_ui.workbench_renderer import render_workbench
        wb_path = root / WORKBENCH_FILE
        render_workbench(report, str(wb_path))
        report.workbench_html_path = str(wb_path.resolve())
        report.workbench_html_name = wb_path.name
    except Exception as e:
        l5_error = f"L5 RENDER ERROR: {type(e).__name__}: {e}"
        warnings.append(l5_error)
        degraded_paths.append("L5:workbench_ui")
    l5_completed = _utc_now()
    lane_results["L5"] = LaneResult(
        lane_id="L5", status="OK" if not l5_error else "DEGRADED",
        item_count=1, errors=[l5_error] if l5_error else [],
        started_at=l5_start, completed_at=l5_completed,
    )

    # ── Save RunReport JSON ──
    try:
        report_path = root / REPORT_FILE
        report_path.parent.mkdir(parents=True, exist_ok=True)
        rp_data = report.as_dict()
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(rp_data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        warnings.append(f"Save report failed: {type(e).__name__}: {e}")

    # ── Save evidence summary ──
    try:
        evidence_path = root / EVIDENCE_FILE
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence = {
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "positions_count": len(l1_positions),
            "changes_count": len(l2_changes),
            "meaningful_changes": len([c for c in l2_changes if c.change_type.value != "NO_CHANGE"]),
            "market_contexts_count": len(l3_contexts),
            "feed_items_count": len(l4_items),
            "source_health_count": len(all_health),
            "ok_sources": len([h for h in all_health if h.status == SourceStatus.OK]),
            "degraded_sources": len([h for h in all_health if h.status == SourceStatus.DEGRADED]),
            "failed_sources": len([h for h in all_health if h.status == SourceStatus.FAILED]),
            "warnings": warnings,
            "degraded_paths": degraded_paths,
        }
        with open(evidence_path, "w", encoding="utf-8") as f:
            json.dump(evidence, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

    return report


def main():
    """CLI entry: run full MVP+ pipeline and print summary."""
    import argparse
    parser = argparse.ArgumentParser(description="MVP+ Crypto Signal Intelligence Workbench")
    parser.add_argument("--fixture", action="store_true", help="Use fixture data (no live API calls)")
    parser.add_argument("--project-root", default=None, help="Override project root path")
    args = parser.parse_args()

    print(f"Crypto Signal Intelligence — MVP+ Workbench")
    print(f"{'='*60}")
    print(f"Mode: {'FIXTURE' if args.fixture else 'LIVE'}")
    print()

    report = run(project_root=args.project_root, use_fixture=args.fixture)

    print(f"\nRun ID: {report.run_id}")
    print(f"Started: {report.started_at}")
    print(f"Completed: {report.completed_at}")
    print(f"{'='*60}")

    # Lane summaries
    for lid in sorted(report.lane_results.keys()):
        lr = report.lane_results[lid]
        print(f"  {lid}: {lr.status} ({lr.item_count} items, {lr.error_count} errors)")
        for e in lr.errors:
            print(f"    ERROR: {e}")
        for w in lr.warnings:
            print(f"    WARN: {w}")

    print(f"\n{'='*60}")
    print(f"Whale Positions: {len(report.whale_positions)}")
    for p in report.whale_positions:
        print(f"  {p.label or 'Unknown':25s} | {p.asset:5s} | {p.side.value:5s} | ${p.position_size_usd:>12,.2f} | "
              f"PnL: ${(p.unrealized_pnl_usd or 0):>10,.2f} | LiqDist: {p.liquidation_distance_pct or 'N/A'}")

    print(f"\nPosition Changes: {len(report.whale_changes)}")
    meaningful = [c for c in report.whale_changes if c.change_type.value != "NO_CHANGE"]
    for c in meaningful:
        print(f"  {c.label or 'Unknown':25s} | {c.asset:5s} | {c.change_type.value:20s} | "
              f"risk={c.risk_level.value} | delta={c.position_delta_usd or 'N/A'}")

    print(f"\nMarket Context: {len(report.market_contexts)} assets")
    for ctx in report.market_contexts:
        chg_str = f"{ctx.price_change_24h_pct:+.2f}%" if ctx.price_change_24h_pct is not None else "N/A"
        print(f"  {ctx.symbol:5s} | ${ctx.price:>8,.2f} | 24h: {chg_str}")

    print(f"\nFeed Items: {len(report.feed_items)}")

    print(f"\nSource Health: {len(report.source_health)} sources")
    for h in report.source_health:
        print(f"  {h.source_name:30s} | {h.status.value:10s} | OK={h.success_count} | Err={h.error_count}")

    wb = report.workbench_html_path or "N/A"
    print(f"\nWorkbench: {wb}")

    print(f"\nWarnings: {len(report.warnings)}")
    for w in report.warnings:
        print(f"  [WARN] {w}")

    if report.degraded_paths:
        print(f"\nDegraded paths: {len(report.degraded_paths)}")
        for d in report.degraded_paths:
            print(f"  [DEGRADED] {d}")

    if report.error:
        print(f"\nFATAL: {report.error}")
        return 2

    print(f"\n{'='*60}")
    print(f"MVP+ Workbench Complete")
    print(f"Evidence: artifacts/evidence/run_evidence.json")
    print(f"Report:   {report.workbench_html_path or 'N/A'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
