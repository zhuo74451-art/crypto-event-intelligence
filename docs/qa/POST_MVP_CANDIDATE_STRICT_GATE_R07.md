# Post-MVP Candidate Strict Gate Restoration Report R07

## R06 Weakened Assertions & Restoration

| # | Issue | R06 State | R07 Fix |
|---|-------|-----------|---------|
| 1 | XSS threshold | Lowered to 4 | Restored to ≥5, added 5th case (R081 encoded) |
| 2 | Credential scan | `os.listdir(".")` shallow | `git ls-files` based, 7 file types, 5 pattern types |
| 3 | Owned paths | `tests/`, `scripts/`, etc. broad allow | Exact W6 paths only + target freeze check |
| 4 | Artifact gate | `results/`, `runs/` broad exclude | Exact allowlist + prefix for pre-existing dirs |
| 5 | Whale JSON | `pass  # filtered` | Real fail on non-allowed paths |

## W6 QA Result

169 passed, 0 failed, 0 skipped.

## Mutation/Sentinel Tests

14 tests added proving the gate catches:
- Fake API key in subdirectory
- Private key in tracked file
- Candidate HEAD change
- Main HEAD change
- W6 modifying candidate file
- `results/run_live.json` as runtime artifact
- `runs/feed_cursor.json` as runtime artifact
- `results/state.db` as runtime artifact
- XSS corpus < 5
- Shallow credential scan
- Evidence self-pointing
- Non-strict owned paths

## Candidate Status

- HEAD: `9637a472` (unchanged)
- Tested: `805188a6` (unchanged)
- Main: `a8fd827e` (unchanged)

## Final Decision

POST_MVP_CANDIDATE_ACCEPTED_FOR_MAIN_REVIEW
