# Crypto Event Intelligence v14 Validation Loop Review

你继续以外部产品负责人 + 量化研究负责人视角审查。请直接批评，不要迎合，完整中文。

## 背景

你上一轮批评我们：

- 281 条全 blocked 不能当成果，标准必须能放过已知应发事件。
- ETF 日频数据出现 2026 日期必须做日期验证，不能未验证就汇报。
- 一手 watcher 的数据来源和端到端发布链路必须说清楚。
- 先把一个功能做对，再扩源。

## 本轮已修

### 1. ETF 日期验证

修改：
- `scripts/build_etf_daily_digest.py`

新增 summary 字段：
- `latest_date_sort`
- `latest_days_lag`
- `date_validation_status`

当前结果：
- rows: 612
- latest_date: 27 May 2026
- latest_date_sort: 2026-05-27
- current date: 2026-05-28
- latest_days_lag: 1
- date_validation_status: ok
- latest_total_net_flow_usd: -733,400,000
- publishable_daily_digest: true

说明：当前环境日期就是 2026-05-28，所以 2026-05-27 不是未来数据，是最新已完成交易日。

### 2. Golden events 验证最小可发布标准

新增：
- `data/v14_publishable_golden_events.csv`
- `scripts/validate_publishable_criteria.py`

Golden 样本：
- FTX 暂停提现：应发
- FTX 破产：应发
- UST/LUNA 脱锚：应发
- Celsius 暂停提现：应发
- Ronin bridge exploit：应发
- Mango exploit：应发
- Binance 官方上币公告：应发
- Curve exploit：应发
- USDC/SVB 脱锚：应发
- Binance 常规维护恢复提现：不应发

验证结果：
- golden_rows: 10
- expected_publishable_rows: 9
- actual_publishable_rows: 9
- failed_rows: 0

### 3. 一手 watcher 路由来源说清楚

新增：
- `scripts/build_first_hand_publish_candidates.py`

输入：
- `data/watcher_alerts_raw.csv`

当前 9 条数据来源：
- Hyperliquid clearinghouse state snapshot
- CEX listing announcement watcher
- Token unlock calendar watcher

路由结果：
- input_rows: 9
- intraday_candidate_rows: 0
- digest_candidate_rows: 1
- daily_digest_candidate_rows: 1
- archived_rows: 7

规则：
- Hyperliquid 静态 snapshot 不发盘中，除非有仓位状态变化。
- Token unlock 大额且占比高进日频摘要。
- CEX listing 进摘要候选。

### 4. 端到端本地发布预览

新增：
- `scripts/test_end_to_end_publish.py`

输出：
- `results/v14_e2e_publish_preview.md`
- `results/v14_e2e_publish_preview_summary.csv`

当前结果：
- etf_publishable: true
- first_hand_publishable_rows: 2
- telegram_send: false
- status: pass

本预览只验证本地链路，不自动发送 Telegram。

## 请你继续批评并给下一批脚本级任务

请重点回答：

1. Golden events 这种验证方式是否够？哪些样本不该放，哪些必须补？
2. 当前最小可发布标准是否开始像“标准”，还是仍然是为了过测试而写？
3. ETF 日频晚报现在是否可以进入正式晚报？还缺哪些字段必须补？
4. 一手 watcher 当前路由是否合理？CEX listing 和 token unlock 是否应该进入同一个端到端预览？
5. Hyperliquid 静态 snapshot 应该做早报背景还是彻底归档？需要什么聚合卡？
6. 接下来 1 天只允许做 5 个任务，你会要求我们改哪 5 个脚本？请精确到脚本名和验收标准。
7. 哪些模块继续暂停？

