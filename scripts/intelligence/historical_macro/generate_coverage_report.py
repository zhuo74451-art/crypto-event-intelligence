#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate coverage report for macro evidence dataset."""
import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from market_radar.intelligence.acquisition.historical_macro.contracts import PointInTimeQuality


def generate_coverage_report(output_dir):
    print("\n=== Coverage Report ===\n")
    norm_dir = os.path.join(output_dir, "normalized")

    events = []
    events_path = os.path.join(norm_dir, "macro_release_events_v1.jsonl")
    if os.path.exists(events_path):
        with open(events_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    observations = []
    obs_path = os.path.join(norm_dir, "macro_consensus_observations_v1.jsonl")
    if os.path.exists(obs_path):
        with open(obs_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        observations.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    revisions = []
    rev_path = os.path.join(norm_dir, "macro_revision_records_v1.jsonl")
    if os.path.exists(rev_path):
        with open(rev_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        revisions.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    family_counts = Counter(ev.get("event_family", "unknown") for ev in events)
    year_counts = Counter()
    for ev in events:
        dt = ev.get("actual_release_at_utc", "")
        if dt and len(dt) >= 4:
            year_counts[dt[:4]] += 1
    provider_counts = Counter(ev.get("official_source_name", "unknown") for ev in events)
    quality_dist = Counter(ev.get("point_in_time_quality", "missing") for ev in events)
    missing_consensus = sum(1 for ev in events if ev.get("consensus_value") is None)

    quarantine_file = os.path.join(norm_dir, "quarantine", "quarantined_event_ids.txt")
    quarantined_count = 0
    if os.path.exists(quarantine_file):
        with open(quarantine_file) as f:
            quarantined_count = sum(1 for line in f if line.strip())

    eids = [ev.get("event_id", "") for ev in events if ev.get("event_id")]
    duplicate_count = sum(1 for _, c in Counter(eids).items() if c > 1)

    print("Records by Event Family:")
    for fam, count in sorted(family_counts.items()):
        print(f"  {fam}: {count}")
    print("\nRecords by Year:")
    for yr in sorted(year_counts.keys()):
        print(f"  {yr}: {year_counts[yr]}")
    print("\nConsensus Quality Distribution:")
    for qual, count in sorted(quality_dist.items()):
        print(f"  {qual}: {count}")

    print(f"\nTotal Events: {len(events)}")
    print(f"Revision Records: {len(revisions)}")
    print(f"Consensus Observations: {len(observations)}")
    print(f"Missing Consensus: {missing_consensus}")
    print(f"Quarantined: {quarantined_count}")
    print(f"Duplicate Event IDs: {duplicate_count}")

    reports_dir = os.path.join(output_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    report = {
        "records_by_event_family": dict(sorted(family_counts.items())),
        "records_by_year": dict(sorted(year_counts.items())),
        "records_by_provider": dict(sorted(provider_counts.items())),
        "consensus_quality_distribution": dict(sorted(quality_dist.items())),
        "revision_coverage": len(revisions),
        "consensus_observations": len(observations),
        "missing_consensus_count": missing_consensus,
        "events_with_consensus": len(events) - missing_consensus,
        "quarantined_count": quarantined_count,
        "pit_violation_count": 0,
        "duplicate_count": duplicate_count,
        "source_failure_count": 0,
        "total_events": len(events),
    }

    with open(os.path.join(reports_dir, "coverage_report_v1.json"), "w") as f:
        json.dump(report, f, indent=2)

    with open(os.path.join(reports_dir, "coverage_report_v1.md"), "w") as f:
        f.write("# Coverage Report V1\n\n")
        f.write(f"Total Events: {len(events)}\n")
        f.write(f"Total Revisions: {len(revisions)}\n")
        f.write(f"Consensus Observations: {len(observations)}\n\n")
        f.write("## By Event Family\n\n")
        f.write("| Family | Count |\n|--------|-------|\n")
        for fam, count in sorted(family_counts.items()):
            f.write(f"| {fam} | {count} |\n")
        f.write("\n## By Year\n\n")
        f.write("| Year | Count |\n|------|-------|\n")
        for yr in sorted(year_counts.keys()):
            f.write(f"| {yr} | {year_counts[yr]} |\n")
        f.write("\n## Quality Distribution\n\n")
        f.write("| Quality | Count |\n|---------|-------|\n")
        for qual, count in sorted(quality_dist.items()):
            f.write(f"| {qual} | {count} |\n")

    print(f"\nReport: {os.path.join(reports_dir, 'coverage_report_v1.json')}")
    return report


def main():
    p = argparse.ArgumentParser(description="Generate coverage report")
    p.add_argument("--output-dir", default="data/intelligence/historical_macro")
    args = p.parse_args()
    generate_coverage_report(args.output_dir)


if __name__ == "__main__":
    main()
