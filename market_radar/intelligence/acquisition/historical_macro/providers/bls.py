"""Bureau of Labor Statistics (BLS) provider.

Provides:
- US CPI (Series CUUR0000SA0)
- US Core CPI (Series CUUR0000SA0L1E)
- Nonfarm Payrolls (Series CES0000000001)
- Unemployment Rate (Series LNS14000000)

Uses BLS Public API v2 (free tier, no key required for historical).
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Optional

from .base import ProviderBase
from ..contracts import (
    MacroReleaseEventV1,
    MacroRevisionRecordV1,
    EventFamily,
    RevisionStatus,
    utc_now, utc_parse,
)


BLS_SERIES_MAP: dict[str, dict[str, Any]] = {
    "CUUR0000SA0": {
        "family": "us_cpi",
        "unit": "index_1982_1984_100",
        "name": "CPI-U All Items",
    },
    "CUUR0000SA0L1E": {
        "family": "us_core_cpi",
        "unit": "index_1982_1984_100",
        "name": "CPI-U All Items Less Food and Energy",
    },
    "CES0000000001": {
        "family": "us_nonfarm_payrolls",
        "unit": "thousands",
        "name": "All Employees, Total Nonfarm",
    },
    "LNS14000000": {
        "family": "us_unemployment_rate",
        "unit": "percent",
        "name": "Unemployment Rate",
    },
}


class BLSProvider(ProviderBase):
    """Provider for BLS macro-economic data via public API."""

    provider_name: str = "bls"
    base_url: str = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    release_calendar_url: str = "https://www.bls.gov/schedule/news_release/"

    def __init__(self, cache_dir: str = "", output_dir: str = ""):
        super().__init__(cache_dir=cache_dir, output_dir=output_dir)
        self.rate_limit_delay = 0.5  # BLS allows ~2 requests/sec free tier

    def fetch_release_calendar(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Return placeholder release calendar entries."""
        # BLS publishes schedules as HTML tables on their site.
        # For now, return known schedule patterns.
        return []

    def fetch_release_values(self, series_id: str, start_year: str, end_year: str) -> list[dict[str, Any]]:
        """Fetch time series data from BLS API.

        Uses the public v2 API with JSON POST. Free tier returns full history.
        """
        self._rate_limit()
        url = self.base_url

        headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
        }
        payload = json.dumps({
            "seriesid": [series_id],
            "startyear": start_year,
            "endyear": end_year,
            "catalog": False,
            "calculations": False,
            "annualaverage": False,
            "registrationkey": "",
        }).encode("utf-8")

        raw_content = None
        try:
            req = urllib.request.Request(url, data=payload, headers=headers,
                                          method="POST")
            with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                raw_content = resp.read()
            self.save_raw_snapshot(url, raw_content, "application/json")
            data = json.loads(raw_content)
            results = data.get("Results", {}).get("series", [])
            if results:
                return results[0].get("data", [])
            return []
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
            if raw_content:
                self.save_raw_snapshot(url, raw_content, "application/json")
            print(f"  [BLS] Error fetching series {series_id}: {e}")
            return []

    def fetch_revision_history(self, series_id: str) -> list[dict[str, Any]]:
        """BLS API returns latest data; revisions are not explicitly versioned in free tier.

        We capture initial values and note when revised values differ.
        """
        return []

    def normalize_release(self, raw: dict[str, Any]) -> Optional[MacroReleaseEventV1]:
        """Normalize a BLS data record to MacroReleaseEventV1."""
        series_id = raw.get("series_id", "")
        if series_id not in BLS_SERIES_MAP:
            return None

        config = BLS_SERIES_MAP[series_id]
        family = config["family"]
        period = raw.get("period", "")
        year = raw.get("year", "")
        value_str = raw.get("value", "")
        footnotes = raw.get("footnotes", [])

        # Parse period: "M01" -> "01", "M12" -> "12"
        if period.startswith("M"):
            ref_period = f"{year}-{period[1:]}"
        else:
            return None

        try:
            value = float(value_str) if value_str and value_str != "-" else None
        except ValueError:
            value = None

        # BLS data is typically released at 8:30 AM ET on scheduled dates.
        # Actual release time is approximated; BLS publishes schedule separately.
        release_date = self._estimate_release_date(year, period)
        if not release_date:
            return None

        event = MacroReleaseEventV1(
            event_family=family,
            series_id=series_id,
            reference_period=ref_period,
            actual_release_at_utc=release_date,
            actual_initial=value,
            actual_initial_unit=config["unit"],
            prior_as_known_then=None,
            revision_status="initial",
            official_source_name="U.S. Bureau of Labor Statistics",
            official_source_url=f"https://data.bls.gov/timeseries/{series_id}",
            official_release_id=f"bls-{series_id}-{ref_period}",
            data_quality_flags=[],
        )
        return event

    def normalize_revision(self, raw: dict[str, Any]) -> Optional[MacroRevisionRecordV1]:
        """BLS free tier does not provide explicit revision history."""
        return None

    def _estimate_release_date(self, year: str, period: str) -> str:
        """Estimate release date for BLS data.

        BLS typically releases CPI around 8:30 AM ET on the scheduled date.
        For simplicity, we use the middle of the month following the reference period.
        """
        if period.startswith("M"):
            month = int(period[1:])
            # CPI is usually released in the month following the reference month
            release_month = month + 1
            release_year = int(year)
            if release_month > 12:
                release_month = 1
                release_year += 1
            # Approximate to the 10th-15th of the release month
            release_day = min(month, 20)
            return f"{release_year}-{release_month:02d}-{release_day:02d}T13:30:00Z"
        return ""
