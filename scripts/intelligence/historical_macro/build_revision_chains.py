"""Build revision chains from release events and revisions.

Tracks the sequence of revisions for each event series.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from market_radar.intelligence.acquisition.historical_macro.contracts import (
    MacroRevisionRecordV1,
    utc_now,
)


def build_revision_chains(
    events_path: str,
    output_dir: str,
) -> list[MacroRevisionRecordV1]:
    """Build revision chains from existing release events.

    Currently a stub ¡ª full revision chain construction requires
    ALFRED vintage API access or BLS revision-specific endpoints.
    Returns a minimal set of revision records captured during data ingestion.
    """
    revisions: list[MacroRevisionRecordV1] = []
    seen_ids: set[str] = set()

    rev_path = os.path.join(output_dir, "normalized", "macro_revision_records_v1.jsonl")
    if os.path.exists(rev_path):
        with open(rev_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    rev = MacroRevisionRecordV1(**data)
                    if rev.revision_id:
                        seen_ids.add(rev.revision_id)
                    revisions.append(rev)
        print(f"  Loaded {len(revisions)} existing revision records")

    return revisions


def create_revision_record(
    event_id: str,
    series_id: str,
    reference_period: str,
    previous_value: float,
    revised_value: float,
    revision_sequence: int,
    source_url: str,
) -> MacroRevisionRecordV1:
    """Create a single revision record."""
    return MacroRevisionRecordV1(
        event_id=event_id,
        series_id=series_id,
        reference_period=reference_period,
        revision_published_at_utc=utc_now(),
        previous_value=previous_value,
        revised_value=revised_value,
        revision_sequence=revision_sequence,
        source_url=source_url,
    )


def write_output(revisions: list[MacroRevisionRecordV1], output_dir: str):
    """Write revision records to canonical output."""
    norm_dir = os.path.join(output_dir, "normalized")
    os.makedirs(norm_dir, exist_ok=True)

    rev_path = os.path.join(norm_dir, "macro_revision_records_v1.jsonl")
    with open(rev_path, "w") as f:
        for rev in revisions:
            f.write(json.dumps(rev.to_dict(), ensure_ascii=False) + "\n")
    print(f"Wrote {len(revisions)} revision records to {rev_path}")


def main():
    parser = argparse.ArgumentParser(description="Build revision chains")
    parser.add_argument("--events-path", default="data/intelligence/historical_macro/normalized/macro_release_events_v1.jsonl")
    parser.add_argument("--output-dir", default="data/intelligence/historical_macro")
    args = parser.parse_args()

    revisions = build_revision_chains(args.events_path, args.output_dir)
    write_output(revisions, args.output_dir)

    print(f"\n=== Revision Build Summary ===")
    print(f"Revisions: {len(revisions)}")


if __name__ == "__main__":
    main()
