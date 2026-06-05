# Market Radar Historical Backtest v1.4b

## 1. Sample Scope

- total_signals: **56**
- time_range: 2026-05-19 00:50:18 ~ 2026-05-19 10:23:18
- assets: 5 (BNB, BTC, ETH, HYPE, XRP)
- event_types: 6
- source: market_radar_admission_candidates_v1_4b (537 -> 56 admission -> **56 with price**)
- thresholds: useful={ab24>=1.5% or raw24>=3%}; neutral={raw24>=0.5%}; noise=else

## 2. Overall Results

| label | count | rate |
|---|---:|
| useful | 4 | 7.1% |
| neutral | 29 | 51.8% |
| noise | 23 | 41.1% |

- avg |ret_4h|: 0.57%
- avg |ret_24h|: 0.90%
- avg |ab_vs_btc_24h|: 0.58%

## 3. Reaction Labels

- vol_reaction: 3 (5.4%)
- weak_reaction: 21 (37.5%)
- no_reaction: 32 (57.1%)

## 4. Beta-Adjusted

- independent_move: 4 (7.1%)
- beta_like: 52 (92.9%)
- partial: 0 (0.0%)

## 5. By Event Type

| type | n | useful | u_rate | avg|ret_24h| |
|---|---:|---:|---:|
| institutional_flow | 9 | 2 | 22.2% | 1.92% |
| token_unlock | 5 | 2 | 40.0% | 1.28% |
| hack_security | 25 | 0 | 0.0% | 0.73% |
| network_upgrade | 7 | 0 | 0.0% | 0.30% |
| halving | 6 | 0 | 0.0% | 0.41% |
| staking_governance | 4 | 0 | 0.0% | 0.92% |

## 6. By Source

| source | n | useful | noise | u_rate |
|---|---:|---:|---:|
| news:cryptonews | 10 | 2 | 6 | 20.0% |
| webhook | 34 | 2 | 8 | 5.9% |
| news:bitcoinmagazine | 2 | 0 | 2 | 0.0% |
| news:coinpedia | 2 | 0 | 2 | 0.0% |
| news:bitcoinist | 5 | 0 | 3 | 0.0% |
| news:odaily_exchange_gap | 2 | 0 | 2 | 0.0% |
| tg:OneMillion_AI | 1 | 0 | 0 | 0.0% |

## 7. Token Unlock Observation

- sample_count: **5**
- useful: 2 (40.0%)
- neutral: 2
- noise: 1
- **Sample insufficient (n<20). Candidate signal only, not a conclusion.**

## 8. Representative Cases

- [USEFUL] 2026-05-19 00:53 HYPE institutional_flow
  |ret_4h|=0.0196 |ret_24h|=0.0681 |ab_vs_btc|=0.0622
  react=weak_reaction beta=independent_move lagging=false
  Bitwise to add HYPE to balance sheet using fees from Hyperliquid ETF

- [USEFUL] 2026-05-19 02:45 HYPE institutional_flow
  |ret_4h|=0.0433 |ret_24h|=0.0690 |ab_vs_btc|=0.0621
  react=vol_reaction beta=independent_move lagging=false
  Bitwise将用10%管理费购买$HYPE

- [USEFUL] 2026-05-19 04:30 XRP token_unlock
  |ret_4h|=0.0027 |ret_24h|=0.0244 |ab_vs_btc|=0.0219
  react=no_reaction beta=independent_move lagging=false
  XRP price slips 2% on profit taking

- [USEFUL] 2026-05-19 04:30 XRP token_unlock
  |ret_4h|=0.0027 |ret_24h|=0.0244 |ab_vs_btc|=0.0219
  react=no_reaction beta=independent_move lagging=false
  XRP price slips 2% on profit taking

- [NEUTRAL] 2026-05-19 06:42 ETH staking_governance
  |ret_4h|=0.0040 |ret_24h|=0.0126 |ab_vs_btc|=0.0090
  react=no_reaction beta=beta_like lagging=false
  以太坊质押比例上升至31%，长期持有者信心依旧

- [NEUTRAL] 2026-05-19 06:42 ETH staking_governance
  |ret_4h|=0.0040 |ret_24h|=0.0126 |ab_vs_btc|=0.0090
  react=no_reaction beta=beta_like lagging=false
  以太坊质押比例上升至31%，长期持有者信心依旧

- [NEUTRAL] 2026-05-19 10:23 ETH hack_security
  |ret_4h|=0.0006 |ret_24h|=0.0092 |ab_vs_btc|=0.0078
  react=no_reaction beta=beta_like lagging=true
  黑客攻击Monad Echo协议，损失约7600万美元

- [NEUTRAL] 2026-05-19 09:00 HYPE institutional_flow
  |ret_4h|=0.0089 |ret_24h|=0.0116 |ab_vs_btc|=0.0076
  react=weak_reaction beta=beta_like lagging=true
  🔥 BULLISH: Bitwise announces it will hold $HYPE on its balance sheet, allocating 10% of its Hyperliq

- [NEUTRAL] 2026-05-19 10:12 ETH staking_governance
  |ret_4h|=0.0055 |ret_24h|=0.0058 |ab_vs_btc|=0.0069
  react=weak_reaction beta=beta_like lagging=false
  5/18 Ethereum ETF Net Flow: $-84.14m
$ETHA (BlackRock): –$55.40m
$FETH (Fidelity): –$14.70m
$ETHW (B

- [NEUTRAL] 2026-05-19 10:12 ETH staking_governance
  |ret_4h|=0.0055 |ret_24h|=0.0058 |ab_vs_btc|=0.0069
  react=weak_reaction beta=beta_like lagging=false
  5/18 Ethereum ETF Net Flow: $-84.14m
$ETHA (BlackRock): –$55.40m
$FETH (Fidelity): –$14.70m
$ETHW (B

## 9. Conclusions

Historical useful_rate=7.1% (baseline only, not predictive). Mean |ab_vs_btc_24h|=0.58% — most signals move with BTC. Current backtest validates historical candidate samples, not real-time Market Radar signals.

> Thresholds NOT modified for display. For Market Radar signal structure observation only. Not trading advice.
