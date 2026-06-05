# Market Radar Historical Backtest v1

## 1. Sample Scope
- total_signals: 37
- assets: 5
- event_types: 8
- time_range: 2026-05-19 00:43:00 ~ 2026-05-19 10:12:50
- source: v043_older_mature50_event_price_backfill.csv

## 2. Overall Results
- useful: 0  |  neutral: 6  |  noise: 31
- useful_rate: 0.0%
- avg |ret_4h|: 0.57%  |  avg |ret_24h|: 0.62%  |  avg |ab_vs_btc_24h|: 0.29%


## 3. By Event Type
| type | n | useful | rate | avg|ret_24h| |
|---|---:|---:|---:|
| institutional_flow | 3 | 0 | 0.0% | 0.40% |
| token_unlock | 3 | 0 | 0.0% | 1.16% |
| hack_security | 8 | 0 | 0.0% | 0.85% |
| network_upgrade | 3 | 0 | 0.0% | 0.35% |
| halving | 3 | 0 | 0.0% | 0.41% |
| staking_governance | 2 | 0 | 0.0% | 0.92% |
| other | 5 | 0 | 0.0% | 0.52% |
| macro | 10 | 0 | 0.0% | 0.50% |

## 4. By Source
| source | n | useful | noise | u_rate |
|---|---:|---:|---:|
| news:cryptonews | 7 | 0 | 5 | 0.0% |
| webhook | 25 | 0 | 22 | 0.0% |
| news:bitcoinmagazine | 1 | 0 | 1 | 0.0% |
| news:coinpedia | 2 | 0 | 2 | 0.0% |
| news:coinpaper | 1 | 0 | 0 | 0.0% |
| news:jin10 | 1 | 0 | 1 | 0.0% |

## 5. By Asset
| asset | n | useful | rate |
|---|---:|---:|
| BTC | 20 | 0 | 0.0% |
| XRP | 2 | 0 | 0.0% |
| ETH | 12 | 0 | 0.0% |
| SOL | 2 | 0 | 0.0% |
| AVAX | 1 | 0 | 0.0% |

## 6. Top Cases
- [NEUTRAL] 2026-05-19 XRP token_unlock
  ab_vs_btc_4h=0.0019  24h=0.0219  reason: mild: raw=2.4%
  XRP price slips 2% on profit taking

- [NEUTRAL] 2026-05-19 XRP macro
  ab_vs_btc_4h=0.0048  24h=0.0137  reason: mild: raw=1.1%
  Crude Oil Prices: Brent and WTI Rise as Markets Respond to Trump-Xi Trade Talks

- [NEUTRAL] 2026-05-19 ETH staking_governance
  ab_vs_btc_4h=0.0002  24h=0.0090  reason: mild: raw=1.3%
  以太坊质押比例上升至31%，长期持有者信心依旧

- [NOISE] 2026-05-19 ETH staking_governance
  ab_vs_btc_4h=0.0014  24h=0.0069  reason: no reaction
  5/18 Ethereum ETF Net Flow: $-84.14m
$ETHA (BlackRock): –$55.40m
$FETH (Fidelity

- [NOISE] 2026-05-19 ETH hack_security
  ab_vs_btc_4h=0.0011  24h=0.0063  reason: no reaction
  Lookonchain：过去4天内发生3起重大黑客攻击事件

- [NEUTRAL] 2026-05-19 ETH hack_security
  ab_vs_btc_4h=0.0042  24h=0.0060  reason: mild: raw=1.4%
  链上监测：过去4天内发生三起重大黑客事件

- [NOISE] 2026-05-19 ETH hack_security
  ab_vs_btc_4h=0.0026  24h=0.0059  reason: no reaction
  #PeckShieldAlert @dcfgod reports that @EchoProtocol_ was hacked on @monad 

The 

- [NOISE] 2026-05-19 ETH hack_security
  ab_vs_btc_4h=0.0041  24h=0.0058  reason: no reaction
  Exploit Alert 🚨

According to @dcfgod, @EchoProtocol_ on @monad has been exploit

## 7. Conclusions
- Candidate boosted event types: institutional_flow, token_unlock, hack_security
- Candidate deprioritized sources: news:bitcoinmagazine, news:coinpedia, news:jin10
- useful_rate=0.0% (historical baseline, not predictive)

> For Market Radar signal structure observation only. Not trading advice.
> Benchmark=BTC. abnormal = asset_return - btc_return.