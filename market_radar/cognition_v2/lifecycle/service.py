"""Canonical 11-state thesis lifecycle service.

Dependency: domain contracts only.
R11: deterministic transition request fingerprint for idempotency.
R12: test-only failure injection hook (production default = no-op).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from market_radar.cognition_v2.domain.contracts import (
    CANONICAL_EDGES,
    CANONICAL_STATES,
    EvidenceRef,
    EvidenceStatus,
    LifecycleTransitionRequest,
    ThesisState,
)
from market_radar.cognition_v2.persistence.models import (
    ThesisModel,
    ThesisRevisionModel,
    cognition_session_scope,
    compare_and_swap_thesis,
    StaleVersionError,
)


class LifecycleValidator:
    """Table-driven thesis lifecycle validator — zero dependencies."""

    def __init__(self):
        self._edges: Dict[ThesisState, Set[ThesisState]] = {
            s: set(targets) for s, targets in CANONICAL_EDGES.items()
        }

    @property
    def code_size(self) -> int:
        return sum(len(v) for v in self._edges.values())

    def validate(self, from_state: ThesisState, to_state: ThesisState) -> bool:
        return to_state in self._edges.get(from_state, set())

    def validate_or_raise(self, from_state: ThesisState, to_state: ThesisState) -> None:
        if not self.validate(from_state, to_state):
            raise ValueError(
                f"Illegal transition: {from_state.value} -> {to_state.value}"
            )

    def get_legal_transitions(self, state: ThesisState) -> List[ThesisState]:
        return sorted(self._edges.get(state, set()), key=lambda s: s.value)

    def all_states(self) -> List[ThesisState]:
        return list(CANONICAL_STATES)


# ═══════════════════════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class IdempotentTransitionError(Exception):
    pass


class TransitionConflictError(Exception):
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# R11 — Deterministic transition request fingerprint
# ═══════════════════════════════════════════════════════════════════════════════

_EPISTEMIC_CLASSES = {ThesisState.ACTIVE, ThesisState.DORMANT,
                       ThesisState.INVALIDATED, ThesisState.REOPEN_REVIEW}


def _is_epistemic_transition(to_state: ThesisState) -> bool:
    return to_state in _EPISTEMIC_CLASSES


def compute_request_fingerprint(request: LifecycleTransitionRequest) -> str:
    """Deterministic SHA256 fingerprint covering all significant request fields."""
    # Normalize evidence refs by sorted serialization
    normalized_evidence = sorted(
        [r.model_dump() for r in request.evidence_refs],
        key=lambda r: (r.get("source", ""), r.get("content_hash", "")),
    ) if request.evidence_refs else []

    # Normalize rule refs
    normalized_rules = sorted(request.rule_refs) if request.rule_refs else []

    content = json.dumps({
        "thesis_id": request.thesis_id,
        "from_state": request.from_state.value,
        "to_state": request.to_state.value,
        "expected_version": request.expected_version,
        "reason": request.reason.strip(),
        "evidence_refs": normalized_evidence,
        "rule_refs": normalized_rules,
    }, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# R12 — Failure injection hook
# ═══════════════════════════════════════════════════════════════════════════════

# Failure hook type: called with (request, thesis, revision) after revision
# is staged and flushed, before CAS commit. Default is no-op.
FailureHook = Callable[[LifecycleTransitionRequest, ThesisModel, ThesisRevisionModel], None]


def _noop_failure_hook(request: LifecycleTransitionRequest,
                        thesis: ThesisModel,
                        revision: ThesisRevisionModel) -> None:
    """Production default — no failure injection."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# Transactional lifecycle service
# ═══════════════════════════════════════════════════════════════════════════════

class TransactionalLifecycleService:
    """Production lifecycle service backed by SQLAlchemy.

    One transition creates an immutable ThesisRevision and CAS-updates
    the current ThesisProjection in a single transaction.
    """

    def __init__(
        self,
        session_factory: sessionmaker,
        validator: Optional[LifecycleValidator] = None,
        failure_hook: Optional[FailureHook] = None,
    ):
        self._factory = session_factory
        self._validator = validator or LifecycleValidator()
        # R12: production default is no-op; test can inject a failure hook
        self._failure_hook = failure_hook or _noop_failure_hook

    @property
    def validator(self) -> LifecycleValidator:
        return self._validator

    def transition(
        self,
        request: LifecycleTransitionRequest,
    ) -> Tuple[ThesisRevisionModel, int]:
        """Execute one lifecycle transition atomically.

        Returns (revision, new_version). The revision is freshly loaded
        so it is bound to a valid session.
        Raises IdempotentTransitionError, TransitionConflictError, ValueError.
        """
        fingerprint = compute_request_fingerprint(request)
        session: Session = self._factory()
        try:
            # 1. Resolve idempotency by fingerprint
            if request.idempotency_key:
                existing = session.query(ThesisRevisionModel).filter(
                    ThesisRevisionModel.idempotency_key == request.idempotency_key
                ).first()
                if existing is not None:
                    session.close()
                    # R11: Compare stored fingerprint with computed fingerprint
                    if existing.request_fingerprint != fingerprint:
                        raise IdempotentTransitionError(
                            f"Idempotency key '{request.idempotency_key}' "
                            f"already used with a different request. "
                            f"Stored fingerprint={existing.request_fingerprint}, "
                            f"new fingerprint={fingerprint}"
                        )
                    # Fingerprint matches — return existing result
                    rev_id = existing.id
                    fresh_session = self._factory()
                    loaded = fresh_session.query(ThesisRevisionModel).filter(
                        ThesisRevisionModel.id == rev_id
                    ).first()
                    fresh_session.close()
                    return loaded, loaded.version

            # 2. Load thesis current projection
            thesis = session.query(ThesisModel).filter(
                ThesisModel.id == request.thesis_id
            ).first()
            if thesis is None:
                session.close()
                raise TransitionConflictError(f"Thesis {request.thesis_id} not found")

            current_state = ThesisState(thesis.lifecycle_state)
            current_version = thesis.version

            # 3. Verify state
            if current_state != request.from_state:
                session.close()
                raise TransitionConflictError(
                    f"Current state {current_state.value} != expected {request.from_state.value}"
                )

            # 4. Verify version
            if current_version != request.expected_version:
                session.close()
                raise TransitionConflictError(
                    f"Current version {current_version} != expected {request.expected_version}"
                )

            # 5. Validate legal edge
            self._validator.validate_or_raise(request.from_state, request.to_state)

            # 6. Require non-empty reason
            if not request.reason.strip():
                session.close()
                raise ValueError("Transition reason must not be empty")

            # 7. Require evidence/rule refs for epistemic transitions
            if _is_epistemic_transition(request.to_state):
                if not request.evidence_refs and not request.rule_refs:
                    session.close()
                    raise ValueError(
                        f"Epistemic transition to {request.to_state.value} requires "
                        "evidence or rule references"
                    )

            # 8. Append immutable revision
            new_version = current_version + 1
            evidence_json = json.dumps(
                [r.model_dump() for r in request.evidence_refs],
                default=str,
            ) if request.evidence_refs else None
            rules_json = json.dumps(request.rule_refs) if request.rule_refs else None

            rev = ThesisRevisionModel(
                id=str(uuid4()),
                thesis_id=request.thesis_id,
                version=new_version,
                previous_version=current_version,
                revision_body=_build_revision_body(request),
                revision_outcome="transition",
                lifecycle_state=request.to_state.value,
                previous_state=request.from_state.value,
                reason=request.reason,
                idempotency_key=request.idempotency_key,
                request_fingerprint=fingerprint,
                evidence_refs_json=evidence_json,
                rule_refs_json=rules_json,
            )
            session.add(rev)
            session.flush()

            # R12: Failure injection hook (test-only, no-op in production)
            self._failure_hook(request, thesis, rev)

            # 9. CAS update current projection
            from sqlalchemy import text
            result = session.execute(
                text(
                    "UPDATE theses SET version = version + 1, updated_at = :now, "
                    "lifecycle_state = :new_state "
                    "WHERE id = :id AND version = :expected_version"
                ),
                {
                    "id": request.thesis_id,
                    "expected_version": current_version,
                    "now": datetime.now(timezone.utc),
                    "new_state": request.to_state.value,
                },
            )
            if result.rowcount == 0:
                session.rollback()
                session.close()
                raise TransitionConflictError(
                    f"CAS failed for thesis {request.thesis_id}: "
                    f"expected version {current_version}"
                )

            # 10. Commit atomically
            session.commit()
            rev_id = rev.id
            session.close()

            fresh_session = self._factory()
            loaded_rev = fresh_session.query(ThesisRevisionModel).filter(
                ThesisRevisionModel.id == rev_id
            ).first()
            fresh_session.close()
            return loaded_rev, new_version

        except (ValueError, TransitionConflictError, IdempotentTransitionError):
            session.rollback()
            session.close()
            raise
        except Exception:
            session.rollback()
            session.close()
            raise


def _build_revision_body(request: LifecycleTransitionRequest) -> str:
    refs = f" evidence_refs={len(request.evidence_refs)}" if request.evidence_refs else ""
    rules = f" rule_refs={len(request.rule_refs)}" if request.rule_refs else ""
    return (
        f"Transition: {request.from_state.value} -> {request.to_state.value}. "
        f"Reason: {request.reason}.{refs}{rules}"
    )
