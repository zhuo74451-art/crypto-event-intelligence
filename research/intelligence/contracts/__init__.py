"""Research Intelligence contracts package."""
from research.intelligence.contracts.common import (
    AccessType, ClaimStatus, ClaimType, ConflictType, CoverageLevel, DecayRisk,
    GapStatus, HypothesisStatus, OriginType, Priority, ProvenanceStatus,
    QualityRating, RedistributionStatus, ResolutionStatus, RuntimeContractStatus,
    SourceRole, StrategyCandidateValidationStatus, StrategySeedStatus,
    TraderVerificationStatus, UnexplainedEventStatus, generate_id,
)
from research.intelligence.contracts.source_record import ResearchSourceRecord
from research.intelligence.contracts.claim import ResearchClaim
from research.intelligence.contracts.conflict import ClaimConflict
from research.intelligence.contracts.coverage import CoverageDomain
from research.intelligence.contracts.knowledge_gap import KnowledgeGap
from research.intelligence.contracts.knowledge_decay import KnowledgeDecayRecord
from research.intelligence.contracts.unexplained_event import UnexplainedEvent
from research.intelligence.contracts.hypothesis import ResearchHypothesis
from research.intelligence.contracts.trader_profile import TraderProfile
from research.intelligence.contracts.capability import Capability
from research.intelligence.contracts.strategy_seed import StrategySeed
from research.intelligence.contracts.strategy_candidate import (
    BaselineSpec, DatasetSpec, LabelSpec, Specification, SplitSpec, StrategyCandidate,
)
from research.intelligence.contracts.errors import (
    ResearchError, circular_provenance, claim_method_missing, claim_period_missing,
    claim_without_source, conflict_type_invalid, copy_forbidden_by_license,
    counterevidence_missing, decay_trigger_missing, hypothesis_leakage_risk_missing,
    hypothesis_not_testable, knowledge_gap_duplicate, license_status_unknown,
    missing_abstention_logic, missing_invalidation, performance_claim_unverified,
    production_promotion_forbidden, redistribution_not_allowed, source_identity_unstable,
    source_record_missing, strategy_without_claims, trader_source_unverified,
    upstream_commit_missing,
)

__all__ = [
    "AccessType", "BaselineSpec", "Capability", "ClaimConflict", "ClaimStatus",
    "ClaimType", "ConflictType", "CoverageDomain", "CoverageLevel", "DatasetSpec",
    "DecayRisk", "GapStatus", "HypothesisStatus", "KnowledgeDecayRecord", "KnowledgeGap",
    "LabelSpec", "OriginType", "Priority", "ProvenanceStatus", "QualityRating",
    "RedistributionStatus", "ResearchClaim", "ResearchError", "ResearchHypothesis",
    "ResearchSourceRecord", "ResolutionStatus", "RuntimeContractStatus", "SourceRole",
    "Specification", "SplitSpec", "StrategyCandidate", "StrategyCandidateValidationStatus",
    "StrategySeed", "StrategySeedStatus", "TraderProfile", "TraderVerificationStatus",
    "UnexplainedEvent", "UnexplainedEventStatus", "circular_provenance",
    "claim_method_missing", "claim_period_missing", "claim_without_source",
    "conflict_type_invalid", "copy_forbidden_by_license", "counterevidence_missing",
    "decay_trigger_missing", "generate_id", "hypothesis_leakage_risk_missing",
    "hypothesis_not_testable", "knowledge_gap_duplicate", "license_status_unknown",
    "missing_abstention_logic", "missing_invalidation", "performance_claim_unverified",
    "production_promotion_forbidden", "redistribution_not_allowed",
    "source_identity_unstable", "source_record_missing", "strategy_without_claims",
    "trader_source_unverified", "upstream_commit_missing",
]
