# Claude Response

- generated_at: 2026-05-28 12:24:02 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_V08_USER_VIEW_PROJECT_REVIEW_PROMPT.md
- prompt_sha256_16: 72cc365d77293179

# Brutal Project Review: Crypto Event Intelligence

## 1. Strongest Critique of Current Direction

**You've built a sophisticated backtesting infrastructure for a product that doesn't need it yet.**

Your core problem is not "how do I measure alert quality historically" — it's **"do I have anything worth alerting on at all?"**

You have 8 live alerts sent. That's not a quality measurement problem, that's a product-market fit problem. You're optimizing the measurement apparatus before you know what you're measuring matters.

The BTC/macro domination in your historical data is a **symptom, not a bug**. It tells you: second-hand news sources are dominated by macro narratives because that's what crypto news is. If you want differentiated intelligence, you need differentiated sources.

You're also conflating two products:
1. A **news aggregator with smart filtering** (what you've mostly built)
2. An **on-chain/first-hand intelligence feed** (what you claim to want)

Pick one or accept they're different feeds with different quality bars.

---

## 2. Keep / Cut / Deprioritize

### **KEEP (Core Infrastructure)**
- Event normalization pipeline
- Price backfill + abnormal return calculation
- Telegram delivery with rate limits and send windows
- Watcher framework (Ethereum addresses, stablecoin mint/burn)
- CEX netflow baseline context
- Hyperliquid position tracking
- China-time scheduling logic

### **CUT (Premature Optimization)**
- Stratified auto-review sampling — you don't have enough data
- Complex historical replay with 200/120 row splits — this is theater
- Benchmark-aware BTC vs ETH switching logic — solve this with better event scoping, not clever metrics
- 4h/24h follow-up on 8 sent alerts — come back when you have 100+

### **DEPRIORITIZE (Build Later)**
- Source usefulness scoring based on historical performance — you need volume first
- Regime filters — you don't know what regimes matter yet
- Pre-event price-in detection — this is a nice-to-have for mature signals
- Quality gates beyond basic deduplication — you're filtering air

---

## 3. Historical Replay Strategy

**Stop expanding historical replay right now.**

Your older500 sample is telling you the truth: second-hand news is not a good source for single-asset, actionable events. Exporting more random news will give you more of the same.

Instead:

### **Option A: Targeted Watcher History (Recommended)**
- Export the last 90 days of Ethereum address activity you're already watching
- Export the last 90 days of stablecoin mint/burn events
- Export the last 90 days of Hyperliquid large position changes
- Export the last 30 days of CEX netflow anomalies (if you have them)

**This gives you 100-500 first-hand events with clean asset scope and timestamps.**

Run replay on this. These are the events you claim to care about. If they don't show price impact, your thesis is wrong.

### **Option B: Targeted Asset/Event Queries (Secondary)**
Only if Option A shows promise:
- Query for single-asset token unlocks (you found 1 XRP event — there should be 50+ in 2024)
- Query for single-asset network upgrades (ETH, SOL, AVAX, etc.)
- Query for single-asset hack/exploit events (these are rare but high-signal)

**Do not export more macro news. You already know it's not useful.**

---

## 4. Handling BTC/Macro Domination

**Stop trying to fix this in post-processing.**

BTC/macro domination is a source selection problem:
- News APIs surface macro narratives because that's what gets clicks
- If you want single-asset alpha, you need single-asset sources

Concrete fixes:

### **Immediate (This Week)**
- Add a **source_type** field: `news_api`, `onchain_watcher`, `cex_flow`, `social_signal`
- Track what % of your sent alerts come from each source type
- Set a target: "50% of alerts should be first-hand sources within 30 days"

### **Tactical (Next 2 Weeks)**
- For news-sourced events:
  - Hard filter: if `scope == "market_wide"` and `event_type == "macro"`, require abnormal return > 5% to alert
  - Soft filter: if `primary_asset == "BTC"` and `event_type in ["macro", "other"]`, deprioritize unless magnitude is extreme
- For first-hand events:
  - Allow lower abnormal return thresholds (2-3%) because timing is better

### **Strategic (Next Month)**
- Accept that BTC macro news is low-signal for your use case
- Build separate feeds:
  - **"Market Moves"** — BTC/ETH macro, low frequency, high bar
  - **"On-Chain Intel"** — first-hand watcher events, higher frequency, lower bar
  - **"Altcoin Events"** — single-asset non-BTC, curated event types

---

## 5. Source Quality Loop Without User Reactions

You're right that user reactions are unreliable. Here's a better loop:

### **Tier 1: Automated Follow-Up (Build This Week)**

For each sent alert, calculate at T+4h, T+24h, T+72h:
- Abnormal return magnitude
- Volatility spike (did something happen?)
- Volume spike (did traders care?)
- Directional consistency (did the move sustain?)

**Aggregate by source:**
```
source_name | alerts_sent | avg_4h_abs_return | avg_24h_abs_return | vol_spike_rate | sustain_rate
CryptoNews  | 45          | 1.2%              | 0.8%               | 22%            | 15%
OnChainBot  | 23          | 3.1%              | 2.4%               | 48%            | 35%
```

**Decision rule:**
- If a source has >20 alerts and avg_24h_abs_return < 1.5% and vol_spike_rate < 20%, **downrank or cut it**
- If a source has >10 alerts and avg_24h_abs_return > 3% and sustain_rate > 30%, **prioritize it**

### **Tier 2: Manual Spot Checks (Weekly)**

Every Monday:
- Pull 10 random sent alerts from the past week
- For each, manually answer:
  - Was this timely? (Did we beat the market?)
  - Was this readable? (Could I scan it in 5 seconds?)
  - Was this actionable? (Did I know what asset/direction to watch?)
  - Was this novel? (Or did I already know this from Twitter/Discord?)

Track these as boolean flags. If <50% are "yes" on any dimension, you have a product problem.

### **Tier 3: Source Concentration (Build Next Week)**

Track:
- How many alerts per source per day?
- How many sources contribute 80% of alerts?

**Red flags:**
- One source sends >40% of all alerts → you're too dependent
- One source sends >5 alerts/day → it's probably noisy
- 80% of alerts come from <3 sources → you don't have diversification

---

## 6. First-Hand Intelligence Sources to Prioritize

You need to 3x your first-hand sources in the next 30 days. Here's the priority order:

### **Week 1-2: Expand Existing Watchers**

**Ethereum Address Watchers (High Priority)**
- Add top 20 CEX cold wallets (Binance, OKX, Bybit, etc.)
- Add top 10 stablecoin treasury addresses (USDT, USDC)
- Add top 5 DeFi protocol treasuries (Uniswap, Aave, Maker)
- Add known whale addresses (use Arkham or Nansen lists)

**Stablecoin Mint/Burn (High Priority)**
- You have this — expand to USDT, USDC, DAI, FDUSD
- Add threshold: only alert if mint/burn > $50M

**Hyperliquid Positions (Medium Priority)**
- You have this — tune the "large position" threshold
- Add: position liquidation alerts (these are often leading indicators)

### **Week 3-4: New Watcher Types**

**Token Unlock Calendar (High Priority)**
- Scrape or API: TokenUnlocks.app, Messari unlocks, project docs
- Alert 24h before unlock if unlock > 2% of circulating supply
- This is **pure alpha** — unlocks are scheduled, predictable, and often move prices

**CEX Listing Announcements (High Priority)**
- Monitor Binance, OKX, Bybit announcement channels (they have RSS/APIs)
- Alert within 60 seconds of listing announcement
- This is **pure alpha** — listing announcements are 10-30% moves

**Large Liquidations (Medium Priority)**
- Use Coinglass API or Hyperliquid API
- Alert if liquidation cascade > $10M in 1 hour
- Useful for volatility context

**GitHub Activity (Low Priority for Now)**
- Monitor commits/releases for top 20 protocols
- Only useful if you can filter for "material" changes (hard problem)

### **Do Not Build Yet**
- Social sentiment analysis (noisy, expensive, low edge)
- Funding rate alerts (already priced in by the time you see it)
- Orderbook imbalance (requires low-latency infra you don't have)
- Mempool monitoring (too noisy, too technical for your user)

---

## 7. TG Feed User Experience

### **Timing**
- **Realtime alerts:** 9:00 - 23:00 China time (UTC+8)
  - No alerts during sleep hours (23:00 - 9:00) unless magnitude is extreme (>10% move)
- **Digests:** 9:30, 13:00, 21:00 China time
  - Morning: what happened overnight (US/EU session)
  - Noon: mid-day check-in
  - Evening: what happened today, what to watch tonight

### **Frequency**
- **Realtime:** Max 1 alert per 30 minutes (current rate limit is good)
- **Digests:** Always send, even if empty (say "quiet period, no major events")

### **Digest vs Realtime**

**Realtime (Interrupt-Worthy):**
- CEX listing announcement
- Large stablecoin mint (>$100M)
- Whale wallet moves (>$10M)
- Liquidation cascade (>$20M)
- Token unlock (>5% supply)

**Digest (Contextual Summary):**
- CEX netflow trends (24h summary)
- Hyperliquid position changes (top 5 by size)
- Binance long/short ratio shifts
- Macro news roundup (only if significant)
- Smaller events that didn't meet realtime bar

### **Message Format**

**Realtime Alert Template:**
```
🔴 [Event Type] | [Asset]

[Chinese headline - 1 line, <50 chars]
[English headline - 1 line]

📊 Context:
• [Key metric 1]
• [Key metric 2]
• [Key metric 3]

⏰ [Timestamp]
🔗 [Source link if available]
```

**Example:**
```
🔴 大额铸币 | USDT

Tether 铸造 2 亿 USDT
Tether minted 200M USDT

📊 Context:
• 24h total mints: 350M
• 7d avg: 120M/day
• Last large mint: 3 days ago (+180M)

⏰ 2024-01-15 14:23 UTC+8
```

**Digest Template:**
```
📅 [Time Period] 市场情报 | Market Intel

━━━━━━━━━━━━━━━━
🔥 重点事件 | Key Events
━━━━━━━━━━━━━━━━

1. [Event 1 - Chinese + English, 2 lines max]
2. [Event 2]
3. [Event 3]

━━━━━━━━━━━━━━━━
📈 资金流向 | Flows
━━━━━━━━━━━━━━━━

• BTC: [netflow summary]
• ETH: [netflow summary]
• Stables: [mint/burn summary]

━━━━━━━━━━━━━━━━
⚖️ 持仓数据 | Positions
━━━━━━━━━━━━━━━━

• Binance多空比: [ratio + change]
• Hyperliquid大户: [top 3 changes]

━━━━━━━━━━━━━━━━
⏰ 下一时段关注 | Watch Next
━━━━━━━━━━━━━━━━

• [Upcoming unlock/event 1]
• [Upcoming unlock/event 2]
```

### **Chinese Readability**
- **Always lead with Chinese for event headlines** (your users are China-based)
- Use English for technical terms (CEX, DeFi, TVL) — these are standard in Chinese crypto community
- Use emojis sparingly but consistently (🔴 for urgent, 📊 for data, ⏰ for time)
- Keep lines short (<60 chars) — mobile Telegram is narrow

### **Useful vs Annoying**

**Useful:**
- Tells me something I don't know yet
- Gives me context (is this normal or unusual?)
- Gives me a number (how big is this?)
- Gives me timing (when did this happen? when will it happen?)

**Annoying:**
- Tells me to buy or sell (I'll decide)
- Gives me obvious news I saw on Twitter 2 hours ago
- Gives me vague macro commentary ("Fed may hike rates")
- Sends me 5 alerts in 10 minutes

---

## 8. Morning/Noon/Evening Digests

**Yes, this is sensible. Keep them.**

### **Morning Digest (9:30 China Time)**
**Purpose:** Catch up on overnight (US/EU session)

**Contents:**
- Top 3 events from past 12 hours (23:00 yesterday - 9:00 today)
- CEX netflow summary (BTC, ETH, major alts)
- Stablecoin mint/burn summary
- Upcoming events today (unlocks, announcements)

**Tone:** Informational, not urgent. "Here's what you missed."

### **Noon Digest (13:00 China Time)**
**Purpose:** Mid-day check-in

**Contents:**
- Morning session recap (9:00 - 13:00)
- Binance long/short ratio + change from morning
- Hyperliquid position changes (if significant)
- Afternoon watch list (events expected 13:00 - 18:00)

**Tone:** Quick update. "Here's where we are."

**Optimization:** This one is least critical. If nothing happened 9:00-13:00, consider skipping it or making it very short.

### **Evening Digest (21:00 China Time)**
**Purpose:** End-of-day summary + overnight watch list

**Contents:**
- Top 5 events from today (9:00 - 21:00)
- Daily CEX netflow summary (24h totals)
- Daily stablecoin mint/burn summary (24h totals)
- Overnight watch list (US session events, unlocks, scheduled announcements)
- Macro calendar (Fed, CPI, etc. if next day)

**Tone:** Comprehensive. "Here's the full picture."

---

## 9. Metrics That Actually Matter

Forget "alert quality score." Here's what matters for a Telegram intelligence product:

### **Tier 1: Engagement (Proxy Metrics)**

You can't rely on reactions, but you can measure:

1. **Subscriber retention**
   - How many users are still in the channel after 7 days? 30 days?
   - Target: >80% retention at 30 days

2. **Read rate (if you can measure it)**
   - Telegram doesn't give you read receipts, but you can infer from:
     - Do users stay in the channel? (They leave if it's useless)
     - Do users forward messages? (Telegram tells you this)
   - Target: >5% of messages get forwarded

3. **Growth rate**
   - Are users inviting others?
   - Target: 10% month-over-month organic growth

### **Tier 2: Timeliness**

4. **Time-to-alert**
   - For first-hand events (on-chain, CEX announcements), how fast do you alert after the event?
   - Target: <60 seconds for CEX listings, <5 minutes for on-chain events

5. **Freshness**
   - What % of alerts are about events that happened <15 minutes ago?
   - Target: >60% of realtime alerts are <15min old

### **Tier 3: Signal Quality**

6. **Abnormal return follow-up**
   - Avg absolute abnormal return at T+4h, T+24h
   - Target: >2.5% at T+4h, >2% at T+24h (this means your alerts correlate with moves)

7. **Volatility spike rate**
   - What % of alerts are followed by a volatility spike (>2x normal) within 4h?
   - Target: >30%

8. **Source diversity**
   - What % of alerts come from first-hand sources?
   - Target: >50% within 30 days

### **Tier 4: User Experience**

9. **Digest consistency**
   - Do digests send on time every day?
   - Target: 100% (this is table stakes)

10. **Rate limit compliance**
    - Are you staying under 1 alert per 30min?
    - Target: 100% (never spam)

### **What NOT to Measure (Yet)**

- User reactions (unreliable)
- Profitability of trades (you're not a trading bot)
- Prediction accuracy (you're not making predictions)
- Sentiment scores (too noisy, too subjective)

---

## 10. Next 7 Days Focus

### **Day 1-2: Source Expansion**
- [ ] Add top 20 CEX cold wallet addresses to Ethereum watcher
- [ ] Add USDT/USDC/DAI mint/burn watchers (if not already comprehensive)
- [ ] Add Binance/OKX/Bybit listing announcement monitors (RSS or API)
- [ ] Add token unlock calendar scraper (TokenUnlocks.app or manual CSV)

**Deliverable:** 4 new first-hand sources feeding into event pipeline

### **Day 3-4: Watcher History Replay**
- [ ] Export last 90 days of Ethereum address activity
- [ ] Export last 90 days of stablecoin mint/burn
- [ ] Export last 90 days of Hyperliquid position changes
- [ ] Run replay on these (should be 100-300 events)
- [ ] Generate abnormal return summary by event type

**Deliverable:** Replay report showing which first-hand event types have price impact

### **Day 5-6: Source Quality Loop**
- [ ] Build automated follow-up script (T+4h, T+24h, T+72h)
- [ ] Calculate abnormal return, volatility spike, volume spike for each sent alert
- [ ] Aggregate by source
- [ ] Generate source quality report

**Deliverable:** Source quality dashboard (CSV or simple HTML)

### **Day 7: Manual Spot Check + Adjust**
- [ ] Pull 10 random sent alerts from past week
- [ ] Manually review: timely? readable? actionable? novel?
- [ ] Adjust message templates if needed
- [ ] Adjust source filters if needed

**Deliverable:** User experience audit doc + template updates

---

## 11. Next 30 Days Focus

### **Week 1: Source Expansion (see above)**

### **Week 2: Quality Loop Automation**
- [ ] Automate source quality report (runs daily, outputs to CSV)
- [ ] Add source concentration tracking (alerts per source per day)
- [ ] Add source diversity metric (% first-hand vs news)
- [ ] Set up weekly manual spot check process

### **Week 3: Message Format Refinement**
- [ ] A/B test message templates (if you have multiple users)
- [ ] Refine Chinese translations (get native speaker review)
- [ ] Add "why this matters" context to each event type
- [ ] Standardize emoji usage

### **Week 4: New Event Types**
- [ ] Add CEX listing announcements (if not done Week 1)
- [ ] Add token unlock alerts (if not done Week 1)
- [ ] Add large liquidation alerts (Coinglass API)
- [ ] Add GitHub release monitoring for top 10 protocols (optional)

### **Ongoing: Metrics Tracking**
- [ ] Set up daily metrics log: alerts sent, sources used, avg abnormal return, rate limit compliance
- [ ] Set up weekly metrics review: subscriber retention, source diversity, timeliness
- [ ] Set up monthly metrics review: growth rate, forward rate, user feedback

---

## 12. What NOT to Build Yet

**Do not build these until you have 100+ sent alerts and clear user feedback:**

- [ ] ~~Regime filters~~ (you don't know what regimes matter)
- [ ] ~~Pre-event price-in detection~~ (premature optimization)
- [ ] ~~ML-based event classification~~ (you don't have training data)
- [ ] ~~Sentiment analysis~~ (noisy and expensive)
- [ ] ~~Multi-language support beyond Chinese/English~~ (focus on core users)
- [ ] ~~Web dashboard~~ (Telegram is your product)
- [ ] ~~User preference settings~~ (you don't know what preferences matter yet)
- [ ] ~~Historical performance leaderboard~~ (vanity metric)
- [ ] ~~Backtesting UI~~ (you're not a trading platform)
- [ ] ~~API for third-party access~~ (you don't have a product yet)

**Also do not:**
- [ ] ~~Expand historical replay beyond first-hand watcher events~~ (you've learned what you need from news data)
- [ ] ~~Build complex benchmark switching logic~~ (solve with better event scoping)
- [ ] ~~Add more macro news sources~~ (you have too much already)

---

## 13. AI Review/Classification: Where and How

**Use AI sparingly. It's expensive and often wrong.**

### **Where to Use AI**

**1. Event Headline Translation (High Value)**
- Use: GPT-4o-mini or Claude Haiku
- Task: Translate English headlines to natural Chinese
- Cost: ~$0.0001 per translation
- Volume: ~50-100 translations/day = $0.01/day
- **Worth it:** Yes, if you don't have a native Chinese speaker on the team

**2. Event Type Classification (Medium Value)**
- Use: GPT-4o-mini with structured output
- Task: Classify ambiguous events into taxonomy (only when rule-based fails)
- Cost: ~$0.0005 per classification
- Volume: ~10-20 classifications/day = $0.01/day
- **Worth it:** Maybe, but try rule-based first (keywords, source patterns)

**3. "Why This Matters" Context Generation (Low Value for Now)**
- Use: GPT-4o
- Task: Generate 1-2 sentence explanation of why an event is significant
- Cost: ~$0.002 per generation
- Volume: ~50 events/day = $0.10/day
- **Worth it:** Not yet. Write templates manually for common event types first.

### **Where NOT to Use AI**

- ~~Relevance scoring~~ (use rule-based + abnormal return)
- ~~Source quality assessment~~ (use automated follow-up metrics)
- ~~Event deduplication~~ (use fuzzy matching on title + timestamp)
- ~~Sentiment analysis~~ (noisy and expensive)
- ~~Trade signal generation~~ (not your product)

### **Cost Control**

**Budget: <$5/day for AI calls**

- Set hard rate limits: max 100 GPT-4o-mini calls/day, max 10 GPT-4o calls/day
- Cache translations (same headline → same translation)
- Batch API calls where possible (translate 10 headlines in one call)
- Use cheapest model that works (Haiku > GPT-4o-mini > GPT-4o)
- Monitor cost daily, alert if >$5/day

**Implementation:**
```python
# Simple cost tracking
ai_calls_today = {
    "gpt-4o-mini": 0,
    "gpt-4o": 0,
    "claude-haiku": 0
}

def call_ai(model, prompt):
    if ai_calls_today[model] >= DAILY_LIMIT[model]:
        return None  # Fail gracefully
    ai_calls_today[model] += 1
    # ... make API call
```

---

## 14. How to Tell If You Have a Useful First Version

**You have a useful first version when:**

### **Quantitative Signals**

1. **Volume:** You're sending 10-20 alerts/day consistently
2. **Diversity:** >50% of alerts are from first-hand sources (not news APIs)
3. **Timeliness:** >60% of alerts are <15min old when sent
4. **Impact:** Avg absolute abnormal return at T+4h is >2.5%
5. **Consistency:** Digests send on time 100% of days
6. **Retention:** >80% of subscribers stay after 30 days

### **Qualitative Signals**

7. **User feedback:** At least 3 users tell you (unprompted) "this is useful"
8. **Forwarding:** Users forward your messages to other groups/people
9. **Novelty:** You regularly alert on events before you see them on Twitter
10. **Clarity:** You can explain in 30 seconds what your product does and why it matters

### **Operational Signals**

11. **Stability:** System runs for 7 days without manual intervention
12. **Coverage:** You have watchers for at least 5 different event types
13. **Quality loop:** You review source quality weekly and make adjustments

### **The Real Test**

**Would you personally pay $50/month for this feed?**

If no, you don't have a useful first version yet.

If yes, you're ready to:
- Invite 10 friends/colleagues to test
- Ask for honest feedback (not "this is cool" but "I would/wouldn't pay for this because...")
- Iterate based on feedback
- Consider charging (even $10/month filters for serious users)

---

## Final Thoughts

**You're 60% of the way to a useful product, but you're spending 80% of your time on the wrong 40%.**

Your infrastructure is solid. Your backtesting apparatus is overbuilt. Your source diversity is weak.

**The path forward is simple:**
1. **Week 1-2:** Add 5+ first-hand sources (CEX listings, unlocks, whale wallets)
2. **Week 3-4:** Run quality loop on real sent data (not historical replay)
3. **Day 30:** Decide if you have enough signal to continue or if you need to pivot

**If after 30 days:**
- You're sending <5 alerts/day → you don't have enough sources
- Avg abnormal return at T+4h is <1.5% → your events don't matter
- Users are leaving the channel → your UX is broken

**If after 30 days:**
- You're sending 10-20 alerts/day → good volume
- Avg abnormal return at T+4h is >2.5% → your events have impact
- Users are staying and forwarding → you have product-market fit

**Then and only then:** build the nice-to-haves (regime filters, price-in detection, ML classification).

**Stop backtesting. Start shipping.**
