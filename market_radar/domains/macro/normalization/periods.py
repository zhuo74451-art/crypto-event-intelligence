from __future__ import annotations
from datetime import datetime, timedelta
from market_radar.domains.macro.contracts.common import ObservationPeriod
from market_radar.domains.macro.taxonomy.event_types import EventFamily


class PeriodConverter:
    @staticmethod
    def observation_period_from_release(release_date: datetime, family: EventFamily) -> ObservationPeriod:
        if family in (EventFamily.CPI_HEADLINE, EventFamily.CPI_CORE, EventFamily.CORE_PCE):
            ref_month = release_date.replace(day=1) - timedelta(days=30)
            return ObservationPeriod(
                period_start=ref_month.replace(day=1),
                period_end=ref_month.replace(day=28) + timedelta(days=4),
                period_label=ref_month.strftime("%Y-%m"),
            )
        elif family in (EventFamily.NONFARM_PAYROLLS, EventFamily.UNEMPLOYMENT_RATE):
            ref_month = release_date.replace(day=1) - timedelta(days=30)
            return ObservationPeriod(
                period_start=ref_month.replace(day=1),
                period_end=ref_month.replace(day=28) + timedelta(days=4),
                period_label=ref_month.strftime("%Y-%m"),
            )
        else:
            ref_month = release_date.replace(day=1)
            return ObservationPeriod(
                period_start=ref_month.replace(day=1),
                period_end=ref_month.replace(day=28) + timedelta(days=4),
                period_label=ref_month.strftime("%Y-%m"),
            )

    @staticmethod
    def format_period_label(period: ObservationPeriod) -> str:
        return period.period_label
