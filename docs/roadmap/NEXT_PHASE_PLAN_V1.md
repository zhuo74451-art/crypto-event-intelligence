# Next Phase Plan v1

## Phase 0: Freeze Current Raw Data Baseline

**Status: Complete**

Frozen artifacts:
- Signal Spine RC1
- Manifest v1.1
- Price Provider v1
- Week 1 Raw Research Dataset v1

---

## Phase 1: Event Attribution Protocol v1

**Priority: P0**

Design and validate (do NOT train a model):

| Component | Description |
|-----------|-------------|
| Interference event inventory | List of concurrent events at each sample time |
| Same-window event clustering | Group events within each observation window |
| Attribution confidence dimensions | Time proximity, source reliability, asset specificity, narrative consistency |
| Counterfactual questions | "Would BTC have moved this way without this event?" |
| Source evidence hierarchy | On-chain direct > official > verified journalist > anonymous |
| Benchmark-relative move | Size of move relative to expected volatility at that time |
| Alternative explanations | Required field: at least one plausible alternative |
| Insufficient evidence state | A third verdict: "not enough evidence to assign or reject attribution" |

**Do not train ML models at this stage.**

The expected output of Phase 1 is a written protocol document, not a software module.

---

## Phase 2: Expand Real Samples

**Priority: P0**

Target: 30–50 samples across event types:

| Type | Target Count |
|------|-------------|
| Whale / on-chain | 5-8 |
| Institutional | 4-6 |
| Regulatory | 4-6 |
| Macro | 4-6 |
| Security incident | 3-5 |
| Listing / delisting | 3-5 |
| Project announcement | 4-6 |
| Market structure | 3-4 |

**Evaluation fields must be pre-specified. No post-hoc rule changes after seeing prices.**

---

## Phase 3: Source and Evidence Protocol

**Priority: P1**

| Component | Description |
|-----------|-------------|
| Primary vs secondary source | Is this first-hand or a repost? |
| Source independence | Are two "separate" sources actually quoting each other? |
| Circular citation penalty | Deduct when sources form a citation loop |
| Time freshness decay | Older sources get lower weight |
| Source reliability tiers | Official > on-chain > verified > anonymous |
| On-chain direct evidence | Transaction-level proof of event |
| Official announcement | Direct from project or regulator |
| Analyst interpretation | Labeled as opinion, not fact |
| Anonymous claim | Marked as lowest reliability |

---

## Phase 4: Event Identity and Merge Protocol

**Priority: P1**

| Component | Description |
|-----------|-------------|
| Same event, multiple titles | "BTC ETF Approved" and "SEC Greenlights Bitcoin ETF" |
| Same title, different times | Reposted news with different timestamps |
| Multiple events at same time | Concurrent events at one broadcast_time |
| Parent/child events | "Fed rate decision" parent → "BTC reaction" child |
| Event updates | "FTX update day 1" → "FTX update day 30" |
| Event reversal | "Approved" → "Rejected" |
| Cross-source merge | Same event from CoinDesk + CoinTelegraph + Binance announcement |

---

## Phase 5: Semi-Automated Research Runs

**Priority: P2**

Only after Protocol phases 1, 3, 4:

| Component | Description |
|-----------|-------------|
| Scheduled collection | Cron-based multi-source event polling |
| Scheduled price backfill | Auto-refresh price data for pending windows |
| Status monitoring | Dashboard for pipeline health |
| Failure retry | Exponential backoff for transient API failures |
| Audit log | Structured log of all pipeline runs |
| Human review queue | Flag events requiring manual attribution review |

---

## Explicitly Out of Scope (Current Phase)

- Automatic trading or order execution
- Black-box ML scoring or "alpha" predictions
- Guaranteed profit claims
- Production Telegram auto-publishing
- Unsupervised attribution conclusions
- Any system that bypasses human review for attribution decisions

## Next Immediate Action

**Before adding any more engineering modules:**

1. Distribute this repository and AI review packet to multiple independent AI and human researchers
2. Collect structured critique (bugs, methodology flaws, design over-engineering)
3. Incorporate feedback into the Attribution Protocol v1 design document
4. Freeze the protocol before expanding samples

> "先让多个独立 AI 和人工研究者审阅当前仓库与 Week 1 Raw Dataset，再冻结《事件归因协议 v1》设计，而不是继续增加工程模块。"
