# Implementation-Side Release Evidence Report

> **This is an implementation-side release evidence report, not an independent third-party audit.**
>
> The evidence below is collected by the project implementation team.
> Independent verification is recommended before production use.

## Audit Scope

- Git history integrity
- File existence and structure
- Data consistency (Manifest vs Price vs Dataset)
- Manifest fact preservation (raw_summaries, tags, IDs unchanged)
- Price provenance (snapshot metadata preserved)
- Shared observation integrity (w1_003 / w1_004)
- Validator output (manifest, price, dataset)
- Test suite pass/fail
- Security boundary enforcement
- Build determinism
- Network isolation during build

## Evidence Matrix

| # | Requirement | Evidence File | Evidence Command | Result | Remaining Risk |
|---|-------------|---------------|------------------|--------|----------------|
| 1 | Git history clean | `git status --short` | Empty output | ✅ | Low |
| 2 | 5 manifest samples exist | `research/week1_samples_v1.json` | `jq '.samples \| length'` | ✅: 5 | Low |
| 3 | 5 unique price observations | `research/week1_price_backfill_raw_v1.json` | `jq '.unique_price_observations'` | ✅: 5 | Low |
| 4 | 6 sample links | `research/week1_raw_research_dataset_v1.json` | `jq '.sample_links_count'` | ✅: 6 | Low |
| 5 | w1_003/004 share observation | `research/week1_raw_research_dataset_v1.json` | Check same price_observation_key | ✅: shared | Low |
| 6 | w1_004 observation_reused=true | Same file | `jq '.sample_price_links[] \| select(.sample_id=="w1_004").observation_reused'` | ✅: true | Low |
| 7 | w1_005 has BTC+ETH links | Same file | Check observed_assets | ✅: both | Low |
| 8 | HYPE signed_lag=-120 | Price JSON | `jq '.results[] \| select(.sample_id=="w1_001").signed_lag_seconds'` | ✅: -120 | Low |
| 9 | Binance signed_lag=0 | Price JSON | `jq '.results[] \| select(.sample_id=="w1_002").signed_lag_seconds'` | ✅: 0 | Low |
| 10 | No fixture in network output | Price JSON | `grep -c fixture` | ✅: 0 | Low |
| 11 | No attribution fields | Dataset JSON | Search for attribution_confidence etc. | ✅: absent | Low |
| 12 | No trading advice | All output files | Search for buy/sell/long/short | ✅: absent | Low |
| 13 | Build deterministic | Compare SHA256 | `sha256sum` after 2 builds | ✅: identical | Low |
| 14 | Build uses 0 network calls | `strace` / audit | No HTTP calls during build | ✅: 0 | Low |
| 15 | 233 tests pass | `pytest -q` | `233 passed` | ✅: 233 | Low |
| 16 | Manifest validator passes | `validate_manifest.py` | ALL CHECKS PASSED | ✅ | Low |
| 17 | Price validator passes | `validate_week1_price_dataset.py` | PASS | ✅ | Low |
| 18 | Dataset validator passes | `validate_week1_raw_research_dataset_v1.py` | PASS | ✅ | Low |
| 19 | calculation_code_commit correct | Dataset JSON | `d7b908d...` | ✅ | Low |
| 20 | price_data_commit correct | Dataset JSON | `7188a52...` | ✅ | Low |

## Confirmed Facts

- 5 manifest samples: w1_001 through w1_005
- 6 sample links: 4 direct + 2 WTI (BTC + ETH)
- 5 unique price observations (w1_003 and w1_004 share one)
- HYPE aligned to nearest 15m candle at -120s signed lag
- Binance snapshots at exact target time (0s lag)
- No fixture data mixed into network output
- No attribution, confidence, causality, or trading advice in any output
- Builder script makes zero network calls

## Incomplete Items and Risks

- **t0 is broadcast_time, not event occurrence time.** Event time may differ from broadcast. Currently null for all samples.
- **Only 5 samples.** Insufficient for statistical conclusions. Phase 2 plans 30-50.
- **Single-source event quality is limited.** Cross-source verification not yet implemented.
- **HYPE 15m vs Binance 1m precision mismatch.** Not comparable at sub-15m granularity.
- **Abnormal return is not causal attribution.** It only shows asset price vs benchmark. Multiple confounding factors always present.
- **Attribution layer not yet implemented.** No confidence score, no interference quantification.
- **No production long-term stability validation.** Tests are all short-lived.
- **No high-concurrency or long-running daemon validation.** Not tested beyond single-shot execution.
- **No Notion auto-sync.** All outputs are local JSON files.
- **Real Binance/HL API may be rate-limited or temporarily fail.** Network mode is not guaranteed to always succeed.

## Release Recommendation

**ACCEPT AS RESEARCH BASELINE**

Not:
- PRODUCTION READY
- TRADING READY
- CAUSALITY VALIDATED
