# Crypto Event Intelligence v14 First-Hand Source Review

你继续以外部产品负责人 + 量化研究负责人视角审查。请直接批评，不要迎合，完整中文。

## 项目目标

我们做的是加密事件情报系统：把历史快讯、链上监控、资金流、巨鲸仓位、安全事件、交易所公告等变成结构化事件，做回测和质量闸门，只把高质量、可解释、可验证、可复盘的市场情报发到 Telegram。

不是交易机器人，不自动下单，不给买卖建议。

## 你上一轮要求

你指出：

- 不要为了“有内容”放低标准。
- 281 条快讯里 0 条可发是可以接受的。
- 必须定义最小可发布标准。
- 安全事件不能继续从新闻里硬抠，必须接外部安全源。
- ETF/Fund flow 应该走日频晚报，而不是盘中推送。
- 一手 watcher 要区分状态变化和静态事实，静态事实不能重复盘中发。

## 本轮已做

### 1. 最小可发布标准

新增：
- `config/publishable_criteria.yaml`
- `scripts/define_publishable_event_criteria.py`

标准必须同时满足：
- 链上可验证或官方一手来源
- 有明确事件时间锚点
- 有可观测影响
- 未被 price-in

结果：
- 281 条历史新闻样本：
  - criteria_passed_rows: 0
  - criteria_blocked_rows: 281

### 2. ETF 日频晚报

新增：
- `scripts/build_etf_daily_digest.py`

数据源：
- Farside Investors BTC ETF public flow table

结果：
- rows: 612
- latest_date: 27 May 2026
- latest_total_net_flow_usd: -733,400,000
- publishable_daily_digest: true

当前卡片：

```text
📊 BTC ETF 日频资金流
数据源：Farside Investors｜等级：公开一手表格
数据日期：27 May 2026（美股收盘后确认）
总净流：-733.4M 美元
状态：已确认日频数据

• IBIT: -527.8M 美元
• GBTC: -104.8M 美元
• FBTC: -60.3M 美元
• BITB: -17.5M 美元
• ARKB: -17.4M 美元

近 7 日均值：-239.2M 美元
近 30 日均值：-33.7M 美元
发布判断：进入晚报候选
验证链接：https://farside.co.uk/bitcoin-etf-flow-all-data/
```

### 3. 外部安全源接入尝试

新增：
- `scripts/ingest_security_alerts.py`

尝试：
- Etherscan Metadata `phish-hack` address tags

结果：
- status: warning
- error: Invalid access level
- normalized_rows: 0

判断：
- 当前 Etherscan key 无法使用该 Metadata export，需要换其他安全源。

### 4. 一手 watcher 路由

新增：
- `scripts/build_first_hand_publish_candidates.py`

输入：
- `data/watcher_alerts_raw.csv`

结果：
- input_rows: 9
- intraday_candidate_rows: 0
- digest_candidate_rows: 1
- daily_digest_candidate_rows: 1
- archived_rows: 7

规则：
- Hyperliquid 静态仓位 snapshot：默认 archive，除非有真实仓位状态变化。
- token unlock：大额且占比高，只进日频摘要，不进盘中。
- CEX listing：进入摘要候选。

## 当前问题

1. Etherscan 标签源权限不可用，下一步安全源应该优先接什么？
2. PeckShield / SlowMist / CertiK / Beosin / ZachXBT / Telegram 安全频道，这些源哪个最适合作为 MVP？
3. 如果没有官方 API，是否应该支持“TG/CSV 导出安全源 → 本地结构化解析”的方式？
4. ETF 日频晚报这张卡还缺什么？是否应补 BTC 当日/次日价格表现、历史分位数、连续流出天数？
5. 一手 watcher 当前 9 条里 7 条归档是否合理？Hyperliquid 静态大仓位是否应该只做早晚报背景，而不是完全归档？
6. CEX listing 摘要候选是否需要马上接 Binance/OKX/Bybit 官方公告源，而不是只靠本地 watcher？
7. 接下来 1 天内最应该写哪 5 个脚本/改哪 5 个脚本？请精确到脚本级别。
8. 哪些现有模块应该暂停，避免继续消耗时间？

