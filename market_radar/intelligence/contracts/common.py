"""Common base contracts for the intelligence kernel.

Provides:
- SchemaVersion for versioned objects
- DataAvailability for fields that may be missing
- IntelligenceID for stable, deterministic IDs
- ContractBase as the base for all contract objects
- Time utilities (strict UTC, no naive datetimes)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


@dataclass(frozen=True)
class SchemaVersion:
    """Semantic version for intelligence contracts."""
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, version_str: str) -> "SchemaVersion":
        parts = version_str.strip().split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid version string: {version_str}")
        return cls(major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2]))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def is_compatible_with(self, other: "SchemaVersion") -> bool:
        if self.major != other.major:
            return False
        if other.minor < self.minor:
            return False
        return True


class DataStatus(str, Enum):
    AVAILABLE = "available"
    MISSING = "missing"
    CONFLICTING = "conflicting"
    STALE = "stale"
    NOT_APPLICABLE = "not_applicable"
    UNSUPPORTED = "unsupported"


@dataclass
class DataAvailability:
    status: DataStatus
    value: Any = None
    reason: str = ""
    observed_at: Optional[str] = None
    source_refs: list[str] = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = DataStatus(self.status)

    @classmethod
    def available(cls, value: Any, observed_at: Optional[str] = None,
                  source_refs: Optional[list[str]] = None) -> "DataAvailability":
        return cls(status=DataStatus.AVAILABLE, value=value,
                   observed_at=observed_at, source_refs=source_refs or [])

    @classmethod
    def missing(cls, reason: str = "") -> "DataAvailability":
        return cls(status=DataStatus.MISSING, reason=reason)

    @classmethod
    def conflicting(cls, reason: str = "") -> "DataAvailability":
        return cls(status=DataStatus.CONFLICTING, reason=reason)

    @classmethod
    def stale(cls, value: Any, reason: str = "") -> "DataAvailability":
        return cls(status=DataStatus.STALE, value=value, reason=reason)

    @classmethod
    def not_applicable(cls) -> "DataAvailability":
        return cls(status=DataStatus.NOT_APPLICABLE, reason="not applicable")

    @classmethod
    def unsupported(cls, reason: str = "") -> "DataAvailability":
        return cls(status=DataStatus.UNSUPPORTED, reason=reason)


class IDPrefix(str, Enum):
    SOURCE = "src"
    EVIDENCE = "evi"
    EVENT = "evt"
    TRANSITION = "trn"
    REGIME = "reg"
    STRATEGY = "str"
    INSTANCE = "sti"
    HYPOTHESIS = "hyp"
    ARBITRATION = "arb"
    ASSESSMENT = "asm"
    CALIBRATION = "cal"


@dataclass(frozen=True)
class IntelligenceID:
    prefix: IDPrefix
    value: str

    def __post_init__(self):
        if isinstance(self.prefix, str):
            object.__setattr__(self, "prefix", IDPrefix(self.prefix))

    @classmethod
    def from_string(cls, raw: str) -> "IntelligenceID":
        parts = raw.split("_", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid ID format: {raw}")
        return cls(prefix=IDPrefix(parts[0]), value=parts[1])

    @classmethod
    def from_payload(cls, prefix: IDPrefix, payload: str) -> "IntelligenceID":
        h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
        return cls(prefix=prefix, value=h)

    def __str__(self) -> str:
        return f"{self.prefix.value}_{self.value}"

    @property
    def full(self) -> str:
        return str(self)


def hash_identity(canonical_payload: str) -> str:
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()[:32]


def hash_content(data: dict) -> str:
    from ..serialization.canonical_json import canonical_json
    raw = canonical_json(data)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def hash_revision(data: dict) -> str:
    filtered = {k: v for k, v in data.items()
                if k not in ("created_at", "updated_at", "revision_hash")}
    return hash_content(filtered)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"


def utc_parse(ts: str) -> datetime:
    ts_clean = ts.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts_clean)
    if dt.tzinfo is None:
        raise ValueError(f"Naive datetime rejected: {ts}")
    return dt


def validate_utc(ts: str) -> str:
    dt = utc_parse(ts)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"


@dataclass
class ContractBase:
    contract_name: str = ""
    schema_version: str = "1.0.0"
    created_at: Optional[str] = None
    as_of_time: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = utc_now()
        if self.as_of_time is None:
            self.as_of_time = self.created_at

    def to_dict(self) -> dict:
        result = {}
        for f in fields(self):
            val = getattr(self, f.name)
            if isinstance(val, Enum):
                result[f.name] = val.value
            elif isinstance(val, Decimal):
                result[f.name] = str(val)
            elif isinstance(val, IntelligenceID):
                result[f.name] = str(val)
            elif isinstance(val, ContractBase):
                result[f.name] = val.to_dict()
            elif isinstance(val, list):
                converted = []
                for v in val:
                    if isinstance(v, ContractBase):
                        converted.append(v.to_dict())
                    elif isinstance(v, (Enum, Decimal, IntelligenceID)):
                        converted.append(str(v))
                    else:
                        converted.append(v)
                result[f.name] = converted
            elif isinstance(val, dict):
                result[f.name] = {
                    k: str(v) if isinstance(v, Enum) else v
                    for k, v in val.items()
                }
            else:
                result[f.name] = val
        return result
