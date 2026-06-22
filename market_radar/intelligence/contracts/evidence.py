"""Evidence contracts — evidence items, bundles, and verification status."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from .common import ContractBase, IntelligenceID, DataStatus


class VerificationStatus(str, Enum):
    VERIFIED_PRIMARY = "verified_primary"
    VERIFIED_MULTI_SOURCE = "verified_multi_source"
    CREDIBLE_SECONDARY = "credible_secondary"
    SINGLE_SOURCE_UNVERIFIED = "single_source_unverified"
    CONFLICTING = "conflicting"
    STALE = "stale"
    RETRACTED = "retracted"
    INSUFFICIENT = "insufficient"


class EvidenceQualityReason(str, Enum):
    PRIMARY_SOURCE_PRESENT = "primary_source_present"
    MULTI_INDEPENDENT = "multi_independent"
    SAME_GROUP_AGGREGATED = "same_group_aggregated"
    CONFLICT_DETECTED = "conflict_detected"
    RETRACTION_DETECTED = "retraction_detected"
    STALE_DATA = "stale_data"
    SINGLE_SOURCE = "single_source"
    NO_EVIDENCE = "no_evidence"
    TIME_ANOMALY = "time_anomaly"


class Stance(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"
    REPORTS = "reports"
    UNKNOWN = "unknown"


class EvidenceAvailability(str, Enum):
    AVAILABLE = "available"
    MISSING = "missing"
    CONFLICTING = "conflicting"
    STALE = "stale"
    RETRACTED = "retracted"
    UNSUPPORTED = "unsupported"


@dataclass
class EvidenceItem(ContractBase):
    """A single piece of evidence from a source."""
    contract_name: str = "EvidenceItem"
    schema_version: str = "1.0.0"

    evidence_id: str = ""
    claim: str = ""
    claim_key: str = ""
    claim_subject: str = ""
    claim_predicate: str = ""
    claim_value: str = ""
    stance: Stance = Stance.UNKNOWN

    source_id: str = ""
    source_role: str = ""

    published_at: Optional[str] = None
    effective_at: Optional[str] = None
    updated_at: Optional[str] = None
    first_seen_at: Optional[str] = None
    retrieved_at: Optional[str] = None

    independence_group: str = ""
    raw_payload_ref: str = ""
    archive_ref: str = ""
    content_hash: str = ""

    is_primary: bool = False
    verification_status: VerificationStatus = VerificationStatus.INSUFFICIENT
    retraction_status: bool = False
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.verification_status, str):
            self.verification_status = VerificationStatus(self.verification_status)
        if isinstance(self.stance, str):
            self.stance = Stance(self.stance)


@dataclass
class StalenessPolicy:
    """Configuration for evidence staleness evaluation."""
    policy_type: str = "never_expires"
    max_age_days: int = 30
    override_expires_at: Optional[str] = None
    event_state_family: str = ""

    def describe(self) -> str:
        if self.policy_type == "never_expires":
            return "Evidence never expires"
        if self.policy_type == "explicit_expires_at":
            return f"Expires at: {self.override_expires_at or 'not set'}"
        return f"Max age: {self.max_age_days} days via {self.policy_type}"


@dataclass
class EvidenceResolutionPolicy:
    """Configuration for evidence resolution behavior."""
    staleness: StalenessPolicy = field(default_factory=StalenessPolicy)
    require_independence_group: bool = False
    min_primary_sources_for_multi: int = 2


@dataclass
class EvidenceDecisionTrace:
    """Machine-readable trace of the evidence resolution process."""
    rule_ids_applied: list[str] = field(default_factory=list)
    included_evidence: list[str] = field(default_factory=list)
    excluded_evidence: list[str] = field(default_factory=list)
    independence_groups: list[str] = field(default_factory=list)
    conflicts: list[dict] = field(default_factory=list)
    staleness_decisions: dict[str, str] = field(default_factory=dict)
    final_rule_id: str = ""


@dataclass
class BundleStatus:
    primary_source_present: bool = False
    independent_source_count: int = 0
    independence_groups: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    staleness: bool = False
    retractions: list[str] = field(default_factory=list)
    quality_reasons: list[EvidenceQualityReason] = field(default_factory=list)

    def __post_init__(self):
        if self.quality_reasons:
            self.quality_reasons = [
                EvidenceQualityReason(r) if isinstance(r, str) else r
                for r in self.quality_reasons
            ]


@dataclass
class EvidenceBundle(ContractBase):
    """Aggregated evidence state for a claim or event."""
    contract_name: str = "EvidenceBundle"
    schema_version: str = "1.0.0"

    bundle_id: str = ""
    items: list[EvidenceItem] = field(default_factory=list)
    status: BundleStatus = field(default_factory=BundleStatus)
    bundle_verdict: VerificationStatus = VerificationStatus.INSUFFICIENT
    decision_trace: EvidenceDecisionTrace = field(default_factory=EvidenceDecisionTrace)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.bundle_verdict, str):
            self.bundle_verdict = VerificationStatus(self.bundle_verdict)
        if isinstance(self.status, dict):
            self.status = BundleStatus(**self.status)
        if isinstance(self.decision_trace, dict):
            self.decision_trace = EvidenceDecisionTrace(**self.decision_trace)
