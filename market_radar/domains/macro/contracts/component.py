from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


@dataclass(frozen=True)
class CompositionConflict:
    """Describes a conflict or inconsistency between release components.

    Attributes:
        component_a: Identifier of the first component in conflict.
        component_b: Identifier of the second component in conflict.
        conflict_type: A short label for the nature of the conflict.
        description: Human-readable explanation of the conflict.
    """
    component_a: str
    component_b: str
    conflict_type: str
    description: str = ""


@dataclass(frozen=True)
class ComponentInterpretation:
    """An interpretation / significance assessment for one component.

    Attributes:
        component_id: Which component this interpretation applies to.
        release_event_id: The release event this component belongs to.
        interpretation: Free-text interpretation or analysis.
        significance: Numeric or categorical significance rating.
        conflict_with: Optional ID of a conflicting component.
    """
    component_id: str
    release_event_id: str
    interpretation: str = ""
    significance: Optional[str] = None
    conflict_with: Optional[str] = None


@dataclass(frozen=True)
class ReleaseComposition:
    """Describes the full composition of a macro release event.

    Attributes:
        release_event_id: The release event this composition describes.
        components: Ordered list of component identifiers.
        conflicts: List of known conflicts between components.
    """
    release_event_id: str
    components: list[str] = field(default_factory=list)
    conflicts: list[CompositionConflict] = field(default_factory=list)

    def has_component(self, component_id: str) -> bool:
        return component_id in self.components

    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0
