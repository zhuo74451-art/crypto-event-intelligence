from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from ..contracts.source import SourceContract
from ..contracts.raw_document import RawDocument
from ..contracts.observation import NormalizedObservation
from ..contracts.timestamps import FiveTimestamps, TimestampEvidence, TimestampQuality, TimestampAnomaly, utc_now
from ..contracts.errors import AcquisitionError

@dataclass
class AcquisitionAdapterResult:
    raw_documents: list[RawDocument] = field(default_factory=list)
    observations: list[NormalizedObservation] = field(default_factory=list)
    errors: list[AcquisitionError] = field(default_factory=list)
    source_id: str = ""

class BaseAcquisitionAdapter(ABC):
    def __init__(self, contract: SourceContract):
        self.contract = contract
    
    @property
    def source_id(self) -> str:
        return self.contract.source_id
    
    @abstractmethod
    def fetch(self, max_items: int = 10) -> AcquisitionAdapterResult:
        ...
    
    def _make_timestamps(self, published=None, effective=None, updated=None, retrieved=None) -> FiveTimestamps:
        now = utc_now()
        return FiveTimestamps(
            published_at=TimestampEvidence(published, TimestampQuality.EXPLICIT_SOURCE if published else TimestampQuality.UNKNOWN, missing_reason="" if published else "source_did_not_provide"),
            effective_at=TimestampEvidence(effective, TimestampQuality.INFERRED_FROM_CONTENT if effective else TimestampQuality.UNKNOWN, missing_reason="" if effective else "source_did_not_provide"),
            updated_at=TimestampEvidence(updated, TimestampQuality.EXPLICIT_SOURCE if updated else TimestampQuality.UNKNOWN, missing_reason="" if updated else "source_did_not_provide"),
            first_seen_at=TimestampEvidence(now, TimestampQuality.RETRIEVAL_ONLY),
            retrieved_at=TimestampEvidence(now, TimestampQuality.RETRIEVAL_ONLY),
        )
