# Claude Response

- generated_at: 2026-05-27 16:38:23 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_NEXT_PROMPT.md
- prompt_sha256_16: 46c573c780a900fd

# External Review: Crypto Event Intelligence

## Executive Summary

**Product Direction**: Fundamentally sound. You're building a human-augmented intelligence filter, not a trading signal generator. The conservative approach (no auto-execution, human review gates) is correct for this domain.

**Current State**: You have a working pipeline but are stuck in quality perfectionism before shipping anything user-facing. The TG draft delay is becoming analysis paralysis.

**Critical Issue**: You're over-engineering the backtest validation when you should be shipping a minimal TG pilot to validate the product hypothesis. The 37-event backtest with 38% discard rate tells you the pipeline works but needs tuning - that's enough to start learning from real users.

---

## 1. Three Assumptions I Disagree With Most

### A. "Backtest statistical readiness is required before TG drafts"

**Why this is wrong**: You're building an intelligence feed, not a quantitative trading strategy. The backtest's purpose should be to catch catastrophic failures (wrong timestamps, broken price data, systematic entity misattribution), not to prove event-type performance with statistical significance.

**What you should do instead**: 
- Use backtest as a **smoke test** only: Does the pipeline produce reasonable event times, valid symbols, and sensible price windows?
- Ship TG drafts to a private test group with 10-20 events/week and measure: Did humans find these interesting? Were any completely wrong? What % would they want to trade on?
- The real "backtest" is whether domain experts find your events actionable.

**Evidence from your data**: You have 22 "clean low-risk" events that passed backtest. That's enough for a 2-week pilot. Waiting for 200+ events with <8.5% review rate is premature optimization.

---

### B. "Manual review required rate of 6.47% is still too fragile for TG drafts"

**Why this is wrong**: You're conflating two different quality bars:
1. **Labeling quality** (for training the AI classifier) - needs high precision
2. **Publishing quality** (for TG output) - needs high recall of valuable events, tolerates some noise

Your current 6.47% review rate is **excellent** for a pilot. In production content moderation systems, 5-10% manual review is standard even at scale.

**What you should do instead**:
- Accept that 5-10% manual review is the **steady state**, not a temporary problem
- Build the TG draft workflow with a manual approval queue baked in
- Focus on reducing review **latency** (can you clear the queue in <30min daily?) rather than review **rate**

**The real risk**: Not that 6.47% is too high, but that you don't have a fast human review workflow. If reviewing 13 events takes 2 hours, that's the bottleneck - not the percentage.

---

### C. "Protocol exploit events need primary-asset policy resolution before use"

**Why this is wrong**: You're trying to create a perfect taxonomy before you understand user needs. The 5 exploit events in your review packet are **obviously valuable** regardless of whether you tag them as ETH, BTC, or the protocol token.

**What you should do instead**:
- Tag exploits with **all relevant assets** (protocol token, chain, stolen asset) as a list
- Let the TG draft show all tags: "🚨 Exploit: Echo Protocol (Monad/ETH) - $76M"
- After 20-30 exploit events, you'll see which asset users actually care about for trading decisions
- **Then** formalize the primary-asset rule based on real feedback

**Why this matters**: You're blocking 5 high-value events over a taxonomy question that users might not even care about. Ship it tagged as "ETH + protocol exploit" and iterate.

---

## 2. Five Highest-Priority Actions Now

### Priority 1: Ship Minimal TG Pilot This Week ⚡
**What**: 
- Take the 22 "clean low-risk" events
- Write a simple TG draft template: `[Event Type] [Asset] [Title] [Link] [Time]`
- Post to a private TG group (just you, or +2 trusted users)
- Run for 2 weeks, 5-10 events/week

**Why**: You need to validate the product hypothesis. Is this feed actually useful? You cannot answer this with more backtests.

**Acceptance criteria**: 
- 3 users review events daily
- Collect feedback: "Would trade on this: Y/N", "Interesting but not actionable", "Noise"
- If >50% of events are marked "interesting or actionable", proceed to v0.7

**Blocks removed**: Ignore backtest statistical readiness, ignore 8.5% review rate target, ignore exploit primary-asset policy.

---

### Priority 2: Collapse `other_review` Into Explicit Reject Reasons
**What**: 
- Split `other_review` (210 rows) into:
  - `reject_non_crypto` (traditional finance, non-blockchain)
  - `reject_weak_signal` (too vague, no clear catalyst)
  - `reject_bad_entity` (entity extraction failed, mostly footer text)
- Re-label 30 random `other_review` rows to calibrate the split

**Why**: "Other" is a taxonomy smell. It hides systematic misclassification. Your 210 `other_review` rows are probably 3-4 distinct failure modes that need different fixes.

**Impact**: This will likely reveal that 50-100 rows are actually `reject_bad_entity` from scraper pollution, which is a data pipeline fix, not a classification problem.

---

### Priority 3: Add Multi-Asset Tagging for Exploits and Macro Events
**What**:
- Change `primary_asset_symbol` from single string to `asset_symbols: List[str]`
- For exploits: tag protocol token + chain + stolen asset
- For macro/regulation: tag all mentioned assets or use `["BTC", "ETH"]` as market proxy
- Update TG draft template to show all tags

**Why**: Forcing single-asset attribution for multi-asset events is causing your review backlog. Many events (exploits, regulations, macro) are inherently multi-asset.

**Example**:
```
🚨 Exploit: Echo Protocol
Assets: MONAD, ETH, eBTC
Loss: $76M
Time: 2026-05-20 14:23 UTC+8
```

Users can decide which asset matters for their portfolio.

---

### Priority 4: Implement Fast Manual Review Workflow
**What**:
- Build a simple review UI (even a CSV + Python script):
  - Show event title, asset, type, AI confidence
  - 3 buttons: Approve, Reject, Flag for policy review
  - Target: <2min per event, <30min for daily queue
- Measure review latency, not just review rate

**Why**: If your 13-event review queue takes 3 hours, you'll never scale. If it takes 20 minutes, 6.47% review rate is fine.

**Acceptance criteria**: You can clear a 20-event queue in <30min.

---

### Priority 5: Separate Macro/Market-Wide Events Into Different TG Channel
**What**:
- Create two TG output streams:
  1. **Alpha channel**: Single-asset events (listings, exploits, partnerships, unlocks)
  2. **Macro channel**: Market-wide events (ETF flows, regulations, Fed policy)
- Route `event_scope=market_wide` → macro channel

**Why**: These serve different use cases:
- Alpha channel: "Should I trade THIS asset now?"
- Macro channel: "Should I trade AT ALL today?"

Mixing them dilutes both signals. Your current `macro_policy` holdout (27 rows) suggests you already know these are different.

**User benefit**: Users can subscribe to one or both based on their strategy (scalper vs. swing trader).

---

## 3. Concrete Recommendations Per Question

### Q1: TG publishing - auto_publish vs human_review approval?
**Recommendation**: Start with **human approval queue only**. No auto_publish for first 100 TG events.

**Reason**: You need to calibrate what "interesting" means in production. After 100 human-approved events, you'll see patterns (e.g., "all exchange listings get approved, all KOL opinions get rejected"). Then build auto_publish rules.

**Timeline**: Enable auto_publish after 100 manually approved events + 90% approval rate on AI suggestions.

---

### Q2: Macro events - same stream or separate?
**Recommendation**: **Separate channels** (see Priority 5).

**Routing rule**:
- `event_scope=market_wide` OR `event_type=regulation_macro` → Macro channel
- `event_scope=single_asset` → Alpha channel
- `event_scope=multi_asset` → Alpha channel if <5 assets, else Macro channel

**Rationale**: A trader watching SOL doesn't care about ETF flows every hour. But a portfolio manager does.

---

### Q3: Benchmark for BTC/ETH events before market basket?
**Recommendation**: Use **BTC as universal benchmark** for all events, even ETH-specific ones.

**Why**: 
- BTC is the market beta. If ETH pumps but BTC pumps more, the "ETH event" didn't matter.
- You already have BTC price data for all timestamps.
- Simple rule: `abnormal_return = (asset_return - btc_return)` over [0h, +4h, +24h].

**When to upgrade**: Only add TOTAL3 or sector baskets when you have 200+ events and see that BTC baseline is systematically wrong (e.g., DeFi events correlate with ETH, not BTC).

---

### Q4: Crypto payment/adoption stories - publishable?
**Recommendation**: **Research-only unless tied to tradable asset**.

**Rule**: 
- "Revolut launches crypto card" → research_only (no tradable catalyst)
- "Revolut adds SOL to crypto card" → publish candidate (SOL is tradable)
- "Visa partners with Circle for USDC settlements" → macro channel (market-wide adoption signal)

**Reason**: Adoption stories are interesting but rarely actionable for short-term trading. Save them for a separate "industry news" channel later.

---

### Q5: Unsupported assets (HYPE/ONDO/WLD) - allow in publish review?
**Recommendation**: **Yes, but route to research_only** until Binance listing.

**Workflow**:
1. Event detected for HYPE → `unsupported_research`
2. If HYPE gets Binance listing → backfill all `unsupported_research` HYPE events → re-score for publish
3. TG draft shows: "⚠️ HYPE (not on Binance yet): [event]"

**Why**: These are leading indicators. HYPE events before listing might predict listing timing. Don't discard them.

---

### Q6: Opinion/analysis from KOLs - ever publishable?
**Recommendation**: **No, unless it's a position disclosure with size**.

**Publish-worthy**:
- "Trader X opened $10M ETH long" (concrete position)
- "Analyst Y predicts ETH to $5K" (opinion, reject)

**Reason**: Opinions are infinite and noisy. Positions with size are rare and actionable (either fade or follow).

**Exception**: If a top-5 KOL (e.g., Arthur Hayes, Cobie) publishes a thesis, that itself moves markets → macro channel.

---

### Q7: Long-form article scraping pollution - how aggressive to discard?
**Recommendation**: **Very aggressive**. Discard any article where entity extraction finds >10 distinct assets.

**Rule**:
```python
if len(detected_entities) > 10 and source_type == "article":
    route = "reject_bad_entity"
```

**Why**: Footer pollution is systematic. A real event article mentions 1-3 assets. If you see 15, it's navigation links.

**Better fix**: Improve scraper to extract only `<article>` or first 500 words. But for now, just reject.

---

### Q8: BTC miner equity / AI data-center stories - part of crypto stream?
**Recommendation**: **Separate "Crypto Equities" channel** (MSTR, COIN, RIOT, HIVE, etc.).

**Why**: 
- These are equity events, not token events (different trading venues, different users)
- Mixing them confuses the asset taxonomy (is MSTR a symbol? No.)
- But they ARE valuable for crypto traders who also trade equities

**Routing**:
- Token events → Alpha channel
- Equity events → Crypto Equities channel (new)
- Macro events → Macro channel

---

### Q9: Enforcement/fraud/Ponzi - taxonomy placement?
**Recommendation**: Create new L1 type: **`legal_enforcement`**.

**Reason**:
- `hack_security` = technical exploit (code vulnerability)
- `regulation_macro` = policy change (new laws, SEC guidance)
- `legal_enforcement` = specific case (arrest, lawsuit, seizure)

These have different implications:
- Hack → affected protocol dumps
- Regulation → market-wide risk-off
- Enforcement → specific exchange/project dumps

**Examples**:
- "Ohio man sentenced for crypto Ponzi" → `legal_enforcement`
- "SEC charges Binance" → `legal_enforcement` (not regulation_macro)
- "EU passes MiCA" → `regulation_macro`

---

### Q10: Minimum standard for auto_publish?
**Recommendation**: **AI confidence >0.85 AND event_type in whitelist AND asset has Binance symbol**.

**Whitelist for auto_publish** (start conservative):
- `exchange_listing`
- `major_unlock` (if unlock_size >5% of circulating supply)
- `hack_security` (if loss >$10M)

**Never auto_publish** (always human review):
- `regulation_macro`
- `partnership_integration` (too subjective)
- `market_moving_trade` (easy to fake)

**Rationale**: Start with objective, high-signal event types. Expand whitelist after 100 events.

---

### Q11: Ground truth for publish quality - who labels, what fields, how many?
**Recommendation**: 
- **Who**: You (domain expert) for first 200 events. Then add 1-2 trusted traders.
- **What fields**: 
  - `publish_decision`: approve / reject / unsure
  - `actionable`: yes / no (would you trade on this?)
  - `reject_reason`: if rejected (noise / duplicate / wrong_asset / too_late)
- **How many**: 200 labeled events minimum before auto_publish. Then 10% ongoing audit.

**Labeling workflow**:
1. AI suggests publish/reject
2. Human reviews and labels
3. Track agreement rate (if >90%, enable auto_publish for that event_type)

---

### Q12: Minimum human audit sampling rate per batch?
**Recommendation**: **20% audit for first 500 events, then 10% ongoing**.

**Breakdown**:
- High-confidence AI labels (>0.9): 10% audit
- Medium-confidence (0.7-0.9): 30% audit
- Low-confidence (<0.7): 100% human review

**Why**: You need to catch systematic errors early (first 500 events), then you can relax to 10% for monitoring.

**Red flag**: If audit finds >5% errors in high-confidence labels, stop auto_publish and retrain.

---

### Q13: High-confidence discard labels - accept directly or require overturn checks?
**Recommendation**: **Accept directly, but sample 5% monthly for overturn check**.

**Workflow**:
- AI labels `discard` with confidence >0.9 → auto-discard
- Every month, randomly sample 20 discarded events → human review
- If >10% should have been published → investigate (new event pattern? taxonomy drift?)

**Why**: High-confidence discards are low-risk. The cost of missing one good event is lower than the cost of reviewing 1000 bad events.

---

### Q14: Human-AI conflict resolution - immediate rule update or batch retraining?
**Recommendation**: **Immediate dictionary update for entity errors, batch retraining for classification errors**.

**Decision tree**:
```
If human overturns AI label:
  - Entity mismatch (wrong asset detected) → update entity dictionary immediately
  - Event type mismatch (listing vs partnership) → log for batch retraining
  - Relevance mismatch (publish vs discard) → log for batch retraining
  
If same error repeats 3+ times in one week → emergency rule patch
```

**Why**: Entity errors are deterministic (fixable with dictionary). Classification errors need more data to retrain properly.

---

### Q15: Should pipeline block TG drafts when manual_review_required exceeds threshold?
**Recommendation**: **No blocking. Always publish what's approved, queue the rest**.

**Better approach**:
- TG draft generator runs daily at 9am
- Publishes all events approved in last 24h
- Sends you a private alert: "15 events pending review" (not public)

**Why**: Blocking TG output because of review backlog defeats the purpose. Users should see approved events immediately. Your review backlog is your problem, not theirs.

**Safeguard**: If review queue >50 events for 3+ days, send escalation alert (you're not keeping up).

---

### Q16: Auto-closed low-risk audit pass-rate requirement?
**Recommendation**: **95% pass-rate** before trusting auto-close in production.

**Validation**:
- Audit 100 auto-closed events
- If <95 are correctly closed → investigate failure mode
- Common failure: AI closes duplicates that are actually different angles on same story

**Why**: Auto-close errors are silent (you never see the event again). Needs higher bar than auto-publish (where humans see the output).

---

### Q17: Should other_review be split into explicit classes?
**Recommendation**: **Yes, split into 3 classes** (see Priority 2):
1. `reject_non_crypto` (traditional finance, no blockchain angle)
2. `reject_weak_signal` (too vague, no clear catalyst, opinion pieces)
3. `reject_bad_entity` (entity extraction failed, scraper pollution)

**Why**: "Other" is a bug magnet. Every time you're unsure, you throw it in "other", and it becomes a 210-row junk drawer.

**Impact**: After split, you'll see that `reject_bad_entity` is 40% of "other" → fix scraper, not classifier.

---

### Q18: Should research_only ever be promoted to publish?
**Recommendation**: **Yes, but only manually** (no auto-promotion).

**Use case**: 
- Unsupported asset gets Binance listing → backfill old `research_only` events → human reviews for publish
- Weak signal gets confirmed by follow-up event → human promotes original event

**Why**: Research-only is a holding area, not a trash bin. But auto-promotion is risky (you might promote outdated news).

---

### Q19: Source-level reliability score?
**Recommendation**: **Not now. Solve after 500+ events**.

**Why**: 
- You don't have enough data yet to score sources reliably
- Source quality is confounded with event type (Jin10 might be great for macro, bad for DeFi)
- Premature optimization

**When to add**: After 500 events, if you see that 80% of rejected events come from 2-3 sources, then add source scoring.

---

### Q20: Hard release gate for first TG draft pilot?
**Recommendation**:
- ✅ **20+ clean events** ready to publish (you have 22)
- ✅ **Manual review workflow** <30min per day (build this week)
- ✅ **Backtest smoke test** passes (no broken timestamps/prices) (you have this)
- ❌ **NOT required**: Statistical backtest significance
- ❌ **NOT required**: <8.5% manual review rate
- ❌ **NOT required**: Exploit primary-asset policy resolution

**Gate check**: Can you publish 5 events/day for 2 weeks without breaking? If yes, ship.

---

## 4. Questions Not Worth Solving Now

### Don't solve now (defer to v0.7+):
- **Q3** (market basket benchmark): BTC baseline is fine for first 200 events
- **Q12** (audit sampling rate): 20% is safe, optimize later
