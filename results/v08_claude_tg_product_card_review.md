# Claude Response

- generated_at: 2026-05-28 15:04:20 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_V08_TG_PRODUCT_CARD_REVIEW_PROMPT.md
- prompt_sha256_16: cd6dc06f1ddc763b

# Brutal Product Review

## 1. Strongest Critique

**You're building a backend-first event database when users need a front-end-first attention filter.**

Your architecture is impressive but backwards. You have:
- Event normalization ✓
- Enrichment pipelines ✓
- Quality gates ✓
- Historical replay ✓
- Price correlation ✓

But you don't have:
- A clear theory of what deserves interruption
- A ranking system users can trust without reading everything
- A way to scan 20 items in 30 seconds

Your cards are still **explanatory prose** when they should be **scannable data rows**. The competing app screenshots show this clearly: users want to see **comparative rankings** and **structured facts**, not narrative explanations.

The fundamental error: **you're treating every event as equally deserving of a full card**. Real intelligence products have layers: headlines, boards, details. You're stuck in the middle layer.

## 2. What The TG Product Should Actually Be

**Primary: Ranked board snapshots pushed at key moments**
**Secondary: Rare interrupt alerts for genuine first-hand signals**
**Tertiary: Scheduled digests with context**

Not an alert feed. Alert feeds train users to ignore alerts.

The mental model should be:
- **Boards** = what's happening now across asset classes (pushed 3-4x per China trading day)
- **Interrupts** = something just happened that you'd want to know in 60 seconds (1-3 per day max)
- **Digests** = what happened while you were away (3x daily)

### Concrete Structure

```
Morning (9:00): Overnight Board
├─ Top 5 overnight movers with OI/volume context
├─ Significant unlocks today
├─ Whale position changes >$10M
└─ [Link to detail channel]

Mid-morning (11:00): Market Snapshot
├─ Funding rate extremes (top 3)
├─ OI anomalies (top 3)
└─ CEX netflow outliers (top 2)

Afternoon (15:00): Afternoon Board
[Same structure]

Evening (21:00): Day Recap
├─ Top 3 events by follow-up impact
├─ Position changes that matter
└─ Tomorrow's unlocks
```

**Interrupts** (separate, rare):
- Security incidents >$1M
- Whale first-hand signals >$50M
- Stablecoin treasury moves >$100M
- Your own address watchlist triggers

## 3. Keep/Cut/Deprioritize

### Keep
- Hyperliquid position tracking (best first-hand signal you have)
- Stablecoin treasury flows (first-hand, clear)
- Price backfill and abnormal return calc (needed for ranking)
- Time provenance (credibility matters)
- Quality gates and token cooldown (essential)

### Cut
- Individual token unlock alerts for anything <$50M
- BTC/ETH macro news (users have 10 other sources)
- "Other" category events (if you can't classify it, don't send it)
- Verbose 🧠 interpretation sections (users don't read them)
- Confidence scores in cards (backend metric, not user-facing)

### Deprioritize
- Historical replay (useful for calibration, not for daily ops)
- AI rewrite of news (deterministic templates > LLM prose)
- Random news source scraping (focus on first-hand signals)

## 4. Information Architecture For Telegram

```
Main Channel: Boards + Rare Interrupts
├─ 3-4 board snapshots per day
├─ 1-3 genuine interrupts per day
└─ Strict: if >10 messages/day, something is wrong

Detail Channel: Full Cards (linked from boards)
├─ Users tap through when interested
├─ Full context, charts, addresses
└─ Can be verbose here

Archive Channel: Everything Else
├─ All qualified events
├─ No notifications
└─ Searchable history
```

**Critical**: The main channel is not a firehose. It's a curated snapshot product. If users need to scroll, you've failed.

## 5. Concrete Card Templates

### Template 1: Board Snapshot (Main Channel)

```
📊 午间市场扫描 11:00

【持仓异动 1h】
1. HYPE +$42M OI ↑38% | $2.34 ↑12%
2. AAVE +$18M OI ↑24% | $289 ↑8%
3. DOGE -$31M OI ↓15% | $0.18 ↓3%

【资金费率极端】
• ORDI 年化+180% 多头拥挤
• PENDLE 年化-45% 空头拥挤

【大额解锁今日】
• APT 2490万枚 $31M 15:00
• IMX 820万枚 $18M 20:00

【稳定币动向】
• USDC +$125M 流入 Coinbase
• USDT -$80M 流出 Binance

⚡ 详情 → /detail
```

**Why this works:**
- Scannable in 15 seconds
- Comparative (ranked)
- Actionable context (price + OI together)
- Not telling you what to do
- Link to details if you care

### Template 2: Interrupt Alert (Main Channel)

```
🚨 【链上大额】

Hyperliquid 新增 BTC 多头仓位
名义: $127M | 均价: $64,200
地址: 0x7a3...4f9 (历史胜率 68%)
时间: 14:23 UTC+8

当前 BTC: $64,850 ↑1.0%
资金费率: 年化 +12% (中性)

→ 详情 /d_20250528_1423
```

**Why this works:**
- Rare (you'd send <3 of these per day)
- First-hand signal
- Structured facts, no prose
- Historical context (win rate) adds credibility
- Current market state for context
- Link to full analysis

### Template 3: Security Incident (Detail Channel)

```
🔴 【安全事件】JOE 代币被盗

风险等级: R1 (高)
涉及资产: JOE
被盗金额: ~$2.4M (119.6万枚)
时间: 2025-05-28 03:15 UTC

核心原因:
• 外部合约重入漏洞
• 攻击者执行25次重入循环
• 受影响合约: 0x8a2...

当前影响:
• JOE价格 $2.01 ↓18%
• 交易所暂停充提
• 团队已确认,补偿方案待定

攻击合约: 0x3f4...
受影响合约: 0x8a2...
来源: PeckShield, 官方 Twitter

⚠️ 情报观察,非交易建议
```

**Why this works:**
- Structured fields, not prose
- Risk level upfront
- Current impact (price, exchange status)
- Addresses for verification
- Source attribution

### Template 4: Whale Position Detail (Detail Channel)

```
🐋 【Hyperliquid 大户仓位】

资产: HYPE
方向: 多头
名义规模: $23.4M
入场均价: ~$21.80
当前价格: $22.45 ↑3.0%
未实现盈亏: +$697K (+3.0%)

地址: 0x4b3...8c1
历史记录:
• 近30天胜率: 7胜 3负
• 平均持仓: 2.3天
• 最大盈利: +$1.2M (ETH多头)
• 最大亏损: -$340K (BTC空头)

仓位状态:
• 距离清算: 18% (价格 $17.89)
• 当前杠杆: 5.2x
• 资金费率: 年化 +24%

快照时间: 2025-05-28 14:35 UTC+8
数据来源: Hyperliquid API

⚠️ 这是仓位状态快照,不是交易建议
大户也会亏损,仓位可能随时变化
```

**Why this works:**
- All critical numbers upfront
- Historical context (win rate, typical hold time)
- Risk context (liquidation distance, leverage)
- Clear disclaimers about limitations

### Template 5: Morning Digest (Main Channel)

```
🌅 早间情报 09:00

【隔夜重要】
• BTC $64.2K→$65.1K ↑1.4% | ETH $3.45K→$3.52K ↑2.0%
• 美股收高 纳指+0.8% | 黄金持平

【链上动向】
• USDT金库 +$51M 转入 (04:35)
• Binance BTC净流出 -2,840 BTC
• Hyperliquid 新增 ETH多头 $34M

【今日解锁】
• APT 2490万枚 $31M 15:00 占流通 2.8%
• IMX 820万枚 $18M 20:00 占流通 1.2%

【需要关注】
• HYPE OI 24h ↑45% 持仓快速增加
• ORDI 资金费率 年化+180% 多头极度拥挤

📊 午间扫描 11:00 见
```

**Why this works:**
- Overnight context (did I miss anything critical?)
- Today's calendar (what to watch)
- Attention flags (what's unusual)
- Sets expectation for next update

## 6. Realtime Interrupt vs Digest

### Realtime Interrupt (1-3 per day max)

- Security incidents >$1M
- Your curated address watchlist (whale moves >$50M)
- Stablecoin treasury >$100M
- Hyperliquid position >$100M
- CEX netflow >$500M in 1 hour
- Major protocol exploit/hack
- Exchange halt/delisting announcement

**Test**: Would a professional trader want to know this in the next 60 seconds even if they're in a meeting?

### Digest Only

- Token unlocks <$50M
- News articles (all)
- OI changes <$20M
- Funding rate moves (unless >100% annualized)
- Social/KOL heat
- Price moves without OI/volume confirmation
- Macro news
- Benchmark (BTC/ETH) moves <5%

**Test**: Can this wait 2-4 hours for the next board snapshot?

## 7. Alert Severity/Ranking

### Severity Formula (for ranking within boards)

```python
severity_score = (
    magnitude_usd * 0.4 +           # Absolute size
    magnitude_relative * 0.3 +       # % of normal
    first_hand_bonus * 0.2 +         # On-chain vs news
    asset_liquidity_weight * 0.1     # Market cap tier
)
```

### Tier Definitions

**Tier 1: Interrupt** (score >90 or manual whitelist)
- Show immediately
- Full card
- Sound notification

**Tier 2: Board inclusion** (score 60-90)
- Include in next scheduled board
- Top 3-5 per category
- Link to detail

**Tier 3: Archive only** (score 30-60)
- Detail channel, no notification
- Searchable
- Used for historical analysis

**Tier 4: Discard** (score <30)
- Don't send
- Log for quality improvement

### Asset Liquidity Weight

- BTC/ETH: 1.0x (but higher threshold for interrupt)
- Top 20 by volume: 0.8x
- Top 100: 0.5x
- Others: 0.2x (digest only unless extraordinary)

## 8. Avoiding Microcap Garbage and False Urgency

### Hard Rules

1. **Microcap filter**: If 24h volume <$5M, digest only (never interrupt)
2. **Token cooldown**: Same token max 1 interrupt per 24h, max 3 board mentions per 24h
3. **Source cap**: Same source max 2 interrupts per 24h
4. **Unlock threshold**: <$20M = archive only, $20-50M = digest only, >$50M = board eligible
5. **OI threshold**: <$10M change = ignore, $10-20M = digest, >$20M = board eligible

### Soft Rules (scoring penalties)

- New token (<30 days): -30 points
- Low liquidity (<$2M daily volume): -20 points
- No price impact (<2% move): -15 points
- News source (vs first-hand): -10 points
- Repeated pattern (similar event <7 days): -25 points

### False Urgency Detection

**Red flags:**
- Unlock that's been scheduled for months (not new information)
- OI increase during obvious price pump (lagging indicator)
- Stablecoin flow to known operational address (not new capital)
- Whale position that's been open for days (not a new signal)

**Solution**: Timestamp provenance + "is this new information?" check
- If event was predictable >24h ago: digest only
- If event is reaction to price move: digest only
- If event is novel first-hand signal: interrupt eligible

## 9. Source Classes to Prioritize Next

### Tier 1: Build Now

1. **Binance/OKX OI snapshots** (you have Hyperliquid, add major CEXes)
   - 1h and 24h OI changes
   - Top 10 by absolute change
   - Top 10 by relative change

2. **Funding rate extremes** (you have long/short ratio, add funding)
   - Snapshot every 4h
   - Alert when >80% annualized
   - Board inclusion when >50% annualized

3. **Liquidation heatmaps** (from Coinglass or similar)
   - Where are the liquidation clusters?
   - Useful for context, not alerts

4. **Token unlock calendar** (you have CMC, good)
   - Enhance with: % of circulating, historical price impact
   - Pre-alert 24h before major unlocks

### Tier 2: Build Next Month

5. **Major CEX netflow** (you have Etherscan baseline, expand)
   - Binance, OKX, Bybit BTC/ETH netflow
   - 1h and 24h aggregates
   - Only alert on >$100M moves

6. **Stablecoin supply changes** (you have treasury, add issuance)
   - USDT/USDC supply changes
   - Mint/burn events
   - Only alert on >$50M changes

7. **Protocol TVL changes** (Defillama API)
   - >20% TVL change in 24h
   - Major protocols only (>$100M TVL)

8. **Whale wallet clusters** (expand your address watchlist)
   - Curate 50-100 known smart money addresses
   - Track their DEX swaps >$1M
   - Track their CEX deposits >$5M

## 10. Source Classes to Avoid For Now

### Don't Build

1. **Twitter/X KOL tracking** - Too noisy, hard to rank, users already have Twitter
   - Exception: If you can get engagement data and rank by "KOL consensus" (5+ major KOLs saying same thing), then maybe in 3 months

2. **Discord/Telegram scraping** - Legal issues, quality issues, too much noise

3. **News aggregation** - You already have too much news, users have other news sources

4. **Reddit/forum sentiment** - Lagging indicator, low signal

5. **GitHub commit tracking** - Interesting but not tradeable, wrong audience

6. **Governance proposals** - Too slow, wrong time horizon

7. **NFT floor prices** - Different audience, different product

8. **Macro economic calendar** - Users have Bloomberg/TradingView/etc.

### Why Avoid

You're not building a "complete" intelligence product. You're building a **crypto-native first-hand signal product**. 

The rule: **If traditional finance tools already do it well, don't compete. If it's on-chain/CEX-specific, own it.**

## 11. Handling KOL/Social Heat Without Becoming Noise

### Option A: Don't Do It (Recommended)

Users already have Twitter. You can't beat Twitter at being Twitter. Focus on what users can't easily get elsewhere: ranked on-chain + CEX data.

### Option B: If You Must, Do It Like This

**Weekly digest only** (Sunday evening):
```
📱 本周 KOL 共识

【多头共识】
• HYPE: 12位 KOL 看多 | 价格 $22.45 ↑18%
• AAVE: 8位 KOL 看多 | 价格 $289 ↑12%

【空头共识】
• DOGE: 7位 KOL 看空 | 价格 $0.18 ↓8%

【分歧最大】
• SOL: 6位看多 vs 5位看空

数据来源: 精选50位 KOL 本周发言
仅供参考,KOL 也会错
```

**Rules:**
- Weekly only, never realtime
- Requires 5+ KOLs saying same thing (consensus filter)
- Show outcome (did price move with consensus?)
- Explicit disclaimer that KOLs are often wrong

**Better approach**: Use KOL heat as a **penalty** in your ranking:
- If 10+ KOLs already talking about it: -20 points
- Reason: Your users already saw it on Twitter
- You want to show them things they might have missed

## 12. Using OI/Funding/Long-Short/Liquidation Data

### OI (Open Interest)

**What it tells you**: New leverage entering or exiting

**How to use**:
- Board snapshots: Top 5 by absolute $ change, top 5 by % change
- Interrupt threshold: >$50M change in 1h (rare)
- Context: Always show with price direction
  - OI up + price up = new longs (momentum)
  - OI up + price down = new shorts (reversal setup?)
  - OI down + price move = liquidations or closes

**Template**:
```
HYPE +$42M OI ↑38% | $2.34 ↑12%
→ 新增多头杠杆,价格同步上涨
```

### Funding Rate

**What it tells you**: Cost to hold leveraged position, proxy for sentiment

**How to use**:
- Board snapshots: Top 3 extremes (>50% annualized)
- Interrupt: Never (it's a slow-moving indicator)
- Context: Extreme funding = crowded trade = reversal risk

**Template**:
```
ORDI 资金费率 年化+180% 多头极度拥挤
→ 高资金成本,注意多头平仓风险
```

### Long/Short Ratio

**What it tells you**: Retail sentiment (on platforms that publish it)

**How to use**:
- Digest only, never interrupt
- Useful as contrarian indicator when extreme
- Show with price: "90% longs, but price down 5%" = retail wrong

**Template**:
```
【多空比极端】
• DOGE 多空比 3.2 (76%多头) | 价格 $0.18 ↓5%
→ 散户看多,价格下跌,注意背离
```

### Liquidation Data

**What it tells you**: Where stops/liquidations cluster

**How to use**:
- Never interrupt
- Show in digest as context: "Large liquidation cluster at $64K BTC"
- Useful for: "If price hits X, expect cascade"

**Template**:
```
【清算密集区】
• BTC $64,000 附近 $230M 多头清算
• ETH $3,400 附近 $120M 多头清算
→ 价格接近时注意连锁反应
```

### Integration Example (Board Snapshot)

```
📊 午间市场扫描 11:00

【持仓异动 1h】
1. HYPE +$42M OI ↑38% | $2.34 ↑12% 新增多头
2. AAVE +$18M OI ↑24% | $289 ↑8% 新增多头
3. DOGE -$31M OI ↓15% | $0.18 ↓3% 多头平仓

【资金费率极端】
• ORDI 年化+180% 多头拥挤 | 多空比 4.1
• PENDLE 年化-45% 空头拥挤 | 多空比 0.3

【清算风险】
• BTC $64K 附近 $230M 多头清算密集
```

**Why this works**: Each data type has a specific job, they're shown together for context, interpretation is minimal.

## 13. Ranking Token Unlocks

### Current Problem

Most unlocks are scheduled months in advance (not new information) and most have zero price impact (not useful information).

### Solution: Multi-Factor Unlock Score

```python
unlock_usefulness_score = (
    unlock_size_usd * 0.2 +
    pct_of_circulating * 0.3 +
    historical_impact * 0.3 +
    recipient_type * 0.2
)
```

### Factors

1. **Size**: Absolute $ value
   - <$10M: ignore
   - $10-50M: digest only
   - >$50M: board eligible

2. **% of Circulating**: Relative supply shock
   - <1%: ignore
   - 1-5%: digest
   - >5%: board eligible

3. **Historical Impact**: Did previous unlocks move price?
   - Check last 3 unlocks for same token
   - If avg price impact <3% in 24h after unlock: lower score
   - If avg price impact >10%: higher score

4. **Recipient Type**:
   - Team/advisors (likely to sell): +20 points
   - Investors (might sell): +10 points
   - Ecosystem/foundation (less likely to sell): +0 points
   - Staking rewards (distributed, less impact): -10 points

### Unlock Card Template (Detail Channel)

```
🔓 【代币解锁】APT

解锁时间: 今日 15:00 (2小时后)
解锁数量: 2,490万枚
解锁价值: ~$31M (按当前价)
占流通比: 2.8%
接收方: 早期投资人

历史影响:
• 上次解锁 (30天前): 价格 -8% (24h后)
• 上上次 (60天前): 价格 -12% (24h后)
• 平均影响: -10%

当前市场:
• APT $1.24 ↓2%
• 24h交易量: $180M
• OI: $95M (无明显变化)

⚠️ 历史影响供参考,不代表未来
```

### Unlock Board (Digest)

```
【今日解锁】
• APT 2490万枚 $31M 15:00 占流通2.8% 历史-10%
• IMX 820万枚 $18M 20:00 占流通1.2% 历史-3%

【本周解锁】
• STRK 4200万枚 $68M 周三 占流通4.1% 历史-15%
```

**Why this works**: 
- Historical impact is the key insight (not just size)
- Users can quickly see: "APT unlocks usually dump 10%"
- Ranking by expected impact, not just size

## 14. Hyperliquid Large-Position Alerts

### Current Problem

Hyperliquid positions are your best first-hand signal, but they're also:
- Snapshots (position might close 5 minutes later)
- Unverified (you don't know if this trader is good)
- Potentially misleading (large size ≠ smart trade)

### Solution: Historical Context + Clear Disclaimers

### Interrupt Alert (Main Channel)

Only send interrupt if:
- Position >$100M nominal
- Trader has historical win rate >60% (if you have history)
- Position is NEW (not just an existing position you're now noticing)

```
🚨 【Hyperliquid 大户】

BTC 新增多头 $127M
均价: $64,200 | 当前: $64,850 ↑1.0%
地址: 0x7a3...4f9 (历史胜率 68%, 19笔)
开仓: 14:23 UTC+8 (3分钟前)

⚠️ 仓位快照,可能随时变化
⚠️ 大户也会亏损

→ 详情 /d_20250528_1423
```

### Board Inclusion (Scheduled)

Show top 3-5 largest NEW positions in each board snapshot:

```
【Hyperliquid 大额仓位】
• BTC +$127M 多头 @$64.2K (新开)
• ETH +$34M 多头 @$3.45K (新开)
• HYPE -$23M 空头 @$22.8 (新开)
```

### Detail Card (Detail Channel)

```
🐋 【Hyperliquid 大户仓位】

资产: BTC
方向: 多头
名义规模: $127M
入场均价: ~$64,200
当前价格: $64,850 ↑1.0%
未实现盈亏: +$1.02M (+0.8%)

地址: 0x7a3...4f9
历史记录 (近30天):
• 总交易: 19笔
• 胜率: 68% (13胜 6负)
• 平均持仓时间: 2.3天
• 最大盈利: +$1.2M (ETH多头, 持仓3天)
• 最大亏损: -$340K (BTC空头, 持仓1天)
• 平均杠杆: 4.5x

当前仓位状态:
• 距离清算: 18% (价格 $52,644)
• 当前杠杆: 5.2x
• 持仓时间: 3分钟

市场环境:
• BTC 资金费率: 年化 +12% (中性)
• BTC OI: $12.3B (24h +2%)
• 主流 CEX 价格: $64,820 (基本一致)

快照时间: 2025-05-28 14:23 UTC+8
数据来源: Hyperliquid API

⚠️ 重要提示
• 这是仓位状态快照,不是交易建议
• 该地址历史胜率 68%,但仍有 32% 的交易亏损
• 仓位可能在发送后几分钟内关闭或调整
• 大户优势在信息和资金,不在方向判断
• 跟单风险自负

建议观察:
• 仓位是否在 24h 内平仓或加仓
• 价格是否向持仓方向移动
• 是否有其他大户跟随
```

### Key Principles

1. **Always show historical win rate** if you have it (builds credibility)
2. **Always show time since position opened** (new position = more interesting)
3. **Always show liquidation distance** (risk context)
4. **Always disclaim that position might close any time**
5. **Never say "smart money"** or imply you should follow
6. **Track and publish**: "Of the 23 large positions we alerted last month, 14 were profitable after 24h (61%)"

### Position Tracking (New Feature Needed)

Build a tracker that:
- Monitors all alerted positions
- Records: entry, exit, PnL, hold time
- Publishes weekly: "Hyperliquid 大户战绩 (本周)"
- Shows: which addresses have best track record
- Uses this to weight future alerts

## 15. CEX Netflow / Stablecoin Flow Alerts

### Current Problem

Most netflows are operational (withdrawals to cold storage, routine treasury management) and don't signal new capital or trading intent.

### Solution: Magnitude Thresholds + Pattern Recognition

### CEX Netflow

**Interrupt threshold**: >$500M in 1 hour (extremely rare)

**Board inclusion**: >$100M in 1 hour or >$300M in 24h

**Template (Board)**:
```
【CEX 资金流向】
• Binance BTC -2,840 BTC ($185M) 24h净流出
• OKX ETH +42,000 ETH ($147M) 24h净流入
• Bybit USDT -$95M 24h净流出
```

**Template (Detail)**:
```
💱 【CEX 资金流向】Binance BTC 大额流出

时间段: 过去 24h
资产: BTC
交易所: Binance
净流向: 流出 -2,840 BTC (~$185M)

流向分解:
• 流入: 8,240 BTC ($535M)
• 流出: 11,080 BTC ($720M)
• 净流出: 2,840 BTC ($185M)

背景:
• Binance BTC 余额: 542K BTC (-0.5%)
• 近7日平均日流出: 1,200 BTC
• 今日流出为近7日平均的 2.4倍

可能解读:
• 大户提币到冷钱包 (中性/看涨)
• 转移到 DeFi 或其他 CEX (中性)
• 机构托管转移 (中性)

⚠️ 净流出不等于看涨信号
需要结合价格、OI、资金费率综合判断
```

### Stablecoin Flow

**Interrupt threshold**: >$100M treasury mint/burn

**Board inclusion**: >$50M treasury movement

**Template (Board)**:
```
【稳定币动向】
• USDC +$125M 流入 Coinbase (1h)
• USDT 金库 +$51M 转入
• USDC 金库 +$80M 新增铸造
```

**Template (Detail)**:
```
💵 【稳定币流动】USDC 大额铸造

事件: USDC 新增铸造
金额: $80M
时间: 04:35 UTC+8
接收方: USDC Treasury

铸造背景:
• 近7日日均铸造: $35M
• 今日铸造为近7日平均的 2.3倍
• USDC 总供应: $42.3B (+0.19%)

后续观察:
• 铸造后 24h 内是否转移到交易所
• 是否伴随 BTC/ETH 价格上涨
• 是否有其他稳定币同步铸造

历史规律:
• 大额铸造后 24h,BTC 平均 +1.2% (过去30天,8次样本)
• 但也有 3次 下跌 (最大 -2.1%)

⚠️ 铸造不等于立即买入
需要观察资金是否真正流入市场
```

### Key Principles

1. **Magnitude matters**: Small flows are noise
2. **Direction matters less than magnitude**: Inflow/outflow both interesting if large enough
3. **Context matters**: Compare to 7-day average
4. **Follow-up matters**: Track what happened 24h after alert
5. **Don't over-interpret**: Stablecoin mint ≠ guaranteed pump

### Pattern Recognition (Advanced)

Track patterns like:
- "USDC mint → Coinbase deposit → BTC pump" (how often does this sequence happen?)
- "Binance BTC outflow → price up" (is this correlation real?)
- "USDT burn → market dump" (or is this just random?)

Publish findings in monthly digest:
```
📊 【月度规律】稳定币与价格关系

过去30天数据:
• USDC 大额铸造 (>$50M): 12次
  → 24h后 BTC 平均 +1.2%
  → 但有 4次 下跌 (最大 -2.1%)
  → 结论: 弱正相关,不可靠

• Binance BTC 大额流出 (>2000 BTC): 8次
  → 24h后 BTC 平均 +0.8%
  → 有 3次 下跌
  → 结论: 无明显相关性

⚠️ 历史规律仅供参考,市场持续变化
```

## 16. Morning/Noon/Evening Digests

### Morning Digest (9:00 China Time)

**Purpose**: What happened overnight while you were asleep?

```
🌅 早间情报 05.28 周三

【隔夜市场】
• BTC $64.2K→$65.1K ↑1.4%
• ETH $3.45K→$3.52K ↑2.0%
• 美股: 纳指 +0.8%, 标普 +0.5%
• 黄金: $2,340 持平

【重要事件】
🚨 USDC 新增铸造 $80M (04:35)
🐋 Hyperliquid BTC 新增多头 $127M (02:15)
💱 Binance BTC 净流出 -1,240 BTC 隔夜

【今日日历】
🔓 APT 解锁 2490万枚 $31M 15:00 (历史-10%)
🔓 IMX 解锁 820万枚 $18M 20:00 (历史-3%)
📊 美国 GDP 数据 20:30

【需要关注】
