# Claude Response

- generated_at: 2026-05-27 16:35:10 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_NEXT_PROMPT.md
- prompt_sha256_16: fca19de014d58043

# External Review: Crypto Event Intelligence

## Executive Assessment

**Product direction**: Fundamentally sound, but you're over-engineering the quality gates before proving the core value hypothesis.

**Current state**: You have a working pipeline with good observability, but you're stuck in a "perfect before launch" loop. The TG pilot delay is a strategic mistake.

**Critical gap**: You don't know if anyone wants this product. You're optimizing classification accuracy without user feedback on what "high-value" actually means.

---

## Top 3 Disagreed Assumptions

### 1. **"TG drafts amplify labeling errors, so delay until <8.5% review rate"**

**Disagree strongly.** This is backwards risk management.

- A private TG channel with 5-10 test users is your *cheapest* way to discover what matters
- Current 13/201 review queue (6.5%) is already better than most ML products at launch
- You're treating TG as "production" when it should be your *ground truth collection tool*
- The real risk isn't bad events reaching TG—it's building for 6 more months without user signal

**What to do instead**: Ship a "Research Preview" TG channel this week with:
- Clear "BETA - Expect Noise" header on every message
- Only `alpha_candidate` + manually approved `human_review` 
- Explicit feedback buttons (👍/👎/🤷)
- 10 sophisticated users who understand it's a prototype

### 2. **"Asset attribution must be perfect before backtest"**

**Disagree.** You're conflating two different problems:

- **Attribution quality** (is this event about BTC or ETH?) 
- **Backtest validity** (can we measure price impact?)

Your "high-risk attribution" rows are mostly fine for *publishing*—they're only problematic for *statistical analysis*. But you're blocking the publish workflow to fix the backtest workflow.

**What to do instead**: 
- Separate the pipelines: `publish_candidates.csv` vs `backtest_clean.csv`
- Let "medium attribution risk" rows publish if they're relevant
- Only exclude from backtest, not from product
- Example: "Hyperliquid dominates perp DEX market" is great content even if HYPE attribution is ambiguous

### 3. **"Manual review required rate is the key quality metric"**

**Disagree.** This metric is gamed by your AI's conservatism, not actual quality.

- AI is trained to say "needs review" when uncertain → inflates the metric
- The real question: *of published events, what % are valuable?*
- You won't know until you publish and measure engagement

**What to do instead**:
- Track *user feedback rate* on published events (👍/👎 ratio)
- Measure *false positive rate* (published but useless) not *review rate*
- Accept that 15-20% "needs review" is fine if the 80% auto-approved is good

---

## 5 Highest-Priority Actions (Next 2 Weeks)

### 1. **Ship TG Research Preview by Friday** ⚠️ CRITICAL
**Why**: You need user feedback more than you need perfect classification.

**Scope**:
- Private channel, 10 invited users (traders/researchers you know)
- Post only `alpha_candidate` + manually approved `human_review`
- Format: `[BETA] {title}\n🏷️ {asset} | 📅 {time}\n{summary}\n👍👎🤷`
- Collect feedback for 2 weeks before any optimization

**Acceptance**: 30+ events posted, 10+ feedback reactions received

---

### 2. **Split Publish and Backtest Pipelines**
**Why**: Attribution ambiguity blocks publishing but shouldn't.

**Implementation**:
```python
# New routing logic
if relevance == "high" and asset_supported:
    → publish_candidates (allow medium attribution risk)
    
if relevance == "high" and asset_supported and attribution_risk == "low":
    → backtest_clean (strict subset)
```

**Acceptance**: 
- `publish_candidates.csv` has 60-80 rows (current 22 + medium-risk)
- `backtest_clean.csv` stays at 22 rows
- Document the split in `DECISIONS.md`

---

### 3. **Collapse `other_review` into Explicit Reject Reasons**
**Why**: "Other" is a classification bug attractor.

**New taxonomy**:
```
discard_non_crypto          # Trad finance, no blockchain angle
discard_weak_relevance      # Crypto-related but not actionable
discard_insufficient_entity # Can't determine what asset this affects
discard_duplicate           # Already covered
```

**Implementation**:
- Audit current 210 `other_review` rows
- Reclassify into 4 buckets above
- Update AI labeling prompt with examples
- Remove `other_review` as a valid label

**Acceptance**: Zero `other_review` rows in next 100-candidate batch

---

### 4. **Define "Protocol Exploit Primary Asset" Policy** 
**Why**: This is blocking 5 high-value events and will recur.

**Recommended policy**:
```
For protocol exploits:
- Primary asset = the stolen/minted asset (eBTC, not ETH)
- If multiple assets stolen, use largest USD value
- Tag secondary: protocol_name, chain
- Route: alpha_candidate (exploits are high-signal)

Exception: If stolen asset unsupported (e.g., eBTC not on Binance):
- Primary asset = chain native token (ETH)
- Add warning: "Proxy asset - actual impact on {stolen_asset}"
```

**Acceptance**: 
- Policy documented in `DECISIONS.md`
- 5 exploit rows reclassified and moved to `publish_candidates`

---

### 5. **Implement User Feedback Loop**
**Why**: You're optimizing for the wrong objective function.

**Schema**:
```python
# Add to TG messages
feedback_buttons = ["👍 Useful", "👎 Noise", "🤷 Unsure"]

# Log to feedback.csv
event_id, user_id, feedback, timestamp, asset, event_type
```

**Analysis** (after 2 weeks):
- Useful rate by `event_type` 
- Useful rate by `asset`
- Useful rate by `event_scope` (single vs market-wide)
- Identify: which `human_review` rows got 👍? (promote rules)

**Acceptance**: Feedback collection working, 50+ feedback points logged

---

## Question-by-Question Recommendations

### Solve Now (Critical Path)

**Q1: TG publishing - auto_publish vs human_review?**
→ **Start with human_review only.** Auto-publish stays disabled until you have 100+ user feedback points proving the AI's judgment aligns with user value. This is a 2-week delay, not a 2-month delay.

**Q10: Minimum standard for auto_publish?**
→ **User feedback 👍 rate >70% on AI-approved events, measured over 100+ events.** Not internal review rate. Let users define quality.

**Q11: Ground truth for publish quality?**
→ **User feedback is ground truth.** Labeling schema:
- `user_feedback`: 👍/👎/🤷 (from TG)
- `feedback_reason`: free text (optional)
- `internal_label`: useful/noise/unsure (your review)
- Need 200+ user feedback points before auto-publish.

**Q17: Split `other_review` bucket?**
→ **Yes, immediately.** Use 4 explicit discard reasons (see Action #3). "Other" is where your classification bugs hide.

**Q20: Hard gate for TG pilot?**
→ **Wrong question.** The gate should be "research preview" vs "production." 
- Research preview: Now (just ship it)
- Production auto-publish: 200+ user feedback, >70% useful rate

---

### Solve This Month (High Value)

**Q2: Separate macro/single-asset feeds?**
→ **Yes, separate sections in same channel.** Format:
```
📊 MARKET-WIDE
[event 1]
[event 2]

🎯 SINGLE-ASSET  
[event 3]
[event 4]
```
Users scan differently for these. Measure engagement separately.

**Q5: Unsupported assets in publish?**
→ **Yes, allow.** Add tag `[No Binance Data]` to message. These are still valuable intelligence. Just exclude from backtest.

**Q9: Enforcement/fraud taxonomy?**
→ **New L1 type: `legal_enforcement`.** Distinct from hacks (technical) and regulation (policy). Examples: Ponzi busts, fraud charges, sanctions. Route to `research_only` unless tied to specific tradable asset.

**Q13: Accept high-confidence discard labels?**
→ **Yes, with audit sampling.** 
- Auto-accept `discard` if confidence >0.85
- Audit 10% random sample weekly
- If audit finds >5% errors, retrain

**Q16: Auto-closed audit pass-rate?**
→ **95% minimum.** These bypass human review entirely, so threshold must be high. Start at 98% until you have 500+ auto-closed examples.

---

### Solve After TG Pilot (Deferred)

**Q3: Benchmark for BTC/ETH events?**
→ **Defer.** Current BTC/ETH abnormal return is fine for initial backtest. Don't build market basket until you prove single-asset events are valuable.

**Q4: Crypto adoption stories (Revolut card)?**
→ **Defer to user feedback.** Publish a few, see if users engage. If 👎 rate >50%, auto-discard this category.

**Q6: Opinion/analysis from KOLs?**
→ **Defer.** Start with facts only. Add opinion later if users request it.

**Q7: Long-form article footer pollution?**
→ **Defer.** This is a data quality issue, not a product blocker. Fix if it causes >10% misclassification in user feedback.

**Q8: BTC miner equity / AI data-center?**
→ **Defer.** Publish a few as `research_only`, measure engagement. Likely separate feed later.

**Q12: Minimum audit sampling rate?**
→ **Defer.** Start with 20% audit. Adjust based on error rate trends after 500+ labels.

**Q14: Human-AI conflict resolution?**
→ **Defer.** Log conflicts, review monthly. Don't build override logic until you see patterns (need 50+ conflicts).

**Q18: Promote research_only to publish?**
→ **Defer.** Keep them separate for now. Revisit after 3 months if certain research_only categories get high engagement.

**Q19: Source reliability scoring?**
→ **Defer.** Solve at row level first. Add source scoring only if you see systematic source-level quality gaps.

---

### Not Worth Solving (Drop)

**Q15: Block TG drafts if review queue >50?**
→ **Drop.** This is the "perfect before launch" trap. The review queue will always have noise. Ship and iterate.

---

## Critical Data/Label Assets

### Must Have Now
1. **User feedback on 100+ published events** (TG pilot)
   - This is your actual ground truth
   - Everything else is a proxy

2. **Exploit event primary-asset policy** (5 blocked events)
   - High-value event type
   - Recurring pattern

3. **`other_review` reclassification** (210 rows)
   - Largest source of ambiguity
   - Hiding classification bugs

### High Value This Month
4. **Market-wide vs single-asset engagement comparison**
   - Determines if you need separate feeds
   - Affects taxonomy design

5. **Unsupported asset user value** (HYPE/ONDO/WLD examples)
   - Determines if you need non-Binance data sources
   - Affects product scope

### Nice to Have Later
6. **Source reliability patterns** (after 1000+ events)
7. **KOL opinion value** (after fact-based events proven)
8. **Adoption story engagement** (after core events working)

---

## Architecture Gaps

### 1. **No User Feedback Loop** ⚠️ CRITICAL
You built a quality pipeline without defining quality. User feedback should be your primary metric, not internal review rate.

**Fix**: Add feedback collection to TG, make it the optimization target.

---

### 2. **Publish and Backtest Conflated**
Attribution ambiguity blocks both, but only matters for backtest. You're over-constraining the publish pipeline.

**Fix**: Separate `publish_candidates` (medium risk OK) from `backtest_clean` (strict).

---

### 3. **"Other" as a Label**
This is a bug attractor. Every ambiguous case lands here, making your AI training data noisy.

**Fix**: Force explicit reject reasons. Remove "other" as valid label.

---

### 4. **No Feedback-Driven Retraining**
You have AI labeling but no loop to improve it based on user feedback.

**Fix**: 
```python
# Monthly retraining flow
user_feedback.csv → retrain_examples.csv → update AI prompt → validate on holdout
```

---

### 5. **Over-Engineered Quality Gates**
You have 10 review actions, 5 audit reports, 3 preview files. This is analysis paralysis.

**Fix**: Collapse to 2 gates:
- **Research preview gate**: Can we show this to 10 users? (passed)
- **Auto-publish gate**: Do users find AI labels useful >70%? (not tested yet)

---

## What You're Doing Right

1. **Time provenance auditing** - This is excellent and rare
2. **Stratified sampling** - Smart way to handle class imbalance  
3. **Non-destructive review packets** - Good operational hygiene
4. **Separation of China time / UTC** - Correct for your use case
5. **Disabled auto-publish** - Right to keep this off until proven

---

## Bottom Line

**You have a working product.** Stop perfecting the classifier and start learning what users value.

**This week**: Ship TG research preview, collect 50+ feedback points.

**This month**: Let user feedback drive your optimization, not internal review queues.

**Risk**: If you wait another month for 98% perfect classification, you might build the wrong product perfectly.
