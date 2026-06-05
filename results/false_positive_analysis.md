# False Positive / Noise Analysis

- 生成时间：2026-06-01 13:29:50 UTC+8
- outcome rows：3
- decision rows：48
- group rows：3

## 结论

- 当前 live 样本仍少，绝大多数分组只能标记 collect_more，不能直接判死刑。
- adverse/flat/priced-in 会被记为 false-positive-like，用于后续降权、转影子或提高阈值。
- suppressed/digest 决策用于衡量重复噪音，不依赖用户反馈。

## Top Groups

- token_unlock / token_unlock / token_unlock_team_large：样本 1，false-positive-like 0.0000，建议 collect_more。
- long_short / market_structure / long_short_crowding_extreme：样本 1，false-positive-like 0.0000，建议 collect_more。
- hyperliquid / whale_position / whale_position_static_large：样本 1，false-positive-like 0.0000，建议 collect_more。
