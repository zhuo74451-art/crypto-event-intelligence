#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build complete macro evidence dataset."""
import argparse
import hashlib
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from market_radar.intelligence.acquisition.historical_macro.contracts import (
    MacroReleaseEventV1, MacroConsensusObservationV1, MacroRevisionRecordV1,
)


def compute_file_hash(filepath):
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def build_sqlite_index(output_dir):
    db_path = os.path.join(output_dir, "indexes", "macro_evidence_v1.sqlite")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS release_events (
            event_id TEXT PRIMARY KEY,
            event_family TEXT, series_id TEXT, country TEXT,
            reference_period TEXT, scheduled_release_at_utc TEXT,
            actual_release_at_utc TEXT, actual_initial REAL,
            actual_initial_unit TEXT, prior_as_known_then REAL,
            prior_revised_latest REAL, revision_status TEXT,
            official_source_name TEXT, official_source_url TEXT,
            consensus_value REAL, consensus_unit TEXT,
            consensus_observed_at_utc TEXT, point_in_time_quality TEXT,
            surprise_raw REAL, data_quality_flags TEXT,
            as_known_then_cutoff_utc TEXT
        );
        CREATE TABLE IF NOT EXISTS consensus_observations (
            consensus_observation_id TEXT PRIMARY KEY,
            event_id TEXT, source_name TEXT, source_url TEXT,
            published_at_utc TEXT, observed_at_utc TEXT,
            consensus_value REAL, consensus_unit TEXT,
            estimate_type TEXT, point_in_time_quality TEXT,
            FOREIGN KEY (event_id) REFERENCES release_events(event_id)
        );
        CREATE TABLE IF NOT EXISTS revision_records (
            revision_id TEXT PRIMARY KEY, event_id TEXT,
            series_id TEXT, reference_period TEXT,
            revision_published_at_utc TEXT, previous_value REAL,
            revised_value REAL, revision_sequence INTEGER,
            source_url TEXT,
            FOREIGN KEY (event_id) REFERENCES release_events(event_id)
        );
        CREATE INDEX IF NOT EXISTS idx_release_family ON release_events(event_family);
        CREATE INDEX IF NOT EXISTS idx_release_period ON release_events(reference_period);
        CREATE INDEX IF NOT EXISTS idx_consensus_event ON consensus_observations(event_id);
        CREATE INDEX IF NOT EXISTS idx_revision_event ON revision_records(event_id);
    """)
    return db_path, conn, cursor


def insert_into_db(cursor, table, records):
    if not records:
        return 0
    cursor.execute(f"DELETE FROM {table}")
    count = 0
    for r in records:
        if table == "release_events":
            cursor.execute("""
                INSERT OR REPLACE INTO release_events VALUES
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                r.get("event_id",""), r.get("event_family",""), r.get("series_id",""),
                r.get("country","US"), r.get("reference_period",""),
                r.get("scheduled_release_at_utc",""), r.get("actual_release_at_utc",""),
                r.get("actual_initial"), r.get("actual_initial_unit",""),
                r.get("prior_as_known_then"), r.get("prior_revised_latest"),
                r.get("revision_status","initial"),
                r.get("official_source_name",""), r.get("official_source_url",""),
                r.get("consensus_value"), r.get("consensus_unit",""),
                r.get("consensus_observed_at_utc"),
                r.get("point_in_time_quality","missing"),
                r.get("surprise_raw"),
                json.dumps(r.get("data_quality_flags",[])),
                r.get("as_known_then_cutoff_utc",""),
            ))
            count += 1
    return count


def build_dataset(output_dir):
    print("\n=== Building Macro Evidence Dataset ===\n")
    norm_dir = os.path.join(output_dir, "normalized")
    counts = {}
    data = {}
    for fname in [
        "macro_release_events_v1.jsonl",
        "macro_consensus_observations_v1.jsonl",
        "macro_revision_records_v1.jsonl",
        "macro_source_snapshots_v1.jsonl",
    ]:
        fpath = os.path.join(norm_dir, fname)
        records = []
        if os.path.exists(fpath):
            size = os.path.getsize(fpath)
            sha = compute_file_hash(fpath)
            print(f"  {fname}: {size} bytes, SHA256: {sha[:16]}...")
            with open(fpath) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        else:
            print(f"  {fname}: NOT FOUND")
        counts[fname] = len(records)
        data[fname] = records

    print("\n  Building SQLite index...")
    db_path, conn, cursor = build_sqlite_index(output_dir)
    cnt = insert_into_db(cursor, "release_events", data.get("macro_release_events_v1.jsonl", []))
    print(f"  SQLite: inserted {cnt} release events")
    conn.commit()
    conn.close()
    db_sha = compute_file_hash(db_path)
    print(f"  SQLite DB SHA256: {db_sha[:16]}...")

    print(f"\n=== Dataset Summary ===")
    for fname, count in counts.items():
        print(f"  {fname}: {count} records")
    return counts


def main():
    parser = argparse.ArgumentParser(description="Build complete macro evidence dataset")
    parser.add_argument("--output-dir", default="data/intelligence/historical_macro")
    args = parser.parse_args()
    build_dataset(args.output_dir)


if __name__ == "__main__":
    main()
