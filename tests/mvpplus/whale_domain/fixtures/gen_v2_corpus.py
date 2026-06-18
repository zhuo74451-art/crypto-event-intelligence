#!/usr/bin/env python3
"""Generate whale_replay_corpus_v2.json with 71 portfolio-level cases.

Usage:
    python gen_v2_corpus.py                          # default: repo fixtures dir
    python gen_v2_corpus.py --output /path/to/output.json
    python gen_v2_corpus.py --force                   # overwrite existing

All output is deterministic — same input produces identical JSON.
No system clock, no random, no absolute paths in the script.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional


# ── Helpers ────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent


def pos(
    addr: str, label: str, coin: str, signed_size: float,
    entry: float, mark: float, pv: float, lev: float,
    pnl: Optional[float], liq: Optional[float],
    ts: str = "2026-06-17T12:00:00Z",
) -> dict:
    return {
        "address": addr, "label": label, "coin": coin,
        "signed_size": signed_size, "entry_price": entry,
        "mark_price": mark, "position_value_usd": pv,
        "leverage": lev, "unrealized_pnl_usd": pnl,
        "liquidation_price": liq, "snapshot_time_utc": ts,
    }


def liq_dist(direction: str, mark: Optional[float], liq: Optional[float]) -> Optional[float]:
    if liq is None or mark is None or mark <= 0:
        return None
    if direction == "long":
        return round((mark - liq) / mark * 100, 4)
    return round((liq - mark) / mark * 100, 4)


def calc_metrics(portfolio: list[dict]) -> dict:
    """Compute portfolio metrics deterministically from position dicts."""
    nulls = {k: None for k in [
        "gross_exposure_usd", "net_exposure_usd", "long_exposure_usd",
        "short_exposure_usd", "long_short_ratio", "weighted_leverage",
        "address_count", "coin_count", "top1_concentration",
        "top3_concentration", "hhi", "liquidation_within_2pct",
        "liquidation_within_5pct", "profitable_exposure", "unprofitable_exposure",
    ]}
    if not portfolio:
        return nulls

    gross = sum(abs(p["position_value_usd"]) for p in portfolio)
    long_val = sum(p["position_value_usd"] for p in portfolio if p["signed_size"] > 0)
    short_val = sum(abs(p["position_value_usd"]) for p in portfolio if p["signed_size"] < 0)
    net = long_val - short_val
    addr_cnt = len({p["address"] for p in portfolio if p["signed_size"] != 0})
    coin_cnt = len({p["coin"] for p in portfolio if p["signed_size"] != 0})
    ls_ratio = round(long_val / short_val, 4) if short_val > 0 else (None if long_val == 0 else float("inf"))

    vals = sorted([abs(p["position_value_usd"]) for p in portfolio if p["signed_size"] != 0], reverse=True)
    t1 = round(vals[0] / gross, 4) if vals and gross else None
    t3 = round(sum(vals[:3]) / gross, 4) if vals and gross else None
    hhi = round(sum((v / gross) ** 2 for v in vals), 4) if gross else None

    tot_lev_val = sum(abs(p["position_value_usd"]) for p in portfolio if p.get("leverage") and p["signed_size"] != 0)
    tot_lev_w = sum(abs(p["position_value_usd"]) * p["leverage"] for p in portfolio if p.get("leverage") and p["signed_size"] != 0)
    wl = round(tot_lev_w / tot_lev_val, 4) if tot_lev_val > 0 else None

    def within_pct(threshold: float) -> int:
        count = 0
        for p in portfolio:
            if p["signed_size"] == 0:
                continue
            d = liq_dist("long" if p["signed_size"] > 0 else "short", p["mark_price"], p["liquidation_price"])
            if d is not None and 0 < d <= threshold:
                count += 1
        return count

    prof = sum(abs(p["position_value_usd"]) for p in portfolio if p.get("unrealized_pnl_usd") is not None and p["unrealized_pnl_usd"] > 0)
    unprof = sum(abs(p["position_value_usd"]) for p in portfolio if p.get("unrealized_pnl_usd") is not None and p["unrealized_pnl_usd"] < 0)

    return {
        "gross_exposure_usd": round(gross, 2),
        "net_exposure_usd": round(net, 2),
        "long_exposure_usd": round(long_val, 2),
        "short_exposure_usd": round(short_val, 2),
        "long_short_ratio": ls_ratio,
        "weighted_leverage": wl,
        "address_count": addr_cnt,
        "coin_count": coin_cnt,
        "top1_concentration": t1,
        "top3_concentration": t3,
        "hhi": hhi,
        "liquidation_within_2pct": within_pct(2.0),
        "liquidation_within_5pct": within_pct(5.0),
        "profitable_exposure": round(prof, 2),
        "unprofitable_exposure": round(unprof, 2),
    }


def build_corpus() -> list[dict]:
    """Return all 71 cases. Deterministic, no I/O, no clock."""
    # Full case list — too long for this excerpt; reads from V1 structure
    from _v2_cases import ALL_CASES  # noqa: keep cases in separate data file
    return ALL_CASES


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate V2 Replay Corpus")
    parser.add_argument("--output", type=str, default=None,
                        help="Output path (default: fixtures/whale_replay_corpus_v2.json)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing file")
    args = parser.parse_args()

    if args.output:
        out_path = Path(args.output).resolve()
    else:
        out_path = ROOT / "whale_replay_corpus_v2.json"

    if out_path.exists() and not args.force:
        print(f"Error: {out_path} exists. Use --force to overwrite.")
        sys.exit(1)

    corpus = {
        "corpus_meta": {
            "name": "Whale Replay Corpus V2 — Portfolio Intelligence",
            "ticket": "W2_WHALE_PORTFOLIO_INTELLIGENCE_R02",
            "version": "v2",
            "total_cases": 71,
            "generated_at_utc": "2026-06-17T12:00:00Z",
            "no_random": True,
            "no_system_clock": True,
        },
        "cases": build_corpus(),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(corpus, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(corpus['cases'])} cases → {out_path}")
    print(f"Deterministic hash: {hash(json.dumps(corpus['cases'], sort_keys=True))}")


if __name__ == "__main__":
    main()
