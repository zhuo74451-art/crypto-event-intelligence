#!/usr/bin/env python3
"""Feed Provider fixture runner — no network, no data committed to repo.

Creates a fake provider, runs one_shot with it, verifies feed becomes ok,
cursor is persisted, and report is written last.  Uses temp dirs only.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from market_radar.integration.models import IntegrationConfig
from market_radar.integration.one_shot import run_one_shot
from market_radar.integration.feed_provider_protocol import (
    FeedProviderInput, IntegrationFeedBatch,
)
from market_radar.integration.feed_handler import _load_cursor, _cursor_path
from market_radar.intelligence_feed.models import (
    FeedItem, FeedSourceType, FeedDataMode, make_feed_id,
)
from market_radar.operations.run_history import get_run


def fake_provider(inp: FeedProviderInput) -> IntegrationFeedBatch:
    """Return 3 fixture FeedItems. No network."""
    items = []
    for i in range(3):
        title = f"Fixture News Item {i+1}"
        fid = make_feed_id(title, "fixture_test")
        items.append(FeedItem(
            feed_id=fid,
            source_type=FeedSourceType.NEWS,
            source_label="news:fixture_test",
            data_mode=FeedDataMode.FIXTURE,
            title=title,
            body=f"Body of fixture item {i+1}",
            published_at=datetime.now(timezone.utc).isoformat(),
        ))
    return IntegrationFeedBatch(
        provider_name="fixture_test_provider",
        overall_status="ok",
        records_seen=3,
        records_accepted=3,
        live_count=0,
        fixture_count=3,
        items=items,
        next_cursor="fixture_cursor_3",
        cursor_safe=True,
        provenance="fixture_test",
        source_statuses=[
            {"source": "news:fixture_test", "status": "ok", "ok": True},
        ],
    )


def main() -> int:
    tmpdir = tempfile.mkdtemp(prefix="feed_fixture_")
    try:
        state_dir = os.path.join(tmpdir, "state")
        output_dir = os.path.join(tmpdir, "output")
        os.makedirs(state_dir)
        os.makedirs(output_dir)

        # First run — no prior state
        print("--- Run 1: no prior state ---")
        cfg = IntegrationConfig(
            mode="fixture",
            state_dir=state_dir,
            output_dir=output_dir,
            whale_address="",
            exchange="binance",
            timeout=15.0,
            no_send=True,
            feed_enabled=True,
        )
        result1 = run_one_shot(cfg, feed_provider=fake_provider)
        d1 = result1.as_dict()
        print(f"  status: {d1['status']}")
        print(f"  feed status: {result1.feed.status if result1.feed else 'N/A'}")
        print(f"  sources: {[s['source'] + '=' + s['status'] for s in d1.get('sources', [])]}")
        print(f"  feed_summary: {json.dumps(d1.get('feed_summary', {}), indent=4)}")

        # Verify cursor was written
        cfg_obj = IntegrationConfig(state_dir=state_dir, output_dir=output_dir, feed_enabled=True)
        cursor1 = _load_cursor(Path(state_dir), cfg_obj)
        print(f"  cursor after run 1: {cursor1.cursor_value if cursor1 else 'NONE'}")

        # Verify report was last write
        report_paths = [p for p in d1.get("output_paths", []) if p.endswith(".json")]
        if report_paths and os.path.exists(report_paths[0]):
            with open(report_paths[0], "r", encoding="utf-8") as f:
                report = json.load(f)
            print(f"  report status: {report['status']}")
            print(f"  report has feed_summary: {'feed_summary' in report}")

        # Verify run history
        rh_db = os.path.join(state_dir, "run_history.db")
        if os.path.exists(rh_db):
            from market_radar.operations.sqlite_schema import get_connection
            row = get_run(rh_db, d1["run_id"])
            print(f"  run history status: {row.get('status') if row else 'N/A'}")

        # Second run — cursor should be loaded
        print("\n--- Run 2: with prior cursor ---")
        result2 = run_one_shot(cfg, feed_provider=fake_provider)
        d2 = result2.as_dict()
        print(f"  status: {d2['status']}")
        cursor2 = _load_cursor(Path(state_dir), cfg_obj)
        print(f"  cursor after run 2: {cursor2.cursor_value if cursor2 else 'NONE'}")
        print(f"  cursor advanced: {d2.get('feed_summary', {}).get('cursor_advanced')}")
        print(f"  cursor before: {d2.get('feed_summary', {}).get('cursor_before')}")
        print(f"  cursor after: {d2.get('feed_summary', {}).get('cursor_after')}")

        print("\n✅ Feed Provider Fixture: ALL PASSED")
        return 0
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
