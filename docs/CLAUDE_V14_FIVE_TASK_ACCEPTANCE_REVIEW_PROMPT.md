# Crypto Event Intelligence v14 Five-Task Acceptance Review

你继续以外部产品负责人 + 量化研究负责人视角审查。请直接批评，不要迎合，完整中文。

## 上一轮你要求 5 个脚本级任务

1. `validate_publishable_criteria.py` 扩到 30 个 Golden 样本，输出 recall / precision / rejection reasons。
2. `build_etf_daily_digest.py` 增加 7d/30d 均值、z-score、异常判断、Top ETF 明细。
3. `build_first_hand_publish_candidates.py` 配置化路由规则，去重，优先级排序。
4. `aggregate_hyperliquid_snapshot.py` 新建 Hyperliquid 静态仓位早报背景卡。
5. `test_end_to_end_publish.py` 增加时间模拟、延迟计算、人工复核标记。

## 当前已完成结果

### 1. Golden publishable criteria validation

文件：
- `data/v14_publishable_golden_events.csv`
- `scripts/validate_publishable_criteria.py`
- `results/v14_publishable_criteria_validation_summary.csv`

结果：
- golden_rows: 30
- expected_publishable_rows: 18
- actual_publishable_rows: 18
- recall: 1.0
- precision_estimate: 1.0
- false_positive_rows: 0
- false_negative_rows: 0
- failed_rows: 0
- top_rejection_reasons: observable_impact_ok:11;source_basis_ok:4;not_price_in_ok:1

### 2. ETF daily anomaly detection

文件：
- `scripts/build_etf_daily_digest.py`
- `results/v14_etf_daily_digest_summary.csv`

结果：
- rows: 612
- latest_date: 27 May 2026
- latest_days_lag: 1
- date_validation_status: ok
- latest_total_net_flow_usd: -733,400,000
- flow_7d_avg: -239,242,857.14
- flow_30d_avg: -33,690,000
- flow_30d_std: 340,470,833.16
- flow_zscore: -2.0551
- is_anomaly: true
- top_3_etf_by_flow: IBIT:-527800000;GBTC:-104800000;FBTC:-60300000
- publishable_daily_digest: true

### 3. First-hand watcher routing

文件：
- `config/routing_rules.yaml`
- `scripts/build_first_hand_publish_candidates.py`
- `results/v14_first_hand_publish_candidates_summary.csv`

结果：
- input_rows: 9
- intraday_candidate_rows: 0
- digest_candidate_rows: 1
- daily_digest_candidate_rows: 1
- archived_rows: 7
- duplicate_rows: 0

### 4. Hyperliquid snapshot background card

文件：
- `scripts/aggregate_hyperliquid_snapshot.py`
- `results/v14_hyperliquid_snapshot_card.md`
- `results/v14_hyperliquid_snapshot_summary.csv`

结果：
- position_count: 5
- total_position_value_usd: 329,883,053.54
- top10_concentration_pct: 100.0
- near_liquidation_value_usd: 0
- baseline_status: missing_previous_snapshot

当前卡片核心内容：

```text
Hyperliquid 市场结构背景
监控仓位数：5｜总规模：3.30 亿美元
Top 持仓集中度：100.0%
距离清算价 <5%：0
Top 持仓：HYPE 空 1.03 亿美元，ETH 多 7952 万美元，HYPE 多 7837 万美元...
```

### 5. End-to-end local preview

文件：
- `scripts/test_end_to_end_publish.py`
- `results/v14_e2e_publish_preview.md`
- `results/v14_e2e_publish_preview_summary.csv`

结果：
- etf_publishable: true
- first_hand_publishable_rows: 2
- events_detected: 9
- events_published: 2
- events_need_review: 2
- avg_latency_minutes: 348.2
- max_latency_minutes: 690.0
- latency_sla_pass: false
- telegram_send: false

解释：
- 当前一手 watcher 样本不是实时 SLA 合格状态，不能自动盘中推送。
- 适合本地预览、早晚报或继续补实时采集。

## 请你继续审查

请重点回答：

1. 这 5 项是否真的达到你上一轮要求？哪些是形式上达标但产品上不达标？
2. Golden 30 个样本是否仍然太“手写适配”？下一步如何避免为样本调规则？
3. ETF 日频异常检测是否可以进入正式晚报？阈值是否需要改？
4. Hyperliquid 早报背景卡还缺哪些字段才能有用户价值？baseline missing 是否能接受？
5. E2E 延迟 SLA false 表明什么？下一步是修采集频率、模拟方式，还是先不做实时？
6. 接下来只允许做 3 个任务，你会要求做什么？请精确到脚本名和验收标准。
7. 哪些模块继续暂停？

