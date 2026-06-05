# Market Radar v1.12-G — Multi-Asset Sync Local Correlation Report

**Generated**: 2026-06-05 04:13:18 UTC+8
**Version**: v1.12-G
**Run ID**: 20260604_202718

---

## 概述

本报告验证 v1.12-G multi-asset market sync 本地相关性适配层可：
1. 稳定读取本地 fixture 快照
2. 计算 synchronize move score（同步异动得分）
3. 计算 direction agreement（方向一致性）
4. 检测 sector / basket 类型
5. 分类 sync type（5 种已知类型 + unknown）
6. 判定 valid / blocked
7. 渲染干净的 public card（无 debug/secret 泄露）

---

## 执行摘要

| 指标 | 值 |
|------|-----|
| 加载快照数 | 8 |
| 处理快照数 | 8 |
| Valid signals | 5 |
| Blocked signals | 3 |
| Public cards | 5 |
| Fallback preview | False |
| Debug leaks | 0 |
| Secret leaks | 0 |
| Sync types found | exchange_token_sync, l2_beta_sync, market_wide_risk_off, market_wide_risk_on, stablecoin_liquidity_stress, unknown |
| Sectors found | L1, L1+L2, exchange_token, stablecoin |

---

## Sync Types Found

- **exchange_token_sync**: 1 snapshot(s)
- **l2_beta_sync**: 1 snapshot(s)
- **market_wide_risk_off**: 1 snapshot(s)
- **market_wide_risk_on**: 2 snapshot(s)
- **stablecoin_liquidity_stress**: 1 snapshot(s)
- **unknown**: 2 snapshot(s)

---

## Valid Signals (5)

### multi_sync_v112g_001_btc_eth_risk_on

| 字段 | 值 |
|------|-----|
| Sync Type | market_wide_risk_on |
| Direction | up |
| Direction Agreement | 1.00 |
| Sync Score | 91.6 |
| Sector | L1 |
| Primary Assets | SOL, BTC, ETH |
| Window | 30 min |
| Avg Price Change | +5.37% |
| Avg Volume Change | +96.0% |
| Avg OI Change | +8.50% |

**Public Card**:
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

🔗 行情查看：CoinGecko / DexScreener（BTC）

💡 触发原因：检测到Layer 1板块3个资产同步上涨，平均涨跌幅+5.4%，同步异动得分92分（强烈），成交量放大96%，OI变化+8.5%。

⚠️ 共振不代表趋势延续，可能为短期情绪驱动，不构成交易建议。
```

### multi_sync_v112g_002_l2_beta_sync

| 字段 | 值 |
|------|-----|
| Sync Type | l2_beta_sync |
| Direction | up |
| Direction Agreement | 1.00 |
| Sync Score | 87.3 |
| Sector | L1+L2 |
| Primary Assets | OP, ARB, MATIC |
| Window | 45 min |
| Avg Price Change | +6.15% |
| Avg Volume Change | +112.2% |
| Avg OI Change | +12.30% |

**Public Card**:
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

🔗 行情查看：CoinGecko / DexScreener（ETH）

💡 触发原因：检测到L1 + L2板块4个资产同步上涨，平均涨跌幅+6.2%，同步异动得分87分（强烈），成交量放大112%，OI变化+12.3%。

⚠️ 共振不代表趋势延续，可能为短期情绪驱动，不构成交易建议。
```

### multi_sync_v112g_003_exchange_token_sync

| 字段 | 值 |
|------|-----|
| Sync Type | exchange_token_sync |
| Direction | up |
| Direction Agreement | 1.00 |
| Sync Score | 88.5 |
| Sector | exchange_token |
| Primary Assets | BNB, OKB, BGB |
| Window | 60 min |
| Avg Price Change | +3.87% |
| Avg Volume Change | +76.0% |
| Avg OI Change | +5.70% |

**Public Card**:
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

💡 触发原因：检测到平台币板块3个资产同步上涨，平均涨跌幅+3.9%，同步异动得分88分（强烈），成交量放大76%，OI变化+5.7%。

⚠️ 共振不代表趋势延续，可能为短期情绪驱动，不构成交易建议。
```

### multi_sync_v112g_004_stablecoin_stress

| 字段 | 值 |
|------|-----|
| Sync Type | stablecoin_liquidity_stress |
| Direction | down |
| Direction Agreement | 1.00 |
| Sync Score | 79.7 |
| Sector | stablecoin |
| Primary Assets | USDT, USDC, DAI |
| Window | 20 min |
| Avg Price Change | -0.97% |
| Avg Volume Change | +283.3% |
| Avg OI Change | +21.67% |

**Public Card**:
```
📉 多资产共振｜稳定币流动性压力 3个资产

一句话：检测到稳定币板块3个资产同步下跌，平均涨跌幅-1.0%，同步异动得分80分（强烈），成交量放大283%，OI变化+21.7%。

● 共振类型：稳定币流动性压力
● 方向：同步下跌
● 主要资产：USDT、USDC、DAI
● 观测窗口：20分钟
● 平均涨跌幅：-0.97%
● 平均成交量变化：+283.3%
● 平均OI变化：+21.67%
● 同步异动得分：80/100
● 总清算金额：$280.00M
● 板块：稳定币

🕐 观测时间：2026-06-04T17:30:00+08:00

🔗 行情查看：CoinGecko / DexScreener（USDT）

💡 触发原因：检测到稳定币板块3个资产同步下跌，平均涨跌幅-1.0%，同步异动得分80分（强烈），成交量放大283%，OI变化+21.7%。

⚠️ 共振不代表趋势延续，可能为短期情绪驱动，不构成交易建议。
```

### multi_sync_v112g_005_market_wide_risk_off

| 字段 | 值 |
|------|-----|
| Sync Type | market_wide_risk_off |
| Direction | down |
| Direction Agreement | 1.00 |
| Sync Score | 94.7 |
| Sector | L1 |
| Primary Assets | SOL, ETH, BTC |
| Window | 30 min |
| Avg Price Change | -7.33% |
| Avg Volume Change | +201.2% |
| Avg OI Change | -14.00% |

**Public Card**:
```
📉 多资产共振｜市场普跌共振 4个资产

一句话：检测到Layer 1板块4个资产同步下跌，平均涨跌幅-7.3%，同步异动得分95分（强烈），成交量放大201%，OI变化-14.0%。

● 共振类型：市场普跌共振
● 方向：同步下跌
● 主要资产：SOL、ETH、BTC
● 观测窗口：30分钟
● 平均涨跌幅：-7.33%
● 平均成交量变化：+201.2%
● 平均OI变化：-14.00%
● 同步异动得分：95/100
● 总清算金额：$558.50M
● 板块：Layer 1

🕐 观测时间：2026-06-04T18:00:00+08:00

🔗 行情查看：CoinGecko / DexScreener（BTC）

💡 触发原因：检测到Layer 1板块4个资产同步下跌，平均涨跌幅-7.3%，同步异动得分95分（强烈），成交量放大201%，OI变化-14.0%。

⚠️ 共振不代表趋势延续，可能为短期情绪驱动，不构成交易建议。
```

---

## Blocked Signals (3)

### multi_sync_v112g_006_blocked_insufficient_assets

- **Block Reason**: insufficient_assets: need at least 2 assets, got 1
- **Sync Type**: unknown
- **Direction**: up
- **Direction Agreement**: 1.00
- **Asset Count**: 1

### multi_sync_v112g_007_blocked_direction_conflict

- **Block Reason**: direction_conflict: direction_agreement=0.50 < 0.66
- **Sync Type**: unknown
- **Direction**: neutral
- **Direction Agreement**: 0.50
- **Asset Count**: 4

### multi_sync_v112g_008_blocked_small_amplitude

- **Block Reason**: small_amplitude: avg_abs_price=1.5% (<3%), avg_volume=25.7% (<80%), avg_oi=1.8% (<15%)
- **Sync Type**: market_wide_risk_on
- **Direction**: up
- **Direction Agreement**: 1.00
- **Asset Count**: 3

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
| token/key/cookie read | false |
| files_deleted | false |
