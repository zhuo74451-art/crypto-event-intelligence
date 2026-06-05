# Market Radar v1.11-J-Mock — Mock Sender Rehearsal Report

**Run**: 2026-06-04 20:54:28 UTC+8
**Version**: v1.11-J-Mock
**Mode**: Mock sender rehearsal (no real TG send)
**Status**: ✅ Complete

## 本轮目标

证明以下完整发送逻辑链路可以在不读取 token、不注入凭证、不真实发送 TG 的情况下完成：

```
SignalValueGate → CooldownGate → payload render → pre_send_gate → mock_sender → sent log
```

## 为什么改用 mock sender

1. 安全阻断正确：旧真实发送路线缺少 TG 运行凭证时无法完成闭环。
2. Mock sender 不依赖 token / chat_id / 网络请求，可以在任何环境执行。
3. 本轮目标不是获取真实 message_id，而是验证发送逻辑闭环的完整性。

## 3 张候选卡列表

| # | Signal ID | Asset | Value Score | Cooldown | Pre-send |
|--:|-----------|-------|------------:|----------|----------|
| 1 | H6-07 | ARB | 140 | upgrade_override | pass |
| 2 | H5-01 | ETH | 115 | upgrade_override | pass |
| 3 | H1-01 | ETH | 120 | allow | pass |

## 每张 mock_message_id

| Mock ID | Signal ID | Asset | Status |
|---------|-----------|-------|--------|
| `mock_v111j_001` | H6-07 | ARB | mock_sent |
| `mock_v111j_002` | H5-01 | ETH | mock_sent |
| `mock_v111j_003` | H1-01 | ETH | mock_sent |

## 每张 payload preview

### mock_v111j_001 — H6-07 ARB

> 📉 行情异动｜ARB 急跌

一句话：ARB 跌幅 8\.50%，价值: allow, 冷却: upgrade\_override \(score↑\), 安全: pass

● 币种：ARB
● 涨跌幅：\-8\.50%
● Funding：\-1\.80%（年化 \-1971\.0%）
● 是否拥挤：否
● 观察窗口：1\-4 小时

🔗 行情查看：\[CoinGecko\]\(https:/...

### mock_v111j_002 — H5-01 ETH

> 📉 行情异动｜ETH 急跌

一句话：ETH 跌幅 8\.50%，强信号: OI\+Vol\+Funding 全确认 \(score\~100\)

● 币种：ETH
● 涨跌幅：\-8\.50%
● Funding：\-2\.50%（年化 \-2737\.5%）
● 是否拥挤：否
● 观察窗口：1\-4 小时

🔗 行情查看：\[CoinGecko\]\(https://www\.coingec...

### mock_v111j_003 — H1-01 ETH

> 📉 行情异动｜ETH 下跌

一句话：ETH 24h 跌幅 6\.80%，OI\+Vol\+Funding 极端四重确认

● 币种：ETH
● 涨跌幅：\-6\.80%
● Funding：\-1\.50%（年化 \-1642\.5%）
● 是否拥挤：否
● 观察窗口：1\-4 小时

🔗 行情查看：\[CoinGecko\]\(https://www\.coingecko\.com/en/co...

## 每张为什么值得进入后续内容复盘

- **H6-07 ARB**: 多因子全确认（price + OI + volume + funding + multi_asset_sync），value_score=140，升级信号，是本轮最强信号。
- **H5-01 ETH**: OI+Vol+Funding 全确认，value_score=115，cooldown=upgrade_override（分数从45提升至115），是典型的升级覆盖案例。
- **H1-01 ETH**: 四重确认（OI+Vol+Funding+多资产同步），value_score=120，是最干净的首发信号案例。

## Sent log 路径

`C:\Users\PC\Desktop\Projects\事件情报系统\logs\market_radar\v111j_mock_sent_messages_log.json`

## 安全声明

- [x] 未真实发送 TG
- [x] 未读取 token/chat_id
- [x] 未触碰正式频道
- [x] 未调用网络请求
- [x] 未写入 ai_relay_desk 目录
- [x] 未启动 loop/daemon/cron
- [x] 未调用付费 API
- [x] 未删除文件

## 是否建议进入 v1.11-K

✅ **建议进入 v1.11-K（内容价值复盘 / Gemini 审计）**。

原因：
1. Mock sender 已验证完整的发送逻辑闭环。
2. 3 张候选卡全部通过了所有门控校验。
3. Payload 内容就绪，可以在不真实发送的情况下进行内容质量审计。
4. 本轮不需要真实 TG 凭证即可推进。
