"""Output storage — writes run artifacts to the results directory.

All output goes to results/source_evidence_pilot/<run_id>/.
Raw evidence bytes are written before any metadata/observation files
so the SHA-256 can be independently verified.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from market_radar.acquisition.contracts import (
    AcquisitionResult,
    RawEvidenceArtifact,
)


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_raw_evidence(
    output_root: Path,
    source_id: str,
    raw_bytes: Optional[bytes],
    artifact: RawEvidenceArtifact,
) -> str:
    """Write raw response bytes to disk atomically and return the relative path.

    Uses a temporary file and os.replace() so partial writes never leave
    a corrupt file.  Returns empty string when raw_bytes is None.
    """
    if raw_bytes is None:
        return ""
    rel = artifact.relative_path
    full_path = output_root / rel
    _ensure_dir(full_path.parent)
    # Atomic write: temp file + os.replace + fsync
    tmp_path = full_path.with_suffix(full_path.suffix + ".tmp")
    with open(tmp_path, "wb") as f:
        f.write(raw_bytes)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, full_path)
    # Re-read and verify SHA-256
    actual_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    if actual_sha256 != artifact.content_sha256:
        if full_path.exists():
            full_path.unlink()
        raise RuntimeError(
            f"SHA-256 mismatch for {rel}: "
            f"declared={artifact.content_sha256} actual={actual_sha256}"
        )
    return rel


def write_fetch_metadata(output_root: Path, meta: Dict[str, Any]) -> str:
    """Write fetch metadata as JSON and return the relative path."""
    rel = f"sources/{meta['source_id']}/fetch_metadata.json"
    full_path = output_root / rel
    _ensure_dir(full_path.parent)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return rel


def write_source_health(output_root: Path, health: Dict[str, Any]) -> str:
    """Append a source health record to source_health.json."""
    rel = "source_health.json"
    full_path = output_root / rel
    # Read existing array or start new
    records: List[Dict[str, Any]] = []
    if full_path.exists():
        with open(full_path, "r", encoding="utf-8") as f:
            try:
                records = json.load(f)
            except json.JSONDecodeError:
                records = []
    records.append(health)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    return rel


def write_observations(
    output_root: Path,
    observations: list[Any],
) -> str:
    """Append observations to observations.jsonl.

    Accepts any object with a to_dict() or as_dict() method.
    """
    rel = "observations.jsonl"
    full_path = output_root / rel
    with open(full_path, "a", encoding="utf-8") as f:
        for obs in observations:
            if hasattr(obs, "to_dict"):
                d = obs.to_dict()
            elif hasattr(obs, "as_dict"):
                d = obs.as_dict()
            else:
                d = dict(obs)
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    return rel


def write_evidence_manifest(
    output_root: Path,
    entries: List[Dict[str, Any]],
) -> str:
    """Write evidence manifest entries to evidence_manifest.jsonl."""
    rel = "evidence_manifest.jsonl"
    full_path = output_root / rel
    with open(full_path, "a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return rel


def write_run_manifest(
    output_root: Path,
    run_id: str,
    sources: List[str],
    started_at: str,
    completed_at: str,
    status: str,
) -> str:
    """Write run_manifest.json."""
    rel = "run_manifest.json"
    manifest = {
        "run_id": run_id,
        "sources": sources,
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
    }
    full_path = output_root / rel
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    return rel


def write_telemetry(
    output_root: Path,
    event: str,
    payload: Dict[str, Any],
) -> str:
    """Append a telemetry event to RUN_TELEMETRY.jsonl."""
    rel = "RUN_TELEMETRY.jsonl"
    full_path = output_root / rel
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **payload,
    }
    with open(full_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return rel
