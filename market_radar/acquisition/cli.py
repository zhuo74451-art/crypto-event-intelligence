"""CLI — one-shot source & evidence pilot.

Usage
-----
Replay mode (no network):
    python -X utf8 -m market_radar.acquisition.cli --mode replay --sources all --limit 20

Live mode:
    python -X utf8 -m market_radar.acquisition.cli --mode live --sources cisa,sec --limit 20
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from market_radar.acquisition.pilot_runner import create_pilot_runner
from market_radar.operations.run_once import run_once


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Source & Evidence Pilot V1 — one-shot acquisition runner",
    )
    p.add_argument(
        "--mode",
        choices=["live", "replay"],
        default="replay",
        help="Execution mode (default: replay)",
    )
    p.add_argument(
        "--sources",
        default="all",
        help="Comma-separated source IDs or 'all' (default: all)",
    )
    p.add_argument("--limit", type=int, default=20, help="Max observations per source")
    p.add_argument("--timeout", type=int, default=None, help="Per-request timeout (seconds)")
    p.add_argument("--output", type=str, default="", help="Output directory path")
    p.add_argument(
        "--sec-user-agent",
        type=str,
        default=None,
        help="User-Agent for SEC requests (overrides env var)",
    )
    return p


def resolve_sources(raw: str) -> list[str]:
    if raw == "all":
        return ["cisa", "sec", "congress", "bls"]
    return [s.strip() for s in raw.split(",")]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    run_id = f"pilot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    sources = resolve_sources(args.sources)
    output_dir = args.output or str(
        Path.cwd() / "results" / "source_evidence_pilot" / run_id
    )

    runner = create_pilot_runner(
        sources=sources,
        limit=args.limit,
        timeout=args.timeout,
        sec_user_agent=args.sec_user_agent,
        output_dir=output_dir,
        mode=args.mode,
    )

    result = run_once(runner, run_id=run_id)

    # Print summary to stdout
    print(f"Run ID:        {result.run_id}")
    print(f"Runner:        {result.runner_label}")
    print(f"Status:        {result.status}")
    print(f"Output:        {output_dir}")
    if result.error:
        print(f"Error:         {result.error}")
    if result.summary:
        summary = result.summary
        print(f"Observations:  {summary.get('total_observations', '?')}")
        print(f"Sources:       {summary.get('source_ids', [])}")
        if summary.get("errors"):
            for e in summary["errors"]:
                print(f"  - {e}")

    return 0 if result.status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
