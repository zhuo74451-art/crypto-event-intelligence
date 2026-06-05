# Market Radar v1.16-I — Liquidation Pressure Proxy Card Preview

**Generated**: 2026-06-05T13:07:20.806958+08:00
**Card Family**: `liquidation_pressure`
**API Source**: Binance public REST endpoints (free, no API key)
**Assets**: BTCUSDT, ETHUSDT, SOLUSDT
**Preflight**: PASS
**Admitted**: 0/3

⚠️ **重要声明**: 本报告所有信号均为清算压力代理信号（liquidation pressure proxy），
基于价格变动、OI变化、资金费率、多空比、taker买卖比等公开衍生指标的复合估算。
Binance REST API 不提供直接清算流数据，本信号不代表真实逐笔清算数据。

---

## Admission Summary

| Asset | Price Chg | QVol | OI Chg | Funding | L/S Ratio | Taker B/S | Score | Admitted | Type |
|-------|-----------|------|--------|---------|-----------|-----------|-------|----------|------|
| BTC | -0.59% | $1,930,283,599 | N/A | +0.0013% | 2.1417 | 0.9064 | 2.59 | False | None |
| ETH | -3.03% | $964,513,581 | N/A | +0.0047% | 2.7793 | 0.8790 | 5.03 | False | None |
| SOL | -3.38% | $275,283,848 | N/A | -0.0097% | 3.7687 | 1.4795 | 6.38 | False | None |

---

## Cards Generated

### BTC

```
[BLOCKED] BTC: liquidation pressure proxy admission not passed. price_chg=-0.59%, proxy_score=2.59/10, confirm_factors=2. Threshold: 4.0%+2 factors or 5.0%+1 factor.
```

---

### ETH

```
[BLOCKED] ETH: liquidation pressure proxy admission not passed. price_chg=-3.03%, proxy_score=5.03/10, confirm_factors=2. Threshold: 4.0%+2 factors or 5.0%+1 factor.
```

---

### SOL

```
[BLOCKED] SOL: liquidation pressure proxy admission not passed. price_chg=-3.38%, proxy_score=6.38/10, confirm_factors=2. Threshold: 4.0%+2 factors or 5.0%+1 factor.
```

---


## Confirmation Factors Detail

| Asset | Price Chg | Confirm Count | Confirm Factors | Admitted |
|-------|-----------|---------------|-----------------|----------|
| BTC | -0.59% | 2 | ls_ratio_bullish: L/S=2.1417 > 1.2 (long dominant — potentia...; volume_confirm: quote_vol=$1,930,283,599 >= $500,000,000 | False |
| ETH | -3.03% | 2 | ls_ratio_bullish: L/S=2.7793 > 1.2 (long dominant — potentia...; volume_confirm: quote_vol=$964,513,581 >= $500,000,000 | False |
| SOL | -3.38% | 2 | ls_ratio_bullish: L/S=3.7687 > 1.2 (long dominant — potentia...; taker_buy_pressure: taker B/S=1.4795 > 1.2 (aggressive buyin... | False |

## Data Availability Matrix

| Asset | Funding | L/S Ratio | Taker B/S | OI History |
|-------|---------|-----------|-----------|------------|
| BTC | True | True | True | False |
| ETH | True | True | True | False |
| SOL | True | True | True | False |

---

## v116I Safety Flags

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
