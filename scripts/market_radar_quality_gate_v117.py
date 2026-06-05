"""Market Radar v1.17 — Unified Quality Gate

Takes a NormalizedSnapshot, runs it through the card type registry's admission
and block rules, and returns a standardized quality gate decision.

This is the SECOND layer in the v117 pipeline:
  ... → NormalizedSnapshot → QualityGate → gate_result → ...

Design:
  - QualityGate class encapsulates the v112a card_type_registry rule engine
  - Produces a QualityGateResult with detailed pass/fail/block info
  - Deterministic only — no AI, no external API calls
  - Reuses validate_signal_against_card_type() from v112a

Constraints:
  - No external API calls
  - No TG send
  - No daemon/cron/loop
  - No token/key/secret read or print

Usage:
    from scripts.market_radar_quality_gate_v117 import (
        QualityGate, QualityGateResult, run_quality_gate,
    )
    from scripts.market_radar_adapter_v117 import NormalizedSnapshot

    gate = QualityGate()
    result = gate.evaluate(snapshot)
    print(f"Passed: {result.quality_gate_passed}")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

CN_TZ = timezone(timedelta(hours=8))
GATE_VERSION = "v1.17"

# Import the existing card type registry from v112a
# (must be importable from the project root or scripts dir)
try:
    from scripts.market_radar_card_type_registry_v112a import (
        CARD_TYPE_REGISTRY,
        get_card_type,
        validate_signal_against_card_type,
        check_admission,
        check_block,
    )
except ImportError:
    # Fallback: try relative import
    import sys
    import os
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    if _script_dir not in sys.path:
        sys.path.insert(0, _script_dir)
    from market_radar_card_type_registry_v112a import (
        CARD_TYPE_REGISTRY,
        get_card_type,
        validate_signal_against_card_type,
        check_admission,
        check_block,
    )


def china_stamp() -> str:
    """Return current time in UTC+8 format."""
    return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


# ══════════════════════════════════════════════════════════════════════════════════════
# Quality Gate Result
# ══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class QualityGateResult:
    """Standardized result from the quality gate.

    Fields:
        card_type: Card type key.
        snapshot_id: The snapshot that was evaluated.
        quality_gate_passed: Overall pass/fail.
        schema_valid: Required fields check passed.
        admission_passed: Admission rules passed.
        block_triggered: Any block rule triggered.
        block_reason: First block reason, if any.
        admission_details: Dict of {rule_id: bool}.
        block_details: Dict of {rule_id: bool}.
        missing_required: List of missing required fields.
        validation_detail: Full validation result from v112a.
        gate_version: Version of the quality gate.
        evaluated_at: When the evaluation was performed.
    """
    card_type: str
    snapshot_id: str
    quality_gate_passed: bool
    schema_valid: bool
    admission_passed: bool
    block_triggered: bool
    block_reason: str | None = None
    admission_details: dict[str, bool] = field(default_factory=dict)
    block_details: dict[str, bool] = field(default_factory=dict)
    missing_required: list[str] = field(default_factory=list)
    validation_detail: dict = field(default_factory=dict)
    gate_version: str = GATE_VERSION
    evaluated_at: str = field(default_factory=china_stamp)

    def as_dict(self) -> dict:
        return {
            "card_type": self.card_type,
            "snapshot_id": self.snapshot_id,
            "quality_gate_passed": self.quality_gate_passed,
            "schema_valid": self.schema_valid,
            "admission_passed": self.admission_passed,
            "block_triggered": self.block_triggered,
            "block_reason": self.block_reason,
            "admission_details": self.admission_details,
            "block_details": self.block_details,
            "missing_required": self.missing_required,
            "gate_version": self.gate_version,
            "evaluated_at": self.evaluated_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════════════
# Quality Gate
# ══════════════════════════════════════════════════════════════════════════════════════

class QualityGate:
    """Unified quality gate for all card types.

    Evaluates a NormalizedSnapshot against the card type registry's
    admission and block rules from v112a.

    The quality gate is purely deterministic — it checks:
      1. Schema completeness (required fields)
      2. Admission rules (conditions that must be met)
      3. Block rules (conditions that block the card)
    """

    def __init__(self):
        self._evaluation_count = 0
        self._pass_count = 0
        self._block_count = 0

    @property
    def evaluation_count(self) -> int:
        return self._evaluation_count

    @property
    def pass_count(self) -> int:
        return self._pass_count

    @property
    def block_count(self) -> int:
        return self._block_count

    def evaluate(self, snapshot) -> QualityGateResult:
        """Evaluate a NormalizedSnapshot against quality rules.

        Args:
            snapshot: A NormalizedSnapshot from an adapter.

        Returns:
            QualityGateResult with detailed pass/fail/block information.
        """
        self._evaluation_count += 1

        # Get card type definition from registry
        card_type_def = get_card_type(snapshot.card_type)
        if card_type_def is None:
            result = QualityGateResult(
                card_type=snapshot.card_type,
                snapshot_id=snapshot.snapshot_id,
                quality_gate_passed=False,
                schema_valid=False,
                admission_passed=False,
                block_triggered=True,
                block_reason=f"Unknown card_type: {snapshot.card_type}",
            )
            self._block_count += 1
            return result

        # Run the v112a validation engine
        validation = validate_signal_against_card_type(
            snapshot.signal_data, card_type_def
        )

        # Extract results
        schema_valid = validation.get("schema_valid", False)
        admission_passed = validation.get("admission_passed", False)
        block_triggered = validation.get("block_triggered", False)
        block_reason = validation.get("block_reason")
        admission_result = validation.get("admission_result", {})
        block_result = validation.get("block_result", {})
        missing_required = validation.get("missing_required", [])

        # Overall quality gate passed = schema valid + admission passed + no blocks
        quality_gate_passed = schema_valid and admission_passed and not block_triggered

        if not quality_gate_passed:
            self._block_count += 1
        else:
            self._pass_count += 1

        return QualityGateResult(
            card_type=snapshot.card_type,
            snapshot_id=snapshot.snapshot_id,
            quality_gate_passed=quality_gate_passed,
            schema_valid=schema_valid,
            admission_passed=admission_passed,
            block_triggered=block_triggered,
            block_reason=block_reason,
            admission_details=admission_result,
            block_details=block_result,
            missing_required=missing_required,
            validation_detail=validation,
        )

    def evaluate_batch(self, snapshots: list) -> list[QualityGateResult]:
        """Evaluate multiple snapshots.

        Args:
            snapshots: List of NormalizedSnapshot objects.

        Returns:
            List of QualityGateResult objects.
        """
        return [self.evaluate(s) for s in snapshots]


# ── Module-level convenience ────────────────────────────────────────────────────

def run_quality_gate(snapshot) -> QualityGateResult:
    """Run quality gate on a single snapshot (convenience function)."""
    gate = QualityGate()
    return gate.evaluate(snapshot)


def run_quality_gate_batch(snapshots: list) -> list[QualityGateResult]:
    """Run quality gate on multiple snapshots (convenience function)."""
    gate = QualityGate()
    return gate.evaluate_batch(snapshots)
