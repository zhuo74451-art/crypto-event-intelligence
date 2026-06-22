"""
Failure Registry — brings Lane D failed experiments into the retrievable research layer.

Each failure is linked to:
- strategy version
- dataset
- time split
- failure reason
- affected regimes
- affected event families
- source claims
- candidate implications
"""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fid(content: str) -> str:
    h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16].upper()
    return f"FL-{h}"


@dataclass
class ResearchFailureRecord:
    strategy_version: str
    dataset_label: str
    time_split: str
    failure_reason: str

    affected_regimes: list = field(default_factory=list)
    affected_event_families: list = field(default_factory=list)
    source_claim_ids: list = field(default_factory=list)
    candidate_ids: list = field(default_factory=list)
    source_lane_d_experiment_id: Optional[str] = None

    notes: Optional[str] = None
    failure_id: Optional[str] = None
    created_at_utc: Optional[str] = None

    def __post_init__(self):
        if self.failure_id is None:
            content = f"{self.strategy_version}::{self.dataset_label}::{self.time_split}::{self.failure_reason}"
            self.failure_id = _fid(content)
        if self.created_at_utc is None:
            self.created_at_utc = _utc_now()

    def to_dict(self) -> dict:
        return asdict(self)


class FailureRegistry:
    """Registry for failed experiments in the research cognition layer."""

    def __init__(self):
        self._records: dict[str, ResearchFailureRecord] = {}

    def add_failure(self, record: ResearchFailureRecord) -> str:
        if record.failure_id in self._records:
            return record.failure_id
        self._records[record.failure_id] = record
        return record.failure_id

    def get_failure(self, failure_id: str) -> Optional[ResearchFailureRecord]:
        return self._records.get(failure_id)

    def get_all_failures(self) -> list:
        return list(self._records.values())

    def count(self) -> int:
        return len(self._records)

    def export_jsonl(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            for rec in self._records.values():
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
