# v0.4.1 Auto50 Backtest Findings

- Total samples: 50

## Backfill Status
| value | count |
|---|---:|
| partial | 38 |
| skipped | 12 |

## Quality Status
| value | count |
|---|---:|
| warning | 38 |
| fail | 12 |

## Samples By Event Type
| value | count |
|---|---:|
| macro | 42 |
| network_upgrade | 5 |
| hack_security | 2 |
| institutional_flow | 1 |

## Event Type Abnormal Return
| event_type | avg_abnormal_vs_btc_1h | avg_abnormal_vs_btc_4h | avg_abnormal_vs_btc_24h | avg_abnormal_vs_btc_72h |
| --- | --- | --- | --- | --- |
| hack_security | -0.000361 | nan | nan | nan |
| institutional_flow | 0.000000 | nan | nan | nan |
| macro | 0.000051 | 0.001343 | nan | nan |
| network_upgrade | 0.000296 | 0.001413 | nan | nan |

## Event Type Win Rate
| event_type | win_rate_vs_btc_1h | win_rate_vs_btc_4h | win_rate_vs_btc_24h | win_rate_vs_btc_72h |
| --- | --- | --- | --- | --- |
| hack_security | 0.000000 | nan | nan | nan |
| institutional_flow | 0.000000 | nan | nan | nan |
| macro | 0.133333 | 0.571429 | nan | nan |
| network_upgrade | 0.400000 | 0.666667 | nan | nan |

## Best 10 Events By 24h Abnormal Vs BTC
_No rows._

## Worst 10 Events By 24h Abnormal Vs BTC
_No rows._

## Suspicious Extreme Return Samples
_No rows._

## Preliminary Notes
- Event types with fewer than 5 valid samples are too small to judge: hack_security, institutional_flow.
- No suspicious_extreme_return rows were flagged.
