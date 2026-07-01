"""Cognition CLI - calls integrated program runner."""
from __future__ import annotations
import argparse, json, sys, uuid
from datetime import datetime, timezone
from pathlib import Path
from market_radar.cognition.program_runner import run_program
from market_radar.cognition.contracts import utc_now

def build_parser():
    p = argparse.ArgumentParser(description="Cognition Spine V1")
    p.add_argument("--mode", choices=["live", "replay"], default="replay")
    p.add_argument("--input", type=str, required=True)
    p.add_argument("--output", type=str, default="")
    p.add_argument("--as-of", type=str, default="")
    p.add_argument("--assets", type=str, default="BTC,ETH")
    p.add_argument("--market-provider", type=str, default="hyperliquid_binance")
    p.add_argument("--strict", action="store_true")
    return p

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    run_id = f"cog_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    output_dir = args.output or str(Path.cwd() / "results" / "cognition" / run_id)
    output_root = Path(output_dir)
    if output_root.exists():
        is_empty = True
        for _ in output_root.iterdir():
            is_empty = False
            break
        if not is_empty:
            print(f"OUTPUT_DIRECTORY_NOT_EMPTY: {output_root}")
            return 1
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input not found: {input_path}")
        return 1
    result = run_program(
        input_path=input_path,
        output_root=output_root,
        run_id=run_id,
        mode=args.mode,
        as_of=args.as_of or None,
        strict=args.strict,
        assets=[a.strip() for a in args.assets.split(",")] if args.assets else None,
    )
    print(f"Run: {run_id}")
    print(f"Status: {result.status}")
    print(f"Events: {len(result.cognition.events) if result.cognition else 0}")
    print(f"Assessments: {len(result.cognition.assessments) if result.cognition else 0}")
    print(f"Abstentions: {len(result.cognition.abstentions) if result.cognition else 0}")
    print(f"Decision packets: {len(result.decision_packets)}")
    print(f"Strategies registered: {len(result.registry.components) if result.registry else 0}")
    print(f"Output: {output_root}")
    for sn, s in (result.cognition.stages if result.cognition else {}).items():
        print(f"  {sn}: {s.status} ({len(s.outputs)} outputs)")
    if result.errors:
        for e in result.errors[:5]:
            print(f"  Error: {e}")
    return 0 if result.status in ("ok", "degraded", "abstained", "partial") else 1

if __name__ == "__main__":
    sys.exit(main())
