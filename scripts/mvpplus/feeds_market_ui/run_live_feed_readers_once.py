#!/usr/bin/env python3
"""One-shot CLI for live feed readers — dry-run only, no send, no loop.

Usage:
    python -m scripts.mvpplus.feeds_market_ui.run_live_feed_readers_once.py \\
        --flash <path> [--news <path>] [--tg <path>] [--dry-run]

All paths default to empty (reader not activated). No production paths are
hardcoded. Output is written to stdout as JSON or to a user-specified path.
"""
import argparse, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from market_radar.intelligence_feed.live_readers import (
    FlashReader, NewsReader, TelegramReader,
    read_all_once,
)


def main():
    parser = argparse.ArgumentParser(
        description="Live feed reader — one-shot, dry-run, no send"
    )
    parser.add_argument("--flash", default="", help="Path to flash JSON/JSONL file")
    parser.add_argument("--news", default="", help="Path to news JSON/JSONL/CSV file")
    parser.add_argument("--tg", "--telegram", default="", help="Path to Telegram SQLite DB")
    parser.add_argument("--limit", type=int, default=20, help="Max items per reader")
    parser.add_argument("--output", default="", help="Output path (default: stdout)")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Dry run flag (always true — no send)")
    args = parser.parse_args()

    readers = []
    if args.flash:
        readers.append(FlashReader(args.flash, limit=args.limit))
    if args.news:
        readers.append(NewsReader(args.news, limit=args.limit))
    if args.tg:
        readers.append(TelegramReader(args.tg, limit=args.limit))

    if not readers:
        result = {
            "status": "no_readers_configured",
            "message": "Provide at least one of --flash, --news, --tg",
        }
        _output(result, args.output)
        return

    summary = read_all_once(readers)
    output = {
        "tool": "run_live_feed_readers_once",
        "dry_run": args.dry_run,
        "no_send": True,
        "no_loop": True,
        "status": summary.overall_status,
        "items_count": len(summary.items),
        "health": [h.as_dict() for h in summary.health],
        "source_statuses": summary.source_statuses,
        "counts": summary.counts,
        "errors": summary.errors[:10],
    }
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
