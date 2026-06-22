"""Arbitration Engine V1 — structured conflict resolution between strategies.

Not a voting system. Not a personality contest. Deterministic rules-based
arbitration with explicit conflict preservation.
"""

from __future__ import annotations

from typing import Any, Optional

from ..contracts.arbitration import (
    ArbitrationInput, ArbitrationOutput, HorizonAssessment,
    VerdictState, HorizonBucket,
)
from ..contracts.hypothesis import MarketHypothesis, HypothesisStatus
from ..contracts.calibration import ConfidenceStatement, ConfidenceType
from ..errors.codes import IntelligenceError, ErrorCode


class ArbitrationEngineV1:
    """Deterministic arbitration between multiple strategy hypotheses.

    Phases:
    1. Eligibility filtering
    2. Time horizon grouping
    3. Support/oppose/conflict analysis
    4. Verdict production
    """

    def __init__(self):
        pass

    def arbitrate(self, input_data: ArbitrationInput) -> ArbitrationOutput:
        """Execute the full arbitration pipeline."""
        hypotheses = [MarketHypothesis(**h) if isinstance(h, dict) else h
                      for h in input_data.hypotheses]

        # Phase 1: Eligibility filtering
        eligible = []
        ineligible = []
        for h in hypotheses:
            if self._is_eligible(h):
                eligible.append(h)
            else:
                ineligible.append(h)
                ineligible_reason = f"Hypothesis {h.hypothesis_id}: ineligible (status={h.status.value})"
                if ineligible_reason not in [r for r in ineligible]:

                    ineligible.append(ineligible_reason)

        # Phase 2: Group by time horizon
        horizon_groups: dict[str, list[MarketHypothesis]] = {}
        for h in eligible:
            horizon = self._normalize_horizon(h.time_horizon)
            horizon_groups.setdefault(horizon, []).append(h)

        # Phase 3: Analyze each horizon
        horizon_assessments = []
        for horizon, group in sorted(horizon_groups.items()):
            assessment = self._assess_horizon(horizon, group)
            horizon_assessments.append(assessment)

        # Determine global verdict
        global_verdict = self._determine_global_verdict(horizon_assessments)

        return ArbitrationOutput(
            arbitration_id=f"arb_{len(hypotheses)}",
            asset=input_data.asset,
            sector=input_data.sector,
            horizon_assessments=horizon_assessments,
            global_verdict=global_verdict,
            eligible_count=len(eligible),
            ineligible_count=len(ineligible),
            ineligible_reasons=list(set(
                f"Hypothesis ineligible" for _ in ineligible
            )),
        )

    def _is_eligible(self, hypothesis: MarketHypothesis) -> bool:
        """Check if a hypothesis is eligible for arbitration."""
        if hypothesis.status in (
            HypothesisStatus.INVALIDATED,
            HypothesisStatus.EXPIRED,
            HypothesisStatus.INSUFFICIENT_EVIDENCE,
        ):
            return False
        return True

    def _normalize_horizon(self, horizon: str) -> str:
        """Normalize a horizon string to a standard bucket."""
        mapping = {
            "intraday": HorizonBucket.INTRADAY.value,
            "short_term": HorizonBucket.SHORT_TERM.value,
            "short term": HorizonBucket.SHORT_TERM.value,
            "swing": HorizonBucket.SWING.value,
            "medium_term": HorizonBucket.MEDIUM_TERM.value,
            "medium term": HorizonBucket.MEDIUM_TERM.value,
            "long_term": HorizonBucket.LONG_TERM.value,
            "long term": HorizonBucket.LONG_TERM.value,
        }
        return mapping.get(horizon.lower().strip(), "medium_term")

    def _assess_horizon(self, horizon: str,
                        hypotheses: list[MarketHypothesis]) -> HorizonAssessment:
        """Assess a single time horizon."""
        supporting = []
        opposing = []
        alternative = []
        conflicts = []
        missing_confirmations = []

        for h in hypotheses:
            expected = h.expected_effect.lower()
            if expected in ("bullish", "positive", "up"):
                supporting.append(h.hypothesis_id)
            elif expected in ("bearish", "negative", "down"):
                opposing.append(h.hypothesis_id)
            else:
                alternative.append(h.hypothesis_id)

            if h.status == HypothesisStatus.AWAITING_CONFIRMATION:
                missing_confirmations.append(h.hypothesis_id)

        # Check for conflicts
        if supporting and opposing:
            conflicts.append(f"Mixed signals: {len(supporting)} support vs {len(opposing)} oppose")

        # Determine verdict
        verdict = self._horizon_verdict(
            supporting=supporting,
            opposing=opposing,
            missing_confirmations=missing_confirmations,
            conflicts=conflicts,
            hypotheses=hypotheses,
        )

        return HorizonAssessment(
            horizon=horizon,
            direction="bullish" if len(supporting) > len(opposing) and not conflicts
                     else "bearish" if len(opposing) > len(supporting) and not conflicts
                     else "neutral",
            supporting_hypotheses=supporting,
            opposing_hypotheses=opposing,
            alternative_hypotheses=alternative,
            unresolved_conflicts=conflicts,
            missing_confirmations=missing_confirmations,
            verdict=verdict,
        )

    def _horizon_verdict(self, supporting: list[str], opposing: list[str],
                          missing_confirmations: list[str], conflicts: list[str],
                          hypotheses: list[MarketHypothesis]) -> VerdictState:
        """Determine verdict state for a horizon."""
        # No eligible strategies
        if not supporting and not opposing:
            return VerdictState.INSUFFICIENT_EVIDENCE

        # Missing confirmations
        if missing_confirmations:
            return VerdictState.WAIT_FOR_CONFIRMATION

        # Unresolved conflicts
        if conflicts:
            return VerdictState.CONFLICT_UNRESOLVED

        # Directional available
        if supporting and not opposing:
            return VerdictState.DIRECTIONAL_AVAILABLE
        if opposing and not supporting:
            return VerdictState.DIRECTIONAL_AVAILABLE

        return VerdictState.ABSTAIN

    def _determine_global_verdict(self,
                                  assessments: list[HorizonAssessment]) -> VerdictState:
        """Determine the global verdict across all horizons."""
        if not assessments:
            return VerdictState.INSUFFICIENT_EVIDENCE

        # If any horizon has a real conflict, surface it
        for a in assessments:
            if a.verdict == VerdictState.CONFLICT_UNRESOLVED:
                return VerdictState.CONFLICT_UNRESOLVED

        # If all horizons are directional_available, that's fine
        all_directional = all(
            a.verdict == VerdictState.DIRECTIONAL_AVAILABLE
            for a in assessments
        )
        if all_directional:
            return VerdictState.DIRECTIONAL_AVAILABLE

        # Mix of waiting and directional
        has_waiting = any(
            a.verdict == VerdictState.WAIT_FOR_CONFIRMATION
            for a in assessments
        )
        if has_waiting:
            return VerdictState.WAIT_FOR_CONFIRMATION

        return VerdictState.INSUFFICIENT_EVIDENCE
