# Market Radar Delta Monitor Preview v1.5C

Generated: 2026-06-01 15:23:41 UTC+8

## Snapshot Status

- total_snapshots: 65 | distinct_times: 10
- has_size_field: True
- delta_basis_distribution: {'size': 11, 'notional_usd_fallback': 0, 'unavailable': 16}
- price_drift_noise_count: 6
- cooldown_applied: 0

## Trigger Rules (v1.5B size-primary)

- size_5m_impact>=$5M | size_1h_impact>=$10M | size_24h_impact>=$30M
- size_pct>=15% (1h/24h) | liq_delta>=5pp | side_flip
- Cooldown: 30min per address+asset+side (unless side_flip or liq_delta>=10pp)
- Price drift (size=0 but notional moved): filtered as noise

## Triggered Deltas

| entity | asset | side | window | size_delta | notional | basis | reasons |
|---|---|---|---:|---:|---|---|
| Unknown HYPE Whale | HYPE | long | 1h | +248407.6788 | $+18.1M | size | size_1h_impact=$18.1M |
| Matrixport Related | ETH | long | 1h | +7200.0000 | $+14.3M | size | size_1h_impact=$14.3M |

## Address Behavior Profiles (v1.5C)

- [Unknown HYPE Whale] HYPE long: profile_enabled=True
  reason= snapshots=10 span=60min
  rank=HYPE 监控池 Top 3 behaviors=['持仓新高'] risks=[]
  text: HYPE 监控池 Top 3；持仓新高。
- [Matrixport Related] ETH long: profile_enabled=True
  reason= snapshots=10 span=60min
  rank=ETH 监控池 Top 3 behaviors=[] risks=[]
  text: ETH 监控池 Top 3。

## Price Drift Items (filtered as noise)

- [Unknown HYPE Whale] HYPE: size unchanged, notional $-0.8M (price drift)
- [Matrixport Related] ETH: size unchanged, notional $-0.1M (price drift)
- [loraclexyz] ASTER: size unchanged, notional $-0.0M (price drift)
- [loraclexyz] TON: size unchanged, notional $-0.0M (price drift)
- [loraclexyz] ZEC: size unchanged, notional $-0.0M (price drift)

> For Market Radar signal structure observation only. Not trading advice.
