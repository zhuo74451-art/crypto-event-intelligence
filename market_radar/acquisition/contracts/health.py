from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class DriftSeverity(str, Enum):
    NONE = "none"
    WARNING = "warning"
    BREAKING = "breaking"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class HealthIndicator:
    name: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    value: float | str | None = None
    threshold: float | str | None = None
    message: str = ""
    checked_at: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "status": self.status.value,
                "value": self.value, "threshold": self.threshold,
                "message": self.message, "checked_at": self.checked_at}


@dataclass(frozen=True)
class ParserDriftReport:
    source_id: str = ""
    severity: DriftSeverity = DriftSeverity.NONE
    details: tuple[str, ...] = field(default_factory=tuple)
    fields_affected: tuple[str, ...] = field(default_factory=tuple)
    detected_at: str = ""

    def to_dict(self) -> dict:
        return {"source_id": self.source_id, "severity": self.severity.value,
                "details": list(self.details), "fields_affected": list(self.fields_affected),
                "detected_at": self.detected_at}


@dataclass(frozen=True)
class SourceHealthReport:
    source_id: str = ""
    overall_status: HealthStatus = HealthStatus.UNKNOWN
    indicators: tuple[HealthIndicator, ...] = field(default_factory=tuple)
    last_success_at: str = ""
    last_failure_at: str = ""
    consecutive_failures: int = 0
    total_requests: int = 0
    success_rate: float = 0.0
    empty_content_rate: float = 0.0
    parser_drift: ParserDriftReport | None = None
    fallback_active: bool = False
    fallback_source_id: str = ""
    reported_at: str = ""

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id, "overall_status": self.overall_status.value,
            "indicators": [i.to_dict() for i in self.indicators],
            "last_success_at": self.last_success_at, "last_failure_at": self.last_failure_at,
            "consecutive_failures": self.consecutive_failures,
            "total_requests": self.total_requests, "success_rate": self.success_rate,
            "empty_content_rate": self.empty_content_rate,
            "parser_drift": self.parser_drift.to_dict() if self.parser_drift else None,
            "fallback_active": self.fallback_active,
            "fallback_source_id": self.fallback_source_id, "reported_at": self.reported_at,
        }
