#!/usr/bin/env python3
"""Print the 13-domain cognitive coverage report.

Usage:
    python scripts/research_intelligence/build_coverage_report.py
"""

import sys
from pathlib import Path

# ── Add project root to sys.path ──────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research.intelligence.coverage.domain_catalog import build_domain_catalog
from research.intelligence.contracts.common import CoverageLevel


def coverage_summary(domains: list) -> dict[str, int]:
    """Count how many domains are at each coverage level."""
    summary: dict[str, int] = {}
    for d in domains:
        level_key = d.level.value.upper() if hasattr(d, "level") else "UNKNOWN"
        summary[level_key] = summary.get(level_key, 0) + 1
    return summary


def by_priority(domains: list) -> dict:
    """Group domains by priority."""
    groups: dict = {}
    for d in domains:
        key = d.priority.value.upper() if hasattr(d, "priority") else "UNKNOWN"
        groups.setdefault(key, []).append(d)
    return groups


def main() -> None:
    domains = build_domain_catalog()

    print("=" * 78)
    print("  RESEARCH INTELLIGENCE -- 13-DOMAIN COGNITIVE COVERAGE REPORT")
    print("=" * 78)

    # ── Per-domain detail ──────────────────────────────────────────────
    print(f"\n{'Domain (ID)':<60} {'Level':<20} {'Priority':<10}")
    print("-" * 90)
    for d in sorted(domains, key=lambda x: (x.priority.value if hasattr(x, "priority") else "z", x.domain_id)):
        level_name = d.level.value.upper() if hasattr(d, "level") else "UNKNOWN"
        pri = d.priority.value.upper() if hasattr(d, "priority") else "?"
        label = f"{d.name} ({d.domain_id})" if hasattr(d, "name") else d.domain_id
        print(f"{label:<60} {level_name:<20} {pri:<10}")

    # ── Coverage summary ──────────────────────────────────────────────
    print("\n" + "-" * 78)
    print("  COVERAGE SUMMARY")
    summary = coverage_summary(domains)
    for level_label, count in sorted(summary.items()):
        bar = "#" * count + "." * (13 - count)
        print(f"  {level_label:<35} {count:>2}/13  {bar}")

    # ── By priority ────────────────────────────────────────────────────
    print("\n" + "-" * 78)
    print("  BY PRIORITY")
    by_prio = by_priority(domains)
    for priority, domains_list in sorted(by_prio.items()):
        print(f"\n  {priority} ({len(domains_list)} domains):")
        for d in domains_list:
            name = d.name if hasattr(d, "name") else d.domain_id
            level_name = d.level.value.upper() if hasattr(d, "level") else "?"
            print(f"    {name:<55} {level_name}")

    # ── Overall assessment ─────────────────────────────────────────────
    print("\n" + "=" * 78)
    l0 = summary.get("NONE", 0)
    l1 = summary.get("MINIMAL", 0) + summary.get("PARTIAL", 0)
    print(f"  Overall: {l0} domains at L0 (absent), {l1} at L1/L2 (partial coverage)")
    print("=" * 78)


if __name__ == "__main__":
    main()
