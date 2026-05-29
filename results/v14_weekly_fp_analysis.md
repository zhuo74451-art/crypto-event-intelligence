# v14 Weekly FP/FN Analysis

生成时间：中国时间 2026-05-28 22:24:33 UTC+8

## 指标

- FP率：8.33%（目标 <5%）
- FN率：8.33%（目标 <10%）
- Precision：0.8148（目标 >=0.8500）
- Recall：0.8148（目标 >=0.8500）
- 状态：review

## 误判原因

| type | reason | count | next action |
|---|---|---:|---|
| false_negative | source_basis_ok | 5 | 补充交叉验证证据 |
| false_positive | market_already_available | 1 | 补充识别规则 |
| false_positive | deprecated_market_scope | 1 | 补充识别规则 |
| false_positive | asset_mapping_conflict_residual | 1 | 补充识别规则 |
| false_positive | inventory_rebalance_residual | 1 | 补充识别规则 |
| false_positive | collateral_rotation_residual | 1 | 补充识别规则 |

## FN复查结论

- adv_016：require_structured_evidence｜trusted_media_market_structure_event｜Trusted media reports exchange wallet freeze confirmed by three users
- adv_017：require_cross_validation｜trusted_media_security_with_signed_proof｜Research desk publishes signed proof of exploit loss before official post
- adv_018：require_structured_evidence｜trusted_media_market_structure_event｜ETF issuer files urgent amendment changing creation basket mechanics
- adv_019：require_structured_evidence｜trusted_media_market_structure_event｜Stablecoin issuer transaction observed by public dashboard before explorer label
- adv_020：require_official_identity_mapping｜verified_founder_boundary｜Protocol emergency shutdown reported by verified founder account

## 下一步

- 不直接放宽 source_basis。
- 先增加结构化证据字段和交叉验证来源，再决定是否提高 Recall。
- FP 目标小于 5%，当前未达标时保持 review，不进入正式放量。
