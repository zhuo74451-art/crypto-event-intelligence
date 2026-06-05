# Market Radar v1.12-F — Whale Position Local Enrichment Report

**Generated**: 2026-06-05 04:13:18 UTC+8
**Version**: v1.12-F
**Mode**: whale_position_local_enrichment
**Run ID**: 20260604_202718

---

## 概述

本报告证明 `whale_position_alert` 已从 fallback preview 推进到真实 local public preview。
通过 v112f 本地适配层，实现了地址标签富集、历史仓位序列追踪、仓位变化计算、
警报类型分类、valid/blocked 判定和公共卡片渲染。

所有数据来自本地 fixture，未调用外部 API、未发送 TG、未启动 daemon。

## 核心指标

| 指标 | 数值 |
|------|------|
| 地址标签数量 | 6 |
| 仓位样本数量 | 8 |
| 有效信号数 | 6 |
| 阻止信号数 | 2 |
| 公共卡片数 | 6 |
| Debug 泄露数 | 0 |
| Secret 泄露数 | 0 |
| Fallback Preview | False |
| Live Ready | False |

---

## 地址标签覆盖

| 钱包短码 | 标签 | 实体类型 | 置信度 |
|----------|------|----------|--------|
| `0x7a9f...6b8c` | Smart Money Alpha | smart_money | high |
| `0x3b6e...4f6a` | Whale #HyperL-42 | high_leverage_trader | medium |
| `0x3b6e...4f6a` | Whale #HyperL-42 | high_leverage_trader | medium |
| `0x1f4a...4f6a` | Unknown Mega Whale #3371 | unknown_whale | low |
| `0x9e2b...6f8a` | Galaxy Digital OTC (Suspected) | fund_wallet | medium |
| `0x5c8d...6a8b` | Binance Hot Wallet #17 (Relate | exchange_related | high |
| `0x2d4e...f0a2` | Wintermute MM (Confirmed) | market_maker | high |

---

## 有效信号 (6)

| # | Event ID | Asset | Side | Size | Leverage | Alert Type | Delta |
|---|----------|-------|------|------|----------|------------|-------|
| 1 | whale_v112f_001_valid_position_open | BTC | 多 | $5.20M | 5x | 新开 | +$5.20M |
| 2 | whale_v112f_002_valid_position_incr | ETH | 空 | $3.80M | 15x | 加仓 | +$2.00M |
| 3 | whale_v112f_003_valid_high_leverage | SOL | 多 | $1.20M | 20x | 高杠杆风险 | $0.00 |
| 4 | whale_v112f_004_valid_large_unreali | ARB | 多 | $850.00K | 8x | 大额浮亏 | $0.00 |
| 5 | whale_v112f_005_valid_position_redu | BTC | 多 | $3.20M | 3x | 减仓 | -$4.80M |
| 6 | whale_v112f_008_control_no_position | ETH | 空 | $1.50M | 4x | 减仓 | $0.00 |

---

## 阻止信号 (2)

| # | Event ID | Block Reason |
|---|----------|-------------|
| 1 | whale_v112f_006_blocked_missing_wallet | 缺少钱包地址 |
| 2 | whale_v112f_007_blocked_small_position | 仓位金额太小 |

---

## 公共卡片预览

### 卡片 1

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

🔗 行情查看：CoinGecko / DexScreener

⚠️ 仅供观察，不构成交易建议。巨鲸行为不保证方向正确性。
```

### 卡片 2

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
🕐 观测时间：2026-06-04T20:10:00+08:00

🔗 行情查看：CoinGecko / DexScreener

⚠️ 仅供观察，不构成交易建议。巨鲸行为不保证方向正确性。
```

### 卡片 3

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
🕐 观测时间：2026-06-04T20:22:00+08:00

🔗 行情查看：CoinGecko / DexScreener

⚠️ 仅供观察，不构成交易建议。巨鲸行为不保证方向正确性。
```

### 卡片 4

```
🔴 巨鲸仓位警报｜ARB 多头 大额浮亏

🏷️ 地址标签：Unknown Mega Whale #3371
📌 钱包地址：`0x1f4a...4f6a`

● 资产：ARB
● 方向：多头
● 持仓规模：$850.00K
● 杠杆倍数：8.0x
● 开仓均价：$1.85
● 当前价格：$1.42
● 未实现盈亏：-$198.00K（-23.3%）
● 清算价格：$1.25（距清算 12.0%）

📢 警报类型：大额浮亏
💡 触发原因：浮亏 $198.00K；大额持仓 $850.00K
📅 上次观测：2026-06-01T14:00:00+08:00
🕐 观测时间：2026-06-04T20:30:00+08:00

🔗 行情查看：CoinGecko / DexScreener

⚠️ 仅供观察，不构成交易建议。巨鲸行为不保证方向正确性。
```

### 卡片 5

```
🔵 巨鲸仓位警报｜BTC 多头 减仓

🏷️ 地址标签：Galaxy Digital OTC (Suspected)
📌 钱包地址：`0x9e2b...6f8a`

● 资产：BTC
● 方向：多头
● 持仓规模：$3.20M
● 杠杆倍数：3.0x
● 仓位变化：-$4.80M
● 开仓均价：$85,200.00
● 当前价格：$88,650.00
● 未实现盈亏：+$129.60K（+4.0%）
● 清算价格：$56,800.00（距清算 35.9%）

📢 警报类型：减仓
💡 触发原因：仓位减少 $4.80M；大额持仓 $3.20M
📅 上次观测：2026-06-02T16:45:00+08:00
🕐 观测时间：2026-06-04T20:35:00+08:00

🔗 行情查看：CoinGecko / DexScreener

⚠️ 仅供观察，不构成交易建议。巨鲸行为不保证方向正确性。
```

### 卡片 6

```
🔵 巨鲸仓位警报｜ETH 空头 减仓

🏷️ 地址标签：Wintermute MM (Confirmed)
📌 钱包地址：`0x2d4e...f0a2`

● 资产：ETH
● 方向：空头
● 持仓规模：$1.50M
● 杠杆倍数：4.0x
● 开仓均价：$4,150.00
● 当前价格：$4,080.25
● 未实现盈亏：+$25.20K（+1.7%）
● 清算价格：$5,187.50（距清算 27.1%）

📢 警报类型：减仓
💡 触发原因：大额持仓 $1.50M
📅 上次观测：2026-06-04T12:00:00+08:00
🕐 观测时间：2026-06-04T20:45:00+08:00

🔗 行情查看：CoinGecko / DexScreener

⚠️ 仅供观察，不构成交易建议。巨鲸行为不保证方向正确性。
```

---

## 执行约束确认

| 约束 | 状态 |
|------|------|
| fallback_preview | False |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |
| live_ready | False |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| full_wallet_in_public | False |
| token/key/cookie read | false |
| files_deleted | false |
