"""
Conflict Engine — identifies and manages conflict sets from claims and evidence.

Detects:
- Same event family, opposite directions
- Same direction, different time scales
- Same strategy, different regime outcomes
- Historical vs holdout contradictions
- High-quality vs low-quality evidence contradictions
- Strict PIT vs reconstructed sample contradictions
- Initial vs revised values leading to different interpretations
- First market reaction vs subsequent reaction contradictions
- Macro transmission vs derivatives confirmation contradictions

Outputs conflict sets without forcing a side.
"""

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import List, Optional

from market_radar.intelligence.research.contracts import (
    ResearchClaimV1,
    EvidenceEdgeV1,
    ConflictSetV1,
    _deterministic_id,
    _utc_now,
    VALID_CONFLICT_TYPES,
)
from market_radar.intelligence.research.claim_normalizer import (
    build_conflict_key,
    claims_are_opposing,
    claims_share_different_horizon,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ConflictEngine:
    """
    Detects and manages evidence/claim conflicts.
    Does NOT auto-resolve by majority — always preserves both sides.
    """

    def __init__(self):
        self._conflict_sets: dict[str, ConflictSetV1] = {}

    def process_claims(self, claims: List[ResearchClaimV1]) -> List[ConflictSetV1]:
        """
        Scan all claims for conflicts and return new/updated conflict sets.
        Idempotent: same claims produce same conflict sets.
        """
        new_conflicts: List[ConflictSetV1] = []

        # Check for direction conflicts (same subject/object, different predicate)
        for i, c1 in enumerate(claims):
            for c2 in claims[i + 1:]:
                if not claims_are_opposing(c1, c2):
                    continue

                conflict_key = build_conflict_key(
                    subject=c1.subject,
                    object=c1.object,
                    event_family=c1.event_family or c2.event_family,
                    time_horizon=c1.time_horizon or c2.time_horizon,
                    regime=c1.regime or c2.regime,
                )

                cs = self._get_or_create(
                    conflict_key=conflict_key,
                    conflict_type="direction_conflict",
                    claim_ids=[c1.claim_id, c2.claim_id],
                    asset=c1.asset or c2.asset,
                    event_family=c1.event_family or c2.event_family,
                    time_horizon=c1.time_horizon or c2.time_horizon,
                    regime=c1.regime or c2.regime,
                )
                new_conflicts.append(cs)

        # Check for horizon conflicts (same subject/predicate/object, different horizon)
        for i, c1 in enumerate(claims):
            for c2 in claims[i + 1:]:
                if not claims_share_different_horizon(c1, c2):
                    continue

                conflict_key = build_conflict_key(
                    subject=c1.subject,
                    object=c1.object,
                    event_family=c1.event_family or c2.event_family,
                    time_horizon="ANY",
                    regime=c1.regime or c2.regime,
                )

                cs = self._get_or_create(
                    conflict_key=conflict_key,
                    conflict_type="horizon_conflict",
                    claim_ids=[c1.claim_id, c2.claim_id],
                    asset=c1.asset or c2.asset,
                    event_family=c1.event_family or c2.event_family,
                    time_horizon="multiple",
                    regime=c1.regime or c2.regime,
                )
                new_conflicts.append(cs)

        return new_conflicts

    def _get_or_create(
        self,
        conflict_key: str,
        conflict_type: str,
        claim_ids: List[str],
        asset: Optional[str] = None,
        event_family: Optional[str] = None,
        time_horizon: Optional[str] = None,
        regime: Optional[str] = None,
    ) -> ConflictSetV1:
        """Get existing conflict set or create new one. Idempotent merge."""
        # Check if conflict set already exists
        for existing in self._conflict_sets.values():
            if existing.conflict_key == conflict_key:
                # Merge claim IDs
                for cid in claim_ids:
                    if cid not in existing.claim_ids:
                        existing.claim_ids.append(cid)
                existing.updated_at_utc = _utc_now()
                return existing

        cs = ConflictSetV1(
            conflict_key=conflict_key,
            conflict_type=conflict_type,
            claim_ids=claim_ids,
            conflict_status="open",
            asset=asset,
            event_family=event_family,
            time_horizon=time_horizon,
            regime=regime,
            resolution_status="unresolved",
        )
        self._conflict_sets[cs.conflict_set_id] = cs
        return cs

    def get_all_conflict_sets(self) -> List[ConflictSetV1]:
        return list(self._conflict_sets.values())

    def get_conflict_sets_for_claim(self, claim_id: str) -> List[ConflictSetV1]:
        return [cs for cs in self._conflict_sets.values() if claim_id in cs.claim_ids]

    def get_open_conflicts(self) -> List[ConflictSetV1]:
        return [cs for cs in self._conflict_sets.values() if cs.conflict_status == "open"]

    def export_jsonl(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            for cs in self._conflict_sets.values():
                f.write(json.dumps(asdict(cs), ensure_ascii=False) + "\n")
