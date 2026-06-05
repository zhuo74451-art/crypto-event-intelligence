# Market Radar v1.11-K — Gemini Review Packet

**写给 Gemini 的审计包** — 不调用 Gemini API，纯文本供后续人工/Gemini 审查。

**Generated**: 2026-06-04 21:00 UTC+8
**Executor**: claude_code_executor (DeepSeek/Claude Code)
**Version**: v1.11-K

---

## 1. 当前链路完成事实

Market Radar 项目已完成以下技术迭代：

```
v1.11-d: SignalValueGate (信号价值门控)
v1.11-f: SameAssetCooldownGate (同资产冷却门控)
v1.11-j: MockTelegramSender (Mock 发送器)
v1.11-i: PreTestSendRehearsal (发送前彩排)

完整发送链路:
SignalValueGate → CooldownGate → payload render → pre_send_gate → mock_sender → sent log
```

技术链路可以在**不读取 TG token、不注入凭证、不真实发送、不调用网络**的情况下完成闭环。

---

## 2. v1.11-J-Mock 证据

### Mock Sender Rehearsal Result

- 3 张候选卡全部通过全部门控 (SignalValueGate → CooldownGate → pre_send_gate)
- 3 张卡全部 mock_sent 成功
- 0 阻断
- 真实 TG 发送: false
- 网络调用: false
- 凭证读取: false

### Sent Log 路径

```
logs/market_radar/v111j_mock_sent_messages_log.json
```

包含 3 条 mock_sent 记录，每条含 payload_text_sha256、payload_preview、send_status。

---

## 3. 3 张卡片内容 Preview

### Card A: mock_v111j_001 — H6-07 ARB

```
📉 行情异动｜ARB 急跌

一句话：ARB 跌幅 8.50%，价值: allow, 冷却: upgrade_override (score↑), 安全: pass

● 币种：ARB
● 涨跌幅：-8.50%
● Funding：-1.80%（年化 -1971.0%）
● 是否拥挤：否
● 观察窗口：1-4 小时

🔗 行情查看：[CoinGecko](https://www.coingecko.com/en/coins/arbitrum) / [DexScreener](https://dexscreener.com/search?q=ARB)
```

**原始门控数据**:
- value_score: 140 (本批次最高)
- cooldown: upgrade_override (score 100→140, Δ=+40)
- pre_send: pass
- 因子: price (-8.50%, strong) + OI ($5.2M) + Volume ($6.1M) + Funding (-1.80%, extreme) + multi_asset_sync (10 assets down)

### Card B: mock_v111j_002 — H5-01 ETH

```
📉 行情异动｜ETH 急跌

一句话：ETH 跌幅 8.50%，强信号: OI+Vol+Funding 全确认 (score~100)

● 币种：ETH
● 涨跌幅：-8.50%
● Funding：-2.50%（年化 -2737.5%）
● 是否拥挤：否
● 观察窗口：1-4 小时

🔗 行情查看：[CoinGecko](https://www.coingecko.com/en/coins/ethereum) / [DexScreener](https://dexscreener.com/search?q=ETH)

💡 触发原因：ETH ...
```

**原始门控数据**:
- value_score: 115
- cooldown: upgrade_override (score 45→115, Δ=+70)
- pre_send: pass
- 因子: price (-8.50%, strong) + OI ($12.5B) + Volume ($18.2B) + Funding (-2.50%, extreme)

### Card C: mock_v111j_003 — H1-01 ETH

```
📉 行情异动｜ETH 下跌

一句话：ETH 24h 跌幅 6.80%，OI+Vol+Funding 极端四重确认

● 币种：ETH
● 涨跌幅：-6.80%
● Funding：-1.50%（年化 -1642.5%）
● 是否拥挤：否
● 观察窗口：1-4 小时

🔗 行情查看：[CoinGecko](https://www.coingecko.com/en/coins/ethereum) / [DexScreener](https://dexscreener.com/search?q=ETH)

💡 触发原因：ETH 24h 跌幅 6.80%
```

**原始门控数据**:
- value_score: 120
- cooldown: allow (first occurrence)
- pre_send: pass
- 因子: price (-6.80%) + OI ($12.9B) + Volume ($16B) + Funding (-1.50%, extreme) + multi_asset_sync (5 assets down)

---

## 4. GPT/执行端初步评分

| Card | Asset | signal_value_score | risk_score | Grade | Recommendation |
|------|-------|--------------------|------------|-------|----------------|
| mock_v111j_001 | ARB | **95** | **8** | **A** | **keep** |
| mock_v111j_002 | ETH | **100** | **38** | **B** | **revise** |
| mock_v111j_003 | ETH | **80** | **41** | **C** | **revise** |

### 评分规则说明

**signal_value_score (0-100)**:
- 多因子支撑: +25
- OI 支撑: +15
- Volume 支撑: +15
- Upgrade override: +20
- Tier-1 资产: +10
- 不是纯价格波动: +15

**risk_score (0-100)**:
- 只有价格波动: +30
- 无 OI/Volume: +20
- 表达像行情播报: +15
- 结论过度推断: +20
- 与其他卡重复: +15
- AI 风格表达检测: +8-15

**Grade**:
- A: net >= 70, risk <= 30 — 强信号，可进入测试发送
- B: net >= 50, risk <= 50 — 可用，建议微调
- C: net >= 30 — 观察，不建议发送
- D: net < 30 — 丢弃

### 执行端判断摘要

- **最佳候选**: mock_v111j_001 (ARB) — 唯一 A 级，5 因子全确认，语言最干净，无重复风险
- **ETH 重复问题**: mock_v111j_002 和 mock_v111j_003 同为 ETH，叙事重叠 70%+，建议只保留一张
- **AI 味问题**: mock_v111j_003 "极端四重确认" 过度渲染；mock_v111j_002 "全确认" 模板化
- **MVP 判断**: 技术闭环完成，内容闭环完成，不建议正式频道解冻

---

## 5. 希望 Gemini 判断的 3 个问题

### 问题 1: 信号价值判断

> 这 3 张卡是否真的有市场信号价值，还是只是包装后的行情播报？

执行端初步判断：3 张卡都有 OI/Volume/Funding 多因子支撑，不是纯行情播报。但 Card C 的 "极端四重确认" 表达过度渲染，让信号显得像包装后的行情播报。

**希望 Gemini 确认**:
- 在当前的多因子门控体系下，"价格异动 + OI + Volume + Funding 极端" 的组合是否真的构成有效市场信号？
- 还是这些因子只是从同一市场事件（普跌）中提取的冗余确认？
- 8.50% 的日跌幅在 crypto 中是否真的算"急跌"？6.80% 呢？

### 问题 2: MVP 闭环判断

> 当前 mock send + content review 是否足以判定 Market Radar MVP 主体闭环完成？

执行端初步判断：是。技术链路（gate → render → send → log)在 v1.11-J 已验证；内容链路在 v1.11-K 已验证。

**希望 Gemini 确认**:
- "MVP 主体闭环"的定义是否应该更严格（例如必须包含真实 TG 发送 + 用户反馈）？
- 如果 mock_send 足以证明技术闭环，那么内容闭环的最低标准是什么？
- 3 张卡的内容审计是否足够代表内容链路闭环？

### 问题 3: 下一步优先级

> 下一步应该进入真实测试群小规模发送，还是先补 sender 安全抽象 / cooldown 持久化 / OI-volume delta？

执行端初步判断：建议先进入真实测试群发送（限制 1 张 A 级卡），并行补充基础设施。

**希望 Gemini 确认**:
- 在 sender 安全抽象（token 注入、发送重试、失败降级）缺失的情况下，真实发送的风险是否可控？
- Cooldown 持久化是否是真实发送的硬性前提（如果只发 1 张卡，cooldown 的实际意义有限）？
- OI-volume delta 追踪是否应该在真实发送前完成（用于过滤假信号），还是可以在并行迭代中补充？

---

## 附录：评分计算详情

### mock_v111j_001 (ARB, Grade A)
```
signal_value_score = 25(多因子) + 15(OI) + 15(Vol) + 20(upgrade) + 5(Tier-2) + 15(非纯价格) = 95
risk_score = 8(broadcast template匹配 2 个模式) = 8
net = 95 - 8 = 87 → A
```

### mock_v111j_002 (ETH, Grade B)
```
signal_value_score = 25(多因子) + 15(OI) + 15(Vol) + 20(upgrade) + 10(Tier-1) + 15(非纯价格) = 100
risk_score = 15(duplicate asset ETH) + 8(broadcast) + 15(AI style: "全确认") = 38
net = 100 - 38 = 62 → B
```

### mock_v111j_003 (ETH, Grade C)
```
signal_value_score = 25(多因子) + 15(OI) + 15(Vol) + 0(no upgrade) + 10(Tier-1) + 15(非纯价格) = 80
risk_score = 15(duplicate asset ETH) + 8(broadcast) + 10(overclaiming: "极端") + 8(AI style: "四重确认") = 41
net = 80 - 41 = 39 → C
```

---

*End of Gemini Review Packet. This file is designed for human or Gemini review — no API call is expected or required.*
