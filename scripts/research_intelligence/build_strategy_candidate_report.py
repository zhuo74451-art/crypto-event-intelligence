#!/usr/bin/env python3
"""Print the strategy candidate report.

Usage:
    python scripts/research_intelligence/build_strategy_candidate_report.py
"""

import sys
from pathlib import Path

# ── Add project root to sys.path ──────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research.intelligence.contracts.strategy_candidate import StrategyCandidate
from research.intelligence.contracts.strategy_seed import StrategySeed
from research.intelligence.contracts.common import (
    RuntimeContractStatus,
    StrategyCandidateValidationStatus,
    StrategySeedStatus,
)
from research.intelligence.compiler.strategy_seed_compiler import StrategySeedCompiler
from research.intelligence.compiler.strategy_candidate_compiler import StrategyCandidateCompiler


def main() -> None:
    seed_compiler = StrategySeedCompiler()
    candidate_compiler = StrategyCandidateCompiler()

    print("=" * 78)
    print("  STRATEGY CANDIDATE REPORT")
    print("=" * 78)

    # ── Phase 1: Check seeds ───────────────────────────────────────────
    print("\n  PHASE 1 - Available Strategy Seeds")
    print("  " + "-" * 50)
    print("  (No seeds registered. To generate a report with real data,")
    print("   load seeds into a StrategySeedRegistry before running this script.)")
    print()

    # Demonstrate with an example seed
    print("  Example compilation from scratch:\n")

    seed = StrategySeed(
        title="Momentum-Breakout Strategy",
        description="Captures breakouts after consolidation",
        source_ids=["SR-001"],
        claim_ids=["CL-001"],
    )
    seed.status = StrategySeedStatus.VALIDATED

    compiled_seed, seed_report = seed_compiler.compile(seed)
    print(f"  Seed:      {seed.title}")
    print(f"  Compilation: {'[SUCCESS]' if seed_report.success else '[FAILED]'}")
    if seed_report.errors:
        for e in seed_report.errors:
            print(f"    Error: {e}")
    if seed_report.enriched_fields:
        print(f"  Enriched:  {', '.join(seed_report.enriched_fields)}")
    print(f"  Status:    {compiled_seed.status.value}")

    # Compile candidate from seed
    candidate, cand_report = candidate_compiler.compile(compiled_seed)
    print(f"\n  Candidate: {candidate.name}")
    print(f"  Compilation: {'[SUCCESS]' if cand_report.success else '[FAILED]'}")
    if cand_report.errors:
        for e in cand_report.errors:
            print(f"    Error: {e}")
    if cand_report.success:
        print(f"  ID:        {candidate.candidate_id}")
        print(f"  Model:     {candidate.specification.model_type}")
        print(f"  Validation: {candidate.validation_status.value}")
        print(f"  Runtime:   {candidate.runtime_status.value}")
        print(f"  Claims:    {len(candidate.claim_ids)}")
        print(f"  Datasets:  {len(candidate.specification.datasets)}")

    # ── Summary ────────────────────────────────────────────────────────
    print("\n" + "=" * 78)
    print("  CANDIDATE SUMMARY")
    if cand_report.success:
        print(f"  Strategy candidate '{candidate.name}' compiled successfully.")
        print(f"  Status: validation={candidate.validation_status.value}, "
              f"runtime={candidate.runtime_status.value}")
        print(f"  Production ready: {candidate.runtime_status == RuntimeContractStatus.ACTIVE}")
    else:
        print("  No candidates ready.")
    print("=" * 78)


if __name__ == "__main__":
    main()
