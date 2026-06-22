"""Research error classes and helper factories.

Each helper returns a ready-to-raise (or catch) ``ResearchError`` instance
with a descriptive message.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResearchError(Exception):
    """Base exception for all research intelligence errors."""
    message: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        parts = [self.message]
        if self.detail:
            parts.append(str(self.detail))
        return " | ".join(parts)


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def source_record_missing(source_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Source record missing{': ' + source_id if source_id else ''}",
    )


def claim_without_source(claim_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Claim has no associated source{': ' + claim_id if claim_id else ''}",
    )


def claim_method_missing(claim_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Claim is missing its methodology{': ' + claim_id if claim_id else ''}",
    )


def claim_period_missing(claim_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Claim is missing its observation period{': ' + claim_id if claim_id else ''}",
    )


def conflict_type_invalid(conflict_id: str = "", detail: str = "") -> ResearchError:
    return ResearchError(
        message=f"Invalid conflict type{': ' + conflict_id if conflict_id else ''}",
        detail={"detail": detail} if detail else {},
    )


def copy_forbidden_by_license(source_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Copying is forbidden by the source license{': ' + source_id if source_id else ''}",
    )


def counterevidence_missing(claim_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Counter-evidence is required but missing{': ' + claim_id if claim_id else ''}",
    )


def decay_trigger_missing(record_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Decay record is missing a trigger event{': ' + record_id if record_id else ''}",
    )


def hypothesis_leakage_risk_missing(hypothesis_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Hypothesis is missing a leakage-risk assessment{': ' + hypothesis_id if hypothesis_id else ''}",
    )


def hypothesis_not_testable(hypothesis_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Hypothesis is not testable{': ' + hypothesis_id if hypothesis_id else ''}",
    )


def knowledge_gap_duplicate(gap_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Knowledge gap already exists{': ' + gap_id if gap_id else ''}",
    )


def license_status_unknown(source_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"License status is unknown for source{': ' + source_id if source_id else ''}",
    )


def missing_abstention_logic(strategy_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Strategy is missing abstention logic{': ' + strategy_id if strategy_id else ''}",
    )


def missing_invalidation(entity: str = "") -> ResearchError:
    return ResearchError(
        message=f"Invalidation criteria are missing{': ' + entity if entity else ''}",
    )


def performance_claim_unverified(claim_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Performance claim has not been verified{': ' + claim_id if claim_id else ''}",
    )


def production_promotion_forbidden(candidate_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Promotion to production is forbidden for this candidate{': ' + candidate_id if candidate_id else ''}",
    )


def redistribution_not_allowed(source_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Redistribution is not allowed for this source{': ' + source_id if source_id else ''}",
    )


def source_identity_unstable(source_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Source identity is unstable or ambiguous{': ' + source_id if source_id else ''}",
    )


def strategy_without_claims(strategy_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Strategy has no associated claims{': ' + strategy_id if strategy_id else ''}",
    )


def trader_source_unverified(trader_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Trader source is unverified{': ' + trader_id if trader_id else ''}",
    )


def upstream_commit_missing(source_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Upstream commit reference is missing{': ' + source_id if source_id else ''}",
    )


def circular_provenance(entity_id: str = "") -> ResearchError:
    return ResearchError(
        message=f"Circular provenance chain detected{': ' + entity_id if entity_id else ''}",
    )
