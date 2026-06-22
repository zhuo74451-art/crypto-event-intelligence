"""Legacy SignalRegistry Adapter — maps legacy Signal objects to new contracts.

Read-only adapter. Does NOT modify legacy objects or trigger any side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from enum import Enum

from ..contracts.evidence import EvidenceItem, VerificationStatus
from ..contracts.strategy import (
    StrategyInstance, StrategyInstanceState, InstanceTransition,
)
from ..contracts.hypothesis import MarketHypothesis, HypothesisStatus
from ..contracts.calibration import (
    ConfidenceStatement, ConfidenceType, NoCalibrationAvailable,
)
from .legacy_observation import MappingQuality, FieldMapping


class LegacySignalRegistryAdapter:
    """Read-only adapter for legacy Signal and SignalRegistry objects."""

    @classmethod
    def map_signal(cls, signal: Any) -> dict:
        """Map a legacy Signal to new contract structures.

        Returns a dict with mapped Hypothesis, StrategyInstance,
        and mapping metadata.

        Critical rule:
        - Legacy confidence is UNSUPPORTED as calibrated probability.
          It becomes uncalibrated_score with production_probability=False.
        - Legacy direction is preserved as-is (lossy — no structured logic).
        """
        signal_dict = cls._to_dict(signal)
        result = {
            "mapped": False,
            "hypothesis": None,
            "instance": None,
            "confidence": None,
            "field_mappings": [],
            "lossy_fields": [],
            "unsupported_fields": [],
            "warnings": [],
        }

        signal_id = signal_dict.get("signal_id", "unknown")
        title = signal_dict.get("title", "")
        assets = signal_dict.get("affected_assets", [])
        direction = signal_dict.get("direction", "neutral")
        confidence = signal_dict.get("confidence", 0.0)
        status = signal_dict.get("status", "candidate")
        first_seen = signal_dict.get("first_seen_at", "")
        evidence = signal_dict.get("evidence", [])

        # Map confidence — legacy confidence is NOT calibrated
        confidence_statement = ConfidenceStatement(
            confidence_type=ConfidenceType.UNCALIBRATED_SCORE,
            value=str(confidence),
            basis="Legacy Signal confidence score — not empirically calibrated",
            probability_value=confidence,
            production_probability=False,
        )

        result["confidence"] = confidence_statement
        result["field_mappings"].append(FieldMapping(
            legacy_field="Signal.confidence",
            new_field="ConfidenceStatement(type=uncalibrated_score)",
            quality=MappingQuality.LOSSY_MAP,
            note="Legacy confidence has no calibration artifact; "
                 "cannot be used as calibrated probability",
        ))

        # Map signal -> StrategyInstance (lossy — legacy has no structured lifecycle)
        instance_state = cls._map_signal_status_to_instance_state(status)
        instance = StrategyInstance(
            instance_id=f"sti_legacy_{signal_id}",
            strategy_id="legacy_unstructured",
            asset=",".join(assets) if isinstance(assets, list) else str(assets),
            time_horizon="medium_term",
            state=instance_state,
            current_evidence_refs=[e.ref if hasattr(e, 'ref') else str(e)
                                   for e in (evidence if isinstance(evidence, list) else [])],
        )

        result["instance"] = instance
        result["field_mappings"].append(FieldMapping(
            legacy_field="Signal (top-level)",
            new_field="StrategyInstance",
            quality=MappingQuality.LOSSY_MAP,
            note="Legacy Signal has no strategy_id, no structured lifecycle, "
                 "no abstention logic — mapping is structural loss",
        ))

        # Map signal -> MarketHypothesis (lossy)
        hypothesis = MarketHypothesis(
            hypothesis_id=f"hyp_legacy_{signal_id}",
            event_id="",
            strategy_instance_id=instance.instance_id,
            affected_assets=[str(a) for a in (assets if isinstance(assets, list) else [])],
            time_horizon="medium_term",
            causal_thesis=title,
            expected_effect=direction,
            status=HypothesisStatus.CANDIDATE,
            confidence_statement=confidence_statement,
        )

        result["hypothesis"] = hypothesis

        result["mapped"] = True
        result["warnings"].append(
            "Legacy Signal has no structured strategy, no abstention logic, "
            "no invalidation conditions. The mapped Hypothesis is a structural "
            "placeholder and should not drive production decisions."
        )

        return result

    @classmethod
    def _to_dict(cls, obj: Any) -> dict:
        if hasattr(obj, "as_dict"):
            return obj.as_dict()
        if hasattr(obj, "__dataclass_fields__"):
            return asdict(obj)
        if isinstance(obj, dict):
            return obj
        return {"_raw": str(obj)}

    @classmethod
    def _map_signal_status_to_instance_state(cls, status: str) -> StrategyInstanceState:
        """Map legacy SignalStatus to StrategyInstanceState."""
        mapping = {
            "candidate": StrategyInstanceState.WATCHING,
            "confirmed": StrategyInstanceState.CONFIRMED,
            "monitoring": StrategyInstanceState.WATCHING,
            "invalidated": StrategyInstanceState.INVALIDATED,
            "expired": StrategyInstanceState.EXPIRED,
            "resolved": StrategyInstanceState.EXPIRED,
        }
        return mapping.get(status.lower().strip(), StrategyInstanceState.INACTIVE)

    @classmethod
    def mapping_summary(cls, signal: Any) -> dict:
        """Return a human-readable summary of what the mapping does and loses."""
        result = cls.map_signal(signal)
        return {
            "mapped": result["mapped"],
            "warnings": len(result["warnings"]),
            "lossy_fields": [fm.legacy_field for fm in result["field_mappings"]
                            if fm.quality == MappingQuality.LOSSY_MAP],
            "unsupported_fields": result["unsupported_fields"],
            "calibration_note": "Legacy confidence is NOT calibrated — "
                                "production_probability forced to False",
        }
