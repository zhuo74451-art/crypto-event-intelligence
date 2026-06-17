"""Operator Run Manifest — standardized output record for every operator run.

Same config produces same config_hash. No full content, no db_path, no env vars.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class OperatorManifest:
    """Standardized manifest for an operator run.

    Paths are sanitised. No full content, no db_path, no env vars.
    """
    manifest_version: str = "1.0"
    run_id: str = ""
    parent_shadow_id: Optional[str] = None
    code_commit: str = ""
    branch: str = ""
    profile_name: str = ""
    profile_hash: str = ""
    config_hash: str = ""
    started_at: str = ""
    finished_at: str = ""
    data_mode: str = ""
    no_send: bool = True
    network_allowed: bool = False
    status: str = ""
    source_summary: dict = field(default_factory=dict)
    output_files: list[dict] = field(default_factory=list)
    cursor_before: Optional[str] = None
    cursor_after: Optional[str] = None
    error_count: int = 0
    limitations: list[str] = field(default_factory=list)
    diagnoses: list[dict] = field(default_factory=list)

    def compute_config_hash(self) -> str:
        """Deterministic hash of config fields (not run_id, not timestamps)."""
        fields = {
            "data_mode": self.data_mode,
            "no_send": self.no_send,
            "profile_name": self.profile_name,
            "profile_hash": self.profile_hash,
        }
        raw = json.dumps(fields, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["config_hash"] = self.compute_config_hash()
        return d


def build_manifest(
    run_id: str,
    profile_name: str,
    profile_hash: str,
    data_mode: str,
    no_send: bool,
    network_allowed: bool,
    status: str,
    source_summary: dict,
    output_files: list[dict],
    cursor_before: Optional[str] = None,
    cursor_after: Optional[str] = None,
    error_count: int = 0,
    parent_shadow_id: Optional[str] = None,
    limitations: Optional[list[str]] = None,
    diagnoses: Optional[list[dict]] = None,
    code_commit: str = "",
    branch: str = "",
) -> OperatorManifest:
    """Build a complete OperatorManifest from run results."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return OperatorManifest(
        manifest_version="1.0",
        run_id=run_id,
        parent_shadow_id=parent_shadow_id,
        code_commit=code_commit,
        branch=branch,
        profile_name=profile_name,
        profile_hash=profile_hash,
        started_at=now,
        finished_at=now,
        data_mode=data_mode,
        no_send=no_send,
        network_allowed=network_allowed,
        status=status,
        source_summary=source_summary,
        output_files=output_files,
        cursor_before=cursor_before,
        cursor_after=cursor_after,
        error_count=error_count,
        limitations=limitations or [],
        diagnoses=diagnoses or [],
    )


def sanitise_path(path: str) -> str:
    """Remove absolute path info, keep only basename."""
    return os.path.basename(path.replace("\\", "/").rstrip("/"))
