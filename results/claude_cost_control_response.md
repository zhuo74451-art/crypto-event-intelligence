# Claude Response

- generated_at: 2026-05-27 17:07:01 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_COST_CONTROL_PROMPT.md
- prompt_sha256_16: b19eecb98c9a29d0

# Cost-Controlled AI Review Architecture for Crypto Event Intelligence

## 1. When Should Claude Review Events?

**Recommendation: Only uncertain cases after multi-stage filtering**

- **Never on raw events** - too noisy, 70-90% will be duplicates/spam/irrelevant
- **Never on obvious passes/fails** - deterministic rules handle these
- **Yes on borderline cases** - where local rules + small models are uncertain (confidence < 0.7)
- **Yes on random 2-5% sample** - for continuous quality auditing and rule refinement

**Critical point:** Your 20-event test is misleading. In production, most events will be garbage. Claude reviewing everything would waste 80%+ of budget on obvious rejections.

## 2. Deterministic Local Rules (Pre-LLM Filter)

**Must implement before any AI call:**

### Immediate Auto-Discard:
- Duplicate detection (content hash, 95%+ similarity in 24hr window)
- Blacklisted sources/channels (known spam Telegram groups)
- Keyword spam patterns: "100x gem", "not financial advice", excessive emojis (>10), all-caps >50%
- Length filters: <20 chars or >5000 chars
- URL-to-text ratio >40% (link spam)
- Repeated messages from same source <1hr apart
- Non-English without translation (if English-only policy)

### Immediate Auto-Approve Candidates:
- Whitelisted official sources (project official channels, verified news outlets)
- Structured on-chain events matching exact templates (e.g., "Wallet 0x123...abc transferred 1000 ETH to Binance")
- Events matching pre-approved patterns with variable substitution

### Extract & Tag (for downstream routing):
- Event type classification (regex/keyword): exploit, funding, listing, partnership, regulatory, price movement
- Mentioned entities: extract wallet addresses, token symbols, exchange names, dollar amounts
- Urgency signals: "breaking", "alert", timestamps, magnitude thresholds

**Expected filter rate: 60-80% of raw events eliminated here, <1ms per event, $0 cost**

## 3. Small Model vs Claude Routing

### Small Model Tier (GPT-4o-mini, Claude Haiku, or Llama 3.1 8B local):
**Use for: ~15-25% of remaining events**

- **Formatting/cleanup tasks**: Extract structured data from semi-structured text
- **Simple binary decisions**: "Does this mention a specific exploit?" "Is this about a token listing?"
- **Confidence scoring**: Rate relevance 0-1 for borderline cases that passed local rules
- **Template matching**: "Does this fit the 'large transfer' event template?"
- **Duplicate semantic check**: Embedding similarity for near-duplicates local rules missed

**Cost: ~$0.10-0.50 per 1M tokens (20-50x cheaper than Claude Sonnet)**

### Claude-Level Model:
**Use for: ~2-5% of total events**

- **Complex editorial judgment**: "Is this newsworthy for traders?" "Does this imply material risk?"
- **Nuanced scam detection**: Sophisticated pump schemes, fake partnerships
- **Ambiguous context**: Events requiring knowledge of project history, market context
- **Quality control**: Random sample audits
- **Edge cases flagged by small model**: confidence score 0.4-0.7

**Critical insight:** Small models are 90% as good for structured tasks, 60% as good for judgment calls. Route accordingly.

## 4. Batching Strategy

### For Telegram/News CSV Processing:
- **Micro-batches of 50-100 events** every 5-15 minutes
- Group by event type before sending to LLM (exploits together, listings together)
- Single prompt with JSON array input/output
- Cost savings: ~30-40% (shared context, reduced per-request overhead)
- Latency: acceptable for news (5-15 min delay tolerable)

### For On-Chain Events:
- **Do NOT batch time-sensitive events** (large exploits, major transfers)
- Batch routine events (small transfers, normal DEX swaps) in 15-min windows
- Separate fast-track queue for high-value events (>$1M, known hacker wallets)

### Batching Anti-Pattern to Avoid:
- Don't batch >200 events - quality degrades, timeouts increase
- Don't batch mixed languages - context confusion
- Don't delay critical events for batch efficiency

**Practical implementation:** 
```
Queue 1 (real-time): High-priority events → immediate small model → Claude if needed
Queue 2 (batched): Routine events → 10-min accumulation → batched small model
Queue 3 (audit): Random 2% sample → daily Claude review batch
```

## 5. Event Routing Thresholds

### Decision Tree:

```
Raw Event
│
├─> Local Rules Check
│   ├─> DISCARD (60-80%): spam score >0.8, duplicate, blacklist
│   ├─> PUBLISH CANDIDATE (5-10%): whitelist source + template match
│   └─> NEEDS_REVIEW (15-30%): passed basic filters
│
└─> Small Model Review (on NEEDS_REVIEW)
    ├─> Confidence >0.8 → PUBLISH CANDIDATE
    ├─> Confidence <0.3 → DISCARD
    └─> Confidence 0.3-0.8 → CLAUDE_REVIEW
        │
        └─> Claude Decision
            ├─> Approve → PUBLISH
            ├─> Reject → DISCARD + log for rule refinement
            └─> Uncertain → HUMAN_AUDIT queue
```

### Specific Thresholds:

| Metric | Auto-Discard | Local Publish | Small Model | Claude | Human |
|--------|--------------|---------------|-------------|--------|-------|
| Spam score | >0.8 | <0.1 (whitelist) | 0.1-0.8 | - | - |
| Duplicate similarity | >95% | - | 85-95% | - | - |
| Small model confidence | - | >0.85 | 0.3-0.85 | 0.3-0.7 | <0.3 (if important) |
| Financial magnitude | - | - | <$100K | $100K-$10M | >$10M (audit) |
| Source reputation | Blacklist | Tier-1 verified | Tier-2/3 | Unknown | Suspicious pattern |

**Calibration process:** Start conservative (more Claude reviews), measure precision/recall weekly, adjust thresholds to hit 95% accuracy target.

## 6. Architecture Changes for On-Chain Watchers

### New Requirements:
- **Volume explosion**: 100x more events than Telegram (every block has transactions)
- **Structured data**: On-chain events are machine-readable (no NLP needed for extraction)
- **Real-time expectations**: Exploit detection must be <1 min latency
- **High signal variance**: 99.9% of transactions are routine, 0.1% are critical

### Architecture Adaptations:

**Pre-Filter Layer (before any AI):**
```
On-Chain Event Stream
│
├─> Magnitude Filter: <$10K → DISCARD (99% of volume)
├─> Whitelist: Known safe wallets/contracts → DISCARD
├─> Pattern Match: Exact template (normal CEX deposit) → LOG_ONLY
└─> Anomaly Detection: Statistical outliers → PRIORITY_REVIEW
```

**Deterministic Rules Become Primary:**
- Template-based event generation: "Wallet {addr} transferred {amount} {token} to {exchange}"
- Threshold alerts: ">$1M USDT to Binance from wallet flagged 30 days ago"
- No LLM needed for 95%+ of on-chain events

**Small Model Use Cases:**
- Contextual enrichment: "This wallet was involved in [previous exploit]"
- Pattern classification: "Is this transfer pattern consistent with OTC deal vs exploit?"
- Narrative generation: Convert structured data to readable alert

**Claude Use Cases (rare):**
- Novel exploit patterns not matching known templates
- Ambiguous multi-step transactions requiring reasoning
- Audit of auto-generated alerts (sample-based)

**Critical change:** On-chain watchers should generate **structured alerts**, not raw events. LLMs review alerts, not transactions.

### Hybrid Architecture:

```
[On-Chain Watcher] → [Rule Engine] → [Alert Generator] → [Small Model Enrichment] → [Publish]
                                              ↓
                                    [Anomaly Detector] → [Claude Review] → [Human Escalation]
```

**Cost impact:** With proper filtering, on-chain events should cost LESS per published alert than Telegram scraping (more structured, less noise).

## 7. Practical Cost Policy by Scale

### Assumptions:
- Claude Sonnet: $3 per 1M input tokens, $15 per 1M output (~$0.01 per event review)
- Small model: $0.15 per 1M input tokens (~$0.0005 per event)
- Local rules: $0.00001 per event (compute only)

### 1,000 Events/Day (Early Stage)

**Budget: $50-100/month**

- Local rules: 1000 events → 200 pass (80% filtered) → $0
- Small model: 200 events → 40 uncertain (80% decided) → $3/month
- Claude: 40 events + 20 audit samples → 60 × $0.01 → $18/month
- Human audit: 5 events/day × $5/event → $750/month (main cost is human time)

**Policy:**
- Conservative thresholds (more Claude reviews to build training data)
- 5% audit rate
- Focus on rule refinement

### 10,000 Events/Day (Growth)

**Budget: $300-500/month**

- Local rules: 10K → 2K pass → $0
- Small model: 2K → 300 uncertain → $30/month
- Claude: 300 + 200 audit → 500 × $0.01 → $150/month
- Buffer for experimentation: $100/month

**Policy:**
- Tighten local rules (target 85% filter rate)
- 2% audit rate
- A/B test small model providers (Haiku vs GPT-4o-mini vs local Llama)

### 100,000 Events/Day (Scale)

**Budget: $1,500-3,000/month**

- Local rules: 100K → 15K pass (85% filtered) → $10/month (compute)
- Small model: 15K → 1.5K uncertain (90% decided) → $225/month
- Claude: 1.5K + 500 audit → 2K × $0.01 → $600/month
- Local model inference (optional): $500/month (GPU instance)
- Human audit: 50 events/day → $7,500/month (still main cost)

**Policy:**
- Aggressive local rules (target 90% filter rate)
- 0.5% audit rate
- Consider self-hosted small model (Llama 3.1 8B on dedicated GPU)
- Implement feedback loop: human corrections → fine-tune local model monthly

**Critical insight:** At scale, human review time costs 3-5x more than AI. Optimize for human efficiency, not just AI cost.

## 8. Metrics to Track AI Spend Justification

### Primary Metrics (Track Weekly):

**Cost Efficiency:**
- **Cost per published event**: Total AI spend / events published
  - Target: <$0.02 at 1K/day, <$0.005 at 100K/day
- **Cost per event reviewed**: AI spend / events sent to AI
  - Should decrease over time as rules improve
- **Filter efficiency**: % events eliminated by $0 local rules
  - Target: 80% → 90% over 6 months

**Quality Metrics:**
- **Precision**: % of published events that are actually valuable (human audit)
  - Target: >90%
- **Recall**: % of valuable events captured (sample raw feed manually)
  - Target: >85%
- **False negative cost**: Estimated value of missed critical events
  - Track: "We missed the [major exploit] 2 hours before public news"

**Operational Metrics:**
- **Latency P95**: Time from event occurrence to publication
  - Target: <5 min for critical, <30 min for routine
- **Claude utilization**: % of Claude reviews that were necessary (couldn't be handled by cheaper tier)
  - Target: >70% (if lower, thresholds too loose)
- **Human override rate**: % of AI decisions reversed by humans
  - Target: <5% (if higher, AI not ready)

### ROI Calculation (Monthly):

```
AI Value = (Critical events caught early × $value) + (Human hours saved × $hourly_rate) - AI_cost

Example:
- 3 exploits detected 1hr early → 3 × $5,000 (user value) = $15,000
- 40 human review hours saved → 40 × $50 = $2,000
- AI cost: $500
- ROI: ($17,000 - $500) / $500 = 33x
```

**If ROI <5x:** AI spend not justified, improve filters or reduce scope.

### Red Flags to Monitor:

- **Cost per event increasing over time**: Rules degrading, need refresh
- **Claude review rate >10% of total events**: Pre-filters failing
- **Precision dropping below 85%**: Quality degradation, tighten thresholds
- **Latency increasing**: Batching too aggressive or API issues
- **Human override rate >10%**: AI not learning from feedback

### Dashboard (Daily View):

```
┌─────────────────────────────────────────┐
│ Events Today: 10,000                     │
│ ├─ Filtered (local): 8,500 (85%)        │
│ ├─ Small model: 1,200 (12%)             │
│ ├─ Claude: 300 (3%)                     │
│ └─ Published: 180 (1.8%)                │
│                                          │
│ Cost Today: $18.50                       │
│ ├─ Small model: $3.00                   │
│ ├─ Claude: $15.00                       │
│ └─ Cost/published: $0.10                │
│                                          │
│ Quality (7-day):                         │
│ ├─ Precision: 92%                       │
│ ├─ Human override: 4%                   │
│ └─ Latency P95: 8min                    │
└─────────────────────────────────────────┘
```

---

## Concrete First Implementation (Week 1)

**Don't overthink it. Start here:**

1. **Implement 10 local rules** (duplicates, spam keywords, length filters) - 2 days
2. **Route remainder to Claude** with confidence scoring prompt - 1 day
3. **Track cost and quality for 1 week** - baseline metrics
4. **Add small model tier** for events Claude rates >0.7 or <0.3 confidence - 2 days
5. **Iterate on local rules** based on Claude rejection patterns - ongoing

**First month goal:** Get to 70% local filter rate, <$0.05 per published event, >85% precision.

**Avoid:** Building complex ML pipelines before understanding your data. Your 20-event test told you nothing about production distribution.
