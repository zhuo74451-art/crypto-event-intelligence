"""Finite checkpointed acquisition for the historical data factory.

D04/P03: Finite acquisition with explicit source, range, limit, checkpoint
and stop behavior. No daemon, cron or hidden loop.
"""

from __future__ import annotations

import dataclasses
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
from market_radar.cognition_v2.data_factory.checkpoints import AtomicCheckpointWriter


def _serialize_record(r: RawIntakeRecord) -> dict:
    """Convert a RawIntakeRecord to a JSON-serializable dict."""
    d = dataclasses.asdict(r)
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


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

    Output is committed durably BEFORE checkpoint advancement.
    Deduplicates by deterministic intake_id.
    Detects cyclic page tokens.
    """

    def __init__(
        self,
        adapter: AcquisitionAdapter,
        checkpoint_dir: str = ".checkpoints",
        output_dir: str = ".output",
    ):
        self._adapter = adapter
        self._checkpoint_dir = checkpoint_dir
        self._writer = AtomicCheckpointWriter(output_dir)
        self._seen_intake_ids: set = set()

    def _checkpoint_path(self, run_id: str) -> str:
        os.makedirs(self._checkpoint_dir, exist_ok=True)
        return os.path.join(self._checkpoint_dir, f"{run_id}.json")

    def _save_checkpoint(self, cp: AcquisitionCheckpoint, output_path: str) -> None:
        """Save checkpoint atomically (output must already be committed)."""
        cp_data = {
            "run_id": cp.run_id,
            "request_fingerprint": cp.request_fingerprint,
            "completed_pages": cp.completed_pages,
            "last_page_token": cp.last_page_token,
            "total_records_so_far": cp.total_records_so_far,
            "total_requests_so_far": cp.total_requests_so_far,
            "failed_requests_so_far": cp.failed_requests_so_far,
            "checkpointed_at": cp.checkpointed_at.isoformat(),
            "output_path": output_path,
            "schema_version": cp.schema_version,
        }
        self._writer.write_checkpoint(cp_data, self._checkpoint_path(cp.run_id))

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
        seen_tokens: set = set()

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

        output_path = self._writer.write_output(request.run_id, [])

        try:
            while True:
                # HARD CEILING: slice to min of record_limit and max_record_budget
                ceiling = min(
                    request.record_limit - request.total_records,
                    request.max_record_budget - request.total_records,
                )
                if ceiling <= 0:
                    if request.total_records >= request.max_record_budget:
                        raise AcquisitionBudgetExceeded(
                            f"Record budget ({request.max_record_budget}) exceeded"
                        )
                    break
                if request.total_requests >= request.max_request_budget:
                    raise AcquisitionBudgetExceeded(
                        f"Request budget ({request.max_request_budget}) exceeded"
                    )

                page_num = max(completed_pages) + 1 if completed_pages else 1

                if page_token in seen_tokens and page_token is not None:
                    raise RuntimeError(
                        f"Cyclic page token detected: {page_token}"
                    )
                if page_token is not None:
                    seen_tokens.add(page_token)

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

                page_records = page_records[:ceiling]

                new_records = []
                for r in page_records:
                    if r.intake_id not in self._seen_intake_ids:
                        self._seen_intake_ids.add(r.intake_id)
                        new_records.append(r)

                records.extend(new_records)
                request.total_records += len(new_records)
                completed_pages.append(page_num)

                record_dicts = [_serialize_record(r) for r in records]
                output_path = self._writer.write_output(request.run_id, record_dicts)

                cp = AcquisitionCheckpoint(
                    run_id=request.run_id,
                    request_fingerprint=request.request_fingerprint(),
                    completed_pages=list(completed_pages),
                    last_page_token=page_token,
                    total_records_so_far=request.total_records,
                    total_requests_so_far=request.total_requests,
                    failed_requests_so_far=request.failed_requests,
                )
                self._save_checkpoint(cp, output_path)

                if request.total_records >= request.record_limit:
                    break
                if page_token is None or not page_records:
                    break

            request.status = AcquisitionStatus.COMPLETED

        except AcquisitionBudgetExceeded:
            request.status = AcquisitionStatus.BUDGET_EXCEEDED
        except Exception as e:
            request.status = AcquisitionStatus.FAILED
            request.error_message = str(e)
        finally:
            request.completed_at = datetime.now(timezone.utc)

        cp = AcquisitionCheckpoint(
            run_id=request.run_id,
            request_fingerprint=request.request_fingerprint(),
            completed_pages=list(completed_pages),
            last_page_token=page_token,
            total_records_so_far=request.total_records,
            total_requests_so_far=request.total_requests,
            failed_requests_so_far=request.failed_requests,
        )
        self._save_checkpoint(cp, output_path)

        return records, request, cp
