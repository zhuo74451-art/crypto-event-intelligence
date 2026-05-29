# Decisions

## D001: Human-Facing Time Is China Time

Decision:

Human review fields use China time: `Asia/Shanghai`, `UTC+8`.

Implementation:

- Keep `*_china` for review.
- Keep `*_utc` for API/math.
- Binance Kline requests use UTC milliseconds.

Reason:

The operator reviews news and Telegram output in China time, while APIs use UTC.

## D002: Backtest Time Uses Published Time

Decision:

Backtests use `published_at` as the default `backtest_time`, not the earlier source event time.

Reason:

This models what was known after the news reached the system and avoids look-ahead bias.

## D003: Unsupported Asset Does Not Mean Irrelevant

Decision:

Assets without Binance symbols can enter `unsupported_research`, but cannot enter Binance price backtest.

Reason:

HYPE/ONDO/WLD-like events can be valuable intelligence even when Binance spot/futures data is unavailable.

## D004: Auto Publish Is Disabled

Decision:

All would-be `auto_publish` items are downgraded to `human_review`.

Reason:

No publishing automation should run before 200+ manually labeled rows prove event intake quality.

## D005: Cursor Handoff Is File-Based

Decision:

Cursor receives generated prompt files instead of direct UI automation.

Reason:

Cursor chat automation is brittle without an official local API. File-based handoff is auditable and repeatable.

## D006: AI-First Labeling With Audit Gates

Decision:

AI owns the main event-intake labeling workflow. Human work is limited to low-confidence review, audit samples, rollback investigation, and taxonomy/policy changes.

Implementation:

- Use `docs/V06_AI_LABELING_POLICY.md` as the labeling policy.
- Use `scripts/check_v06_tg_pilot_gate.py` before any TG draft pilot.
- Keep `auto_publish` disabled.

Reason:

The product needs Web3-aware AI judgment at scale. Large manual labeling queues are slow, inconsistent, and do not match the intended operating model.

## D007: Delay TG Drafts Until Labeling Fragility Is Reduced

Decision:

Do not build the TG draft generator yet, even though an earlier pilot gate passed.

Implementation:

- Treat `results/v06_claude_next_engineering_direction.md` as the latest direction-level guidance.
- Continue v0.6 quality work until `manual_review_required` is at or below 10% or explicitly accepted.
- Require a larger audit sample before draft pilot.

Reason:

Claude identified TG drafts as a downstream visibility step that would amplify upstream labeling errors. A 59-row review queue on 201 labels is still too high for a production-like draft workflow.

## D008: Gate Pass Is Not Enough For TG Drafts

Decision:

Even after the stricter pilot gate passed, TG draft generation remains delayed.

Implementation:

- Treat `results/v06_claude_after_gate_next_step.md` as current direction-level guidance.
- Expand audit sample to 200+ rows.
- Add synthetic edge cases for timezone, missing assets, macro scope, conflicting signals, and unsupported assets.
- New target: `manual_review_required_rate <= 0.085`.

Reason:

The previous pass was too close to the 10% ceiling. A single noisy macro batch could break the gate again.

## D009: High-Confidence Macro Discards Leave The Main Review Queue

Decision:

High-confidence rows with `manual_decision=discard`, `manual_channel_route=macro_policy`, and `event_scope=multi_asset` or `market_wide` do not remain in the main `manual_review_required` queue.

Implementation:

- Use `scripts/release_v06_macro_discard_rows.py`.
- Move released rows to `macro_discard_audit`.
- Preserve released rows in `data/v06_macro_discard_released_rows.csv`.
- Do not release `approve_publish` or `keep_review` rows with this rule.

Reason:

These rows are already excluded from publishing and trading-facing flows. Keeping them in the main review queue inflates the blocker rate without improving TG draft safety. They still remain auditable and reversible.

## D010: TG Draft Pilot Is A Product Smoke Test, Not A Statistical Claim

Decision:

Start a local TG draft pilot queue before waiting for statistically significant event-type backtest conclusions.

Implementation:

- Generate local draft files only.
- Do not call Telegram API.
- Do not auto-send.
- Keep every draft in `pending_review` until a human approves, rejects, or edits it.
- Use backtests as smoke tests for time, symbol, and price sanity; do not present event-type performance as a product conclusion.
- Keep `auto_publish` disabled.

Reason:

Claude's latest direction review argued that the product is an intelligence feed, not a quantitative trading strategy. The backtest is useful for catching broken data, but the next product risk is whether reviewed event drafts are useful to real readers.

## D011: Multi-Asset Exploit Events Should Not Be Blocked By Primary-Asset Perfection

Decision:

Protocol exploit and security events may carry multiple relevant asset tags during draft/review workflows.

Implementation:

- Do not force uncertain exploit events into BTC or ETH just to make the price backtest easier.
- Use protocol token, chain, stolen asset, and affected ecosystem as review context when available.
- If a single primary asset is not defensible, keep the item in review/research routing instead of publishing as a clean single-asset backtest row.

Reason:

Exploit events can be high-value intelligence even when the primary trading asset is ambiguous. The taxonomy should improve from review feedback rather than blocking all such items.

## D012: Claude Is A Scarce Review Tier, Not The First Filter

Decision:

Claude-level models must not review every raw news item or every future on-chain event.

Implementation:

- Run deterministic local rules before any model call.
- Use local dedup, source quality, length/truncation checks, entity extraction, and obvious discard rules first.
- Use cheaper/smaller review tiers for simple classification and confidence scoring when available.
- Use Claude for borderline cases, complex editorial judgment, exploit/multi-asset ambiguity, and random audit samples.
- Do not send raw on-chain transaction streams to Claude. On-chain watchers must produce structured alerts first.

Reason:

Full Claude review over raw feeds would waste budget on duplicates, spam, generic stories, and routine on-chain activity. Claude is most valuable as a scarce judgment layer after local filtering and cheap review have reduced the candidate set.

## D013: v0.7 Builds First-Hand Structured Watcher Alerts

Decision:

The next major product layer is first-hand structured intelligence, not more second-hand news scraping.

Implementation:

- Start with local watcher scripts and CSV/SQLite artifacts.
- Prioritize watched Ethereum address transfers and USDT/USDC mint/burn monitoring.
- Add DEX liquidity and protocol treasury watchers only after the first watcher layer is stable.
- Watchers emit structured alerts, not raw transaction streams.
- Convert approved watcher alerts into the existing event/backtest schema.
- Use deterministic local rules for thresholds, dedupe, entity matching, spam suppression, and routine internal-transfer suppression.
- Use Claude only for high-value uncertain structured alerts, cluster interpretation, and risk-safe wording.
- Do not build full-chain scanning, mempool monitoring, broad multi-chain indexing, Hyperliquid position tracking, UI dashboards, Telegram auto-send, or trading integration in v0.7.

Reason:

The existing news pipeline is a cleaned second-hand intake layer. Product differentiation requires information that can appear before public news: watched address movement, treasury/stablecoin supply changes, and other structured on-chain signals. Starting with curated watchlists keeps noise and model cost controlled.

## D014: First-Hand TG Publishing Uses A Strict Production Gate

Decision:

First-hand watcher alerts must pass a deterministic send gate before entering the Telegram live sender.

Implementation:

- Gate on structured fields, not message text: `amount_usd`, `event_type`, `raw_signal_type`, `risk_category`, `confidence`, and `strength`.
- Block rows with missing candidate id, missing text, missing asset, missing amount, sample/low confidence, or explicit trading-advice words.
- Keep warning rows eligible only when score remains above the minimum threshold.
- Write per-cycle gate artifacts:
  - `results/v07_tg_live_quality_gate_report.csv`
  - `results/v07_tg_live_quality_gate_summary.csv`
- Keep already-sent dedupe before send, so service restarts do not re-broadcast old signals.

Reason:

The live group should not become a raw alert firehose. Deterministic gates reduce model cost, prevent routine watcher noise, and keep the feed useful while remaining auditable.

## D015: Exchange Wallet Watchers Are High-Threshold Seeds, Not A Final CEX Flow Product

Decision:

Exchange hot wallet single-transfer alerts are allowed only as high-threshold seed monitoring. The target v0.8 design should move to net-flow aggregation.

Implementation:

- Add only source-verified high-value exchange/entity addresses.
- Use elevated thresholds for exchange wallets to suppress routine churn.
- Do not treat single exchange transfers as directional market conclusions.
- Next design task: aggregate 1h/4h/24h exchange wallet net flow before publishing most CEX wallet signals.

Reason:

Single exchange wallet transfers are noisy and often internal. Net-flow context is a better market-structure signal than one-off transactions.

## D016: Next Source Priority Is Market Structure, Not More News

Decision:

After watched addresses, stablecoin treasury, and curated Hyperliquid positions, the next sources should be market-structure feeds.

Implementation priority:

1. CEX order book depth / abnormal depth change if a reliable public source is available.
2. DEX large swaps and liquidity-depth changes for top WETH/USDC/USDT/WBTC pools.
3. Funding-rate abnormal changes for major perpetual markets.
4. Aave/Compound/Maker liquidation events.

Do not prioritize broad social scraping, NFT metrics, mempool monitoring, or more generic news scraping.

Reason:

The product needs early structural signals. More second-hand news increases volume without improving information advantage.

## D017: v0.8 Prioritizes Follow-Up And Alert Quality Over More Sources

Decision:

After CEX netflow, funding-rate anomalies, and Aave V3 liquidations are connected, do not keep adding broad sources until the live TG feed has follow-up measurement, severity, and rate-limit controls.

Implementation:

- Add automated 4h/24h/72h follow-up tracking for Telegram alerts.
- Exclude user reactions/replies from the realtime quality loop.
- Add source/token rate limits before scaling alert volume.
- Add daily usefulness metrics.
- Keep broad DEX swaps, social sentiment, mempool monitoring, UI, and paid tiers out of scope for now.

Reason:

More sources increase noise faster than they increase intelligence. The current risk is alert fatigue, not lack of raw data.

## D018: Hyperliquid And CEX Netflow Are The Primary Short-Term Sources

Decision:

The next optimization pass should focus on Hyperliquid large positions and CEX netflow quality/context before expanding lower-signal feeds.

Implementation:

- Track prior Hyperliquid position state so alerts can say whether a position opened, grew, shrank, or closed.
- Add CEX netflow rolling baseline context.
- Keep funding-rate and liquidation watchers under strict thresholds unless they correlate with stronger sources.

Reason:

Hyperliquid positions and CEX netflow currently provide the clearest first-hand market-structure signals. Funding and generic watched-address flows are more likely to be noisy without context.

## D019: Every TG Alert Needs "Why This Matters" Context

Decision:

TG output should move from raw event cards to intelligence cards. Every high-priority alert should explain why the event matters now and what should be watched next, without giving trade direction.

Implementation:

- Add context fields to TG drafts.
- Add follow-up measurement at 4h/24h after alerts.
- Add daily reports for useful alerts vs noise.

Reason:

Raw alerts are easy to ignore. The product value is not monitoring everything; it is selecting and explaining the few events that matter.

## D020: TG Send Timing Should Follow User Attention Windows

Decision:

Routine TG alert delivery should be shaped around China-time user attention windows, not fixed rigid clock rules.

Implementation:

- Keep the watcher running continuously so critical first-hand alerts are not delayed by schedule windows.
- Add a configurable China-time send policy in `config/tg_send_time_policy.csv`.
- Use the policy to raise per-cycle capacity during morning, daytime, afternoon, and evening user-attention windows.
- Keep the overnight window quiet by allowing only `critical` alerts by default.
- Keep daily/source/token rate limits active, so active windows do not turn into alert spam.

Reason:

The goal is user convenience. People check Telegram and markets more often during China-time daytime and evening trading windows. Timing policy should improve usefulness without becoming a brittle fixed timetable.

## D021: Scheduled Digests Are Separate Product Surfaces

Decision:

Daily recaps should be handled as separate scheduled digests, not mixed into the real-time alert stream.

Implementation:

- Generate China-time morning, noon, and evening digests.
- Default morning window is 20:00 previous day to 08:00 current day.
- Default noon window is 08:00 to 12:00.
- Default evening window is 12:00 to 20:00.
- Include TG alerts sent overnight, notable first-hand source counts, follow-up availability, and Binance USD-M long/short sentiment snapshots.
- Run digests by separate server-side systemd timers around 08:30, 12:30, and 20:30 China time.
- Keep the live watcher continuous and independent from the digest timer.

Reason:

Users need two different surfaces: real-time alerts for events that matter now, and scheduled summaries for catching up without reading every message.

## D022: CEX Netflow Needs Rolling Baseline Context

Decision:

CEX netflow alerts should compare the current window against recent rolling history, not only absolute USD thresholds.

Implementation:

- Store CEX entity/asset/window snapshots in `data/cex_netflow_baseline_state.csv`.
- Include baseline sample count, average absolute net flow, average gross flow, and abnormal multiple in alert metadata.
- Allow a baseline anomaly gate when current net flow is meaningfully larger than recent history.

Reason:

A fixed USD threshold misses smaller but unusual flows and overweights routine exchange churn. Baseline context makes the alert more explainable.

## D023: Hyperliquid Position Alerts Must Distinguish State Changes

Decision:

Hyperliquid whale alerts should describe state transitions, not just repeat large open positions.

Implementation:

- Continue tracking previous position state in `data/hyperliquid_position_state.csv`.
- Distinguish first seen, crossed threshold, increased, decreased, side changed, near liquidation, and closed/disappeared positions.
- Track estimated mark price and liquidation distance when available.

Reason:

Users care less that a big position exists and more that it changed, became risky, or disappeared.

## D024: Near-Term Product Focus Is CEX Netflow Plus Hyperliquid

Decision:

For the next iteration, optimize the product around CEX netflow and Hyperliquid position intelligence instead of adding more broad sources.

Implementation:

- Treat CEX netflow and Hyperliquid position changes as Tier 1 real-time alert sources.
- Keep stablecoin mint/burn and Binance long/short ratios as digest/context sources.
- Keep funding-rate and lending-liquidation watchers connected but low-maintenance unless replay/follow-up behavior proves demand.
- Convert Claude's "trading edge" language into product-safe "intelligence usefulness" and post-alert movement metrics.
- Do not add automatic trading, buy/sell/long/short instructions, or order execution.

Reason:

Claude's v0.8 project planning review was blunt: the product risk is not lack of infrastructure, it is lack of proven user value. The highest-signal current feeds are CEX netflow and Hyperliquid position changes, so the next work should prove those alerts are useful before expanding.

## D025: Automated Replay And Follow-Up Come Before More Sources

Decision:

Do not expand into broad DEX swaps, broad social sentiment, or more generic feeds until the current alert stream has a measurable replay/follow-up loop.

Implementation:

- Do not treat Telegram reactions or user replies as a quality metric.
- Do not run realtime feedback collection in the live monitor or quality loop.
- Build daily/weekly source usefulness reports using alert count, 4h/24h follow-up movement, historical replay, and source concentration.
- Add same-token/source cooldowns and source-level rate limits before raising alert volume.
- Keep DEX swap monitoring parked; if DEX is added later, start with large liquidity removal rather than raw swaps.
- Treat noon digest as a user-convenience experiment; keep it while requested, but measure whether it adds value.

Reason:

Relying on users to carefully react to Telegram messages is a weak product assumption. Most users will read, ignore, or act privately. The system should judge signal quality primarily from observable data: whether the event was timely, whether follow-up movement existed, whether similar historical events behaved consistently, and whether the source creates too much noise.

## D026: Historical Replay Is For Signal Learning, Not Direct TG Rules

Decision:

Use older historical candidates to increase sample size for signal research, but do not convert replay results directly into Telegram publishing rules.

Implementation:

- Run broad historical replay to expose aggregate behavior across more samples.
- Run conservative replay to compare against a cleaner high-score subset.
- Keep outputs under `v08_historical_replay_*` so they do not overwrite v043/v06 results.
- Treat BTC-heavy samples carefully because BTC events versus BTC benchmark flatten abnormal-vs-BTC.
- Use replay results to identify weak buckets, benchmark problems, and taxonomy pollution before changing live thresholds.

Reason:

Realtime TG has too few mature alerts for 24h/72h usefulness. Historical replay can add sample size quickly, but it inherits historical classification noise and benchmark bias. It is useful for diagnosis, not automatic publishing decisions.

## D027: Real-Time TG User Feedback Is Not A Core Product Line

Decision:

Remove realtime Telegram replies/reactions from the core quality loop. Do not optimize the intelligence system around whether users react inside the group.

Implementation:

- Live monitor no longer collects Telegram feedback.
- The TG quality loop now uses sent-state metadata, 4h/24h follow-up, and source usefulness reports.
- Historical replay remains the main way to test whether past event classes had measurable post-publication behavior.
- Local draft-review feedback can remain as an internal editorial tool, but it is not a realtime product metric.
- Next replay work should separate BTC/ETH benchmark assets, macro events, and non-BTC single-asset events.

Reason:

Telegram reactions are sparse, noisy, and easy to misread. Serious users may read without reacting, act privately, or ignore feedback prompts entirely. A better quality loop is based on observable system outputs and market follow-up, not group behavior theater.

## D028: First-Hand Source Expansion Beats More Random News Replay

Decision:

Prioritize first-hand event sources over larger random news exports.

Implementation:

- Add CEX listing announcement watcher.
- Add token unlock calendar watcher.
- Keep CEX netflow, stablecoin mint/burn, Hyperliquid positions, funding, and liquidation watchers wired into the same normalized event/TG draft path.
- Measure product usefulness through source diversity, timeliness, follow-up movement, rate-limit compliance, and user-view readability.
- Do not spend the next iteration expanding random historical news replay. The older500 replay already showed BTC/macro domination.

Reason:

The project is a Telegram intelligence product, not a research paper. Random news replay mostly adds BTC and macro noise. Differentiation comes from structured, timely, first-hand sources that users can scan during active China-time market windows.

## D029: Use Historical Replay To Triage Sources, Not To Fake Missing Source Data

Decision:

Use historical backtest/replay to triage event types and source families. Do not pretend historical news can replace source-native data:

- token unlock needs a real unlock calendar.
- CEX netflow needs rolling wallet-flow baseline snapshots.
- Hyperliquid change alerts need previous/current state snapshots.
- OKX/Bybit listing expansion needs parser-level time validation per exchange.

Implementation:

- Tightened token-unlock detection to require token-specific unlock language.
- Added historical source usefulness reports:
  - `scripts/build_historical_source_usefulness_from_backtest.py`
  - `results/v081_historical_source_usefulness_report.md`
- Added source readiness reports:
  - `scripts/build_v08_source_readiness_report.py`
  - `results/v081_source_readiness_report.md`
- Added Hyperliquid state history append:
  - `data/hyperliquid_position_state_history.csv`

Current evidence:

- v081 older500 candidate token_unlock count: 0 after stricter rules.
- v081 conservative historical replay selected 120 rows and no token_unlock rows.
- CEX netflow baseline rows: 37, still below a robust baseline.
- Hyperliquid state history exists and server watcher now appends future snapshots.

Reason:

Historical news replay is useful for detecting bad buckets, benchmark pollution, and under-sampled event types. It is not a substitute for first-hand structured source history. Treating news prose as source-native history would recreate the same dirty-data problem the project is trying to remove.

## D030: Token Unlock Uses CoinMarketCap Public Page API As First Real Calendar Source

Decision:

Use CoinMarketCap's public token-unlocks page API as the first real token unlock source. Do not wait for a manual CSV import when a no-key public source is available.

Implementation:

- Added API probe and fetch scripts:
  - `scripts/probe_token_unlock_sources.py`
  - `scripts/fetch_coinmarketcap_token_unlocks.py`
- Discovered and wired:
  - `https://api.coinmarketcap.com/data-api/v3/token-unlock/listing`
- New local outputs:
  - `data/token_unlock_calendar_cmc.csv`
  - `data/token_unlock_calendar_cmc_raw.json`
  - `results/v081_cmc_token_unlock_fetch_summary.csv`
  - `results/v081_cmc_token_unlock_quality_report.md`
- `scripts/run_v07_first_hand_watchers.py` now refreshes CMC unlock data before running `watch_token_unlock_calendar.py`.
- Token unlock quality no longer requires Binance symbol-map coverage. Binance support is a price/backtest constraint, not a live calendar-source constraint.
- TG copy now displays token-unlock `预计解锁` time in China time and separately shows `发现时间`.
- Server `/opt/crypto-event-intel-watchers` was updated and `crypto-event-intel-watchers.service` restarted.

Current evidence:

- CMC API total count: 1264.
- Fetched rows: 500.
- Future rows: 495.
- Rows in next 72h: 234.
- Current watcher threshold emitted 5 token_unlock alerts.
- Quality gate only lets meaningful unlocks through; low-dollar high-percent unlocks remain blocked.

Reason:

The previous “real calendar needed” blocker was a data-source problem, not a code problem. A direct public page API is enough for the first live token-unlock source. The source should be monitored for schema breakage because it is not a formal paid API contract, but it is immediately useful for TG intelligence.

## D031: Show New Sources In TG Now, While Keeping Quality Gates

Decision:

New first-hand sources should be visible in the Telegram group during the pilot. Do not wait for days of passive accumulation before showing users the product surface.

Implementation:

- Server send limit changed from the default 15/day to 45/day.
- Server per-cycle send limit changed from 3 to 5.
- Hyperliquid watcher now supports current large-position snapshot alerts:
  - `--alert-first-seen true`
  - `--alert-snapshot true`
- CEX netflow baseline can be seeded from recent historical Etherscan transfers:
  - `scripts/seed_cex_netflow_baseline_from_transfers.py`
  - latest server seed: 6000 raw transfers, 1097 used transfers, 24 new 4h buckets, 384 baseline rows.
- TG drafts now add source-specific context:
  - token unlock: distance to unlock, circulating percentage, allocation object, discovery time.
  - CEX netflow: direction, inflow/outflow, historical baseline sample count, abnormal multiple, trigger gate.
  - Hyperliquid: side, snapshot/change type, entry/liquidation price, liquidation distance when available.
- Quality gate adjusted so 30M+ Hyperliquid positions are at least warning candidates instead of being incorrectly blocked.

Observed server result:

- First new-source send after change:
  - ETH Hyperliquid position snapshot.
  - HYPE Hyperliquid position snapshot.
  - HOME token unlock.
- Next cycle:
  - BTC Hyperliquid position snapshot.

Reason:

The pilot needs visible product feedback. Purely waiting for state history makes the group look unchanged even when the backend is working. Current-position snapshots solve that for Hyperliquid without turning it into a trading signal; CEX baseline seeding uses historical transfer data rather than waiting passively.

## D032: Move Telegram From Full-Card Feed To Market Radar

Decision:

The main Telegram surface should become a market radar, not a full-card alert feed.

Implementation direction:

- Main group/channel:
  - ranked board snapshots during China-time active windows
  - rare interrupt alerts
  - morning/noon/evening digests
- Detail cards:
  - used only for high-severity events or linked drill-down context
  - security, major Hyperliquid, major stablecoin/CEX flow, large unlocks
- Archive/history:
  - keep lower-priority qualified events for follow-up and source usefulness analysis
  - do not push every qualified event to the main group

Product rules:

- Compact ranked rows are preferred over explanatory prose in the main channel.
- Full card verbosity is acceptable only when the event deserves detailed context.
- Main-channel volume should stay low enough that users do not need to scroll heavily.
- The next sprint should build board generation and severity routing before adding more broad sources.

Reason:

Claude's product review identified the current risk: the system is backend-first and treats too many events as deserving full cards. A Telegram user needs an attention filter. The useful first version is a scannable board plus rare high-signal interrupts, not a larger news feed.

## D033: Pause Dense Radar And Redesign Around Mobile Readability

Decision:

The first v0.9 market-radar board was technically functional but too dense for real Telegram use. It exposed backend terms, raw scores, wallet fragments, and too many rows. The server auto-sender is paused until the message surface passes a mobile readability gate.

Implementation:

- Main radar messages now use at most five items and two sections.
- Raw scores, raw addresses, backend source labels, raw liquidation prices, and unexplained ratios are hidden from the main feed.
- Hyperliquid leaderboards are no longer treated as intelligence by default.
- Static large positions are archive/context unless they are near liquidation, materially changed, or tied to a known entity with unusual exposure.
- Detail cards no longer use the repeated `事件 / 详情 / 解读` structure.
- Generic interpretation text has been replaced with a specific `关注点` line or omitted.
- Displayed times are normalized to China time.

Evidence:

- Claude review: `results/v09_claude_tg_readability_review.md`
- Redesign plan: `docs/V09_TG_READABILITY_REDESIGN_PLAN.md`
- Board generator: `scripts/build_tg_market_radar_board.py`
- Detail-card generator: `scripts/generate_watcher_tg_drafts.py`
- Latest board summary: `results/v09_tg_market_radar_board_summary.csv`

Reason:

The product should filter attention, not force users to decode raw monitoring output. If a message needs an instruction footer explaining how to read it, the message format is wrong.

## D034: Shift Next Sprint To Measured Signal Quality Before More Sources

Decision:

The next project phase prioritizes Telegram alert outcome measurement and quant-facing data quality before adding more sources or richer UI.

Accepted direction:

- Every Telegram alert/radar item should become a structured `alert_id` with publish status and message id.
- Every published item should be automatically evaluated after 1h / 4h / 24h / 72h.
- Daily quality reports should rank event types, sources, assets, and repeated alerts by usefulness.
- New source expansion is deferred unless it directly improves a measured weak spot.
- Quant collaboration should start with a clean CSV/SQLite data package, not a vague product demo.

Near-term implementation:

- Add a TG alert ledger.
- Add post-publish outcome evaluation.
- Add price-in and simple regime tags.
- Prepare quant export files and a data dictionary.
- Use results to reduce low-quality event types and repeated static facts.

Evidence:

- Prompt: `docs/CLAUDE_V10_QUANT_COLLABORATION_PROMPT.md`
- Claude response: `results/v10_claude_quant_collaboration_plan.md`
- Continuation prompt: `docs/CLAUDE_V10_QUANT_COLLABORATION_CONTINUATION_PROMPT.md`
- Continuation response: `results/v10_claude_quant_collaboration_continuation.md`
- Plan: `docs/V10_QUANT_COLLABORATION_AND_SIGNAL_QUALITY_PLAN.md`

Reason:

The system already publishes and backtests, but it has not yet proven which live intelligence types are useful. More feeds will increase noise unless the publish-evaluate-learn loop is in place.

## D035: Pause Intraday Radar Until v14 Data-Quality Gates Pass

Decision:

暂停盘中雷达和高频观察池推送。当前阶段只允许早报/晚报这类摘要型输出，并且必须从已通过质量闸门的候选事件中生成。

Accepted direction:

- 不再把“可监控到”直接等同于“值得推送到群”。
- `webhook` 必须拆成子来源后再评分，`webhook_unknown` 默认阻断。
- `needs_taxonomy_review` 不能直接进入 Telegram，需要先拆成可解释的细分桶。
- ETF/基金流只保留有金额、头部发行方或明确 ETF/资金流语境的内容。
- active exploit 只保留有明确 hack/exploit/drain/breach 上下文、金额可解析、且来源分达标的内容。
- 所有不满足来源分、金额语境、资产一致性或时间质量的内容，只能进入历史分析或人工/规则复核，不能进入实时推送。

Evidence:

- Claude review: `results/v13_claude_quality_audit_continuation.md`
- Claude continuation: `results/v13_claude_extended_replay_review.md`
- Time diagnosis: `results/v14_time_field_diagnosis.md`
- Source split: `results/v14_webhook_split_report.md`
- Taxonomy cleanup: `results/v14_needs_taxonomy_review_report.md`
- ETF/fund-flow filter: `results/v14_etf_fund_flow_filter_report.md`
- Active exploit verification: `results/v14_active_exploit_amount_verification_report.md`
- Strict digest preview: `results/v14_digest_preview.md`

Reason:

当前问题不是能不能发，而是发出去是否可信、是否可读、是否会制造噪音。盘中雷达需要更高的数据质量和更强的历史验证；在此之前，摘要型输出更符合用户阅读习惯，也更不容易把弱信号包装成结论。

## D036: v14 Publisher Uses Hard Gates Plus Event-Specific Routes

Decision:

Composer 和 Publisher 不再使用总分作为主要发布依据。v14 改为硬门槛：先做 PreFilter，再做 Composer gate，最后由事件类型专属路由决定是否进入摘要。

Accepted direction:

- Flow 事件拆成 `etf_creation_redemption`、`cex_netflow`、`institutional_disclosure`、`etf_macro_news`、`flow_unclear`，不同子类进入不同发布通道。
- ETF 申赎/流量必须有明确金额和上下文；ETF 宏观新闻、机构披露默认不做盘中推送。
- Security/exploit 必须分离受害协议、被盗资产、受影响可交易资产、主资产置信度。
- PreFilter 使用 5m/15m/1h price-in 检查补足 6h 检查，已明显提前反应的事件不进入摘要。
- `upgrade_or_fork` 可以进入摘要，但仅限明确主网/硬分叉/共识升级/有时间锚点的事件；常规 SDK、模糊路线图和价格观点默认阻断或背景化。
- TG 摘要不展示模型分数，只展示事件、资产、类型、来源/上下文和风险提示。

Evidence:

- Claude review: `results/v14_claude_composer_policy_review.md`
- Claude gate review: `results/v14_claude_gate_policy_review.md`
- Short price-in: `data/v14_short_price_in.csv`
- Upgrade classification: `data/v14_upgrade_events.csv`
- Composer gate output: `data/v14_composer_scores.csv`
- Publish policy output: `data/v14_publish_policy_candidates.csv`

Reason:

加权总分会掩盖来源差、资产归因差、价格已提前反应等硬问题。不同事件类型的信息价值不同，应该走不同通道：盘中只发强时效异动，早晚报发背景型结构信息，无法解释的内容只归档。
