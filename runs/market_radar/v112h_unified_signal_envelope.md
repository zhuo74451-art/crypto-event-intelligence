# Market Radar v1.12-H — Unified Signal Envelope Report

**Generated**: 2026-06-05 05:43:10 UTC+8
**Version**: v1.12-H
**Run ID**: 20260604_202718
**Schema Version**: v1.12-H

---

## 概述

本报告证明 5 类固定卡片类型均已产出统一的 Signal Envelope 结构。
每条 envelope 都包含稳定的 `dedupe_key`、`cooldown_key` 和 `payload_hash`，
为后续去重、冷却、回放、审计和真实数据源接入做好准备。

本任务未连接外部 API、未发送 TG、未启动 daemon/loop/cron。

## 全局统计

| 指标 | 值 |
|------|-----|
| 总 envelope 数量 | 13 |
| 覆盖 card type 数量 | 5/5 |
| 全部验证通过 | True |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| all_clean | True |
| full_wallet_leak | False |
| dedupe_key_stable | True |
| cooldown_key_stable | True |
| payload_hash_stable | True |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |
| live_ready | False |

---

## Cardinality Check

| Card Type | Expected | Actual | Status |
|-----------|----------|--------|--------|
| `multi_asset_market_sync` | >= 3 | 3 | ✅ |
| `whale_position_alert` | >= 3 | 3 | ✅ |
| `price_oi_volume_anomaly` | >= 1 | 1 | ✅ |
| `liquidation_pressure` | >= 3 | 3 | ✅ |
| `news_event_market_impact` | >= 3 | 3 | ✅ |

**Total**: 13 envelopes (minimum: 13)

---

## Envelope 列表

### 1. price_oi_volume_anomaly — `sig-pova-cf3a0c25-202606042000`

| 字段 | 值 |
|------|-----|
| schema_version | 1.0.0 |
| signal_id | sig-pova-cf3a0c25-202606042000 |
| card_type | price_oi_volume_anomaly |
| adapter_version | v1.12-A |
| source_kind | fixture |
| observed_at | 2026-06-04T20:00:00+08:00 |
| primary_assets | BTC |
| direction | bullish |
| severity_score | 45.0 |
| confidence_score | 0.8 |
| readiness | fixture |
| live_ready | False |
| dedupe_key | 8b7c4239a2b7ee3d... |
| cooldown_key | df78e9c3875ea5c6... |
| payload_hash | 28225b5c363df8f6... |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |

**Public Card Preview**:

```
📉 行情异动｜ARB 急跌

一句话：ARB 多因子同步异动（价格跌幅 + OI + 成交量 + 资金费率偏空），短时升级信号。

● 币种：ARB
● 涨跌幅：-8.50%
● OI：$5.20M
● 成交量：$6.10M
● Funding：-1.80%（年化 -1971.0%）
● 观察窗口：1-4 小时

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=ARB) / [DexScreener](https://dexscreener.com/search?q=ARB)

💡 触发原因：ARB 多因子同步异动（价格跌幅 
```

### 2. whale_position_alert — `sig-wpa-f71d2b1d-202606041945`

| 字段 | 值 |
|------|-----|
| schema_version | 1.0.0 |
| signal_id | sig-wpa-f71d2b1d-202606041945 |
| card_type | whale_position_alert |
| adapter_version | v1.12-F |
| source_kind | fixture |
| observed_at | 2026-06-04T19:45:00+08:00 |
| primary_assets | BTC |
| direction | bullish |
| severity_score | 50.0 |
| confidence_score | 0.85 |
| readiness | fixture |
| live_ready | False |
| dedupe_key | 0faa23cba4ab3fbb... |
| cooldown_key | df85e357101e53be... |
| payload_hash | 9e6a9fbb99abfd5b... |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |

**Public Card Preview**:

```
🟢 巨鲸仓位警报｜BTC 多头 新开仓位

🏷️ 地址标签：Smart Money Alpha
📌 钱包地址：`0x7a9f...6b8c`

● 资产：BTC
● 方向：多头
● 持仓规模：$5.20M
● 杠杆倍数：5.0x
● 仓位变化：+$5.20M
● 开仓均价：$87,200.50
● 当前价格：$88,650.00
● 未实现盈亏：+$86.80K（+1.7%）
● 清算价格：$69,800.00（距清算 21.3%）

📢 警报类型：新开仓位
💡 触发原因：仓位增加 $5.20M；大额持仓 $5.20M
🕐 观测时间：2026-06-04T19:45:00+08:00

🔗 行
```

### 3. whale_position_alert — `sig-wpa-1ae7a01d-202606042010`

| 字段 | 值 |
|------|-----|
| schema_version | 1.0.0 |
| signal_id | sig-wpa-1ae7a01d-202606042010 |
| card_type | whale_position_alert |
| adapter_version | v1.12-F |
| source_kind | fixture |
| observed_at | 2026-06-04T20:10:00+08:00 |
| primary_assets | ETH |
| direction | bearish |
| severity_score | 60.0 |
| confidence_score | 0.65 |
| readiness | fixture |
| live_ready | False |
| dedupe_key | c74e9e689d3257ec... |
| cooldown_key | 5504df45b9358135... |
| payload_hash | 1748799a89b7bdca... |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |

**Public Card Preview**:

```
🟠 巨鲸仓位警报｜ETH 空头 加仓

🏷️ 地址标签：Whale #HyperL-42
📌 钱包地址：`0x3b6e...4f6a`

● 资产：ETH
● 方向：空头
● 持仓规模：$3.80M
● 杠杆倍数：15.0x
● 仓位变化：+$2.00M
● 开仓均价：$4,120.75
● 当前价格：$4,080.25
● 未实现盈亏：+$37.40K（+1.0%）
● 清算价格：$4,395.00（距清算 7.7%）

📢 警报类型：加仓
💡 触发原因：仓位增加 $2.00M；15x 高杠杆；大额持仓 $3.80M
📅 上次观测：2026-06-03T22:30:00+08:00
🕐 观测
```

### 4. whale_position_alert — `sig-wpa-46d9d399-202606042022`

| 字段 | 值 |
|------|-----|
| schema_version | 1.0.0 |
| signal_id | sig-wpa-46d9d399-202606042022 |
| card_type | whale_position_alert |
| adapter_version | v1.12-F |
| source_kind | fixture |
| observed_at | 2026-06-04T20:22:00+08:00 |
| primary_assets | SOL |
| direction | bullish |
| severity_score | 70.0 |
| confidence_score | 0.65 |
| readiness | fixture |
| live_ready | False |
| dedupe_key | 90ea67f8d8ec5fb6... |
| cooldown_key | 0491c6deff37807c... |
| payload_hash | a5bddfbc76b6d0de... |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |

**Public Card Preview**:

```
🟠 巨鲸仓位警报｜SOL 多头 高杠杆风险

🏷️ 地址标签：Whale #HyperL-42
📌 钱包地址：`0x3b6e...4f6a`

● 资产：SOL
● 方向：多头
● 持仓规模：$1.20M
● 杠杆倍数：20.0x
● 开仓均价：$215.40
● 当前价格：$208.75
● 未实现盈亏：-$37.20K（-3.1%）
● 清算价格：$196.80（距清算 5.7%）

📢 警报类型：高杠杆风险
💡 触发原因：20x 高杠杆；大额持仓 $1.20M
📅 上次观测：2026-06-03T18:15:00+08:00
🕐 观测时间：2026-06-04T20:22:00+08:0
```

### 5. liquidation_pressure — `sig-lipr-a94980e2-202606041200`

| 字段 | 值 |
|------|-----|
| schema_version | 1.0.0 |
| signal_id | sig-lipr-a94980e2-202606041200 |
| card_type | liquidation_pressure |
| adapter_version | v1.12-C |
| source_kind | fixture |
| observed_at | 2026-06-04T12:00:00+08:00 |
| primary_assets | BTC |
| direction | bearish |
| severity_score | 60.0 |
| confidence_score | 0.7 |
| readiness | fixture |
| live_ready | False |
| dedupe_key | 6ffe28e7622ad1a4... |
| cooldown_key | d62e85c889be446e... |
| payload_hash | 5729e72b9480b10b... |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |

**Public Card Preview**:

```
⚠️ 清算压力｜BTC

一句话：BTC 下方多头清算压力升高，近1h 多头清算 $18.50M，下方清算密集区 $0.00，若价格继续回落可能放大短线波动。

● 当前价格：$63,500.00
● 近 1h 多头清算：$18.50M
● 近 1h 空头清算：$3.20M
● 近 24h 多头清算：$125.00M
● 近 24h 空头清算：$28.00M
● 未平仓合约：$18.50B
● 24h 成交量：$42.00B
● 观察窗口：1-4 小时

💡 触发原因：BTC 下方多头清算压力升高，近1h 多头清算 $18.50M，下方清算密集区 $0.00，若价格继续回落可能放大短线波动。

```

### 6. liquidation_pressure — `sig-lipr-dd740422-202606041200`

| 字段 | 值 |
|------|-----|
| schema_version | 1.0.0 |
| signal_id | sig-lipr-dd740422-202606041200 |
| card_type | liquidation_pressure |
| adapter_version | v1.12-C |
| source_kind | fixture |
| observed_at | 2026-06-04T12:00:00+08:00 |
| primary_assets | ETH |
| direction | bullish |
| severity_score | 60.0 |
| confidence_score | 0.7 |
| readiness | fixture |
| live_ready | False |
| dedupe_key | 3d1fc05ec59ec6cf... |
| cooldown_key | 6a00109f37584ae7... |
| payload_hash | 716ebac26f9d200e... |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |

**Public Card Preview**:

```
⚠️ 清算压力｜ETH

一句话：ETH 上方空头清算压力升高，近1h 空头清算 $22.00M，上方清算密集区 $0.00，若价格上行可能引发空头踩踏。

● 当前价格：$3,050.00
● 近 1h 多头清算：$4.20M
● 近 1h 空头清算：$22.00M
● 近 24h 多头清算：$38.00M
● 近 24h 空头清算：$145.00M
● 未平仓合约：$8.20B
● 24h 成交量：$18.50B
● 观察窗口：1-4 小时

💡 触发原因：ETH 上方空头清算压力升高，近1h 空头清算 $22.00M，上方清算密集区 $0.00，若价格上行可能引发空头踩踏。

⚠️ 仅供
```

### 7. liquidation_pressure — `sig-lipr-03ec60ab-202606041200`

| 字段 | 值 |
|------|-----|
| schema_version | 1.0.0 |
| signal_id | sig-lipr-03ec60ab-202606041200 |
| card_type | liquidation_pressure |
| adapter_version | v1.12-C |
| source_kind | fixture |
| observed_at | 2026-06-04T12:00:00+08:00 |
| primary_assets | SOL |
| direction | mixed |
| severity_score | 75.0 |
| confidence_score | 0.7 |
| readiness | fixture |
| live_ready | False |
| dedupe_key | 6b5a04c7a286e9fd... |
| cooldown_key | 3d8001551dbeb839... |
| payload_hash | 2c47e66e78f5c6cd... |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |

**Public Card Preview**:

```
⚠️ 清算压力｜SOL

一句话：SOL 上下方均存在清算密集区，下方多头清算 $0.00，上方空头清算 $0.00，双向波动风险升高。

● 当前价格：$142.50
● 近 1h 多头清算：$28.00M
● 近 1h 空头清算：$31.00M
● 近 24h 多头清算：$185.00M
● 近 24h 空头清算：$210.00M
● 未平仓合约：$2.10B
● 24h 成交量：$5.80B
● 观察窗口：2-6 小时

💡 触发原因：SOL 上下方均存在清算密集区，下方多头清算 $0.00，上方空头清算 $0.00，双向波动风险升高。

⚠️ 仅供观察，不构成交易建议。
```

### 8. multi_asset_market_sync — `sig-mams-018a768f-202606041430`

| 字段 | 值 |
|------|-----|
| schema_version | 1.0.0 |
| signal_id | sig-mams-018a768f-202606041430 |
| card_type | multi_asset_market_sync |
| adapter_version | v1.12-G |
| source_kind | fixture |
| observed_at | 2026-06-04T14:30:00+08:00 |
| primary_assets | SOL, BTC, ETH |
| direction | bullish |
| severity_score | 80.0 |
| confidence_score | 0.9 |
| readiness | fixture |
| live_ready | False |
| dedupe_key | 6591c1c9cdb0e620... |
| cooldown_key | 434d3fa3ea019205... |
| payload_hash | 4d5c408bb3411b04... |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |

**Public Card Preview**:

```
📈 多资产共振｜市场普涨共振 3个资产

一句话：检测到Layer 1板块3个资产同步上涨，平均涨跌幅+5.4%，同步异动得分92分（强烈），成交量放大96%，OI变化+8.5%。

● 共振类型：市场普涨共振
● 方向：同步上涨
● 主要资产：SOL、BTC、ETH
● 观测窗口：30分钟
● 平均涨跌幅：+5.37%
● 平均成交量变化：+96.0%
● 平均OI变化：+8.50%
● 同步异动得分：92/100
● 总清算金额：$165.00M
● 板块：Layer 1

🕐 观测时间：2026-06-04T14:30:00+08:00

🔗 行情查看：CoinGecko / DexSc
```

### 9. multi_asset_market_sync — `sig-mams-a4e05c21-202606041515`

| 字段 | 值 |
|------|-----|
| schema_version | 1.0.0 |
| signal_id | sig-mams-a4e05c21-202606041515 |
| card_type | multi_asset_market_sync |
| adapter_version | v1.12-G |
| source_kind | fixture |
| observed_at | 2026-06-04T15:15:00+08:00 |
| primary_assets | OP, ARB, MATIC |
| direction | bullish |
| severity_score | 80.0 |
| confidence_score | 0.9 |
| readiness | fixture |
| live_ready | False |
| dedupe_key | 680e6ca162cfc3b2... |
| cooldown_key | 830fc95c9cb10a9d... |
| payload_hash | dc0a2a5edc0bc603... |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |

**Public Card Preview**:

```
📈 多资产共振｜L2 高Beta同步 4个资产

一句话：检测到L1 + L2板块4个资产同步上涨，平均涨跌幅+6.2%，同步异动得分87分（强烈），成交量放大112%，OI变化+12.3%。

● 共振类型：L2 高Beta同步
● 方向：同步上涨
● 主要资产：OP、ARB、MATIC
● 观测窗口：45分钟
● 平均涨跌幅：+6.15%
● 平均成交量变化：+112.2%
● 平均OI变化：+12.30%
● 同步异动得分：87/100
● 总清算金额：$45.50M
● 板块：L1 + L2

🕐 观测时间：2026-06-04T15:15:00+08:00

🔗 行情查看：CoinG
```

### 10. multi_asset_market_sync — `sig-mams-b2ab4cdd-202606041600`

| 字段 | 值 |
|------|-----|
| schema_version | 1.0.0 |
| signal_id | sig-mams-b2ab4cdd-202606041600 |
| card_type | multi_asset_market_sync |
| adapter_version | v1.12-G |
| source_kind | fixture |
| observed_at | 2026-06-04T16:00:00+08:00 |
| primary_assets | BNB, OKB, BGB |
| direction | bullish |
| severity_score | 80.0 |
| confidence_score | 0.9 |
| readiness | fixture |
| live_ready | False |
| dedupe_key | 9423a42cf131b412... |
| cooldown_key | 0ee7143b11a0ce80... |
| payload_hash | b59dac773bc274a3... |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |

**Public Card Preview**:

```
📈 多资产共振｜平台币联动 3个资产

一句话：检测到平台币板块3个资产同步上涨，平均涨跌幅+3.9%，同步异动得分88分（强烈），成交量放大76%，OI变化+5.7%。

● 共振类型：平台币联动
● 方向：同步上涨
● 主要资产：BNB、OKB、BGB
● 观测窗口：60分钟
● 平均涨跌幅：+3.87%
● 平均成交量变化：+76.0%
● 平均OI变化：+5.70%
● 同步异动得分：88/100
● 总清算金额：$17.00M
● 板块：平台币

🕐 观测时间：2026-06-04T16:00:00+08:00

🔗 行情查看：CoinGecko / DexScreener（BNB）
```

### 11. news_event_market_impact — `sig-nemi-d3dbfd91-202606041430`

| 字段 | 值 |
|------|-----|
| schema_version | 1.0.0 |
| signal_id | sig-nemi-d3dbfd91-202606041430 |
| card_type | news_event_market_impact |
| adapter_version | v1.12-D |
| source_kind | fixture |
| observed_at | 2026-06-04T14:30:00+08:00 |
| primary_assets | BTC |
| direction | bullish |
| severity_score | 85.0 |
| confidence_score | 0.6 |
| readiness | fixture |
| live_ready | False |
| dedupe_key | 96e12fd4bdc66355... |
| cooldown_key | 2e7268b07cb27896... |
| payload_hash | c35c2b17f435ce01... |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |

**Public Card Preview**:

```
📊 新闻事件｜BlackRock Bitcoin ETF Sees $420M Inflows, Largest Single-Day Since March

🟢 市场影响方向：偏多

ETF类型事件，影响 BTC。

● 事件分类：ETF资金流向
● 受影响资产：BTC
● 来源：CoinDesk
● 发布时间：2026-06-04T14:30:00Z
● 交易相关性：高
● 是否已被定价：部分已定价

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=BTC) / [DexScreener](https://dexscre
```

### 12. news_event_market_impact — `sig-nemi-f8590f16-202606041015`

| 字段 | 值 |
|------|-----|
| schema_version | 1.0.0 |
| signal_id | sig-nemi-f8590f16-202606041015 |
| card_type | news_event_market_impact |
| adapter_version | v1.12-D |
| source_kind | fixture |
| observed_at | 2026-06-04T10:15:00+08:00 |
| primary_assets | DEFI, ETH |
| direction | bearish |
| severity_score | 60.0 |
| confidence_score | 0.6 |
| readiness | fixture |
| live_ready | False |
| dedupe_key | a28a7917c77dff31... |
| cooldown_key | b0ec045e23c8b535... |
| payload_hash | 4fc01222682c6c6e... |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |

**Public Card Preview**:

```
🏛️ 新闻事件｜EU Parliament Passes Stricter DeFi KYC Rules, Effective January 2027

🔴 市场影响方向：偏空

政策类型事件，影响 DEFI / ETH。

● 事件分类：监管政策
● 受影响资产：DEFI, ETH
● 来源：The Block
● 发布时间：2026-06-04T10:15:00Z
● 交易相关性：高
● 是否已被定价：未定价

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=DEFI) / [DexScreener](https://d
```

### 13. news_event_market_impact — `sig-nemi-20d248d1-202606040845`

| 字段 | 值 |
|------|-----|
| schema_version | 1.0.0 |
| signal_id | sig-nemi-20d248d1-202606040845 |
| card_type | news_event_market_impact |
| adapter_version | v1.12-D |
| source_kind | fixture |
| observed_at | 2026-06-04T08:45:00+08:00 |
| primary_assets | ARB, ETH, USDC |
| direction | bearish |
| severity_score | 90.0 |
| confidence_score | 0.6 |
| readiness | fixture |
| live_ready | False |
| dedupe_key | df4efb7ae3be6b11... |
| cooldown_key | d13da0968d1715ec... |
| payload_hash | 028369932730a5dd... |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |

**Public Card Preview**:

```
🔒 新闻事件｜Arbitrum Bridge Exploit Drains $47M in ETH and USDC — Team Confirms Investigation

🔴 市场影响方向：偏空

安全类型事件，影响 ARB / ETH / USDC。

● 事件分类：安全事件
● 受影响资产：ARB, ETH, USDC
● 来源：PeckShield
● 发布时间：2026-06-04T08:45:00Z
● 交易相关性：高
● 是否已被定价：未定价

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=ARB) / 
```

---

## Readiness Matrix

| # | Card Type | Readiness |
|---|-----------|-----------|
| 1 | price_oi_volume_anomaly | ✅ Ready (1) |
| 2 | whale_position_alert | ⚠️ Partial (1) |
| 3 | liquidation_pressure | ⚠️ Partial (2) |
| 4 | multi_asset_market_sync | ⚠️ Partial (3) |
| 5 | news_event_market_impact | ⚠️ Partial (4) |

**Final**: Ready=1, Partial=4, Missing=0

---

## 执行约束确认

| 约束 | 状态 |
|------|------|
| real_tg_sent | false |
| external_api_called | false |
| external_ai_called | false |
| daemon_started | false |
| live_ready | false |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| files_deleted | false |
| wallet_leak | false |
