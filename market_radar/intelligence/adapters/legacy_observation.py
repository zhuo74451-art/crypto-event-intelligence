"""Legacy Observation Adapter — maps legacy Observation objects to new contracts.

Read-only adapter. Does NOT modify legacy objects. Maps:
- Observation -> EvidenceItem(s)
- Observation -> partial EventEntity
- Observation fields that have no new-contract equivalent are flagged as LOSSY or UNSUPPORTED.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional
from enum import Enum

from ..contracts.evidence import EvidenceItem, VerificationStatus
from ..contracts.event import EventEntity, EventState
from ..contracts.common import IntelligenceID, IDPrefix, DataAvailability, DataStatus


class MappingQuality(str, Enum):
    DIRECT_MAP = "direct_map"
    DERIVED_MAP = "derived_map"
    LOSSY_MAP = "lossy_map"
    UNSUPPORTED = "unsupported"
    DEPRECATED = "deprecated"


@dataclass
class FieldMapping:
    """Record of a single field mapping from legacy to new contract."""
    legacy_field: str = ""
    new_field: str = ""
    quality: MappingQuality = MappingQuality.DIRECT_MAP
    note: str = ""


@dataclass
class ObservationMappingResult:
    """Result of mapping a legacy Observation to new contracts."""
    evidence_items: list[EvidenceItem] = field(default_factory=list)
    event: Optional[EventEntity] = None
    field_mappings: list[FieldMapping] = field(default_factory=list)
    lossy_fields: list[str] = field(default_factory=list)
    unsupported_fields: list[str] = field(default_factory=list)
    success: bool = True


class LegacyObservationAdapter:
    """Read-only adapter for legacy Observation objects."""

    SUPPORTED_SOURCE_TYPES = {"fixture", "free_public_api", "free_public_source", "local_snapshot"}

    @classmethod
    def map_observation(cls, obs: Any) -> ObservationMappingResult:
        """Map a legacy Observation to new contract models.

        Args:
            obs: A legacy Observation-like object (from shared/models.py).

        Returns:
            ObservationMappingResult with new contracts and mapping metadata.
        """
        result = ObservationMappingResult()

        # Extract fields with introspection
        obs_dict = cls._to_dict(obs)

        # Map to EvidenceItem(s)
        evidence = cls._map_evidence(obs_dict)
        result.evidence_items = evidence

        for ev in evidence:
            result.field_mappings.append(FieldMapping(
                legacy_field="evidence (from observation.source_refs)",
                new_field=f"EvidenceItem(evidence_id={ev.evidence_id})",
                quality=MappingQuality.DIRECT_MAP,
                note="Direct mapping of observation evidence links",
            ))

        # Map to partial EventEntity
        event = cls._map_event(obs_dict)
        if event:
            result.event = event
            result.field_mappings.append(FieldMapping(
                legacy_field="observation (top-level)",
                new_field="EventEntity",
                quality=MappingQuality.DERIVED_MAP,
                note="Partial event entity derived from observation metadata",
            ))

        # Track lossy/unsupported fields
        legacy_fields = set(obs_dict.keys())
        mapped_fields = {
            "observation_id", "source", "source_type", "observed_at",
            "event_time", "affected_assets", "normalized_payload",
            "evidence", "data_quality", "card_family", "source_refs",
            "risk_notes",
        }
        unmapped = legacy_fields - mapped_fields
        for field_name in sorted(unmapped):
            if field_name.startswith("_"):
                continue
            result.unsupported_fields.append(field_name)
            result.field_mappings.append(FieldMapping(
                legacy_field=field_name,
                new_field="(none)",
                quality=MappingQuality.UNSUPPORTED,
                note=f"Field '{field_name}' has no equivalent in new contracts",
            ))

        return result

    @classmethod
    def _to_dict(cls, obj: Any) -> dict:
        """Convert a potential dataclass/object to dict."""
        if hasattr(obj, "as_dict"):
            return obj.as_dict()
        if hasattr(obj, "__dataclass_fields__"):
            return asdict(obj)
        if isinstance(obj, dict):
            return obj
        return {"_raw": str(obj)}

    @classmethod
    def _map_evidence(cls, obs_dict: dict) -> list[EvidenceItem]:
        """Map observation evidence links to EvidenceItems."""
        items = []
        evidence_list = obs_dict.get("evidence", [])
        if not evidence_list:
            return items

        for i, ev in enumerate(evidence_list):
            if isinstance(ev, dict):
                ev_dict = ev
            elif hasattr(ev, "__dataclass_fields__"):
                ev_dict = asdict(ev)
            else:
                ev_dict = {"ref": str(ev), "source": str(ev)}

            published_at = obs_dict.get("observed_at")
            item = EvidenceItem(
                evidence_id=f"evi_legacy_{i}_{obs_dict.get('observation_id', 'unknown')}",
                claim=obs_dict.get("normalized_payload", {}).get("title",
                      obs_dict.get("title", "Unknown observation")),
                source_id=ev_dict.get("source", obs_dict.get("source", "unknown")),
                source_role=obs_dict.get("source_type", "unknown"),
                published_at=published_at,
                retrieved_at=published_at,
                first_seen_at=published_at,
                independence_group=ev_dict.get("source", obs_dict.get("source", "unknown")),
                raw_payload_ref=ev_dict.get("ref", ""),
                content_hash=ev_dict.get("ref", ""),
                is_primary=False,
                verification_status=VerificationStatus.SINGLE_SOURCE_UNVERIFIED,
                limitations=[
                    "Legacy observation: no independence_group tracking",
                    "Legacy observation: no explicit verification status",
                ],
            )
            items.append(item)
        return items

    @classmethod
    def _map_event(cls, obs_dict: dict) -> Optional[EventEntity]:
        """Map observation to a partial EventEntity."""
        obs_id = obs_dict.get("observation_id", "")
        if not obs_id:
            return None

        title = obs_dict.get("normalized_payload", {}).get("title",
                obs_dict.get("title", "Unknown"))
        assets = obs_dict.get("affected_assets", [])
        entities = []

        source = obs_dict.get("source", "")
        if source:
            entities.append(source)

        return EventEntity(
            event_id=f"evt_legacy_{obs_id}",
            title=str(title),
            entities=entities,
            assets=[str(a) for a in assets],
            current_state=EventState.UNKNOWN,
            evidence_bundle_id=None,
        )

    @classmethod
    def mapping_summary(cls, obs: Any) -> dict:
        """Return a human-readable summary of what the mapping does and loses."""
        result = cls.map_observation(obs)
        return {
            "field_count": len(result.field_mappings),
            "lossy_count": len(result.lossy_fields),
            "unsupported_count": len(result.unsupported_fields),
            "evidence_items": len(result.evidence_items),
            "event_created": result.event is not None,
            "lossy_fields": result.lossy_fields,
            "unsupported_fields": result.unsupported_fields,
        }
