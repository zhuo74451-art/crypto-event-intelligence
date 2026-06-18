# Post-MVP Integration Candidate V1

**Branch**: `workbench/post-mvp-integration-candidate-v1`
**Baseline**: `8d553fa` (MVP+ Integration-v2 R10)
**Code Tree SHA**: `da8338e`

---

## Assembly

| Lane | Source Base | Tested Commit | Commits | Conflicts |
|------|------------|---------------|---------|-----------|
| W5 Operations | `5c6f33c` | `1175bb4` | 3 | 0 |
| W4 Markets | `b7672f8` | `b99c2b4` | 5 | 0 |
| W2 Whale | `6802ac8` | `3f40c1e` | 9 | 0 |
| W3 Events | `483b38f` | `b5ef848` | 3 | 0 |
| W1 Operator | `0cf9edf` | `fa3ecd5` | 5 | 0 |

Assembly order: W5 → W4 → W2 → W3 → W1. Zero conflicts across all 25 commits.

## Stage Tests

| After | Test Suite | Result |
|-------|-----------|--------|
| W5 | operations | 151 passed |
| W4 | adapters | 96 passed |
| W2 | whale_domain | 127 passed, 1 skipped |
| W3 | feeds_market_ui | 170 passed |
| W1 | operator + integration | 212 passed |

## Full Regression

- Combined pytest: **2314 passed, 3 skipped**
- Adapter unittest: **96 passed**
- **Total: 2410 passed, 0 failed**

### Known Skips

1. W2 whale: 1 skip (test_c022 — pre-existing fixture limitation)

## Live Acceptance

- **Doctor**: 8 checks PASS, 0 FAIL (offline)
- **One-shot**: `os-efa748de085d` — **completed**, 13 sources, 0 errors
- **Shadow**: **completed**, 2/2 rounds, 0 errors

## Public Contracts

- W5 Operations: schema v2, parent_run_id, run_ordinal, run_kind, link_existing
- W4 Markets: Binance/OKX/Bybit/Hyperliquid, OI/funding/basis/mark/index, venue health
- W2 Whale: Portfolio model (71 V2 corpus + 30 V1), rule_id, no trading advice
- W3 Events: FeedItem contract, Event Intelligence, 1200+ pair corpus, score breakdown
- W1 Operator: doctor/run/shadow/inspect/compare/bundle/catalog/replay-pack/readiness-score, no_send locked

## Standalone Modules

The following modules work independently without Integration wiring:
- W2 Portfolio Intelligence
- W3 Event Clustering
- W4 Market Resilience
- W5 Ops Doctor/Audit/Backup

## Security

- No credentials, API keys, secrets, seed phrases tracked
- No send/order/signing/trade capability
- No daemon/scheduler/thread
- No infinite loops
- No absolute user paths in evidence
- Git excludes: *.db, *.lock, STOP, feed_cursor.json, run_*.json, workbench_*.html

## Not Included

- W6 Independent QA (runs separately to validate this candidate)
- main merge (candidate is not a production release)
- Telegram/X/webhook send
- Production deployment
