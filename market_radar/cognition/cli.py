"""Cognition Spine V1 CLI."""
from __future__ import annotations
import argparse, json, sys, uuid
from datetime import datetime, timezone
from pathlib import Path
from market_radar.cognition.event_store import EventStore
from market_radar.cognition.event_grouper import group_observations
from market_radar.cognition.input_loader import load_observations, load_evidence_manifest
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
        for _ in output_root.iterdir(): is_empty = False; break
        if not is_empty:
            print(f"OUTPUT_DIRECTORY_NOT_EMPTY: {output_root}"); return 1
    output_root.mkdir(parents=True, exist_ok=True)
    input_path = Path(args.input)
    if not input_path.exists(): print(f"Input not found: {input_path}"); return 1
    obs_path = input_path / "observations.jsonl"
    obs_list, inventory = load_observations(obs_path)
    print(f"Loaded {inventory.valid_observations} valid / {inventory.rejected_observations} rejected")
    events, conflicts = group_observations(obs_list)
    print(f"Grouped {len(events)} events, {len(conflicts)} conflicts")
    db_path = str(output_root / "cognition.db")
    store = EventStore(db_path)
    for ev in events: store.upsert_event(ev)
    for cf in conflicts: store.add_conflict(cf)
    with open(output_root / "run_manifest.json", "w") as f: json.dump({"run_id": run_id, "started_at": utc_now(), "completed_at": utc_now(), "status": "ok", "mode": args.mode, "stages": ["load","group","store"]}, f, indent=2)
    with open(output_root / "event_states.jsonl", "w") as f:
        for ev in events: f.write(json.dumps(ev.to_dict()) + chr(10))
    with open(output_root / "source_conflicts.jsonl", "w") as f:
        for cf in conflicts: f.write(json.dumps(cf.to_dict()) + chr(10))
    print(f"Output: {output_root}"); print(f"Events: {len(events)}"); print(f"Conflicts: {len(conflicts)}")
    return 0
if __name__ == "__main__": sys.exit(main())