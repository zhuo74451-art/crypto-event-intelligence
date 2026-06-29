"""Source & Evidence Pilot V1 — minimal source contracts.

All dataclasses are lightweight, serialisable, and free of third-party
dependencies.  Every timestamp is zone-aware ISO 8601.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ── Enums ────────────────────────────────────────────────────────────────────


class SourceStatus(str, Enum):
    """Canonical health states for an acquisition source."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    SCHEMA_INVALID = "schema_invalid"
    CONFIGURATION_REQUIRED = "configuration_required"


class SourceCategory(str, Enum):
    """High-level category for the subject domain."""

    REGULATORY = "regulatory"
    LEGISLATIVE = "legislative"
    MACRO = "macro"
    SOFTWARE_RELEASE = "software_release"
    SECURITY = "security"
    MARKET_DATA = "market_data"
    CHAIN_DATA = "chain_data"
    RESEARCH = "research"


class Transport(str, Enum):
    HTTP_GET = "http_get"
    HTTP_POST = "http_post"
    HTTPS_GET = "https_get"
    HTTPS_POST = "https_post"
    FILE = "file"
    FIXTURE = "fixture"


class AuthMode(str, Enum):
    NONE = "none"
    HEADER = "header"
    QUERY_PARAM = "query_param"
    ENV_TOKEN = "env_token"
    USER_AGENT = "user_agent"


# ── Contracts ────────────────────────────────────────────────────────────────


@dataclass
class SourceContract:
    """Immutable contract that defines *how* to acquire a source.

    Every source in the Pilot must have one of these.  It is the single
    source of truth for identity, transport, and constraints.
    """

    source_id: str
    display_name: str
    category: SourceCategory
    authority: str
    primary_url: str
    fallback_urls: List[str] = field(default_factory=list)
    transport: Transport = Transport.HTTPS_GET
    content_type: str = ""
    auth_mode: AuthMode = AuthMode.NONE
    timeout_seconds: int = 15
    max_response_bytes: int = 5 * 1024 * 1024  # 5 MiB
    parser_version: str = "1"
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SourceContract:
        # Enums are stored as strings; reconstruct them.
        if "category" in data and isinstance(data["category"], str):
            data["category"] = SourceCategory(data["category"])
        if "transport" in data and isinstance(data["transport"], str):
            data["transport"] = Transport(data["transport"])
        if "auth_mode" in data and isinstance(data["auth_mode"], str):
            data["auth_mode"] = AuthMode(data["auth_mode"])
        return cls(**data)


@dataclass
class FetchMetadata:
    """What was actually requested and what came back (wire-level)."""

    source_id: str
    attempted_urls: List[str] = field(default_factory=list)
    selected_url: str = ""
    http_status: int = 0
    content_type: str = ""
    bytes_received: int = 0
    latency_ms: float = 0.0
    retrieved_at: str = ""  # ISO 8601 with timezone
    content_sha256: str = ""
    fallback_used: bool = False
    error_code: str = ""
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items()}


@dataclass
class SourceHealth:
    """Health snapshot for one acquisition attempt."""

    source_id: str
    status: SourceStatus = SourceStatus.UNAVAILABLE
    attempted_urls: List[str] = field(default_factory=list)
    selected_url: str = ""
    http_status: int = 0
    content_type: str = ""
    bytes_received: int = 0
    latency_ms: float = 0.0
    retrieved_at: str = ""  # ISO 8601 with timezone
    content_sha256: str = ""
    fallback_used: bool = False
    error_code: str = ""
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_metadata(
        cls, meta: FetchMetadata, status: SourceStatus
    ) -> SourceHealth:
        return cls(
            source_id=meta.source_id,
            status=status,
            attempted_urls=meta.attempted_urls,
            selected_url=meta.selected_url,
            http_status=meta.http_status,
            content_type=meta.content_type,
            bytes_received=meta.bytes_received,
            latency_ms=meta.latency_ms,
            retrieved_at=meta.retrieved_at,
            content_sha256=meta.content_sha256,
            fallback_used=meta.fallback_used,
            error_code=meta.error_code,
            error_message=meta.error_message,
        )


@dataclass
class RawEvidenceArtifact:
    """A reference to saved raw evidence on disk.

    The actual bytes are written to the output directory *before* this
    object is created, so the path and hash can be verified independently.
    """

    source_id: str
    relative_path: str  # relative to run output root
    bytes_written: int
    content_sha256: str
    content_type: str
    retrieved_at: str  # ISO 8601

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ObservationStub:
    """Lightweight observation stub produced by acquisition adapters.

    This is later converted to a full ``market_radar.shared.models.Observation``
    by the pilot runner so that the existing pipeline can consume it without
    changes to the old model.
    """

    observation_id: str
    source_id: str
    title: str
    description: str
    event_time: str  # ISO 8601
    observed_at: str  # ISO 8601
    raw_provenance: Dict[str, Any] = field(default_factory=dict)
    affected_assets: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AcquisitionResult:
    """Complete output of one source acquisition."""

    source_id: str
    contract: SourceContract
    health: SourceHealth
    fetch_metadata: FetchMetadata
    artifact: RawEvidenceArtifact
    observations: List[ObservationStub] = field(default_factory=list)
    raw_bytes: Optional[bytes] = None
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "contract": self.contract.to_dict(),
            "health": self.health.to_dict(),
            "fetch_metadata": self.fetch_metadata.to_dict(),
            "artifact": self.artifact.to_dict(),
            "observations": [o.to_dict() for o in self.observations],
            "errors": self.errors,
        }


# ── Helpers ──────────────────────────────────────────────────────────────────


def utc_now() -> str:
    """Return current UTC time as ISO 8601 string with timezone."""
    return datetime.now(timezone.utc).isoformat()


def sha256_of_bytes(data: bytes) -> str:
    """Return lowercase hex SHA-256 of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def deterministic_observation_id(
    source_id: str,
    record_key: str,
    event_time: str,
) -> str:
    """Deterministic ID so replay produces identical IDs."""
    raw = f"{source_id}:{record_key}:{event_time}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]
