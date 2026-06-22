from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AuthorityTier(str, Enum):
    PRIMARY_OFFICIAL = "primary_official"
    SPECIALIZED_INDEPENDENT = "specialized_independent"
    SECONDARY_MEDIA = "secondary_media"
    SOCIAL_UNVERIFIED = "social_unverified"
    DERIVED_DATASET = "derived_dataset"


class SourceRole(str, Enum):
    DISCOVERY = "discovery"
    AUTHORITATIVE_EVIDENCE = "authoritative_evidence"
    EXPECTATION = "expectation"
    MARKET_CONFIRMATION = "market_confirmation"
    RESEARCH = "research"
    COMMENTARY = "commentary"


class AcquisitionMethod(str, Enum):
    HTTP_JSON_API = "http_json_api"
    RSS = "rss"
    STATIC_HTML = "static_html"
    GITHUB_API = "github_api"
    FIXTURE = "fixture"
    RSSHUB = "rsshub"


@dataclass(frozen=True)
class RateLimitPolicy:
    requests_per_second: float = 1.0
    max_burst: int = 5
    retry_after_default: float = 60.0


@dataclass(frozen=True)
class HealthPolicy:
    max_freshness_delay_hours: float = 24.0
    consecutive_failure_limit: int = 3
    empty_content_threshold: float = 0.1
    parser_drift_detection: bool = True


@dataclass(frozen=True)
class LegalStatus:
    terms_reviewed: bool = False
    robots_policy: str = "not_reviewed"
    redistribution_status: str = "not_reviewed"
    personal_data_expected: bool = False


@dataclass(frozen=True)
class SourceContract:
    source_id: str = ""
    source_name: str = ""
    source_version: str = "1.0.0"
    authority_tier: AuthorityTier = AuthorityTier.SECONDARY_MEDIA
    roles: tuple[SourceRole, ...] = (SourceRole.DISCOVERY,)
    content_types: tuple[str, ...] = ("text",)
    languages: tuple[str, ...] = ("en",)
    jurisdictions: tuple[str, ...] = field(default_factory=tuple)
    market_domains: tuple[str, ...] = field(default_factory=tuple)
    primary_method: AcquisitionMethod = AcquisitionMethod.HTTP_JSON_API
    fallback_methods: tuple[AcquisitionMethod, ...] = field(default_factory=tuple)
    authentication: str = "none"
    expected_content_type: str = "application/json"
    timeout_seconds: float = 30.0
    rate_limit: RateLimitPolicy = field(default_factory=RateLimitPolicy)
    user_agent_policy: str = "default"
    source_timezone: str = "UTC"
    published_time_available: bool = False
    updated_time_available: bool = False
    effective_time_available: bool = False
    preserve_raw_payload: bool = True
    archive_required: bool = False
    content_hash_required: bool = True
    health_policy: HealthPolicy = field(default_factory=HealthPolicy)
    legal: LegalStatus = field(default_factory=LegalStatus)
    independence_group: str = ""
    upstream_source_refs: tuple[str, ...] = field(default_factory=tuple)
    derived_from: str = ""
    reposted_from: str = ""
    quoted_source: str = ""
    enabled: bool = True
    support_status: str = "active"
    known_biases: tuple[str, ...] = field(default_factory=tuple)
    manipulation_risk: str = "unknown"

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id, "source_name": self.source_name,
            "source_version": self.source_version,
            "authority_tier": self.authority_tier.value,
            "roles": [r.value for r in self.roles],
            "content_types": list(self.content_types),
            "languages": list(self.languages),
            "jurisdictions": list(self.jurisdictions),
            "market_domains": list(self.market_domains),
            "primary_method": self.primary_method.value,
            "fallback_methods": [m.value for m in self.fallback_methods],
            "authentication": self.authentication,
            "expected_content_type": self.expected_content_type,
            "timeout_seconds": self.timeout_seconds,
            "source_timezone": self.source_timezone,
            "published_time_available": self.published_time_available,
            "updated_time_available": self.updated_time_available,
            "effective_time_available": self.effective_time_available,
            "preserve_raw_payload": self.preserve_raw_payload,
            "archive_required": self.archive_required,
            "content_hash_required": self.content_hash_required,
            "independence_group": self.independence_group,
            "upstream_source_refs": list(self.upstream_source_refs),
            "derived_from": self.derived_from,
            "reposted_from": self.reposted_from,
            "quoted_source": self.quoted_source,
            "enabled": self.enabled,
            "support_status": self.support_status,
            "known_biases": list(self.known_biases),
            "manipulation_risk": self.manipulation_risk,
            "legal": {
                "terms_reviewed": self.legal.terms_reviewed,
                "robots_policy": self.legal.robots_policy,
                "redistribution_status": self.legal.redistribution_status,
                "personal_data_expected": self.legal.personal_data_expected,
            },
        }

    @classmethod
    def from_dict(cls, d: dict) -> SourceContract:
        return cls(
            source_id=d.get("source_id", ""),
            source_name=d.get("source_name", ""),
            source_version=d.get("source_version", "1.0.0"),
            authority_tier=AuthorityTier(d["authority_tier"]) if "authority_tier" in d else AuthorityTier.SECONDARY_MEDIA,
            roles=tuple(SourceRole(r) for r in d.get("roles", ["discovery"])),
            content_types=tuple(d.get("content_types", ["text"])),
            languages=tuple(d.get("languages", ["en"])),
            jurisdictions=tuple(d.get("jurisdictions", [])),
            market_domains=tuple(d.get("market_domains", [])),
            primary_method=AcquisitionMethod(d["primary_method"]) if "primary_method" in d else AcquisitionMethod.HTTP_JSON_API,
            fallback_methods=tuple(AcquisitionMethod(m) for m in d.get("fallback_methods", [])),
            authentication=d.get("authentication", "none"),
            expected_content_type=d.get("expected_content_type", "application/json"),
            timeout_seconds=d.get("timeout_seconds", 30.0),
            source_timezone=d.get("source_timezone", "UTC"),
            published_time_available=d.get("published_time_available", False),
            updated_time_available=d.get("updated_time_available", False),
            effective_time_available=d.get("effective_time_available", False),
            preserve_raw_payload=d.get("preserve_raw_payload", True),
            archive_required=d.get("archive_required", False),
            content_hash_required=d.get("content_hash_required", True),
            independence_group=d.get("independence_group", ""),
            upstream_source_refs=tuple(d.get("upstream_source_refs", [])),
            derived_from=d.get("derived_from", ""),
            reposted_from=d.get("reposted_from", ""),
            quoted_source=d.get("quoted_source", ""),
            enabled=d.get("enabled", True),
            support_status=d.get("support_status", "active"),
            known_biases=tuple(d.get("known_biases", [])),
            manipulation_risk=d.get("manipulation_risk", "unknown"),
        )
