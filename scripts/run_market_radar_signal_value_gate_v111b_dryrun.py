"""Market Radar v1.11-B — Signal Value Gate Dry-Run

Reads signals (live fetch or fixture) and evaluates each through the
SignalValueGate. Outputs a structured JSON report. No TG send, no secrets.

Usage:
    python scripts/run_market_radar_signal_value_gate_v111b_dryrun.py
    python scripts/run_market_radar_signal_value_gate_v111b_dryrun.py --no-live
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))

sys.path.insert(0, str(ROOT))

from scripts.market_radar_signal_value_gate_v111b import evaluate_signal_value, GATE_VERSION


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Market Radar v1.11-B — Signal Value Gate Dry-Run"
    )
    parser.add_argument(
        "--no-live",
        action="store_true",
        help="Skip live fetch, use fixture signals only",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "market_radar_v111b_signal_value_gate_dryrun.json"),
        help="Output path for dry-run result JSON",
    )
    return parser.parse_args()


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


# ── Fixture signals ───────────────────────────────────────────────────────────

def _fixture_signals() -> list[dict]:
    """Realistic fixture signals based on v1.11-A review findings."""
    return [
        # allow: price + OI + volume (high quality)
        {
            "signal_type": "market_anomaly",
            "asset": "BTC",
            "core_entity": "BTC",
            "price_change_pct": -5.54,
            "open_interest": 1_826_000_000,
            "volume": 6_345_000_000,
            "funding_rate": 0.00004,
            "source": "hyperliquid",
            "source_type": "api",
            "status": "ok",
            "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger_reason": "BTC 24h 跌幅 5.54% + OI 18.26亿",
        },
        # allow: price + funding extreme
        {
            "signal_type": "market_anomaly",
            "asset": "ETH",
            "core_entity": "ETH",
            "price_change_pct": -8.2,
            "open_interest": 890_000_000,
            "funding_rate": -0.025,
            "source": "hyperliquid",
            "source_type": "api",
            "status": "ok",
            "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger_reason": "ETH 跌幅 8.2% + funding -2.5% extreme",
        },
        # allow: strong price + volume
        {
            "signal_type": "market_anomaly",
            "asset": "SOL",
            "core_entity": "SOL",
            "price_change_pct": -11.5,
            "volume": 1_200_000_000,
            "source": "hyperliquid",
            "source_type": "api",
            "status": "ok",
            "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger_reason": "SOL 跌幅 11.5% strong + volume surge",
        },
        # observe: price only, no confirmation
        {
            "signal_type": "market_anomaly",
            "asset": "ARB",
            "core_entity": "ARB",
            "price_change_pct": -7.55,
            "open_interest": 4_656_700,
            "source": "hyperliquid",
            "source_type": "api",
            "status": "ok",
            "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger_reason": "ARB 跌幅 7.55% (小市值, OI极小)",
        },
        # observe: price with near-zero funding
        {
            "signal_type": "market_anomaly",
            "asset": "SUI",
            "core_entity": "SUI",
            "price_change_pct": -6.73,
            "open_interest": 27_997_200,
            "funding_rate": 0.00004,
            "source": "hyperliquid",
            "source_type": "api",
            "status": "ok",
            "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger_reason": "SUI 跌幅 6.73% (funding ~0%)",
        },
        # block: price < 5%
        {
            "signal_type": "market_anomaly",
            "asset": "LINK",
            "core_entity": "LINK",
            "price_change_pct": -3.2,
            "open_interest": 150_000_000,
            "source": "hyperliquid",
            "source_type": "api",
            "status": "ok",
            "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger_reason": "LINK 仅跌 3.2%, 未触发异常阈值",
        },
        # block: no price_change_pct
        {
            "signal_type": "market_anomaly",
            "asset": "DOT",
            "core_entity": "DOT",
            "source": "hyperliquid",
            "source_type": "api",
            "status": "ok",
            "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger_reason": "DOT 无可用价格数据",
        },
        # non market_anomaly: should still be evaluable
        {
            "signal_type": "onchain_position",
            "asset": "HYPE",
            "core_entity": "HYPE",
            "price_change_pct": 15.0,
            "open_interest": 450_000_000,
            "volume": 890_000_000,
            "source": "hyperliquid",
            "source_type": "api",
            "status": "ok",
            "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger_reason": "HYPE +15% with OI spike",
        },
    ]


# ── Live fetch (minimal, reuses existing infrastructure) ──────────────────────

def _try_live_fetch() -> list[dict]:
    """Attempt to fetch live signals using existing free_sources module."""
    signals: list[dict] = []
    try:
        from scripts.market_radar_free_sources import fetch_market_anomaly_public
        symbols = ["BTC", "ETH", "SOL", "ARB", "SUI", "HYPE", "AVAX", "LINK", "DOT"]
        anomaly_signals = fetch_market_anomaly_public(symbols, timeout=8)
        signals.extend(anomaly_signals)
    except Exception:
        pass
    return signals


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    print(f"Market Radar v1.11-B Signal Value Gate Dry-Run: {china_stamp()}")
    print(f"Gate version: {GATE_VERSION}")

    # Gather signals
    signals: list[dict] = []

    if not args.no_live:
        print("\n[1/3] Attempting live fetch...")
        live_signals = _try_live_fetch()
        ok_live = [s for s in live_signals if s.get("status") == "ok"]
        print(f"  Live signals fetched: {len(ok_live)} ok / {len(live_signals)} total")
        signals.extend(ok_live)

    # Always add fixture signals to ensure diverse coverage
    fixtures = _fixture_signals()
    if not signals:
        print("\n[1/3] Using fixture signals (no live data available)")
        signals = fixtures
    else:
        # Add fixtures not already covered
        existing_assets = {s.get("asset", "") for s in signals}
        for f in fixtures:
            if f.get("asset") not in existing_assets:
                signals.append(f)
        print(f"  Total signals (live + fixture): {len(signals)}")

    # ── Run value gate on each signal ──
    print(f"\n[2/3] Evaluating {len(signals)} signals through SignalValueGate...")

    results: list[dict] = []
    for sig in signals:
        # Build multi-asset context from all signals
        context = {"signals": signals}
        gate_result = evaluate_signal_value(sig, context)

        entry = {
            "asset": sig.get("asset", "unknown"),
            "signal_type": sig.get("signal_type", "unknown"),
            "price_change_pct": sig.get("price_change_pct"),
            "open_interest": sig.get("open_interest"),
            "volume": sig.get("volume"),
            "funding_rate": sig.get("funding_rate"),
            "gate_result": gate_result,
        }
        results.append(entry)

        decision = gate_result["decision"]
        score = gate_result["value_score"]
        asset = entry["asset"]
        print(f"  [{decision.upper():7s}] {asset:6s} score={score:3d} tier={gate_result['value_tier']}")

    # ── Aggregate statistics ──
    allow_count = sum(1 for r in results if r["gate_result"]["decision"] == "allow")
    observe_count = sum(1 for r in results if r["gate_result"]["decision"] == "observe")
    block_count = sum(1 for r in results if r["gate_result"]["decision"] == "block")

    allowed_assets = [r["asset"] for r in results if r["gate_result"]["decision"] == "allow"]
    observed_assets = [r["asset"] for r in results if r["gate_result"]["decision"] == "observe"]
    blocked_assets = [r["asset"] for r in results if r["gate_result"]["decision"] == "block"]

    # Collect all warnings
    all_warnings: list[str] = []
    for r in results:
        for w in r["gate_result"].get("warnings", []):
            if w not in all_warnings:
                all_warnings.append(w)

    # Decision breakdown
    decision_breakdown: dict[str, int] = {}
    for r in results:
        d = r["gate_result"]["decision"]
        decision_breakdown[d] = decision_breakdown.get(d, 0) + 1

    report = {
        "gate_version": GATE_VERSION,
        "generated_at": china_stamp(),
        "total_signals": len(results),
        "allow_count": allow_count,
        "observe_count": observe_count,
        "block_count": block_count,
        "allowed_assets": allowed_assets,
        "observed_assets": observed_assets,
        "blocked_assets": blocked_assets,
        "decision_breakdown": decision_breakdown,
        "warnings": all_warnings,
        "details": results,
    }

    # ── Write output ──
    print(f"\n[3/3] Writing dry-run report to {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    # ── Summary ──
    print(f"\n{'=' * 60}")
    print(f"SignalValueGate Dry-Run Summary")
    print(f"{'=' * 60}")
    print(f"  Total signals:    {len(results)}")
    print(f"  Allowed:          {allow_count}  ({', '.join(allowed_assets) if allowed_assets else 'none'})")
    print(f"  Observe:          {observe_count}  ({', '.join(observed_assets) if observed_assets else 'none'})")
    print(f"  Blocked:          {block_count}  ({', '.join(blocked_assets) if blocked_assets else 'none'})")
    if all_warnings:
        print(f"  Warnings:         {len(all_warnings)}")
        for w in all_warnings[:5]:
            print(f"    - {w}")
    print(f"\n  TG send:          NONE (dry-run only)")
    print(f"  Secrets loaded:   NONE")
    print(f"  Paid APIs:        NONE")
    print(f"\n  Report written to: {output_path}")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
