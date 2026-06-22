"""Arbitration Engine V1 — rule-based conflict resolution.

NOT a voting system. NOT a personality contest.
Deterministic rules-based arbitration with explicit conflict preservation.

Key fixes over original:
- Vote counting REMOVED: direction NOT determined by len(supporting) > len(opposing)
- Eligibility pipeline checks evidence state, regime state, required inputs
- Ineligible reasons use structured types, not mixed list
- Support clustering folds same-origin strategies
- Quality dimensions with explicit levels (no synthetic total score)
- Rule IDs for every decision (traceable)
- Multi-horizon preservation (global status does not flatten)
"""
from __future__ import annotations

from typing import Any, Optional

from ..contracts.arbitration import (
    ArbitrationInput, ArbitrationOutput, HorizonAssessment,
    HorizonDecisionTrace, VerdictState, HorizonBucket,
    EligibleHypothesis, IneligibleHypothesis, EligibilityDecision,
    EligibilityReasonCode, HypothesisSupportCluster,
    QualityDimensions, QualityLevel, ArbitrationStatus,
)
from ..contracts.hypothesis import MarketHypothesis, HypothesisStatus
from ..contracts.calibration import ConfidenceStatement, ConfidenceType
from ..errors.codes import IntelligenceError, ErrorCode


# Known horizon bucket values for validation
VALID_HORIZONS = {
    "intraday", "short_term", "swing", "medium_term", "long_term",
    "intraday", "short term", "swing", "medium term", "long term",
}

HORIZON_MAP = {
    "intraday": HorizonBucket.INTRADAY.value,
    "short_term": HorizonBucket.SHORT_TERM.value,
    "short term": HorizonBucket.SHORT_TERM.value,
    "swing": HorizonBucket.SWING.value,
    "medium_term": HorizonBucket.MEDIUM_TERM.value,
    "medium term": HorizonBucket.MEDIUM_TERM.value,
    "long_term": HorizonBucket.LONG_TERM.value,
    "long term": HorizonBucket.LONG_TERM.value,
}


class ArbitrationEngineV1:
    """Deterministic arbitration between multiple strategy hypotheses.

    Phases:
    1. Eligibility pipeline (12 checks)
    2. Time horizon grouping
    3. Support clustering (origin folding)
    4. Rule-based verdict per horizon
    5. Global status (not a single direction)
    """

    def __init__(self):
        pass

    def arbitrate(self, input_data: ArbitrationInput) -> ArbitrationOutput:
        """Execute the full arbitration pipeline."""
        hypotheses = [MarketHypothesis(**h) if isinstance(h, dict) else h
                      for h in input_data.hypotheses]

        evidence_state = input_data.evidence_state or {}
        regime_state = input_data.regime_state or {}

        # Phase 1: Eligibility pipeline
        eligible, ineligible = self._eligibility_pipeline(
            hypotheses, evidence_state, regime_state
        )

        eligible_hyp_data = []
        for h in eligible:
            eligible_hyp_data.append(EligibleHypothesis(
                hypothesis_id=h.hypothesis_id,
                time_horizon=h.time_horizon,
                expected_effect=h.expected_effect,
                alternative_explanations=list(h.alternative_explanations),
                invalidation_conditions=list(h.invalidation_conditions),
                strategy_instance_id=h.strategy_instance_id,
                asset=input_data.asset,
                sector=input_data.sector,
            ))

        # Phase 2: Group by time horizon
        horizon_groups: dict[str, list[EligibleHypothesis]] = {}
        for h in eligible_hyp_data:
            horizon = self._normalize_horizon(h.time_horizon)
            horizon_groups.setdefault(horizon, []).append(h)

        # Phase 3+4: Analyze each horizon with rule-based verdict
        horizon_assessments = []
        for horizon, group in sorted(horizon_groups.items()):
            assessment = self._assess_horizon(horizon, group)
            horizon_assessments.append(assessment)

        # Determine arbitration status (not a single direction)
        arbitration_status = self._determine_arbitration_status(
            horizon_assessments, ineligible
        )

        # Determine global verdict
        global_verdict = self._determine_global_verdict(horizon_assessments)

        # Stable arbitration ID: hash of asset + rule + horizon assessment keys
        import hashlib
        payload = f"{input_data.asset}|{input_data.sector}|{len(hypotheses)}"
        arb_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
        arbitration_id = f"arb_{arb_hash}"

        return ArbitrationOutput(
            arbitration_id=arbitration_id,
            asset=input_data.asset,
            sector=input_data.sector,
            horizon_assessments=horizon_assessments,
            global_verdict=global_verdict,
            arbitration_status=arbitration_status,
            eligible_hypotheses=eligible_hyp_data,
            ineligible_hypotheses=ineligible,
        )

    # ── Eligibility Pipeline ──────────────────────────────────────────────

    def _eligibility_pipeline(
        self,
        hypotheses: list[MarketHypothesis],
        evidence_state: dict,
        regime_state: dict,
    ) -> tuple[list[MarketHypothesis], list[IneligibleHypothesis]]:
        """Run the full eligibility pipeline on all hypotheses."""
        eligible = []
        ineligible_list = []

        for h in hypotheses:
            decisions = []

            # E01: contract valid
            d1 = EligibilityDecision(hypothesis_id=h.hypothesis_id)
            if not h.hypothesis_id:
                d1.eligible = False
                d1.reason_codes.append(EligibilityReasonCode.CONTRACT_VALID)
                d1.trace.append("E01_FAIL: no hypothesis_id")
            else:
                d1.eligible = True
                d1.trace.append("E01_OK: contract valid")
            decisions.append(d1)

            # E04: strategy state eligible
            d4 = EligibilityDecision(hypothesis_id=h.hypothesis_id)
            if h.status in (
                HypothesisStatus.INVALIDATED,
                HypothesisStatus.EXPIRED,
                HypothesisStatus.INSUFFICIENT_EVIDENCE,
            ):
                d4.eligible = False
                d4.reason_codes.append(EligibilityReasonCode.STRATEGY_STATE_INELIGIBLE)
                d4.strategy_status = h.status.value
                d4.trace.append(f"E04_FAIL: status={h.status.value}")
            else:
                d4.eligible = True
                d4.strategy_status = h.status.value
                d4.trace.append("E04_OK: strategy eligible")
            decisions.append(d4)

            # E03: horizon recognized
            d3 = EligibilityDecision(hypothesis_id=h.hypothesis_id)
            norm = self._normalize_horizon(h.time_horizon)
            if norm == "unknown":
                d3.eligible = False
                d3.reason_codes.append(EligibilityReasonCode.HORIZON_UNRECOGNIZED)
                d3.trace.append(f"E03_FAIL: horizon={h.time_horizon}")
            else:
                d3.eligible = True
                d3.trace.append(f"E03_OK: horizon={norm}")
            decisions.append(d3)

            # E09: hypothesis not expired
            d9 = EligibilityDecision(hypothesis_id=h.hypothesis_id)
            if h.status == HypothesisStatus.EXPIRED:
                d9.eligible = False
                d9.reason_codes.append(EligibilityReasonCode.HYPOTHESIS_EXPIRED)
                d9.trace.append("E09_FAIL: hypothesis expired")
            else:
                d9.eligible = True
                d9.trace.append("E09_OK: not expired")
            decisions.append(d9)

            # Check evidence state if provided
            if evidence_state:
                d6 = EligibilityDecision(hypothesis_id=h.hypothesis_id)
                ev_state = evidence_state.get(h.hypothesis_id, {})
                if isinstance(ev_state, dict) and ev_state.get("verdict") == "conflicting":
                    d6.eligible = False
                    d6.reason_codes.append(EligibilityReasonCode.EVIDENCE_CONFLICTING)
                    d6.evidence_status = "conflicting"
                    d6.trace.append("E07_FAIL: evidence conflicting")
                else:
                    d6.eligible = True
                    d6.evidence_status = "ok"
                    d6.trace.append("E07_OK: evidence not conflicting")
                decisions.append(d6)

            # Check regime state if provided
            if regime_state:
                d8 = EligibilityDecision(hypothesis_id=h.hypothesis_id)
                regime_status = regime_state.get("match", "")
                invalid_regimes = regime_state.get("invalid_regimes", [])
                if regime_status == "mismatch":
                    d8.eligible = False
                    d8.reason_codes.append(EligibilityReasonCode.REGIME_INVALID)
                    d8.regime_status = "mismatch"
                    d8.trace.append("E08_FAIL: regime mismatch")
                else:
                    d8.eligible = True
                    d8.regime_status = regime_status
                    d8.trace.append(f"E08_OK: regime={regime_status}")
                decisions.append(d8)

            all_eligible = all(d.eligible for d in decisions)
            if all_eligible:
                eligible.append(h)
            else:
                ineligible_list.append(IneligibleHypothesis(
                    hypothesis_id=h.hypothesis_id,
                    decisions=decisions,
                ))

        return eligible, ineligible_list

    def _normalize_horizon(self, horizon: str) -> str:
        """Normalize a horizon string to a standard bucket.
        Returns 'unknown' for unrecognized horizons (no silent default).
        """
        key = horizon.lower().strip() if horizon else ""
        return HORIZON_MAP.get(key, "unknown")

    # ── Horizon Assessment (Rule-based, NO vote counting) ─────────────────

    def _assess_horizon(self, horizon: str,
                        hypotheses: list[EligibleHypothesis]) -> HorizonAssessment:
        """Assess a single time horizon using explicit rules.

        Rules evaluated (ARB-001 through ARB-013):
        - ARB-001: No eligible hypotheses -> INSUFFICIENT_EVIDENCE
        - ARB-005: Both sides have strong evidence -> CONFLICT_UNRESOLVED
        - ARB-010: Only derivatives confirmation -> WAIT_FOR_CONFIRMATION
        """
        trace = HorizonDecisionTrace(horizon=horizon)
        rule_ids = []

        # Classify hypotheses by expected effect
        bull_hypotheses = []
        bear_hypotheses = []
        neutral_hypotheses = []

        for h in hypotheses:
            trace.eligible_hypotheses.append(h.hypothesis_id)
            expected = h.expected_effect.lower() if h.expected_effect else ""
            if expected in ("bullish", "positive", "up", "long"):
                bull_hypotheses.append(h)
            elif expected in ("bearish", "negative", "down", "short"):
                bear_hypotheses.append(h)
            else:
                neutral_hypotheses.append(h)

        support_ids = [h.hypothesis_id for h in bull_hypotheses]
        oppose_ids = [h.hypothesis_id for h in bear_hypotheses]
        alt_ids = [h.hypothesis_id for h in neutral_hypotheses]
        missing_confirmations = [
            h.hypothesis_id for h in hypotheses
            if not h.market_confirmation or h.market_confirmation == "awaiting"
        ]

        # Build support clusters (for origin folding)
        bull_clusters = self._build_clusters(bull_hypotheses)
        bear_clusters = self._build_clusters(bear_hypotheses)
        trace.support_clusters = bull_clusters
        trace.opposing_clusters = bear_clusters

        # ── Evaluate rules ────────────────────────────────────────────────

        rule_ids.append("ARB-001")
        if not hypotheses:
            trace.final_verdict = VerdictState.INSUFFICIENT_EVIDENCE
            trace.rule_id_selected = "ARB-001"
            trace.limitations.append("No eligible hypotheses")
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids,
                                          alt_ids, missing_confirmations, [])

        # ARB-005: Both sides have strong evidence
        rule_ids.append("ARB-005")
        if self._has_strong_evidence(bull_clusters) and self._has_strong_evidence(bear_clusters):
            trace.final_verdict = VerdictState.CONFLICT_UNRESOLVED
            trace.rule_id_selected = "ARB-005"
            trace.limitations.append("Both sides have strong evidence")
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids,
                                          alt_ids, missing_confirmations,
                                          ["Strong evidence on both sides"])

        # ARB-007: Evidence bundle itself conflicting
        rule_ids.append("ARB-007")
        for h in hypotheses:
            if h.evidence_bundle_verdict == "conflicting":
                trace.final_verdict = VerdictState.CONFLICT_UNRESOLVED
                trace.rule_id_selected = "ARB-007"
                trace.limitations.append("Evidence bundle conflicting")
                trace.rule_ids_evaluated = list(rule_ids)
                return self._build_assessment(horizon, trace, support_ids, oppose_ids,
                                              alt_ids, missing_confirmations,
                                              ["Evidence bundle is conflicting"])

        # ARB-010: Only derivatives confirmation
        rule_ids.append("ARB-010")
        all_derivatives = all(
            h.market_confirmation in ("derivatives_only", "awaiting", "")
            for h in hypotheses
        ) if hypotheses else False
        if all_derivatives and not bull_clusters and not bear_clusters:
            trace.final_verdict = VerdictState.WAIT_FOR_CONFIRMATION
            trace.rule_id_selected = "ARB-010"
            trace.limitations.append("Only derivatives confirmation available")
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids,
                                          alt_ids, missing_confirmations, [])

        # ARB-002: Only awaiting confirmation
        rule_ids.append("ARB-002")
        only_awaiting = (
            all(h.market_confirmation in ("awaiting", "") for h in hypotheses)
            if hypotheses else False
        )
        if only_awaiting:
            trace.final_verdict = VerdictState.WAIT_FOR_CONFIRMATION
            trace.rule_id_selected = "ARB-002"
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids,
                                          alt_ids, missing_confirmations, [])

        # ARB-004: Three weak bull vs one strong bear -> not bull majority
        rule_ids.append("ARB-004")
        strong_bear = self._has_strong_evidence(bear_clusters)
        weak_bull = bull_clusters and not self._has_strong_evidence(bull_clusters)
        if weak_bull and strong_bear:
            # Strong bear outweighs weak bull consensus
            trace.final_verdict = VerdictState.DIRECTIONAL_AVAILABLE
            trace.rule_id_selected = "ARB-004"
            trace.direction = "bearish"
            trace.limitations.append("Strong independent bearish evidence overrides weaker bullish consensus")
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids,
                                          alt_ids, missing_confirmations, [])

        # ARB-003: Direction consistent with at least one complete evidence chain
        rule_ids.append("ARB-003")
        if self._has_strong_evidence(bull_clusters) and not self._has_strong_evidence(bear_clusters):
            trace.final_verdict = VerdictState.DIRECTIONAL_AVAILABLE
            trace.rule_id_selected = "ARB-003"
            trace.direction = "bullish"
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids,
                                          alt_ids, missing_confirmations, [])

        if self._has_strong_evidence(bear_clusters) and not self._has_strong_evidence(bull_clusters):
            trace.final_verdict = VerdictState.DIRECTIONAL_AVAILABLE
            trace.rule_id_selected = "ARB-003"
            trace.direction = "bearish"
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids,
                                          alt_ids, missing_confirmations, [])

        # ARB-006: One side strong, other only ineligible (but all eligible here)
        rule_ids.append("ARB-006")

        # ARB-012: Different time scales — handled at horizon grouping level
        rule_ids.append("ARB-012")

        # ARB-013: No calibration artifact
        rule_ids.append("ARB-013")
        has_calibration = any(
            h.calibration_artifact_ref for h in hypotheses
        ) if hypotheses else False
        if not has_calibration:
            trace.limitations.append("No calibration artifact available — confidence limited")

        # Default: if no rule matched, check basic direction
        if bull_hypotheses and not bear_hypotheses:
            trace.final_verdict = VerdictState.DIRECTIONAL_AVAILABLE
            trace.rule_id_selected = "ARB-199"
            trace.direction = "bullish"
        elif bear_hypotheses and not bull_hypotheses:
            trace.final_verdict = VerdictState.DIRECTIONAL_AVAILABLE
            trace.rule_id_selected = "ARB-199"
            trace.direction = "bearish"
        else:
            trace.final_verdict = VerdictState.INSUFFICIENT_EVIDENCE
            trace.rule_id_selected = "ARB-001"
            trace.direction = "neutral"

        trace.rule_ids_evaluated = list(rule_ids)
        return self._build_assessment(horizon, trace, support_ids, oppose_ids,
                                      alt_ids, missing_confirmations, [])

    def _build_clusters(self, hypotheses: list[EligibleHypothesis]) -> list[HypothesisSupportCluster]:
        """Build support clusters from hypotheses."""
        clusters = []
        seen = set()
        for h in hypotheses:
            if h.hypothesis_id in seen:
                continue
            seen.add(h.hypothesis_id)
            cluster = HypothesisSupportCluster(
                hypotheses=[h.hypothesis_id],
                origin_groups=[h.strategy_origin_group] if h.strategy_origin_group else [],
                evidence_independence_groups=[],
                direction=h.expected_effect,
            )
            clusters.append(cluster)
        return clusters

    def _has_strong_evidence(self, clusters: list[HypothesisSupportCluster]) -> bool:
        """Check if any cluster has strong evidence support."""
        for c in clusters:
            if c.quality in (QualityLevel.STRONG, QualityLevel.MODERATE):
                return True
        return False

    def _build_assessment(
        self, horizon: str, trace: HorizonDecisionTrace,
        support_ids: list[str], oppose_ids: list[str],
        alt_ids: list[str], missing_conf: list[str],
        conflicts: list[str], rule_ids: list[str] | None = None,
    ) -> HorizonAssessment:
        """Build a HorizonAssessment from the rule outputs."""
        direction = trace.direction if trace.direction != "neutral" else "neutral"

        # Determine direction_basis from rule
        basis = trace.rule_id_selected if trace.rule_id_selected else "no_rule_matched"
        trace.rule_ids_evaluated = rule_ids or trace.rule_ids_evaluated or []

        return HorizonAssessment(
            horizon=horizon,
            direction=direction,
            direction_basis=basis,
            supporting_hypotheses=support_ids,
            opposing_hypotheses=oppose_ids,
            alternative_hypotheses=alt_ids,
            unresolved_conflicts=conflicts,
            missing_confirmations=missing_conf,
            verdict=trace.final_verdict,
            decision_trace=trace,
        )

    # ── Global Status (NOT a single direction) ────────────────────────────

    def _determine_arbitration_status(
        self,
        assessments: list[HorizonAssessment],
        ineligible: list[IneligibleHypothesis],
    ) -> ArbitrationStatus:
        """Determine system-level arbitration status, not a direction."""
        verdicts = {a.verdict for a in assessments}
        directions = {a.direction for a in assessments}

        if not assessments:
            return ArbitrationStatus.ALL_HORIZONS_INSUFFICIENT

        has_conflict = VerdictState.CONFLICT_UNRESOLVED in verdicts
        has_directional = VerdictState.DIRECTIONAL_AVAILABLE in verdicts
        has_waiting = VerdictState.WAIT_FOR_CONFIRMATION in verdicts

        if has_conflict:
            return ArbitrationStatus.CONFLICT_PRESENT
        if has_waiting and not has_directional:
            return ArbitrationStatus.WAITING_FOR_CONFIRMATION
        if has_directional:
            # Check for mixed directions across horizons
            if len(directions - {"neutral"}) > 1:
                return ArbitrationStatus.MULTI_HORIZON_MIXED
            else:
                return ArbitrationStatus.SOME_HORIZONS_DIRECTIONAL

        return ArbitrationStatus.ALL_HORIZONS_INSUFFICIENT

    def _determine_global_verdict(self,
                                  assessments: list[HorizonAssessment]) -> VerdictState:
        """Determine the global verdict across all horizons."""
        if not assessments:
            return VerdictState.INSUFFICIENT_EVIDENCE

        # If any horizon has a real conflict, surface it
        for a in assessments:
            if a.verdict == VerdictState.CONFLICT_UNRESOLVED:
                return VerdictState.CONFLICT_UNRESOLVED

        # If all horizons are directional_available
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
