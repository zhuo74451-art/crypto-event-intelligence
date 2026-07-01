"""Versioned source registry for the historical data factory.

D01/C01: Source feasibility and permission register with explicit
source-to-family bindings. Every source has exact counts.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set

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

    def count(self) -> int:
        return len(self._entries)

    def summary(self) -> dict:
        """Summary statistics for the registry."""
        classes = {}
        for sc in SourceClass:
            count = len(self.by_class(sc))
            if count > 0:
                classes[sc.value] = count
        return {
            "total_entries": self.count(),
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
            for time_field in ("historical_coverage_start", "historical_coverage_end", "created_at"):
                val = entry_data.get(time_field)
                if val:
                    entry_data[time_field] = datetime.fromisoformat(val)
            reg._entries[entry_data["source_id"]] = SourceRegistryEntry(**entry_data)
        return reg

    def source_family_mapping(self) -> Dict[str, str]:
        """Return source_id -> event_family mapping."""
        return {}


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
# Family-bound source registry
# ──────────────────────────────────────────────────────────────────────────────

class FamilyBoundRegistry(SourceRegistry):
    """Registry with explicit source-to-family bindings.

    One source_id may map to one primary family. Sources that serve
    multiple families are registered under their primary family with
    secondary_families listed.
    """

    def __init__(self):
        super().__init__()
        self._family_bindings: Dict[str, str] = {}  # source_id -> family
        self._secondary_families: Dict[str, List[str]] = {}

    def bind_to_family(
        self, source_id: str, family: str,
        secondary_families: Optional[List[str]] = None,
    ) -> None:
        """Bind a registered source to an event family."""
        if source_id not in self._entries:
            raise ValueError(f"Source '{source_id}' not registered")
        self._family_bindings[source_id] = family
        if secondary_families:
            self._secondary_families[source_id] = secondary_families

    def source_family_mapping(self) -> Dict[str, str]:
        return dict(self._family_bindings)

    def family_binding_counts(self) -> Dict[str, int]:
        """Count unique sources per family (primary binding)."""
        counts: Dict[str, int] = {}
        for sid, family in self._family_bindings.items():
            counts[family] = counts.get(family, 0) + 1
        return counts

    def families_with_sources(self) -> Dict[str, List[str]]:
        """Family -> [source_id] mapping."""
        result: Dict[str, List[str]] = {}
        for sid, family in self._family_bindings.items():
            if family not in result:
                result[family] = []
            result[family].append(sid)
        return result

    def to_yaml(self) -> str:
        data = {
            "schema_version": SCHEMA_VERSION,
            "entries": [asdict_clean(e) for e in self._entries.values()],
            "family_bindings": {
                sid: {"primary": f, "secondary": self._secondary_families.get(sid, [])}
                for sid, f in self._family_bindings.items()
            },
        }
        return yaml.dump(data, default_flow_style=False, sort_keys=True)

    @classmethod
    def from_yaml(cls, text: str) -> "FamilyBoundRegistry":
        data = yaml.safe_load(text)
        reg = cls()
        for entry_data in data.get("entries", []):
            entry_data["source_class"] = SourceClass(entry_data["source_class"])
            for time_field in ("historical_coverage_start", "historical_coverage_end", "created_at"):
                val = entry_data.get(time_field)
                if val:
                    entry_data[time_field] = datetime.fromisoformat(val)
            reg._entries[entry_data["source_id"]] = SourceRegistryEntry(**entry_data)
        for sid, binding in data.get("family_bindings", {}).items():
            reg._family_bindings[sid] = binding["primary"]
            if binding.get("secondary"):
                reg._secondary_families[sid] = binding["secondary"]
        return reg


# ──────────────────────────────────────────────────────────────────────────────
# Default registry — public, read-only sources with family bindings
# ──────────────────────────────────────────────────────────────────────────────

def build_default_registry() -> FamilyBoundRegistry:
    """Build the initial source registry with family bindings.

    11 unique source IDs, each bound to exactly one primary family.
    """
    reg = FamilyBoundRegistry()

    # ── Regulatory ──
    reg.register(SourceRegistryEntry(
        source_id="sec-edgar",
        name="SEC EDGAR — Corporate Filings",
        source_class=SourceClass.QUALIFYING_EVIDENCE,
        authority="government_official",
        fact_permission="public_record",
        access_method="https GET (rate-limited, robots.txt permitted)",
        base_url="https://www.sec.gov/cgi-bin/browse-edgar",
        rate_limit_per_second=10.0, retry_limit=3,
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
        rate_limit_per_second=5.0, retry_limit=3,
        terms_note="Public government website.",
        short_excerpts_allowed=True,
    ))
    reg.bind_to_family("sec-edgar", "regulatory")
    reg.bind_to_family("cftc-enforcement", "regulatory")

    # ── Corporate ──
    reg.register(SourceRegistryEntry(
        source_id="company-press-releases",
        name="Public Company Press Releases",
        source_class=SourceClass.DISCOVERY_ONLY,
        authority="corporate_official",
        fact_permission="public_communication",
        access_method="https GET",
        base_url="https://www.prnewswire.com",
        rate_limit_per_second=5.0, retry_limit=2,
        terms_note="Public press release aggregators. Verify with primary source.",
        short_excerpts_allowed=True,
        fallback_source_id="sec-edgar",
    ))
    reg.bind_to_family("company-press-releases", "corporate")

    # ── Macro ──
    reg.register(SourceRegistryEntry(
        source_id="federal-reserve",
        name="Federal Reserve — Press Releases and Speeches",
        source_class=SourceClass.QUALIFYING_EVIDENCE,
        authority="government_official",
        fact_permission="public_record",
        access_method="https GET",
        base_url="https://www.federalreserve.gov/newsevents.htm",
        rate_limit_per_second=10.0, retry_limit=3,
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
        rate_limit_per_second=10.0, retry_limit=3,
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
        rate_limit_per_second=30.0, retry_limit=3,
        terms_note="Public EU statistics. Free API access.",
        short_excerpts_allowed=True,
    ))
    reg.bind_to_family("federal-reserve", "macro")
    reg.bind_to_family("bls-economic-releases", "macro")
    reg.bind_to_family("eurostat", "macro")

    # ── Technology ──
    reg.register(SourceRegistryEntry(
        source_id="github-security-advisories",
        name="GitHub Security Advisories",
        source_class=SourceClass.QUALIFYING_EVIDENCE,
        authority="platform_official",
        fact_permission="public_disclosure",
        access_method="https GET (API)",
        base_url="https://api.github.com/advisories",
        rate_limit_per_second=5.0, retry_limit=3,
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
        rate_limit_per_second=5.0, retry_limit=3,
        terms_note="Public US government vulnerability data.",
        short_excerpts_allowed=True,
    ))
    reg.bind_to_family("github-security-advisories", "technology")
    reg.bind_to_family("nvd-nist", "technology")

    # ── Market ──
    reg.register(SourceRegistryEntry(
        source_id="binance-public",
        name="Binance Public Market Data",
        source_class=SourceClass.MARKET_OUTCOME,
        authority="exchange_official",
        fact_permission="public_market_data",
        access_method="https GET (REST API)",
        base_url="https://api.binance.com/api/v3",
        rate_limit_per_second=20.0, retry_limit=3,
        terms_note="Public market data endpoints. No API key needed.",
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
        rate_limit_per_second=10.0, retry_limit=3,
        terms_note="Public market data. No key for public OHLCV.",
        short_excerpts_allowed=True,
        fallback_source_id="binance-public",
    ))
    reg.bind_to_family("binance-public", "market")
    reg.bind_to_family("coinbase-public", "market")

    # ── Security ──
    reg.register(SourceRegistryEntry(
        source_id="cisa-alerts",
        name="CISA Cybersecurity Alerts",
        source_class=SourceClass.QUALIFYING_EVIDENCE,
        authority="government_official",
        fact_permission="public_record",
        access_method="https GET",
        base_url="https://www.cisa.gov/news-events/cybersecurity-advisories",
        rate_limit_per_second=5.0, retry_limit=3,
        terms_note="Public US government cybersecurity advisories.",
        short_excerpts_allowed=True,
    ))
    reg.bind_to_family("cisa-alerts", "security")

    # ── Cross-family sources (NVD also serves security) ──
    reg.bind_to_family("nvd-nist", "technology", secondary_families=["security"])

    return reg
