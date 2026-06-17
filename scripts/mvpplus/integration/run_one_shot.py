#!/usr/bin/env python3
"""One-shot integration runner CLI — no-send, read-only.

Usage:
    python scripts/mvpplus/integration/run_one_shot.py --mode fixture
    python scripts/mvpplus/integration/run_one_shot.py --mode live-public --whale-address 0x... --exchange binance

--no-send is always true. The program refuses to run if disabled.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from market_radar.integration.models import IntegrationConfig
from market_radar.integration.one_shot import run_one_shot


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="No-send one-shot integration runner (read-only).",
    )
    p.add_argument("--mode", choices=["fixture", "live-public"], default="fixture",
                    help="Run mode (default: fixture). live-public requires explicit flag.")
    p.add_argument("--state-dir", default="data/integration/state",
                    help="State directory for locks, DBs, stop marker.")
    p.add_argument("--output-dir", default="data/integration/output",
                    help="Output directory for run artifacts.")
    p.add_argument("--whale-address", default="",
                    help="Whale address for clearinghouseState probe.")
    p.add_argument("--exchange", default="binance",
                    help="Exchange for CCXT ticker (default: binance).")
    p.add_argument("--timeout", type=float, default=30.0,
                    help="Network timeout in seconds.")
    p.add_argument("--no-send", action="store_true", default=True,
                    help="Must remain true. This flag is for clarity only.")
    p.add_argument("--no-send-disable", action="store_true", dest="no_send_disable",
                    help=argparse.SUPPRESS)
    p.add_argument("--feed-since", default=None,
                    help="Initial feed cursor (UTC ISO 8601) for first run.")
    p.add_argument("--curated-base-url",
                    default="http://43.98.174.247:8001/api/integration/curated",
                    help="Curated API base URL.")
    p.add_argument("--feed-limit", type=int, default=100,
                    help="Feed items per page (1-500).")
    p.add_argument("--feed-max-items", type=int, default=500,
                    help="Max feed items to accept (1-5000).")
    p.add_argument("--feed-timeout", type=float, default=15.0,
                    help="Feed HTTP timeout in seconds.")
    p.add_argument("--curated-max-pages", type=int, default=5,
                    help="Max curated API pages (1-10).")
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # --no-send enforcement
    if args.no_send_disable:
        print("ERROR: --no-send cannot be disabled. This program is read-only.", file=sys.stderr)
        return 1

    # Build CuratedFeedProvider for live-public mode
    provider = None
    if args.mode == "live-public":
        from market_radar.integration.curated_feed_provider import CuratedFeedProvider
        provider = CuratedFeedProvider(
            base_url=args.curated_base_url,
            limit=args.feed_limit,
            max_items=args.feed_max_items,
            max_pages=args.curated_max_pages,
            timeout_seconds=args.feed_timeout,
        )

    config = IntegrationConfig(
        mode=args.mode,
        state_dir=args.state_dir,
        output_dir=args.output_dir,
        whale_address=args.whale_address or "",
        exchange=args.exchange,
        timeout=args.timeout,
        no_send=True,
        feed_initial_since=args.feed_since,
        feed_enabled=(args.mode == "live-public"),
    )

    result = run_one_shot(config, feed_provider=provider)

    # Print report to stdout
    print(json.dumps(result.as_dict(), indent=2, default=str))

    # Summary
    print(f"\n--- Run {result.run_id} ---", file=sys.stderr)
    print(f"  status:     {result.status}", file=sys.stderr)
    print(f"  data_mode:  {result.data_mode}", file=sys.stderr)
    print(f"  whale_ok:   {result.whale.ok if result.whale else 'N/A'}", file=sys.stderr)
    print(f"  markets:    {len(result.markets)} assets", file=sys.stderr)
    print(f"  feed_items: {result.feed.live_count if result.feed else 0} live, "
          f"{result.feed.fixture_count if result.feed else 0} fixture", file=sys.stderr)
    print(f"  errors:     {len(result.errors)}", file=sys.stderr)
    print(f"  outputs:    {len(result.output_paths)} files", file=sys.stderr)

    if args.mode == "fixture":
        return 0
    return 0 if result.status in ("completed", "degraded") else 1


if __name__ == "__main__":
    sys.exit(main())
