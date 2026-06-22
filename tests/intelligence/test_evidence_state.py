"""Tests for evidence state — EvidenceItem, EvidenceBundle, EvidenceResolver."""

import pytest

from market_radar.intelligence.contracts.evidence import (
    EvidenceItem, EvidenceBundle, BundleStatus,
    VerificationStatus, EvidenceQualityReason,
)
from market_radar.intelligence.engines.evidence_resolver import EvidenceResolverV1


def make_item(eid, claim="test claim", source="src_001",
              is_primary=False, retracted=False,
              independence_group="", verification="single_source_unverified"):
    return EvidenceItem(
        evidence_id=eid,
        claim=claim,
        source_id=source,
        independence_group=independence_group or source,
        is_primary=is_primary,
        retraction_status=retracted,
        verification_status=VerificationStatus(verification),
        source_role="reporter",
    )


class TestEvidenceItem:
    def test_create_primary(self):
        item = make_item("evi_001", is_primary=True)
        assert item.evidence_id == "evi_001"
        assert item.is_primary

    def test_create_secondary(self):
        item = make_item("evi_002", is_primary=False)
        assert not item.is_primary


class TestEvidenceResolver:
    def test_zero_evidence_returns_insufficient(self):
        resolver = EvidenceResolverV1()
        bundle = resolver.resolve([])
        assert bundle.bundle_verdict == VerificationStatus.INSUFFICIENT
        assert EvidenceQualityReason.NO_EVIDENCE in bundle.status.quality_reasons

    def test_single_primary_source_verified(self):
        resolver = EvidenceResolverV1()
        items = [
            make_item("evi_001", is_primary=True,
                      verification="verified_primary",
                      independence_group="group_a"),
        ]
        bundle = resolver.resolve(items)
        assert bundle.bundle_verdict == VerificationStatus.VERIFIED_PRIMARY

    def test_two_independent_primaries(self):
        resolver = EvidenceResolverV1()
        items = [
            make_item("evi_001", claim="same claim", is_primary=True,
                      independence_group="group_a"),
            make_item("evi_002", claim="same claim", is_primary=True,
                      independence_group="group_b"),
        ]
        bundle = resolver.resolve(items)
        assert bundle.bundle_verdict == VerificationStatus.VERIFIED_MULTI_SOURCE
        assert bundle.status.independent_source_count >= 2

    def test_same_group_does_not_increase_count(self):
        resolver = EvidenceResolverV1()
        items = [
            make_item("evi_001", is_primary=True, independence_group="group_a"),
            make_item("evi_002", is_primary=True, independence_group="group_a"),
        ]
        bundle = resolver.resolve(items)
        assert bundle.status.independent_source_count == 1

    def test_duplicate_claims_same_source_same_group_aggregated(self):
        resolver = EvidenceResolverV1()
        items = [
            make_item("evi_001", claim="same", is_primary=True,
                      independence_group="group_a"),
            make_item("evi_002", claim="same", is_primary=True,
                      independence_group="group_a"),
        ]
        bundle = resolver.resolve(items)
        assert bundle.status.independent_source_count == 1

    def test_retracted_primary_not_verified(self):
        resolver = EvidenceResolverV1()
        items = [
            make_item("evi_001", is_primary=True, retracted=True,
                      independence_group="group_a"),
        ]
        bundle = resolver.resolve(items)
        assert bundle.bundle_verdict != VerificationStatus.VERIFIED_PRIMARY
        assert bundle.status.retractions

    def test_conflicting_primaries(self):
        resolver = EvidenceResolverV1()
        items = [
            make_item("evi_001", claim="claim A", is_primary=True,
                      independence_group="group_a"),
            make_item("evi_002", claim="claim B", is_primary=True,
                      independence_group="group_b"),
        ]
        bundle = resolver.resolve(items)
        assert bundle.bundle_verdict == VerificationStatus.CONFLICTING

    def test_all_retracted_primaries_return_retracted(self):
        resolver = EvidenceResolverV1()
        items = [
            make_item("evi_001", is_primary=True, retracted=True,
                      independence_group="group_a"),
            make_item("evi_002", is_primary=True, retracted=True,
                      independence_group="group_b"),
        ]
        bundle = resolver.resolve(items)
        assert bundle.bundle_verdict == VerificationStatus.RETRACTED

    def test_secondary_sources_credible(self):
        resolver = EvidenceResolverV1()
        items = [
            make_item("evi_001", is_primary=False, independence_group="group_a"),
        ]
        bundle = resolver.resolve(items)
        assert bundle.bundle_verdict == VerificationStatus.CREDIBLE_SECONDARY

    def test_ten_republished_from_same_source(self):
        resolver = EvidenceResolverV1()
        items = [
            make_item(f"evi_{i:03d}", claim="same news", is_primary=False,
                      independence_group="original_source")
            for i in range(10)
        ]
        bundle = resolver.resolve(items)
        assert bundle.status.independent_source_count == 1
        assert bundle.bundle_verdict != VerificationStatus.VERIFIED_MULTI_SOURCE

    def test_bundle_id_includes_count(self):
        resolver = EvidenceResolverV1()
        bundle = resolver.resolve([make_item("evi_001")])
        assert "bundle" in bundle.bundle_id

    def test_quality_reasons_present_for_conflict(self):
        resolver = EvidenceResolverV1()
        items = [
            make_item("evi_001", claim="claim A", is_primary=True,
                      independence_group="group_a"),
            make_item("evi_002", claim="claim B", is_primary=True,
                      independence_group="group_b"),
        ]
        bundle = resolver.resolve(items)
        assert EvidenceQualityReason.CONFLICT_DETECTED in bundle.status.quality_reasons
