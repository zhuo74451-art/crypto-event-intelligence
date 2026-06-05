# Market Radar v1.16-H — Next Real E2E Candidate Decision (post v116G)

**Generated**: 2026-06-05 12:50:54 UTC+8
**Version**: v1.16-H

---

## Context

After v116E (multi_asset_market_sync) and v116G (price_oi_volume_anomaly) both successfully demonstrated real free Binance API + TG test group one-shot sends, 2/5 card families are now at `real_free_api_tg_test_sent`. The next step is to select the best candidate from the remaining families for the next real E2E integration.

**Already complete**:

1. ✅ `multi_asset_market_sync` — v116E real free API + TG test sent
2. ✅ `price_oi_volume_anomaly` — v116G real free API + TG test sent (ETH, SOL)

**Remaining candidates**:

1. ⏳ `liquidation_pressure` — fixture E2E passed, real not started
2. ⏳ `news_event_market_impact` — fixture E2E passed, real not started
3. ⛔ `whale_position_alert` — blocked by manual evidence requirement

**Evaluation criteria**:

1. Free public API availability (no paid API keys required)
2. No manual/human evidence required (fully automated)
3. Existing fixture E2E foundation (quality gate baseline)
4. TG test group one-shot suitability
5. Data quality risk (inverse: higher score = lower risk)
6. Implementation complexity (inverse: higher score = simpler)

## Candidate Scoring Matrix

| Rank | Card Family | Free API | No Manual | Fixture E2E | TG Suitability | Data Quality | Complexity | **Weighted Total** |
|------|-------------|----------|-----------|-------------|---------------|--------------|------------|-------------------|
| 1 | **Liquidation Pressure** | 8 | 9 | 8 | 9 | 6 | 7 | **8.0** |
| 2 | **News Event Market Impact** | 6 | 7 | 9 | 7 | 5 | 4 | **6.4** |

**Weights**: Free API 25% | No Manual 20% | Fixture E2E 15% | TG Suitability 15% | Data Quality 10% | Complexity 15%

## Recommendation

### 🥇 **Recommended: Liquidation Pressure** (`liquidation_pressure`)

**Weighted score**: 8.0/10

**Rationale**:

- **Free Api** (score=8): Binance liquidation streams + Hyperliquid API (free tier exists). Binance REST does not directly provide liquidation pressure data; may need WebSocket or public endpoints (futures ticker, OI, funding, long/short ratio) as weak proxies.
- **No Manual** (score=9): Fully automated — liquidation data from exchange APIs.
- **Fixture E2E** (score=8): v116C: fixture_e2e_passed, QG=3/5 (moderate baseline — better than POVA's 1/7)
- **Tg One Shot** (score=9): Well-suited: single card per liquidation cluster, easy to validate.
- **Data Quality** (score=6): MODERATE RISK: Binance REST does not directly provide full liquidation pressure data. May need to use public futures ticker, OI, funding rate, long/short ratio, or available WebSocket/public endpoints as weak proxies. If insufficient real data, MUST NOT force-generate liquidation cards. 3/5 QG passed on fixtures shows moderate baseline.
- **Complexity** (score=7): Medium-low: needs liquidation-specific endpoints but similar REST pattern to v116E/v116G. Risk: data proxy quality uncertain.

### ⚠ Risk Analysis for Recommended Candidate

**Primary risk**: Binance REST API does **not** directly provide complete liquidation pressure data. The free API endpoints (futures ticker, openInterest, funding rate, long/short ratio) are **weak proxies** for actual liquidation pressure. Without sufficient real data, generating meaningful liquidation cards may not be possible.

**Specific risks**:

1. **Data availability**: Binance liquidation order data is primarily available via WebSocket streams, not REST. Public REST endpoints provide derivative metrics (OI changes, funding, L/S ratio) that only partially correlate with liquidation pressure.
2. **Proxy quality**: Using OI delta + funding rate + L/S ratio as a composite liquidation pressure score may produce false signals during normal market volatility.
3. **Sparse events**: Liquidation cascades are event-driven and infrequent. During calm market periods, the pipeline may produce empty or low-confidence cards.
4. **Hyperliquid API**: Provides additional data but covers a different exchange ecosystem — cross-exchange arbitrage differences may confuse the signal.

**Mitigation strategy**:

1. Start with composite proxy: OI delta (%) + funding rate extreme + long/short ratio shift, with configurable thresholds.
2. Use Binance futures ticker/24hr (free REST) for price and volume context.
3. If WebSocket access is feasible without paid keys, add liquidation order stream.
4. Set strict quality gate thresholds — if proxy data is insufficient, do NOT force-generate cards.
5. Accept that first-pass QG pass rate may be low (similar to POVA's initial 1/7 on fixtures).

### 🥈 Runner-up: News Event Market Impact (`news_event_market_impact`)

**Weighted score**: 6.4/10

**Why not first**:

- **Free Api**: 6 vs 8 for Liquidation Pressure
- **No Manual**: 7 vs 9 for Liquidation Pressure
- **Tg One Shot**: 7 vs 9 for Liquidation Pressure
- **Data Quality**: 5 vs 6 for Liquidation Pressure
- **Complexity**: 4 vs 7 for Liquidation Pressure

**Assessment**: News Event Market Impact is a strong candidate with the best fixture QG baseline (5/7). However, it requires NLP/sentiment processing which adds implementation complexity. Recommended as the **next candidate after** liquidation_pressure.

### ⛔ whale_position_alert — NOT Recommended for Next Real E2E

`whale_position_alert` remains **excluded** from the candidate pool because:

1. Requires **real human operator** to complete address verification workbook (v115F)
2. Cannot be automated with free APIs alone — needs on-chain attribution data
3. All 4 addresses have empty fields in the real operator workbook
4. Blocked by v115R submission validator
5. This status has not changed since v116A — no progress on the manual evidence front

## Recommended Implementation Sequence

| # | Card Family | Status | Rationale | Est. Complexity |
|---|-------------|--------|-----------|-----------------|
| - | `multi_asset_market_sync` | ✅ Done | v116E: real API + TG sent | — |
| - | `price_oi_volume_anomaly` | ✅ Done | v116G: real API + TG sent (ETH/SOL) | — |
| 1 | `liquidation_pressure` | ⏳ Pending | Top candidate by score | Low |
| 2 | `news_event_market_impact` | ⏳ Pending | Top candidate by score | Medium |
| - | `whale_position_alert` | ⛔ Blocked | Requires human operator — deferred indefinitely | Highest |

## Decision Summary

**Selected next real E2E candidate**: `liquidation_pressure`
**Recommended version tag**: `v116I`
**Recommended task**: Build real free API data adapter for `liquidation_pressure`, using Binance free REST endpoints (futures ticker, OI, funding rate, long/short ratio) as composite proxy. Integrate with existing quality gate. Send one-shot TG test to test group only if quality gate passes and real data is sufficient.

**Key constraint**: If real data is insufficient to generate meaningful liquidation pressure signals, do NOT force card generation. Record the limitation and consider news_event_market_impact as fallback candidate.
