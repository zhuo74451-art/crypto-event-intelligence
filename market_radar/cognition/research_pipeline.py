"""F04: Research Intelligence pipeline.

Markdown/JSON ingestion, claim lifecycle, conflict/decay handling.
Status transitions: seed -> testable -> historical_supported
  -> shadow_supported -> rejected/stale
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from market_radar.cognition.intake_contracts import ResearchClaimInput, LaneOrigin


_VALID_TRANSITIONS = {
    "seed": ["testable", "rejected"],
    "testable": ["historical_supported", "rejected", "stale"],
    "historical_supported": ["shadow_supported", "rejected", "stale"],
    "shadow_supported": ["rejected", "stale"],
    "rejected": [],
    "stale": [],
}


def transition_status(claim: ResearchClaimInput, new_status: str) -> Optional[str]:
    if new_status == claim.status:
        return None
    allowed = _VALID_TRANSITIONS.get(claim.status, [])
    if new_status not in allowed:
        return f"invalid transition: {claim.status} -> {new_status}"
    claim.status = new_status
    return None


def check_decay(claim: ResearchClaimInput, current_date: str) -> bool:
    """Check if a claim should transition to stale based on knowledge half-life."""
    if not claim.source_date or claim.knowledge_half_life_days <= 0:
        return False
    try:
        cd = datetime.fromisoformat(current_date.replace("Z", "+00:00"))
        sd = datetime.fromisoformat(claim.source_date.replace("Z", "+00:00"))
        elapsed = (cd - sd).days
        if elapsed > claim.knowledge_half_life_days * 2:
            return True
    except (ValueError, TypeError):
        pass
    return False


def compile_testable_hypotheses(claims: List[ResearchClaimInput]) -> List[Dict[str, Any]]:
    """Compile claims with status=testable into structured hypotheses."""
    hypotheses = []
    for c in claims:
        if c.status != "testable":
            continue
        hypotheses.append({
            "hypothesis_id": c.claim_id,
            "claim": c.claim_text,
            "domain": c.domain,
            "expected_direction": c.expected_direction,
            "falsification": c.falsification_condition,
            "applicable_regime": c.applicable_regime,
            "limitations": c.limitations,
        })
    return hypotheses