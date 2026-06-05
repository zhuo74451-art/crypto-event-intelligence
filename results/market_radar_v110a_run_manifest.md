# Market Radar v1.10-A R2｜Run Manifest

生成时间：2026-06-04 16:42:17 UTC+8

---

## 当前状态

| 指标 | 值 |
|------|-----|
| 版本 | v1.10-A R2 |
| 抓取信号总数（原始） | 15 |
| 真实外网数据源成功 | 2 |
| 真实外网数据源失败 | 1 |
| 真实外网数据数量 | 12 |
| Fixture / Fallback 数量 | 6 |
| 字段降级数量 | 0 |
| Combo 合并组数 | 3 |
| 被合并信号数量 | 8 |
| 最终卡片数量 | 10 |
| MarkdownV2 兜底次数 | 0 |
| TG 发送 | 否 |
| 付费 API | 否 |
| 后台循环 | 否 |

---

## 卡片类型分布

- **组合雷达卡**：3 张
- **行情异动卡**：3 张
- **新闻事件卡**：4 张

---

## 每类卡片生成原因摘要

- **组合雷达卡**：同一资产在相同时段内触发多种信号类型，自动合并为组合卡片，避免刷屏。
- **行情异动卡**：Hyperliquid 公开 Info API 监控全市场价格变化和资金费率异常。
- **新闻事件卡**：CoinDesk / CoinTelegraph RSS Feed 拉取最新加密货币新闻（免费公开）。

---

## Combo Card 详情

| Combo # | 资产 | 合并信号类型 | 成员数 |
|---------|------|-------------|--------|
| 1 | ETH | market_anomaly + news_event + whale_transfer | 3 |
| 2 | SOL | market_anomaly + news_event | 2 |
| 3 | HYPE | market_anomaly + onchain_position + risk_alert | 3 |

---

## 数据源汇总

| 数据源 | 类型 | 状态 |
|--------|------|------|
| Hyperliquid Info API | 免费公开 API | ✅ 行情数据正常 |
| CoinDesk RSS | 免费 RSS Feed | ✅ 新闻拉取正常 |
| CoinTelegraph RSS | 免费 RSS Feed | ✅ 新闻拉取正常 |
| Etherscan / Whale Alert | 未接入 | ⏳ 按计划未扩展 |

---

## 产品化增强清单

- [x] 数字人性化格式化（$4.32M / 1.38M HYPE）
- [x] Telegram MarkdownV2 安全转义
- [x] 一键公开行情外链（CoinGecko / DexScreener）
- [x] source_type / core_entity / trigger_reason / topic_key 元数据
- [x] Combo Card：同币多信号合并（最多 3 条）
- [x] 用户可读 run manifest
- [ ] Shadow Context（待后续迭代）

---

⚠️ 仅供观察，不构成交易建议。
