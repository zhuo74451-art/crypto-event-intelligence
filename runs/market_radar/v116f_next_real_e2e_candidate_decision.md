# Market Radar v1.16-F — Next Real E2E Candidate Decision

**Generated**: 2026-06-05 12:22:33 UTC+8
**Version**: v1.16-F

---

## Context

After v116E successfully demonstrated real free Binance API + TG test group one-shot send for `multi_asset_market_sync`, the next step is to select the best candidate card family for the next real E2E integration.

The 4 remaining card families are evaluated against these criteria:

1. Free public API availability (no paid API keys required)
2. No manual/human evidence required (fully automated)
3. Existing fixture E2E foundation (quality gate baseline)
4. TG test group one-shot suitability
5. Data quality risk (inverse: higher score = lower risk)
6. Implementation complexity (inverse: higher score = simpler)

## Candidate Scoring Matrix

| Rank | Card Family | Free API | No Manual | Fixture E2E | TG Suitability | Data Quality | Complexity | **Weighted Total** |
|------|-------------|----------|-----------|-------------|---------------|--------------|------------|-------------------|
| 1 | **Price/OI/Volume Anomaly** | 9 | 10 | 7 | 9 | 4 | 8 | **8.2** |
| 2 | **Liquidation Pressure** | 8 | 9 | 8 | 9 | 6 | 7 | **8.0** |
| 3 | **News Event Market Impact** | 6 | 7 | 9 | 7 | 5 | 4 | **6.4** |

**Weights**: Free API 25% | No Manual 20% | Fixture E2E 15% | TG Suitability 15% | Data Quality 10% | Complexity 15%

## Recommendation

### 🥇 **Recommended: Price/OI/Volume Anomaly** (`price_oi_volume_anomaly`)

**Weighted score**: 8.2/10

**Rationale**:

- **Free Api** (score=9): Binance ticker/24hr + openInterest (free, no key)
- **No Manual** (score=10): Fully automated — price/OI data from exchange
- **Fixture E2E** (score=7): v116C: fixture_e2e_passed, but QG=1/7 (weak baseline)
- **Tg One Shot** (score=9): Well-suited: single card per anomaly event, easy to validate
- **Data Quality** (score=4): HIGH RISK: v116C only 1/7 passed QG. Fixtures from derivative analysis, not raw market data. Real data QG pass rate may be worse.
- **Complexity** (score=8): Low: pattern follows multi_asset_market_sync v116E. Same Binance API, different metric computation.

### ⚠ Risk Analysis for Recommended Candidate

**Primary risk**: v116C fixture E2E showed only **1/7 records passed QG**. The fixtures were constructed from derivative analysis, not raw market data. When real API data is used, the QG pass rate could be:

1. **Worse than fixture**: if raw market data has more noise/edge cases
2. **Better than fixture**: if real data is cleaner than synthetic derivatives
3. **About the same**: if the QG rules are well-calibrated

**Mitigation**: Start with a single asset pair (e.g., BTCUSDT) using the same Binance free API pattern proven in v116E. Validate QG pass rate before scaling to multi-asset.

---

### 🥈 Runner-up: Liquidation Pressure (`liquidation_pressure`)

**Weighted score**: 8.0/10

**Why not first**:

- **Free Api**: 8 vs 9 for #Price/OI/Volume Anomaly
- **No Manual**: 9 vs 10 for #Price/OI/Volume Anomaly
- **Complexity**: 7 vs 8 for #Price/OI/Volume Anomaly

### ⛔ whale_position_alert — NOT Recommended for Next Real E2E

`whale_position_alert` is **excluded** from the candidate pool because:

1. Requires **real human operator** to complete address verification workbook (v115F)
2. Cannot be automated with free APIs alone — needs on-chain attribution data
3. All 4 addresses have empty fields in the real operator workbook
4. Blocked by v115R submission validator

This card family should be advanced **only after** the operator completes the workbook, and ideally after the automated card families are proven.

## Recommended Implementation Sequence

| # | Card Family | Rationale | Est. Complexity |
|---|-------------|-----------|-----------------|
| 1 | `price_oi_volume_anomaly` | Top candidate by weighted score | Low |
| 2 | `liquidation_pressure` | Top candidate by weighted score | Low |
| 3 | `news_event_market_impact` | Top candidate by weighted score | Medium |
| - | `whale_position_alert` | Requires human operator — deferred | Highest |

## Decision Summary

**Selected next real E2E candidate**: `price_oi_volume_anomaly`
**Recommended version tag**: `v116G`
**Recommended task**: Build real free API data adapter for `price_oi_volume_anomaly`, integrate with existing quality gate, and send one-shot TG test to test group if QG passes.
