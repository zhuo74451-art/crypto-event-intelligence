"""Minimal Durable-Review Runtime (Experiment D).

Provides a lightweight in-process runtime that persists reviews, supports
idempotent creation, atomic claiming, cancellation/resume, and file-based
checkpoint recovery — all without an external database.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional


# ── Domain types ────────────────────────────────────────────────────────────


class ReviewStatus(str, Enum):
    """Possible states of a review in the runtime."""

    PENDING = "pending"
    CLAIMED = "claimed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass
class Review:
    """A single review tracked by the runtime."""

    review_id: str
    idempotency_key: str
    status: ReviewStatus = ReviewStatus.PENDING
    payload: dict = field(default_factory=dict)
    claimed_by: Optional[str] = None


# ── Custom exceptions ──────────────────────────────────────────────────────


class DuplicateIdempotencyKeyError(ValueError):
    """Raised when persist is called with an idempotency key already on file."""


class ReviewNotClaimableError(RuntimeError):
    """Raised when a review cannot be claimed (not in PENDING state)."""


class ReviewNotFoundError(KeyError):
    """Raised when a review_id is unknown."""


# ── Runtime ────────────────────────────────────────────────────────────────


class MinimalReviewRuntime:
    """A minimal durable-review runtime with file-based checkpoint recovery.

    All public mutating methods are thread-safe.  When a *checkpoint_path* is
    provided, state is automatically persisted to that file after each write
    operation so the runtime can resume after a crash.
    """

    def __init__(self, checkpoint_path: Optional[str] = None) -> None:
        self._reviews: dict[str, Review] = {}
        self._idempotency_keys: set[str] = set()
        self._lock = threading.Lock()
        self._checkpoint_path = Path(checkpoint_path) if checkpoint_path else None
        self._load_checkpoint()

    # ── public query API ─────────────────────────────────────────────────

    def get_review(self, review_id: str) -> Review:
        """Return the review with *review_id* or raise ReviewNotFoundError."""
        with self._lock:
            if review_id not in self._reviews:
                raise ReviewNotFoundError(review_id)
            return self._reviews[review_id]

    def list_reviews(self, status: Optional[ReviewStatus] = None) -> list[Review]:
        """Return all reviews, optionally filtered by *status*."""
        with self._lock:
            reviews = list(self._reviews.values())
        if status is not None:
            reviews = [r for r in reviews if r.status == status]
        return reviews

    def has_idempotency_key(self, key: str) -> bool:
        """Return True if *key* has already been used."""
        with self._lock:
            return key in self._idempotency_keys

    # ── public mutation API ──────────────────────────────────────────────

    def persist_review(
        self,
        review_id: str,
        idempotency_key: str,
        payload: Optional[dict] = None,
    ) -> Review:
        """Persist a new review.

        Raises DuplicateIdempotencyKeyError if *idempotency_key* is already
        known.
        """
        with self._lock:
            if idempotency_key in self._idempotency_keys:
                raise DuplicateIdempotencyKeyError(
                    f"Idempotency key {idempotency_key!r} already exists"
                )
            review = Review(
                review_id=review_id,
                idempotency_key=idempotency_key,
                payload=payload or {},
            )
            self._reviews[review_id] = review
            self._idempotency_keys.add(idempotency_key)
        self._write_checkpoint()
        return review

    def claim_review(self, review_id: str, worker: str = "default") -> Review:
        """Atomically claim a PENDING review for *worker*.

        Raises ReviewNotClaimableError if the review is not PENDING.
        """
        with self._lock:
            review = self._reviews.get(review_id)
            if review is None:
                raise ReviewNotFoundError(review_id)
            if review.status is not ReviewStatus.PENDING:
                raise ReviewNotClaimableError(
                    f"Review {review_id!r} is {review.status.value}, not pending"
                )
            review.status = ReviewStatus.CLAIMED
            review.claimed_by = worker
        self._write_checkpoint()
        return review

    def cancel_review(self, review_id: str) -> Review:
        """Cancel a review (set status to CANCELLED).

        Only PENDING or CLAIMED reviews may be cancelled.
        """
        with self._lock:
            review = self._reviews.get(review_id)
            if review is None:
                raise ReviewNotFoundError(review_id)
            if review.status not in (ReviewStatus.PENDING, ReviewStatus.CLAIMED):
                raise RuntimeError(
                    f"Cannot cancel review {review_id!r} "
                    f"in status {review.status.value}"
                )
            review.status = ReviewStatus.CANCELLED
            review.claimed_by = None
        self._write_checkpoint()
        return review

    def resume_review(self, review_id: str) -> Review:
        """Resume a CANCELLED review back to PENDING."""
        with self._lock:
            review = self._reviews.get(review_id)
            if review is None:
                raise ReviewNotFoundError(review_id)
            if review.status is not ReviewStatus.CANCELLED:
                raise RuntimeError(
                    f"Cannot resume review {review_id!r} "
                    f"in status {review.status.value}"
                )
            review.status = ReviewStatus.PENDING
            review.claimed_by = None
        self._write_checkpoint()
        return review

    def complete_review(self, review_id: str) -> Review:
        """Mark a CLAIMED review as COMPLETED."""
        with self._lock:
            review = self._reviews.get(review_id)
            if review is None:
                raise ReviewNotFoundError(review_id)
            if review.status is not ReviewStatus.CLAIMED:
                raise RuntimeError(
                    f"Cannot complete review {review_id!r} "
                    f"in status {review.status.value}"
                )
            review.status = ReviewStatus.COMPLETED
        self._write_checkpoint()
        return review

    # ── checkpoint support ───────────────────────────────────────────────

    def _checkpoint_data(self) -> dict:
        """Return serialisable checkpoint state."""
        with self._lock:
            return {
                "reviews": {
                    rid: asdict(r) for rid, r in self._reviews.items()
                },
                "idempotency_keys": sorted(self._idempotency_keys),
            }

    def _write_checkpoint(self) -> None:
        """Synchronously flush current state to the checkpoint file."""
        if self._checkpoint_path is None:
            return
        with self._checkpoint_lock:
            data = self._checkpoint_data()
            tmp = str(self._checkpoint_path) + ".tmp"
            with open(tmp, "w") as f:
                json.dump(data, f, default=str)
            os.replace(tmp, self._checkpoint_path)

    def _load_checkpoint(self) -> None:
        """Load state from the checkpoint file if it exists."""
        if self._checkpoint_path is None or not self._checkpoint_path.exists():
            return
        with self._checkpoint_path.open() as f:
            data = json.load(f)
        with self._lock:
            self._reviews.clear()
            self._idempotency_keys.clear()
            for rid, rd in data.get("reviews", {}).items():
                rd["status"] = ReviewStatus(rd["status"])
                self._reviews[rid] = Review(**rd)
            self._idempotency_keys.update(data.get("idempotency_keys", []))

    def close(self) -> None:
        """Flush checkpoint and release resources."""
        self._write_checkpoint()
