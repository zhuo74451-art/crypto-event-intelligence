# Market Radar False Negative Scan v1

## 1. Sample Scope

- assets scanned: ['HYPE']
- time_range: 2026-05-19 00:53:58 ~ 2026-05-19 02:45:00
- major_move_count: **2** (strict=0, adjusted=2)
- thresholds: strict(4h>=8%, 24h>=12%), adjusted(4h>=4%, 24h>=6%)
- data_sources: v043_price_backfill + v1.4b_price_backfill + market_radar_historical_backtest
- **Note: HYPE/SOL price data present but below strict thresholds. BTC/ETH added as supplementary assets.**

## 2. False Negative Overview

| label | count | rate |
|---|---:|
| covered (signal within 4h) | 2 | 100.0% |
| weakly_covered (signal within 24h) | 0 | 0.0% |
| missed (no signal within 24h) | 0 | 0.0% |
- false_negative_rate: **0.0%**

## 3. Top Major Moves

- [COVERED] [adjusted] 2026-05-19 00:53 HYPE 24h ret=6.8%
  nearest_signal: 2026-05-19 00:53 institutional_flow

- [COVERED] [adjusted] 2026-05-19 02:45 HYPE 4h ret=4.3%
  nearest_signal: 2026-05-19 02:45 institutional_flow

## 4. Potential Blind Spots

- 0 major moves had no signal within 24h prior
- Data limited to single-day backfill window (2026-05-19)
- HYPE highest 24h move: 6.9% (below strict 12% threshold, meets adjusted 6%)
- SOL highest 24h move: 0.3% (no major moves detected)

## 5. Conclusions

**Sample insufficient (n=2<10). Pipeline validated, not a coverage assessment.**

- fn_rate=0.0% — directional only from single-day sample
- Current backfill data too narrow for reliable FN scan
- SOL has near-zero volatility in this sample — not useful for FN detection
- Need multi-day HYPE/BTC/ETH price data to meaningfully assess coverage

> For Market Radar signal quality observation only. Not trading advice.
