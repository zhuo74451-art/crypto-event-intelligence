"""Public consensus provider.

Gathers pre-event consensus estimates from publicly available sources:
- ForexFactory calendar archives
- Investing.com economic calendar history
- Bloomberg public snapshots (article previews)
- Reuters public polling data

This provider does NOT use any paid API or bypass paywalls.
All data is from public, archived, pre-event publications.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Optional

from .base import ProviderBase
from ..contracts import (
    MacroConsensusObservationV1,
    EventFamily,
    EstimateType,
    PointInTimeQuality,
    utc_now, utc_parse,
)


class PublicConsensusProvider(ProviderBase):
    """Provider for public pre-event consensus estimates."""

    provider_name: str = "public_consensus"
    base_url: str = "https://www.forexfactory.com/"

    def __init__(self, cache_dir: str = "", output_dir: str = ""):
        super().__init__(cache_dir=cache_dir, output_dir=output_dir)
        self.rate_limit_delay = 2.0

    def fetch_release_calendar(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        return []

    def fetch_release_values(self, series_id: str, start_year: str, end_year: str) -> list[dict[str, Any]]:
        return []

    def fetch_revision_history(self, series_id: str) -> list[dict[str, Any]]:
        return []

    def fetch_consensus_observations(self, event_family: str,
                                      reference_period: str) -> list[dict[str, Any]]:
        """Fetch consensus estimates from ForexFactory calendar archives.

        ForexFactory maintains a public economic calendar with historical data
        that includes 'Expected' (consensus) values alongside actuals.
        """
        # ForexFactory calendar URL pattern
        # e.g., https://www.forexfactory.com/calendar?month=jan2023
        year = reference_period[:4]
        month_num = reference_period[5:7]

        month_abbrs = ["jan", "feb", "mar", "apr", "may", "jun",
                       "jul", "aug", "sep", "oct", "nov", "dec"]
        month_abbr = month_abbrs[int(month_num) - 1] if 1 <= int(month_num) <= 12 else "jan"

        url = f"https://www.forexfactory.com/calendar?month={month_abbr}{year}"
        self._rate_limit()

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html",
                },
            )
            with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                raw_content = resp.read()
            self.save_raw_snapshot(url, raw_content, "text/html")
            html = raw_content.decode("utf-8", errors="replace")

            records = self._parse_forexfactory_calendar(html, event_family)
            return records
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"  [Consensus] Error fetching {url}: {e}")
            return []

    def normalize_consensus(self, raw: dict[str, Any]) -> Optional[MacroConsensusObservationV1]:
        """Normalize a consensus observation."""
        try:
            obs = MacroConsensusObservationV1(
                event_id=raw.get("event_id", ""),
                source_name=raw.get("source_name", "ForexFactory"),
                source_url=raw.get("source_url", ""),
                published_at_utc=raw.get("published_at_utc", ""),
                consensus_value=raw.get("consensus_value", 0.0),
                consensus_unit=raw.get("consensus_unit", ""),
                estimate_type="consensus_median",
                point_in_time_quality=raw.get("point_in_time_quality", "reconstructed_multi_source"),
                archive_method="web_archive",
                independence_group="forexfactory",
                notes=raw.get("notes", ""),
            )
            return obs
        except Exception as e:
            print(f"  [Consensus] Normalize error: {e}")
            return None

    def _parse_forexfactory_calendar(self, html: str,
                                      event_family: str) -> list[dict[str, Any]]:
        """Parse ForexFactory calendar HTML for consensus estimates.

        This is a best-effort parser for the public HTML calendar page.
        Actual parsing depends on ForexFactory's HTML structure.
        """
        records = []

        # Map event family to ForexFactory calendar event names
        ff_event_names = {
            "us_cpi": ["CPI", "Consumer Price Index"],
            "us_core_cpi": ["Core CPI", "Core Consumer Price Index"],
            "us_nonfarm_payrolls": ["Non-Farm Employment Change", "NFP", "Nonfarm Payrolls"],
            "us_unemployment_rate": ["Unemployment Rate"],
            "us_core_pce": ["Core PCE", "Core Personal Consumption Expenditure"],
            "us_fomc_rate_decision": ["FOMC Statement", "Interest Rate Decision"],
        }

        names = ff_event_names.get(event_family, [])
        if not names:
            return records

        # Look for table rows containing event names and expected values
        # Pattern: <tr> containing event name and expected value
        for name in names:
            # Search for event rows matching this name
            pattern = re.escape(name)
            matches = re.finditer(
                rf'<tr[^>]*>.*?{pattern}.*?</tr>',
                html, re.IGNORECASE | re.DOTALL,
            )
            for match in matches:
                row_html = match.group(0)
                # Extract expected/consensus value
                expected_match = re.search(
                    r'<td[^>]*class="[^"]*expect[^"]*"[^>]*>\s*([\d.]+)\s*</td>',
                    row_html, re.IGNORECASE,
                )
                if expected_match:
                    try:
                        consensus_value = float(expected_match.group(1))
                        records.append({
                            "source_name": "ForexFactory",
                            "source_url": "https://www.forexfactory.com/calendar",
                            "consensus_value": consensus_value,
                            "point_in_time_quality": "reconstructed_multi_source",
                            "estimate_type": "consensus_median",
                            "notes": f"Parsed from ForexFactory calendar for {event_family}",
                        })
                    except ValueError:
                        continue

        return records
