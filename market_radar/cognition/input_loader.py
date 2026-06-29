"""Input loader — validates acquisition output for cognition processing."""

from __future__ import annotations
import json, hashlib
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from market_radar.cognition.contracts import SourceOrigin, sha256_id


@dataclass
class ValidatedObservation:
    observation: Any  # market_radar.shared.models.Observation
    source_origin: SourceOrigin = SourceOrigin.FIXTURE
    valid: bool = True
    rejection_reason: str = ""


@dataclass
class InputInventory:
    total_observations: int = 0
    valid_observations: int = 0
    rejected_observations: int = 0
    duplicate_ids: int = 0
    evidence_files_checked: int = 0
    evidence_hash_mismatches: int = 0
    source_origins: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


def load_observations(path: Path) -> Tuple[List[ValidatedObservation], InputInventory]:
    """Load and validate observations.jsonl."""
    from market_radar.shared.models import Observation, DataSourceType, DataQuality, ObservationStatus
    inventory = InputInventory()
    obs_list: List[ValidatedObservation] = []
    seen_ids: set = set()
    if not path.exists():
        inventory.errors.append(f"observations file not found: {path}")
        return [], inventory
    for line in path.read_text(encoding="utf-8").strip().split(chr(10)):
        if not line.strip():
            continue
        inventory.total_observations += 1
        try:
            d = json.loads(line)
            # Handle both acquisition JSONL format and direct Observation format
            if "normalized_payload" in d:
                # Direct from acquisition pipeline - rebuild as Observation
                obs = Observation(
                    observation_id=d.get("observation_id", ""),
                    source=d.get("source", ""),
                    source_type=DataSourceType(d.get("source_type", "free_public_api")),
                    observed_at=d.get("observed_at", ""),
                    event_time=d.get("event_time"),
                    affected_assets=list(d.get("affected_assets", [])),
                    normalized_payload=dict(d.get("normalized_payload", {})),
                    raw_provenance=dict(d.get("raw_provenance", {})),
                    evidence=list(d.get("evidence", [])),
                    data_quality=DataQuality(d.get("data_quality", "unverified")),
                    observation_fingerprint=d.get("observation_fingerprint", ""),
                    event_dedup_key=d.get("event_dedup_key", ""),
                    ingestion_status=ObservationStatus(d.get("ingestion_status", "raw")),
                    source_refs=list(d.get("source_refs", [])),
                    risk_notes=list(d.get("risk_notes", [])),
                )
            else:
                obs = Observation(**d)
            vo = ValidatedObservation(observation=obs, source_origin=SourceOrigin.FIXTURE)
            if obs.observation_id in seen_ids:
                inventory.duplicate_ids += 1
                vo.valid = False
                vo.rejection_reason = "duplicate_observation_id"
            seen_ids.add(obs.observation_id)
            if vo.valid:
                inventory.valid_observations += 1
            else:
                inventory.rejected_observations += 1
            obs_list.append(vo)
        except Exception as e:
            inventory.rejected_observations += 1
            inventory.errors.append(f"parse_error line {inventory.total_observations}: {e}")
    return obs_list, inventory


def load_evidence_manifest(path: Path) -> Tuple[List[Dict], List[str]]:
    """Load and validate evidence_manifest.jsonl."""
    entries: List[Dict] = []
    errors: List[str] = []
    if not path.exists():
        errors.append(f"evidence manifest not found: {path}")
        return [], errors
    for line in path.read_text(encoding="utf-8").strip().split(chr(10)):
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as e:
            errors.append(f"manifest_parse: {e}")
    return entries, errors


def verify_evidence_hash(manifest_dir: Path, entry: Dict) -> Optional[str]:
    """Verify disk SHA-256 matches manifest entry."""
    art_path = entry.get("raw_artifact_path", "")
    expected_hash = entry.get("raw_artifact_sha256", "")
    if not art_path or not expected_hash:
        return "missing_path_or_hash"
    full = manifest_dir / art_path
    if not full.exists():
        return "file_not_found: " + str(full)
    actual = hashlib.sha256(full.read_bytes()).hexdigest()
    if actual != expected_hash:
        return f"hash_mismatch: {actual} != {expected_hash}"
    return None
