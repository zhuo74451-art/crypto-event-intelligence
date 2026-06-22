#!/usr/bin/env python3
"""Validate all research intelligence contracts, registries, compilers, and coverage.

Runs a comprehensive validation: instantiates each contract type, tests validation
rules, exercises registries, provenance validation, compilers, coverage evaluator,
promotion logic, and error contracts.

Usage:
    python scripts/research_intelligence/validate_research_intelligence.py
"""

import sys
from pathlib import Path

# ── Add project root to sys.path ──────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Imports ───────────────────────────────────────────────────────────────
from datetime import datetime
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
from research.intelligence.contracts.promotion import (
    can_transition_claim, can_transition_hypothesis, can_transition_seed,
    can_transition_candidate_validation, can_transition_runtime,
    can_transition_resolution, can_transition_gap, can_transition_unexplained_event,
)
from research.intelligence.registries.source_registry import SourceRegistry
from research.intelligence.registries.claim_registry import ClaimRegistry
from research.intelligence.registries.conflict_registry import ConflictRegistry
from research.intelligence.registries.gap_registry import GapRegistry
from research.intelligence.registries.decay_registry import DecayRegistry
from research.intelligence.registries.unexplained_event_registry import UnexplainedEventRegistry
from research.intelligence.registries.hypothesis_registry import HypothesisRegistry
from research.intelligence.registries.trader_registry import TraderRegistry
from research.intelligence.registries.strategy_seed_registry import StrategySeedRegistry
from research.intelligence.compiler.provenance_validator import ProvenanceValidator, ProvenanceValidationReport
from research.intelligence.compiler.strategy_seed_compiler import StrategySeedCompiler, SeedCompilationReport
from research.intelligence.compiler.strategy_candidate_compiler import StrategyCandidateCompiler, CandidateCompilationReport
from research.intelligence.coverage.domain_catalog import build_domain_catalog

# ════════════════════════════════════════════════════════════════════════════
# Validation helpers
# ════════════════════════════════════════════════════════════════════════════

_passed = 0
_failed = 0


def check(description: str, condition: bool) -> None:
    global _passed, _failed
    if condition:
        print(f"  [OK] {description}")
        _passed += 1
    else:
        print(f"  [FAIL] {description}")
        _failed += 1


def section(title: str) -> None:
    print(f"\n{'=' * 68}")
    print(f"  {title}")
    print(f"{'=' * 68}")


# ════════════════════════════════════════════════════════════════════════════
# 1. Instantiate each contract type
# ════════════════════════════════════════════════════════════════════════════

section("1. Instantiate each contract type")

sr = ResearchSourceRecord(name="Test Source", url="https://example.com", source_type="web")
check("ResearchSourceRecord instantiated", isinstance(sr, ResearchSourceRecord))

cl = ResearchClaim(statement="Test claim", source_id=sr.source_id, methodology="backtest", observation_period="2024")
check("ResearchClaim instantiated", isinstance(cl, ResearchClaim))

cf = ClaimConflict(claim_ids=["CL-001", "CL-002"], description="Test conflict")
check("ClaimConflict instantiated", isinstance(cf, ClaimConflict))

cd = CoverageDomain(name="Test Domain", description="A test domain")
check("CoverageDomain instantiated", isinstance(cd, CoverageDomain))

kg = KnowledgeGap(title="Test Gap", description="A knowledge gap")
check("KnowledgeGap instantiated", isinstance(kg, KnowledgeGap))

kd = KnowledgeDecayRecord(entity_type="claim", entity_id="CL-001", trigger_event="Market change")
check("KnowledgeDecayRecord instantiated", isinstance(kd, KnowledgeDecayRecord))

ue = UnexplainedEvent(title="Test Event", description="An unexplained event")
check("UnexplainedEvent instantiated", isinstance(ue, UnexplainedEvent))

hy = ResearchHypothesis(title="Test Hypothesis", statement="Market impact", leakage_risk_assessment="low")
check("ResearchHypothesis instantiated", isinstance(hy, ResearchHypothesis))

tp = TraderProfile(name="Test Trader", source_ids=["SR-001"])
check("TraderProfile instantiated", isinstance(tp, TraderProfile))

cap = Capability(name="Test Capability", description="A test capability")
check("Capability instantiated", isinstance(cap, Capability))

ss = StrategySeed(title="Test Seed", description="A test strategy seed")
check("StrategySeed instantiated", isinstance(ss, StrategySeed))

ds = DatasetSpec(name="dataset1", source="exchange")
check("DatasetSpec instantiated", isinstance(ds, DatasetSpec))

ls = LabelSpec(name="target", column="ret")
check("LabelSpec instantiated", isinstance(ls, LabelSpec))

bs = BaselineSpec(name="S&P500")
check("BaselineSpec instantiated", isinstance(bs, BaselineSpec))

sps = SplitSpec(method="temporal")
check("SplitSpec instantiated", isinstance(sps, SplitSpec))

spec = Specification(model_type="xgboost")
check("Specification instantiated", isinstance(spec, Specification))

sc = StrategyCandidate(name="Test Candidate", description="A candidate strategy", claim_ids=["CL-001"])
check("StrategyCandidate instantiated", isinstance(sc, StrategyCandidate))

err = ResearchError(message="test error")
check("ResearchError instantiated", isinstance(err, ResearchError))

# ════════════════════════════════════════════════════════════════════════════
# 2. Test validation on each contract
# ════════════════════════════════════════════════════════════════════════════

section("2. Validation rules")

# Source record
sr_valid = ResearchSourceRecord(name="Valid", url="https://ex.com", source_type="arxiv")
check("SourceRecord valid passes", len(sr_valid.validate()) == 0)

sr_no_name = ResearchSourceRecord(url="https://ex.com", source_type="arxiv")
check("SourceRecord missing name fails", len(sr_no_name.validate()) > 0)

sr_no_url = ResearchSourceRecord(name="No URL", source_type="arxiv")
check("SourceRecord missing url fails", len(sr_no_url.validate()) > 0)

sr_no_type = ResearchSourceRecord(name="No Type", url="https://ex.com")
check("SourceRecord missing source_type fails", len(sr_no_type.validate()) > 0)

sr_bad_role = ResearchSourceRecord(name="Bad", url="https://ex.com", source_type="web", role="invalid")
check("SourceRecord invalid role fails", len(sr_bad_role.validate()) > 0)

sr_bad_access = ResearchSourceRecord(name="Bad", url="https://ex.com", source_type="web", access_type="nope")
check("SourceRecord invalid access_type fails", len(sr_bad_access.validate()) > 0)

# Claim
cl_valid = ResearchClaim(statement="Test", source_id="SR-001", methodology="backtest", observation_period="2024")
check("Claim valid passes", len(cl_valid.validate()) == 0)

cl_no_stmt = ResearchClaim(source_id="SR-001", methodology="backtest", observation_period="2024")
check("Claim missing statement fails", len(cl_no_stmt.validate()) > 0)

cl_no_source = ResearchClaim(statement="Test", methodology="backtest", observation_period="2024")
check("Claim missing source_id fails", len(cl_no_source.validate()) > 0)

cl_no_method = ResearchClaim(statement="Test", source_id="SR-001", observation_period="2024")
check("Claim missing methodology fails", len(cl_no_method.validate()) > 0)

cl_no_period = ResearchClaim(statement="Test", source_id="SR-001", methodology="backtest")
check("Claim missing observation_period fails", len(cl_no_period.validate()) > 0)

cl_bad_type = ResearchClaim(statement="Test", source_id="SR-001", methodology="bt", observation_period="2024", claim_type="invalid")
check("Claim invalid claim_type fails", len(cl_bad_type.validate()) > 0)

# Conflict
cf_valid = ClaimConflict(claim_ids=["CL-001", "CL-002"], description="Conflict")
check("Conflict valid passes", len(cf_valid.validate()) == 0)

cf_no_claims = ClaimConflict(description="No claims")
check("Conflict missing claim_ids fails", len(cf_no_claims.validate()) > 0)

cf_single = ClaimConflict(claim_ids=["CL-001"], description="Single claim")
check("Conflict <2 claim_ids fails", len(cf_single.validate()) > 0)

cf_bad_type = ClaimConflict(claim_ids=["CL-001", "CL-002"], conflict_type="nope")
check("Conflict invalid type fails", len(cf_bad_type.validate()) > 0)

# CoverageDomain
cd_valid = CoverageDomain(name="Valid Domain", description="Test")
check("CoverageDomain valid passes", len(cd_valid.validate()) == 0)

cd_no_name = CoverageDomain(description="No name")
check("CoverageDomain missing name fails", len(cd_no_name.validate()) > 0)

cd_self_parent = CoverageDomain(name="Self", description="Self parent", parent_domain_id="self")
cd_self_parent.domain_id = "self"
check("CoverageDomain self-parent fails", len(cd_self_parent.validate()) > 0)

# KnowledgeGap
kg_valid = KnowledgeGap(title="Gap", description="A gap")
check("KnowledgeGap valid passes", len(kg_valid.validate()) == 0)

kg_no_title = KnowledgeGap(description="No title")
check("KnowledgeGap missing title fails", len(kg_no_title.validate()) > 0)

kg_no_desc = KnowledgeGap(title="No desc")
check("KnowledgeGap missing description fails", len(kg_no_desc.validate()) > 0)

# KnowledgeDecayRecord
kd_valid = KnowledgeDecayRecord(entity_type="claim", entity_id="CL-001", trigger_event="Change")
check("KnowledgeDecayRecord valid passes", len(kd_valid.validate()) == 0)

kd_no_entity_type = KnowledgeDecayRecord(entity_id="CL-001", trigger_event="Change")
check("DecayRecord missing entity_type fails", len(kd_no_entity_type.validate()) > 0)

kd_no_entity_id = KnowledgeDecayRecord(entity_type="claim", trigger_event="Change")
check("DecayRecord missing entity_id fails", len(kd_no_entity_id.validate()) > 0)

kd_no_trigger = KnowledgeDecayRecord(entity_type="claim", entity_id="CL-001")
check("DecayRecord missing trigger_event fails", len(kd_no_trigger.validate()) > 0)

# UnexplainedEvent
ue_valid = UnexplainedEvent(title="Event", description="Desc")
check("UnexplainedEvent valid passes", len(ue_valid.validate()) == 0)

ue_no_title = UnexplainedEvent(description="Desc")
check("UnexplainedEvent missing title fails", len(ue_no_title.validate()) > 0)

ue_no_desc = UnexplainedEvent(title="Event")
check("UnexplainedEvent missing description fails", len(ue_no_desc.validate()) > 0)

# ResearchHypothesis
hy_valid = ResearchHypothesis(title="Hyp", statement="Market goes up", leakage_risk_assessment="low")
check("Hypothesis valid passes", len(hy_valid.validate()) == 0)

hy_no_title = ResearchHypothesis(statement="Market goes up", leakage_risk_assessment="low")
check("Hypothesis missing title fails", len(hy_no_title.validate()) > 0)

hy_no_stmt = ResearchHypothesis(title="Hyp", leakage_risk_assessment="low")
check("Hypothesis missing statement fails", len(hy_no_stmt.validate()) > 0)

hy_no_leakage = ResearchHypothesis(title="Hyp", statement="Market goes up")
check("Hypothesis missing leakage_risk fails", len(hy_no_leakage.validate()) > 0)

hy_not_testable = ResearchHypothesis(title="Hyp", statement="Test", is_testable=False, leakage_risk_assessment="low")
check("Hypothesis not testable fails", len(hy_not_testable.validate()) > 0)

# TraderProfile
tp_valid = TraderProfile(name="Trader", source_ids=["SR-001"])
tp_valid.verification_status = TraderVerificationStatus.VERIFIED
check("TraderProfile verified passes", len(tp_valid.validate()) == 0)

tp_no_name = TraderProfile(source_ids=["SR-001"])
check("TraderProfile missing name fails", len(tp_no_name.validate()) > 0)

tp_no_sources = TraderProfile(name="Trader")
check("TraderProfile missing source_ids fails", len(tp_no_sources.validate()) > 0)

# Capability
cap_valid = Capability(name="Cap", description="A capability")
check("Capability valid passes", len(cap_valid.validate()) == 0)

cap_no_name = Capability(description="No name")
check("Capability missing name fails", len(cap_no_name.validate()) > 0)

cap_no_desc = Capability(name="Cap")
check("Capability missing description fails", len(cap_no_desc.validate()) > 0)

# StrategySeed
ss_valid = StrategySeed(title="Seed", description="A seed")
check("StrategySeed valid passes", len(ss_valid.validate()) == 0)

ss_no_title = StrategySeed(description="No title")
check("StrategySeed missing title fails", len(ss_no_title.validate()) > 0)

ss_no_desc = StrategySeed(title="Seed")
check("StrategySeed missing description fails", len(ss_no_desc.validate()) > 0)

# StrategyCandidate
sc_valid = StrategyCandidate(name="Cand", description="A candidate", claim_ids=["CL-001"])
sc_valid.specification.model_type = "xgboost"
sc_valid.specification.abstention_logic = "abstain"
sc_valid.specification.invalidation_criteria = "invalidate"
sc_valid.specification.splits.method = "temporal"
check("StrategyCandidate valid passes", len(sc_valid.validate()) == 0)

sc_no_name = StrategyCandidate(description="No name", claim_ids=["CL-001"])
check("Candidate missing name fails", len(sc_no_name.validate()) > 0)

sc_no_claims = StrategyCandidate(name="Cand", description="No claims")
check("Candidate missing claim_ids fails", len(sc_no_claims.validate()) > 0)

sc_no_abstention = StrategyCandidate(name="Cand", description="No abstain", claim_ids=["CL-001"])
sc_no_abstention.specification.model_type = "xgboost"
sc_no_abstention.specification.splits.method = "temporal"
check("Candidate missing abstention fails", len(sc_no_abstention.validate()) > 0)

sc_no_invalidation = StrategyCandidate(name="Cand", description="No invalidate", claim_ids=["CL-001"])
sc_no_invalidation.specification.model_type = "xgboost"
sc_no_invalidation.specification.abstention_logic = "abstain"
sc_no_invalidation.specification.splits.method = "temporal"
check("Candidate missing invalidation fails", len(sc_no_invalidation.validate()) > 0)

# Component specs
ds_no_name = DatasetSpec(source="ex")
check("DatasetSpec missing name fails", len(ds_no_name.validate()) > 0)

ds_no_source = DatasetSpec(name="ds")
check("DatasetSpec missing source fails", len(ds_no_source.validate()) > 0)

ls_no_name = LabelSpec(column="ret")
check("LabelSpec missing name fails", len(ls_no_name.validate()) > 0)

ls_no_column = LabelSpec(name="target")
check("LabelSpec missing column fails", len(ls_no_column.validate()) > 0)

bs_no_name = BaselineSpec(model_type="lin")
check("BaselineSpec missing name fails", len(bs_no_name.validate()) > 0)

sps_no_method = SplitSpec(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15)
check("SplitSpec missing method fails", len(sps_no_method.validate()) > 0)

sps_bad_ratios = SplitSpec(method="temporal", train_ratio=0.5, val_ratio=0.5, test_ratio=0.5)
check("SplitSpec bad ratios fails", len(sps_bad_ratios.validate()) > 0)

# ════════════════════════════════════════════════════════════════════════════
# 3. Registries
# ════════════════════════════════════════════════════════════════════════════

section("3. Registries")

# SourceRegistry
src_reg = SourceRegistry()
sr1 = ResearchSourceRecord(name="Source 1", url="https://ex1.com", source_type="web")
src_reg.add(sr1)
check("SourceRegistry.add works", src_reg.count() == 1)
check("SourceRegistry.get works", src_reg.get(sr1.source_id) is sr1)
check("SourceRegistry.list_all works", len(src_reg.list_all()) == 1)
src_reg.remove(sr1.source_id)
check("SourceRegistry.remove works", src_reg.count() == 0)
src_reg.add(sr1)
src_reg.update(sr1)
check("SourceRegistry.update works", src_reg.count() == 1)
check("SourceRegistry.find_by_name works", len(src_reg.find_by_name("Source")) == 1)
sr1.tags.append("important")
check("SourceRegistry.find_by_tag works", len(src_reg.find_by_tag("important")) == 1)

# ClaimRegistry
cl_reg = ClaimRegistry()
cl1 = ResearchClaim(statement="Claim 1", source_id="SR-001", methodology="backtest", observation_period="2024")
cl_reg.add(cl1)
check("ClaimRegistry.add works", cl_reg.count() == 1)
check("ClaimRegistry.get works", cl_reg.get(cl1.claim_id) is cl1)
check("ClaimRegistry.find_by_source works", len(cl_reg.find_by_source("SR-001")) == 1)
check("ClaimRegistry.find_by_type works", len(cl_reg.find_by_type(ClaimType.FACTUAL)) == 1)
check("ClaimRegistry.find_by_status works", len(cl_reg.find_by_status(ClaimStatus.DRAFT)) == 1)

# ConflictRegistry
cf_reg = ConflictRegistry()
cf1 = ClaimConflict(claim_ids=["CL-001", "CL-002"], description="Conflict 1")
cf_reg.add(cf1)
check("ConflictRegistry.add works", cf_reg.count() == 1)
check("ConflictRegistry.find_by_claim works", len(cf_reg.find_by_claim("CL-001")) == 1)
check("ConflictRegistry.find_unresolved works", len(cf_reg.find_unresolved()) == 1)

# GapRegistry
gap_reg = GapRegistry()
kg1 = KnowledgeGap(title="Gap 1", description="Gap desc")
gap_reg.add(kg1)
check("GapRegistry.add works", gap_reg.count() == 1)
check("GapRegistry.find_open works", len(gap_reg.find_open()) == 1)

# DecayRegistry
decay_reg = DecayRegistry()
kd1 = KnowledgeDecayRecord(entity_type="claim", entity_id="CL-001", trigger_event="Change")
decay_reg.add(kd1)
check("DecayRegistry.add works", decay_reg.count() == 1)
check("DecayRegistry.find_critical works", len(decay_reg.find_critical()) == 0)

# UnexplainedEventRegistry
ue_reg = UnexplainedEventRegistry()
ue1 = UnexplainedEvent(title="Event 1", description="Event desc")
ue_reg.add(ue1)
check("UnexplainedEventRegistry.add works", ue_reg.count() == 1)
check("UnexplainedEventRegistry.find_unexplained works", len(ue_reg.find_unexplained()) == 1)

# HypothesisRegistry
hy_reg = HypothesisRegistry()
hy1 = ResearchHypothesis(title="Hyp 1", statement="Market impact", leakage_risk_assessment="low")
hy_reg.add(hy1)
check("HypothesisRegistry.add works", hy_reg.count() == 1)
check("HypothesisRegistry.find_active works", len(hy_reg.find_active()) == 1)

# TraderRegistry
t_reg = TraderRegistry()
tp1 = TraderProfile(name="Trader 1", source_ids=["SR-001"])
tp1.verification_status = TraderVerificationStatus.VERIFIED
t_reg.add(tp1)
check("TraderRegistry.add works", t_reg.count() == 1)
check("TraderRegistry.find_by_name works", len(t_reg.find_by_name("Trader")) == 1)
check("TraderRegistry.find_verified works", len(t_reg.find_verified()) == 1)

# StrategySeedRegistry
seed_reg = StrategySeedRegistry()
ss1 = StrategySeed(title="Seed 1", description="Seed desc")
seed_reg.add(ss1)
check("StrategySeedRegistry.add works", seed_reg.count() == 1)
check("StrategySeedRegistry.find_by_status works", len(seed_reg.find_by_status(StrategySeedStatus.RAW)) == 1)

# ════════════════════════════════════════════════════════════════════════════
# 4. Provenance validation
# ════════════════════════════════════════════════════════════════════════════

section("4. Provenance validation")

pv = ProvenanceValidator()

report = pv.validate_chain([])
check("Empty chain passes", report.passed)
check("Empty chain has warning", len(report.warnings) > 0)

report = pv.validate_chain(["A", "B", "C"])
check("Valid chain passes", report.passed)
check("Valid chain is verified", report.status == ProvenanceStatus.VERIFIED)

report = pv.validate_chain(["X", "X"])
check("Circular chain fails", not report.passed)
check("Circular chain is broken", report.status == ProvenanceStatus.BROKEN)

report = pv.validate_chain(["", "Y"])
check("Empty entity in chain fails", not report.passed)

warnings = pv.validate_source_stability("stable-id", [])
check("Stable source has no warnings", len(warnings) == 0)

warnings = pv.validate_source_stability("", ["a", "b"])
check("Empty source_id warns", len(warnings) > 0)

warnings = pv.validate_source_stability("s", ["a", "b", "c", "d", "e"])
check("Many aliases warn", len(warnings) > 0)

# ════════════════════════════════════════════════════════════════════════════
# 5. Compilers
# ════════════════════════════════════════════════════════════════════════════

section("5. Compilers")

seed_comp = StrategySeedCompiler()

ss_compile = StrategySeed(
    title="Compilable Seed",
    description="A test seed for compilation",
    source_ids=["SR-001"],
)
ss_compile.tags = ["test", "TAG"]
result_seed, report = seed_comp.compile(ss_compile)
check("Seed compiler returns success", report.success)
check("Seed compiler enriches tags", "test" in result_seed.tags and "tag" in result_seed.tags)
check("Seed compiler promotes status", result_seed.status == StrategySeedStatus.SCRAPED)

ss_no_sources = StrategySeed(
    title="No Sources",
    description="Seed without sources",
)
result2, report2 = seed_comp.compile(ss_no_sources)
check("Seed with no sources succeeds (empty provenance ok)", report2.success)

cand_comp = StrategyCandidateCompiler()

ss_validated = StrategySeed(
    title="Candidate Seed",
    description="Ready for candidate",
    claim_ids=["CL-001"],
)
ss_validated.status = StrategySeedStatus.VALIDATED
candidate, cand_report = cand_comp.compile(ss_validated)
check("Candidate compiler returns success", cand_report.success)
check("Candidate has name from seed", candidate.name == "Candidate Seed")
check("Candidate has specification", candidate.specification.model_type == "unset")

ss_raw = StrategySeed(
    title="Raw Seed",
    description="Not ready",
)
candidate2, cand_report2 = cand_comp.compile(ss_raw)
check("Candidate compiler rejects raw seed", not cand_report2.success)

# ════════════════════════════════════════════════════════════════════════════
# 6. Coverage evaluator
# ════════════════════════════════════════════════════════════════════════════

section("6. Coverage evaluator")

domains = build_domain_catalog()
check("build_domain_catalog returns 13 domains", len(domains) == 13)

# Coverage summary inline
summary: dict[str, int] = {}
for d in domains:
    level_key = d.level.value.upper() if hasattr(d, "level") else "UNKNOWN"
    summary[level_key] = summary.get(level_key, 0) + 1
check("Coverage summary sums to 13", sum(summary.values()) == 13)

# Count distinct priorities (CoverageDomain may not have priority)
check("All 13 domains have .level attribute", all(hasattr(d, "level") for d in domains))

# Check that all 13 have unique domain_ids
domain_ids = [d.domain_id for d in domains]
check("All 13 domain IDs are unique", len(set(domain_ids)) == 13)

check("D01 domain present", any("D01" in d.domain_id for d in domains))
check("D13 domain present", any("D13" in d.domain_id for d in domains))

# ════════════════════════════════════════════════════════════════════════════
# 7. Promotion / transition logic
# ════════════════════════════════════════════════════════════════════════════

section("7. Promotion / transition logic")

check("Claim DRAFT->SUBMITTED valid", can_transition_claim(ClaimStatus.DRAFT, ClaimStatus.SUBMITTED))
check("Claim DRAFT->ARCHIVED valid", can_transition_claim(ClaimStatus.DRAFT, ClaimStatus.ARCHIVED))
check("Claim DRAFT->VERIFIED invalid", not can_transition_claim(ClaimStatus.DRAFT, ClaimStatus.VERIFIED))
check("Claim ARCHIVED no transitions", not can_transition_claim(ClaimStatus.ARCHIVED, ClaimStatus.DRAFT))

check("Hypothesis PROPOSED->UNDER_INVESTIGATION valid", can_transition_hypothesis(HypothesisStatus.PROPOSED, HypothesisStatus.UNDER_INVESTIGATION))
check("Hypothesis PROPOSED->WITHDRAWN valid", can_transition_hypothesis(HypothesisStatus.PROPOSED, HypothesisStatus.WITHDRAWN))
check("Hypothesis PROPOSED->SUPPORTED invalid", not can_transition_hypothesis(HypothesisStatus.PROPOSED, HypothesisStatus.SUPPORTED))

check("Seed RAW->SCRAPED valid", can_transition_seed(StrategySeedStatus.RAW, StrategySeedStatus.SCRAPED))
check("Seed RAW->REJECTED valid", can_transition_seed(StrategySeedStatus.RAW, StrategySeedStatus.REJECTED))
check("Seed RAW->CURATED invalid", not can_transition_seed(StrategySeedStatus.RAW, StrategySeedStatus.CURATED))

check("Candidate PENDING->PASSED valid", can_transition_candidate_validation(StrategyCandidateValidationStatus.PENDING, StrategyCandidateValidationStatus.PASSED))
check("Candidate PENDING->BLOCKED valid", can_transition_candidate_validation(StrategyCandidateValidationStatus.PENDING, StrategyCandidateValidationStatus.BLOCKED))
check("Candidate PENDING->WAIVED invalid", not can_transition_candidate_validation(StrategyCandidateValidationStatus.PENDING, StrategyCandidateValidationStatus.WAIVED))

check("Runtime ACTIVE->PAUSED valid", can_transition_runtime(RuntimeContractStatus.ACTIVE, RuntimeContractStatus.PAUSED))
check("Runtime PAUSED->ACTIVE valid", can_transition_runtime(RuntimeContractStatus.PAUSED, RuntimeContractStatus.ACTIVE))
check("Runtime EXPIRED no transitions", not can_transition_runtime(RuntimeContractStatus.EXPIRED, RuntimeContractStatus.ACTIVE))

check("Resolution UNRESOLVED->RESOLVED valid", can_transition_resolution(ResolutionStatus.UNRESOLVED, ResolutionStatus.RESOLVED))
check("Resolution RESOLVED->DISMISSED valid", can_transition_resolution(ResolutionStatus.RESOLVED, ResolutionStatus.DISMISSED))

check("Gap IDENTIFIED->UNDER_INVESTIGATION valid", can_transition_gap(GapStatus.IDENTIFIED, GapStatus.UNDER_INVESTIGATION))
check("Gap CLOSED no transitions", not can_transition_gap(GapStatus.CLOSED, GapStatus.IDENTIFIED))

check("Event DETECTED->INVESTIGATING valid", can_transition_unexplained_event(UnexplainedEventStatus.DETECTED, UnexplainedEventStatus.INVESTIGATING))
check("Event EXPLAINED no transitions", not can_transition_unexplained_event(UnexplainedEventStatus.EXPLAINED, UnexplainedEventStatus.DETECTED))

# ════════════════════════════════════════════════════════════════════════════
# 8. Error contracts
# ════════════════════════════════════════════════════════════════════════════

section("8. Error contracts")

check("ResearchError is Exception subclass", issubclass(ResearchError, Exception))
check("source_record_missing returns ResearchError", isinstance(source_record_missing(), ResearchError))
check("claim_without_source returns ResearchError", isinstance(claim_without_source(), ResearchError))
check("claim_method_missing returns ResearchError", isinstance(claim_method_missing(), ResearchError))
check("claim_period_missing returns ResearchError", isinstance(claim_period_missing(), ResearchError))
check("conflict_type_invalid returns ResearchError", isinstance(conflict_type_invalid(), ResearchError))
check("copy_forbidden_by_license returns ResearchError", isinstance(copy_forbidden_by_license(), ResearchError))
check("counterevidence_missing returns ResearchError", isinstance(counterevidence_missing(), ResearchError))
check("decay_trigger_missing returns ResearchError", isinstance(decay_trigger_missing(), ResearchError))
check("hypothesis_leakage_risk_missing returns ResearchError", isinstance(hypothesis_leakage_risk_missing(), ResearchError))
check("hypothesis_not_testable returns ResearchError", isinstance(hypothesis_not_testable(), ResearchError))
check("knowledge_gap_duplicate returns ResearchError", isinstance(knowledge_gap_duplicate(), ResearchError))
check("license_status_unknown returns ResearchError", isinstance(license_status_unknown(), ResearchError))
check("missing_abstention_logic returns ResearchError", isinstance(missing_abstention_logic(), ResearchError))
check("missing_invalidation returns ResearchError", isinstance(missing_invalidation(), ResearchError))
check("performance_claim_unverified returns ResearchError", isinstance(performance_claim_unverified(), ResearchError))
check("production_promotion_forbidden returns ResearchError", isinstance(production_promotion_forbidden(), ResearchError))
check("redistribution_not_allowed returns ResearchError", isinstance(redistribution_not_allowed(), ResearchError))
check("source_identity_unstable returns ResearchError", isinstance(source_identity_unstable(), ResearchError))
check("strategy_without_claims returns ResearchError", isinstance(strategy_without_claims(), ResearchError))
check("trader_source_unverified returns ResearchError", isinstance(trader_source_unverified(), ResearchError))
check("upstream_commit_missing returns ResearchError", isinstance(upstream_commit_missing(), ResearchError))
check("circular_provenance returns ResearchError", isinstance(circular_provenance(), ResearchError))

err = source_record_missing("SR-001")
check("Error message contains source ID", "SR-001" in str(err))
check("Error is str-able", isinstance(str(err), str))

# ════════════════════════════════════════════════════════════════════════════
# Summary
# ════════════════════════════════════════════════════════════════════════════

section("Summary")
total = _passed + _failed
print(f"  Passed: {_passed}/{total}")
print(f"  Failed: {_failed}/{total}")

if _failed:
    print("\n  !! SOME VALIDATIONS FAILED")
    sys.exit(1)
else:
    print("\n  ALL VALIDATIONS PASSED")
