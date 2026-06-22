"""
Candidate Compiler — compiles research candidates from claims, conflicts, and validation results.

Candidates can come from:
- Historically supported but uncalibrated strategies
- Regime-stable strategies
- Low-error strategies with limited coverage
- Clear conflicts worth additional data
- Failed experiments revealing boundary conditions
- New event families or data fields

Auto-compilation always produces candidate_status: "proposed".
Upgrades require structured evidence from Lane D validation.
"""

from dataclasses import asdict
from datetime import datetime, timezone
from typing import List, Optional

from market_radar.intelligence.research.contracts import (
    ResearchClaimV1,
    ConflictSetV1,
    CandidateRecordV1,
    _deterministic_id,
    _utc_now,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class CandidateCompiler:
    """
    Compiles research candidates from existing evidence.
    Auto-compilation only produces "proposed" status.
    """

    def __init__(self):
        self._candidates: dict[str, CandidateRecordV1] = {}

    def propose_from_claim(
        self,
        claim: ResearchClaimV1,
        candidate_type: str = "directional_strategy",
    ) -> CandidateRecordV1:
        """Create a proposed candidate from a supported / contested claim."""
        candidate_name = f"candidate_{claim.claim_key.replace('::', '_')[:60]}"
        candidate = CandidateRecordV1(
            candidate_type=candidate_type,
            candidate_name=candidate_name,
            candidate_status="proposed",
            source_claim_ids=[claim.claim_id],
            strategy_family=claim.strategy_id or claim.event_family,
            asset_scope=[claim.asset] if claim.asset else [],
            event_family_scope=[claim.event_family] if claim.event_family else [],
            horizon_scope=[claim.time_horizon] if claim.time_horizon else [],
            regime_scope=[claim.regime] if claim.regime else [],
            limitations=claim.limitations.copy(),
        )
        return self._add_or_merge(candidate)

    def propose_from_conflict(
        self,
        conflict: ConflictSetV1,
    ) -> CandidateRecordV1:
        """Create a proposed candidate from an open conflict worth investigating."""
        candidate_name = f"conflict_candidate_{conflict.conflict_key.replace('::', '_')[:60]}"
        candidate = CandidateRecordV1(
            candidate_type="event_cluster",
            candidate_name=candidate_name,
            candidate_status="proposed",
            source_conflict_ids=[conflict.conflict_set_id],
            source_claim_ids=conflict.claim_ids.copy(),
            event_family_scope=[conflict.event_family] if conflict.event_family else [],
            horizon_scope=[conflict.time_horizon] if conflict.time_horizon else [],
            regime_scope=[conflict.regime] if conflict.regime else [],
            limitations=["open conflict — needs additional evidence"],
        )
        return self._add_or_merge(candidate)

    def _add_or_merge(self, candidate: CandidateRecordV1) -> CandidateRecordV1:
        """Add a candidate or merge if one with same ID already exists."""
        if candidate.candidate_id in self._candidates:
            existing = self._candidates[candidate.candidate_id]
            # Merge source references
            existing.source_claim_ids = list(set(
                existing.source_claim_ids + candidate.source_claim_ids
            ))
            existing.source_conflict_ids = list(set(
                existing.source_conflict_ids + candidate.source_conflict_ids
            ))
            existing.updated_at_utc = _utc_now()
            return existing
        self._candidates[candidate.candidate_id] = candidate
        return candidate

    def get_all_candidates(self) -> List[CandidateRecordV1]:
        return list(self._candidates.values())

    def get_proposed_candidates(self) -> List[CandidateRecordV1]:
        return [c for c in self._candidates.values() if c.candidate_status == "proposed"]

    def export_jsonl(self, path: str):
        import json
        with open(path, "w", encoding="utf-8") as f:
            for c in self._candidates.values():
                f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
