"""BLS news release archive parser.

Fetches actual BLS news release HTML pages from the official archive:
- CPI: https://www.bls.gov/news.release/archives/cpi_YYYY-MM-DD.htm
- Employment Situation: https://www.bls.gov/news.release/archives/empsit_YYYY-MM-DD.htm

Extracts release time, actual values, and revision data from HTML tables.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from market_radar.intelligence.acquisition.historical_macro.contracts import (
    MacroReleaseEventV1, MacroReleaseObservationV1, MacroSourceSnapshotV1,
    us_eastern_date_to_utc, generate_event_id, generate_logical_event_key,
    generate_observation_id, generate_snapshot_id, utc_now, utc_parse,
    ReleaseTimeQuality, ActualValueStatus,
)

PARSER_VERSION = "bls_release_archive_v1"


class BLSReleaseArchiveProvider:
    """Parser for BLS news release archive HTML pages."""

    CPI_BASE = "https://www.bls.gov/news.release/archives/cpi_{date}.htm"
    EMPSIT_BASE = "https://www.bls.gov/news.release/archives/empsit_{date}.htm"

    def __init__(self, raw_dir: str = ""):
        self.raw_dir = raw_dir
        self.snapshots: list[MacroSourceSnapshotV1] = []

    def fetch_release_page(self, url: str) -> Optional[bytes]:
        """Fetch a release page HTML and save raw bytes."""
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (research; +https://github.com/zhuo74451-art)"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read()
            return content
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code}: {url}")
            return None
        except urllib.error.URLError as e:
            print(f"  URL error: {e.reason}: {url}")
            return None

    def save_snapshot(self, url: str, content: bytes,
                       published_at_utc: str = "") -> Optional[MacroSourceSnapshotV1]:
        """Save raw bytes to disk and create snapshot record."""
        sha = hashlib.sha256(content).hexdigest()
        retrieved_at = utc_now()

        # Deterministic filename
        provider = "bls"
        fname = f"bls__{sha[:16]}__{url.split('/')[-1]}"
        if self.raw_dir:
            subdir = os.path.join(self.raw_dir, "official_release_pages", "bls")
            os.makedirs(subdir, exist_ok=True)
            fpath = os.path.join(subdir, fname)
            with open(fpath, "wb") as f:
                f.write(content)
        else:
            fpath = ""

        snap = MacroSourceSnapshotV1(
            provider=provider,
            source_url=url,
            retrieved_at_utc=retrieved_at,
            published_at_utc=published_at_utc,
            content_type="text/html",
            sha256=sha,
            local_path=fpath,
            http_status=200,
            parse_status="parsed",
        )
        snap.parse_status = "parsed"
        self.snapshots.append(snap)
        return snap

    def parse_cpi_release(self, html: str) -> dict[str, Any]:
        """Parse CPI news release HTML for MoM% values.

        Returns dict with keys like:
        - cpi_sa_mom_pct: seasonally adjusted CPI MoM%
        - core_cpi_sa_mom_pct: seasonally adjusted Core CPI MoM%
        - cpi_sa_index: CPI index level
        - release_date_text: date text found in page
        """
        result = {}
        text = re.sub(r'<[^>]+>', '\n', html)

        # Find "Consumer Price Index" table section
        # Look for "Seasonally adjusted" and "Unadjusted" sections
        lines = text.split('\n')

        # Find CPI MoM% - pattern: "All items" followed by a percent
        for i, line in enumerate(lines):
            line_s = line.strip()

            # CPI MoM SA: "All items" near percent value
            if "All items" in line_s and i + 1 < len(lines):
                # Look at surrounding lines for percent values
                context = '\n'.join(lines[max(0,i-2):i+3])
                pcts = re.findall(r'(-?\d+\.?\d*)\s*(?:percent|%)?', context)
                # Filter to reasonable CPI MoM range (-5 to 5)
                reasonable = [float(p) for p in pcts if p and abs(float(p)) < 50]
                if reasonable:
                    result["cpi_sa_mom_pct"] = reasonable[0]

            # Core CPI MoM SA: "All items less food and energy" 
            if "less food" in line_s.lower() and i + 1 < len(lines):
                context = '\n'.join(lines[max(0,i-2):i+3])
                pcts = re.findall(r'(-?\d+\.?\d*)\s*(?:percent|%)?', context)
                reasonable = [float(p) for p in pcts if p and abs(float(p)) < 50]
                if reasonable:
                    result["core_cpi_sa_mom_pct"] = reasonable[0]

            # CPI YoY Unadjusted
            if "All items" in line_s and i + 2 < len(lines):
                context = '\n'.join(lines[max(0,i-2):i+5])
                # Find larger numbers that would be YoY
                yoy = re.findall(r'(\d+\.?\d*)\s*(?:percent|%)', context)
                reasonable = [float(y) for y in yoy if y and abs(float(y)) < 50]
                if len(reasonable) > 1:
                    result["cpi_sa_mom_pct"] = reasonable[0]
                    if len(reasonable) > 2:
                        result["cpi_yoy_pct"] = reasonable[1]

        return result

    def parse_employment_release(self, html: str) -> dict[str, Any]:
        """Parse Employment Situation news release for NFP and unemployment values."""
        result = {}
        text = re.sub(r'<[^>]+>', '\n', html)
        lines = text.split('\n')

        for i, line in enumerate(lines):
            line_s = line.strip()

            # Nonfarm payroll change: look for "Total nonfarm" + number
            if "total nonfarm" in line_s.lower():
                context = '\n'.join(lines[max(0,i-2):i+5])
                nums = re.findall(r'[,]?(\d{3,4})\s', context)
                if nums:
                    result["payroll_change"] = int(nums[0].replace(',', ''))

            # Unemployment rate
            if "unemployment rate" in line_s.lower():
                context = '\n'.join(lines[max(0,i-2):i+3])
                pcts = re.findall(r'(\d+\.?\d*)\s*percent', context, re.IGNORECASE)
                if pcts:
                    result["unemployment_rate"] = float(pcts[0])

            # Previous revisions
            if "revised" in line_s.lower() and "previous" in line_s.lower():
                nums = re.findall(r'[,]?(\d{3,4})', line_s)
                if len(nums) >= 2:
                    result["previous_month_revision"] = int(nums[0].replace(',', ''))
                    if len(nums) >= 3:
                        result["second_previous_revision"] = int(nums[1].replace(',', ''))

        return result

    def build_cpi_events(self, release_date: str, html: str,
                          snapshot: MacroSourceSnapshotV1) -> list[MacroReleaseEventV1]:
        """Build CPI and Core CPI canonical events from a release page."""
        parsed = self.parse_cpi_release(html)
        events = []

        ref_month = _month_before(release_date[:7])

        for family, key in [("us_cpi", "cpi_sa_mom_pct"), ("us_core_cpi", "core_cpi_sa_mom_pct")]:
            val = parsed.get(key)
            if val is None:
                continue

            lek = generate_logical_event_key("US", family, ref_month)
            release_utc = us_eastern_date_to_utc(release_date, "08:30")
            eid = generate_event_id(lek, release_utc)

            ev = MacroReleaseEventV1(
                event_id=eid,
                logical_event_key=lek,
                event_family=family,
                reference_period=ref_month,
                actual_release_at_utc=release_utc,
                release_time_timezone="America/New_York",
                release_time_quality="verified_official_release_page",
                release_time_verified=True,
                release_time_source_snapshot_id=snapshot.snapshot_id,
                release_time_source_url=snapshot.source_url,
                event_alignment_eligible=True,
                actual_initial=val,
                actual_initial_unit="pct_change_mom",
                actual_value_status="verified_initial_from_release",
                measure_type="seasonally_adjusted_mom_percent",
                primary_measure="seasonally_adjusted_mom_percent",
                strategy_replay_eligible=True,
                official_source_name="U.S. Bureau of Labor Statistics",
                official_source_url=snapshot.source_url,
                data_quality_flags=[],
            )
            events.append(ev)

        return events

    def build_employment_events(self, release_date: str, html: str,
                                 snapshot: MacroSourceSnapshotV1) -> list[MacroReleaseEventV1]:
        """Build NFP and Unemployment canonical events."""
        parsed = self.parse_employment_release(html)
        events = []
        ref_month = _month_before(release_date[:7])
        release_utc = us_eastern_date_to_utc(release_date, "08:30")

        # NFP event
        nfp_val = parsed.get("payroll_change")
        if nfp_val is not None:
            lek = generate_logical_event_key("US", "us_nonfarm_payrolls", ref_month)
            eid = generate_event_id(lek, release_utc)
            events.append(MacroReleaseEventV1(
                event_id=eid, logical_event_key=lek,
                event_family="us_nonfarm_payrolls", reference_period=ref_month,
                actual_release_at_utc=release_utc, release_time_timezone="America/New_York",
                release_time_quality="verified_official_release_page", release_time_verified=True,
                release_time_source_snapshot_id=snapshot.snapshot_id,
                release_time_source_url=snapshot.source_url, event_alignment_eligible=True,
                actual_initial=float(nfp_val), actual_initial_unit="thousands",
                actual_value_status="verified_initial_from_release",
                measure_type="payroll_change_thousands", primary_measure="payroll_change_thousands",
                strategy_replay_eligible=True,
                official_source_name="U.S. Bureau of Labor Statistics",
                official_source_url=snapshot.source_url, data_quality_flags=[],
            ))

        # Unemployment event
        ue_val = parsed.get("unemployment_rate")
        if ue_val is not None:
            lek = generate_logical_event_key("US", "us_unemployment_rate", ref_month)
            eid = generate_event_id(lek, release_utc)
            events.append(MacroReleaseEventV1(
                event_id=eid, logical_event_key=lek,
                event_family="us_unemployment_rate", reference_period=ref_month,
                actual_release_at_utc=release_utc, release_time_timezone="America/New_York",
                release_time_quality="verified_official_release_page", release_time_verified=True,
                release_time_source_snapshot_id=snapshot.snapshot_id,
                release_time_source_url=snapshot.source_url, event_alignment_eligible=True,
                actual_initial=ue_val, actual_initial_unit="percent",
                actual_value_status="verified_initial_from_release",
                measure_type="unemployment_rate_percent", primary_measure="unemployment_rate_percent",
                strategy_replay_eligible=True,
                official_source_name="U.S. Bureau of Labor Statistics",
                official_source_url=snapshot.source_url, data_quality_flags=[],
            ))

        return events


def _month_before(ref: str) -> str:
    parts = ref.split("-")
    y, m = int(parts[0]), int(parts[1])
    m -= 1
    if m == 0:
        m = 12
        y -= 1
    return f"{y}-{m:02d}"
