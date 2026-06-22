from __future__ import annotations
from typing import Dict, List, Optional
from market_radar.domains.macro.contracts.component import (
    ComponentInterpretation, ReleaseComposition, CompositionConflict,
)
from market_radar.domains.macro.contracts.actual_release import OfficialReleaseRecord
from market_radar.domains.macro.taxonomy.event_types import EventComponent


class ComponentInterpreter:
    @staticmethod
    def interpret_release_composition(release: OfficialReleaseRecord,
                                       components: Dict[str, float]) -> ReleaseComposition:
        """Build a release composition from component value dict."""
        comps: List[ComponentInterpretation] = []
        conflicts: List[CompositionConflict] = []
        has_headline = EventComponent.HEADLINE_MOM.value in components or EventComponent.HEADLINE_YOY.value in components
        has_core = EventComponent.CORE_MOM.value in components or EventComponent.CORE_YOY.value in components

        for comp_id, value in components.items():
            significance = "primary"
            if comp_id in (EventComponent.SHELTER.value, EventComponent.ENERGY.value):
                significance = "sub_component"
            comps.append(ComponentInterpretation(
                component_id=comp_id,
                release_event_id=release.release_event_id,
                interpretation="",
                significance=significance,
            ))

        if has_headline and has_core:
            conflict = ComponentInterpreter.detect_headline_core_conflict(None, None)
            if conflict:
                conflicts.append(conflict)

        return ReleaseComposition(
            release_event_id=release.release_event_id,
            components=comps,
            conflicts=conflicts,
        )

    @staticmethod
    def detect_headline_core_conflict(headline_surprise: Optional[float],
                                       core_surprise: Optional[float]) -> Optional[CompositionConflict]:
        """Detect when headline and core move in opposite directions."""
        if headline_surprise is None or core_surprise is None:
            return None
        if (headline_surprise > 0 and core_surprise < 0) or (headline_surprise < 0 and core_surprise > 0):
            return CompositionConflict(
                component_a=EventComponent.HEADLINE_MOM.value,
                component_b=EventComponent.CORE_MOM.value,
                conflict_type="headline_core_divergence",
                description=f"Headline ({headline_surprise:+.2f}) and Core ({core_surprise:+.2f}) diverge",
            )
        return None

    @staticmethod
    def detect_nfp_internal_conflict(payroll_change: Optional[float],
                                      unemployment: Optional[float],
                                      wages: Optional[float]) -> List[CompositionConflict]:
        """Detect conflicts between NFP sub-components."""
        conflicts: List[CompositionConflict] = []
        if payroll_change is not None and unemployment is not None:
            # Strong payroll + rising unemployment is conflicting
            if payroll_change > 150 and unemployment is not None and unemployment > 0.3:
                conflicts.append(CompositionConflict(
                    component_a=EventComponent.PAYROLL_CHANGE.value,
                    component_b=EventComponent.UNEMPLOYMENT_RATE.value,
                    conflict_type="payroll_unemployment_divergence",
                    description=f"Payrolls strong ({payroll_change:+.0f}K) but unemployment rising ({unemployment:+.1f}%)",
                ))
        return conflicts
