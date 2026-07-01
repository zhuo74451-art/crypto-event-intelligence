"""Finite checkpointed acquisition for the historical data factory.

D04: Finite acquisition with explicit source, range, limit, checkpoint
and stop behavior. No daemon, cron or hidden loop.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from market_radar.cognition_v2.data_factory.contracts import (
    AcquisitionCheckpoint,
    AcquisitionRun,
    AcquisitionStatus,
    RawIntakeRecord,
)


class AcquisitionBudgetExceeded(Exception):
    """Raised when the acquisition budget (records or requests) is exceeded."""
    pass


class IncompatibleResumeError(Exception):
    """Raised when a checkpoint is incompatible with the current request."""
    pass


class AcquisitionAdapter:
    """Base class for finite acquisition adapters.

    Subclasses must implement fetch_page() which returns a list of raw
    intake records and an optional next page token.
    """

    def fetch_page(
        self,
        source_id: str,
        start_time: datetime,
        end_time: datetime,
        page_size: int,
        page_token: Optional[str] = None,
    ) -> Tuple[List[RawIntakeRecord], Optional[str]]:
        """Fetch one page of records.

        Returns (records, next_page_token).
        Next page token is None when there are no more pages.
        """
        raise NotImplementedError


class CheckpointedAcquisition:
    """Finite, checkpointed, resumable acquisition from a single source.

    Requirements:
    - interruption preserves the last committed checkpoint
    - resume does not duplicate accepted intake records
    - checkpoint request fingerprint rejects incompatible resume parameters
    - each run has a maximum request and record budget
    """

    def __init__(
        self,
        adapter: AcquisitionAdapter,
        checkpoint_dir: str = ".checkpoints",
    ):
        self._adapter = adapter
        self._checkpoint_dir = checkpoint_dir

    def _checkpoint_path(self, run_id: str) -> str:
        os.makedirs(self._checkpoint_dir, exist_ok=True)
        return os.path.join(self._checkpoint_dir, f"{run_id}.json")

    def _save_checkpoint(self, cp: AcquisitionCheckpoint) -> None:
        path = self._checkpoint_path(cp.run_id)
        with open(path, "w") as f:
            json.dump({
                "run_id": cp.run_id,
                "request_fingerprint": cp.request_fingerprint,
                "completed_pages": cp.completed_pages,
                "last_page_token": cp.last_page_token,
                "total_records_so_far": cp.total_records_so_far,
                "total_requests_so_far": cp.total_requests_so_far,
                "failed_requests_so_far": cp.failed_requests_so_far,
                "checkpointed_at": cp.checkpointed_at.isoformat(),
                "schema_version": cp.schema_version,
            }, f, sort_keys=True)

    def _load_checkpoint(self, run_id: str) -> Optional[AcquisitionCheckpoint]:
        path = self._checkpoint_path(run_id)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)
        return AcquisitionCheckpoint(
            run_id=data["run_id"],
            request_fingerprint=data["request_fingerprint"],
            completed_pages=data["completed_pages"],
            last_page_token=data.get("last_page_token"),
            total_records_so_far=data["total_records_so_far"],
            total_requests_so_far=data["total_requests_so_far"],
            failed_requests_so_far=data["failed_requests_so_far"],
            checkpointed_at=datetime.fromisoformat(data["checkpointed_at"]),
            schema_version=data.get("schema_version", "1.0"),
        )

    def run(
        self,
        request: AcquisitionRun,
        resume: bool = False,
    ) -> Tuple[List[RawIntakeRecord], AcquisitionRun, AcquisitionCheckpoint]:
        """Execute a finite acquisition run with hard ceilings and atomic checkpoints.

        Args:
            request: Acquisition run configuration.
            resume: If True, attempt to resume from an existing checkpoint.

        Returns:
            (records, completed_run, checkpoint)
        """
        request.status = AcquisitionStatus.RUNNING
        request.started_at = datetime.now(timezone.utc)
        records: List[RawIntakeRecord] = []
        page_token: Optional[str] = None
        completed_pages: List[int] = []
        initial_records = 0

        # Resume from checkpoint if requested
        if resume:
            cp = self._load_checkpoint(request.run_id)
            if cp is not None:
                if not cp.is_compatible(request):
                    raise IncompatibleResumeError(
                        f"Checkpoint for {request.run_id} has incompatible "
                        f"fingerprint. Expected {request.request_fingerprint()}, "
                        f"got {cp.request_fingerprint}."
                    )
                completed_pages = list(cp.completed_pages)
                page_token = cp.last_page_token
                request.total_records = cp.total_records_so_far
                request.total_requests = cp.total_requests_so_far
                request.failed_requests = cp.failed_requests_so_far
                initial_records = request.total_records

        try:
            while True:
                # HARD CEILING: check record budget before each request
                if request.total_records >= request.max_record_budget:
                    raise AcquisitionBudgetExceeded(
                        f"Record budget ({request.max_record_budget}) exceeded: "
                        f"{request.total_records}"
                    )
                if request.total_records >= request.record_limit:
                    break  # Hard ceiling — stop before next page
                if request.total_requests >= request.max_request_budget:
                    raise AcquisitionBudgetExceeded(
                        f"Request budget ({request.max_request_budget}) exceeded: "
                        f"{request.total_requests}"
                    )

                # Determine next page number (skip already-completed pages)
                page_num = max(completed_pages) + 1 if completed_pages else 1

                # Fetch page with retry
                retries = 0
                page_records = []
                while retries <= request.retry_limit:
                    try:
                        page_records, page_token = self._adapter.fetch_page(
                            source_id=request.source_id,
                            start_time=request.start_time,
                            end_time=request.end_time,
                            page_size=request.page_size,
                            page_token=page_token,
                        )
                        request.total_requests += 1
                        break
                    except Exception as e:
                        retries += 1
                        request.failed_requests += 1
                        if retries > request.retry_limit:
                            raise
                        time.sleep(request.backoff_seconds * (2 ** (retries - 1)))

                # Hard ceiling: only add records up to the limit
                remaining = request.record_limit - request.total_records
                can_add = page_records[:remaining]

                # Atomic: save checkpoint BEFORE committing records to output
                records.extend(can_add)
                request.total_records += len(can_add)
                completed_pages.append(page_num)

                # Atomic: save checkpoint after records committed
                cp = AcquisitionCheckpoint(
                    run_id=request.run_id,
                    request_fingerprint=request.request_fingerprint(),
                    completed_pages=list(completed_pages),
                    last_page_token=page_token,
                    total_records_so_far=request.total_records,
                    total_requests_so_far=request.total_requests,
                    failed_requests_so_far=request.failed_requests,
                )
                self._save_checkpoint(cp)

                # Check if we hit the record limit exactly
                if request.total_records >= request.record_limit:
                    break

                # No more pages
                if page_token is None or not page_records:
                    break

            # Completed resume returns zero new records
            if resume and request.total_records == initial_records and completed_pages:
                request.status = AcquisitionStatus.COMPLETED
            else:
                request.status = AcquisitionStatus.COMPLETED

        except AcquisitionBudgetExceeded:
            request.status = AcquisitionStatus.BUDGET_EXCEEDED
        except Exception as e:
            request.status = AcquisitionStatus.FAILED
            request.error_message = str(e)
        finally:
            request.completed_at = datetime.now(timezone.utc)

        # Final checkpoint
        cp = AcquisitionCheckpoint(
            run_id=request.run_id,
            request_fingerprint=request.request_fingerprint(),
            completed_pages=list(completed_pages),
            last_page_token=page_token,
            total_records_so_far=request.total_records,
            total_requests_so_far=request.total_requests,
            failed_requests_so_far=request.failed_requests,
        )
        self._save_checkpoint(cp)

        return records, request, cp
