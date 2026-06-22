"""
Integration Contracts — Typed structures for the integration layer (Lane E).
"""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


VALID_GATE_NAMES = [
    "lock_hash_verification",
    "contract_compatibility",
    "single_lane_tests",
    "cross_lane_interfaces",
    "end_to_end_real_sample",
    "kernel_seal_regression",
    "full_repository_matrix",
]

VALID_CHECK_NAMES = [
    "producer_base_sha_matches",
    "producer_head_matches_manifest",
    "artifact_hash_matches",
    "schema_file_present",
    "schema_version_supported",
    "required_fields_present",
    "consumer_expected_fields_present",
    "timestamp_format_utc",
    "deterministic_ids_present",
    "duplicate_ids_absent",
    "point_in_time_fields_present",
    "evaluation_labels_separated_from_inputs",
    "calibration_scope_bound",
    "failed_experiments_preserved",
    "abstention_records_preserved",
    "kernel_contract_unchanged",
]

VALID_INTEGRATION_STATUSES = [
    "integration_not_started",
    "partial_producers_locked",
    "contracts_compatible",
    "end_to_end_sample_passed",
    "historical_internal_alpha",
    "blocked_by_producer",
    "blocked_by_contract",
    "blocked_by_evidence",
]


def deterministic_run_id(
    sealed_base_sha: str,
    producer_shas: dict,
    contract_versions: dict,
    pipeline_version: str,
) -> str:
    """Generate a deterministic run ID from locked inputs."""
    content = json.dumps({
        "sealed": sealed_base_sha,
        "producers": {k: v for k, v in sorted(producer_shas.items())},
        "contracts": {k: v for k, v in sorted(contract_versions.items())},
        "pipeline": pipeline_version,
    }, sort_keys=True)
    h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]
    return f"RUN-{h}"


@dataclass
class CompatibilityCheckV1:
    check_name: str
    lane: str
    passed: bool
    details: str = ""

    check_id: Optional[str] = None
    checked_at_utc: Optional[str] = None

    def __post_init__(self):
        if self.check_name not in VALID_CHECK_NAMES:
            raise ValueError(f"Invalid check name: {self.check_name}")
        if self.check_id is None:
            content = f"{self.lane}::{self.check_name}"
            h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16].upper()
            self.check_id = f"CHK-{h}"
        if self.checked_at_utc is None:
            self.checked_at_utc = _utc_now()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class IntegrationRunV1:
    sealed_base_sha: str
    producer_shas: dict
    pipeline_version: str
    contract_versions: dict

    run_id: Optional[str] = None
    status: str = "running"
    compatibility_results_path: Optional[str] = None
    pipeline_result_path: Optional[str] = None

    claim_count: int = 0
    edge_count: int = 0
    conflict_count: int = 0
    candidate_count: int = 0
    dossier_count: int = 0

    started_at_utc: Optional[str] = None
    completed_at_utc: Optional[str] = None
    resumed_from: Optional[str] = None
    idempotent_rerun: bool = False
    gate_results: Optional[dict] = None

    def __post_init__(self):
        if self.run_id is None:
            self.run_id = deterministic_run_id(
                self.sealed_base_sha,
                self.producer_shas,
                self.contract_versions,
                self.pipeline_version,
            )
        if self.started_at_utc is None:
            self.started_at_utc = _utc_now()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EndToEndResultV1:
    run_id: str
    sample_label: str
    macro_event_count: int
    market_window_count: int
    replay_result_count: int
    validation_result_count: int
    status: str = "partial"
    sample_status: str = "temporary_real_integration_sample"

    claim_count: int = 0
    edge_count: int = 0
    conflict_count: int = 0
    candidate_count: int = 0
    dossier_count: int = 0
    unresolved_references: int = 0
    failures: list = field(default_factory=list)
    completed_at_utc: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)
