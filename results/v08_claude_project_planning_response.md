# Claude v0.8 Project Planning Response

# Blunt Diagnosis

## The 5 Biggest Wrong Assumptions

1. **You're building a research platform when you need a trading edge product.** Your backtest pipeline is academic theater. Crypto traders don't care about "abnormal returns vs BTC/ETH" in a PDF—they want to know "Tether just minted $1B, here are the 3 tokens that pumped in the last 4 times this happened, watch SOL/AVAX/MATIC in the next 2 hours."

2. **You're treating all signal sources equally when CEX netflow and Hyperliquid are 10x more valuable than the rest.** You admitted it yourself. Stop pretending funding rates and Aave liquidations matter at the same tier. They don't. Cut them or make them footnotes.

3. **The Telegram feed structure is backwards.** You're sending "high-priority alerts" + digests, but you haven't defined what makes something high-priority based on *user action*, only your internal scoring. You're optimizing for coverage, not for trade-worthiness.

4. **You're collecting feedback but probably not acting on it fast enough.** TG feedback collection is nice. But if you don't have a weekly "what got ignored vs what got acted on" report driving your priority queue, it's just logging.

5. **The morning/noon/evening digest has no clear job.** Is it a recap? A trade setup preview? A "here's what mattered" summary? Without a specific user outcome, it's just a newsletter no one reads.

---

## What To Build In The Next 7 Days

### Day 1-2: Ruthless Signal Triage
- **Audit last 30 days of sent alerts.** Tag each one:
  - Did it have a clear trade implication within 4 hours?
  - Did any user react/comment?
  - Was it actionable or just "interesting"?
- **Output:** A spreadsheet ranking your sources by "led to user engagement" and "had price impact >2% in 4h."

### Day 3-4: Rebuild Alert Priority Logic
- **Redefine "high-priority" as:**
  - CEX netflow crosses 2-sigma threshold for a top-20 token
  - Hyperliquid whale position >$5M opened/changed/near liquidation
  - USDT/USDC mint >$500M
  - (Optional) Binance long/short ratio flips >10% in 1 hour for BTC/ETH
- **Everything else goes to digest-only or gets dropped.**

### Day 5-6: Hyperliquid + CEX Netflow "Playbook" Messages
- When a Hyperliquid whale opens a $10M long on SOL, don't just say "Whale opened $10M long on SOL."
- Say:
  - "🐋 $10M SOL long opened on Hyperliquid at $X. Last 3 times a >$8M long appeared, SOL moved +Y% in Z hours. Current price: $X. Watch for: [specific level]."
- **Ship this format for your top 2 sources only.**

### Day 7: Kill or Defer
- **Disable:** Aave liquidation alerts, funding rate alerts (unless you see clear user demand).
- **Defer:** All backtest PDF generation, entity attribution cleanup, taxonomy expansion.
- **Keep running but don't improve:** News ingestion (just keep it alive).

---

## What To Explicitly Stop Building

1. **Backtest reports with statistical rigor.** You don't have enough samples, and traders don't read them. Stop.
2. **Entity/asset attribution cleanup for old news.** It's a data science tar pit. Freeze it.
3. **Broad event-type bucketing.** You're not building a research taxonomy. You're building a trade signal product.
4. **Any new source integration.** You have 7 sources and only 2 are working. Fix those first.
5. **Digest formatting experiments.** Lock the format for 2 weeks and measure engagement, don't keep tweaking it.

---

## Which First-Hand Sources To Prioritize

### Tier 1 (double down):
1. **CEX netflow** – This is pure order flow. If you can detect $50M flowing into Binance for a mid-cap token, that's alpha.
2. **Hyperliquid large positions** – Transparent whale tracking. This is gold.

### Tier 2 (keep alive, low maintenance):
3. **USDT/USDC mints** – Macro liquidity signal. Easy to track, low noise.
4. **Binance long/short ratio** – Only for BTC/ETH, only for sharp moves.

### Tier 3 (disable or make digest-only):
5. **Funding rates** – Too slow, too noisy.
6. **Aave liquidations** – Lagging indicator, not predictive.
7. **Watched Ethereum addresses** – Only useful if you have a curated list of 10-20 known whale/insider addresses. Otherwise, noise.

---

## How Telegram Should Be Structured

### Real-Time Channel:
- **Only Tier 1 signals.**
- Max 3-5 messages per day.
- Each message must answer: "What happened? What does it mean? What should I watch?"

### Digest Channel (or same channel, clearly marked):
- **Morning (9 AM China):** "Here's what happened overnight + top 3 setups to watch today."
- **Evening (9 PM China):** "Here's what moved today + why + what it means for tomorrow."
- **No noon digest.** It's redundant.

### Feedback Loop:
- After every real-time alert, auto-post a follow-up 4 hours later: "Update: [token] moved X%. Here's what happened."
- Ask users to react with 👍 (useful), 👎 (noise), or 💰 (traded it).

---

## How Digests Should Differ From Alerts

| **Real-Time Alerts** | **Digests** |
|----------------------|-------------|
| Single event, immediate | Synthesis of 6-12 hours |
| "This just happened" | "Here's what mattered" |
| Actionable in next 1-4 hours | Contextual, educational, forward-looking |
| Tier 1 sources only | Can include Tier 2 + curated news |
| No more than 5/day | Exactly 2/day (morning, evening) |

**Morning Digest:**
- Overnight CEX flows, Hyperliquid changes, major mints.
- "Watch these 3 tokens today: [why]."

**Evening Digest:**
- What moved >5% today and why.
- Hyperliquid position updates.
- "Tomorrow's setup: [thesis]."

---

## Metrics That Decide If This Works

### Week 1-2 (Engagement):
- % of alerts that get user reactions (target: >40%)
- % of alerts followed by user comments (target: >20%)
- Daily active users reading messages (track via TG analytics)

### Week 3-4 (Usefulness):
- User self-reported: "Did you trade based on this?" (poll after each alert)
- % of alerts where price moved >2% in predicted direction within 4h (target: >60%)

### Month 2 (Retention):
- Weekly active users (target: grow 10% week-over-week)
- Paid conversion if you add a premium tier (target: 5% of active users)

### Red Flag Metrics:
- If >30% of alerts get 👎 reactions, you're spamming.
- If <10% of users open digests, they're useless.

---

## What Stays In The Backtest Pipeline

**Keep:**
- Price backfill (you need this to validate signals).
- 4h/24h follow-up reports (this is your ground truth).
- Time provenance audit (proves you're not cheating).

**Kill:**
- Event candidate extraction (you're not doing NLP research).
- Entity/taxonomy scoring (not your job).
- Quality reports (replace with simple "did price move?" check).

**Replace:**
- Instead of "abnormal return vs BTC/ETH," just track: "In the 4 hours after this signal, did [token] move >2%? >5%? In which direction?"

---

## Architecture In 30 Days

```
┌─────────────────────────────────────────┐
│  Data Ingestion (Minimal)              │
│  - CEX netflow (live)                   │
│  - Hyperliquid API (live)               │
│  - USDT/USDC mints (live)               │
│  - Binance long/short (live)            │
│  - News feed (keep alive, low priority) │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  Signal Scoring Engine                  │
│  - Threshold logic (2-sigma, $5M, etc.) │
│  - Playbook templates (last 3 times...) │
│  - Deduplication (1 alert per token/4h) │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  Telegram Sender                        │
│  - Real-time (Tier 1 only)              │
│  - Digests (morning/evening)            │
│  - Follow-up posts (4h later)           │
│  - Reaction collection                  │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  Feedback Loop                          │
│  - Weekly "what worked" report          │
│  - Threshold tuning based on reactions  │
│  - Source priority adjustment           │
└─────────────────────────────────────────┘
```

**Tech:**
- Keep SQLite for now (it's fine for 10K events/day).
- Move to Postgres only if you hit performance issues.
- No Kafka, no microservices, no Docker orchestration. You're not there yet.

---

## Simplest Credible MVP For A Crypto Trader

**A Telegram channel that posts:**

1. **3-5 real-time alerts per day:**
   - "🐋 $12M ETH long opened on Hyperliquid at $3,240. Last 3 times this happened, ETH moved +3.2% avg in 4h. Watch $3,280."

2. **2 digests per day:**
   - Morning: "Overnight: $800M flowed into Binance BTC wallets. Watch for resistance at $45K. Hyperliquid: 2 new SOL longs, 1 closed. Today's watch list: BTC, SOL, AVAX."
   - Evening: "Today: BTC +2.1% (netflow was the tell). SOL -1.2% (whale closed). Tomorrow: Watch USDC mint scheduled, historically bullish for ETH."

3. **Follow-up posts 4 hours after each alert:**
   - "Update: ETH hit $3,285 (+1.4%). Whale position still open."

**That's it.** No PDFs, no backtests, no entity graphs. Just actionable signals with context.

---

## What To Do This Week

### Monday-Tuesday:
- [ ] Audit last 30 days of alerts (engagement + price impact)
- [ ] Rank sources by usefulness
- [ ] Write down new "high-priority" definition

### Wednesday-Thursday:
- [ ] Rebuild alert logic (Tier 1 only)
- [ ] Write playbook message templates for CEX netflow + Hyperliquid
- [ ] Disable Aave + funding rate alerts

### Friday:
- [ ] Ship new alert format to Telegram
- [ ] Set up 4h follow-up auto-posts with reaction buttons
- [ ] Schedule only morning + evening digests (kill noon)

### Weekend:
- [ ] Watch user reactions
- [ ] Manually tune thresholds based on feedback
- [ ] Write a 1-page "what we learned" doc

---

## What NOT To Do This Week

- ❌ Don't touch the backtest pipeline
- ❌ Don't add new sources
- ❌ Don't clean up old news data
- ❌ Don't build a web dashboard
- ❌ Don't write documentation
- ❌ Don't refactor code (unless it's blocking the above)

---

## Product Risks

1. **You're building for yourself, not users.** If you're the only one who understands the alerts, you've failed.
2. **Crypto moves fast; your feedback loop is too slow.** You need daily iteration, not weekly.
3. **You might be too late.** If 10 other groups are doing this, you need a sharper edge (probably Hyperliquid + CEX netflow fusion).

---

## Engineering Risks

1. **Scope creep.** You'll be tempted to add sources, improve backtests, build dashboards. Don't.
2. **Premature optimization.** SQLite is fine. Python is fine. Don't rewrite in Rust.
3. **Data quality obsession.** You'll never have perfect entity attribution. Ship with 80% accuracy and iterate.

---

## Final Word

You have two sources that matter (CEX netflow, Hyperliquid) and a Telegram channel. Everything else is distraction. 

**Your job this week:** Prove that 3-5 alerts per day can make a trader money. If you can't do that, nothing else matters.

Stop building infrastructure. Start proving value.
