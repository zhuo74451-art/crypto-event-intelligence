"""Migrate unverified legacy data to quarantine with full report."""
import json
import hashlib
import os
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


def migrate_legacy_data(output_dir: str) -> dict:
    """Move legacy (V1) data to quarantine and generate migration report."""
    norm_dir = os.path.join(output_dir, "normalized")
    quarantine_dir = os.path.join(output_dir, "quarantine", "unverified_series_archive_v1")
    os.makedirs(quarantine_dir, exist_ok=True)

    report = {
        "migration_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reasons": [
            "estimated_release_times",
            "latest_values_not_verified_initial",
            "cross_provider_logical_duplicates",
            "incorrect_fomc_event_semantics",
            "synthetic_snapshot_metadata",
        ],
        "legacy_files": [],
        "record_counts": {},
        "new_canonical_started": False,
    }

    # Migrate release events
    src = os.path.join(norm_dir, "macro_release_events_v1.jsonl")
    if os.path.exists(src):
        count = sum(1 for _ in open(src) if _.strip())
        dst = os.path.join(quarantine_dir, "legacy_macro_release_events_v1.jsonl")
        shutil.copy2(src, dst)
        report["legacy_files"].append("legacy_macro_release_events_v1.jsonl")
        report["record_counts"]["release_events"] = count

        csv_src = os.path.join(norm_dir, "macro_release_events_v1.csv")
        if os.path.exists(csv_src):
            csv_dst = os.path.join(quarantine_dir, "legacy_macro_release_events_v1.csv")
            shutil.copy2(csv_src, csv_dst)
            report["legacy_files"].append("legacy_macro_release_events_v1.csv")

        # Analyze legacy data
        families = Counter()
        has_null_initial = 0
        has_null_release_time = 0
        has_estimated_time = 0
        fedfunds_as_fomc = 0

        with open(src) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ev = json.loads(line)
                families[ev.get("event_family", "")] += 1
                if ev.get("actual_initial") is None:
                    has_null_initial += 1
                rt = ev.get("release_time_quality", "")
                if not rt or rt == "missing":
                    has_null_release_time += 1
                if ev.get("event_family") == "us_fomc_rate_decision":
                    fedfunds_as_fomc += 1

        report["analysis"] = {
            "families": dict(families),
            "total_events": count,
            "null_initial_count": has_null_initial,
            "estimated_release_times": has_null_release_time,
            "fedfunds_observations_as_fomc": fedfunds_as_fomc,
            "estimated_release_time_details": [
                "Release times were synthetic (estimated from ref_period, not verified)"
            ],
            "fomc_semantics_details": [
                f"{fedfunds_as_fomc} events were monthly FEDFUNDS observations, not FOMC meeting decisions"
            ],
        }

    # Migrate snapshots
    snap_src = os.path.join(norm_dir, "macro_source_snapshots_v1.jsonl")
    if os.path.exists(snap_src):
        count = sum(1 for _ in open(snap_src) if _.strip())
        snap_dst = os.path.join(quarantine_dir, "legacy_macro_source_snapshots_v1.jsonl")
        shutil.copy2(snap_src, snap_dst)
        report["legacy_files"].append("legacy_macro_source_snapshots_v1.jsonl")
        report["record_counts"]["source_snapshots"] = count

        # Check for synthetic snapshots
        synthetic = 0
        with open(snap_src) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                snap = json.loads(line)
                url = snap.get("source_url", "")
                local_path = snap.get("local_path", "")
                if "data.bls.gov/series/" in url and not url.startswith("https://fred"):
                    synthetic += 1

        report["analysis"]["synthetic_snapshots"] = synthetic

    # Write migration report
    report_path = os.path.join(quarantine_dir, "legacy_migration_report_v1.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    report_md_path = os.path.join(quarantine_dir, "legacy_migration_report_v1.md")
    with open(report_md_path, "w") as f:
        f.write("# Legacy Migration Report V1\n\n")
        f.write(f"Timestamp: {report['migration_timestamp']}\n\n")
        f.write("## Migration Reasons\n\n")
        for r in report["reasons"]:
            f.write(f"- {r}\n")
        f.write("\n## Legacy Files\n\n")
        for lf in report["legacy_files"]:
            f.write(f"- {lf}\n")
        f.write(f"\n## Record Counts\n\n")
        for k, v in report["record_counts"].items():
            f.write(f"- {k}: {v}\n")
        if "analysis" in report:
            f.write(f"\n## Analysis\n\n")
            a = report["analysis"]
            f.write(f"- Families: {json.dumps(a.get('families', {}))}\n")
            f.write(f"- Total events: {a.get('total_events', 0)}\n")
            f.write(f"- Estimated release times: {a.get('estimated_release_times', 0)}\n")
            f.write(f"- FEDFUNDS as FOMC: {a.get('fedfunds_observations_as_fomc', 0)}\n")
            f.write(f"- Synthetic snapshots: {a.get('synthetic_snapshots', 0)}\n")

    print(f"Legacy data migrated to: {quarantine_dir}")
    print(f"  Release events: {report['record_counts'].get('release_events', 0)}")
    print(f"  Snapshots: {report['record_counts'].get('source_snapshots', 0)}")
    print(f"  Synthetic snapshots detected: {report['analysis'].get('synthetic_snapshots', 0)}")

    # Clean old canonical files (they will be rebuilt)
    for fname in ["macro_release_events_v1.jsonl", "macro_release_events_v1.csv",
                   "macro_source_snapshots_v1.jsonl", "macro_consensus_observations_v1.jsonl",
                   "macro_revision_records_v1.jsonl"]:
        fpath = os.path.join(norm_dir, fname)
        if os.path.exists(fpath):
            os.remove(fpath)
            print(f"  Removed old: {fname}")

    report["new_canonical_started"] = True
    return report


def main():
    r = migrate_legacy_data("data/intelligence/historical_macro")
    print("\nMigration complete.")


if __name__ == "__main__":
    main()
