# Market Radar v1.11-K — Content Value Review Report

**Run**: 2026-06-04 21:00 UTC+8
**Version**: v1.11-K
**Mode**: Content value review (no TG send, no external AI, no paid API)
**Status**: Complete

---

## 本轮目标

对 v1.11-J-Mock 的 3 张 mock_sent 卡片进行内容价值复盘，判断它们是否真的值得进入后续测试频道/正式频道候选，而不是只证明技术链路能跑。

重点回答：
1. 这 3 张卡是否只是行情播报？
2. 是否有足够多因子支撑？
3. 是否有重复、AI 味、噪音、误导性表达？
4. 哪张最值得保留？
5. 当前 Market Radar 是否可以视为 MVP 主体闭环完成？
6. 正式频道解冻还缺什么？

---

## 审计对象：3 张 mock_sent 卡

| # | Mock ID | Signal ID | Asset | Value Score | Cooldown | Pre-send |
|--:|---------|-----------|-------|-------------:|----------|----------|
| 1 | `mock_v111j_001` | H6-07 | ARB | 140 | upgrade_override | pass |
| 2 | `mock_v111j_002` | H5-01 | ETH | 115 | upgrade_override | pass |
| 3 | `mock_v111j_003` | H1-01 | ETH | 120 | allow (first) | pass |

---

## 每张卡的内容复盘

### Card 1: mock_v111j_001 — H6-07 ARB

**Payload Preview**:
> 📉 行情异动｜ARB 急跌
>
> 一句话：ARB 跌幅 8.50%，价值: allow, 冷却: upgrade_override (score↑), 安全: pass
>
> ● 币种：ARB
> ● 涨跌幅：-8.50%
> ● Funding：-1.80%（年化 -1971.0%）
> ● 是否拥挤：否
> ● 观察窗口：1-4 小时
>
> 🔗 行情查看：[CoinGecko](https://www.coingecko.com/en/coins/arbitrum) / [DexScreener](https://dexscreener.com/search?q=ARB)

**因子分析**:
- Price: -8.50% (strong, >=8%)
- OI: $5.2M (confirmed)
- Volume: $6.1M (confirmed)
- Funding: -1.80% annualized -1971% (extreme)
- Multi-asset sync: 10 assets all down (backed by OI/volume)
- Upgrade signal: yes (score 100 → 140, Δ=+40)

**内容评分**:

| Dimension | Score |
|-----------|-------|
| signal_value_score | **95/100** |
| risk_score | **8/100** |
| final_grade | **A** |
| recommendation | **keep** |

**判断理由**:
- 5/4 因子全确认（price + OI + volume + funding + multi_asset_sync）
- 升级信号（upgrade_override），代表信号在快速恶化
- 无重复风险（唯一 ARB 卡）
- 无 AI 味（语言中性，未使用"全确认""极端"等表达）
- 无过度推断
- 表达直接、可用
- **不存在行情播报噪音**：有 OI/Volume/Funding 三重支撑，不是仅价格波动

**是/否行情播报**: 否。有充分的 OI/Volume/Funding/Multi-asset 多维因子支撑。

---

### Card 2: mock_v111j_002 — H5-01 ETH

**Payload Preview**:
> 📉 行情异动｜ETH 急跌
>
> 一句话：ETH 跌幅 8.50%，强信号: OI+Vol+Funding 全确认 (score~100)
>
> ● 币种：ETH
> ● 涨跌幅：-8.50%
> ● Funding：-2.50%（年化 -2737.5%）
> ● 是否拥挤：否
> ● 观察窗口：1-4 小时
>
> 🔗 行情查看：[CoinGecko](https://www.coingecko.com/en/coins/ethereum) / [DexScreener](https://dexscreener.com/search?q=ETH)
>
> 💡 触发原因：ETH ...

**因子分析**:
- Price: -8.50% (strong, >=8%)
- OI: $12.5B (confirmed)
- Volume: $18.2B (confirmed)
- Funding: -2.50% annualized -2737.5% (extreme)
- Multi-asset sync: not in this scenario (H5 has 5 assets, but this signal doesn't have multi_asset_sync reason)
- Upgrade signal: yes (score 45 → 115, Δ=+70)

**内容评分**:

| Dimension | Score |
|-----------|-------|
| signal_value_score | **100/100** |
| risk_score | **38/100** |
| final_grade | **B** |
| recommendation | **revise** |

**判断理由**:
- 3/4 因子确认（price + OI + volume + funding，缺 multi_asset_sync）
- 升级信号（Δ=+70，最大升级幅度）
- Tier-1 资产 (ETH)
- **存在 AI 味**："全确认" 表达略显模板化
- **存在重复风险**：与 mock_v111j_003 同为 ETH 急跌，叙事重叠
- **存在行情播报倾向**：表达方式接近"涨了跌了"风格，但因为有 OI/Vol/Funding 支撑，不是纯噪音
- Funding -2.50% 是极端值，信号价值高

**是/否行情播报**: 否。有 OI/Volume/Funding 三维确认 + Tier-1 资产 + upgrade 信号，不是纯行情播报。但表达有改进空间。

**改进建议**: 去掉 "(score~100)" 这类内部评分泄露；避免与 H1-01 ETH 叙事重复；可强化"Funding -2.50% 极端"的独特视角。

---

### Card 3: mock_v111j_003 — H1-01 ETH

**Payload Preview**:
> 📉 行情异动｜ETH 下跌
>
> 一句话：ETH 24h 跌幅 6.80%，OI+Vol+Funding 极端四重确认
>
> ● 币种：ETH
> ● 涨跌幅：-6.80%
> ● Funding：-1.50%（年化 -1642.5%）
> ● 是否拥挤：否
> ● 观察窗口：1-4 小时
>
> 🔗 行情查看：[CoinGecko](https://www.coingecko.com/en/coins/ethereum) / [DexScreener](https://dexscreener.com/search?q=ETH)
>
> 💡 触发原因：ETH 24h 跌幅 6.80%

**因子分析**:
- Price: -6.80% (>=5%, not strong >=8%)
- OI: $12.9B (confirmed)
- Volume: $16B (confirmed)
- Funding: -1.50% annualized -1642.5% (extreme)
- Multi-asset sync: 5 assets all down (backed by OI/volume)
- No upgrade signal (first occurrence)

**内容评分**:

| Dimension | Score |
|-----------|-------|
| signal_value_score | **80/100** |
| risk_score | **41/100** |
| final_grade | **C** |
| recommendation | **revise** |

**判断理由**:
- 4/4 因子确认（price + OI + volume + funding + multi_asset_sync）
- 原始 value_score 120（本批次最高之一）
- **存在过度推断**："极端四重确认" — "极端" 用词过度，Funding -1.50% 虽触发 extreme 阈值但不如 H5-01 的 -2.50%
- **存在 AI 味**："四重确认" 是典型的 AI 生成表达
- **存在重复风险**：与 mock_v111j_002 同为 ETH 急跌，两张 ETH 卡只选其一
- **存在行情播报倾向**：价格跌幅 6.80% 在所有信号中属于中等，强调"极端"有夸大嫌疑

**是/否行情播报**: 边缘。数据支撑足够（4/4 因子），但表达过度渲染让信号显得像包装后的行情播报。

**改进建议**: 去掉"极端"修饰；将"四重确认"改为更中性的"OI+Vol+Funding 同步异动"；考虑是否与 H5-01 合并为一张 ETH 综合卡。

---

## 汇总判断

| Recommendation | Count | Cards |
|---------------|-------|-------|
| **keep** | 1 | mock_v111j_001 (ARB, grade A) |
| **revise** | 2 | mock_v111j_002 (ETH, grade B), mock_v111j_003 (ETH, grade C) |
| observe | 0 | — |
| drop | 0 | — |

---

## 最佳候选卡

**mock_v111j_001 — H6-07 ARB (Grade A)**

理由：
- 唯一一张 A 级卡
- 5/4 因子全确认，无短板
- 升级信号，代表信号恶化（信息量 > 普通 allow）
- 唯一 ARB 卡，无重复风险
- 语言最干净，无 AI 味、无过度推断
- risk_score 仅 8/100，是本轮最低

---

## 是否存在行情播报噪音？

**总体：否。** 3 张卡都有 OI/Volume/Funding 多因子支撑，不是纯价格播报。

但存在以下问题：
1. **模板化表达**：3 张卡共用同一模板（"📉 行情异动｜X 急跌/下跌" → "一句话" → bullet points），长期发送会产生审美疲劳。
2. **ETH 重复**：mock_v111j_002 和 mock_v111j_003 都是 ETH 急跌，对同一资产的两张卡叙事重叠 70%+。应只保留一张（推荐保留 H5-01，因其 Funding 更极端）。
3. **信号强度与表达的匹配度**：mock_v111j_003 的 "极端四重确认" 与实际数据强度不匹配（Funding -1.50% vs H5-01 的 -2.50%）。

---

## 是否存在 AI 味 / 过度推断？

**是，局部存在。**

- mock_v111j_002："全确认"、"score~100"（内部评分泄露）
- mock_v111j_003："极端四重确认"（过度渲染 + AI 模板表达）
- mock_v111j_001：基本无 AI 味

建议：
- 去掉卡片中的内部 gate 状态文字（"价值: allow, 冷却: upgrade_override"等），这些是调试信息，不是终端用户需要的内容。
- 用更自然的语言替代"全确认""X重确认"等表达。

---

## 是否建议后续真实测试群发送？

**建议：是，但限制为 1 张（mock_v111j_001 ARB）。**

理由：
- mock_v111j_001 (ARB, grade A) 通过全部审计标准，适合作为首张真实测试发送卡。
- 另外 2 张 ETH 卡需要先微调文案、解决重复问题后再进入候选。
- 测试群发送的目的是验证真实 TG 发送效果，1 张 A 级卡足够完成这个验证。

---

## 是否建议正式频道解冻？

**不建议。默认应为否，除非有强理由。**

当前缺乏的：
1. **真实 TG 发送验证** — 所有发送都是 mock，未验证 TG API 实际行为（速率限制、格式渲染、链接预览等）。
2. **Sender 安全抽象** — 缺少 token 注入、发送重试、失败降级、发送确认机制。
3. **Cooldown 持久化** — 当前 cooldown 在内存中，进程重启后丢失状态。需要跨进程/跨重启持久化。
4. **OI-Volume delta 追踪** — 缺少对 OI/Volume 变化趋势的追踪（区分趋势性异动 vs 瞬时波动）。
5. **真实行情数据接入** — 当前基于 v1.11-I 的存量假设数据，未接入实时行情源。
6. **测试群用户反馈** — 从未在真实 TG 群中获取过用户反馈。

---

## Market Radar MVP 主体闭环判断

| 维度 | 状态 | 说明 |
|------|------|------|
| 技术链路闭环 | **完成** | SignalValueGate → CooldownGate → payload render → pre_send_gate → mock_sender → sent log 全部跑通 |
| 内容链路闭环 | **完成** | 3 张 mock_sent 卡内容可评估，至少 1 张 A 级卡可进入测试发送候选 |
| 可进入真实测试群发送 | **是（限制 1 张）** | mock_v111j_001 (ARB, grade A) 适合作为首张真实测试发送 |
| 可进入正式频道 | **否** | 缺少真实发送验证、安全抽象、持久化、delta 追踪、用户反馈 |

**结论：Market Radar MVP 主体闭环完成。技术链路在 v1.11-J 已验证；内容链路在 v1.11-K 已验证。可以进行下一步（真实测试群小规模发送），但正式频道解冻还需要多轮迭代。**

---

## 安全声明

- [x] 未真实发送 TG
- [x] 未调用外部 AI / 付费 API
- [x] 未读取 token/chat_id/key/cookie/password
- [x] 未触碰正式频道
- [x] 未写入 ai_relay_desk 目录
- [x] 未启动 loop/daemon/cron
- [x] 未删除文件
