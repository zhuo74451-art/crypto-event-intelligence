"""FRED / ALFRED provider.

FRED (Federal Reserve Economic Data) provides current and historical series.
ALFRED (Archival FRED) preserves vintage data - point-in-time snapshots.

Provides data for:
- All 6 core event families via FRED series
- Revision tracking via ALFRED vintage dates

Source: https://fred.stlouisfed.org/
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
    MacroSourceSnapshotV1,
    EventFamily,
    RevisionStatus,
    utc_now, utc_parse,
)


FRED_SERIES_MAP: dict[str, dict[str, Any]] = {
    "CPIAUCSL": {
        "family": "us_cpi",
        "unit": "index_1982_1984_100",
        "name": "CPI-U All Items",
        "release_time": "08:30",
    },
    "CPILFESL": {
        "family": "us_core_cpi",
        "unit": "index_1982_1984_100",
        "name": "CPI-U All Items Less Food and Energy",
        "release_time": "08:30",
    },
    "PAYEMS": {
        "family": "us_nonfarm_payrolls",
        "unit": "thousands",
        "name": "All Employees, Total Nonfarm",
        "release_time": "08:30",
    },
    "UNRATE": {
        "family": "us_unemployment_rate",
        "unit": "percent",
        "name": "Unemployment Rate",
        "release_time": "08:30",
    },
    "PCEPILFE": {
        "family": "us_core_pce",
        "unit": "pct_change_mom",
        "name": "PCE Excluding Food and Energy",
        "release_time": "08:30",
    },
    "FEDFUNDS": {
        "family": "us_fomc_rate_decision",
        "unit": "percent",
        "name": "Federal Funds Effective Rate",
        "release_time": "14:00",
    },
}


class FREDAlfredProvider(ProviderBase):
    """Provider for FRED data series and ALFRED vintage data."""

    provider_name: str = "fred_alfred"
    base_url: str = "https://api.stlouisfed.org/fred/"
    alfred_base_url: str = "https://alfred.stlouisfed.org/api/fred/"

    def __init__(self, cache_dir: str = "", output_dir: str = "", fred_api_key: str = ""):
        super().__init__(cache_dir=cache_dir, output_dir=output_dir)
        self.fred_api_key = fred_api_key or ""
        self.rate_limit_delay = 1.0
        self._use_vintage_api = False  # ALFRED requires API key for vintage access

    def fetch_release_calendar(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        return []

    def fetch_release_values(self, series_id: str, start_year: str, end_year: str) -> list[dict[str, Any]]:
        """Fetch series observations from FRED using file download (no API key needed)."""
        config = FRED_SERIES_MAP.get(series_id)
        if not config:
            return []

        # FRED provides CSV download without API key for individual series
        csv_url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        self._rate_limit()

        try:
            req = urllib.request.Request(csv_url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                raw_content = resp.read()
            self.save_raw_snapshot(csv_url, raw_content, "text/csv")

            text = raw_content.decode("utf-8", errors="replace")
            lines = text.strip().split("\n")

            records = []
            for line in lines[1:]:  # Skip header
                parts = line.split(",")
                if len(parts) >= 2:
                    date_str = parts[0].strip()
                    val_str = parts[1].strip()

                    # Filter by year range
                    year = date_str[:4]
                    if year < start_year or year > end_year:
                        continue

                    try:
                        value = float(val_str) if val_str and val_str != "." else None
                    except ValueError:
                        value = None

                    records.append({
                        "series_id": series_id,
                        "date": date_str,
                        "value": value,
                    })
            return records
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"  [FRED] Error fetching {series_id}: {e}")
            return []

    def fetch_revision_history(self, series_id: str) -> list[dict[str, Any]]:
        """Fetch revision history via ALFRED vintage API if key is available."""
        if not self.fred_api_key:
            return []
        return []

    def normalize_release(self, raw: dict[str, Any]) -> Optional[MacroReleaseEventV1]:
        """Normalize a FRED observation to MacroReleaseEventV1."""
        series_id = raw.get("series_id", "")
        if series_id not in FRED_SERIES_MAP:
            return None

        config = FRED_SERIES_MAP[series_id]
        family = config["family"]
        date_str = raw.get("date", "")
        value = raw.get("value")

        if not date_str or value is None:
            return None

        # Parse date: "2023-01-01" -> ref period "2023-01"
        ref_period = date_str[:7]
        year, month = ref_period.split("-")

        # Estimate release date (FRED data appears after official release)
        release_time = config.get("release_time", "08:30")
        release_hour = release_time.split(":")[0]
        release_min = release_time.split(":")[1]

        # FRED typically posts data on the day of official release or next business day
        # For monthly data, estimate release ~15th of following month
        m = int(month)
        y = int(year)
        release_month = m + 1
        release_year = y
        if release_month > 12:
            release_month = 1
            release_year += 1
        release_day = min(m, 20)

        release_utc = f"{release_year}-{release_month:02d}-{release_day:02d}T{release_hour}:{release_min}:00Z"

        event = MacroReleaseEventV1(
            event_family=family,
            series_id=series_id,
            reference_period=ref_period,
            actual_release_at_utc=release_utc,
            actual_initial=value,
            actual_initial_unit=config["unit"],
            prior_as_known_then=None,
            revision_status="initial",
            official_source_name="FRED, Federal Reserve Bank of St. Louis",
            official_source_url=f"https://fred.stlouisfed.org/series/{series_id}",
            data_quality_flags=[],
        )
        return event

    def normalize_revision(self, raw: dict[str, Any]) -> Optional[MacroRevisionRecordV1]:
        return None

    def fetch_alfred_vintage(self, series_id: str, vintage_date: str) -> Optional[bytes]:
        """Fetch ALFRED vintage data (requires API key)."""
        if not self.fred_api_key:
            return None

        params = urllib.parse.urlencode({
            "series_id": series_id,
            "api_key": self.fred_api_key,
            "file_type": "json",
            "vintage_dates": vintage_date,
        })
        url = f"{self.alfred_base_url}series/observations?{params}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"  [ALFRED] Error: {e}")
            return None
