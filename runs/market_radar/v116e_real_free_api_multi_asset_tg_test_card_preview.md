# Market Radar v1.16-E — Multi-Asset Card Preview

**Generated**: 2026-06-05T11:59:27.048816+08:00
**Card Family**: `multi_asset_market_sync`
**API Source**: Binance public REST endpoints (free, no API key)
**Assets**: BTC, ETH, SOL
**Preflight**: PASS

---

## Card Preview

```
📉 多资产共振｜市场普跌共振 3个资产

一句话：检测到3个主要资产同步下跌，平均涨跌幅-4.4%，同步异动得分60分（明显），成交量变化-2%，OI变化+0.0%。

● 共振类型：市场普跌共振
● 方向：同步下跌
● 主要资产：SOL、ETH、BTC
● 观测窗口：30分钟快照
● 平均涨跌幅：-4.37%
● 平均成交量变化：-2.2%
● 平均OI变化：+0.00%
● 同步异动得分：60/100
● 方向一致性：100%

🕐 观测时间：2026-06-05T11:59:25.707856+08:00

💡 触发原因：检测到3个主要资产同步下跌，平均涨跌幅-4.4%，同步异动得分60分（明显），成交量变化-2%，OI变化+0.0%。

⚠️ 共振不代表趋势延续，可能为短期情绪驱动，不构成交易建议。

📊 数据源：Binance 公开行情 API（免费，无需 API Key）

🔐 v116E 安全预检通过 | 真实API | 测试群 one-shot 发送
```

---

## Signal Metrics

| Metric | Value |
|--------|-------|
| sync_type | `market_wide_risk_off` |
| direction | `down` |
| sync_score | 59.8/100 |
| direction_agreement | 100.0% |
| avg_price_change | -4.37% |
| avg_volume_change | -2.2% |
| avg_oi_change | +0.00% |
| asset_count | 3 |
| valid | True |
| api_key_required | False |

---

## v116E Safety Flags

| Flag | Value |
|------|-------|
| secret_preflight_run | True |
| telegram_bot_token_present | True |
| telegram_chat_id_present | True |
| secret_preflight_passed | True |
| real_external_api_called | True |
| fixture_only | False |
| production_send_ready | False |
| ai_model_called | False |
| files_deleted | False |
| one_shot | True |
