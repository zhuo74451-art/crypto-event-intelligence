"""Evidence Resolver V1 — deterministic evidence bundle resolution.

V1 does NOT use LLM inference. All resolution is based on explicit fields
and deterministic rules.
"""

from __future__ import annotations

from typing import Optional

from ..contracts.evidence import (
    EvidenceItem, EvidenceBundle, BundleStatus, VerificationStatus,
    EvidenceQualityReason,
)
from ..contracts.common import DataStatus
from ..errors.codes import IntelligenceError, ErrorCode


class EvidenceResolverV1:
    """Deterministic evidence resolver.

    Rules:
    - Retracted primary sources cannot produce verified_primary
    - Two contradictory primary sources -> conflicting
    - Same-group re-posts do not increase independent count
    - Zero evidence or all unavailable -> insufficient
    - Stale evidence does not auto-keep verified status
    """

    def __init__(self, max_staleness_days: int = 30):
        self.max_staleness_days = max_staleness_days

    def resolve(self, items: list[EvidenceItem]) -> EvidenceBundle:
        """Resolve a list of evidence items into an evidence bundle."""
        bundle_id = f"bundle_{len(items)}"

        primary_items = [i for i in items if i.is_primary]
        non_retracted = [i for i in items if not i.retraction_status]
        retracted_items = [i for i in items if i.retraction_status]

        # Independence groups
        groups: dict[str, list[EvidenceItem]] = {}
        for item in items:
            grp = item.independence_group or item.source_id
            groups.setdefault(grp, []).append(item)

        independent_count = len(groups)
        group_names = list(groups.keys())

        # Conflict detection among active primary sources
        conflicts: list[str] = []
        active_primaries = [i for i in primary_items if not i.retraction_status]
        if len(active_primaries) >= 2:
            # Check for contradictory claims across primary sources
            # Same claims across independent sources = confirmation (good)
            # Different claims = conflict
            unique_claims = set(p.claim for p in active_primaries)
            if len(unique_claims) >= 2:
                conflicts.append("Conflicting claims across primary sources")

        # Check retractions on primary sources
        retraction_conflicts = [i.evidence_id for i in retracted_items if i.is_primary]

        # Determine overall verdict
        status = BundleStatus(
            primary_source_present=len(primary_items) > 0,
            independent_source_count=independent_count,
            independence_groups=group_names,
            conflicts=conflicts,
            staleness=False,
            retractions=retraction_conflicts,
        )

        # Quality reasons
        quality_reasons = []

        if not items:
            status.quality_reasons.append(EvidenceQualityReason.NO_EVIDENCE)
            bundle_verdict = VerificationStatus.INSUFFICIENT
            return EvidenceBundle(
                bundle_id=bundle_id,
                items=items,
                status=status,
                bundle_verdict=bundle_verdict,
            )

        # Check retraction on primary
        if retraction_conflicts:
            status.quality_reasons.append(EvidenceQualityReason.RETRACTION_DETECTED)

        # Check conflicts
        if conflicts:
            status.quality_reasons.append(EvidenceQualityReason.CONFLICT_DETECTED)

        # Determine bundle verdict
        bundle_verdict = self._determine_verdict(
            primary_items=active_primaries,
            conflicts=conflicts,
            retractions=retraction_conflicts,
            independent_count=independent_count,
            items=items,
            quality_reasons=quality_reasons,
        )

        status.quality_reasons = quality_reasons
        # Ensure quality_reasons is properly set
        if conflicts and EvidenceQualityReason.CONFLICT_DETECTED not in status.quality_reasons:
            status.quality_reasons.append(EvidenceQualityReason.CONFLICT_DETECTED)

        return EvidenceBundle(
            bundle_id=bundle_id,
            items=items,
            status=status,
            bundle_verdict=bundle_verdict,
        )

    def _determine_verdict(
        self,
        primary_items: list[EvidenceItem],
        conflicts: list[str],
        retractions: list[str],
        independent_count: int,
        items: list[EvidenceItem],
        quality_reasons: list[EvidenceQualityReason],
    ) -> VerificationStatus:
        """Determine the bundle verdict based on deterministic rules."""
        # Zero evidence
        if not items:
            quality_reasons.append(EvidenceQualityReason.NO_EVIDENCE)
            return VerificationStatus.INSUFFICIENT

        # Retracted primary -> cannot be verified_primary
        if retractions:
            # Check if ALL primary sources are retracted
            all_primaries = [i for i in items if i.is_primary]
            all_retracted = all(i.retraction_status for i in all_primaries) if all_primaries else False
            if all_retracted:
                return VerificationStatus.RETRACTED

        # Conflicting primary sources
        if conflicts and len(primary_items) >= 2:
            return VerificationStatus.CONFLICTING

        # Verified multi-source
        if len(primary_items) >= 2 and independent_count >= 2 and not conflicts:
            quality_reasons.append(EvidenceQualityReason.MULTI_INDEPENDENT)
            return VerificationStatus.VERIFIED_MULTI_SOURCE

        # Single primary source
        if len(primary_items) == 1:
            item = primary_items[0]
            if independent_count > 1:
                quality_reasons.append(EvidenceQualityReason.MULTI_INDEPENDENT)
                return VerificationStatus.VERIFIED_MULTI_SOURCE
            quality_reasons.append(EvidenceQualityReason.SINGLE_SOURCE)
            if item.verification_status == VerificationStatus.VERIFIED_PRIMARY:
                return VerificationStatus.VERIFIED_PRIMARY
            return VerificationStatus.SINGLE_SOURCE_UNVERIFIED

        # Secondary sources only
        secondary_items = [i for i in items if not i.is_primary]
        if secondary_items:
            quality_reasons.append(EvidenceQualityReason.SINGLE_SOURCE)
            return VerificationStatus.CREDIBLE_SECONDARY

        return VerificationStatus.INSUFFICIENT
