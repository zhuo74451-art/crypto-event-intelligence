#!/usr/bin/env python3
"""Print the claim conflict report.

Usage:
    python scripts/research_intelligence/build_conflict_report.py
"""

import sys
from pathlib import Path

# ── Add project root to sys.path ──────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research.intelligence.contracts.conflict import ClaimConflict
from research.intelligence.contracts.common import ConflictType, ResolutionStatus
from research.intelligence.registries.conflict_registry import ConflictRegistry


def main() -> None:
    registry = ConflictRegistry()

    print("=" * 78)
    print("  CLAIM CONFLICT REPORT")
    print("=" * 78)

    total = registry.count()

    if total == 0:
        print("\n  No conflicts registered.")
        print("\n  To register conflicts, add ClaimConflict objects to a")
        print("  ConflictRegistry and re-run this report.")
        print()

        # Show example usage
        print("  Example:")
        print('    cf = ClaimConflict(claim_ids=["CL-001", "CL-002"],')
        print('                        description="Disagreement on market impact")')
        print("    registry.add(cf)")
        print("    python scripts/research_intelligence/build_conflict_report.py")
        return

    unresolved = registry.find_unresolved()
    by_type: dict[ConflictType, list[ClaimConflict]] = {}
    for cf in registry.list_all():
        by_type.setdefault(cf.conflict_type, []).append(cf)

    print(f"\n  Total conflicts:  {total}")
    print(f"  Unresolved:       {len(unresolved)}")
    print(f"  Resolved:         {total - len(unresolved)}")
    print()

    # ── By type ────────────────────────────────────────────────────────
    print("  BREAKDOWN BY TYPE")
    print("  " + "-" * 50)
    for ctype in sorted(by_type.keys(), key=lambda x: x.value):
        items = by_type[ctype]
        unresolved_count = sum(1 for c in items if c.resolution == ResolutionStatus.UNRESOLVED)
        print(f"    {ctype.value:<20} {len(items):>3} total, {unresolved_count} unresolved")

    # ── Unresolved detail ──────────────────────────────────────────────
    if unresolved:
        print(f"\n  UNRESOLVED CONFLICTS")
        print("  " + "-" * 50)
        for cf in sorted(unresolved, key=lambda x: x.detected_at):
            print(f"    [{cf.conflict_id}] {cf.description}")
            print(f"      Claims: {', '.join(cf.claim_ids)}")
            print(f"      Type:   {cf.conflict_type.value}")
            print(f"      Since:  {cf.detected_at}")
            print()

    print("=" * 78)


if __name__ == "__main__":
    main()
