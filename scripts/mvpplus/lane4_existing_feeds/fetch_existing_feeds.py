#!/usr/bin/env python3
"""MVP+ Lane 4 — Existing Feeds Reader.

Reads existing flash, news, and Telegram data from the repository's
data/ directory. Outputs UnifiedFeedItem[] matching
contracts/mvpplus/v1/unified_feed_item.schema.json.

One-shot read-only. No network access required for this lane.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Optional
from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(__file__, *[os.pardir] * 4))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "results", "mvpplus")
os.makedirs(OUTPUT_DIR, exist_ok=True)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")


def utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_source_health(
    source: str, status: str, occurred_at_utc: str,
    error_type: Optional[str] = None, retryable: Optional[bool] = None,
    message_summary: Optional[str] = None,
) -> dict:
    entry: dict[str, Any] = {"status": status, "source": source, "occurred_at_utc": occurred_at_utc}
    if error_type is not None: entry["error_type"] = error_type
    if retryable is not None: entry["retryable"] = retryable
    if message_summary is not None: entry["message_summary"] = message_summary
    return entry


def read_csv_as_items(file_path: str, source_label: str, stream_type: str) -> list[dict]:
    """Read a CSV data file and convert rows to UnifiedFeedItem-like dicts."""
    items: list[dict] = []
    if not os.path.isfile(file_path):
        return items

    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get("title", "") or row.get("event_title", "") or row.get("headline", "") or ""
                if not title:
                    continue
                item_id = row.get("id", "") or row.get("event_id", "") or f"csv-{len(items)}"
                published = row.get("published_at", "") or row.get("event_time", "") or utc_now_str()
                summary = row.get("summary", "") or row.get("body", "") or row.get("description", "") or ""
                assets_str = row.get("assets", "") or row.get("affected_assets", "") or ""
                assets = [a.strip() for a in assets_str.split(",") if a.strip()]

                item = {
                    "item_id": item_id,
                    "stream_type": stream_type,
                    "source_label": source_label,
                    "published_at_utc": published,
                    "ingested_at_utc": utc_now_str(),
                    "title": title.strip()[:200],
                    "summary": summary.strip()[:500] if summary else None,
                    "assets": assets,
                    "source_url": None,
                    "existing_decision": row.get("decision", "") or None,
                    "raw_reference": os.path.basename(file_path),
                    "source_health": make_source_health(
                        source=f"local_csv:{os.path.basename(file_path)}",
                        status="healthy",
                        occurred_at_utc=utc_now_str(),
                    ),
                }
                items.append(item)
    except (IOError, csv.Error) as e:
        print(f"    [WARN] Failed to read {file_path}: {e}", file=sys.stderr)
        return []

    return items


def read_json_as_items(file_path: str, source_label: str, stream_type: str) -> list[dict]:
    """Read a JSON data file and extract feed items."""
    items: list[dict] = []
    if not os.path.isfile(file_path):
        return items

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"    [WARN] Failed to parse {file_path}: {e}", file=sys.stderr)
        return []

    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict) and entry.get("title"):
                title = str(entry.get("title", ""))
                item_id = entry.get("id", "") or entry.get("event_id", "") or f"json-{len(items)}"
                published = entry.get("published_at", "") or entry.get("timestamp", "") or entry.get("event_time", "") or utc_now_str()
                summary = entry.get("summary", "") or entry.get("body", "") or entry.get("description", "") or ""
                assets = entry.get("assets", []) or entry.get("affected_assets", [])

                item = {
                    "item_id": item_id,
                    "stream_type": stream_type,
                    "source_label": source_label,
                    "published_at_utc": published,
                    "ingested_at_utc": utc_now_str(),
                    "title": title[:200],
                    "summary": str(summary)[:500] if summary else None,
                    "assets": assets if isinstance(assets, list) else [],
                    "source_url": None,
                    "existing_decision": entry.get("decision", "") or None,
                    "raw_reference": os.path.basename(file_path),
                    "source_health": make_source_health(
                        source=f"local_json:{os.path.basename(file_path)}",
                        status="healthy",
                        occurred_at_utc=utc_now_str(),
                    ),
                }
                items.append(item)
    elif isinstance(data, dict):
        # Single item or nested structure
        if data.get("title"):
            items.append({
                "item_id": data.get("id", "json-root"),
                "stream_type": stream_type,
                "source_label": source_label,
                "published_at_utc": data.get("published_at", data.get("timestamp", utc_now_str())),
                "ingested_at_utc": utc_now_str(),
                "title": str(data.get("title", ""))[:200],
                "summary": str(data.get("summary", data.get("body", "")))[:500] or None,
                "assets": data.get("assets", data.get("affected_assets", [])),
                "source_url": None,
                "existing_decision": data.get("decision") or None,
                "raw_reference": os.path.basename(file_path),
                "source_health": make_source_health(
                    source=f"local_json:{os.path.basename(file_path)}",
                    status="healthy",
                    occurred_at_utc=utc_now_str(),
                ),
            })

    return items


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> int:
    start_time = time.time()
    run_id = f"mvpplus_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}_lane4"
    snapshot_time = utc_now_str()

    print(f"[{run_id}] Lane 4: Existing Feeds Reader", file=sys.stderr)
    print(f"  Data dir: {DATA_DIR}", file=sys.stderr)

    all_items: list[dict] = []
    errors: list[dict] = []
    source_stats: dict[str, int] = {}

    if not os.path.isdir(DATA_DIR):
        print(f"  [DEGRADED] Data directory not found: {DATA_DIR}", file=sys.stderr)
        empty_output = {
            "run_id": run_id,
            "snapshot_time_utc": snapshot_time,
            "lane": "lane4_existing_feeds",
            "feed_items": [],
            "source_health": make_source_health(
                source="local_data_dir",
                status="unavailable",
                occurred_at_utc=snapshot_time,
                error_type="dir_not_found",
                message_summary=f"Data directory not found: {DATA_DIR}",
            ),
            "errors": [{"source": "local_data_dir", "error_type": "dir_not_found",
                         "message_summary": f"Data directory not found",
                         "occurred_at_utc": snapshot_time}],
        }
        output_path = os.path.join(OUTPUT_DIR, "lane4_existing_feeds.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(empty_output, f, indent=2, ensure_ascii=False)
        return 1

    # CSV files representing events/flash news
    csv_feeds: list[dict[str, str]] = [
        {"file": "events_raw.csv", "label": "Events Raw", "type": "flash"},
        {"file": "aggregated_events.csv", "label": "Aggregated Events", "type": "flash"},
        {"file": "events_raw_real_50.csv", "label": "Real Events Sample", "type": "flash"},
        {"file": "claude_decision_review_queue.csv", "label": "AI Review Queue", "type": "flash"},
        {"file": "event_candidates_live_incremental_review.csv", "label": "Live Event Candidates", "type": "flash"},
        {"file": "events_v06_clean_low_risk_preview.csv", "label": "Low Risk Preview", "type": "flash"},
    ]

    for feed in csv_feeds:
        file_path = os.path.join(DATA_DIR, feed["file"])
        if not os.path.isfile(file_path):
            continue
        items = read_csv_as_items(file_path, feed["label"], feed["type"])
        if items:
            all_items.extend(items)
            source_stats[feed["file"]] = len(items)
            print(f"  {feed['label']}: {len(items)} items", file=sys.stderr)

    # JSON files
    json_feeds: list[dict[str, str]] = [
        {"file": "entity_dictionary.json", "label": "Entity Dictionary", "type": "news"},
    ]
    # Check for JSON files in data dir with event/signal naming
    for fname in os.listdir(DATA_DIR):
        if fname.endswith(".json") and fname not in [f["file"] for f in json_feeds]:
            # Try to read it
            file_path = os.path.join(DATA_DIR, fname)
            if os.path.getsize(file_path) > 500_000:  # Skip files >500KB
                continue
            items = read_json_as_items(file_path, fname.replace(".json", ""), "news")
            if items:
                all_items.extend(items)
                source_stats[fname] = len(items)
                print(f"  {fname}: {len(items)} items", file=sys.stderr)

    # Read run reports / research data for news
    research_dir = os.path.join(PROJECT_ROOT, "research")
    if os.path.isdir(research_dir):
        for fname in os.listdir(research_dir):
            if fname.endswith(".json") and os.path.isfile(os.path.join(research_dir, fname)):
                file_path = os.path.join(research_dir, fname)
                if os.path.getsize(file_path) > 500_000:
                    continue
                items = read_json_as_items(file_path, fname.replace(".json", ""), "news")
                if items:
                    all_items.extend(items)
                    source_stats[fname] = len(items)
                    print(f"  {fname}: {len(items)} items", file=sys.stderr)

    overall_status = "healthy" if all_items else "degraded"

    output = {
        "run_id": run_id,
        "snapshot_time_utc": snapshot_time,
        "lane": "lane4_existing_feeds",
        "feed_items": all_items,
        "source_health": make_source_health(
            source="local_data_dir",
            status=overall_status,
            occurred_at_utc=snapshot_time,
            error_type=None if overall_status == "healthy" else "no_items_found",
            message_summary=f"{len(all_items)} feed items from {len(source_stats)} sources"
                           if all_items else "No feed items found in data directory",
        ),
    }
    if errors:
        output["errors"] = errors

    output_path = os.path.join(OUTPUT_DIR, "lane4_existing_feeds.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - start_time
    print(f"  Done in {elapsed:.1f}s. {len(all_items)} feed items.", file=sys.stderr)
    print(f"  Output: {output_path}", file=sys.stderr)

    return 0 if overall_status == "healthy" else 1


if __name__ == "__main__":
    sys.exit(main())
