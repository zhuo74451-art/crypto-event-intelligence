# v11 历史优先雷达路由策略

- 生成时间：2026-05-28 19:24:40 UTC+8
- 策略行数：62
- boost：1，downrank：0，digest_only：3，collect_more：35

## 策略说明

- 这张表只决定 TG 雷达展示优先级、是否转早午晚报、是否延长冷却；不产生任何交易方向。
- 历史样本不足或 benchmark 污染时，默认 collect_more/review_benchmark，而不是强行下结论。
- false-positive-like 只来自价格回看和雷达决策日志，不依赖用户反馈。

## 预览

| scope | name | action | cooldown | reason |
| --- | --- | --- | ---: | --- |
| event_subtype | exploit_or_theft | digest_only | 2.00 | 历史回测显示同类事件更像背景信息，优先进入早午晚报，不适合盘中反复刷。 |
| event_subtype | macro | review_benchmark | 1.50 | 历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。 |
| event_subtype | hack_security | review_benchmark | 1.50 | 历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。 |
| event_subtype | halving | review_benchmark | 1.50 | 历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。 |
| event_subtype | institutional_flow | review_benchmark | 1.50 | 历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。 |
| event_subtype | network_upgrade | review_benchmark | 1.50 | 历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。 |
| event_subtype | other | review_benchmark | 1.50 | 历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。 |
| event_subtype | staking_governance | review_benchmark | 1.50 | 历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。 |
| event_subtype | needs_taxonomy_review | collect_more | 1.20 | 历史样本不足，先收集更多，不做强结论；盘中降低重复曝光。 |
| event_subtype | etf_or_fund_flow | collect_more | 1.20 | 历史样本不足，先收集更多，不做强结论；盘中降低重复曝光。 |
| event_subtype | staking_or_governance | collect_more | 1.20 | 历史样本不足，先收集更多，不做强结论；盘中降低重复曝光。 |
| event_subtype | upgrade_or_fork | collect_more | 1.20 | 历史样本不足，先收集更多，不做强结论；盘中降低重复曝光。 |
| event_subtype | stablecoin_supply_or_flow | collect_more | 1.20 | 历史样本不足，先收集更多，不做强结论；盘中降低重复曝光。 |
| event_subtype | listing_delisting | collect_more | 1.20 | 历史样本不足，先收集更多，不做强结论；盘中降低重复曝光。 |
| event_subtype | long_short_crowding_extreme | collect_more | 1.50 | 历史样本不足，先收集更多，不做强结论；盘中降低重复曝光。 |
| event_subtype | rwa_tokenization | collect_more | 1.20 | 历史样本不足，先收集更多，不做强结论；盘中降低重复曝光。 |
| event_subtype | token_unlock_team_large | collect_more | 1.50 | 历史样本不足，先收集更多，不做强结论；盘中降低重复曝光。 |
| event_subtype | whale_position_static_large | collect_more | 1.50 | 历史样本不足，先收集更多，不做强结论；盘中降低重复曝光。 |
| event_subtype | token_unlock | collect_more | 1.20 | 历史样本不足，先收集更多，不做强结论；盘中降低重复曝光。 |
| event_subtype | whale_wallet_position | boost | 0.80 | 历史同类事件 24h 后续表现较好，允许提高观察优先级，但仍不代表方向建议。 |
| source_type | news:cointelegraph | digest_only | 2.00 | 历史回测显示同类事件更像背景信息，优先进入早午晚报，不适合盘中反复刷。 |
| source_type | news:jin10 | review_benchmark | 1.50 | 历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。 |
| source_type | webhook | review_benchmark | 1.50 | 历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。 |
| source_type | tg:HyperInsight | review_benchmark | 1.50 | 历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。 |
| source_type | news:cryptonews | review_benchmark | 1.50 | 历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。 |
| source_type | news:coinpaper | review_benchmark | 1.50 | 历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。 |
| source_type | news:odaily_exchange_gap | review_benchmark | 1.50 | 历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。 |
| source_type | news:utoday | review_benchmark | 1.50 | 历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。 |
| source_type | tg:OneMillion_AI | review_benchmark | 1.50 | 历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。 |
| source_type | news:bitcoinmagazine | review_benchmark | 1.50 | 历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。 |
