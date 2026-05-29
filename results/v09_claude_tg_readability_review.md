# Claude Response

- generated_at: 2026-05-28 15:37:55 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_V09_TG_READABILITY_REVIEW_PROMPT.md
- prompt_sha256_16: 1f29cda44912b65d

# Brutal Review: Your Product Looks Like a Data Dump, Not Intelligence

## 1. What is fundamentally wrong with the current board?

**It's a database query result pretending to be intelligence.**

Specific failures:
- **No hierarchy of importance** - 5 whale positions listed equally means none matter
- **Cognitive overload** - 20+ data points per line, user must parse everything
- **Mixed timeframes** - static positions next to flow events next to 24h metrics
- **No narrative** - it's a spreadsheet in monospace font
- **Backend leakage everywhere** - `cex_netflow_in`, `0x8def...2dae`, "分数 62.8"
- **The "阅读方式" footer admits the product failed** - if you need instructions to read a radar, the radar is broken

**Core problem: You ranked items within categories, but didn't rank categories by urgency or filter by materiality threshold.**

---

## 2. What is fundamentally wrong with the current detail card?

**It repeats itself 3 times and says nothing actionable.**

```
📌 事件：麻吉黄立成减持ETH多单...465万美元...
📝 详情：麻吉黄立成减持ETH多单...465万美元...
🧠 解读：合约仓位或杠杆结构发生变化，需结合价格、资金费率和清算分布复核。
```

The "解读" is **template garbage**. It applies to every contract event. It provides zero insight. A user reading this learns:
1. Something happened (事件)
2. The same thing, again (详情)
3. "You should think about related things" (解读) ← **this is not intelligence**

**What's missing:**
- Why this trader matters (beyond "曾因蓝筹NFT获利" buried mid-text)
- Whether this is unusual behavior for them
- Whether the size/timing is significant vs. their history
- What the liquidation risk actually means (清算价 1947 vs 市价 1988 = 2% away = **extremely dangerous**, but you don't say that)

**The card has 8 fields and 4 emojis but zero insight.**

---

## 3. What should a Telegram market radar message look like on mobile?

### Anti-pattern (current):
```
🐋 Hyperliquid 大额仓位
1. HYPE 空头 $104.8M | loraclexyz 0x8def...2dae | 均价 45.37 | 强平 90.13 | 浮盈亏 -$22.8M
```
- Wraps badly
- User must parse 6 fields
- Doesn't know if -$22.8M unrealized loss matters

### Better pattern:
```
🚨 HYPE空头巨亏 | $105M仓位浮亏$23M
   loraclexyz 持仓，距离爆仓还有98%空间
```

**Principles:**
- **One line = one claim** (not 6 metrics)
- **Lead with the insight**, not the category
- **Hide non-critical fields** (均价/强平 are for detail view)
- **Use natural language** ("距离爆仓98%" not "强平 90.13")

### Proposed mobile-first structure:

```
📡 市场雷达 | 15:26

⚠️ 值得关注（2）
• HYPE空头$105M浮亏$23M，loraclexyz持仓
• HOME明日解锁$18M，占流通7.5%

📊 结构信号（3）
• DOGE多头拥挤，大户/散户仓位比2.1倍
• USDT流入Binance $505M（24h最大）
• ETH Matrixport相关多单$80M浮亏$11M

💬 详情回复本消息 | ⏸ 静音2小时
```

**Key changes:**
- Max 5 items total
- Two-tier: "值得关注" (actionable) vs "结构信号" (context)
- One sentence per item
- Details hidden behind interaction
- Escape hatch to mute

---

## 4. Single board vs. split vs. digest-only?

**Digest-only for scheduled, interrupt-only for urgent.**

| Format | Use case | Frequency |
|--------|----------|-----------|
| **紧急插播** | Liquidation cascade, major unlock starting, CEX halt | Real-time, <5/day |
| **整点雷达** | Top 3-5 structural changes | Every 2 hours during CN active hours |
| **晚间复盘** | Narrative summary of the day | 21:00 daily |
| **周末周报** | Pattern analysis, no raw events | Sunday |

**Kill the current "盘中市场雷达" entirely.** It tries to be both real-time and comprehensive, so it's neither.

---

## 5. Which fields should be hidden from users?

**Hide in main feed, show only on detail request:**

| Field | Why hide |
|-------|----------|
| 均价 | Only matters for calculating PnL, which you already show |
| 强平价格 | Meaningless without context (% distance is what matters) |
| 0x地址 | Visual noise, use entity label only |
| Source labels | `cex_netflow_in` is backend code |
| 分数 | Unexplained math |
| 主动买卖比 | Requires explanation |
| 大户仓位比 | Same |
| Allocation strings | "Core Contributors:$12,219,942; Early Backe..." is broken English in Chinese message |

**Show in main feed:**
- Asset symbol
- Direction (多/空)
- Size (in USD)
- Entity name (if known)
- Key insight (浮亏/即将解锁/拥挤)

---

## 6. Which fields should be renamed into user language?

| Backend term | User term |
|--------------|-----------|
| 强平 90.13 | 距离爆仓 +98% |
| 浮盈亏 -$22.8M | 未实现亏损 $23M |
| 分数 62.8 | 多头极度拥挤 |
| 大户仓位比 2.1321 | 大户持仓是散户2倍 |
| 主动买卖比 0.8625 | 主动卖出压力 |
| cex_netflow_in | 流入交易所 |
| stablecoin_treasury_in | 稳定币增发 |
| 流通占比 7.50% | 解锁量=当前流通7.5% |

**Rule: If a number needs explanation, either explain it inline or hide it.**

---

## 7. How many rows per section are reasonable?

**Main feed: Max 3 per section, max 2 sections per message.**

Why:
- Telegram mobile shows ~8 lines before "expand"
- User attention span for a "radar" is ~15 seconds
- If you have 10 items, 7 don't matter

**Proposed limits:**
- 紧急插播: 1 item (by definition)
- 整点雷达: 5 items total (2+3 split)
- 晚间复盘: Narrative format, not list
- Detail cards: No limit, but must be requested

---

## 8. Which sections should be shown in main group, and which should be detail/archive only?

### Main group (interrupt or scheduled):
- **Large liquidations in progress** (>$50M or cascading)
- **Major unlocks starting within 4 hours** (>$20M and >5% circulating)
- **Extreme funding rates** (>0.1% 8h or flipping sign rapidly)
- **CEX deposit spikes** (>$500M/24h single asset)
- **Known whale position changes** (if entity has track record)

### Detail/archive only:
- **All Hyperliquid positions** unless liquidation imminent
- **Long-short ratios** (noisy, needs context)
- **Taker buy/sell ratios** (same)
- **Stablecoin mints** unless >$1B
- **Small unlocks** (<$10M or <3% circulating)

**Principle: Main group is for "something changed that might matter in next 4 hours." Everything else is reference material.**

---

## 9. How should Hyperliquid positions be presented without looking like copy-trade bait?

**Current problem: You show 5 positions with entry/exit/PnL like a leaderboard.**

### Proposed: Only show positions when something changes or risk emerges

**Good reasons to show a Hyperliquid position:**
1. **Liquidation imminent** (<5% to liquidation price)
2. **Position size increased >50% in 1 hour**
3. **Known entity opened new position in unusual asset**
4. **Position closed with >$10M realized PnL**

**Template:**
```
⚠️ HYPE空头临近爆仓
$105M仓位（loraclexyz）距离强平仅剩2%
当前价格 $45.37，清算价 $46.24
```

**What to remove:**
- Don't show "top 5 positions by size" - size alone isn't a signal
- Don't show floating PnL on static positions - it's just price movement
- Don't show "Unknown Whale 0x..." - if unknown, probably not worth showing

---

## 10. How should long-short/funding/crowding data be presented without unexplained scores?

**Current: "DOGE 多头拥挤 | 分数 62.8 | 大户仓位比 2.1321 | 主动买卖比 0.8625"**

User questions:
- What is 62.8 out of?
- Is 2.1321 high?
- Is 0.8625 bearish?

### Proposed template:

```
📊 DOGE多头拥挤
大户持仓是散户2倍（近期高位），但主动卖压增加
→ 可能的多头止盈信号
```

**Structure:**
1. **Claim** (多头拥挤)
2. **Evidence** (大户2倍 + 卖压增加)
3. **Implication** (可能止盈)

**Alternative: Use percentile language**
```
DOGE多头拥挤度 85百分位（高于过去30天85%的时间）
```

**Or: Just show extremes**
- Only show if crowding score >80 or <20
- Label as "极度拥挤" or "极度空旷"
- Drop the raw numbers entirely

---

## 11. How should token unlocks be presented cleanly?

**Current: "HOME $18.3M | 流通占比 7.50% | 05-29 08:00 UTC+8 | Core Contributors:$12,219,942; Early Backe..."**

Problems:
- Broken allocation string
- Time format is verbose
- Doesn't say if this is large

### Proposed:

**For main feed (only if material):**
```
🔓 HOME明日8:00解锁$18M
占当前流通7.5%，主要是团队份额
```

**For detail card:**
```
🔓 HOME解锁详情

金额：$18.3M
时间：明天 08:00（5月29日）
占流通：7.5%

分配：
• 核心团队：$12.2M (67%)
• 早期投资人：$6.1M (33%)

历史：过去3次解锁后24h平均跌幅 -8.3%
```

**Rules:**
- Main feed: Only show if >5% circulating AND >$10M
- Always include historical price impact if available
- Translate allocation categories to Chinese
- Round percentages

---

## 12. How should CEX/stablecoin flows be presented cleanly?

**Current: "USDT 交易所净流 $504.8M | Binance | cex_netflow_in"**

Problems:
- "净流" is ambiguous (net or gross?)
- `cex_netflow_in` is code
- Doesn't say if $504M is large

### Proposed:

**Threshold-based:**
```
💧 USDT大额流入Binance
24小时流入$505M，为近7天最高
历史上类似流入后24h内BTC平均 +2.1%
```

**Structure:**
1. Direction + exchange
2. Size + context (vs. recent history)
3. Historical correlation (if strong)

**Only show if:**
- Single-day flow >$500M for BTC/ETH
- Or >$300M for single altcoin
- Or flow direction reversed vs. 7-day trend

**For stablecoin mints:**
```
💵 Tether增发$97M USDT
近3日累计增发$420M，通常领先市场反弹1-2天
```

---

## 13. What should replace the current meaningless "解读" paragraph?

**Current template garbage:**
```
🧠 解读：合约仓位或杠杆结构发生变化，需结合价格、资金费率和清算分布复核。
```

This says: "Something happened in the category this event belongs to. You should look at related things."

**It's a non-statement.**

### Replacement options:

#### Option A: Specific implication
```
⚠️ 关注：该交易员距离清算仅2%，若ETH跌破$1950可能触发连锁爆仓
```

#### Option B: Historical pattern
```
📊 参考：该交易员过去5次大额减仓后，ETH在24h内平均波动±4.2%
```

#### Option C: Related signals
```
🔗 同时：ETH资金费率转负，Binance流入增加$120M
```

#### Option D: Nothing
If you have nothing specific to say, **say nothing**. The event description should be self-contained.

**Rule: Every "解读" must contain either:**
1. A specific risk/opportunity
2. A historical pattern with numbers
3. A related confirming/contradicting signal
4. Or be deleted

---

## 14. What are 3-5 concrete user-facing templates we should implement next?

### Template 1: 紧急插播（清算风险）
```
🚨 {ASSET}清算风险

{ENTITY}持有${SIZE}M {DIRECTION}仓位
当前距离强平仅{PERCENT}%

若{ASSET}触及${PRICE}，可能引发连锁清算
相关仓位总计${TOTAL}M

🔕 静音此类提醒
```

### Template 2: 整点雷达（结构化摘要）
```
📡 {HH:MM}市场雷达

⚠️ 优先关注
• {claim 1}
• {claim 2}

📊 结构信号  
• {claim 3}
• {claim 4}
• {claim 5}

💬 详情回复本消息
```

### Template 3: 巨鲸异动（仓位变化）
```
🐋 {ENTITY} {ACTION}

{ASSET} {DIRECTION} {ACTION_VERB} ${SIZE}M
{CONTEXT_LINE}

历史：{TRACK_RECORD}
```

Example:
```
🐋 麻吉黄立成 大幅减仓

ETH 多单 平仓 $4.65M（减持70%）
剩余仓位$1M，距清算价仅2%

历史：该交易员今年已累计亏损$80M
```

### Template 4: 解锁预警（倒计时）
```
🔓 {ASSET}解锁倒计时

{TIME_UNTIL}后解锁${SIZE}M
占当前流通{PERCENT}%

分配：{TOP_CATEGORY} {PERCENT}%
历史影响：解锁后24h平均{IMPACT}

⏰ 解锁时提醒我
```

### Template 5: 晚间复盘（叙事）
```
📰 {DATE}市场复盘

今日关键：
{2-3 sentence narrative}

数据：
• {metric 1}
• {metric 2}
• {metric 3}

明日关注：
• {upcoming event 1}
• {upcoming event 2}
```

---

## 15. Strict checklist for every Telegram message before sending

### Pre-send checklist:

- [ ] **Passes mobile wrap test** (preview in Telegram mobile, no line >40 chars)
- [ ] **Lead insight in first line** (user knows why this message exists within 2 seconds)
- [ ] **No backend terms** (no `cex_netflow_in`, no `0x...`, no unexplained scores)
- [ ] **No template phrases** ("需结合...复核", "仅作...观察")
- [ ] **Numbers have context** (every number compared to threshold/history/percentile)
- [ ] **Entity names are clean** ("Unknown Whale 0x..." → hide it)
- [ ] **Action is clear** (user knows whether to: monitor, ignore, or dive deeper)
- [ ] **Passes "so what?" test** (if user asks "so what?", message fails)
- [ ] **No repetition** (don't say the same thing in 事件/详情/解读)
- [ ] **Emoji usage is consistent** (🚨 = urgent, ⚠️ = watch, 📊 = context)
- [ ] **Has escape hatch** (mute option or detail-on-demand)

### Severity gate:

Before sending to main group:
- [ ] Event severity ≥ 4/5 (for interrupts)
- [ ] OR scheduled digest time
- [ ] OR user explicitly requested details

---

## 16. What should we immediately stop sending?

### Stop immediately:

1. **"盘中市场雷达" with 20+ items** - it's a data dump
2. **Hyperliquid position leaderboards** - unless liquidation risk
3. **Long-short ratio updates** - unless extreme (>80th percentile)
4. **Small unlocks** - threshold: $10M AND >5% circulating
5. **Stablecoin mints <$500M** - noise
6. **Template "解读" paragraphs** - they say nothing
7. **Any message with `cex_netflow_in` or raw source labels**
8. **Any message with "Unknown Whale 0x..."** - if unknown, don't show
9. **Floating PnL on static positions** - only show on open/close/liquidation risk
10. **"阅读方式" footers** - if you need to teach users how to read it, redesign it

### Pause for redesign:

- All "detail cards" until template is fixed
- All "crowding" signals until you can explain the score
- All CEX flow data until you add historical context

---

## 17. What should the next 48 hours of engineering focus on?

### Hour 0-8: Kill and simplify
- [ ] Disable current "盘中市场雷达" entirely
- [ ] Set severity threshold: only send events with severity ≥4 to main group
- [ ] Implement max 5 items per message rule
- [ ] Remove all backend term leakage (source labels, 0x addresses, raw scores)

### Hour 8-16: Implement Template 2 (整点雷达)
- [ ] Build two-tier structure: "优先关注" + "结构信号"
- [ ] Implement mobile wrap test (max 40 chars per line)
- [ ] Add historical context to all numbers (percentile or vs. 7-day avg)
- [ ] Add "详情回复本消息" interaction

### Hour 16-24: Fix detail cards (Template 3)
- [ ] Remove duplicate text between 事件/详情
- [ ] Replace template "解读" with specific implication or delete
- [ ] Add track record line for known entities
- [ ] Add historical pattern if available
- [ ] Hide non-critical fields (均价, raw 强平价)

### Hour 24-32: Implement thresholds
- [ ] Hyperliquid: only show if <5% to liquidation OR position change >50%/hour
- [ ] Unlocks: only show if >$10M AND >5% circulating
- [ ] CEX flows: only show if >$500M/24h OR reversal of 7-day trend
- [ ] Crowding: only show if >80th percentile

### Hour 32-40: Add context layers
- [ ] For unlocks: add historical price impact (avg 24h change after past unlocks)
- [ ] For CEX flows: add correlation stat if strong
- [ ] For whale positions: add track record summary
- [ ] For crowding: translate score to percentile or "极度拥挤" label

### Hour 40-48: User testing
- [ ] Send redesigned 整点雷达 to test group
- [ ] Measure: time to understand, perceived usefulness, false positive rate
- [ ] Iterate based on "I don't understand X" feedback
- [ ] Set up A/B test: new template vs. silence (prove the message adds value)

---

## Deeper Product Problems You Haven't Asked About

### Problem 1: You don't have a theory of what matters

You're ranking within categories, but you haven't defined:
- What makes a whale position newsworthy vs. just large?
- What size unlock is material vs. routine?
- What crowding level predicts reversals vs. trend continuation?

**You need thresholds based on historical analysis, not just "show top 5."**

### Problem 2: You're conflating monitoring with alerting

A "radar" implies continuous monitoring. But Telegram is an interrupt-driven medium. Every message is an alert.

**Decision: Are you building a dashboard (user pulls) or an alert system (system pushes)?**

If alert system: Only send when something crosses a threshold.
If dashboard: Don't use Telegram, build a web view.

**You can't be both.** Current product tries to be both, so it spams.

### Problem 3: You have no feedback loop

How do you know if a message was useful? You're measuring:
- [ ] Click-through to details?
- [ ] User muting the bot?
- [ ] User asking follow-up questions?
- [ ] Correlation between your alerts and user trading activity?

**Without measurement, you're optimizing for your intuition, not user value.**

### Problem 4: "Intelligence" requires synthesis, not aggregation

Current product: 5 data sources → 5 sections in message
Intelligence product: 5 data sources → 1 narrative

Example:
- USDT flowing into Binance $500M
- BTC funding rate turning negative
- Large BTC long position opened on Hyperliquid
- Stablecoin mint $100M

**Current output:** 4 separate line items in 4 sections

**Intelligence output:**
```
⚠️ BTC多空分歧加剧
• Binance流入$500M USDT（备弹药）
• 但资金费率转负（空头增加）
• 同时某巨鲸新开$50M多单

→ 大额博弈中，关注$67K支撑
```

**You're building an aggregator. User wants a synthesizer.**

### Problem 5: You don't have an opinion

Every message ends with "不构成任何交易建议" - fine, legally necessary.

But you also have no opinion on:
- Is this bullish or bearish?
- Is this unusual or routine?
- Should I watch this closely or just be aware?

**User wants:** "This is weird, watch closely"
**You provide:** "This happened, think about related things"

You can have an opinion without giving trading advice:
- ✅ "历史上类似情况后24h内BTC平均+2.1%"
- ✅ "该交易员过去5次操作4次亏损"
- ✅ "此解锁规模为今年第二大"
- ❌ "建议做多BTC"

**You're allowed to provide context and pattern. You're currently providing neither.**

---

## Summary: The Brutal Truth

Your product is a **data API with a Telegram webhook**, not an intelligence product.

You have:
- ✅ Data ingestion
- ✅ Categorization
- ✅ Ranking within categories
- ❌ Materiality thresholds
- ❌ Synthesis across sources
- ❌ Historical context
- ❌ User-facing language
- ❌ Narrative structure
- ❌ Feedback loop

**The user is right: it's messy, hard to read, and not useful enough.**

But the problem isn't formatting. **The problem is you're sending too much, with too little insight, in a medium designed for interrupts.**

### What "good" looks like:

**Scenario: ETH drops 5% in 30 minutes**

**Bad (current approach):**
```
📊 盘中市场雷达
🐋 Hyperliquid大额仓位
1. ETH 多头 $79.6M | Matrixport Related...
💧 资金流向
1. ETH 交易所净流 $120M | Binance...
⚖️ 多空拥挤
1. ETH 多头拥挤 | 分数 45.2...
```

**Good (intelligence approach):**
```
🚨 ETH急跌5%触发连锁反应

Matrixport相关$80M多单距清算仅8%
同时Binance流入$120M ETH（近期高点）
多头持仓从拥挤快速降温

→ 关注$2200支撑，下方有$200M清算墙
```

**The difference:**
- One narrative vs. three separate sections
- Synthesis vs. aggregation
- Implication vs. observation
- 4 lines vs. 15 lines

---

## Final Recommendation

**Next 48 hours:**
1. Turn off the current board
2. Implement severity threshold (only send ≥4/5)
3. Build Template 2 (整点雷达, max 5 items)
4. Fix detail cards (remove repetition, add context)
5. User test with 10 messages

**Next 2 weeks:**
1. Define materiality thresholds for each data source
2. Build synthesis engine (detect multi-source patterns)
3. Add historical context to all numbers
4. Implement feedback measurement
5. A/B test: new format vs. silence

**Next month:**
1. Build narrative digest (晚间复盘)
2. Add user preference controls (mute categories, set thresholds)
3. Implement detail-on-demand (reply for more info)
4. Launch public beta

**You have good data. You need to stop showing all of it.**
