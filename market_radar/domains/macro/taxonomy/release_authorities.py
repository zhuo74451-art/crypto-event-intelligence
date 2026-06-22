from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict
from market_radar.domains.macro.taxonomy.event_types import EventFamily


class ReleaseAuthority(str, Enum):
    BLS = "bls"
    BEA = "bea"
    FEDERAL_RESERVE = "federal_reserve"
    FRED = "fred"
    CENSUS_BUREAU = "census_bureau"
    DOL = "dol"
    TREASURY = "treasury"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AuthorityMetadata:
    name: str
    url: str
    data_available: Dict[str, bool]


AUTHORITY_MAP: Dict[EventFamily, ReleaseAuthority] = {
    EventFamily.CPI_HEADLINE: ReleaseAuthority.BLS,
    EventFamily.CPI_CORE: ReleaseAuthority.BLS,
    EventFamily.NONFARM_PAYROLLS: ReleaseAuthority.BLS,
    EventFamily.UNEMPLOYMENT_RATE: ReleaseAuthority.BLS,
    EventFamily.CORE_PCE: ReleaseAuthority.BEA,
    EventFamily.FOMC_RATE_DECISION: ReleaseAuthority.FEDERAL_RESERVE,
    EventFamily.FOMC_STATEMENT: ReleaseAuthority.FEDERAL_RESERVE,
    EventFamily.AVERAGE_HOURLY_EARNINGS: ReleaseAuthority.BLS,
    EventFamily.LABOR_FORCE_PARTICIPATION: ReleaseAuthority.BLS,
    EventFamily.INITIAL_JOBLESS_CLAIMS: ReleaseAuthority.DOL,
    EventFamily.PPI: ReleaseAuthority.BLS,
    EventFamily.RETAIL_SALES: ReleaseAuthority.CENSUS_BUREAU,
    EventFamily.ISM: ReleaseAuthority.UNKNOWN,
}


def get_authority_for_event(family: EventFamily) -> ReleaseAuthority:
    return AUTHORITY_MAP.get(family, ReleaseAuthority.UNKNOWN)


def get_authority_url(authority: ReleaseAuthority) -> str:
    urls = {
        ReleaseAuthority.BLS: "https://www.bls.gov/",
        ReleaseAuthority.BEA: "https://www.bea.gov/",
        ReleaseAuthority.FEDERAL_RESERVE: "https://www.federalreserve.gov/",
        ReleaseAuthority.FRED: "https://fred.stlouisfed.org/",
        ReleaseAuthority.CENSUS_BUREAU: "https://www.census.gov/",
        ReleaseAuthority.DOL: "https://www.dol.gov/",
        ReleaseAuthority.TREASURY: "https://home.treasury.gov/",
        ReleaseAuthority.UNKNOWN: "",
    }
    return urls.get(authority, "")
