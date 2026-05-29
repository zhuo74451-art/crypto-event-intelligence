# v14 False Negative Case Review

生成时间：中国时间 2026-05-28 22:19:50 UTC+8

- false_negative_count：5
- dominant_block_reason：source_basis_ok
- recommended_policy：不直接放宽 source_basis；增加交叉验证字段后再放开。

| event_id | source_tier | subtype | action | evidence_requirement | title |
|---|---|---|---|---|---|
| adv_016 | trusted_media | exchange_halt | require_structured_evidence | trusted_media_market_structure_event | Trusted media reports exchange wallet freeze confirmed by three users |
| adv_017 | trusted_media | exploit_or_theft | require_cross_validation | trusted_media_security_with_signed_proof | Research desk publishes signed proof of exploit loss before official post |
| adv_018 | trusted_media | etf_or_fund_flow | require_structured_evidence | trusted_media_market_structure_event | ETF issuer files urgent amendment changing creation basket mechanics |
| adv_019 | trusted_media | stablecoin_supply_or_flow | require_structured_evidence | trusted_media_market_structure_event | Stablecoin issuer transaction observed by public dashboard before explorer label |
| adv_020 | community_or_unknown | exchange_halt | require_official_identity_mapping | verified_founder_boundary | Protocol emergency shutdown reported by verified founder account |
