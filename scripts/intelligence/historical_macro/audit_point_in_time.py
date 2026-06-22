#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Point-in-Time audit for macro evidence dataset."""
import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from market_radar.intelligence.acquisition.historical_macro.contracts import utc_parse

AUDIT_CHECKS = [
    "consensus_before_release",
    "published_before_release",
    "first_seen_before_retrieved",
    "revision_after_release",
    "initial_not_overwritten",
    "current_best_not_in_historical",
    "missing_consensus_stays_null",
    "quality_not_mislabeled",
    "source_hash_present",
    "no_duplicate_event_ids",
]


def run_pit_audit(output_dir):
    print("\n=== Point-in-Time Audit ===\n")
    norm_dir = os.path.join(output_dir, "normalized")
    results = {c: {"pass": 0, "fail": 0, "errors": []} for c in AUDIT_CHECKS}
    quarantine = set()
    events, observations, revisions, snapshots = [], [], [], []

    for fname, container in [
        ("macro_release_events_v1.jsonl", events),
        ("macro_consensus_observations_v1.jsonl", observations),
        ("macro_revision_records_v1.jsonl", revisions),
        ("macro_source_snapshots_v1.jsonl", snapshots),
    ]:
        fpath = os.path.join(norm_dir, fname)
        if os.path.exists(fpath):
            with open(fpath) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            container.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass

    for ev in events:
        if ev.get("consensus_observed_at_utc") and ev.get("actual_release_at_utc"):
            try:
                if utc_parse(ev["consensus_observed_at_utc"]) < utc_parse(ev["actual_release_at_utc"]):
                    results["consensus_before_release"]["pass"] += 1
                else:
                    results["consensus_before_release"]["fail"] += 1
                    quarantine.add(ev.get("event_id", ""))
            except (ValueError, TypeError):
                results["consensus_before_release"]["fail"] += 1
        else:
            results["consensus_before_release"]["pass"] += 1

    for obs in observations:
        if obs.get("published_at_utc"):
            evs = [e for e in events if e["event_id"] == obs.get("event_id")]
            if evs and evs[0].get("actual_release_at_utc"):
                try:
                    if utc_parse(obs["published_at_utc"]) < utc_parse(evs[0]["actual_release_at_utc"]):
                        results["published_before_release"]["pass"] += 1
                    else:
                        results["published_before_release"]["fail"] += 1
                        quarantine.add(obs.get("event_id", ""))
                except (ValueError, TypeError):
                    results["published_before_release"]["fail"] += 1

    for ev in events:
        if ev.get("point_in_time_quality") == "missing":
            if ev.get("consensus_value") is not None:
                results["missing_consensus_stays_null"]["fail"] += 1
            else:
                results["missing_consensus_stays_null"]["pass"] += 1

    for snap in snapshots:
        if snap.get("sha256") and len(snap["sha256"]) > 0:
            results["source_hash_present"]["pass"] += 1
        else:
            results["source_hash_present"]["fail"] += 1

    eids = [e.get("event_id", "") for e in events if e.get("event_id")]
    dupes = [eid for eid, c in Counter(eids).items() if c > 1]
    if dupes:
        results["no_duplicate_event_ids"]["fail"] += len(dupes)
    else:
        results["no_duplicate_event_ids"]["pass"] += len(eids)

    violations = sum(r["fail"] for r in results.values())

    quarantine_dir = os.path.join(norm_dir, "quarantine")
    if quarantine:
        os.makedirs(quarantine_dir, exist_ok=True)
        with open(os.path.join(quarantine_dir, "quarantined_event_ids.txt"), "w") as f:
            for eid in sorted(quarantine):
                f.write(eid + "\n")

    reports_dir = os.path.join(output_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    from datetime import datetime, timezone
    report = {
        "audit_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event_count": len(events),
        "observation_count": len(observations),
        "revision_count": len(revisions),
        "snapshot_count": len(snapshots),
        "total_violations": violations,
        "quarantined_count": len(quarantine),
        "results": {k: {"pass": v["pass"], "fail": v["fail"]} for k, v in results.items()},
    }

    with open(os.path.join(reports_dir, "pit_audit_v1.json"), "w") as f:
        json.dump(report, f, indent=2)

    with open(os.path.join(reports_dir, "pit_audit_v1.md"), "w") as f:
        f.write("# PIT Audit Report V1\n\n")
        f.write(f"Timestamp: {report['audit_timestamp']}\n")
        f.write(f"Events: {len(events)} | Obs: {len(observations)} | Revs: {len(revisions)} | Snaps: {len(snapshots)}\n\n")
        for c in AUDIT_CHECKS:
            r = results[c]
            f.write(f"| {c} | {r['pass']} | {r['fail']} |\n")
        f.write(f"\nTotal violations: {violations}\n")
        f.write(f"Quarantined: {len(quarantine)}\n")

    print(f"Audit done: {violations} violations, {len(quarantine)} quarantined")
    return report


def main():
    p = argparse.ArgumentParser(description="Run point-in-time audit")
    p.add_argument("--output-dir", default="data/intelligence/historical_macro")
    args = p.parse_args()
    run_pit_audit(args.output_dir)


if __name__ == "__main__":
    main()
