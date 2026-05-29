# v14 False Positive Monitor

生成时间：中国时间 2026-05-28 22:19:49 UTC+8

## 总览

- 样本数：60
- 假阳性：5（8.33%）
- 假阴性：5（8.33%）
- Precision：0.8148
- Recall：0.8148
- 状态：review

## 主要误判原因

| type | reason | count |
|---|---|---:|
| false_negative | source_basis_ok | 5 |
| false_positive | market_already_available | 1 |
| false_positive | deprecated_market_scope | 1 |
| false_positive | asset_mapping_conflict_residual | 1 |
| false_positive | inventory_rebalance_residual | 1 |
| false_positive | collateral_rotation_residual | 1 |

## 待优先查看样本

- false_negative｜adv_016｜source_basis_ok｜Trusted media reports exchange wallet freeze confirmed by three users
- false_negative｜adv_017｜source_basis_ok｜Research desk publishes signed proof of exploit loss before official post
- false_negative｜adv_018｜source_basis_ok｜ETF issuer files urgent amendment changing creation basket mechanics
- false_negative｜adv_019｜source_basis_ok｜Stablecoin issuer transaction observed by public dashboard before explorer label
- false_negative｜adv_020｜source_basis_ok｜Protocol emergency shutdown reported by verified founder account
- false_positive｜adv_056｜market_already_available｜Official listing notice for token already active on major perpetual venues
- false_positive｜adv_057｜deprecated_market_scope｜Official parameter execution only affects deprecated isolated lending market
- false_positive｜adv_058｜asset_mapping_conflict_residual｜Bridge exploit confirmed but affected asset is an unlisted NFT collection
- false_positive｜adv_059｜inventory_rebalance_residual｜Large stablecoin treasury flow later identified as exchange inventory rebalancing
- false_positive｜adv_060｜collateral_rotation_residual｜Whale forced liquidation belongs to same-wallet collateral rotation
