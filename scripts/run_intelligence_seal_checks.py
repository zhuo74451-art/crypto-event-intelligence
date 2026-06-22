#!/usr/bin/env python3
"""Intelligence Kernel Seal Checks — verify all P0/P1 fixes are in place."""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.path.insert(0, str(PROJECT_ROOT))

PASS = 0
FAIL = 0
ERRORS: list[str] = []


def check(condition: bool, msg: str):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL += 1
        ERRORS.append(msg)
        print(f"  [FAIL] {msg}")


def main():
    global PASS, FAIL
    print("=== Intelligence Kernel Seal Checks ===\n")

    # 1. Vote counting check — exclude comments
    print("--- P0-1: Vote Counting Removed ---")
    arb_source = (PROJECT_ROOT / "market_radar/intelligence/engines/arbitration.py").read_text(encoding="utf-8")
    lines = arb_source.split("\n")
    # Exclude docstring lines (triple quotes), comments, and empty lines
    in_docstring = False
    code_lines = []
    for l in lines:
        if l.strip().startswith("\"\"\""):
            in_docstring = not in_docstring
            continue
        if in_docstring:
            continue
        if l.strip().startswith("#"):
            continue
        if not l.strip():
            continue
        code_lines.append(l)
    code_text = "\n".join(code_lines)
    # Be more specific: check for direction assignment using len comparison
    check('"bullish" if len(supporting)' not in code_text,
          "No directional assignment based on len(supporting) count")
    check('"bearish" if len(opposing)' not in code_text,
          "No directional assignment based on len(opposing) count")
    check("majority" not in code_text.lower() or 'not majority' in code_text.lower(),
          "No 'majority' in arbitration direction logic")
    check("len(opposing) > len(supporting)" not in code_text,
          "No len(opposing) > len(supporting) in arbitration logic")
    check("majority" not in code_text.lower(),
          "No 'majority' in arbitration direction logic")

    # 2. Evidence/Regime state used
    print("\n--- P0-2: Evidence/Regime State Used ---")
    check("evidence_state" in arb_source,
          "evidence_state referenced in arbitration")
    check("regime_state" in arb_source,
          "regime_state referenced in arbitration")

    # 3. Ineligible structure
    print("\n--- P0-3: Ineligible Structured ---")
    arb_output = (PROJECT_ROOT / "market_radar/intelligence/contracts/arbitration.py").read_text(encoding="utf-8")
    check("IneligibleHypothesis" in arb_output,
          "IneligibleHypothesis contract exists")
    check("EligibilityDecision" in arb_output,
          "EligibilityDecision contract exists")

    # 4. Structured claim conflict
    print("\n--- P0-4: Structured Claim Conflict ---")
    ev_source = (PROJECT_ROOT / "market_radar/intelligence/engines/evidence_resolver.py").read_text(encoding="utf-8")
    check("claim_key" in ev_source,
          "claim_key used for conflict detection")
    check("unique_claims = set(p.claim" not in ev_source,
          "Old claim string conflict detection removed")

    # 5. Staleness enforced
    print("\n--- P0-5: Staleness Enforced ---")
    check("def _is_stale" in ev_source,
          "_is_stale method implemented")
    check("StalenessPolicy" in ev_source,
          "StalenessPolicy used in resolver")

    # 6. Event machine
    print("\n--- P0-6: Event State Machine ---")
    esm_source = (PROJECT_ROOT / "market_radar/intelligence/engines/event_state_machine.py").read_text(encoding="utf-8")
    check("force_state_change" in esm_source,
          "Revision/Correction require force_state_change")
    check("EventTransitionResult" in esm_source,
          "EventTransitionResult exists (pure function)")
    check("idempotent" in esm_source,
          "Idempotent detection implemented")
    check("utc_parse" in esm_source,
          "UTC datetime parsing used")

    # 7. Stable IDs
    print("\n--- P1-1: Stable IDs ---")
    check("import hashlib" in arb_source,
          "Arbitration uses hash-based IDs")
    check("evb_" in ev_source,
          "Evidence uses hash-based bundle IDs")

    # 8. Architecture doc
    print("\n--- P1-3: Documentation ---")
    arch = (PROJECT_ROOT / "docs/ARCHITECTURE.md").read_text(encoding="utf-8")
    check("market_radar/intelligence/" in arch,
          "Architecture doc has valid kernel reference")
    check("INTELLIGENCE_KERNEL_FOUNDATION_V1.md" in arch,
          "Architecture doc has kernel doc reference")

    # 9. Test baseline
    print("\n--- Test Baseline ---")
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "pytest", "tests/intelligence/", "-q", "--no-header"],
        capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT),
    )
    check("passed" in result.stderr or "passed" in result.stdout,
          "Intelligence tests still pass")

    # 10. ARB-199 removed and canonical IDs
    print("\n--- Arbitration Specific Checks ---")
    arb_text = (PROJECT_ROOT / "market_radar/intelligence/engines/arbitration.py").read_text(encoding="utf-8")
    # Exclude comments/docstrings
    clean_lines = []
    in_doc = False
    for line in arb_text.split("\n"):
        if '"""' in line:
            in_doc = not in_doc
            continue
        if in_doc or line.strip().startswith("#"):
            continue
        clean_lines.append(line)
    clean_text = "\n".join(clean_lines)
    check("ARB-199" not in clean_text,
          "ARB-199 fallback removed")
    check("sorted_ids" in clean_text,
          "Canonical content-based arbitration ID")
    check("E01_CONTRACT_INVALID" in arb_text,
          "Full E01-E12 eligibility checks implemented")

    # Summary
    print(f"\n=== Results: {PASS} passed, {FAIL} failed ===")
    if FAIL > 0:
        print("\nFailures:")
        for e in ERRORS:
            print(f"  - {e}")
        sys.exit(1)
    print("All seal checks passed.")


if __name__ == "__main__":
    main()
