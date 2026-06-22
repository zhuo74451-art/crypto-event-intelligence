"""Evidence Resolver V1 — deterministic evidence bundle resolution.

V1 does NOT use LLM inference. All resolution is based on explicit fields
and deterministic rules.

Key fixes over original:
- Structured claim fields (claim_key) for conflict detection, not string comparison
- Staleness policy actually enforced
- Proper independence group deduplication
- All verdict rules from the arbitration rulebook
- Decision trace output
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..contracts.evidence import (
    EvidenceItem, EvidenceBundle, BundleStatus, VerificationStatus,
    EvidenceQualityReason, EvidenceDecisionTrace,
    StalenessPolicy, EvidenceResolutionPolicy, Stance,
)
from ..contracts.common import DataStatus
from ..errors.codes import IntelligenceError, ErrorCode


class EvidenceResolverV1:
    """Deterministic evidence resolver with full rulebook support."""

    def __init__(self, policy: Optional[EvidenceResolutionPolicy] = None):
        self.policy = policy or EvidenceResolutionPolicy()

    def resolve(self, items: list[EvidenceItem],
                as_of_time: Optional[str] = None) -> EvidenceBundle:
        """Resolve a list of evidence items into an evidence bundle.

        Args:
            items: Evidence items to resolve.
            as_of_time: Point-in-time for staleness evaluation (UTC ISO).
                        If None, uses current time.

        Returns:
            EvidenceBundle with verdict and decision trace.
        """
        trace = EvidenceDecisionTrace()
        now = as_of_time or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"

        # Stable bundle ID: hash of all evidence IDs sorted
        sorted_ids = sorted(i.evidence_id for i in items if i.evidence_id)
        import hashlib
        bundle_hash = hashlib.sha256(
            "|".join(sorted_ids).encode("utf-8")
        ).hexdigest()[:24] if sorted_ids else "empty"
        bundle_id = f"evb_{bundle_hash}"
        trace.rule_ids_applied.append("EVI-001: stable_bundle_id")

        # Phase 1: Evaluate availability for each item
        available_items = []
        excluded_items = []
        staleness_decisions = {}

        for item in items:
            if item.retraction_status:
                excluded_items.append(item.evidence_id)
                trace.rule_ids_applied.append(f"EVI-002: retracted_{item.evidence_id}")
                continue

            if self._is_stale(item, now):
                excluded_items.append(item.evidence_id)
                staleness_decisions[item.evidence_id] = "stale"
                trace.rule_ids_applied.append(f"EVI-003: stale_{item.evidence_id}")
                continue

            available_items.append(item)
            trace.included_evidence.append(item.evidence_id)

        trace.staleness_decisions = staleness_decisions
        trace.excluded_evidence = excluded_items

        # Phase 2: Independence groups on available items
        groups: dict[str, list[EvidenceItem]] = {}
        for item in available_items:
            grp = item.independence_group if item.independence_group else (
                f"ungrouped_{item.source_id}" if item.source_id else "ungrouped_unknown"
            )
            groups.setdefault(grp, []).append(item)

        independent_count = len(groups)
        group_names = list(groups.keys())
        trace.independence_groups = group_names
        trace.rule_ids_applied.append("EVI-004: independence_grouping")

        # Phase 3: Conflict detection using structured claim keys
        conflicts: list[dict] = []
        active_primaries = [i for i in available_items if i.is_primary]

        # Only detect conflict when same claim_key has contradictory stances
        claim_key_map: dict[str, list[EvidenceItem]] = {}
        for item in available_items:
            key = item.claim_key or item.claim
            claim_key_map.setdefault(key, []).append(item)

        for claim_key, group_items in claim_key_map.items():
            stances = set(i.stance.value for i in group_items)
            if Stance.SUPPORTS.value in stances and Stance.CONTRADICTS.value in stances:
                has_primary = any(i.is_primary for i in group_items)
                if has_primary or len(group_items) >= 2:
                    conflicts.append({
                        "claim_key": claim_key,
                        "reason": "Same claim key has both supports and contradicts stances",
                        "sources": [i.source_id for i in group_items if i.source_id],
                    })
                    trace.rule_ids_applied.append(f"EVI-005: conflict_{claim_key}")

        trace.conflicts = conflicts

        # Phase 4: Retraction check on primary sources
        retraction_conflicts = [i.evidence_id for i in items if i.retraction_status and i.is_primary]

        # Phase 5: Determine verdict
        status = BundleStatus(
            primary_source_present=len(active_primaries) > 0,
            independent_source_count=independent_count,
            independence_groups=group_names,
            conflicts=[c["reason"] for c in conflicts],
            staleness=len(staleness_decisions) > 0,
            retractions=retraction_conflicts,
        )

        quality_reasons: list[EvidenceQualityReason] = []

        if not items:
            quality_reasons.append(EvidenceQualityReason.NO_EVIDENCE)
            bundle_verdict = VerificationStatus.INSUFFICIENT
            trace.final_rule_id = "EVI-100: zero_evidence"
        else:
            bundle_verdict = self._determine_verdict(
                active_primaries=active_primaries,
                available_items=available_items,
                conflicts=conflicts,
                retractions=retraction_conflicts,
                independent_count=independent_count,
                quality_reasons=quality_reasons,
                trace=trace,
            )

        status.quality_reasons = quality_reasons
        for c in conflicts:
            if EvidenceQualityReason.CONFLICT_DETECTED not in status.quality_reasons:
                status.quality_reasons.append(EvidenceQualityReason.CONFLICT_DETECTED)

        if staleness_decisions and EvidenceQualityReason.STALE_DATA not in status.quality_reasons:
            status.quality_reasons.append(EvidenceQualityReason.STALE_DATA)

        return EvidenceBundle(
            bundle_id=bundle_id,
            items=items,
            status=status,
            bundle_verdict=bundle_verdict,
            decision_trace=trace,
        )

    def _is_stale(self, item: EvidenceItem, now: str) -> bool:
        """Check if an evidence item is stale according to policy."""
        policy = self.policy.staleness

        if policy.policy_type == "never_expires":
            return False

        if policy.policy_type == "explicit_expires_at":
            if not policy.override_expires_at:
                return False
            try:
                return policy.override_expires_at <= now
            except (ValueError, TypeError):
                return False

        # Age-based: get the reference timestamp from the item
        if policy.policy_type == "age_from_published_at":
            ref = item.published_at
        elif policy.policy_type == "age_from_updated_at":
            ref = item.updated_at
        elif policy.policy_type == "age_from_retrieved_at":
            ref = item.retrieved_at
        else:
            return False

        if not ref:
            return False

        try:
            from ..contracts.common import utc_parse
            ref_dt = utc_parse(ref)
            now_dt = utc_parse(now)
            delta = now_dt - ref_dt
            return delta.days > policy.max_age_days
        except (ValueError, TypeError):
            return False

    def _determine_verdict(
        self,
        active_primaries: list[EvidenceItem],
        available_items: list[EvidenceItem],
        conflicts: list[dict],
        retractions: list[str],
        independent_count: int,
        quality_reasons: list[EvidenceQualityReason],
        trace: EvidenceDecisionTrace,
    ) -> VerificationStatus:
        """Determine the bundle verdict based on deterministic rules."""

        # EVI-100: Zero evidence
        if not available_items:
            quality_reasons.append(EvidenceQualityReason.NO_EVIDENCE)
            trace.final_rule_id = "EVI-100: zero_evidence"
            return VerificationStatus.INSUFFICIENT

        # EVI-110: All evidence retracted
        if retractions:
            all_primaries = [i for i in available_items if i.is_primary]
            all_primaries_retracted = all(
                i.retraction_status for i in
                [i for i in active_primaries if i.evidence_id in retractions]
            ) if active_primaries else False
            if active_primaries and all(i.retraction_status for i in active_primaries):
                quality_reasons.append(EvidenceQualityReason.RETRACTION_DETECTED)
                trace.final_rule_id = "EVI-110: all_primary_retracted"
                return VerificationStatus.RETRACTED

        # EVI-120: Conflicting primary sources on same claim key
        if conflicts and any(c.get("sources") for c in conflicts):
            quality_reasons.append(EvidenceQualityReason.CONFLICT_DETECTED)
            trace.final_rule_id = "EVI-120: conflicting_primary_sources"
            return VerificationStatus.CONFLICTING

        # EVI-130: Two independent primary sources, same claim
        if len(active_primaries) >= 2 and independent_count >= 2 and not conflicts:
            quality_reasons.append(EvidenceQualityReason.MULTI_INDEPENDENT)
            trace.final_rule_id = "EVI-130: verified_multi_source"
            return VerificationStatus.VERIFIED_MULTI_SOURCE

        # EVI-140: One active primary source
        if len(active_primaries) == 1:
            item = active_primaries[0]
            trace.final_rule_id = "EVI-140: single_primary"
            if item.verification_status == VerificationStatus.VERIFIED_PRIMARY:
                quality_reasons.append(EvidenceQualityReason.PRIMARY_SOURCE_PRESENT)
                return VerificationStatus.VERIFIED_PRIMARY
            quality_reasons.append(EvidenceQualityReason.SINGLE_SOURCE)
            return VerificationStatus.SINGLE_SOURCE_UNVERIFIED

        # EVI-150: Secondary sources only
        secondary = [i for i in available_items if not i.is_primary]
        if secondary:
            if independent_count >= 2:
                quality_reasons.append(EvidenceQualityReason.MULTI_INDEPENDENT)
                trace.final_rule_id = "EVI-151: multi_secondary"
                return VerificationStatus.CREDIBLE_SECONDARY
            quality_reasons.append(EvidenceQualityReason.SINGLE_SOURCE)
            trace.final_rule_id = "EVI-152: single_secondary"
            return VerificationStatus.CREDIBLE_SECONDARY

        trace.final_rule_id = "EVI-199: insufficient_default"
        return VerificationStatus.INSUFFICIENT


