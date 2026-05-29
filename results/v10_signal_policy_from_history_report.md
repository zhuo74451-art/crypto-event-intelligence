# 历史回测生成的 TG 信号策略建议

这份文件把历史回测中的来源和事件类型表现转成机器可读的初步动作：提高权重、只进早晚报、继续收集、降权或重新审查 benchmark。

## 策略表

| 范围 | 名称 | 样本 | 24h有效 | 24h平均异常收益 | 动作 | 原因 |
| --- | --- | ---: | ---: | ---: | --- | --- |
| source | tg:HyperInsight | 20 | 20 | 0.009271 | boost | 历史样本显示有一定后续波动，优先扩样本，但仍需分资产和分市场状态验证。 |
| source | webhook | 48 | 48 | -0.000469 | review_benchmark | BTC/ETH 占比过高，当前异常收益结论会被 benchmark 污染，不能直接用于雷达加权。 |
| source | news:jin10 | 28 | 28 | 0.0 | review_benchmark | BTC/ETH 占比过高，当前异常收益结论会被 benchmark 污染，不能直接用于雷达加权。 |
| source | news:cryptonews | 13 | 13 | -0.001263 | review_benchmark | BTC/ETH 占比过高，当前异常收益结论会被 benchmark 污染，不能直接用于雷达加权。 |
| source | news:coinpaper | 5 | 5 | -0.002733 | review_benchmark | BTC/ETH 占比过高，当前异常收益结论会被 benchmark 污染，不能直接用于雷达加权。 |
| source | news:coinpedia | 2 | 2 | 0.001749 | review_benchmark | BTC/ETH 占比过高，当前异常收益结论会被 benchmark 污染，不能直接用于雷达加权。 |
| source | news:odaily_exchange_gap | 2 | 2 | -0.028497 | collect_more | 样本太少，不能下结论；保留但不提高权重。 |
| source | news:bitcoinmagazine | 1 | 1 | 0.0 | review_benchmark | BTC/ETH 占比过高，当前异常收益结论会被 benchmark 污染，不能直接用于雷达加权。 |
| source | news:utoday | 1 | 1 | 0.0 | review_benchmark | BTC/ETH 占比过高，当前异常收益结论会被 benchmark 污染，不能直接用于雷达加权。 |
| event_type | macro | 94 | 94 | 0.000865 | review_benchmark | BTC/ETH 占比过高，当前异常收益结论会被 benchmark 污染，不能直接用于雷达加权。 |
| event_type | hack_security | 10 | 10 | -0.003375 | review_benchmark | BTC/ETH 占比过高，当前异常收益结论会被 benchmark 污染，不能直接用于雷达加权。 |
| event_type | institutional_flow | 6 | 6 | 0.019451 | collect_more | 样本太少，不能下结论；保留但不提高权重。 |
| event_type | halving | 3 | 3 | 0.0 | review_benchmark | BTC/ETH 占比过高，当前异常收益结论会被 benchmark 污染，不能直接用于雷达加权。 |
| event_type | staking_governance | 3 | 3 | -0.012606 | review_benchmark | BTC/ETH 占比过高，当前异常收益结论会被 benchmark 污染，不能直接用于雷达加权。 |
| event_type | network_upgrade | 2 | 2 | 0.002001 | review_benchmark | BTC/ETH 占比过高，当前异常收益结论会被 benchmark 污染，不能直接用于雷达加权。 |
| event_type | whale_position | 2 | 2 | -0.025591 | collect_more | 样本太少，不能下结论；保留但不提高权重。 |

## 说明

- `boost` 不是交易方向，只表示这个来源或事件类型值得扩样本、提高雷达关注度。
- `digest_only` 表示适合早报/晚报背景，不适合盘中频繁刷。
- `review_benchmark` 表示 BTC/ETH 污染较重，不能用当前异常收益直接判断有效性。
- `collect_more` 表示样本太少，先不做强结论。
