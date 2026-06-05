# v112X — HyperLiquid One-Shot Read-Only Dry-Run — Run Report

**Version:** v1.12-X  
**Run ID:** 20260605_022952  
**Task ID:** 20260605_022952.r15  
**Generated:** 2026-06-05T04:41:49+08:00  

---

## 1. Execution Summary

| Metric | Value |
|--------|-------|
| Addresses requested | 4 |
| Successful responses | 4 (100%) |
| Failed requests | 0 |
| Total positions found | 9 |
| Active positions | 9 |
| API key used | **false** |
| Authorization header used | **false** |
| Retry count | **0** |
| TG sent | **false** |
| Prod state write | **false** |
| Daemon / watcher started | **false** |
| eligible_for_real_send | **false** |
| Stop decision | **DEGRADE_TO_MOCK** |

---

## 2. Addresses Requested (脱敏展示)

| # | Address (short) | Label | Entity Type | Confidence | Positions | HTTP |
|---|-----------------|-------|-------------|------------|-----------|------|
| 1 | 0x6c85...d84f6 | Matrixport Related | fund_wallet | medium | 1 (ETH long, $70.9M, 20x) | 200 |
| 2 | 0x8def...92dae | loraclexyz | high_leverage_trader | medium | 7 (WLD, TON, NEAR, HYPE, ASTER, ZEC, XMR) | 200 |
| 3 | 0x082e...dca88 | Unknown HYPE Whale | unknown_whale | low | 1 (HYPE short, $1.4M, 3x) | 200 |
| 4 | 0x50b3...c9f20 | Unknown Hyperliquid Whale | unknown_whale | low | 0 | 200 |

**Total positions: 9 active positions across 4 addresses.**

---

## 3. Stop Decision Analysis

### Decision: DEGRADE_TO_MOCK

### Reasons:

1. **DEGRADE_LABEL_MISSING** — 2 of 4 addresses (0x082e...dca88, 0x50b3...c9f20) have low label confidence ("Unknown * Whale" labels). These are valid HyperLiquid observer labels but unverified.

2. **DEGRADE_LIQUIDATION_PRICE_MISSING** — 7 of 9 positions (WLD, TON, NEAR, HYPE, ASTER, ZEC, XMR from loraclexyz) have `liquidationPx: null` in the HyperLiquid response. This is likely because these positions use cross margin and the exchange does not report a discrete liquidation price for them.

3. **DEGRADE_DELTA_CANNOT_COMPUTE** — No previous position history is available from this one-shot read. Position delta (change since last observation) cannot be computed.

4. **DEGRADE_TIMESTAMP_FRESHNESS** — Timestamps are locally generated (`datetime.now(CN_TZ)`). The HyperLiquid API response does not include a server timestamp for individual position queries.

5. **DEGRADE_PREVIOUS_SIZE_UNAVAILABLE** — One-shot read has no previous snapshot to compare against.

### Why NOT CONTINUE?

CONTINUE requires all quality gates to pass cleanly. The following CONTINUE conditions failed:
- **CONTINUE_LABEL_OK**: 50% of labels are low confidence
- **CONTINUE_ALL_REQUIRED_FIELDS**: 7/9 positions missing liquidation_price
- **CONTINUE_ADAPTER_CAN_PRODUCE**: Missing liquidation_price for most positions impairs v112F-compatible event generation

### Why NOT ABORT?

No ABORT conditions are triggered:
- All HTTP responses were 200 OK
- No timeouts
- Valid JSON from all responses
- No rate limiting
- No auth required
- No API key or Authorization header used
- No production state writes
- Zero of 9 positions had numeric parse failures
- All required fields present for at least one address (Matrixport Related has full ETH position data)

---

## 4. Data Quality Notes

### Strengths:
- 4/4 addresses returned valid HTTP 200 responses
- 9 real, active positions extracted from live HyperLiquid API
- All numeric fields (szi, entryPx, unrealizedPnl, positionValue, marginUsed) parsed successfully
- Position sizes are substantial ($70.9M ETH long, multiple $10K-$500K positions)
- Side determination (long/short) works correctly via szi sign
- Entry prices and mark prices are available for all positions
- All safety invariants enforced and verified

### Weaknesses:
- 7/9 positions have null liquidation_price (cross-margin positions on HyperLiquid)
- 2/4 labels are low confidence ("Unknown * Whale")
- Mark price is derived from `positionValue / abs(szi)`, not from an external price oracle
- No historical context for position delta computation
- 1 address returned 0 positions (likely closed all positions)

---

## 5. Safety Invariants — All Passed

| Invariant | Status |
|-----------|--------|
| API key never used | ✅ true |
| Authorization header never sent | ✅ true |
| No credentials, tokens, cookies read | ✅ true |
| No .env file accessed | ✅ true |
| No retries on failure | ✅ true (retry_count=0) |
| No daemon / watcher / cron / loop | ✅ true |
| No TG send | ✅ true |
| No production state write | ✅ true |
| No file deletion | ✅ true |
| eligible_for_real_send always false | ✅ true |
| dry_run_only enforcement | ✅ true |
| No misleading production claims | ✅ true |

---

## 6. Next Step Recommendation

**v112Y: whale degraded mock replay with label explanation.**

Since the stop decision is DEGRADE_TO_MOCK:
1. Build a degraded mock replay using the real live response data from this run
2. Map the live response to v112F-compatible whale_position_alert format
3. Handle null liquidation_price with explicit "清算价格不可用" notation
4. Explain label confidence levels to end users
5. Design envelope integration with degraded quality flags
6. Prep for v112Z adapter compatibility verification

The live data is real and valuable — the degradation is about data completeness, not data validity. A degraded mock replay can still produce high-quality signal cards with proper caveats.

---

## 7. Files Generated

| File | Description |
|------|-------------|
| `results/market_radar_v112x_hyperliquid_live_response.json` | Full live response with 9 positions from 4 addresses |
| `results/market_radar_v112x_hyperliquid_stop_decision.json` | Stop decision: DEGRADE_TO_MOCK with 11 reasons |
| `scripts/run_market_radar_v112x_hyperliquid_one_shot_readonly_dryrun.py` | Runner script |
| `scripts/test_market_radar_v112x_hyperliquid_one_shot_readonly_dryrun.py` | Test suite |
| `runs/market_radar/v112x_hyperliquid_one_shot_readonly_dryrun.md` | This report |
| `runs/market_radar/v112x_hyperliquid_one_shot_readonly_dryrun_handoff.md` | Handoff document |
