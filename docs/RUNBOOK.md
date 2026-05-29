# Crypto Event Intelligence Runbook

## 项目边界

Crypto Event Intelligence 是一个本地事件研究与复盘模块：把历史加密快讯 CSV 转成可复核事件样本，回填快讯发布后 1h / 4h / 24h / 72h 的资产价格变化，并计算相对 BTC / ETH 的异常收益。

本项目不接 Notion，不接交易，不接网页，不做交易建议，不做自动下单，不接 AI 自动分类。当前只使用本地 CSV / SQLite / Python 和公开行情 API。

## 安装依赖

```powershell
python -m pip install pandas requests
```

## v0.3.1 为什么先修时间

真实历史快讯里常见几种时间格式：ISO 字符串、Unix 秒级时间戳、Unix 毫秒级时间戳、Excel 序列日期。Excel 序列日期是 Excel 内部保存日期的数字，通常以 `1899-12-30` 为基准，例如 `45301.885416666664` 代表 2024-01-10 21:15:00 UTC 附近。

回测必须把 `published_at/backtest_time` 标准化为 UTC ISO：

```text
YYYY-MM-DDTHH:MM:SSZ
```

原因：

- 价格 API 需要明确的 UTC 时间点。
- 纯数字时间容易被误读成 Unix 秒、Unix 毫秒或 Excel serial。
- 非标准时间如果直接进入回测，会污染 1h / 4h / 24h / 72h 窗口。
- 当前回测模拟的是“快讯发布后”的市场反应，不能偷看事件真实发生时间。

时间解析工具：

```text
scripts/utils/time_utils.py
```

核心函数：

```python
parse_any_time_to_utc_iso(value)
```

## 推荐流程

### 1. 准备历史快讯 CSV

模板：

```text
data/raw_news_export_template.csv
```

字段：

```text
raw_id,published_at,title,content,source,url,language,author,category,tags
```

`published_at` 可以是 ISO、Unix 秒、Unix 毫秒或 Excel 序列日期。导入脚本会统一转成 UTC ISO。

### 2. 导入候选事件

```powershell
python scripts/import_raw_news_to_event_candidates.py --input data/raw_news_export_template.csv --output data/event_candidates_review.csv --symbol-map data/symbol_map.csv --limit 100
```

输出：

```text
data/event_candidates_review.csv
```

关键字段：

- `raw_published_at`：原始时间。
- `published_at_utc`：标准化后的发布时间。
- `backtest_time_utc`：用于回测的 t0。
- `time_parse_status`：`ok` 或 `failed`。
- `time_parse_flags`：时间标准化标记。
- `candidate_asset_symbol`：规则识别出的资产。
- `candidate_event_type`：规则识别出的事件类型。
- `quality_flags`：候选质量问题。

### 3. 查看候选质量汇总

```powershell
python scripts/summarize_event_candidates.py --input data/event_candidates_review.csv --output-dir results
```

输出：

```text
results/v03_candidate_import_summary.csv
results/v03_candidate_summary_by_event_type.csv
results/v03_candidate_summary_by_scope.csv
```

重点看：

- `time_parse_failed_count` 是否为 0。
- `missing_asset_count` 是否过高。
- `multi_asset_count` 是否过高。
- `market_wide_count` 是否符合预期。
- `unknown_event_type_count` 是否过高。
- `asset_confidence_low_count` 是否过高。

如果这些数字很高，不要进入 50 条回测，先修 CSV 或规则。

### 时间统一规则

项目对人工复核统一显示北京时间：

```text
Asia/Shanghai
UTC+8
```

脚本内部仍保留 UTC，因为 Binance K线 API 使用 UTC 毫秒时间戳。

核心字段：

```text
published_at          # 北京时间，人工查看
published_at_utc      # UTC，机器计算
published_at_china    # 北京时间，人工查看

source_published_at_utc
source_published_at_china
source_timezone
source_timezone_assumption
source_lag_minutes

backtest_time         # 北京时间，人工查看
backtest_time_utc     # UTC，机器计算
backtest_time_china   # 北京时间，人工查看
backtest_time_basis   # 默认 published_at
```

规则：

- 没有时区的时间，例如 `2026-05-27 12:00:00`，默认按北京时间解析。
- 带 `Z` 或 `+00:00` 的时间按 UTC 解析，再转北京时间展示。
- Unix 秒 / 毫秒时间戳是绝对 UTC 时间。
- Excel 序列日期按北京时间墙上时间解释。
- 如果原始 CSV 以后有 `source_published_at`、`source_time` 或 `original_published_at`，脚本会单独解析源新闻时间。
- 如果原始 CSV 以后有 `source_timezone`，脚本会用该字段解析无时区的源新闻时间。
- 如果没有 `source_timezone`，脚本会读取 `data/source_timezone_rules.csv` 按来源推断。
- 回测默认使用 `published_at` 作为 `backtest_time`，避免用更早的源新闻时间造成偷看未来。
- 价格输出会同时写 `price_target_*_china` 和实际 Binance K线 `*_kline_time_china`。

源时区规则文件：

```text
data/source_timezone_rules.csv
```

规则优先级：

1. 原始时间自带 `Z` / `+08:00` / `-04:00` 等明确时区，直接按明确时区解析。
2. 原始 CSV 有 `source_timezone`，用该字段。
3. 按 `source` 命中 `data/source_timezone_rules.csv`。
4. 都没有则默认 `Asia/Shanghai`，并在审计里可见。

时间审计命令：

```powershell
python scripts/audit_event_time_provenance.py --candidates data/event_candidates_real_500_older_review.csv --backfill results/v043_older_mature50_event_price_backfill.csv --output results/v043_time_provenance_report.csv --summary results/v043_time_provenance_summary.csv
```

重点看：

- `timezone_assumed_china_count`
- `source_lag_over_30m_count`
- `source_lag_over_6h_count`
- `price_kline_lag_out_of_range_count`

如果 `price_kline_lag_out_of_range_count > 0`，说明价格 K线时间和目标时间错位，需要先排查再看收益。

### 4. 人工复核候选事件

打开：

```text
data/event_candidates_review.csv
```

人工填写 `review_decision`：

- `include`：进入回测。
- `exclude`：不要回测。
- `fix`：需要先修正币种、时间或类型。

第一轮 50 条不建议包含：

- 无明确资产。
- 多资产且无法判断主资产。
- 纯宏观但没有明确归因。
- 明显已经被市场提前消化。
- 不是价格相关事件。
- 发布时间明显滞后。
- 交易所没有价格数据。

### 5. 构建 50 条事件样本

```powershell
python scripts/build_events_from_review.py --input data/event_candidates_review.csv --output data/events_raw_50.csv --limit 50
```

脚本只输出 `review_decision=include` 的行，并优先使用 `backtest_time_utc` 作为 `event_time`。

### 6. 运行 50 条回测

```powershell
python scripts/run_v03_50_sample_backtest.py --review-input data/event_candidates_review.csv --limit 50
```

输出：

```text
results/v03_event_price_backfill_50.csv
results/v03_event_quality_report_50.csv
results/v03_event_backtest_summary_50.csv
results/v03_event_backtest_summary_by_direction_50.csv
```

## 时间质量检查

质量脚本：

```powershell
python scripts/validate_backfill_results.py --input results/v03_event_price_backfill_50.csv --output results/v03_event_quality_report_50.csv
```

新增字段：

- `parsed_event_time_utc`
- `time_quality_status`

规则：

- 无法解析时间：`invalid_event_time`，质量失败。
- 可以解析但不是标准 UTC ISO：`non_standard_time_format`，质量警告。
- 晚于当前时间：`future_event_time`，质量失败。

## 资产和事件类型识别

候选导入只使用规则，不使用 AI。

优先资产规则包括：

- Bitcoin / BTC / 比特币 -> BTC
- Ethereum / ETH / 以太坊 -> ETH
- Solana / SOL / 索拉纳 -> SOL
- XRP / Ripple / 瑞波 -> XRP
- Dogecoin / DOGE / 狗狗币 -> DOGE
- Chainlink / LINK -> LINK
- Avalanche / AVAX -> AVAX
- BNB / Binance Coin / 币安币 -> BNB

只有在没有明确资产、但命中宏观/全市场关键词时，才默认 `candidate_asset_symbol=BTC`。

事件类型规则包括：

- `network_upgrade`
- `token_unlock`
- `halving`
- `macro`
- `staking_governance`
- `institutional_flow`
- `whale_position`
- `exchange_listing`
- `hack_security`
- `other`

## v0.3.1 验收命令

```powershell
python scripts/import_raw_news_to_event_candidates.py --input data/raw_news_export_template.csv --output data/event_candidates_review.csv --symbol-map data/symbol_map.csv --limit 100
python scripts/summarize_event_candidates.py --input data/event_candidates_review.csv --output-dir results
python scripts/build_events_from_review.py --input data/event_candidates_review.csv --output data/events_raw_50.csv --limit 50
python scripts/run_v03_50_sample_backtest.py --review-input data/event_candidates_review.csv --limit 50
```

注意：真实使用时，第二步之后需要人工复核 `data/event_candidates_review.csv`，把合格样本标记为 `include`，再运行后两步。

## v0.5 统计验证

v0.4.3 的 older500 链路证明了真实数据 pipeline 可以跑通，但这不等于发现了稳定 alpha。v0.5 的目标是验证当前异常收益是否可能只是小样本、分桶、multiple testing 或分类噪声造成。

运行统计验证：

```powershell
python scripts/statistical_validate_event_returns.py --backfill results/v043_older_mature50_event_price_backfill.csv --quality results/v043_older_mature50_event_quality_report.csv --output results/v05_event_return_statistical_validation.csv --report results/v05_event_return_statistical_validation.md
```

输出：

```text
results/v05_event_return_statistical_validation.csv
results/v05_event_return_statistical_validation.md
```

检查重点：

- `sample_count` 是否达到最小样本阈值。
- `bootstrap_ci_low/bootstrap_ci_high` 是否跨过 0。
- `permutation_p_value` 是否只是偶然显著。
- `fdr_bh_p_value` 是否通过多重检验校正。
- `reliability_label` 是否仍然是 `too_small`。

导出 `other` 桶人工复核：

```powershell
python scripts/export_other_review.py --input results/v043_older_mature50_event_price_backfill.csv --output data/v05_other_event_review.csv
```

`other` 如果在 72h 表现最好，不能直接解释为一种事件类型有效。它更可能表示分类体系太粗，需要拆成更明确的事件类型或从结论中排除。

也可以一键运行 v0.5 验证：

```powershell
python scripts/run_v05_research_validation.py
```

当前 v0.5 默认结论：

- 没有任何 `event_type` 通过 FDR 校正。
- 大部分分桶样本量不足。
- v0.4.3 的 descriptive winners 只能作为观察，不能作为结论。

## v0.6 方向：事件准入质量层

v0.6 不先做 Regime Filter。原因是当前事件桶仍然较脏：`other` 不可解释、BTC/ETH benchmark 会污染结果、重复快讯没有聚合、很多候选还不适合发群。

v0.6 先做：

- entity dictionary
- 事件实体识别
- L1 / L2 事件分类
- 多源重复事件聚合
- BTC / ETH benchmark 修正
- real-time relevance score
- publish decision：`auto_publish` / `human_review` / `discard`

详细规划见：

```text
docs/PROJECT_PLAN.md
docs/V06_INITIAL_SCOPE.md
docs/OPEN_QUESTIONS.md
```

Regime Filter 仍然重要，但推迟到事件准入质量层稳定之后。

### 运行 v0.6 事件准入质量层

```powershell
python scripts/run_v06_event_intake_quality.py --input data/event_candidates_real_500_older_review_suggested.csv
```

默认输出：

```text
data/event_candidates_v06_enriched.csv
data/event_candidates_v06_deduped.csv
data/event_candidates_v06_relevance_scored.csv
results/v06_relevance_filter_summary.csv
```

单步运行：

```powershell
python scripts/enrich_event_entities.py --input data/event_candidates_real_500_older_review_suggested.csv --entity-dictionary data/entity_dictionary.csv --output data/event_candidates_v06_enriched.csv

python scripts/deduplicate_event_candidates.py --input data/event_candidates_v06_enriched.csv --output data/event_candidates_v06_deduped.csv --window-hours 2

python scripts/filter_research_relevant_events.py --input data/event_candidates_v06_deduped.csv --output data/event_candidates_v06_relevance_scored.csv --summary results/v06_relevance_filter_summary.csv
```

第一版 v0.6 默认比较保守：

- `auto_publish` 当前强制禁用；高分样本也会降级为 `human_review`。
- 大部分可疑但可能有价值的事件进入 `human_review`。
- `discard` 包含低相关、重复、缺实体、`other_review`、纯价格复述等。
- 不支持 Binance 价格的高价值资产事件进入 `unsupported_research`，不能进入 Binance 回测，但可以人工研究复核。

当前不要把 `auto_publish` 直接接 TG。先人工检查 `human_review` 的样本质量。

### 导出 v0.6.1 人工审阅队列

```powershell
python scripts/export_v06_review_queues.py --input data/event_candidates_v06_relevance_scored.csv
```

输出：

```text
data/event_candidates_v06_publish_review_queue.csv
data/event_candidates_v06_other_review_queue.csv
data/event_candidates_v06_discard_audit_sample.csv
results/v061_review_queue_report.md
```

### 生成 v0.6 人工标注表

```powershell
python scripts/prepare_v06_manual_label_sheet.py --output data/v06_manual_label_sheet.csv --summary results/v06_manual_label_sheet_summary.csv
```

输出：

```text
data/v06_manual_label_sheet.csv
results/v06_manual_label_sheet_summary.csv
```

默认会合并：

- 全量 publish review queue
- 64 条 other review
- 64 条 discard audit

目标是先做 200 条人工 ground truth。标注字段包括：

- `manual_decision`
- `manual_event_type_l1`
- `manual_event_type_l2`
- `manual_primary_asset_symbol`
- `manual_channel_route`
- `manual_useful_for_research`
- `manual_notes`

把 Cursor 交接给：

```text
docs/CURSOR_HANDOFF.md
```

方向性问题先记录到：

```text
docs/CLAUDE_QUESTION_BACKLOG.md
```

### 生成 v0.6.2 规则改进建议

```powershell
python scripts/analyze_v06_review_queues.py
```

输出：

```text
results/v062_review_queue_rule_suggestions.md
```

### 查看 v0.6.5 决策表

```text
docs/V065_DECISION_TABLE.md
```

Claude backlog 满 10 个问题后的回答：

```text
results/v06_claude_question_backlog_response.md
```

## v0.7 一手情报 watcher

v0.7 的目标是把二手快讯之外的链上/市场结构信号变成结构化事件。当前实现的是本地最小闭环：

- 重点 Ethereum 地址 ERC20 转账监控
- USDT / USDC treasury mint/burn 监控
- Aave V3 Ethereum 大额借贷清算监控
- watcher alert 归一化为现有 event schema
- 生成本地 TG 草稿预览
- 可选接入现有 Binance 价格回填与质量检查

默认不调用 Telegram，不自动发送，不提供交易建议。

### 文件

```text
data/watchlist_addresses.csv
data/stablecoin_watchlist.csv
data/liquidation_market_map.csv
data/watcher_alerts_raw.csv
data/watcher_events_raw.csv
data/tg_drafts_v07_watcher_private_pilot.csv
results/v07_watcher_daily_report.md
results/tg_drafts_v07_watcher_private_pilot.md
```

### 无 Etherscan key 的本地验证

没有 `ETHERSCAN_API_KEY` 时，脚本会写入 mature sample alerts，用于验证本地 pipeline、TG 草稿和价格回填兼容性：

```powershell
python scripts/run_v07_first_hand_watchers.py --hours 24 --limit-alerts 100 --backfill
```

### 使用真实 Etherscan 数据

只在当前 PowerShell 临时设置 key，不写入代码、文档或 Git：

```powershell
$env:ETHERSCAN_API_KEY="你的_key"
python scripts/run_v07_first_hand_watchers.py --hours 24 --limit-alerts 100
```

也可以使用本地忽略的 secret 文件，见：

```text
docs/SECRET_SETUP.md
config/secrets.example.ps1
scripts/load_local_secrets.ps1
```

如需验证 watcher events 能进入现有价格回填：

```powershell
$env:ETHERSCAN_API_KEY="你的_key"
python scripts/run_v07_first_hand_watchers.py --hours 96 --limit-alerts 100 --backfill
```

实时 watcher 产生的新事件通常还没有 24h/72h 后续价格，因此即时 backfill 可能出现 partial/skipped。成熟样本或历史窗口更适合完整回填。

### 接 TG 前检查

先看本地草稿：

```text
results/tg_drafts_v07_watcher_private_pilot.md
```

确认：

- `auto_send_enabled=false`
- 没有买入/卖出/做多/做空建议
- 地址标签可信
- 金额和 tx_hash 合理
- 稳定币 mint/burn 是观察，不解读成交易动作

TG 群测试应只发送 approved/pending_review 的少量样本，先不开自动发送。

### TG 群手动测试发送

先 dry-run 看一条消息，不调用 Telegram：

```powershell
python scripts/send_tg_draft_test.py --input data/tg_drafts_v07_watcher_private_pilot.csv --limit 1
```

确认无误后，只在当前 PowerShell 临时设置 bot token 和 chat id：

```powershell
$env:TELEGRAM_BOT_TOKEN="你的_bot_token"
$env:TELEGRAM_CHAT_ID="你的_chat_id"
python scripts/send_tg_draft_test.py --input data/tg_drafts_v07_watcher_private_pilot.csv --limit 1 --send
```

注意：

- 不要把 token/chat id 写入文件。
- 第一次只发 1 条。
- 当前脚本是手动测试发送，不是自动群发。
- 默认读取 `draft_text`；如果以后填了 `approved_text`，会优先发送 `approved_text`。
## v0.7 Server Live Watcher Deployment

Current production-style first-hand watcher service:

```text
server_path: /opt/crypto-event-intel-watchers
systemd_service: crypto-event-intel-watchers.service
interval_seconds: 300
mode: send
```

It runs these local CSV/Python watcher sources:

- Watched Ethereum address ERC20 transfers.
- USDT/USDC treasury mint/burn monitoring.
- Curated Hyperliquid large-position monitoring.
- CEX wallet net-flow lite monitoring.
- Binance USD-M funding-rate anomaly monitoring.
- Aave V3 Ethereum lending liquidation monitoring.

Check service status:

```bash
systemctl status crypto-event-intel-watchers.service
```

View watcher log:

```bash
tail -100 /opt/crypto-event-intel-watchers/results/v07_tg_live_monitor.log
```

Restart only the first-hand watcher service:

```bash
systemctl restart crypto-event-intel-watchers.service
```

Stop only the first-hand watcher service:

```bash
systemctl stop crypto-event-intel-watchers.service
```

Important:

- This service is separate from `/opt/x-monitor/current`.
- It does not change the existing news collection/publishing containers.
- It uses existing Telegram env values from the server and a private Etherscan env file.
- Do not write bot tokens, API keys, or chat IDs into code, docs, logs, or Git.
- Messages remain event intelligence only and must not include buy/sell/long/short advice.

Quality gate outputs:

```bash
cat /opt/crypto-event-intel-watchers/results/v07_tg_live_quality_gate_summary.csv
tail -100 /opt/crypto-event-intel-watchers/results/v07_tg_live_quality_gate_report.csv
```

Rate-limit and follow-up outputs:

```bash
cat /opt/crypto-event-intel-watchers/results/v08_tg_rate_limit_summary.csv
cat /opt/crypto-event-intel-watchers/results/v08_tg_live_performance_summary.csv
cat /opt/crypto-event-intel-watchers/results/v08_tg_alert_followup_summary.csv
tail -100 /opt/crypto-event-intel-watchers/results/v08_tg_live_performance_report.md
tail -100 /opt/crypto-event-intel-watchers/results/v08_tg_alert_followup_report.md
```

The gate blocks missing/low-quality rows before Telegram send. Main checks:

- missing candidate id, text, asset, or amount
- low/sample confidence
- event type not in the allowed first-hand watcher set
- amount below source-specific threshold
- explicit trading-advice language
- low quality score after amount/confidence/strength scoring

The v0.8 live sender also limits noise:

- Daily live-send cap defaults to 15 alerts.
- Per-source caps default to 3-8 alerts/day depending on source.
- Same `event_type + asset` cooldown defaults to 60 minutes.
- Routine send capacity is shaped by China-time user attention windows in `config/tg_send_time_policy.csv`.
- Telegram replies/reactions are not part of the core quality loop.
- Sent alerts are followed up after 4h by default; 24h results appear after the alert is old enough.

Default China-time timing policy:

| Window | Behavior |
|---|---|
| 00:00-07:00 | Quiet window. Only `critical` alerts pass by default. |
| 07:00-10:00 | Morning check window. Normal useful alerts can pass. |
| 10:00-15:00 | Daytime active window. Normal useful alerts can pass. |
| 15:00-18:00 | Afternoon trading window. Slightly higher per-cycle capacity. |
| 18:00-24:00 | Evening trading window. Slightly higher per-cycle capacity. |

This is not a hard timetable. The service still runs continuously every 5 minutes. The time policy only decides whether routine lower-priority alerts should be held back during low-attention hours and how much capacity to allow during active hours. Daily caps, source caps, quality gate, dedupe, and cooldown still apply.

Timing policy file:

```text
config/tg_send_time_policy.csv
```

Server check:

```bash
cat /opt/crypto-event-intel-watchers/config/tg_send_time_policy.csv
cat /opt/crypto-event-intel-watchers/results/v08_tg_rate_limit_summary.csv
```

## v0.8 Scheduled Digests

Scheduled digests are separate from the live watcher. They summarize recent windows for users who check Telegram around morning, noon, and evening.

Default behavior:

```text
morning window: previous day 20:00 to current day 08:00, China time
noon window: current day 08:00 to 12:00, China time
evening window: current day 12:00 to 20:00, China time
send times: around 08:30, 12:30, and 20:30 China time
timers:
- crypto-event-intel-morning-digest.timer
- crypto-event-intel-noon-digest.timer
- crypto-event-intel-evening-digest.timer
```

Local dry-run:

```powershell
python scripts/build_tg_morning_digest.py --output results/v08_tg_morning_digest.md --summary results/v08_tg_morning_digest_summary.csv
```

Local noon/evening dry-run:

```powershell
python scripts/build_tg_morning_digest.py --digest-label noon --window-end-hour 12 --window-hours 4 --output results/v08_tg_noon_digest.md --summary results/v08_tg_noon_digest_summary.csv
python scripts/build_tg_morning_digest.py --digest-label evening --window-end-hour 20 --window-hours 8 --output results/v08_tg_evening_digest.md --summary results/v08_tg_evening_digest_summary.csv
```

Local long/short snapshot only:

```powershell
python scripts/watch_binance_long_short_ratios.py --output data/binance_long_short_snapshot.csv --summary results/v08_binance_long_short_summary.csv --period 1h --limit 2
```

Server checks:

```bash
systemctl status crypto-event-intel-morning-digest.timer
systemctl status crypto-event-intel-noon-digest.timer
systemctl status crypto-event-intel-evening-digest.timer
systemctl list-timers 'crypto-event-intel-*-digest.timer' --no-pager
tail -100 /opt/crypto-event-intel-watchers/results/v08_tg_digest_systemd.log
tail -100 /opt/crypto-event-intel-watchers/results/v08_tg_morning_digest.md
tail -100 /opt/crypto-event-intel-watchers/results/v08_tg_noon_digest.md
tail -100 /opt/crypto-event-intel-watchers/results/v08_tg_evening_digest.md
cat /opt/crypto-event-intel-watchers/results/v08_tg_morning_digest_summary.csv
cat /opt/crypto-event-intel-watchers/results/v08_tg_noon_digest_summary.csv
cat /opt/crypto-event-intel-watchers/results/v08_tg_evening_digest_summary.csv
cat /opt/crypto-event-intel-watchers/results/v08_binance_long_short_summary.csv
```

The derivatives sentiment section uses Binance USD-M public market data:

- Top trader long/short position ratio.
- Top trader long/short account ratio.
- Global long/short account ratio.
- Taker buy/sell volume ratio.

Interpretation rule:

- Treat this as market-structure/crowding context.
- Do not describe it as a direction instruction.
- Read it together with funding, CEX netflow, Hyperliquid positions, and follow-up behavior.

Hyperliquid watcher also has stateful change detection:

```text
data/hyperliquid_position_state.csv
results/v07_hyperliquid_position_watcher_summary.csv
```

Default behavior:

- First observation only seeds state and does not alert.
- Existing unchanged positions do not alert again.
- Alert only when the position crosses threshold, changes side, or changes by at least 15% and 5,000,000 USD.
- This prevents old large Hyperliquid positions from being reposted every cycle.

TG follow-up report:

```text
scripts/build_tg_alert_followup_report.py
data/tg_alert_followup_events.csv
results/v08_tg_alert_followup_backfill.csv
results/v08_tg_alert_followup_summary.csv
results/v08_tg_alert_followup_report.md
```

Notes:

- It reads `data/tg_live_sent_state.csv`.
- Only `status=sent` rows with asset metadata are eligible.
- Default minimum age is 4 hours.
- Stablecoin flow and CEX stablecoin netflow use BTC as the price follow-up proxy.
- The report is for alert-quality review only and does not provide trading advice.

TG source usefulness report:

```powershell
python scripts/enrich_tg_sent_state_metadata.py
python scripts/build_tg_source_usefulness_report.py --lookback-days 7
```

Full TG quality loop:

```powershell
python scripts/run_tg_quality_loop.py --lookback-days 7 --followup-min-age-hours 4
```

This runs sent-state metadata enrichment, 4h/24h follow-up, and source usefulness reporting in one pass. Telegram replies/reactions are not part of the core quality loop.

Outputs:

```text
results/v08_tg_quality_loop_summary.csv
results/v08_tg_sent_state_metadata_enrichment_summary.csv
results/v08_tg_source_usefulness_report.md
results/v08_tg_source_usefulness_summary.csv
results/v08_tg_source_usefulness_by_source.csv
```

Interpretation:

- `promising`: 4h/24h follow-up behavior supports keeping the source.
- `review_noise`: lower priority, raise thresholds, or move to digest-only.
- `needs_instrumentation`: sent alerts exist but follow-up metadata is incomplete.
- `insufficient_data`: not enough observations.

This is an alert-quality report only. It is not a trading signal and does not produce buy/sell/long/short instructions.

Historical signal replay:

```powershell
python scripts/run_v08_historical_signal_replay.py --limit 200 --mode broad
python scripts/run_v08_historical_signal_replay.py --limit 120 --mode conservative
```

Outputs:

```text
data/events_v08_historical_replay_broad_200.csv
results/v08_historical_replay_broad_200_price_backfill.csv
results/v08_historical_replay_broad_200_quality_report.csv
results/v08_historical_replay_broad_200_backtest_summary.csv
results/v08_historical_replay_broad_200_findings.md
data/events_v08_historical_replay_conservative_120.csv
results/v08_historical_replay_conservative_120_price_backfill.csv
results/v08_historical_replay_conservative_120_quality_report.csv
results/v08_historical_replay_conservative_120_backtest_summary.csv
results/v08_historical_replay_conservative_120_findings.md
```

Use:

- `broad`: more sample size, more macro/BTC pollution.
- `conservative`: cleaner sample, still not a live publishing rule.

Important limitation:

BTC events versus BTC benchmark flatten `abnormal_vs_btc`. For BTC-heavy historical samples, read `asset_return_*` and future alternative benchmarks before drawing conclusions.

Current accepted direction:

- Exchange hot wallet single transfers are only high-threshold seed monitoring.
- v0.8 should prefer exchange net-flow aggregation over one-off exchange wallet transfers.
- Next source priority is market structure: order-book depth changes, DEX large swaps/liquidity changes, funding-rate anomalies, and lending-protocol liquidations.

## v0.8 CEX Netflow Lite

The first market-structure upgrade is CEX netflow lite.

It aggregates watched CEX hot-wallet ERC20 transfers by:

- entity
- asset
- window

Then it publishes only net-flow alerts that pass thresholds, instead of sending routine single wallet transfers.

Local run:

```powershell
$env:ETHERSCAN_API_KEY="your_key"
python scripts/watch_cex_netflows.py --hours 24 --window-hours 4 --sample-if-no-key false
```

Output:

```text
data/watcher_alerts_cex_netflows.csv
results/v08_cex_netflow_watcher_summary.csv
```

Server live service already runs this through:

```text
scripts/run_v07_first_hand_watchers.py
```

Current default gate:

```text
min_net_usd: 20,000,000
min_gross_usd: 50,000,000
window_hours: 4
```

Interpretation rule:

- CEX netflow is a market-structure observation.
- It must not be described as a directional trade cue.
- It should be read with order book, volume, funding, and follow-up price behavior.

## v0.8 Lending Liquidation Watcher

借贷清算 watcher 使用 Etherscan 只读 logs API 监控 Aave V3 Ethereum Pool 的 `LiquidationCall` 事件。

文件：

```text
scripts/watch_lending_liquidations.py
data/liquidation_market_map.csv
data/watcher_alerts_lending_liquidations.csv
results/v08_lending_liquidation_watcher_summary.csv
```

默认生产阈值：

```text
protocol: Aave V3 Ethereum
pool: 0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2
event: LiquidationCall
min_usd: 1,000,000
window: 24h
```

本地运行：

```powershell
. .\config\local_secrets.ps1
python scripts/watch_lending_liquidations.py --hours 24 --output data/watcher_alerts_lending_liquidations.csv --summary results/v08_lending_liquidation_watcher_summary.csv --sample-if-no-key false
```

说明：

- 该 watcher 只读链上日志，不提交交易，不参与清算。
- 低于阈值的清算只进入 summary 的 skipped 统计，不进 TG 草稿。
- 生产阈值下没有事件时，`status=pass` 且 `alert_rows=0` 是正常结果。
- TG 文案只表达风险释放、市场压力和继续观察，不生成交易建议。

## v0.8 Funding Rate Watcher

Funding-rate anomalies are monitored from Binance USD-M public API. No API key is required.

Watchlist:

```text
data/funding_watchlist.csv
```

Local run:

```powershell
python scripts/watch_binance_funding_rates.py
```

Output:

```text
data/watcher_alerts_binance_funding.csv
results/v08_funding_rate_watcher_summary.csv
```

Default monitored markets:

```text
BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, DOGEUSDT, HYPEUSDT
```

Interpretation rule:

- Positive funding means longs are paying shorts.
- Negative funding means shorts are paying longs.
- This is a derivatives crowding/positioning signal, not a direction signal.
- It must not be phrased as buy/sell/long/short advice.

Current production behavior:

- Alerts are only created when absolute funding rate or funding-rate change exceeds thresholds.
- If all rows are below threshold, the watcher still reports `status=pass` and sends nothing.
