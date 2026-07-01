"""Finite checkpointed acquisition for the historical data factory.

D04/Q02: Finite acquisition with persistent output, deduplication,
atomic checkpoints and safe resume. Never truncates committed output.
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
from market_radar.cognition_v2.data_factory.checkpoints import AtomicCheckpointWriter


class AcquisitionBudgetExceeded(Exception):
    """Raised when the acquisition budget (records or requests) is exceeded."""
    pass


class IncompatibleResumeError(Exception):
    """Raised when a checkpoint is incompatible with the current request."""
    pass


class OutputCheckpointMismatchError(Exception):
    """Raised when output and checkpoint disagree on committed state."""
    pass


class AcquisitionAdapter:
    """Base class for finite acquisition adapters."""
    def fetch_page(self, source_id, start_time, end_time,
                   page_size, page_token=None):
        raise NotImplementedError


def _serialize_record(r: RawIntakeRecord) -> dict:
    d = {}
    for f in ("intake_id", "source_id", "source_url", "raw_body",
              "intake_status", "parser_version", "error_message",
              "schema_version"):
        d[f] = getattr(r, f)
    d["retrieved_at"] = r.retrieved_at.isoformat()
    d["created_at"] = r.created_at.isoformat()
    return d


def _load_committed_records(output_path: str) -> Tuple[List[RawIntakeRecord], set]:
    """Load committed records from output file and return (records, intake_ids)."""
    records = []
    intake_ids = set()
    if os.path.exists(output_path):
        with open(output_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                r = RawIntakeRecord(
                    intake_id=data["intake_id"],
                    source_id=data["source_id"],
                    source_url=data.get("source_url", ""),
                    raw_body=data.get("raw_body", ""),
                    retrieved_at=datetime.fromisoformat(data["retrieved_at"]),
                    intake_status=data.get("intake_status", "raw"),
                    parser_version=data.get("parser_version", "1.0"),
                    error_message=data.get("error_message"),
                    schema_version=data.get("schema_version", "1.0"),
                    created_at=datetime.fromisoformat(
                        data.get("created_at", data["retrieved_at"])
                    ),
                )
                records.append(r)
                intake_ids.add(r.intake_id)
    return records, intake_ids


class CheckpointedAcquisition:
    """Finite, checkpointed, resumable acquisition.

    - Loads existing output before writing; never truncates committed data.
    - Output committed BEFORE checkpoint advancement.
    - Deduplicates by deterministic intake_id.
    - Detects output/checkpoint mismatches.
    """

    def __init__(
        self,
        adapter: AcquisitionAdapter,
        checkpoint_dir: str = ".checkpoints",
        output_dir: Optional[str] = None,
    ):
        self._adapter = adapter
        self._checkpoint_dir = checkpoint_dir
        self._writer = AtomicCheckpointWriter(output_dir or checkpoint_dir)

    def _checkpoint_path(self, run_id: str) -> str:
        os.makedirs(self._checkpoint_dir, exist_ok=True)
        return os.path.join(self._checkpoint_dir, f"{run_id}.json")

    def _load_checkpoint(self, run_id: str) -> Optional[dict]:
        path = self._checkpoint_path(run_id)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f)

    def run(
        self,
        request: AcquisitionRun,
        resume: bool = False,
    ) -> Tuple[List[RawIntakeRecord], AcquisitionRun, AcquisitionCheckpoint]:
        """Execute a finite acquisition run with atomic, non-truncating resume."""
        request.status = AcquisitionStatus.RUNNING
        request.started_at = datetime.now(timezone.utc)
        page_token: Optional[str] = None
        completed_pages: List[int] = []
        seen_tokens: set = set()
        output_path = self._writer._output_path(request.run_id)

        # Load existing state if resuming
        records: List[RawIntakeRecord] = []
        seen_ids: set = set()
        initial_count = 0

        if resume:
            cp_data = self._load_checkpoint(request.run_id)
            if cp_data is not None:
                if not self._check_fingerprint(cp_data, request):
                    raise IncompatibleResumeError(
                        f"Incompatible fingerprint for {request.run_id}"
                    )
                # Load committed output first
                records, seen_ids = _load_committed_records(output_path)
                initial_count = len(records)
                request.total_records = cp_data["total_records_so_far"]
                request.total_requests = cp_data["total_requests_so_far"]
                request.failed_requests = cp_data["failed_requests_so_far"]
                completed_pages = list(cp_data.get("completed_pages", []))
                page_token = cp_data.get("last_page_token")

                # Verify output count matches checkpoint
                if len(records) != request.total_records:
                    raise OutputCheckpointMismatchError(
                        f"Output has {len(records)} records but checkpoint "
                        f"claims {request.total_records}"
                    )

                # Source-exhausted or record-limit completion is terminal
                if cp_data.get("status") == AcquisitionStatus.COMPLETED.value:
                    # Load existing output and return it
                    request.status = AcquisitionStatus.COMPLETED
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
                    return records, request, cp

        try:
            while True:
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
                    raise RuntimeError(f"Cyclic page token: {page_token}")
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
                    if r.intake_id not in seen_ids:
                        seen_ids.add(r.intake_id)
                        new_records.append(r)

                records.extend(new_records)
                request.total_records += len(new_records)
                completed_pages.append(page_num)

                # Write output atomically BEFORE checkpoint
                record_dicts = [_serialize_record(r) for r in records]
                output_path = self._writer.write_output(
                    request.run_id, record_dicts
                )

                # Now checkpoint (output already durable)
                cp_data_out = {
                    "run_id": request.run_id,
                    "request_fingerprint": request.request_fingerprint(),
                    "completed_pages": list(completed_pages),
                    "last_page_token": page_token,
                    "total_records_so_far": request.total_records,
                    "total_requests_so_far": request.total_requests,
                    "failed_requests_so_far": request.failed_requests,
                    "status": AcquisitionStatus.RUNNING.value,
                    "output_path": output_path,
                }
                self._writer.write_checkpoint(
                    cp_data_out, self._checkpoint_path(request.run_id)
                )

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

        # Final checkpoint
        cp_data_final = {
            "run_id": request.run_id,
            "request_fingerprint": request.request_fingerprint(),
            "completed_pages": list(completed_pages),
            "last_page_token": page_token,
            "total_records_so_far": request.total_records,
            "total_requests_so_far": request.total_requests,
            "failed_requests_so_far": request.failed_requests,
            "status": request.status.value,
            "output_path": output_path,
        }
        self._writer.write_checkpoint(
            cp_data_final, self._checkpoint_path(request.run_id)
        )

        cp = AcquisitionCheckpoint(
            run_id=request.run_id,
            request_fingerprint=request.request_fingerprint(),
            completed_pages=list(completed_pages),
            last_page_token=page_token,
            total_records_so_far=request.total_records,
            total_requests_so_far=request.total_requests,
            failed_requests_so_far=request.failed_requests,
        )
        return records, request, cp

    @staticmethod
    def _check_fingerprint(cp_data: dict, request: AcquisitionRun) -> bool:
        expected = request.request_fingerprint()
        actual = cp_data.get("request_fingerprint", "")
        return expected == actual
