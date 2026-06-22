"""Bureau of Economic Analysis (BEA) provider.

Provides:
- Core PCE Price Index (Series: PCEPILFE)

Uses BEA's public JSON API for historical data retrieval.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
import urllib.error
import urllib.parse
from typing import Any, Optional

from .base import ProviderBase
from ..contracts import (
    MacroReleaseEventV1,
    MacroRevisionRecordV1,
    EventFamily,
    RevisionStatus,
    utc_now, utc_parse,
)


BEA_SERIES_MAP: dict[str, dict[str, Any]] = {
    "PCEPILFE": {
        "family": "us_core_pce",
        "unit": "pct_change_mom",
        "name": "PCE Excluding Food and Energy (Monthly)",
        "table": "T20805",
    },
}


class BEAProvider(ProviderBase):
    """Provider for BEA macro-economic data."""

    provider_name: str = "bea"
    base_url: str = "https://apps.bea.gov/api/data/"
    release_calendar_url: str = "https://www.bea.gov/news/schedule"

    def __init__(self, cache_dir: str = "", output_dir: str = ""):
        super().__init__(cache_dir=cache_dir, output_dir=output_dir)
        self.rate_limit_delay = 1.0

    def fetch_release_calendar(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        return []

    def fetch_release_values(self, series_id: str, start_year: str, end_year: str) -> list[dict[str, Any]]:
        """Fetch PCE data via BEA Data API using public access.

        Uses NIPA table download with specific table ID.
        """
        config = BEA_SERIES_MAP.get(series_id)
        if not config:
            return []

        table_id = config["table"]
        self._rate_limit()

        params = urllib.parse.urlencode({
            "UserID": "Public",
            "Method": "GetData",
            "DataSetName": "NIPA",
            "TableName": table_id,
            "Frequency": "M",
            "Year": f"{start_year},{end_year}",
            "ResultFormat": "JSON",
        })
        url = f"{self.base_url}?{params}"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                raw_content = resp.read()
            self.save_raw_snapshot(url, raw_content, "application/json")

            data = json.loads(raw_content)
            results = (data.get("BEAAPI", {})
                       .get("Results", {})
                       .get("Data", []))
            return results
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
            print(f"  [BEA] Error: {e}")
            return []

    def fetch_revision_history(self, series_id: str) -> list[dict[str, Any]]:
        return []

    def normalize_release(self, raw: dict[str, Any]) -> Optional[MacroReleaseEventV1]:
        """Normalize BEA data record to MacroReleaseEventV1."""
        series_id = raw.get("SeriesCode", "")
        if series_id not in BEA_SERIES_MAP:
            return None

        config = BEA_SERIES_MAP[series_id]
        family = config["family"]

        # Parse time period: "2023M05" -> "2023-05"
        time_period = raw.get("TimePeriod", "")
        year = raw.get("Year", "")

        if time_period:
            m = re.match(r"(\d{4})M(\d{2})", time_period)
            if m:
                ref_period = f"{m.group(1)}-{m.group(2)}"
            else:
                return None
        else:
            return None

        try:
            value = float(raw.get("DataValue", ""))
        except (ValueError, TypeError):
            value = None

        # PCE is usually released around end of month: estimate release date
        release_date = self._estimate_release_date(year or ref_period[:4], ref_period[5:7])

        event = MacroReleaseEventV1(
            event_family=family,
            series_id=series_id,
            reference_period=ref_period,
            actual_release_at_utc=release_date,
            actual_initial=value,
            actual_initial_unit=config["unit"],
            prior_as_known_then=None,
            revision_status="initial",
            official_source_name="U.S. Bureau of Economic Analysis",
            official_source_url=f"https://www.bea.gov/data/consumer-spending/main",
            data_quality_flags=[],
        )
        return event

    def normalize_revision(self, raw: dict[str, Any]) -> Optional[MacroRevisionRecordV1]:
        return None

    def _estimate_release_date(self, year: str, month: str) -> str:
        """Estimate PCE release date (typically around 25th-30th of month)."""
        m = int(month)
        y = int(year)
        # PCE for month M is typically released in month M+1, around day 28
        release_month = m + 1
        release_year = y
        if release_month > 12:
            release_month = 1
            release_year += 1
        return f"{release_year}-{release_month:02d}-28T13:30:00Z"
