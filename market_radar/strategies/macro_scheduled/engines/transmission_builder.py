from __future__ import annotations
from typing import Dict, List, Optional
from market_radar.domains.macro.taxonomy.transmission_channels import (
    TransmissionEdge, TransmissionChannel, get_default_transmission_paths,
    TransmissionSign,
)
from market_radar.domains.macro.taxonomy.event_types import EventFamily
from market_radar.domains.macro.contracts.market_context import GrowthInflationRegime
from market_radar.strategies.macro_scheduled.contracts.transmission import TransmissionPath, TransmissionStatus


class TransmissionBuilder:
    @staticmethod
    def build_transmission_paths(event_family: EventFamily,
                                  surprise_direction: str,
                                  regime: Optional[GrowthInflationRegime] = None) -> List[TransmissionPath]:
        edges = get_default_transmission_paths(event_family, surprise_direction)
        if not edges:
            return []
        path = TransmissionPath(
            name=f"{event_family.value}_{surprise_direction}",
            edges=edges,
            status=TransmissionStatus.ACTIVE,
            primary_sign=surprise_direction,
        )
        return [path]

    @staticmethod
    def evaluate_path_conditions(path: TransmissionPath,
                                  regime: GrowthInflationRegime) -> TransmissionStatus:
        for edge in path.edges:
            if "growth_collapse" in edge.conditions:
                if regime == GrowthInflationRegime.GROWTH_DOWN_INFLATION_DOWN:
                    path = TransmissionPath(**dict(path._asdict()))
                    return TransmissionStatus.CONDITIONAL
            if "inflation_driven_by_demand" in edge.conditions:
                if regime in (GrowthInflationRegime.GROWTH_UP_INFLATION_DOWN,
                              GrowthInflationRegime.GROWTH_UP_INFLATION_UP):
                    return TransmissionStatus.ACTIVE
        return path.status

    @staticmethod
    def select_competing_paths(paths: List[TransmissionPath]) -> List[TransmissionPath]:
        if len(paths) <= 1:
            return paths
        active = [p for p in paths if p.status == TransmissionStatus.ACTIVE]
        if active:
            return active
        return paths

    @staticmethod
    def get_dominant_path(paths: List[TransmissionPath]) -> Optional[TransmissionPath]:
        active = [p for p in paths if p.status == TransmissionStatus.ACTIVE]
        if active:
            return active[0]
        conditional = [p for p in paths if p.status == TransmissionStatus.CONDITIONAL]
        if conditional:
            return conditional[0]
        return paths[0] if paths else None
