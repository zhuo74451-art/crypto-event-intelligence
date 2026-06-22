from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ReplayMode(str, Enum):
    KNOWLEDGE_AS_KNOWN_THEN = "knowledge_as_known_then"
    CURRENT_BEST_RECONSTRUCTION = "current_best_reconstruction"


@dataclass(frozen=True)
class ReplayQuery:
    as_of_time: datetime
    source_ids: tuple[str, ...] = field(default_factory=tuple)
    content_types: tuple[str, ...] = field(default_factory=tuple)
    entity_filters: tuple[str, ...] = field(default_factory=tuple)
    asset_filters: tuple[str, ...] = field(default_factory=tuple)
    mode: ReplayMode = ReplayMode.KNOWLEDGE_AS_KNOWN_THEN

    def to_dict(self) -> dict:
        return {"as_of_time": self.as_of_time.isoformat(),
                "source_ids": list(self.source_ids),
                "content_types": list(self.content_types),
                "entity_filters": list(self.entity_filters),
                "asset_filters": list(self.asset_filters),
                "mode": self.mode.value}


@dataclass(frozen=True)
class ReplayResult:
    query: ReplayQuery
    observations: tuple = field(default_factory=tuple)
    observation_count: int = 0
    mode_used: ReplayMode = ReplayMode.KNOWLEDGE_AS_KNOWN_THEN
    is_reconstructed: bool = False
    warnings: tuple[str, ...] = field(default_factory=tuple)
    generated_at: str = ""

    def to_dict(self) -> dict:
        return {"query": self.query.to_dict(), "observation_count": self.observation_count,
                "mode_used": self.mode_used.value, "is_reconstructed": self.is_reconstructed,
                "warnings": list(self.warnings), "generated_at": self.generated_at}
