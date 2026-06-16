# External AI Review Packet v1

> 你可以把这个文件连同 GitHub 仓库发给其他 AI，让它们快速进入批判讨论。

## 1. Project Summary

**Crypto Event Intelligence** is an evidence-oriented system for organizing crypto event facts, filtering noise, recording price reactions, and building research datasets for future attribution analysis.

It is NOT:
- A trading bot or signal service
- A profit-guaranteeing system
- A completed causal attribution engine

It IS:
- A structured pipeline: raw data → normalized signals → noise gate → registry → price backfill → research dataset
- A reproducible, audit-friendly research foundation
- Currently 5 event samples, 233 tests, no attribution

## 2. Key Evidence Entry Points

| File | Purpose |
|------|---------|
| `README.md` | Quick start, project boundaries |
| `docs/PROJECT_OVERVIEW.md` | Detailed design decisions and maturity assessment |
| `docs/ARCHITECTURE.md` | System architecture, data flow, security boundaries |
| `research/week1_raw_research_dataset_v1.json` | The unified research dataset |
| `docs/research/week1_raw_research_dataset_v1.md` | Dataset documentation |
| `docs/audits/week1_raw_research_dataset_v1_release_evidence.md` | Evidence matrix (20 checks) |
| `docs/releases/week1_raw_research_dataset_v1_release.md` | Release report |
| `docs/roadmap/NEXT_PHASE_PLAN_V1.md` | Roadmap Phases 0-5 |

## 3. Verified Facts

- 5 event samples (w1_001 through w1_005)
- 6 sample-to-price links
- 5 unique price observations
- Shared observation key for w1_003 and w1_004 (same BTC broadcast time)
- HYPE price aligned to nearest 15m candle (signed lag -120s)
- BTC/ETH price at exact target time (0s lag)
- 233 tests passing
- 3 independent validators all passing
- Zero fixture data in network output
- Zero attribution fields
- Zero trading advice
- Deterministic build (byte-identical on repeat)

## 4. Known Assumptions

### Facts
- Binance public REST API does not require authentication
- Hyperliquid public Info API does not require authentication
- 2026-05-25 is a valid trading day

### Design Choices
- t0 = broadcast_time (not event_time) — broadcast is the verifiable anchor
- HYPE uses 15m candles — HL only provides 15m history
- BTC/ETH use 1m klines — Binance provides free 1m data
- max price lag 120s for Binance, 450s for HL
- Nearest-candle-open for HL, first-after-target for Binance
- Abnormal return = asset_return - benchmark_return

### Inferences (unverified)
- All 5 samples have sufficient signal quality for price backfill
- Price data source selection (Binance vs HL) is appropriate per asset
- 120s/450s max lag thresholds are reasonable
- Broadcast time is within 120s of market-relevant action

### Unverified Hypotheses
- The 5 samples represent meaningful event diversity
- Future attribution rules can be built on this data model
- Price observation dedup (w1_003/004) does not lose information
- The dataset is useful for designing attribution protocols

## 5. Key Questions for External AI Review

Please focus your critique on these questions:

1. **t0 = broadcast_time**: Is broadcast time the correct anchor? What biases does this introduce? Should we use event_time when available, or always broadcast?

2. **Event classification adequacy**: Are the 5 event categories sufficient? The manifest uses tags like `巨鲸流入`, `机构增持`, `监管动态`, `宏观`. Is this taxonomy granular enough for attribution?

3. **Noise Gate bias**: The Noise Gate uses deterministic thresholds (intensity≥medium, title non-empty, assets≥2). Are these thresholds creating systematic false positives or false negatives?

4. **Abnormal return methodology**: Asset return minus BTC or ETH return as "abnormal" — is this too simplistic? Should it be beta-adjusted? Should it include sector-specific benchmarks?

5. **Dual benchmark (BTC + ETH)**: Is it useful to report both BTC and ETH abnormal returns? When would they diverge meaningfully?

6. **Concurrent event separation**: On 2026-05-25T16:12:00Z, two events (w1_003 and w1_004) share the same broadcast time. How should attribution handle concurrent events?

7. **Interference quantification**: There is currently no way to quantify interference (other events, macro factors, market microstructure). How should this be approached?

8. **Confidence framework**: What dimensions should attribution confidence include? Time proximity? Source reliability? Asset specificity? Narrative consistency?

9. **Sample size requirements**: How many samples are needed before drawing conclusions about system accuracy? What's the minimum viable sample size for Phase 2?

10. **Source credibility scoring**: How should source trust enter the model? Primary vs secondary? On-chain evidence vs anonymous claims?

11. **Hindsight bias prevention**: What design elements prevent post-hoc rationalization of price moves? Are there pre-registration proposals?

12. **Data leakage risks**: What aspects of the current pipeline could cause look-ahead bias or information leakage? Time alignment? Window selection?

13. **Engineering vs research value**: Which components are solid engineering but add limited research value? What could be removed without harming research goals?

## 6. Output Requirements for Reviewing AI

When providing your review:

- DO NOT restate the documentation
- DO provide evidence-based objections
- DO distinguish: bugs / methodology flaws / product deficiencies
- DO assign priority: P0 (blocker) / P1 (important) / P2 (nice to have)
- DO NOT treat correlation as causation
- DO NOT recommend auto-trading
- DO highlight over-engineered components
- DO propose the smallest next-step validation experiment

## 7. Independent Review Prompt (Chinese)

> 你是一个严格、不客气的加密货币研究系统审计者。请审查 GitHub 仓库 `https://github.com/zhuo74451-art/crypto-event-intelligence` 分支 `workbench/week1-raw-dataset-v1`。
>
> 项目定位为"加密事件事实整理、噪音过滤、价格反应回填与后续归因研究的证据型系统"——不是交易机器人。
>
> 已知事实：
> - 5 个事件样本、6 条价格关联、5 个唯一价格观察
> - w1_003 和 w1_004 共用价格观察
> - HYPE 使用 15m，BTC/ETH 使用 1m
> - t0 = broadcast_time
> - 233 tests, 3 validators 全部通过
> - attribution layer 未实现
>
> 请在阅读以下文件后回答：
> - README.md
> - docs/PROJECT_OVERVIEW.md
> - docs/ARCHITECTURE.md
> - research/week1_raw_research_dataset_v1.json (结构)
> - docs/audits/week1_raw_research_dataset_v1_release_evidence.md
>
> 要求：
> 1. 区分 bug、方法论缺陷、产品缺陷
> 2. 标记 P0/P1/P2
> 3. 指出哪里可能是"漂亮工程但研究价值有限"
> 4. 指出哪里可能有数据泄漏
> 5. 给出最小区块链验证方案，而非继续扩样本
> 6. 不写"可以改进"这种套话，写"这里必须删掉"或"这里逻辑不成立"
> 7. 不要假设归因已经实现，只评价已存在的东西
