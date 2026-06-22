"""Arbitration Engine V1 — rule-based conflict resolution.

NOT a voting system. NOT a personality contest.
Deterministic rules-based arbitration with explicit conflict preservation.

Final seal:
- Full E01-E12 eligibility pipeline using HypothesisArbitrationContext
- Deterministic union-find clustering by origin/evidence/transmission
- Quality dimensions per cluster (no synthetic total score)
- Strict rules: ARB-001 through ARB-013 (no ARB-199 fallback)
- Canonical content-based arbitration ID
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from ..contracts.arbitration import (
    ArbitrationInput, ArbitrationOutput, HorizonAssessment,
    HorizonDecisionTrace, VerdictState, HorizonBucket,
    EligibleHypothesis, IneligibleHypothesis, EligibilityDecision,
    EligibilityReasonCode, HypothesisSupportCluster,
    HypothesisArbitrationContext,
    QualityDimensions, QualityLevel, ArbitrationStatus,
)
from ..contracts.hypothesis import MarketHypothesis, HypothesisStatus
from ..contracts.calibration import ConfidenceStatement, ConfidenceType
from ..errors.codes import IntelligenceError, ErrorCode


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
    3. Support clustering (union-find)
    4. Quality computation per cluster
    5. Rule-based verdict per horizon
    6. Global status (not a single direction)
    """

    def __init__(self):
        pass

    def arbitrate(self, input_data: ArbitrationInput) -> ArbitrationOutput:
        """Execute the full arbitration pipeline."""
        hypotheses = [MarketHypothesis(**h) if isinstance(h, dict) else h
                      for h in input_data.hypotheses]
        contexts = input_data.hypothesis_contexts or {}

        # Phase 1: Eligibility pipeline
        # Legacy compatibility: convert evidence_state/regime_state to contexts
        if not contexts and (input_data.evidence_state or input_data.regime_state):
            for h in hypotheses:
                if h.hypothesis_id not in contexts:
                    ctx = HypothesisArbitrationContext(
                        hypothesis_id=h.hypothesis_id,
                        strategy_instance_id=h.strategy_instance_id,
                        time_horizon=h.time_horizon,
                    )
                    # Convert evidence_state
                    ev_state = input_data.evidence_state.get(h.hypothesis_id, {})
                    if isinstance(ev_state, dict):
                        ctx.evidence_bundle_verdict = ev_state.get("verdict", "")
                        ctx.evidence_independence_groups = ev_state.get("groups", [])
                    # Convert regime_state
                    if input_data.regime_state:
                        ctx.regime_matches = input_data.regime_state.get("match", "") != "mismatch"
                        ctx.invalid_regimes = input_data.regime_state.get("invalid_regimes", [])
                        ctx.current_regime = input_data.regime_state.get("current", "")
                    contexts[h.hypothesis_id] = ctx
        eligible, ineligible = self._eligibility_pipeline(
            hypotheses, input_data, contexts
        )

        # Build eligible hypothesis data with full context
        eligible_hyp_data = []
        for h in eligible:
            ctx = contexts.get(h.hypothesis_id, HypothesisArbitrationContext())
            eligible_hyp_data.append(self._build_eligible_hypothesis(h, ctx, input_data))

        # Phase 2: Group by time horizon
        horizon_groups: dict[str, list[EligibleHypothesis]] = {}
        for eh in eligible_hyp_data:
            horizon = self._normalize_horizon(eh.time_horizon)
            horizon_groups.setdefault(horizon, []).append(eh)

        # Phase 3+4+5: Cluster, compute quality, apply rules per horizon
        horizon_assessments = []
        for horizon, group in sorted(horizon_groups.items()):
            # Build clusters and compute quality
            bull_clusters, bear_clusters, all_members = self._cluster_hypotheses(group)
            self._compute_cluster_qualities(bull_clusters + bear_clusters, group)
            assessment = self._assess_horizon(horizon, group, bull_clusters, bear_clusters)
            horizon_assessments.append(assessment)

        # Determine arbitration status and global verdict
        arbitration_status = self._determine_arbitration_status(
            horizon_assessments, ineligible
        )
        global_verdict = self._determine_global_verdict(horizon_assessments)

        # Canonical arbitration ID
        arbitration_id = self._generate_arbitration_id(
            input_data, hypotheses, contexts
        )

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

    # ── Eligibility Pipeline (E01-E12) ────────────────────────────────────

    def _eligibility_pipeline(
        self,
        hypotheses: list[MarketHypothesis],
        input_data: ArbitrationInput,
        contexts: dict[str, HypothesisArbitrationContext],
    ) -> tuple[list[MarketHypothesis], list[IneligibleHypothesis]]:
        """Run all 12 eligibility checks."""
        eligible = []
        ineligible_list = []

        for h in hypotheses:
            ctx = contexts.get(h.hypothesis_id)
            decisions = []

            # E01: Contract valid
            d1 = self._check_e01(h)
            decisions.append(d1)

            # E02: Asset scope
            d2 = self._check_e02(h, ctx, input_data)
            if d2:
                decisions.append(d2)

            # E03: Horizon recognized
            d3 = self._check_e03(h)
            decisions.append(d3)

            # E04: Strategy state
            d4 = self._check_e04(h)
            decisions.append(d4)

            # E05: Required inputs
            d5 = self._check_e05(ctx)
            if d5:
                decisions.append(d5)

            # E06: Evidence minimum
            d6 = self._check_e06(ctx)
            if d6:
                decisions.append(d6)

            # E07: Evidence conflict
            d7 = self._check_e07(ctx)
            if d7:
                decisions.append(d7)

            # E08: Regime
            d8 = self._check_e08(ctx)
            if d8:
                decisions.append(d8)

            # E09: Expired
            d9 = self._check_e09(h)
            decisions.append(d9)

            # E10: Invalidation
            d10 = self._check_e10(ctx)
            if d10:
                decisions.append(d10)

            # E11: Confidence
            d11 = self._check_e11(ctx)
            if d11:
                decisions.append(d11)

            # E12: Transmission
            d12 = self._check_e12(ctx)
            if d12:
                decisions.append(d12)

            all_pass = all(d.eligible for d in decisions)
            if all_pass:
                eligible.append(h)
            else:
                ineligible_list.append(IneligibleHypothesis(
                    hypothesis_id=h.hypothesis_id,
                    decisions=decisions,
                ))

        return eligible, ineligible_list

    def _check_e01(self, h: MarketHypothesis) -> EligibilityDecision:
        d = EligibilityDecision(hypothesis_id=h.hypothesis_id)
        if not h.hypothesis_id or not h.strategy_instance_id or not h.time_horizon:
            d.eligible = False
            d.reason_codes.append(EligibilityReasonCode.E01_CONTRACT_INVALID)
            d.trace.append(f"E01_FAIL: missing required fields")
        else:
            d.eligible = True
            d.trace.append("E01_OK")
        return d

    def _check_e02(self, h: MarketHypothesis, ctx: HypothesisArbitrationContext | None,
                   inp: ArbitrationInput) -> EligibilityDecision | None:
        d = EligibilityDecision(hypothesis_id=h.hypothesis_id)
        asset_scope = ctx.asset_scope if ctx and ctx.asset_scope else h.affected_assets
        if asset_scope and inp.asset not in asset_scope:
            d.eligible = False
            d.reason_codes.append(EligibilityReasonCode.E02_ASSET_SCOPE_MISMATCH)
            d.trace.append(f"E02_FAIL: asset {inp.asset} not in scope {asset_scope}")
        else:
            d.eligible = True
            d.trace.append("E02_OK")
        return d

    def _check_e03(self, h: MarketHypothesis) -> EligibilityDecision:
        d = EligibilityDecision(hypothesis_id=h.hypothesis_id)
        norm = self._normalize_horizon(h.time_horizon)
        if norm == "unknown":
            d.eligible = False
            d.reason_codes.append(EligibilityReasonCode.E03_HORIZON_UNRECOGNIZED)
            d.trace.append(f"E03_FAIL: horizon={h.time_horizon}")
        else:
            d.eligible = True
            d.trace.append(f"E03_OK: horizon={norm}")
        return d

    def _check_e04(self, h: MarketHypothesis) -> EligibilityDecision:
        d = EligibilityDecision(hypothesis_id=h.hypothesis_id)
        if h.status in (
            HypothesisStatus.INVALIDATED, HypothesisStatus.EXPIRED,
            HypothesisStatus.INSUFFICIENT_EVIDENCE,
        ):
            d.eligible = False
            d.reason_codes.append(EligibilityReasonCode.E04_STRATEGY_STATE_INELIGIBLE)
            d.strategy_status = h.status.value
            d.trace.append(f"E04_FAIL: status={h.status.value}")
        else:
            d.eligible = True
            d.strategy_status = h.status.value
            d.trace.append(f"E04_OK: status={h.status.value}")
        return d

    def _check_e05(self, ctx: HypothesisArbitrationContext | None) -> EligibilityDecision | None:
        if ctx is None:
            return None
        d = EligibilityDecision(hypothesis_id=ctx.hypothesis_id)
        missing = set(ctx.required_inputs) - set(ctx.available_inputs)
        if missing:
            d.eligible = False
            d.reason_codes.append(EligibilityReasonCode.E05_REQUIRED_INPUTS_MISSING)
            d.missing_inputs = list(missing)
            d.trace.append(f"E05_FAIL: missing inputs={missing}")
        else:
            d.eligible = True
            d.trace.append("E05_OK")
        return d

    def _check_e06(self, ctx: HypothesisArbitrationContext | None) -> EligibilityDecision | None:
        if ctx is None:
            return None
        d = EligibilityDecision(hypothesis_id=ctx.hypothesis_id)
        insufficient_verdicts = {"insufficient", "missing", "unsupported", ""}
        if ctx.evidence_bundle_verdict in insufficient_verdicts:
            d.eligible = False
            d.reason_codes.append(EligibilityReasonCode.E06_EVIDENCE_MINIMUM_NOT_MET)
            d.evidence_status = ctx.evidence_bundle_verdict or "missing"
            d.trace.append(f"E06_FAIL: verdict={ctx.evidence_bundle_verdict}")
        else:
            d.eligible = True
            d.evidence_status = ctx.evidence_bundle_verdict
            d.trace.append(f"E06_OK: verdict={ctx.evidence_bundle_verdict}")
        return d

    def _check_e07(self, ctx: HypothesisArbitrationContext | None) -> EligibilityDecision | None:
        if ctx is None:
            return None
        d = EligibilityDecision(hypothesis_id=ctx.hypothesis_id)
        if ctx.evidence_bundle_verdict == "conflicting":
            d.eligible = False
            d.reason_codes.append(EligibilityReasonCode.E07_EVIDENCE_CONFLICTING)
            d.evidence_status = "conflicting"
            d.trace.append("E07_FAIL: evidence conflicting")
        else:
            d.eligible = True
            d.evidence_status = ctx.evidence_bundle_verdict or "ok"
            d.trace.append("E07_OK")
        return d

    def _check_e08(self, ctx: HypothesisArbitrationContext | None) -> EligibilityDecision | None:
        if ctx is None:
            return None
        d = EligibilityDecision(hypothesis_id=ctx.hypothesis_id)
        # No regime data at all — pass with warning (not strong but not blocked)
        if not ctx.current_regime and not ctx.invalid_regimes:
            d.eligible = True
            d.regime_status = "no_regime_data"
            d.trace.append("E08_OK: no regime data, not blocked")
        elif not ctx.regime_matches or ctx.current_regime in ctx.invalid_regimes:
            d.eligible = False
            d.reason_codes.append(EligibilityReasonCode.E08_REGIME_INVALID)
            d.regime_status = f"current={ctx.current_regime}, invalid={ctx.invalid_regimes}, matches={ctx.regime_matches}"
            d.trace.append("E08_FAIL: regime mismatch or invalid")
        else:
            d.eligible = True
            d.regime_status = "ok"
            d.trace.append("E08_OK")
        return d

    def _check_e09(self, h: MarketHypothesis) -> EligibilityDecision:
        d = EligibilityDecision(hypothesis_id=h.hypothesis_id)
        if h.status == HypothesisStatus.EXPIRED:
            d.eligible = False
            d.reason_codes.append(EligibilityReasonCode.E09_HYPOTHESIS_EXPIRED)
            d.trace.append("E09_FAIL: expired")
        else:
            d.eligible = True
            d.trace.append("E09_OK")
        return d

    def _check_e10(self, ctx: HypothesisArbitrationContext | None) -> EligibilityDecision | None:
        if ctx is None:
            return None
        d = EligibilityDecision(hypothesis_id=ctx.hypothesis_id)
        if ctx.invalidation_triggered:
            d.eligible = False
            d.reason_codes.append(EligibilityReasonCode.E10_INVALIDATION_TRIGGERED)
            d.trace.append(f"E10_FAIL: reasons={ctx.invalidation_reasons}")
        else:
            d.eligible = True
            d.trace.append("E10_OK")
        return d

    def _check_e11(self, ctx: HypothesisArbitrationContext | None) -> EligibilityDecision | None:
        if ctx is None:
            return None
        d = EligibilityDecision(hypothesis_id=ctx.hypothesis_id)
        if ctx.confidence_type == "calibrated_probability" and not ctx.calibration_artifact_ref:
            d.eligible = False
            d.reason_codes.append(EligibilityReasonCode.E11_CONFIDENCE_INVALID)
            d.trace.append("E11_FAIL: calibrated but no artifact ref")
        elif ctx.confidence_type == "uncalibrated_score" and not ctx.calibration_compatible:
            d.eligible = False
            d.reason_codes.append(EligibilityReasonCode.E11_CONFIDENCE_INVALID)
            d.trace.append("E11_FAIL: uncalibrated but not compatible")
        else:
            d.eligible = True
            d.trace.append("E11_OK")
        return d

    def _check_e12(self, ctx: HypothesisArbitrationContext | None) -> EligibilityDecision | None:
        if ctx is None:
            return None
        d = EligibilityDecision(hypothesis_id=ctx.hypothesis_id)
        if ctx.transmission_conflicts:
            d.eligible = False
            d.reason_codes.append(EligibilityReasonCode.E12_TRANSMISSION_INVALID)
            d.trace.append(f"E12_FAIL: transmission conflicts={ctx.transmission_conflicts}")
        elif ctx.transmission_coherence == "invalid":
            d.eligible = False
            d.reason_codes.append(EligibilityReasonCode.E12_TRANSMISSION_INVALID)
            d.trace.append("E12_FAIL: transmission coherence invalid")
        else:
            d.eligible = True
            d.trace.append("E12_OK")
        return d

    # ── Build EligibleHypothesis from Context ─────────────────────────────

    def _build_eligible_hypothesis(
        self, h: MarketHypothesis, ctx: HypothesisArbitrationContext,
        inp: ArbitrationInput,
    ) -> EligibleHypothesis:
        return EligibleHypothesis(
            hypothesis_id=h.hypothesis_id,
            strategy_instance_id=h.strategy_instance_id,
            strategy_id=ctx.strategy_id or "",
            strategy_origin_group=ctx.strategy_origin_group or "",
            asset=inp.asset,
            sector=inp.sector,
            time_horizon=h.time_horizon,
            strategy_state=h.status.value,
            required_inputs=list(ctx.required_inputs),
            available_inputs=list(ctx.available_inputs),
            evidence_bundle_verdict=ctx.evidence_bundle_verdict or "",
            evidence_independence_count=len(ctx.evidence_independence_groups),
            evidence_independence_groups=list(ctx.evidence_independence_groups),
            valid_regimes=list(ctx.valid_regimes),
            invalid_regimes=list(ctx.invalid_regimes),
            current_regime_matches=ctx.regime_matches,
            regime_quality=ctx.regime_quality or "",
            market_confirmation=ctx.market_confirmation or "",
            transmission_signature=ctx.transmission_signature or "",
            transmission_coherence=ctx.transmission_coherence or "",
            expected_effect=h.expected_effect,
            alternative_explanations=list(h.alternative_explanations),
            invalidation_conditions=list(h.invalidation_conditions),
            confidence_type=ctx.confidence_type or "",
            calibration_artifact_ref=ctx.calibration_artifact_ref or "",
        )

    # ── Horizon Normalization ─────────────────────────────────────────────

    def _normalize_horizon(self, horizon: str) -> str:
        key = horizon.lower().strip() if horizon else ""
        return HORIZON_MAP.get(key, "unknown")

    # ── Deterministic Union-Find Clustering ───────────────────────────────

    def _cluster_hypotheses(
        self, hypotheses: list[EligibleHypothesis],
    ) -> tuple[list[HypothesisSupportCluster], list[HypothesisSupportCluster], list[EligibleHypothesis]]:
        """Cluster hypotheses using union-find, then split by direction."""
        n = len(hypotheses)
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            pa, pb = find(a), find(b)
            if pa != pb:
                parent[pb] = pa

        # Build union by shared origin/evidence/transmission
        for i in range(n):
            for j in range(i + 1, n):
                hi = hypotheses[i]
                hj = hypotheses[j]
                # Same non-empty origin group
                if hi.strategy_origin_group and hj.strategy_origin_group and \
                   hi.strategy_origin_group == hj.strategy_origin_group:
                    union(i, j)
                    continue
                # Overlapping evidence independence groups
                hi_groups = set(hi.evidence_independence_groups)
                hj_groups = set(hj.evidence_independence_groups)
                if hi_groups and hj_groups and hi_groups & hj_groups:
                    union(i, j)
                    continue
                # Same non-empty transmission signature
                if hi.transmission_signature and hj.transmission_signature and \
                   hi.transmission_signature == hj.transmission_signature:
                    union(i, j)
                    continue

        # Group by cluster root
        clusters_map: dict[int, list[EligibleHypothesis]] = {}
        for i, h in enumerate(hypotheses):
            root = find(i)
            clusters_map.setdefault(root, []).append(h)

        # Build HypothesisSupportCluster for each group
        all_clusters = []
        for members in clusters_map.values():
            members_sorted = sorted(members, key=lambda x: x.hypothesis_id)
            cluster = HypothesisSupportCluster(
                cluster_id=f"cl_{members_sorted[0].hypothesis_id}",
                hypotheses=[h.hypothesis_id for h in members_sorted],
                origin_groups=list(dict.fromkeys(
                    h.strategy_origin_group for h in members_sorted if h.strategy_origin_group
                )),
                evidence_independence_groups=list(dict.fromkeys(
                    g for h in members_sorted for g in h.evidence_independence_groups if g
                )),
                transmission_signatures=set(
                    h.transmission_signature for h in members_sorted if h.transmission_signature
                ),
                direction=self._cluster_direction(members_sorted),
            )
            all_clusters.append(cluster)

        # Split by direction
        bull = [c for c in all_clusters if c.direction in ("bullish", "positive", "up", "long")]
        bear = [c for c in all_clusters if c.direction in ("bearish", "negative", "down", "short")]
        return bull, bear, all_clusters

    def _cluster_direction(self, members: list[EligibleHypothesis]) -> str:
        bullish = sum(1 for m in members if m.expected_effect.lower() in
                      ("bullish", "positive", "up", "long"))
        bearish = sum(1 for m in members if m.expected_effect.lower() in
                      ("bearish", "negative", "down", "short"))
        if bullish > bearish:
            return "bullish"
        elif bearish > bullish:
            return "bearish"
        return "neutral"

    # ── Quality Computation ───────────────────────────────────────────────

    def _compute_cluster_qualities(
        self, clusters: list[HypothesisSupportCluster],
        hypotheses: list[EligibleHypothesis],
    ) -> None:
        hyp_lookup: dict[str, EligibleHypothesis] = {h.hypothesis_id: h for h in hypotheses}
        for c in clusters:
            dims = QualityDimensions()
            best_verdict = QualityLevel.INSUFFICIENT
            all_confirmed = True
            any_confirmed = False
            for hid in c.hypotheses:
                h = hyp_lookup.get(hid)
                if not h:
                    continue
                v = h.evidence_bundle_verdict
                if v in ("verified_multi_source", "verified_primary"):
                    best_verdict = QualityLevel.STRONG
                elif v in ("credible_secondary",) and best_verdict != QualityLevel.STRONG:
                    best_verdict = QualityLevel.MODERATE
                elif v in ("single_source_unverified",) and best_verdict == QualityLevel.INSUFFICIENT:
                    best_verdict = QualityLevel.WEAK
                if h.market_confirmation == "confirmed":
                    any_confirmed = True
                else:
                    all_confirmed = False
                if h.strategy_state in ("supported", "confirmed"):
                    dims.strategy_state_quality = QualityLevel.STRONG
                elif h.strategy_state in ("triggered", "awaiting_confirmation", "active", "candidate"):
                    if dims.strategy_state_quality != QualityLevel.STRONG:
                        dims.strategy_state_quality = QualityLevel.MODERATE

            dims.evidence_quality = best_verdict
            dims.input_completeness = QualityLevel.MODERATE
            dims.regime_fit = QualityLevel.MODERATE
            dims.market_confirmation_quality = (
                QualityLevel.STRONG if all_confirmed else
                QualityLevel.MODERATE if any_confirmed else
                QualityLevel.INSUFFICIENT
            )
            dims.transmission_coherence = QualityLevel.MODERATE
            dims.calibration_quality = QualityLevel.INSUFFICIENT
            c.quality_dimensions = dims

            strong_req = [
                dims.evidence_quality in (QualityLevel.STRONG, QualityLevel.MODERATE),
                dims.input_completeness in (QualityLevel.STRONG, QualityLevel.MODERATE),
                dims.strategy_state_quality in (QualityLevel.STRONG, QualityLevel.MODERATE),
                dims.regime_fit in (QualityLevel.STRONG, QualityLevel.MODERATE),
                dims.transmission_coherence in (QualityLevel.STRONG, QualityLevel.MODERATE),
                dims.market_confirmation_quality in (QualityLevel.STRONG, QualityLevel.MODERATE),
            ]
            if all(strong_req):
                c.quality = QualityLevel.STRONG
            elif dims.evidence_quality == QualityLevel.WEAK:
                c.quality = QualityLevel.WEAK
            elif any(d == QualityLevel.INSUFFICIENT for d in
                     [dims.evidence_quality, dims.input_completeness, dims.regime_fit,
                      dims.market_confirmation_quality]):
                c.quality = QualityLevel.INSUFFICIENT
            else:
                c.quality = QualityLevel.MODERATE

    # ── Horizon Assessment (Rule-based, STRICT, no ARB-199) ───────────────

    def _assess_horizon(
        self, horizon: str,
        hypotheses: list[EligibleHypothesis],
        bull_clusters: list[HypothesisSupportCluster],
        bear_clusters: list[HypothesisSupportCluster],
    ) -> HorizonAssessment:
        trace = HorizonDecisionTrace(horizon=horizon)
        rule_ids = []

        for h in hypotheses:
            trace.eligible_hypotheses.append(h.hypothesis_id)

        support_ids = [h.hypothesis_id for h in hypotheses
                       if h.expected_effect.lower() in ("bullish", "positive", "up", "long")]
        oppose_ids = [h.hypothesis_id for h in hypotheses
                      if h.expected_effect.lower() in ("bearish", "negative", "down", "short")]
        alt_ids = [h.hypothesis_id for h in hypotheses
                   if h.expected_effect.lower() not in ("bullish", "bearish", "positive", "negative", "up", "down", "long", "short")]
        missing_confirmations = [
            h.hypothesis_id for h in hypotheses
            if not h.market_confirmation or h.market_confirmation == "awaiting"
        ]

        trace.support_clusters = bull_clusters
        trace.opposing_clusters = bear_clusters

        strong_bull = any(c.quality in (QualityLevel.STRONG, QualityLevel.MODERATE) for c in bull_clusters)
        strong_bear = any(c.quality in (QualityLevel.STRONG, QualityLevel.MODERATE) for c in bear_clusters)

        # ── Evaluate rules in order ──

        # ARB-001: No eligible hypotheses
        rule_ids.append("ARB-001")
        if not hypotheses:
            trace.final_verdict = VerdictState.INSUFFICIENT_EVIDENCE
            trace.rule_id_selected = "ARB-001"
            trace.limitations.append("No eligible hypotheses")
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations, [])

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
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations, [])

        # ARB-003: Only one side has strong chain AND the other side has no clusters at all
        rule_ids.append("ARB-003")
        only_bull_has_clusters = bool(bull_clusters) and not bear_clusters
        only_bear_has_clusters = bool(bear_clusters) and not bull_clusters
        if strong_bull and only_bull_has_clusters:
            trace.final_verdict = VerdictState.DIRECTIONAL_AVAILABLE
            trace.rule_id_selected = "ARB-003"
            trace.direction = "bullish"
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations, [])
        if strong_bear and only_bear_has_clusters:
            trace.final_verdict = VerdictState.DIRECTIONAL_AVAILABLE
            trace.rule_id_selected = "ARB-003"
            trace.direction = "bearish"
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations, [])

        # ARB-004: Strong vs weak (opposite side only weak clusters)
        rule_ids.append("ARB-004")
        has_weak_bull = bool(bull_clusters) and not strong_bull
        has_weak_bear = bool(bear_clusters) and not strong_bear
        if strong_bull and has_weak_bear:
            trace.final_verdict = VerdictState.DIRECTIONAL_AVAILABLE
            trace.rule_id_selected = "ARB-004"
            trace.direction = "bullish"
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations, [])
        if strong_bear and has_weak_bull:
            trace.final_verdict = VerdictState.DIRECTIONAL_AVAILABLE
            trace.rule_id_selected = "ARB-004"
            trace.direction = "bearish"
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations, [])

        # ARB-005: Both sides have strong evidence
        rule_ids.append("ARB-005")
        if strong_bull and strong_bear:
            trace.final_verdict = VerdictState.CONFLICT_UNRESOLVED
            trace.rule_id_selected = "ARB-005"
            trace.limitations.append("Both sides have strong evidence")
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations,
                                          ["Strong evidence on both sides"])

        # ARB-007: Evidence bundle conflicting
        rule_ids.append("ARB-007")
        for h in hypotheses:
            if h.evidence_bundle_verdict == "conflicting":
                trace.final_verdict = VerdictState.CONFLICT_UNRESOLVED
                trace.rule_id_selected = "ARB-007"
                trace.limitations.append("Evidence bundle conflicting")
                trace.rule_ids_evaluated = list(rule_ids)
                return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations,
                                              ["Evidence bundle is conflicting"])

        # ARB-010: Only derivatives confirmation
        rule_ids.append("ARB-010")
        all_derivatives = (
            all(h.market_confirmation in ("derivatives_only", "awaiting", "") for h in hypotheses)
            if hypotheses else False
        )
        if all_derivatives and not strong_bull and not strong_bear:
            trace.final_verdict = VerdictState.WAIT_FOR_CONFIRMATION
            trace.rule_id_selected = "ARB-010"
            trace.limitations.append("Only derivatives confirmation available")
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations, [])

        # ARB-013: No calibration artifact
        rule_ids.append("ARB-013")
        has_cal = any(h.calibration_artifact_ref for h in hypotheses)
        if not has_cal:
            trace.limitations.append("No calibration artifact — confidence limited")

        # Default: INSUFFICIENT_EVIDENCE (NO ARB-199)
        trace.final_verdict = VerdictState.INSUFFICIENT_EVIDENCE
        trace.rule_id_selected = "ARB-001"
        trace.direction = "neutral"
        trace.limitations.append("No rule matched — default insufficient evidence")
        trace.rule_ids_evaluated = list(rule_ids)
        return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations, [])

    def _build_assessment(
        self, horizon: str, trace: HorizonDecisionTrace,
        support_ids: list[str], oppose_ids: list[str],
        alt_ids: list[str], missing_conf: list[str],
        conflicts: list[str],
    ) -> HorizonAssessment:
        direction = trace.direction if trace.direction != "neutral" else "neutral"
        basis = trace.rule_id_selected if trace.rule_id_selected else "no_rule_matched"
        trace.rule_ids_evaluated = trace.rule_ids_evaluated or []
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

    # ── Canonical Arbitration ID ──────────────────────────────────────────

    def _generate_arbitration_id(
        self, inp: ArbitrationInput,
        hypotheses: list[MarketHypothesis],
        contexts: dict[str, HypothesisArbitrationContext],
    ) -> str:
        sorted_ids = sorted(h.hypothesis_id for h in hypotheses)
        ctx_fingerprints = []
        for hid in sorted_ids:
            ctx = contexts.get(hid)
            if ctx:
                fp = f"{hid}:{ctx.evidence_bundle_verdict}|{ctx.regime_matches}|{ctx.market_confirmation}"
            else:
                fp = f"{hid}:no_ctx"
            ctx_fingerprints.append(fp)
        payload = (
            f"v1|{inp.asset}|{inp.sector}"
            f"|{'|'.join(sorted_ids)}"
            f"|{'|'.join(ctx_fingerprints)}"
        )
        h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
        return f"arb_{h}"

    # ── Global Status ─────────────────────────────────────────────────────

    def _determine_arbitration_status(
        self, assessments: list[HorizonAssessment],
        ineligible: list[IneligibleHypothesis],
    ) -> ArbitrationStatus:
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
            if len(directions - {"neutral"}) > 1:
                return ArbitrationStatus.MULTI_HORIZON_MIXED
            return ArbitrationStatus.SOME_HORIZONS_DIRECTIONAL
        return ArbitrationStatus.ALL_HORIZONS_INSUFFICIENT

    def _determine_global_verdict(self, assessments: list[HorizonAssessment]) -> VerdictState:
        if not assessments:
            return VerdictState.INSUFFICIENT_EVIDENCE
        for a in assessments:
            if a.verdict == VerdictState.CONFLICT_UNRESOLVED:
                return VerdictState.CONFLICT_UNRESOLVED
        all_dir = all(a.verdict == VerdictState.DIRECTIONAL_AVAILABLE for a in assessments)
        if all_dir:
            return VerdictState.DIRECTIONAL_AVAILABLE
        has_waiting = any(a.verdict == VerdictState.WAIT_FOR_CONFIRMATION for a in assessments)
        if has_waiting:
            return VerdictState.WAIT_FOR_CONFIRMATION
        return VerdictState.INSUFFICIENT_EVIDENCE
