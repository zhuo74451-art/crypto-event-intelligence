# Market Radar v1.16-G — Price/OI/Volume Anomaly Card Preview

**Generated**: 2026-06-05T12:32:11.793387+08:00
**Card Family**: `price_oi_volume_anomaly`
**API Source**: Binance public REST endpoints (free, no API key)
**Assets**: BTCUSDT, ETHUSDT, SOLUSDT
**Preflight**: PASS
**Admitted**: 2/3

---

## Admission Summary

| Asset | Price Chg | QVol | OI Chg | OI Hist | Admitted | Type |
|-------|-----------|------|--------|---------|----------|------|
| BTC | -2.24% | $1,930,179,409 | N/A | False | False | None |
| ETH | -4.44% | $970,053,734 | N/A | False | True | down_anomaly_confirmed |
| SOL | -5.46% | $273,666,572 | N/A | False | True | down_anomaly_confirmed |

---

## Cards Generated

### BTC

```
[BLOCKED] BTC: admission not passed. price_chg=-2.24%. Threshold: 4.0%+confirm or 5.0% weak.
```

---

### ETH

```
📉 🟠 价格/OI/成交量异常｜ETH 下跌
一句话：检测到ETH 24小时down幅度 4.44%, 合约同步变化 -4.57%, OI历史数据不可用。
● 资产：ETH (ETHUSDT)
● 当前价格：$1,729.21
● 24h涨跌幅：-4.44%
● 合约24h涨跌幅：-4.57%
● 24h最高：$1,809.91
● 24h最低：$1,718.25
● 24h成交量（Quote）：$970,053,734
● 当前OI：2,238,622
● OI变化：N/A（历史数据不可用）
● 异常类型：down_anomaly_confirmed
● 异常等级：确认异常
确认因子：
● volume_confirm: quote_vol=$970,053,734 >= $500,000,000
● spot_futures_convergent: spot_chg=-4.44%, fut_chg=-4.57%
🕐 观测时间：2026-06-05T12:32:09.153786+08:00
💡 说明：价格/OI/成交量异常可能反映市场短期情绪或
资金流动，不代表趋势延续。不构成交易建议。

⚠️ OI历史数据缺失，本信号为弱确认异常。
📊 数据源：Binance 公开行情 API（免费，无需 API Key）
🔐 v116G 安全预检通过 | 真实API | 测试群 one-shot 发送
```

---

### SOL

```
📉 🟠 价格/OI/成交量异常｜SOL 下跌
一句话：检测到SOL 24小时down幅度 5.46%, 合约同步变化 -5.42%, OI历史数据不可用。
● 资产：SOL (SOLUSDT)
● 当前价格：$67.40
● 24h涨跌幅：-5.46%
● 合约24h涨跌幅：-5.42%
● 24h最高：$71.30
● 24h最低：$66.52
● 24h成交量（Quote）：$273,666,572
● 当前OI：10,144,858
● OI变化：N/A（历史数据不可用）
● 异常类型：down_anomaly_confirmed
● 异常等级：确认异常
确认因子：
● spot_futures_convergent: spot_chg=-5.46%, fut_chg=-5.42%
🕐 观测时间：2026-06-05T12:32:09.153786+08:00
💡 说明：价格/OI/成交量异常可能反映市场短期情绪或
资金流动，不代表趋势延续。不构成交易建议。

⚠️ OI历史数据缺失，本信号为弱确认异常。
📊 数据源：Binance 公开行情 API（免费，无需 API Key）
🔐 v116G 安全预检通过 | 真实API | 测试群 one-shot 发送
```

---


## Signal Metrics

| Asset | Anomaly Type | Confirm Factors | Admitted |
|-------|-------------|-----------------|----------|
| BTC | None | 2 | False |
| ETH | down_anomaly_confirmed | 2 | True |
| SOL | down_anomaly_confirmed | 1 | True |

---

## v116G Safety Flags

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
