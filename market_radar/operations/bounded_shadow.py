"""Bounded Shadow Runner — finite, synchronous, stoppable, auditable, never-send.

A bounded shadow runner executes an injected one-shot callable a finite
number of times (max_runs, hard-capped at 10) in the **current process**.
It is **not** a daemon, scheduler, cron job, or background service.

Key properties
--------------
* Synchronous — the caller blocks until the shadow completes.
* Finite — max_runs has a hard upper bound of 10.
* Stoppable — checks a StopMarker before every round.
* Auditable — persists parent and child run records to SQLite.
* Never-send — the ``no_send`` flag is locked to ``True``.

Lifecycle
---------
1. Validate config.
2. Create state_dir.
3. Check StopMarker (pre-race check).
4. Acquire FileLock (single instance per state_dir).
5. Initialize SQLite schema.
6. Insert parent shadow run-history row.
7. Loop ordinal 1..max_runs.
   a. Check StopMarker.
   b. Call injected one-shot callable.
   c. Normalize result.
   d. Write child run record (insert or link_existing).
   e. Apply stop-policy rules.
   f. If not last round, call injected sleep_fn.
8. Update parent run-history row (final status).
9. Release FileLock.
10. Return BoundedShadowResult.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Protocol

from market_radar.operations.file_lock import FileLock
from market_radar.operations.run_history import (
    insert_run,
    link_existing_run_to_parent,
    update_run_finish,
)
from market_radar.operations.sqlite_schema import initialize_sqlite
from market_radar.operations.stop_marker import StopMarker

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class BoundedShadowConfig:
    """Configuration for a bounded shadow run.

    Raises ``ValueError`` on invalid values at construction time.
    """

    max_runs: int = 2
    interval_seconds: float = 0.0
    stop_on_failure: bool = True
    continue_on_degraded: bool = True
    no_send: bool = True
    state_dir: str = ""
    runner_label: str = "bounded_shadow"
    lock_name: str = "bounded_shadow.lock"
    stop_marker_name: str = "STOP"
    run_history_db_name: str = "run_history.db"
    child_history_mode: str = "insert"
    # "insert" — bounded_shadow inserts wrapper child row
    # "link_existing" — callable already wrote its row, only link

    def __post_init__(self) -> None:
        if self.max_runs is None:
            raise ValueError("max_runs must not be None")
        if not isinstance(self.max_runs, int):
            raise ValueError(f"max_runs must be an int, got {type(self.max_runs).__name__}")
        if self.max_runs < 1:
            raise ValueError(f"max_runs must be >= 1, got {self.max_runs}")
        if self.max_runs > 10:
            raise ValueError(f"max_runs must be <= 10, got {self.max_runs}")
        if self.interval_seconds < 0:
            raise ValueError(
                f"interval_seconds must be >= 0, got {self.interval_seconds}"
            )
        if self.interval_seconds > 3600:
            raise ValueError(
                f"interval_seconds must be <= 3600, got {self.interval_seconds}"
            )
        if not self.no_send:
            raise ValueError(
                "no_send must be True — bounded shadow never sends. "
                "Set no_send=True explicitly."
            )
        if not self.state_dir:
            raise ValueError("state_dir must be a non-empty path")
        if self.child_history_mode not in ("insert", "link_existing"):
            raise ValueError(
                f"child_history_mode must be 'insert' or 'link_existing', "
                f"got '{self.child_history_mode}'"
            )

    @property
    def run_history_db(self) -> Path:
        return Path(self.state_dir) / self.run_history_db_name

    @property
    def lock_path(self) -> Path:
        return Path(self.state_dir) / self.lock_name

    @property
    def stop_marker_path(self) -> Path:
        return Path(self.state_dir) / self.stop_marker_name


# ---------------------------------------------------------------------------
# Callable protocol
# ---------------------------------------------------------------------------


@dataclass
class ShadowCallableResult:
    """Standardised result from a single one-shot callable invocation."""

    child_run_id: str
    status: str  # "completed" | "degraded" | "failed"
    summary: Optional[dict[str, Any]] = None
    error: Optional[str] = None

    def __post_init__(self) -> None:
        valid = {"completed", "degraded", "failed"}
        if self.status not in valid:
            raise ValueError(
                f"invalid status '{self.status}'; must be one of {valid}"
            )
        if not self.child_run_id:
            raise ValueError("child_run_id must be non-empty")


class ShadowCallable(Protocol):
    """Protocol for a one-shot callable injected into the bounded shadow.

    The implementation MUST NOT:
    * Send messages (Telegram, X, webhook).
    * Access the network.
    * Import Integration code.
    * Start threads or background work.
    """

    def __call__(
        self,
        ordinal: int,
        shared_state_dir: str,
        no_send: bool,
        parent_shadow_run_id: str,
    ) -> ShadowCallableResult:
        ...


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


@dataclass
class BoundedShadowRunRecord:
    """Record of a single child run within a bounded shadow session."""

    ordinal: int
    child_run_id: str
    status: str  # "completed" | "degraded" | "failed"
    started_at: str
    finished_at: str
    duration_ms: float
    error: Optional[str] = None
    summary: Optional[dict[str, Any]] = None
    stopped_after_this_run: bool = False
    no_send: bool = True


# Total shadow status constants
STATUS_COMPLETED = "completed"
STATUS_DEGRADED = "degraded"
STATUS_FAILED = "failed"
STATUS_STOPPED = "stopped"


@dataclass
class BoundedShadowResult:
    """Aggregate result of a full bounded shadow session."""

    shadow_run_id: str
    started_at: str
    finished_at: str
    status: str  # "completed" | "degraded" | "failed" | "stopped"
    requested_runs: int
    attempted_runs: int = 0
    completed_runs: int = 0
    degraded_runs: int = 0
    failed_runs: int = 0
    skipped_runs: int = 0
    stopped_by_marker: bool = False
    stopped_by_failure: bool = False
    stopped_by_policy: bool = False
    lock_acquired: bool = True
    no_send: bool = True
    records: list[BoundedShadowRunRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Status determination
# ---------------------------------------------------------------------------

# Deterministic status rules (in order):
# 1. Any failed run    → "failed"
# 2. Any degraded run  → "degraded"
# 3. Stopped by marker → "stopped"
# 4. All completed     → "completed"
#
# Additionally: if result.errors contains a persistence failure the
# parent status MUST be "failed" regardless of child statuses.


def _determine_final_status(result: BoundedShadowResult) -> str:
    """Determine the final parent status from child-run counters.

    Rules (applied in order):
    1. ``result.errors`` contains persistence failure  → ``failed``
    2. ``failed_runs > 0``              → ``failed``
    3. ``degraded_runs > 0``            → ``degraded``
    4. ``stopped_by_marker``            → ``stopped``
    5. ``attempted_runs == 0``          → ``stopped`` (pre-race stop)
    6. Otherwise                        → ``completed``
    """
    # Persistence errors force failed status
    for err in result.errors:
        if _is_persistence_error(err):
            return STATUS_FAILED

    if result.failed_runs > 0:
        return STATUS_FAILED
    if result.degraded_runs > 0:
        return STATUS_DEGRADED
    if result.stopped_by_marker or result.attempted_runs == 0:
        return STATUS_STOPPED
    return STATUS_COMPLETED


def _is_persistence_error(err: str) -> bool:
    """Heuristic: does *err* describe a persistence/DB failure?"""
    keywords = (
        "child insert failed",
        "link_existing",
        "unique constraint",
        "duplicate run_id",
        "child does not exist",
        "parent does not exist",
        "link returned false",
        "db init failed",
        "parent insert failed",
        "parent update failed",
    )
    return any(kw in err.lower() for kw in keywords)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_bounded_shadow(
    config: BoundedShadowConfig,
    one_shot_callable: ShadowCallable,
    sleep_fn: Callable[[float], None] = time.sleep,
    clock_fn: Callable[[], float] = time.time,
) -> BoundedShadowResult:
    """Execute a bounded shadow session.

    Args:
        config: Validated ``BoundedShadowConfig``.
        one_shot_callable: A ``ShadowCallable``-conforming function.
        sleep_fn: Sleep function (injectable for tests).
        clock_fn: Clock function (injectable for deterministic tests).

    Returns:
        ``BoundedShadowResult`` summarising the session.
    """
    # ------------------------------------------------------------------
    # 1. Validate config
    # ------------------------------------------------------------------
    # __post_init__ already ran; re-validate no_send at runtime as defence
    if not config.no_send:
        raise ValueError("no_send must be True")

    shadow_run_id = uuid.uuid4().hex
    started_at = _ts(clock_fn)
    result = BoundedShadowResult(
        shadow_run_id=shadow_run_id,
        started_at=started_at,
        finished_at=started_at,
        status=STATUS_COMPLETED,
        requested_runs=config.max_runs,
        no_send=True,
    )

    try:
        # ------------------------------------------------------------------
        # 2. Create state_dir
        # ------------------------------------------------------------------
        state_path = Path(config.state_dir)
        state_path.mkdir(parents=True, exist_ok=True)

        # ------------------------------------------------------------------
        # 3. Check StopMarker before acquiring lock
        # ------------------------------------------------------------------
        stop_marker = StopMarker(config.stop_marker_path)
        if stop_marker.is_set:
            result.status = STATUS_STOPPED
            result.stopped_by_marker = True
            result.finished_at = _ts(clock_fn)
            return result

        # ------------------------------------------------------------------
        # 4. Acquire FileLock
        # ------------------------------------------------------------------
        lock = FileLock(config.lock_path)
        lock_err = lock.try_acquire()
        if lock_err is not None:
            result.lock_acquired = False
            result.status = STATUS_FAILED
            result.errors.append(f"lock acquisition failed: {lock_err}")
            result.finished_at = _ts(clock_fn)
            return result

        # ------------------------------------------------------------------
        # 5. Initialize SQLite schema
        # ------------------------------------------------------------------
        db_path = config.run_history_db
        try:
            initialize_sqlite(db_path)
        except Exception as e:
            result.status = STATUS_FAILED
            result.errors.append(f"db init failed: {_safe_error(e)}")
            result.finished_at = _ts(clock_fn)
            lock.release()
            return result

        # ------------------------------------------------------------------
        # 6. Insert parent shadow run-history row (run_kind=shadow_parent)
        # ------------------------------------------------------------------
        parent_config_summary = {
            "max_runs": config.max_runs,
            "interval_seconds": config.interval_seconds,
            "stop_on_failure": config.stop_on_failure,
            "continue_on_degraded": config.continue_on_degraded,
            "runner_label": config.runner_label,
            "child_history_mode": config.child_history_mode,
        }
        try:
            insert_run(
                db_path=str(db_path),
                run_id=shadow_run_id,
                runner_label=config.runner_label,
                status="started",
                summary=parent_config_summary,
                parent_run_id=None,
                run_ordinal=None,
                run_kind="shadow_parent",
            )
        except Exception as e:
            result.status = STATUS_FAILED
            result.errors.append(f"parent insert failed: {_safe_error(e)}")
            result.finished_at = _ts(clock_fn)
            lock.release()
            return result

        # ------------------------------------------------------------------
        # 7. Main loop (ordinal 1..max_runs)
        # ------------------------------------------------------------------
        ordinal = 1
        while ordinal <= config.max_runs:
            # 8. Check StopMarker before each round
            if stop_marker.is_set:
                result.stopped_by_marker = True
                break

            child_start = _ts(clock_fn)
            child_start_epoch = clock_fn()

            try:
                callable_result = one_shot_callable(
                    ordinal=ordinal,
                    shared_state_dir=config.state_dir,
                    no_send=True,
                    parent_shadow_run_id=shadow_run_id,
                )
                # Normalise — catch invalid returns
                if callable_result is None:
                    raise ValueError("callable returned None")
                child_status = callable_result.status
                child_run_id = callable_result.child_run_id
                child_error = callable_result.error
                child_summary = callable_result.summary
            except Exception as e:
                child_status = STATUS_FAILED
                child_run_id = uuid.uuid4().hex
                child_error = _safe_error(e)
                child_summary = {"error_type": type(e).__name__}

            child_end_epoch = clock_fn()
            child_finish = _ts(clock_fn)
            duration_ms = max(0.0, (child_end_epoch - child_start_epoch) * 1000.0)

            # Build child run record
            record = BoundedShadowRunRecord(
                ordinal=ordinal,
                child_run_id=child_run_id,
                status=child_status,
                started_at=child_start,
                finished_at=child_finish,
                duration_ms=duration_ms,
                error=child_error,
                summary=child_summary,
                no_send=True,
            )

            # ------------------------------------------------------------------
            # d. Write child run record (insert or link_existing)
            # ------------------------------------------------------------------
            _persist_child_record(
                config=config,
                db_path=db_path,
                shadow_run_id=shadow_run_id,
                ordinal=ordinal,
                child_run_id=child_run_id,
                child_status=child_status,
                child_error=child_error,
                child_summary=child_summary,
                result=result,
            )

            # Update counters
            result.attempted_runs += 1
            if child_status == STATUS_COMPLETED:
                result.completed_runs += 1
            elif child_status == STATUS_DEGRADED:
                result.degraded_runs += 1
            else:
                result.failed_runs += 1

            # Apply policy — stop decision
            stop_reason: Optional[str] = None
            if child_status == STATUS_FAILED and config.stop_on_failure:
                stop_reason = "stop_on_failure"
                result.stopped_by_failure = True
            elif child_status == STATUS_DEGRADED and not config.continue_on_degraded:
                stop_reason = "continue_on_degraded=False"
                result.stopped_by_policy = True

            record.stopped_after_this_run = stop_reason is not None
            result.records.append(record)

            if stop_reason is not None:
                break

            # Stop if last round
            if ordinal >= config.max_runs:
                record.stopped_after_this_run = True  # natural end
                break

            # 13. Sleep before next round (injected)
            if config.interval_seconds > 0:
                try:
                    # Check StopMarker before sleep too
                    if stop_marker.is_set:
                        result.stopped_by_marker = True
                        break
                    sleep_fn(config.interval_seconds)
                    # Check StopMarker again after sleep
                    if stop_marker.is_set:
                        result.stopped_by_marker = True
                        break
                except Exception as e:
                    result.errors.append(
                        f"sleep_fn failed after ordinal {ordinal}: {_safe_error(e)}"
                    )
                    result.failed_runs += 1 if child_status != STATUS_FAILED else 0
                    break

            ordinal += 1

        # Any runs not attempted = skipped
        result.skipped_runs = max(0, config.max_runs - result.attempted_runs)

    except Exception as e:
        # Top-level safety net
        result.status = STATUS_FAILED
        result.errors.append(f"unexpected shadow error: {_safe_error(e)}")
        result.finished_at = _ts(clock_fn)
        # Attempt lock release even on crash
        try:
            if "lock" in dir() and lock is not None:
                lock.release()
        except Exception:
            pass
        return result

    # ------------------------------------------------------------------
    # 14. Update parent run-history with final status
    # ------------------------------------------------------------------
    final_status = _determine_final_status(result)
    result.status = final_status
    result.finished_at = _ts(clock_fn)

    parent_summary_final: dict[str, Any] = {
        "config": parent_config_summary,
        "attempted_runs": result.attempted_runs,
        "completed_runs": result.completed_runs,
        "degraded_runs": result.degraded_runs,
        "failed_runs": result.failed_runs,
        "skipped_runs": result.skipped_runs,
        "stopped_by_marker": result.stopped_by_marker,
        "stopped_by_failure": result.stopped_by_failure,
        "stopped_by_policy": result.stopped_by_policy,
        "no_send": True,
        "child_records": [
            {
                "ordinal": r.ordinal,
                "child_run_id": r.child_run_id,
                "status": r.status,
            }
            for r in result.records
        ],
    }

    try:
        update_run_finish(
            db_path=str(db_path),
            run_id=shadow_run_id,
            status=final_status,
            summary=parent_summary_final,
            error=result.errors[-1] if result.errors else None,
        )
    except Exception as e:
        result.errors.append(f"parent update failed: {_safe_error(e)}")
        # Re-evaluate status after persistence failure — must downgrade to failed
        result.status = _determine_final_status(result)
        # Best-effort fallback: try once more with failed status
        try:
            update_run_finish(
                db_path=str(db_path),
                run_id=shadow_run_id,
                status=result.status,
                summary=parent_summary_final,
                error=result.errors[-1] if result.errors else None,
            )
        except Exception:
            pass  # Unable to persist — keep in-memory result for diagnostics

    # ------------------------------------------------------------------
    # 15. Release lock
    # ------------------------------------------------------------------
    try:
        lock.release()
    except Exception as e:
        result.errors.append(f"lock release failed: {_safe_error(e)}")

    return result


# ---------------------------------------------------------------------------
# Child persistence
# ---------------------------------------------------------------------------


def _persist_child_record(
    config: BoundedShadowConfig,
    db_path: Path,
    shadow_run_id: str,
    ordinal: int,
    child_run_id: str,
    child_status: str,
    child_error: Optional[str],
    child_summary: Optional[dict[str, Any]],
    result: BoundedShadowResult,
) -> None:
    """Write the child run record — either *insert* or *link_existing*.

    On failure, appends to ``result.errors``.
    """
    try:
        if config.child_history_mode == "link_existing":
            # Callable already wrote its own row — just link
            link_existing_run_to_parent(
                db_path=str(db_path),
                run_id=child_run_id,
                parent_run_id=shadow_run_id,
                run_ordinal=ordinal,
                run_kind="shadow_child",
            )
        else:
            # Default "insert" mode — write a wrapper child row
            child_summary_json = {
                "parent_shadow_run_id": shadow_run_id,
                "ordinal": ordinal,
                "no_send": True,
            }
            if child_summary:
                child_summary_json["callable_summary"] = child_summary

            insert_run(
                db_path=str(db_path),
                run_id=child_run_id,
                runner_label=f"{config.runner_label}_child",
                status=child_status,
                summary=child_summary_json,
                error=child_error,
                parent_run_id=shadow_run_id,
                run_ordinal=ordinal,
                run_kind="shadow_child",
            )
    except Exception as e:
        result.errors.append(
            f"child insert failed for ordinal {ordinal}: {_safe_error(e)}"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ts(clock_fn: Callable[[], float]) -> str:
    """ISO-8601 timestamp using the injected clock."""
    from datetime import datetime, timezone

    return datetime.fromtimestamp(clock_fn(), tz=timezone.utc).isoformat()


def _safe_error(exc: Exception) -> str:
    """Return a safe error string without leaking absolute paths or env vars."""
    msg = str(exc) or repr(exc)
    # Strip drive letters / absolute paths on Windows and POSIX
    import re

    msg = re.sub(r"[A-Za-z]:\\[^\s:,)]+", "<path>", msg)
    msg = re.sub(r"/[^\s:,)]+", "<path>", msg)
    # Truncate to 500 chars
    if len(msg) > 500:
        msg = msg[:497] + "..."
    return f"{type(exc).__name__}: {msg}"
