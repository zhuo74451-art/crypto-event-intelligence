"""Versioned source registry for the historical data factory.

D01: Source feasibility and permission register.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

import yaml

from market_radar.cognition_v2.data_factory.contracts import (
    SourceClass,
    SourceRegistryEntry,
    SCHEMA_VERSION,
)


class SourceRegistry:
    """Versioned registry of public, read-only data sources.

    Every accepted source entry requires:
    - stable source ID and source class
    - authority and fact permission
    - public read-only access method
    - historical coverage
    - parser version
    - rate limit and finite retry policy
    - terms/permission note
    - whether short excerpts may be stored
    - source-health and failure evidence
    - fallback source when available
    """

    def __init__(self):
        self._entries: Dict[str, SourceRegistryEntry] = {}

    def register(self, entry: SourceRegistryEntry) -> None:
        """Register or update a source entry."""
        if entry.source_class == SourceClass.REJECTED:
            raise ValueError(
                f"Cannot register REJECTED source {entry.source_id}. "
                "Use reject() instead."
            )
        self._entries[entry.source_id] = entry

    def reject(self, entry: SourceRegistryEntry) -> None:
        """Add a rejected source (always REJECTED class)."""
        entry.source_class = SourceClass.REJECTED
        self._entries[entry.source_id] = entry

    def get(self, source_id: str) -> Optional[SourceRegistryEntry]:
        return self._entries.get(source_id)

    def all(self) -> List[SourceRegistryEntry]:
        return list(self._entries.values())

    def by_class(self, source_class: SourceClass) -> List[SourceRegistryEntry]:
        return [e for e in self._entries.values() if e.source_class == source_class]

    def summary(self) -> dict:
        """Summary statistics for the registry."""
        classes = {}
        for sc in SourceClass:
            count = len(self.by_class(sc))
            if count > 0:
                classes[sc.value] = count
        return {
            "total_entries": len(self._entries),
            "by_class": classes,
        }

    def to_yaml(self) -> str:
        """Serialize registry to YAML."""
        records = [asdict_clean(e) for e in self._entries.values()]
        records.sort(key=lambda r: r["source_id"])
        return yaml.dump({
            "schema_version": SCHEMA_VERSION,
            "entries": records,
        }, default_flow_style=False, sort_keys=True)

    @classmethod
    def from_yaml(cls, text: str) -> "SourceRegistry":
        """Load registry from YAML."""
        data = yaml.safe_load(text)
        reg = cls()
        for entry_data in data.get("entries", []):
            entry_data["source_class"] = SourceClass(entry_data["source_class"])
            if "historical_coverage_start" in entry_data and entry_data["historical_coverage_start"]:
                entry_data["historical_coverage_start"] = datetime.fromisoformat(
                    entry_data["historical_coverage_start"]
                )
            if "historical_coverage_end" in entry_data and entry_data["historical_coverage_end"]:
                entry_data["historical_coverage_end"] = datetime.fromisoformat(
                    entry_data["historical_coverage_end"]
                )
            if "created_at" in entry_data and entry_data["created_at"]:
                entry_data["created_at"] = datetime.fromisoformat(
                    entry_data["created_at"]
                )
            reg._entries[entry_data["source_id"]] = SourceRegistryEntry(**entry_data)
        return reg


def asdict_clean(obj) -> dict:
    """Convert a dataclass to dict, converting datetimes to ISO strings."""
    from dataclasses import asdict

    def _convert(v):
        if isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, Enum):
            return v.value
        return v

    raw = asdict(obj)
    return {k: _convert(v) for k, v in raw.items()}


# ──────────────────────────────────────────────────────────────────────────────
# Default registry — public, read-only sources
# ──────────────────────────────────────────────────────────────────────────────

def build_default_registry() -> SourceRegistry:
    """Build the initial source registry with known public sources."""
    reg = SourceRegistry()

    # ── Regulatory ──
    reg.register(SourceRegistryEntry(
        source_id="sec-edgar",
        name="SEC EDGAR — Corporate Filings",
        source_class=SourceClass.QUALIFYING_EVIDENCE,
        authority="government_official",
        fact_permission="public_record",
        access_method="https GET (rate-limited, robots.txt permitted)",
        base_url="https://www.sec.gov/cgi-bin/browse-edgar",
        historical_coverage_start=datetime(2021, 1, 1, tzinfo=timezone.utc),
        historical_coverage_end=datetime(2026, 6, 30, tzinfo=timezone.utc),
        rate_limit_per_second=10.0,
        retry_limit=3,
        terms_note="Public data, no API key required. Respect robots.txt.",
        short_excerpts_allowed=True,
    ))
    reg.register(SourceRegistryEntry(
        source_id="cftc-enforcement",
        name="CFTC Enforcement Actions",
        source_class=SourceClass.QUALIFYING_EVIDENCE,
        authority="government_official",
        fact_permission="public_record",
        access_method="https GET",
        base_url="https://www.cftc.gov/cpenforcement",
        historical_coverage_start=datetime(2021, 1, 1, tzinfo=timezone.utc),
        historical_coverage_end=datetime(2026, 6, 30, tzinfo=timezone.utc),
        rate_limit_per_second=5.0,
        retry_limit=3,
        terms_note="Public government website.",
        short_excerpts_allowed=True,
    ))

    # ── Corporate ──
    reg.register(SourceRegistryEntry(
        source_id="company-press-releases",
        name="Public Company Press Releases (PRNewswire, BusinessWire, GlobeNewswire)",
        source_class=SourceClass.DISCOVERY_ONLY,
        authority="corporate_official",
        fact_permission="public_communication",
        access_method="https GET",
        base_url="https://www.prnewswire.com",
        historical_coverage_start=datetime(2021, 1, 1, tzinfo=timezone.utc),
        historical_coverage_end=datetime(2026, 6, 30, tzinfo=timezone.utc),
        rate_limit_per_second=5.0,
        retry_limit=2,
        terms_note="Public press release aggregators. Verify with primary source.",
        short_excerpts_allowed=True,
        fallback_source_id="sec-edgar",
    ))

    # ── Macro ──
    reg.register(SourceRegistryEntry(
        source_id="federal-reserve",
        name="Federal Reserve — Press Releases and Speeches",
        source_class=SourceClass.QUALIFYING_EVIDENCE,
        authority="government_official",
        fact_permission="public_record",
        access_method="https GET",
        base_url="https://www.federalreserve.gov/newsevents.htm",
        historical_coverage_start=datetime(2021, 1, 1, tzinfo=timezone.utc),
        historical_coverage_end=datetime(2026, 6, 30, tzinfo=timezone.utc),
        rate_limit_per_second=10.0,
        retry_limit=3,
        terms_note="Public US government data.",
        short_excerpts_allowed=True,
    ))
    reg.register(SourceRegistryEntry(
        source_id="bls-economic-releases",
        name="Bureau of Labor Statistics — Economic Releases",
        source_class=SourceClass.QUALIFYING_EVIDENCE,
        authority="government_official",
        fact_permission="public_record",
        access_method="https GET",
        base_url="https://www.bls.gov/news.release/",
        historical_coverage_start=datetime(2021, 1, 1, tzinfo=timezone.utc),
        historical_coverage_end=datetime(2026, 6, 30, tzinfo=timezone.utc),
        rate_limit_per_second=10.0,
        retry_limit=3,
        terms_note="Public US government data.",
        short_excerpts_allowed=True,
    ))
    reg.register(SourceRegistryEntry(
        source_id="eurostat",
        name="Eurostat — Economic Indicators",
        source_class=SourceClass.QUALIFYING_EVIDENCE,
        authority="government_official",
        fact_permission="public_record",
        access_method="https GET (API)",
        base_url="https://ec.europa.eu/eurostat/api/dissemination/",
        historical_coverage_start=datetime(2021, 1, 1, tzinfo=timezone.utc),
        historical_coverage_end=datetime(2026, 6, 30, tzinfo=timezone.utc),
        rate_limit_per_second=30.0,
        retry_limit=3,
        terms_note="Public EU statistics. Free API access.",
        short_excerpts_allowed=True,
    ))

    # ── Technology ──
    reg.register(SourceRegistryEntry(
        source_id="github-security-advisories",
        name="GitHub Security Advisories",
        source_class=SourceClass.QUALIFYING_EVIDENCE,
        authority="platform_official",
        fact_permission="public_disclosure",
        access_method="https GET (API)",
        base_url="https://api.github.com/advisories",
        historical_coverage_start=datetime(2021, 1, 1, tzinfo=timezone.utc),
        historical_coverage_end=datetime(2026, 6, 30, tzinfo=timezone.utc),
        rate_limit_per_second=5.0,
        retry_limit=3,
        terms_note="Public API, no key required for public advisories.",
        short_excerpts_allowed=True,
    ))
    reg.register(SourceRegistryEntry(
        source_id="nvd-nist",
        name="NVD — National Vulnerability Database",
        source_class=SourceClass.QUALIFYING_EVIDENCE,
        authority="government_official",
        fact_permission="public_record",
        access_method="https GET (API)",
        base_url="https://services.nvd.nist.gov/rest/json/cves/2.0",
        historical_coverage_start=datetime(2021, 1, 1, tzinfo=timezone.utc),
        historical_coverage_end=datetime(2026, 6, 30, tzinfo=timezone.utc),
        rate_limit_per_second=5.0,
        retry_limit=3,
        terms_note="Public US government vulnerability data.",
        short_excerpts_allowed=True,
    ))

    # ── Market ──
    reg.register(SourceRegistryEntry(
        source_id="binance-public",
        name="Binance Public Market Data",
        source_class=SourceClass.MARKET_OUTCOME,
        authority="exchange_official",
        fact_permission="public_market_data",
        access_method="https GET (REST API, no key for public endpoints)",
        base_url="https://api.binance.com/api/v3",
        historical_coverage_start=datetime(2021, 1, 1, tzinfo=timezone.utc),
        historical_coverage_end=datetime(2026, 6, 30, tzinfo=timezone.utc),
        rate_limit_per_second=20.0,
        retry_limit=3,
        terms_note="Public market data endpoints. No API key needed for klines/ticker.",
        short_excerpts_allowed=True,
    ))
    reg.register(SourceRegistryEntry(
        source_id="coinbase-public",
        name="Coinbase Public Market Data",
        source_class=SourceClass.MARKET_OUTCOME,
        authority="exchange_official",
        fact_permission="public_market_data",
        access_method="https GET (REST API)",
        base_url="https://api.exchange.coinbase.com",
        historical_coverage_start=datetime(2021, 1, 1, tzinfo=timezone.utc),
        historical_coverage_end=datetime(2026, 6, 30, tzinfo=timezone.utc),
        rate_limit_per_second=10.0,
        retry_limit=3,
        terms_note="Public market data. No key for public OHLCV.",
        short_excerpts_allowed=True,
        fallback_source_id="binance-public",
    ))

    # ── Security ──
    reg.register(SourceRegistryEntry(
        source_id="cisa-alerts",
        name="CISA Cybersecurity Alerts",
        source_class=SourceClass.QUALIFYING_EVIDENCE,
        authority="government_official",
        fact_permission="public_record",
        access_method="https GET",
        base_url="https://www.cisa.gov/news-events/cybersecurity-advisories",
        historical_coverage_start=datetime(2021, 1, 1, tzinfo=timezone.utc),
        historical_coverage_end=datetime(2026, 6, 30, tzinfo=timezone.utc),
        rate_limit_per_second=5.0,
        retry_limit=3,
        terms_note="Public US government cybersecurity advisories.",
        short_excerpts_allowed=True,
    ))

    return reg
