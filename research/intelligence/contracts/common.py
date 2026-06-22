"""Research Intelligence — common types, enums."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone


def generate_id(prefix: str = "RI") -> str:
    """Generate a canonical ID."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    short = uuid.uuid4().hex[:12]
    return f"{prefix}-{ts}-{short}"


class CoverageLevel(str, enum.Enum):
    L0_ABSENT = "L0_absent"
    L1_SOURCE_OR_KEYWORD_ONLY = "L1_source_or_keyword_only"
    L2_DESCRIPTIVE = "L2_descriptive"
    L3_HISTORICAL_HYPOTHESIS = "L3_historical_hypothesis"
    L4_OUT_OF_SAMPLE_VALIDATED = "L4_out_of_sample_validated"
    L5_REAL_TIME_SHADOW_CALIBRATED = "L5_real_time_shadow_calibrated"


class Priority(str, enum.Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class QualityRating(str, enum.Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    UNKNOWN = "unknown"


class AccessType(str, enum.Enum):
    OPEN_ACCESS = "open_access"
    PUBLIC_WEB = "public_web"
    METADATA_ONLY = "metadata_only"
    PAYWALLED = "paywalled"
    USER_PROVIDED = "user_provided"
    UNKNOWN = "unknown"


class SourceRole(str, enum.Enum):
    FOUNDATIONAL_MECHANISM = "foundational_mechanism"
    EMPIRICAL_UPDATE = "empirical_update"
    COUNTEREVIDENCE = "counterevidence"
    METHODOLOGY = "methodology"
    DATA_QUALITY = "data_quality"
    INDUSTRY_RESEARCH = "industry_research"
    TRADER_MATERIAL = "trader_material"
    OFFICIAL_REPORT = "official_report"


class ClaimType(str, enum.Enum):
    MECHANISM = "mechanism"
    EMPIRICAL_RELATIONSHIP = "empirical_relationship"
    MEASUREMENT_WARNING = "measurement_warning"
    CAUSAL_CLAIM = "causal_claim"
    DESCRIPTIVE_CLAIM = "descriptive_claim"
    NULL_RESULT = "null_result"
    BOUNDARY_CONDITION = "boundary_condition"


class ClaimStatus(str, enum.Enum):
    BACKGROUND = "background"
    CANDIDATE = "candidate"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    MIXED = "mixed"
    STALE = "stale"
    RETRACTED = "retracted"
    UNVERIFIED = "unverified"


class ConflictType(str, enum.Enum):
    DIRECT_CONTRADICTION = "direct_contradiction"
    DIFFERENT_SAMPLE = "different_sample"
    DIFFERENT_PERIOD = "different_period"
    DIFFERENT_MARKET = "different_market"
    DIFFERENT_REGIME = "different_regime"
    DIFFERENT_MEASUREMENT = "different_measurement"
    DIFFERENT_HORIZON = "different_horizon"
    METHODOLOGICAL_DISAGREEMENT = "methodological_disagreement"
    REPLICATION_FAILURE = "replication_failure"
    SCOPE_MISMATCH = "scope_mismatch"
    APPARENT_CONFLICT = "apparent_conflict"


class ResolutionStatus(str, enum.Enum):
    UNRESOLVED = "unresolved"
    PARTIALLY_RESOLVED = "partially_resolved"
    NOT_A_TRUE_CONFLICT = "not_a_true_conflict"
    LEFT_MORE_SUPPORTED = "left_more_supported"
    RIGHT_MORE_SUPPORTED = "right_more_supported"
    REGIME_DEPENDENT = "regime_dependent"
    MEASUREMENT_DEPENDENT = "measurement_dependent"


class HypothesisStatus(str, enum.Enum):
    PROPOSED = "proposed"
    SPECIFICATION_READY = "specification_ready"
    DATA_BLOCKED = "data_blocked"
    VALIDATION_READY = "validation_ready"
    UNDER_TEST = "under_test"
    SUPPORTED = "supported"
    REJECTED = "rejected"
    MIXED = "mixed"
    STALE = "stale"


class StrategySeedStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    RESEARCH_READY = "research_ready"
    SPECIFICATION_READY = "specification_ready"
    VALIDATION_READY = "validation_ready"
    REJECTED = "rejected"
    STALE = "stale"


class StrategyCandidateValidationStatus(str, enum.Enum):
    UNVALIDATED = "unvalidated"
    DATA_BLOCKED = "data_blocked"
    VALIDATION_READY = "validation_ready"
    UNDER_EXTERNAL_VALIDATION = "under_external_validation"
    REJECTED = "rejected"


class RuntimeContractStatus(str, enum.Enum):
    PENDING_INTEGRATION = "pending_integration"
    INCOMPATIBLE = "incompatible"
    INTEGRATION_READY = "integration_ready"


class DecayRisk(str, enum.Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNKNOWN = "unknown"


class GapStatus(str, enum.Enum):
    OPEN = "open"
    PARTIALLY_ADDRESSED = "partially_addressed"
    CLOSED = "closed"
    SUPERSEDED = "superseded"


class UnexplainedEventStatus(str, enum.Enum):
    OPEN = "open"
    UNDER_INVESTIGATION = "under_investigation"
    CANDIDATE_EXPLANATION_FOUND = "candidate_explanation_found"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ProvenanceStatus(str, enum.Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    UNVERIFIABLE = "unverifiable"
    CONTESTED = "contested"
    UNVERIFIED_OR_PARTIAL = "unverified_or_partial"


class TraderVerificationStatus(str, enum.Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    UNVERIFIED_OR_PARTIAL = "unverified_or_partial"
    CONTRADICTED = "contradicted"
    SELF_REPORTED = "self_reported"


class RedistributionStatus(str, enum.Enum):
    ALLOWED = "allowed"
    METADATA_ONLY = "metadata_only"
    FORBIDDEN = "forbidden"
    UNKNOWN = "unknown"


class OriginType(str, enum.Enum):
    TRADER = "trader"
    PAPER = "paper"
    PROJECT = "project"
    INTERNAL = "internal"
    MIXED = "mixed"
