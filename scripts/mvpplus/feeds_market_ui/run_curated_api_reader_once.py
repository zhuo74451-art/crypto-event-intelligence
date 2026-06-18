#!/usr/bin/env python3
"""One-shot CLI for CuratedApiReader — dry-run, no send, no loop.

Usage:
    python scripts/mvpplus/feeds_market_ui/run_curated_api_reader_once.py
    python scripts/mvpplus/feeds_market_ui/run_curated_api_reader_once.py --limit 200 --max-pages 3
    python scripts/mvpplus/feeds_market_ui/run_curated_api_reader_once.py --summary-only

Default: summary-only=true, no filters, no include_special_line, no raw_json.
"""
import argparse, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from market_radar.intelligence_feed.live_readers import (
    CuratedApiReader, CuratedApiConfig, ReaderStatus,
)


def main():
    parser = argparse.ArgumentParser(
        description="Curated API reader — one-shot, dry-run, no send"
    )
    parser.add_argument("--base-url", default="http://43.98.174.247:8001/api/integration/curated")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--max-items", type=int, default=200)
    parser.add_argument("--since", default=None)
    parser.add_argument("--source", default=None)
    parser.add_argument("--exclude-source", default=None)
    parser.add_argument("--content-type", default=None)
    parser.add_argument("--query", default=None)
    parser.add_argument("--include-special-line", action="store_true", default=None,
                        help="Send include_special_line=1")
    parser.add_argument("--no-include-special-line", action="store_true", dest="no_special",
                        help="Send include_special_line=0")
    parser.add_argument("--include-raw-json", action="store_true")
    parser.add_argument("--summary-only", action="store_true", default=True,
                        help="Only output summary (no full content)")
    parser.add_argument("--output", default="", help="Output path")

    args = parser.parse_args()

    # Resolve include_special_line tri-state
    if args.include_special_line:
        special_line = True
    elif args.no_special:
        special_line = False
    else:
        special_line = None

    config = CuratedApiConfig(
        base_url=args.base_url,
        limit=min(args.limit, 500),
        max_pages=args.max_pages,
        max_items=args.max_items,
        since=args.since,
        source=args.source,
        exclude_source=args.exclude_source,
        content_type=args.content_type,
        q=args.query,
        include_special_line=special_line,
        include_raw_json=args.include_raw_json,
    )

    reader = CuratedApiReader(config)
    result = reader.read_once()

    source_kinds = {}
    content_types = {}
    featured_true = 0
    featured_false = 0
    max_backend = None

    for item in result.items:
        meta = getattr(item, "_metadata", {}) or {}
        sk = meta.get("source_kind") or "unknown"
        source_kinds[sk] = source_kinds.get(sk, 0) + 1
        ct = meta.get("content_type") or "unknown"
        content_types[ct] = content_types.get(ct, 0) + 1
        if meta.get("is_featured") is True:
            featured_true += 1
        else:
            featured_false += 1
        pub_back = meta.get("published_at_backend")
        if pub_back and (max_backend is None or pub_back > max_backend):
            max_backend = pub_back

    cursor = getattr(result, "_next_cursor", None)
    pages = getattr(result, "_pages", 0)

    output = {
        "tool": "run_curated_api_reader_once",
        "dry_run": True,
        "no_send": True,
        "no_loop": True,
        "status": result.status.value,
        "records_seen": result.records_seen,
        "records_accepted": len(result.items),
        "records_rejected": result.records_rejected,
        "source_kind_distribution": source_kinds,
        "content_type_distribution": content_types,
        "is_featured_true": featured_true,
        "is_featured_false": featured_false,
        "max_published_at_backend": max_backend,
        "next_cursor": cursor,
        "pages_fetched": pages,
        "errors": result.errors[:5],
        "summary_only": args.summary_only,
    }

    if not args.summary_only and result.items:
        output["sample_items"] = [
            {
                "feed_id": i.feed_id,
                "source_type": i.source_type.value,
                "source_label": i.source_label,
                "title": i.title[:80],
                "url": i.url,
                "freshness": i.freshness.value,
            }
            for i in result.items[:3]
        ]

    _output(output, args.output)


def _output(data: dict, path: str = ""):
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
            f.write("\n")
        print(f"Output written to {path}")
    else:
        print(text)


if __name__ == "__main__":
    main()
