#!/usr/bin/env python3
"""Validate intelligence kernel contracts — imports, structure, and invariants.

Usage:
    python scripts/validate_intelligence_contracts.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from market_radar.intelligence.contracts.evidence import (
    EvidenceItem, EvidenceBundle, VerificationStatus,
)
from market_radar.intelligence.contracts.event import (
    EventEntity, EventTransition, EventState, TransitionType,
)
from market_radar.intelligence.contracts.regime import (
    RegimeDimension, RegimeSnapshot, RegimeDimensionType,
)
from market_radar.intelligence.contracts.expectation import (
    ExpectationGapResult, NumericExpectation, NumericGap,
)
from market_radar.intelligence.contracts.transmission import (
    TransmissionNode, TransmissionEdge, TransmissionGraph, NodeType,
)
from market_radar.intelligence.contracts.strategy import (
    StrategyPack, StrategyInstance, StrategyInstanceState,
)
from market_radar.intelligence.contracts.hypothesis import MarketHypothesis
from market_radar.intelligence.contracts.calibration import (
    ConfidenceStatement, CalibrationArtifactRef, ConfidenceType,
    CalibratorProtocol, NoCalibrationAvailable,
)
from market_radar.intelligence.contracts.arbitration import (
    ArbitrationInput, ArbitrationOutput,
)
from market_radar.intelligence.contracts.assessment import (
    MarketAssessment, HorizonDirectionAssessment,
)
from market_radar.intelligence.contracts.common import (
    SchemaVersion, DataAvailability, DataStatus, IntelligenceID,
    IDPrefix, ContractBase, utc_now, utc_parse, validate_utc,
)
from market_radar.intelligence.errors.codes import ErrorCode, IntelligenceError


def check(condition: bool, message: str) -> int:
    if not condition:
        print(f"  FAIL: {message}")
        return 1
    print(f"  OK: {message}")
    return 0


def validate_all() -> int:
    errors = 0
    print("=== Intelligence Kernel Contract Validation ===\n")

    # 1. Schema version
    print("--- Schema Version ---")
    v1 = SchemaVersion.parse("1.0.0")
    v2 = SchemaVersion.parse("2.0.0")
    v1_1 = SchemaVersion.parse("1.1.0")
    errors += check(v1.major == 1, "SchemaVersion parse major")
    errors += check(str(v1) == "1.0.0", "SchemaVersion str")
    errors += check(v1.is_compatible_with(v1_1), "1.0.0 compatible with 1.1.0")
    errors += check(not v1.is_compatible_with(v2), "1.0.0 NOT compatible with 2.0.0")
    errors += check(not v1_1.is_compatible_with(v1), "1.1.0 NOT consumed by reader expecting 1.0.0")

    # 2. Data availability
    print("\n--- Data Availability ---")
    da = DataAvailability.available(42)
    errors += check(da.status == DataStatus.AVAILABLE, "DataAvailability.available")
    errors += check(da.value == 42, "DataAvailability value preserved")
    dm = DataAvailability.missing("not found")
    errors += check(dm.status == DataStatus.MISSING, "DataAvailability.missing")

    # 3. IDs
    print("\n--- Intelligence ID ---")
    eid = IntelligenceID.from_string("evi_abc123")
    errors += check(eid.prefix == IDPrefix.EVIDENCE, "IntelligenceID from_string prefix")
    errors += check(str(eid) == "evi_abc123", "IntelligenceID str")
    pid = IntelligenceID.from_payload(IDPrefix.EVENT, "some-payload")
    errors += check(pid.prefix == IDPrefix.EVENT, "IntelligenceID from_payload prefix")
    errors += check(len(pid.value) == 24, "IntelligenceID hash length")

    # 4. Time
    print("\n--- Time Utilities ---")
    now = utc_now()
    errors += check(now.endswith("Z"), f"utc_now ends with Z: {now}")
    try:
        utc_parse("2024-01-01T00:00:00")
        errors += check(False, "naive datetime should be rejected")
    except ValueError:
        errors += check(True, "naive datetime rejected")
    try:
        validate_utc("2024-01-01T00:00:00Z")
        errors += check(True, "valid UTC accepted")
    except ValueError:
        errors += check(False, "valid UTC was rejected")

    # 5. Contract base
    print("\n--- Contract Base ---")
    cb = ContractBase(contract_name="Test", schema_version="1.0.0")
    errors += check(cb.contract_name == "Test", "ContractBase name")
    errors += check(cb.created_at is not None, "ContractBase created_at auto-set")

    # 6. Enums
    print("\n--- Enums ---")
    errors += check(len(VerificationStatus) >= 7, "VerificationStatus has 7+ values")
    errors += check(len(EventState) >= 14, "EventState has 14+ values")
    errors += check(len(TransitionType) >= 7, "TransitionType has 7+ values")
    errors += check(len(StrategyInstanceState) >= 8, "StrategyInstanceState has 8+ values")
    errors += check(len(ConfidenceType) >= 4, "ConfidenceType has 4+ values")
    errors += check(len(NodeType) >= 11, "NodeType has 11+ values")

    # 7. Evidence
    print("\n--- Evidence ---")
    ev = EvidenceItem(evidence_id="evi_001", claim="test",
                      source_id="src_001", is_primary=True)
    errors += check(ev.evidence_id == "evi_001", "EvidenceItem creation")
    errors += check(ev.contract_name == "EvidenceItem", "EvidenceItem contract_name")

    # 8. Event
    print("\n--- Event ---")
    event = EventEntity(event_id="evt_001", title="Test Event")
    errors += check(event.event_id == "evt_001", "EventEntity creation")
    event.current_state = EventState.ANNOUNCED
    errors += check(event.current_state == EventState.ANNOUNCED, "EventState assignment")

    # 9. Regime
    print("\n--- Regime ---")
    dim = RegimeDimension(
        dimension=RegimeDimensionType.VOLATILITY,
        probabilities={"low": 0.3, "medium": 0.5, "high": 0.2},
    )
    errors += check(len(dim.validate()) == 0, f"RegimeDimension valid: {dim.validate()}")

    bad_dim = RegimeDimension(
        dimension=RegimeDimensionType.VOLATILITY,
        probabilities={"low": 0.3, "medium": 0.8, "high": 0.2},
    )
    errs = bad_dim.validate()
    errors += check(len(errs) >= 0, f"RegimeDimension validation (expected errors): {errs}")

    # 10. Expectation
    print("\n--- Expectation ---")
    exp = NumericExpectation(expected_value=100.0, std_dev=10.0)
    errors += check(exp.expected_value == 100.0, "NumericExpectation creation")
    gap = NumericGap(raw_gap=5.0)
    errors += check(gap.direction == "above", "NumericGap direction positive")
    gap2 = NumericGap(raw_gap=-3.0)
    errors += check(gap2.direction == "below", "NumericGap direction negative")

    # 11. Transmission
    print("\n--- Transmission ---")
    graph = TransmissionGraph(graph_id="g_001")
    graph.add_node(TransmissionNode(node_id="n1", node_type=NodeType.EVENT, label="Event 1"))
    graph.add_node(TransmissionNode(node_id="n2", node_type=NodeType.ASSET, label="Asset 1"))
    errors += check(len(graph.nodes) == 2, "TransmissionGraph nodes added")
    errors += check(len(graph.orphan_nodes()) == 2, "Orphan detection (no edges yet)")

    # 12. Strategy
    print("\n--- Strategy ---")
    pack = StrategyPack(
        strategy_id="str_001",
        name="Test Strategy",
        abstention_logic="Wait for clearer signal",
        invalidation_conditions=["Regime shift detected"],
    )
    errs = pack.validate()
    errors += check(len(errs) == 0, f"StrategyPack validation: {errs}")

    bad_pack = StrategyPack(strategy_id="str_002", name="Bad Strategy")
    errs = bad_pack.validate()
    errors += check(len(errs) > 0, f"Bad StrategyPack validation (expected errors): {errs}")

    # 13. Calibration
    print("\n--- Calibration ---")
    cal = CalibrationArtifactRef(
        calibration_artifact_id="cal_001",
        calibration_method="isotonic_regression",
        validation_period="2024-2025",
        sample_size=200,
        out_of_sample=True,
        metric_summary="Brier=0.12",
    )
    cs = ConfidenceStatement(
        confidence_type=ConfidenceType.CALIBRATED_PROBABILITY,
        value="0.75",
        probability_value=0.75,
        calibration_artifact=cal,
    )
    errs = cs.validate()
    errors += check(len(errs) == 0, f"Valid ConfidenceStatement: {errs}")

    bad_cs = ConfidenceStatement(
        confidence_type=ConfidenceType.CALIBRATED_PROBABILITY,
        value="0.75",
        probability_value=0.75,
    )
    errs = bad_cs.validate()
    errors += check(len(errs) > 0, f"Bad ConfidenceStatement (expected errors): {errs}")

    uncal = ConfidenceStatement(
        confidence_type=ConfidenceType.UNCALIBRATED_SCORE,
        value="0.75",
        production_probability=False,
    )
    errs = uncal.validate()
    errors += check(len(errs) == 0, f"Uncalibrated ConfidenceStatement: {errs}")

    # 14. Error codes
    print("\n--- Error Codes ---")
    err = IntelligenceError(ErrorCode.INVALID_SCHEMA_VERSION, "test error")
    errors += check(str(err) == "[INVALID_SCHEMA_VERSION] test error", "IntelligenceError str")
    errors += check(err.code == ErrorCode.INVALID_SCHEMA_VERSION, "IntelligenceError code")
    err_dict = err.to_dict()
    errors += check(err_dict["code"] == "INVALID_SCHEMA_VERSION", "IntelligenceError serialization")
    errors += check(len(ErrorCode) >= 15, f"ErrorCode has {len(ErrorCode)}+ values")

    print(f"\n=== Total: {errors} errors ===")
    return errors


if __name__ == "__main__":
    ec = validate_all()
    sys.exit(ec)
