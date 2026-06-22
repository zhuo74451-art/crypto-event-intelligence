from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
from market_radar.domains.macro.taxonomy.event_types import EventFamily, EventComponent
from market_radar.domains.macro.contracts.common import UnitType


@dataclass(frozen=True)
class ComponentMetadata:
    name: str
    description: str
    unit: UnitType
    typical_source: str
    release_authority: str


CPI_COMPONENTS: List[EventComponent] = [
    EventComponent.HEADLINE_MOM,
    EventComponent.HEADLINE_YOY,
    EventComponent.CORE_MOM,
    EventComponent.CORE_YOY,
    EventComponent.SHELTER,
    EventComponent.SERVICES_EX_HOUSING,
    EventComponent.ENERGY,
    EventComponent.FOOD,
]

NFP_COMPONENTS: List[EventComponent] = [
    EventComponent.PAYROLL_CHANGE,
    EventComponent.UNEMPLOYMENT_RATE,
    EventComponent.AVERAGE_HOURLY_EARNINGS,
    EventComponent.PARTICIPATION_RATE,
    EventComponent.PRIOR_MONTH_REVISION,
]

PCE_COMPONENTS: List[EventComponent] = [
    EventComponent.CORE_PCE_MOM,
    EventComponent.CORE_PCE_YOY,
    EventComponent.HEADLINE_PCE_MOM,
    EventComponent.HEADLINE_PCE_YOY,
    EventComponent.PERSONAL_INCOME,
    EventComponent.PERSONAL_SPENDING,
]

FOMC_COMPONENTS: List[EventComponent] = [
    EventComponent.RATE_DECISION,
    EventComponent.RATE_TARGET_UPPER,
    EventComponent.RATE_TARGET_LOWER,
    EventComponent.DOT_PLOT_MEDIAN,
    EventComponent.STATEMENT_TEXT_HASH,
    EventComponent.BALANCE_SHEET,
    EventComponent.FORWARD_GUIDANCE,
    EventComponent.ECONOMIC_PROJECTIONS,
]

FAMILY_COMPONENTS: Dict[EventFamily, List[EventComponent]] = {
    EventFamily.CPI_HEADLINE: [
        EventComponent.HEADLINE_MOM,
        EventComponent.HEADLINE_YOY,
        EventComponent.SHELTER,
        EventComponent.SERVICES_EX_HOUSING,
        EventComponent.ENERGY,
        EventComponent.FOOD,
    ],
    EventFamily.CPI_CORE: [
        EventComponent.CORE_MOM,
        EventComponent.CORE_YOY,
        EventComponent.SHELTER,
        EventComponent.SERVICES_EX_HOUSING,
    ],
    EventFamily.NONFARM_PAYROLLS: NFP_COMPONENTS,
    EventFamily.UNEMPLOYMENT_RATE: [
        EventComponent.UNEMPLOYMENT_RATE,
        EventComponent.PARTICIPATION_RATE,
    ],
    EventFamily.CORE_PCE: PCE_COMPONENTS,
    EventFamily.FOMC_RATE_DECISION: [
        EventComponent.RATE_DECISION,
        EventComponent.RATE_TARGET_UPPER,
        EventComponent.RATE_TARGET_LOWER,
        EventComponent.DOT_PLOT_MEDIAN,
    ],
    EventFamily.FOMC_STATEMENT: [
        EventComponent.STATEMENT_TEXT_HASH,
        EventComponent.BALANCE_SHEET,
        EventComponent.FORWARD_GUIDANCE,
        EventComponent.ECONOMIC_PROJECTIONS,
    ],
}


def get_components_for_family(family: EventFamily) -> List[EventComponent]:
    return FAMILY_COMPONENTS.get(family, [])


class ComponentCatalog:
    _metadata: Dict[EventComponent, ComponentMetadata] = {
        EventComponent.HEADLINE_MOM: ComponentMetadata("Headline MoM", "CPI Headline month-over-month change", UnitType.CHANGE_MOM, "BLS", "BLS"),
        EventComponent.HEADLINE_YOY: ComponentMetadata("Headline YoY", "CPI Headline year-over-year change", UnitType.CHANGE_YOY, "BLS", "BLS"),
        EventComponent.CORE_MOM: ComponentMetadata("Core MoM", "CPI Core (ex-food/energy) month-over-month", UnitType.CHANGE_MOM, "BLS", "BLS"),
        EventComponent.CORE_YOY: ComponentMetadata("Core YoY", "CPI Core year-over-year change", UnitType.CHANGE_YOY, "BLS", "BLS"),
        EventComponent.PAYROLL_CHANGE: ComponentMetadata("Payroll Change", "Change in nonfarm payrolls", UnitType.THOUSANDS, "BLS", "BLS"),
        EventComponent.UNEMPLOYMENT_RATE: ComponentMetadata("Unemployment Rate", "U-3 unemployment rate", UnitType.PERCENT, "BLS", "BLS"),
        EventComponent.CORE_PCE_MOM: ComponentMetadata("Core PCE MoM", "Core PCE month-over-month change", UnitType.CHANGE_MOM, "BEA", "BEA"),
        EventComponent.CORE_PCE_YOY: ComponentMetadata("Core PCE YoY", "Core PCE year-over-year change", UnitType.CHANGE_YOY, "BEA", "BEA"),
    }

    @classmethod
    def get_metadata(cls, component: EventComponent) -> ComponentMetadata | None:
        return cls._metadata.get(component)

    @classmethod
    def register_metadata(cls, component: EventComponent, metadata: ComponentMetadata) -> None:
        cls._metadata[component] = metadata
