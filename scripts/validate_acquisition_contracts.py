#!/usr/bin/env python3
"""Validate acquisition contracts — schemas exist, Python contracts import, sample data valid."""
import json
import os
import sys

# Ensure project root is on path
_project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import json
import os
import sys
from datetime import datetime, timezone


# --- Test 1: Python contracts import ---
def test_contracts_import() -> list[str]:
    errors = []
    try:
        from market_radar.acquisition.contracts import (
            AcquisitionError, AcquisitionErrorCode, FiveTimestamps,
            TimestampEvidence, TimestampQuality, TimestampAnomaly,
            SourceContract, AuthorityTier, SourceRole,
            RawDocument, NormalizedObservation, ObservationStatus,
            RevisionRecord, RevisionType,
            HealthStatus, SourceHealthReport, HealthIndicator,
            ReplayMode, ReplayQuery, ReplayResult,
        )
        count = len([x for x in dir() if not x.startswith("_")])
        print(f"PASS: contracts import OK ({count} symbols)")
    except Exception as e:
        errors.append(f"FAIL: contracts import — {e}")
        print(f"FAIL: contracts import — {e}")
    return errors


# --- Test 2: Timestamps are timezone-aware ---
def test_timestamps_timezone() -> list[str]:
    errors = []
    try:
        from market_radar.acquisition.contracts.timestamps import utc_now
        from market_radar.acquisition.contracts import FiveTimestamps, TimestampEvidence, TimestampQuality

        now = utc_now()
        assert now.tzinfo is not None, "utc_now() must be timezone-aware"
        assert now.tzinfo.utcoffset(now) is not None, "utc_now() must have UTC offset"

        ts = FiveTimestamps(
            retrieved_at=TimestampEvidence(now, TimestampQuality.RETRIEVAL_ONLY)
        )
        d = ts.to_dict()
        assert d["retrieved_at"]["value"] is not None, "retrieved_at must have value"
        print(f"PASS: timestamps are timezone-aware ({now.isoformat()})")
    except Exception as e:
        errors.append(f"FAIL: timestamp timezone — {e}")
        print(f"FAIL: timestamp timezone — {e}")
    return errors


# --- Test 3: SourceContract serialization round-trip ---
def test_source_contract_roundtrip() -> list[str]:
    errors = []
    try:
        from market_radar.acquisition.contracts import SourceContract, AuthorityTier, SourceRole
        c = SourceContract(
            source_id="test-source",
            source_name="Test Source",
            authority_tier=AuthorityTier.PRIMARY_OFFICIAL,
            roles=(SourceRole.DISCOVERY,),
        )
        d = c.to_dict()
        assert d["source_id"] == "test-source"
        assert d["authority_tier"] == "primary_official"
        c2 = SourceContract.from_dict(d)
        assert c2.source_id == c.source_id
        assert c2.authority_tier == c.authority_tier
        print("PASS: SourceContract round-trip OK")
    except Exception as e:
        errors.append(f"FAIL: SourceContract round-trip — {e}")
        print(f"FAIL: SourceContract round-trip — {e}")
    return errors


# --- Test 4: Error serialization ---
def test_error_serialization() -> list[str]:
    errors = []
    try:
        from market_radar.acquisition.contracts import AcquisitionError, AcquisitionErrorCode
        e = AcquisitionError(AcquisitionErrorCode.RATE_LIMITED, "Too many requests", source_id="test", http_status=429)
        d = e.to_dict()
        assert d["code"] == "RATE_LIMITED"
        assert d["http_status"] == 429
        print("PASS: AcquisitionError serialization OK")
    except Exception as e:
        errors.append(f"FAIL: error serialization — {e}")
        print(f"FAIL: error serialization — {e}")
    return errors


# --- Test 5: Observation has no market direction ---
def test_observation_no_market_direction() -> list[str]:
    errors = []
    forbidden = ["bullish", "bearish", "signal_score", "buy", "sell", "market_impact"]
    try:
        from market_radar.acquisition.contracts import NormalizedObservation
        o = NormalizedObservation()
        d = o.to_dict()
        for key in d:
            assert not any(f in key.lower() for f in forbidden), f"Found forbidden field: {key}"
        print("PASS: NormalizedObservation has no market direction fields")
    except Exception as e:
        errors.append(f"FAIL: observation no market direction — {e}")
        print(f"FAIL: observation no market direction — {e}")
    return errors


# --- Test 6: Schema files exist and are valid ---
def test_schema_files() -> list[str]:
    errors = []
    schema_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "schemas", "acquisition", "v1"))
    expected = [
        "source_contract.schema.json",
        "source_registry.schema.json",
        "acquisition_timestamp.schema.json",
        "raw_document.schema.json",
        "normalized_observation.schema.json",
        "revision.schema.json",
        "source_health.schema.json",
        "replay_snapshot.schema.json",
        "evidence_manifest.schema.json",
    ]
    for fname in expected:
        path = os.path.join(schema_dir, fname)
        if not os.path.exists(path):
            errors.append(f"MISSING schema: {fname}")
            print(f"FAIL: missing schema — {fname}")
        else:
            try:
                with open(path, "r") as f:
                    json.load(f)
                print(f"PASS: schema valid — {fname}")
            except json.JSONDecodeError as e:
                errors.append(f"INVALID schema: {fname} — {e}")
                print(f"FAIL: invalid schema — {fname} ({e})")
    return errors


def main():
    print("=" * 60)
    print("Acquisition Contract Validation")
    print("=" * 60)

    all_errors = []
    all_errors.extend(test_contracts_import())
    all_errors.extend(test_timestamps_timezone())
    all_errors.extend(test_source_contract_roundtrip())
    all_errors.extend(test_error_serialization())
    all_errors.extend(test_observation_no_market_direction())
    all_errors.extend(test_schema_files())

    print("\n" + "=" * 60)
    if all_errors:
        print(f"FAILED: {len(all_errors)} error(s)")
        for e in all_errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("ALL VALIDATION PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
