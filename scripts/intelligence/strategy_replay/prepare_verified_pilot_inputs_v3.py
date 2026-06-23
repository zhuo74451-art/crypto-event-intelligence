"""Prepare verified pilot inputs V3 — from locked git objects to release units and decision inputs.
No dependency on pre-existing files in pilot_v2/ directory.
"""
import subprocess, hashlib, json, pathlib, sys
from collections import defaultdict

LANE_A_SHA = "9aaabc82f34141e6797d3f92b773d5c463ad99b8"
LANE_B_SHA = "ec8952b600ffceebeabcb50ac11e3b182e76c5e2"

WORKTREE = pathlib.Path(r"C:\Users\zhuo7\Desktop\crypto-event-intelligence-worktrees\lane-c-macro-strategy-replay-v1")
OUT = WORKTREE / "data" / "intelligence" / "strategy_replay" / "pilot_v2"
UP = OUT / "upstream"


def git_cat(sha, repo_path):
    return subprocess.check_output(["git", "cat-file", "blob", f"{sha}:{repo_path}"], cwd=str(WORKTREE))


def load_jsonl_from_bytes(data):
    return [json.loads(l) for l in data.decode("utf-8").strip().splitlines() if l]


def det_id(prefix, parts):
    h = hashlib.sha256("|".join(sorted(parts)).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{h}"


def extract_asset(symbol):
    if symbol.startswith("BTC"): return "BTC"
    if symbol.startswith("ETH"): return "ETH"
    return symbol


def write_jsonl(records, path, sort_key=None):
    OUT.mkdir(parents=True, exist_ok=True)
    if sort_key:
        records = sorted(records, key=lambda r: r.get(sort_key, ""))
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def prepare_pilot_inputs(force=False):
    # Step 1: Verify Lane A/B remote SHAs
    print(f"Lane A SHA: {LANE_A_SHA}")
    print(f"Lane B SHA: {LANE_B_SHA}")

    # Step 2: Read and verify artifacts
    artifacts = [
        ("lane_a_macro_release_events_v1.jsonl", LANE_A_SHA,
         "data/intelligence/historical_macro/normalized/macro_release_events_v1.jsonl"),
        ("lane_b_horizon_windows_v3.jsonl", LANE_B_SHA,
         "data/intelligence/historical_market/pilot_v3/horizon_windows_v3.jsonl"),
        ("lane_b_reaction_labels_v3.jsonl", LANE_B_SHA,
         "data/intelligence/historical_market/pilot_v3/reaction_labels_v3.jsonl"),
        ("lane_b_cross_asset_context_v3.jsonl", LANE_B_SHA,
         "data/intelligence/historical_market/pilot_v3/cross_asset_context_v3.jsonl"),
        ("lane_b_funding_context_v3.jsonl", LANE_B_SHA,
         "data/intelligence/historical_market/pilot_v3/funding_context_v3.jsonl"),
    ]

    UP.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for fname, sha, repo_path in artifacts:
        raw = git_cat(sha, repo_path)
        h = hashlib.sha256(raw).hexdigest()
        (UP / fname).write_bytes(raw)
        lines = len(raw.decode("utf-8").strip().splitlines()) if fname.endswith(".jsonl") else 0
        hashes[fname] = {"sha256": h, "records": lines}
        print(f"  {fname}: {lines} lines, sha256={h[:16]}...")

    # Copy lock files
    lock_bytes = git_cat(LANE_B_SHA, "data/intelligence/historical_market/pilot_v3/lane_a_input/PRODUCER_LOCK.yaml")
    (UP / "LANE_A_LOCK.yaml").write_bytes(lock_bytes)

    manifest_bytes = git_cat(LANE_B_SHA, "docs/execution/lane_b/PILOT_V3_INTEGRATION_MANIFEST.yaml")
    (UP / "LANE_B_LOCK.yaml").write_bytes(manifest_bytes)

    # Write PRODUCER_LOCKS.yaml
    lock_lines = ["# Producer Locks — Lane C Pilot V3", f"# Reproduced from locked git objects"]
    lock_lines.append(f"lane_a_final_sha: {LANE_A_SHA}")
    lock_lines.append(f"lane_b_final_sha: {LANE_B_SHA}")
    for fname, info in hashes.items():
        lock_lines.append(f"{fname}:")
        lock_lines.append(f"  sha256: \"{info['sha256']}\"")
        lock_lines.append(f"  record_count: {info['records']}")
    (UP / "PRODUCER_LOCKS.yaml").write_text("\n".join(lock_lines) + "\n", encoding="utf-8")
    print(f"  PRODUCER_LOCKS.yaml: {len(lock_lines)} lines")

    # Step 3: Load events
    events = load_jsonl_from_bytes(git_cat(LANE_A_SHA,
        "data/intelligence/historical_macro/normalized/macro_release_events_v1.jsonl"))
    horizons = load_jsonl_from_bytes(git_cat(LANE_B_SHA,
        "data/intelligence/historical_market/pilot_v3/horizon_windows_v3.jsonl"))

    print(f"\nLoaded {len(events)} events, {len(horizons)} horizon windows")

    # Step 4: Build release units
    by_time = defaultdict(list)
    for e in events:
        t = e.get("actual_release_at_utc", e.get("release_time_utc", ""))
        by_time[t].append(e)

    release_units = []
    for t, evts in sorted(by_time.items()):
        eids = sorted(e["event_id"] for e in evts)
        fams = sorted(e["event_family"] for e in evts)
        ru_id = det_id("ru", eids)
        is_shared = len(evts) >= 2
        release_units.append({
            "release_unit_id": ru_id, "shared_release_group_id": ru_id if not is_shared else f"shared_{'_'.join(fams)}",
            "constituent_event_ids": eids, "event_families": fams,
            "event_time_utc": t, "is_shared": is_shared,
        })

    # Step 5: Shared release consistency check
    conflicts = 0
    for ru in release_units:
        if not ru["is_shared"]: continue
        for nh in ["1h", "4h", "24h"]:
            for sym in ["BTCUSDT", "ETHUSDT"]:
                asset = extract_asset(sym)
                eid_wins = {}
                for eid in ru["constituent_event_ids"]:
                    mm = [w for w in horizons if w["event_id"] == eid and w["symbol"] == sym and w["nominal_horizon"] == nh]
                    if mm: eid_wins[eid] = mm[0]
                if len(eid_wins) >= 2:
                    ref = list(eid_wins.values())[0]
                    for eid, w in eid_wins.items():
                        for f in ["event_time_utc", "baseline_price_time_utc", "endpoint_price_time_utc",
                                   "pre_bar_close", "post_bar_close", "return_pct", "direction", "precision_class"]:
                            if w.get(f) != ref.get(f):
                                print(f"  CONFLICT: ru={ru['release_unit_id'][:16]} {asset} {nh} {f}")
                                conflicts += 1
    print(f"Shared release conflicts: {conflicts}")
    assert conflicts == 0, f"Shared release conflicts: {conflicts}"

    # Step 6: Build decision inputs
    decision_inputs = []
    for ru in release_units:
        for sym in ["BTCUSDT", "ETHUSDT"]:
            asset = extract_asset(sym)
            du_id = det_id("du", [ru["release_unit_id"], asset])
            first_eid = ru["constituent_event_ids"][0]
            wh = [w for w in horizons if w["event_id"] == first_eid and w["symbol"] == sym and w["nominal_horizon"] == "1h"]
            if not wh:
                print(f"  SKIP: no 1h window for {first_eid}/{sym}")
                continue
            w1 = wh[0]
            ep_time = w1.get("endpoint_price_time_utc", w1.get("event_time_utc", ""))
            decision_inputs.append({
                "decision_unit_id": du_id, "release_unit_id": ru["release_unit_id"],
                "shared_release_group_id": ru["shared_release_group_id"],
                "constituent_event_ids": ru["constituent_event_ids"],
                "event_families": ru["event_families"],
                "asset": asset, "instrument_id": sym,
                "event_time_utc": ru["event_time_utc"],
                "information_cutoff_utc": ep_time,
                "signal_window_id": w1.get("window_id", ""),
                "signal_horizon": "1h",
                "signal_direction": w1.get("direction", "neutral"),
                "signal_return_pct": w1.get("return_pct", 0.0),
                "signal_endpoint_price": w1.get("post_bar_close", w1.get("endpoint_price", 0)),
                "signal_endpoint_time_utc": ep_time,
                "precision_class": "coarse_hourly_alignment",
                "horizon_alignment_error_minutes": w1.get("horizon_alignment_error_minutes", 0),
                "exact_event_price_available": False,
                "source_refs": ["window:" + w1.get("window_id", ""), "release_unit:" + ru["release_unit_id"]],
                "quality_flags": ["coarse_hourly_alignment", "pilot_sample"],
            })

    print(f"\nRelease units: {len(release_units)} (shared={sum(1 for r in release_units if r['is_shared'])})")
    print(f"Decision inputs: {len(decision_inputs)}")

    assert len(release_units) == 8, f"Expected 8 release units, got {len(release_units)}"
    assert len(decision_inputs) == 16, f"Expected 16 decision inputs, got {len(decision_inputs)}"

    # Write
    write_jsonl(release_units, OUT / "release_units_v1.jsonl", sort_key="release_unit_id")
    write_jsonl(decision_inputs, OUT / "decision_inputs_v1.jsonl", sort_key="decision_unit_id")

    print(f"\nPrepare complete. Written {len(release_units)} RUs, {len(decision_inputs)} DUs")
    return {"release_units": len(release_units), "decision_inputs": len(decision_inputs)}


if __name__ == "__main__":
    result = prepare_pilot_inputs()
    print(json.dumps(result, indent=2))
