# Market Radar v1.12-Q — Multi-Asset Market Sync Noise-Aware One-Shot Plan

**Generated**: 2026-06-05 04:13:17 UTC+8
**Status**: passed
**Dry Run Only**: Yes

---

## 1. Why v112Q Selected multi_asset_market_sync

The v112P Live Source Readiness Audit scored `multi_asset_market_sync` at **18/18**, the highest readiness score among all 5 card types. Key strengths:

- **Zero credentials required**: All data sources (CoinGecko, CoinCap, Exchange REST) are free public APIs with no API key needed.
- **No daemon or WebSocket required**: Fully compatible with one-shot manual execution.
- **3 preview cards already exist** in v112O, providing a rich local artifact base for validation.
- **All required fields are simple**: price, volume, OI changes — no complex NLP or entity extraction needed.
- **Fallback strategy is robust**: CoinCap can substitute CoinGecko; exchange public endpoints provide redundancy.

## 2. Why NOT news_event_market_impact

The v112P audit scored `news_event_market_impact` at only **10/18** (medium readiness). Critical blockers:

- **Credentials required**: CryptoPanic and Twitter/X APIs both need free-tier API keys — adds setup friction and key-rotation burden.
- **Paid API likely required**: Twitter/X free tier is severely rate-limited; practical use needs paid access.
- **Complex data fields**: Sentiment scoring, social volume, priced-in determination — all require NLP/AI pipelines that are not locally available.
- **6 failure modes** vs 4 for multi_asset_market_sync — more points of failure in a one-shot experiment.
- **Multi-source dependency**: RSS feeds + NLP + social volume + price impact — more integration surface = more debugging.

**Conclusion**: `news_event_market_impact` is a valid future candidate but its implementation complexity and credential dependency make it unsuitable as the FIRST one-shot experiment. It is recommended as a **third or fourth candidate**, after `multi_asset_market_sync` and `whale_position_alert`.

## 3. v112P Readiness Score Gap: Missing Signal Quality / False Positive Risk

The v112P scoring breakdown for `multi_asset_market_sync` awarded perfect scores in all 9 dimensions. However, the scoring framework had a critical blind spot:

| v112P Dimension | Score | Gap Identified by v112Q |
|-----------------|-------|--------------------------|
| local_artifact_complete | 2/2 | — |
| has_preview_cards | 2/2 | — |
| live_source_likely_free | 2/2 | — |
| no_credential_required | 2/2 | — |
| no_daemon_required | 2/2 | — |
| one_shot_possible | 2/2 | — |
| data_fields_simple | 2/2 | — |
| easy_fallback | 2/2 | — |
| no_production_write_risk | 2/2 | — |
| **signal_quality / false_positive_risk** | **NOT SCORED** | **v112Q adds this dimension** |

The original v112G valid/blocked logic uses a direction agreement threshold of 0.66 and allows OR-combined price/volume/OI checks. This is permissive enough to let through several classes of false-positive signals that a human reviewer would flag. v112Q addresses this gap by adding 6 noise-injection test categories.

## 4. Six Noise Risk Categories

### 4.1 Direction Conflict (two_of_three_direction_should_block)
Three assets: 2 bullish, 1 bearish. Old 0.66 threshold would allow (2/3 ≈ 0.67). New small-basket rule requires 1.0 agreement for baskets of ≤3 assets. **Risk**: false sync signal when one asset moves counter to the other two.

### 4.2 Single-Asset Volume Distortion (single_asset_volume_spike_should_block)
One asset has an 800% volume spike (e.g., wash trading on a single exchange). The old logic averages volumes, letting the outlier drag the mean above the 80% threshold. **Risk**: volume confirmation is fake — only one asset drives the signal.

### 4.3 Timestamp Skew (timestamp_skew_should_block)
Asset prices observed at times differing by >60 seconds. In fast markets, this means the "sync" may not have happened simultaneously. **Risk**: stale price data creates phantom correlation.

### 4.4 Leader-Driven Pseudo-Sync (leader_driven_move_should_downgrade_or_block)
BTC surges +8%, but ETH (+1.2%) and SOL (+0.8%) barely move. This is not multi-asset sync — it's a single-asset event with noise-level followers. **Risk**: misclassifying a BTC-specific event as market-wide resonance.

### 4.5 Sector Dispersion (mixed_sector_should_flag_low_confidence)
Five assets from four distinct sectors (L1, L2, meme, stablecoin). Even if prices move in the same direction, the lack of sector concentration weakens the narrative. **Risk**: random correlation across unrelated assets looks like sync.

### 4.6 Clean Sync Verification (clean_sync_should_pass)
Baseline positive case: 3 L1 assets, all bullish, sufficient price moves, timestamps aligned. Ensures stricter thresholds don't block genuine signals.

## 5. Stricter Threshold Plan

| Rule | v112G (Old) | v112Q (New) | Rationale |
|------|-------------|-------------|-----------|
| Direction agreement (small basket) | 0.66 | 1.0 | ≤3 assets must all agree |
| Direction agreement (large basket) | 0.66 | 0.8 | >3 assets need 80%+ agreement |
| Per-asset price floor | Not checked | ≥2.0% absolute | Each asset must individually move meaningfully |
| Min assets meeting price floor | Not checked | ≥80% of basket | Prevents 1 asset dragging others |
| Secondary metric requirement | OR logic | AND logic (price + volume|OI) | Two-factor confirmation |
| Timestamp skew | Not checked | ≤60 seconds | Ensures observations are simultaneous |
| Leader-driven detection | Not checked | Follower/leader ratio <0.25 → downgrade | Prevents BTC-only events from looking like sync |
| Volume outlier detection | Not checked | Z-score >3.0 → block | Prevents single-exchange volume distortion |
| Sector concentration | Not checked | ≥50% in dominant sector → low confidence | Prevents random cross-sector correlation |

## 6. Local Noise Case Results

| # | Case ID | Expected | Actual | Passed | Direction Agreement | Timestamp Skew | Leader Driven | Confidence | Noise Vectors |
|---|---------|----------|--------|--------|--------------------|---------------|---------------|------------|---------------|
| 1 | clean_sync_should_pass | passed | passed | ✅ | 1.000 | 30.0s | No | high | — |
| 2 | two_of_three_direction_should_block | blocked | blocked | ✅ | 0.667 | 20.0s | No | medium | direction_conflict |
| 3 | single_asset_volume_spike_should_block | blocked | blocked | ✅ | 1.000 | 15.0s | No | low | single_asset_volume_distortion |
| 4 | timestamp_skew_should_block | degraded | degraded | ✅ | 0.000 | 90.0s | No | low | timestamp_skew |
| 5 | leader_driven_move_should_downgrade_or_block | downgraded | downgraded | ✅ | 1.000 | 20.0s | Yes | low | leader_driven_pseudo_sync |
| 6 | mixed_sector_should_flag_low_confidence | low_confidence | low_confidence | ✅ | 1.000 | 25.0s | No | low | sector_dispersion |

**Summary**: 6/6 cases passed.

## 7. One-Shot Live-Like Plan Boundaries

This v112Q plan defines the boundaries for a future one-shot live-like experiment:

**In scope for v112Q (this run)**:
- ✅ Local noise-injection mock validation
- ✅ Stricter threshold definition and testing
- ✅ Fixture-based case verification (no live data)
- ✅ False-positive risk identification

**Out of scope (NOT attempted in this run)**:
- ❌ Real CoinGecko / CoinCap / Exchange API calls
- ❌ Telegram message sending (even to test channel)
- ❌ Production state file writes
- ❌ Daemon / cron / background process startup
- ❌ External AI/LLM API calls
- ❌ Real-time WebSocket streaming
- ❌ Historical baseline computation (requires live data pull)

## 8. Why Real Send Is Still NOT Ready

Despite the noise-aware plan being complete, the following blockers remain before real TG send:

1. **Historical baseline required**: The config mandates `historical_baseline_required_before_real_send: true`. A one-shot live API pull is needed to establish a baseline for comparing sync signals against historical frequency.
2. **No live data validation**: All testing used mock fixtures. Real-world data may have edge cases (missing fields, API timeouts, rate limits) not covered by fixtures.
3. **Envelope compatibility**: v112Q rules must be integrated into the v112H envelope pipeline before candidate signals can reach the send gate.
4. **Manual review gate**: Per v112P, `manual_review_required_before_send` remains true for all card types.
5. **Test channel rehearsal**: Lane 1 policy allows test-group TG delivery, but a rehearsal dry-run with the actual sender pipeline (v112R) should precede any real send.

## 9. Next Steps

### v112R (Recommended): Mock Adapter → Envelope Compatibility
- Build a mock adapter that bridges v112Q threshold rules into the v112H envelope format
- Test that stricter-filtered candidates pass through the existing dedupe/cooldown gate (v112I)
- Verify that noise-blocked signals are correctly excluded from eligible packs (v112J)

### v112S: One-Shot Live Pull + Baseline
- Execute a single one-shot pull from CoinGecko free API (no credentials needed)
- Establish historical sync frequency baseline
- Feed live data through v112Q stricter thresholds
- Compare live results against fixture-based expectations

### Second Candidate: whale_position_alert
- Scored 16/18 in v112P audit
- 2 preview cards already exist
- No credentials required, one-shot feasible
- Should undergo the same noise-aware threshold review before first live pull

---

## Safety Declaration

| Constraint | Status |
|------------|--------|
| Live API called | ❌ No |
| TG message sent | ❌ No |
| Production state written | ❌ No |
| Daemon started | ❌ No |
| External AI called | ❌ No |
| Files deleted | ❌ No |
| Secrets leaked | ❌ No (0 terms) |
| Debug terms leaked | ❌ No (0 terms) |
| Dry run only | ✅ Yes |

*Report generated by v112Q runner on 2026-06-05 04:13:17 UTC+8*