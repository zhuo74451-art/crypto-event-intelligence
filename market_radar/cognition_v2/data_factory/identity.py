"""Event identity, duplicates and correction chains.

D06: Deterministic identity assignment using permitted fields and
versioned rules.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional, Set, Tuple

from market_radar.cognition_v2.data_factory.contracts import (
    CorrectionChainAssignment,
    CorrectionType,
    DuplicateType,
    EventIdentityAssignment,
    SplitLabel,
)


class EventIdentityResolver:
    """Resolves stable event identities and correction chains."""

    def __init__(self, rule_version: str = "1.0"):
        self._rule_version = rule_version
        self._identities: Dict[str, EventIdentityAssignment] = {}
        self._chains: Dict[str, CorrectionChainAssignment] = {}

    def compute_event_identity(
        self,
        case_id: str,
        title: str,
        event_family: str,
        event_time: Optional[str] = None,
        source_ids: Optional[List[str]] = None,
    ) -> str:
        """Compute a deterministic event identity from stable fields."""
        content = json.dumps({
            "title_stem": self._stem(title),
            "family": event_family,
            "time": event_time,
        }, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _stem(self, title: str) -> str:
        """Simple title stem — lower, strip common words, sort tokens."""
        import re
        common = {"the", "a", "an", "and", "or", "of", "in", "to", "for",
                  "on", "at", "by", "with", "from", "is", "are", "was", "were",
                  "has", "have", "had", "be", "been", "being", "its", "it",
                  "this", "that", "not", "no", "after", "before", "during"}
        tokens = [t.lower() for t in re.findall(r'\w+', title)]
        tokens = [t for t in tokens if t not in common]
        tokens.sort()
        return " ".join(tokens[:10])

    def assign_identity(
        self,
        case_id: str,
        event_identity_id: str,
        duplicate_type: Optional[DuplicateType] = None,
        evidence_refs: Optional[List[str]] = None,
    ) -> EventIdentityAssignment:
        """Assign a case to an event identity."""
        assignment = EventIdentityAssignment(
            case_id=case_id,
            event_identity_id=event_identity_id,
            duplicate_type=duplicate_type,
            rule_version=self._rule_version,
            evidence_refs=evidence_refs or [],
        )
        self._identities[case_id] = assignment
        return assignment

    def assign_correction_chain(
        self,
        case_id: str,
        chain_id: str,
        chain_root_case_id: Optional[str] = None,
        correction_type: Optional[CorrectionType] = None,
        target_case_id: Optional[str] = None,
        evidence_refs: Optional[List[str]] = None,
    ) -> CorrectionChainAssignment:
        """Assign a case to a correction chain."""
        assignment = CorrectionChainAssignment(
            case_id=case_id,
            correction_chain_id=chain_id,
            chain_root_case_id=chain_root_case_id,
            correction_type=correction_type,
            target_case_id=target_case_id,
            rule_version=self._rule_version,
            evidence_refs=evidence_refs or [],
        )
        self._chains[case_id] = assignment
        return assignment

    def get_chain_members(self, chain_id: str) -> List[str]:
        """Get all case IDs in a correction chain."""
        return [
            ca.case_id for ca in self._chains.values()
            if ca.correction_chain_id == chain_id
        ]

    def get_identity_cases(self, identity_id: str) -> List[str]:
        """Get all case IDs sharing an event identity."""
        return [
            ia.case_id for ia in self._identities.values()
            if ia.event_identity_id == identity_id
        ]

    def validate_cross_split(
        self,
        case_to_split: Dict[str, SplitLabel],
    ) -> List[str]:
        """Validate no identity or chain crosses a split."""
        errors = []

        # Check identities
        id_to_splits: Dict[str, Set[SplitLabel]] = {}
        for ia in self._identities.values():
            split = case_to_split.get(ia.case_id)
            if split is None:
                continue
            if ia.event_identity_id not in id_to_splits:
                id_to_splits[ia.event_identity_id] = set()
            id_to_splits[ia.event_identity_id].add(split)

        for eid, splits in id_to_splits.items():
            if len(splits) > 1:
                errors.append(
                    f"Event identity '{eid}' crosses splits: "
                    f"{', '.join(s.value for s in splits)}"
                )

        # Check chains
        chain_to_splits: Dict[str, Set[SplitLabel]] = {}
        for ca in self._chains.values():
            split = case_to_split.get(ca.case_id)
            if split is None:
                continue
            if ca.correction_chain_id not in chain_to_splits:
                chain_to_splits[ca.correction_chain_id] = set()
            chain_to_splits[ca.correction_chain_id].add(split)

        for cid, splits in chain_to_splits.items():
            if len(splits) > 1:
                errors.append(
                    f"Correction chain '{cid}' crosses splits: "
                    f"{', '.join(s.value for s in splits)}"
                )

        return errors
