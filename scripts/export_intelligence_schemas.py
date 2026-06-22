#!/usr/bin/env python3
"""Export intelligence kernel models to JSON Schema files.

Usage:
    python scripts/export_intelligence_schemas.py          # Export all schemas
    python scripts/export_intelligence_schemas.py --check   # Check for drift only
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from market_radar.intelligence.serialization.schema_export import (
    export_schema, check_schema_drift, write_schema,
)
from market_radar.intelligence.contracts.evidence import EvidenceItem, EvidenceBundle
from market_radar.intelligence.contracts.event import EventEntity, EventTransition
from market_radar.intelligence.contracts.regime import RegimeSnapshot, RegimeDimension
from market_radar.intelligence.contracts.expectation import (
    NumericExpectation, NumericRangeExpectation,
    CategoricalExpectation, BinaryProbabilityExpectation,
    ExpectationGapResult,
)
from market_radar.intelligence.contracts.transmission import (
    TransmissionNode, TransmissionEdge, TransmissionGraph,
)
from market_radar.intelligence.contracts.strategy import (
    StrategyPack, StrategyInstance,
)
from market_radar.intelligence.contracts.hypothesis import MarketHypothesis
from market_radar.intelligence.contracts.arbitration import (
    ArbitrationInput, ArbitrationOutput,
)
from market_radar.intelligence.contracts.calibration import (
    ConfidenceStatement, CalibrationArtifactRef,
)
from market_radar.intelligence.contracts.assessment import (
    HorizonDirectionAssessment, MarketAssessment,
)

SCHEMA_DIR = PROJECT_ROOT / "schemas" / "intelligence" / "v1"

MODELS = {
    "common.schema.json": None,  # No simple top-level model for common
    "evidence.schema.json": EvidenceItem,
    "event.schema.json": EventEntity,
    "regime.schema.json": RegimeSnapshot,
    "expectation.schema.json": ExpectationGapResult,
    "transmission.schema.json": TransmissionGraph,
    "strategy_pack.schema.json": StrategyPack,
    "market_hypothesis.schema.json": MarketHypothesis,
    "arbitration.schema.json": ArbitrationOutput,
    "calibration.schema.json": ConfidenceStatement,
    "market_assessment.schema.json": MarketAssessment,
}


def export_all(check_only: bool = False) -> bool:
    """Export all schemas. Returns True if all match (for --check)."""
    all_match = True
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)

    for filename, model in MODELS.items():
        if model is None:
            continue
        schema_path = SCHEMA_DIR / filename

        if check_only:
            matches = check_schema_drift(model, str(schema_path))
            status = "OK" if matches else "DRIFT"
            if not matches:
                all_match = False
            print(f"  {filename}: {status}")
        else:
            write_schema(model, str(schema_path))
            print(f"  {filename}: written")

    return all_match


def main():
    check_only = "--check" in sys.argv
    action = "Checking" if check_only else "Exporting"
    print(f"Intelligence Kernel — {action} JSON Schemas")
    print(f"  Target: {SCHEMA_DIR}")

    all_match = export_all(check_only=check_only)

    if check_only:
        if all_match:
            print("\nAll schemas match Python models (no drift).")
            return 0
        else:
            print("\nERROR: Schema drift detected. Run without --check to update.")
            return 1
    else:
        print(f"\nExported {len([m for m in MODELS.values() if m])} schemas to {SCHEMA_DIR}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
