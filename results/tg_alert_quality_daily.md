# TG 情报质量日报

- 生成时间：2026-06-01 13:29:49 UTC+8
- 情报账本总数：3
- 已评价记录：3

## 总览

- 完整评价：3
- 部分评价：0
- 跳过/错误：0
- 1h 可计算：3
- 4h 可计算：3
- 24h 可计算：3
- 72h 可计算：3

## 样本结构

| 事件子类型 | 数量 |
| --- | --- |
| token_unlock_team_large | 1 |
| long_short_crowding_extreme | 1 |
| whale_position_static_large | 1 |

## 当前样本对应的事件假设

| 事件子类型 | 数量 | TG优先级 | 待验证假设 |
| --- | --- | --- | --- |
| token_unlock_team_large | 1 | low | 团队/贡献者大额解锁通常是供给压力背景，盘中不应重复推送，适合日报/早晚报。 |
| long_short_crowding_extreme | 1 | medium | 多空持仓极端拥挤更适合做风险观察，不直接代表方向。 |
| whale_position_static_large | 1 | low | 静态大仓位本身不一定有方向性，但可作为后续仓位变化和清算风险的背景。 |

## 按事件子类型看 4h 主 benchmark 异常收益

| 事件子类型 | 样本数 | 平均异常收益 | 正收益比例 |
| --- | --- | --- | --- |
| token_unlock_team_large | 1 | 6.00% | 100.00% |
| long_short_crowding_extreme | 1 | -0.61% | 0.00% |
| whale_position_static_large | 1 | -1.62% | 0.00% |

## 按事件子类型看 24h 主 benchmark 异常收益

| 事件子类型 | 样本数 | 平均异常收益 | 正收益比例 |
| --- | --- | --- | --- |
| token_unlock_team_large | 1 | 10.93% | 100.00% |
| whale_position_static_large | 1 | 8.50% | 100.00% |
| long_short_crowding_extreme | 1 | 0.98% | 100.00% |

## 按是否提前反应看 4h

| 提前反应状态 | 样本数 | 平均异常收益 | 正收益比例 |
| --- | --- | --- | --- |
| none | 3 | 1.26% | 33.33% |

## 按 BTC 14日趋势看 4h

| 市场趋势 | 样本数 | 平均异常收益 | 正收益比例 |
| --- | --- | --- | --- |
| downtrend | 3 | 1.26% | 33.33% |

## 按 BTC 7日波动看 4h

| 波动状态 | 样本数 | 平均异常收益 | 正收益比例 |
| --- | --- | --- | --- |
| low_vol | 3 | 1.26% | 33.33% |

## 24h 表现最好事件

| 异常收益 | 资产 | 子类型 | 内容 |
| --- | --- | --- | --- |
| 10.93% | HOME | token_unlock_team_large |  |
| 8.50% | HYPE | whale_position_static_large |  |
| 0.98% | DOGE | long_short_crowding_extreme |  |

## 24h 表现最差事件

| 异常收益 | 资产 | 子类型 | 内容 |
| --- | --- | --- | --- |
| 0.98% | DOGE | long_short_crowding_extreme |  |
| 8.50% | HYPE | whale_position_static_large |  |
| 10.93% | HOME | token_unlock_team_large |  |

## 读法

- 主 benchmark 会按资产自动选择：BTC 事件默认相对 ETH；ETH 和小币默认相对 BTC。
- `partial` 通常表示情报太新，4h/24h/72h 还没到。
- `priced_in_flag` 用来识别发布前是否已经明显反应，避免把滞后快讯误当有效信号。
- BTC 市场趋势和波动状态用于粗分市场环境，后续会验证哪些事件类型只在特定环境有效。
- 本报告只用于市场结构观察和研究复盘，不构成任何交易建议。
