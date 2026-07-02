"""Finite checkpointed acquisition for the historical data factory.

D04/Q02: Finite acquisition with persistent output, deduplication,
atomic checkpoints and safe resume. Never truncates committed output.
"""

from __future__ import annotations

import hashlib
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


def _output_sha256(output_path: str) -> str:
    """Compute SHA-256 of an output file."""
    if not os.path.exists(output_path):
        return ""
    h = hashlib.sha256()
    with open(output_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _output_byte_size(output_path: str) -> int:
    """Get byte size of an output file."""
    if not os.path.exists(output_path):
        return 0
    return os.path.getsize(output_path)


class CheckpointedAcquisition:
    """Finite, checkpointed, resumable acquisition.

    - Loads existing output before writing; never truncates committed data.
    - Output committed BEFORE checkpoint advancement.
    - Deduplicates by deterministic intake_id.
    - Verifies output SHA-256 and byte size on resume.
    - Rejects adapter/parser version mismatch on resume.
    """

    CHECKPOINT_SCHEMA_VERSION = "2.0"

    def __init__(
        self,
        adapter: AcquisitionAdapter,
        checkpoint_dir: str = ".checkpoints",
        output_dir: Optional[str] = None,
        adapter_version: str = "1.0",
        parser_version: str = "1.0",
    ):
        self._adapter = adapter
        self._checkpoint_dir = checkpoint_dir
        self._writer = AtomicCheckpointWriter(output_dir or checkpoint_dir)
        self._adapter_version = adapter_version
        self._parser_version = parser_version

    def _completion_reason(self, request: AcquisitionRun) -> str:
        if request.status == AcquisitionStatus.FAILED:
            return "FAILED"
        if request.error_message:
            return "FAILED"
        if request.status == AcquisitionStatus.BUDGET_EXCEEDED:
            check = request.max_record_budget - request.total_records
            if check <= 0:
                return "RECORD_BUDGET"
            return "REQUEST_BUDGET"
        if request.total_records >= request.record_limit:
            return "RECORD_LIMIT"
        return "SOURCE_EXHAUSTED"

    def _checkpoint_path(self, run_id: str) -> str:
        os.makedirs(self._checkpoint_dir, exist_ok=True)
        return os.path.join(self._checkpoint_dir, f"{run_id}.json")

    def _load_checkpoint(self, run_id: str) -> Optional[dict]:
        path = self._checkpoint_path(run_id)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f)

    def _build_checkpoint_data(
        self, request: AcquisitionRun, completed_pages: list,
        page_token, output_path: str,
    ) -> dict:
        return {
            "run_id": request.run_id,
            "request_fingerprint": request.request_fingerprint(),
            "completed_pages": list(completed_pages),
            "last_page_token": page_token,
            "total_records_so_far": request.total_records,
            "total_requests_so_far": request.total_requests,
            "failed_requests_so_far": request.failed_requests,
            "status": request.status.value,
            "completion_reason": self._completion_reason(request),
            "output_sha256": _output_sha256(output_path),
            "output_byte_size": _output_byte_size(output_path),
            "adapter_version": self._adapter_version,
            "parser_version": self._parser_version,
            "checkpoint_schema_version": self.CHECKPOINT_SCHEMA_VERSION,
            "output_path": output_path,
        }

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
                # Verify adapter and parser version
                cp_av = cp_data.get("adapter_version", "1.0")
                cp_pv = cp_data.get("parser_version", "1.0")
                if cp_av != self._adapter_version or cp_pv != self._parser_version:
                    raise IncompatibleResumeError(
                        f"Adapter/parser version mismatch: "
                        f"checkpoint has adapter={cp_av} parser={cp_pv}, "
                        f"current has adapter={self._adapter_version} "
                        f"parser={self._parser_version}"
                    )
                # Load committed output first
                records, seen_ids = _load_committed_records(output_path)
                initial_count = len(records)
                request.total_records = cp_data["total_records_so_far"]
                request.total_requests = cp_data["total_requests_so_far"]
                request.failed_requests = cp_data["failed_requests_so_far"]
                completed_pages = list(cp_data.get("completed_pages", []))
                page_token = cp_data.get("last_page_token")

                # Verify output SHA-256 and byte size
                cp_sha = cp_data.get("output_sha256", "")
                cp_size = cp_data.get("output_byte_size", 0)
                actual_sha = _output_sha256(output_path)
                actual_size = _output_byte_size(output_path)
                if cp_sha and cp_sha != actual_sha:
                    raise OutputCheckpointMismatchError(
                        f"Output SHA-256 mismatch: checkpoint={cp_sha}, "
                        f"actual={actual_sha}"
                    )
                if cp_size and cp_size != actual_size:
                    raise OutputCheckpointMismatchError(
                        f"Output size mismatch: checkpoint={cp_size}, "
                        f"actual={actual_size}"
                    )
                if len(records) != request.total_records:
                    raise OutputCheckpointMismatchError(
                        f"Output has {len(records)} records but checkpoint "
                        f"claims {request.total_records}"
                    )

                # Terminal completion — return committed state
                if cp_data.get("status") in (
                    AcquisitionStatus.COMPLETED.value, "COMPLETED"
                ):
                    request.status = AcquisitionStatus.COMPLETED
                    request.completed_at = datetime.now(timezone.utc)
                    # Copy completion reason
                    request.error_message = cp_data.get("completion_reason", "")
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
                cp_data_out = self._build_checkpoint_data(
                    request, completed_pages, page_token, output_path
                )
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
        cp_data_final = self._build_checkpoint_data(
            request, completed_pages, page_token, output_path
        )
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
