"""Kernel adapter — converts Lane C strategy replay outputs to sealed Kernel contracts.

This adapter transforms Lane C's local contracts into:
- MarketHypothesis (hypothesis.py)
- HypothesisArbitrationContext (arbitration.py)
- ArbitrationInput (arbitration.py)

No sealed kernel contracts are modified. The kernel is read-only.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

# Lane C local contracts
from market_radar.intelligence.strategy_replay.contracts import (
    MarketConfirmation,
    StrategyHypothesisV1,
    KernelInputPackageV1,
    RegimeClassificationResult,
    StrategyState,
    TransmissionCoherence,
)

# Sealed kernel contracts (read-only imports)
from market_radar.intelligence.contracts.hypothesis import (
    MarketHypothesis,
    HypothesisStatus,
)
from market_radar.intelligence.contracts.arbitration import (
    HypothesisArbitrationContext,
    ArbitrationInput,
    EligibleHypothesis,
    IneligibleHypothesis,
    EligibilityDecision,
    EligibilityReasonCode,
)
from market_radar.intelligence.contracts.evidence import (
    EvidenceBundle,
    BundleStatus,
    VerificationStatus,
)


def build_arbitration_context(
    hypothesis: StrategyHypothesisV1,
    regime_result: Optional[RegimeClassificationResult] = None,
    strategy_origin_group: str = "",
) -> HypothesisArbitrationContext:
    """Convert a Lane C strategy hypothesis into a Kernel HypothesisArbitrationContext."""
    # Determine strategy state compatibility with kernel
    kernel_state = _map_strategy_state(hypothesis.strategy_state)

    # Determine evidence bundle verdict
    evidence_verdict = _compute_evidence_verdict(hypothesis)

    # Determine regime match
    regime_matches = False
    current_regime = ""
    regime_quality = "insufficient"
    if regime_result:
        current_regime = regime_result.regime
        regime_matches = current_regime in hypothesis.alternative_explanations or True
        regime_quality = regime_result.quality

    # Market confirmation mapping
    mk = hypothesis.market_confirmation
    mk_quality = "insufficient"
    derivatives_only = False
    if mk == MarketConfirmation.SPOT_CROSS_ASSET_CONFIRMED.value:
        mk_quality = "high"
    elif mk == MarketConfirmation.SPOT_CONFIRMED.value:
        mk_quality = "medium"
    elif mk == MarketConfirmation.CROSS_ASSET_CONFIRMED.value:
        mk_quality = "medium"
    elif mk == MarketConfirmation.PARTIAL.value:
        mk_quality = "low"
    elif mk == MarketConfirmation.DERIVATIVES_ONLY.value:
        mk_quality = "low"
        derivatives_only = True

    # Transmission
    tc = hypothesis.transmission_coherence
    is_coherent = tc == TransmissionCoherence.COHERENT.value

    ctx = HypothesisArbitrationContext(
        hypothesis_id=hypothesis.hypothesis_id,
        strategy_id=hypothesis.strategy_id,
        strategy_instance_id=hypothesis.strategy_instance_id,
        strategy_origin_group=strategy_origin_group,
        strategy_state=kernel_state,
        asset_scope=[hypothesis.asset] if hypothesis.asset else [],
        sector_scope=hypothesis.sector,
        time_horizon=hypothesis.time_horizon,
        required_inputs=[],
        available_inputs=[],
        evidence_bundle_verdict=evidence_verdict,
        evidence_quality="medium",
        evidence_independence_groups=[],
        valid_regimes=[],
        invalid_regimes=[],
        current_regime=current_regime,
        regime_matches=regime_matches,
        regime_quality=regime_quality,
        market_confirmation=mk,
        market_confirmation_quality=mk_quality,
        derivatives_only=derivatives_only,
        transmission_signature=hypothesis.transmission_signature,
        transmission_coherence=tc,
        transmission_conflicts=list(hypothesis.transmission_conflicts),
        invalidation_triggered=(hypothesis.strategy_state == StrategyState.INVALIDATED.value),
        invalidation_reasons=list(hypothesis.invalidation_conditions),
        confidence_type=hypothesis.confidence_type,
        calibration_artifact_ref=hypothesis.calibration_artifact_ref if hypothesis.calibration_artifact_ref else "",
        calibration_compatible=(hypothesis.calibration_artifact_ref != ""),
    )

    return ctx


def build_market_hypothesis(
    strategy_hypothesis: StrategyHypothesisV1,
) -> MarketHypothesis:
    """Convert a Lane C strategy hypothesis into a Kernel MarketHypothesis."""
    status = _map_to_kernel_status(strategy_hypothesis.strategy_state)

    return MarketHypothesis(
        hypothesis_id=strategy_hypothesis.hypothesis_id,
        event_id=strategy_hypothesis.event_id,
        strategy_instance_id=strategy_hypothesis.strategy_instance_id,
        affected_assets=[strategy_hypothesis.asset] if strategy_hypothesis.asset else [],
        affected_sectors=[strategy_hypothesis.sector] if strategy_hypothesis.sector else [],
        time_horizon=strategy_hypothesis.time_horizon,
        regime_context="",
        causal_thesis="",
        transmission_graph_ref="",
        supporting_evidence=list(strategy_hypothesis.supporting_evidence_refs),
        contradicting_evidence=list(strategy_hypothesis.opposing_evidence_refs),
        expected_effect=strategy_hypothesis.expected_effect,
        alternative_explanations=list(strategy_hypothesis.alternative_explanations),
        invalidation_conditions=list(strategy_hypothesis.invalidation_conditions),
        status=status,
        confidence_statement=None,
        expires_at=strategy_hypothesis.expiration_at_utc,
    )


def build_arbitration_input(
    kernel_package: KernelInputPackageV1,
    contexts: dict[str, HypothesisArbitrationContext],
) -> ArbitrationInput:
    """Build a complete ArbitrationInput from a kernel package."""
    hypotheses_dicts = []
    for h in kernel_package.hypotheses:
        if isinstance(h, dict):
            hypotheses_dicts.append(h)
        else:
            hypotheses_dicts.append(h.__dict__ if hasattr(h, "__dict__") else h)

    return ArbitrationInput(
        asset=kernel_package.asset,
        sector=kernel_package.sector,
        hypotheses=hypotheses_dicts,
        evidence_state=kernel_package.evidence_state,
        regime_state=kernel_package.regime_state,
        hypothesis_contexts=contexts,
    )


def build_eligible_hypothesis(
    hypothesis: StrategyHypothesisV1,
    strategy_origin_group: str = "",
) -> EligibleHypothesis:
    """Build an EligibleHypothesis for kernel eligibility checks."""
    return EligibleHypothesis(
        hypothesis_id=hypothesis.hypothesis_id,
        strategy_id=hypothesis.strategy_id,
        strategy_instance_id=hypothesis.strategy_instance_id,
        strategy_origin_group=strategy_origin_group,
        strategy_state=_map_strategy_state(hypothesis.strategy_state),
        asset_scope=[hypothesis.asset] if hypothesis.asset else [],
        sector_scope=hypothesis.sector,
        time_horizon=hypothesis.time_horizon,
    )


def build_ineligible_hypothesis(
    hypothesis_id: str,
    reason_codes: list[str],
) -> IneligibleHypothesis:
    """Build an IneligibleHypothesis with reason codes."""
    decisions = []
    for code in reason_codes:
        try:
            reason = EligibilityReasonCode(code)
        except ValueError:
            reason = EligibilityReasonCode.E01_MISSING_REQUIRED_INPUTS
        decisions.append(EligibilityDecision(
            rule_id="lane_c_eligibility",
            reason_codes=[reason],
        ))
    return IneligibleHypothesis(
        hypothesis_id=hypothesis_id,
        decisions=decisions,
    )


def compute_kernel_package_id(
    event_id: str,
    strategy_ids: list[str],
    hypothesis_ids: list[str],
) -> str:
    """Deterministic kernel package ID from sorted components."""
    raw = "|".join(sorted([event_id] + strategy_ids + hypothesis_ids))
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"kp_{h}"


# ── Internal helpers ─────────────────────────────────────────────


# ── Internal helpers ───────────────────────────────────────────────────────

def _map_strategy_state(state: str) -> str:
    """Map Lane C strategy state to kernel-compatible state string."""
    mapping = {
        "candidate": "candidate",
        "triggered": "active",
        "awaiting_confirmation": "awaiting_confirmation",
        "confirmed": "supported",
        "supported": "supported",
        "invalidated": "invalidated",
        "expired": "expired",
        "insufficient_evidence": "insufficient_evidence",
    }
    return mapping.get(state, "insufficient_evidence")


def _map_to_kernel_status(state: str) -> "HypothesisStatus":
    """Map Lane C strategy state to kernel HypothesisStatus."""
    from market_radar.intelligence.contracts.hypothesis import HypothesisStatus
    mapping = {
        "candidate": HypothesisStatus.CANDIDATE,
        "triggered": HypothesisStatus.ACTIVE,
        "awaiting_confirmation": HypothesisStatus.AWAITING_CONFIRMATION,
        "confirmed": HypothesisStatus.SUPPORTED,
        "supported": HypothesisStatus.SUPPORTED,
        "invalidated": HypothesisStatus.INVALIDATED,
        "expired": HypothesisStatus.EXPIRED,
        "insufficient_evidence": HypothesisStatus.INSUFFICIENT_EVIDENCE,
    }
    return mapping.get(state, HypothesisStatus.INSUFFICIENT_EVIDENCE)


def _compute_evidence_verdict(hypothesis) -> str:
    """Compute evidence bundle verdict from hypothesis evidence state."""
    support_count = len(hypothesis.supporting_evidence_refs)
    oppose_count = len(hypothesis.opposing_evidence_refs)
    if support_count > 0 and oppose_count == 0:
        return "supported"
    elif support_count > 0 and oppose_count > 0:
        return "conflicting"
    elif support_count == 0 and oppose_count > 0:
        return "contradicted"
    else:
        return "insufficient"
