"""Test no cross-asset records have instrument_id or symbol fields.
Test no duplicate (event_id, series_id) pairs."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import pytest

PILOT_DIR = Path("data/intelligence/historical_market/pilot_v3")
CROSS_ASSET_FILE = PILOT_DIR / "cross_asset_context_v3.jsonl"

FORBIDDEN_FIELDS = ["instrument_id", "symbol"]


class TestCrossAssetNotDuplicatedByCryptoAsset:
    """Validate that cross-asset context records do not carry crypto-specific
    fields and have no duplicate (event_id, series_id) pairs."""

    def load_records(self):
        records = []
        with open(CROSS_ASSET_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def test_no_instrument_id_field(self):
        records = self.load_records()
        found = [i for i, r in enumerate(records) if "instrument_id" in r]
        assert not found, (
            f"Found {len(found)} record(s) with forbidden 'instrument_id' field: "
            f"indices {found[:10]}"
        )

    def test_no_symbol_field(self):
        records = self.load_records()
        found = [i for i, r in enumerate(records) if "symbol" in r]
        assert not found, (
            f"Found {len(found)} record(s) with forbidden 'symbol' field: "
            f"indices {found[:10]}"
        )

    def test_no_forbidden_fields(self):
        records = self.load_records()
        errors = []
        for i, r in enumerate(records):
            for field in FORBIDDEN_FIELDS:
                if field in r:
                    errors.append(
                        f"Record {i} (event={r.get('event_id', '?')}, "
                        f"series={r.get('series_id', '?')}) "
                        f"has forbidden field '{field}'"
                    )
        assert not errors, (
            f"Found {len(errors)} records with forbidden fields:\n"
            + "\n".join(errors[:10])
        )

    def test_no_duplicate_event_id_series_id_pairs(self):
        records = self.load_records()
        pairs = [(r["event_id"], r["series_id"]) for r in records]
        seen = set()
        duplicates = []
        for i, pair in enumerate(pairs):
            if pair in seen:
                duplicates.append(f"Record {i}: duplicate pair {pair}")
            seen.add(pair)
        assert not duplicates, (
            f"Found {len(duplicates)} duplicate (event_id, series_id) pairs:\n"
            + "\n".join(duplicates[:10])
        )

    def test_record_count_matches_unique_pairs(self):
        """Total record count should equal the number of unique
        (event_id, series_id) pairs (i.e. no duplicates)."""
        records = self.load_records()
        pairs = {(r["event_id"], r["series_id"]) for r in records}
        assert len(records) == len(pairs), (
            f"Record count ({len(records)}) does not match unique pair "
            f"count ({len(pairs)}) — duplicates exist"
        )
