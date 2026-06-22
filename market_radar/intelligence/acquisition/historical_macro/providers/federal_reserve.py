"""Federal Reserve provider.

Provides:
- FOMC Rate Decisions (Federal Funds Target Rate)

Sources:
- Federal Reserve Board: historical FOMC meeting calendars and rate decisions
- FRB website: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
import urllib.error
from typing import Any, Optional

from .base import ProviderBase
from ..contracts import (
    MacroReleaseEventV1,
    MacroRevisionRecordV1,
    EventFamily,
    RevisionStatus,
    utc_now, utc_parse,
)


FOMC_SERIES_MAP: dict[str, dict[str, Any]] = {
    "FEDFUNDS": {
        "family": "us_fomc_rate_decision",
        "unit": "percent",
        "name": "Federal Funds Target Rate",
    },
}


class FederalReserveProvider(ProviderBase):
    """Provider for Federal Reserve / FOMC data."""

    provider_name: str = "federal_reserve"
    base_url: str = "https://www.federalreserve.gov/"
    release_calendar_url: str = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

    def __init__(self, cache_dir: str = "", output_dir: str = ""):
        super().__init__(cache_dir=cache_dir, output_dir=output_dir)
        self.rate_limit_delay = 1.0

    def fetch_release_calendar(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Fetch FOMC meeting calendar from the FRB website."""
        url = self.release_calendar_url
        self._rate_limit()

        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                raw_content = resp.read()
            self.save_raw_snapshot(url, raw_content, "text/html")
            html = raw_content.decode("utf-8", errors="replace")

            # Parse historical meeting dates from HTML
            # Pattern: FOMC meetings listed in tables
            records = []
            # Look for meeting date patterns like "2024-01-30" or "January 30-31, 2024"
            date_patterns = re.findall(
                r'(\d{4})[-\u2013](\d{1,2})[-\u2013](\d{1,2})',
                html,
            )
            for year_str, start_month, start_day in date_patterns:
                year = int(year_str)
                if year < 2010 or year > 2026:
                    continue
                records.append({
                    "year": year_str,
                    "month": start_month,
                    "day": start_day,
                    "type": "fomc_meeting",
                })
            return records
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"  [Fed] Error fetching calendar: {e}")
            return []

    def fetch_release_values(self, series_id: str, start_year: str, end_year: str) -> list[dict[str, Any]]:
        """Fetch FOMC rate decisions from FRB historical data.

        Uses the Federal Reserve Board's historical rate change data.
        """
        if series_id != "FEDFUNDS":
            return []

        # FRB publishes historical target rate changes
        url = "https://www.federalreserve.gov/monetarypolicy/fomc historical.htm"
        # Note: the actual URL contains no space; using the correct one
        url = "https://www.federalreserve.gov/monetarypolicy/fomchistorical2005.htm"
        self._rate_limit()

        records = []
        for hist_year in range(int(start_year), int(end_year) + 1):
            try:
                if hist_year <= 2007:
                    hist_url = f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{hist_year}.htm"
                else:
                    hist_url = f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{hist_year}.htm"

                req = urllib.request.Request(hist_url, headers={"User-Agent": self.user_agent})
                with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                    raw_content = resp.read()
                self.save_raw_snapshot(hist_url, raw_content, "text/html")
                html = raw_content.decode("utf-8", errors="replace")

                # Parse tables for rate decisions
                # FOMC press release dates and rate changes
                rate_pattern = re.findall(
                    r'(\w+ \d+,? \d{4}).*?(\d+(?:\.\d+)?)[-\u2013](\d+(?:\.\d+)?)\s*percent',
                    html, re.IGNORECASE,
                )
                for date_str, old_rate, new_rate in rate_pattern:
                    records.append({
                        "date": date_str,
                        "old_rate": float(old_rate),
                        "new_rate": float(new_rate),
                    })
            except (urllib.error.URLError, urllib.error.HTTPError) as e:
                print(f"  [Fed] Error fetching year {hist_year}: {e}")
                continue

        return records

    def fetch_revision_history(self, series_id: str) -> list[dict[str, Any]]:
        return []

    def normalize_release(self, raw: dict[str, Any]) -> Optional[MacroReleaseEventV1]:
        """Normalize a FOMC rate decision record."""
        series_id = "FEDFUNDS"
        config = FOMC_SERIES_MAP[series_id]
        family = config["family"]

        date_str = raw.get("date", "")
        new_rate = raw.get("new_rate")
        old_rate = raw.get("old_rate")

        if not date_str or new_rate is None:
            return None

        # Parse date
        try:
            from datetime import datetime
            for fmt in ("%B %d, %Y", "%B %d %Y", "%d %B %Y"):
                try:
                    dt = datetime.strptime(date_str, fmt)
                    ref_period = dt.strftime("%Y-%m")
                    release_utc = dt.strftime("%Y-%m-%dT18:00:00Z")  # ~2pm ET
                    break
                except ValueError:
                    continue
            else:
                return None
        except Exception:
            return None

        event = MacroReleaseEventV1(
            event_family=family,
            series_id=series_id,
            reference_period=ref_period,
            actual_release_at_utc=release_utc,
            actual_initial=new_rate,
            actual_initial_unit=config["unit"],
            prior_as_known_then=old_rate,
            revision_status="initial",
            official_source_name="Federal Reserve Board",
            official_source_url="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
            data_quality_flags=[],
        )
        return event

    def normalize_revision(self, raw: dict[str, Any]) -> Optional[MacroRevisionRecordV1]:
        return None
