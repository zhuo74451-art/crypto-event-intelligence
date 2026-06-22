"""
Claim Normalizer — Deterministic claim key generation and structure validation.

Ensures:
- Same structured content produces same claim_id
- Different time horizons produce different claim_ids
- Opposite directions on same subject share a conflict key
"""

import hashlib
import json
from dataclasses import asdict
from typing import List, Optional, Tuple

from market_radar.intelligence.research.contracts import (
    ResearchClaimV1,
    _deterministic_id,
    VALID_CLAIM_STATUSES,
    FORBIDDEN_STATUSES,
)


def build_claim_key(
    subject: str,
    predicate: str,
    object: str,
    asset: Optional[str] = None,
    event_family: Optional[str] = None,
    time_horizon: Optional[str] = None,
    regime: Optional[str] = None,
    claim_scope: str = "historical_only",
) -> str:
    """Build a deterministic claim key from structured components."""
    parts = [
        subject,
        predicate,
        object,
        asset or "",
        event_family or "",
        time_horizon or "",
        regime or "",
        claim_scope,
    ]
    return "::".join(parts)


def build_conflict_key(
    subject: str,
    object: str,
    event_family: Optional[str] = None,
    time_horizon: Optional[str] = None,
    regime: Optional[str] = None,
) -> str:
    """
    Build a conflict key that groups opposing claims.
    Strips direction (predicate) so opposite claims map to same set.
    """
    parts = [
        subject,
        object,
        event_family or "",
        time_horizon or "",
        regime or "",
    ]
    return "CONFLICT::" + "::".join(parts)


def create_claim(
    subject: str,
    predicate: str,
    object: str,
    claim_type: str,
    claim_status: str,
    asset: Optional[str] = None,
    event_family: Optional[str] = None,
    time_horizon: Optional[str] = None,
    regime: Optional[str] = None,
    claim_scope: str = "historical_only",
    **kwargs,
) -> ResearchClaimV1:
    """
    Factory function to create a normalized claim.
    Validates structure and generates deterministic IDs.
    """
    claim = ResearchClaimV1(
        subject=subject,
        predicate=predicate,
        object=object,
        claim_type=claim_type,
        claim_status=claim_status,
        claim_scope=claim_scope,
        asset=asset,
        event_family=event_family,
        time_horizon=time_horizon,
        regime=regime,
        **kwargs,
    )
    return claim


def validate_claim_semantics(claim: ResearchClaimV1) -> List[str]:
    """Validate claim semantic rules. Returns list of warnings."""
    warnings = []
    if claim.claim_status in FORBIDDEN_STATUSES:
        warnings.append(f"Forbidden status '{claim.claim_status}' used")
    if claim.claim_status not in VALID_CLAIM_STATUSES:
        warnings.append(f"Invalid status '{claim.claim_status}'")
    if claim.maturity < 0 or claim.maturity > 5:
        warnings.append(f"Maturity out of range: {claim.maturity}")
    return warnings


def claims_are_opposing(c1: ResearchClaimV1, c2: ResearchClaimV1) -> bool:
    """
    Check if two claims are opposing (same subject/object, opposite direction).
    """
    if c1.subject != c2.subject or c1.object != c2.object:
        return False
    # Different predicates on same subject-object pair = opposing direction
    if c1.predicate != c2.predicate:
        return True
    return False


def claims_share_different_horizon(c1: ResearchClaimV1, c2: ResearchClaimV1) -> bool:
    """
    Check if two claims differ only in time horizon (same subject/predicate/object).
    """
    same_core = (
        c1.subject == c2.subject
        and c1.predicate == c2.predicate
        and c1.object == c2.object
    )
    if not same_core:
        return False
    return c1.time_horizon != c2.time_horizon
