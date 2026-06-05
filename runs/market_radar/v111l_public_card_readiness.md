# Market Radar v1.11-L — Public Card Readiness Report

**Generated**: 2026-06-04 21:12:21 UTC+8
**Version**: v1.11-L
**Mode**: public_card_readiness

---

## 本轮目标

将 Market Radar 卡片从"调试态 payload"升级为"用户可读的公开卡片"。
修复 v1.11-K 暴露的内容问题：公开卡片文本不得包含内部 gate/debug 状态。

## 为什么不能直接真实发送

1. **内容污染**：v1.11-K 确认 payload 中仍包含 `价值: allow`, `冷却: upgrade_override` 等内部调试信息。
2. **sender 安全抽象未完成**：token 注入、发送重试、失败降级均未实现。
3. **cooldown 持久化未完成**：跨进程/跨重启状态不保留。
4. **无真实 TG 环境验证**：端到端效果未确认。

---

## 3 张卡 Public Preview

### H6-07 — ARB (natural)

- **状态**: ✅ 通过
- **parse_mode**: `MarkdownV2`
- **text_length**: 358 chars
- **debug_terms_found**: 无
- **ai_style_terms_found**: 无

```
📉 行情异动｜ARB 急跌

一句话：ARB 24h 跌幅 \-8\.50%，多因子异动信号 — OI/成交量同步放大，资金费率极端偏空。

● 币种：ARB
● 涨跌幅：\-8\.50%
● Funding：\-1\.80%（年化 \-1971\.0%）
● 是否拥挤：否
● 观察窗口：1\-4 小时

🔗 行情查看：\[CoinGecko\]\(https://www\.coingecko\.com/en/coins/arbitrum\) / \[DexScreener\]\(https://dexscreener\.com/search?q\=ARB\)

💡 触发原因：ARB 多因子同步异动（价格跌幅 \+ OI \+ 成交量 \+ 资金费率偏空），短时升级信号。

⚠️ 仅供观察，不构成交易建议。
```

### H5-01 — ETH (upgrade_focus)

- **状态**: ✅ 通过
- **parse_mode**: `MarkdownV2`
- **text_length**: 386 chars
- **debug_terms_found**: 无
- **ai_style_terms_found**: 无

```
📉 行情异动｜ETH 急跌

一句话：ETH 24h 跌幅 \-8\.50%，多因子同步确认 — OI/成交量/资金费率三者共振，信号强度升级。

● 币种：ETH
● 涨跌幅：\-8\.50%
● OI：$12\.50B
● 成交量：$18\.20B
● Funding：\-2\.50%（年化 \-2737\.5%）
● 是否拥挤：否
● 观察窗口：1\-4 小时

🔗 行情查看：\[CoinGecko\]\(https://www\.coingecko\.com/en/coins/ethereum\) / \[DexScreener\]\(https://dexscreener\.com/search?q\=ETH\)

💡 触发原因：ETH 价格跌幅扩大，OI 与成交量同步放大，资金费率极端偏空，信号强度较前次明显升级。

⚠️ 仅供观察，不构成交易建议。
```

### H1-01 — ETH (strength_focus)

- **状态**: ✅ 通过
- **parse_mode**: `MarkdownV2`
- **text_length**: 375 chars
- **debug_terms_found**: 无
- **ai_style_terms_found**: 无

```
📉 行情异动｜ETH 下跌

一句话：ETH 24h 跌幅 \-6\.80%，基础面偏空 — 大额 OI 配合成交量放大，资金费率转负。

● 币种：ETH
● 涨跌幅：\-6\.80%
● OI：$12\.90B
● 成交量：$16\.00B
● Funding：\-1\.50%（年化 \-1642\.5%）
● 是否拥挤：否
● 观察窗口：1\-4 小时

🔗 行情查看：\[CoinGecko\]\(https://www\.coingecko\.com/en/coins/ethereum\) / \[DexScreener\]\(https://dexscreener\.com/search?q\=ETH\)

💡 触发原因：ETH 价格持续走弱，OI 维持高位，成交量明显放大，短期偏空压力未缓解。

⚠️ 仅供观察，不构成交易建议。
```

---

## Debug Leak 检查结果

| Card | Debug Terms | AI Terms | Passed |
|------|-------------|----------|--------|
| H6-07 (ARB) | — | — | ✅ |
| H5-01 (ETH) | — | — | ✅ |
| H1-01 (ETH) | — | — | ✅ |

**debug_leak_count**: 0

---

## ETH 重复度 / AI 味修正结果

### H5-01 ETH (升级信号角度)
- 定位：多因子同步升级信号，OI/成交量/资金费率三者共振
- 语言：自然描述"信号强度升级"，避免"四重确认"等模板化表达

### H1-01 ETH (基础强度角度)
- 定位：基础面偏空，大额 OI 配合成交量放大
- 语言：更简洁的基础描述，与 H5-01 形成角度差异

### 差异检查
- ✅ ETH 两张卡内容有差异：H5-01 独有 7 行，H1-01 独有 7 行

**AI 风格术语总计**: 0 处

---

## Best Candidate

- **信号**: H6-07
- **资产**: ARB
- **评级**: A
- **建议**: keep

**ARB 仍为 best_candidate**：多因子确认（价格 + OI + 成交量 + 资金费率），
composite score 最高，内容净化后保留核心信息。

---

## 是否建议进入下一步

**建议进入 v1.11-M（Gemini 外部审计）或 v1.11-N（真实测试群发送）**，条件：

1. ✅ 3 张卡均通过 debug leak 检查
2. ✅ 审计 metadata 完整保留
3. ✅ ETH 卡差异化处理完成
4. ✅ best_candidate 明确
5. ⚠️ 需先完成 Gemini 外部审计确认内容质量

---

## 正式频道解冻建议

**必须为否**。原因：

- 未经过真实 TG 测试群发送验证
- sender 安全抽象（token 注入、重试、降级）未实现
- cooldown 持久化（跨进程/跨重启）未实现
- OI/Volume delta 实时追踪未实现
- 仅 3 张 mock 卡，样本量不足

---

## 下一步建议

1. **Gemini 外部审计 (v1.11-M)**：将 public card preview 发送 Gemini 评估内容质量
2. **sender 安全抽象**：实现 token 安全注入、发送重试、失败降级
3. **cooldown 持久化**：跨进程/跨重启状态保留
4. **真实测试群发送 (v1.11-N)**：在确认内容质量后，以 test channel 小规模发送 1-2 张 A 级卡
5. **OI/Volume delta 追踪**：区分趋势性 vs 瞬时异动
