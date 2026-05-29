# v0.9 Telegram Market Radar Plan

Sources:

- `results/v08_claude_tg_product_card_review.md`
- `results/v08_claude_tg_product_card_review_continuation.md`
- `docs/REFERENCE_DOC_LEARNINGS.md`

## Core Diagnosis

The current system is technically working, but the product is still too backend-first.

The main Telegram channel should not be a stream of full explanatory cards. A real user needs to scan what matters in 15-30 seconds. The product should become a market radar:

1. ranked board snapshots
2. rare realtime interrupt alerts
3. scheduled digests
4. detail cards only when the item deserves context

Single full cards remain useful, but they should not be the default surface for every event.

## v0.9 Readability Correction

After the first live board was sent, the output was paused and reviewed again because it was still too dense for Telegram mobile reading.

Accepted corrections:

- A radar message is not a table. It must be an attention filter.
- Max five items per message.
- Max two sections per message.
- Hide raw scores, backend labels, wallet fragments, raw liquidation prices, and unexplained ratios.
- Remove the `阅读方式` footer. If the product needs reading instructions, the format has failed.
- Do not show Hyperliquid position leaderboards by default. Size alone is not enough.
- Long/short crowding only appears when extreme and translated into natural language.
- Token unlocks only appear in the main feed when they are both large and material to circulating supply.
- Single event cards must not repeat the same content in `事件`, `详情`, and `解读`.

New implementation reference:

- `docs/V09_TG_READABILITY_REDESIGN_PLAN.md`
- `results/v09_claude_tg_readability_review.md`

## Accepted Product Direction

### Main Channel

Use the main Telegram group/channel for:

- 3-4 ranked board snapshots per China trading day.
- 1-3 rare interrupt alerts per day.
- Morning/noon/evening digests.

If the main channel exceeds roughly 10 high-attention messages per day, the product is becoming a firehose.

### Detail Surface

Use detail cards for:

- security incidents
- major Hyperliquid positions
- major stablecoin/CEX flows
- large token unlocks
- items linked from board snapshots

Detail cards can be longer, but the main channel should remain scannable.

### Archive Surface

Keep lower-priority qualified events in local CSV/SQLite and optional no-notification archive output. Do not force every qualified event into the main group.

## What To Keep

- Hyperliquid large-position tracking.
- Token unlock calendar from CoinMarketCap public page API.
- Stablecoin treasury and CEX flow monitoring.
- Funding, long/short, and OI-style market-structure context.
- Binance price backfill and abnormal return follow-up.
- Time provenance and China-time display.
- Quality gates, token cooldowns, and source caps.

## What To Cut Or Deprioritize

- Full verbose cards for every event.
- Generic BTC/ETH macro news as a main product surface.
- `other` category alerts.
- Low-dollar token unlock alerts.
- Random news export expansion as the main way to improve the live product.
- Social/KOL heat as realtime alerts.
- User-reply/reaction feedback as a core quality metric.
- Web dashboard, portfolio tracking, AI chatbot, and strategy builder.

## Realtime Interrupt Rules

Realtime interrupts should be rare. Use the test:

Would a professional crypto user want to know this within 60 seconds, even if busy?

Eligible interrupt classes:

- security incident or protocol exploit over roughly 1M USD
- curated address/watchlist movement over roughly 50M USD
- stablecoin treasury mint/burn/transfer over roughly 100M USD
- Hyperliquid position over roughly 100M USD, preferably new and with history
- CEX netflow over roughly 500M USD in 1h
- exchange halt/delisting/security event

Digest/board-only classes:

- token unlocks below 50M USD
- ordinary news articles
- ordinary macro headlines
- funding rate moves unless extremely crowded
- social/KOL heat
- price-only moves without OI/volume/source confirmation

## Board Snapshot Templates

### Market Structure Board

```text
📊 午间市场扫描 11:00

【持仓异动 1h】
1. HYPE +$42M OI ↑38% | $2.34 ↑12% | 新增杠杆
2. AAVE +$18M OI ↑24% | $289 ↑8%
3. DOGE -$31M OI ↓15% | $0.18 ↓3% | 平仓/去杠杆

【资金费率极端】
• ORDI 年化 +180% | 多头拥挤
• PENDLE 年化 -45% | 空头拥挤

【今日大额解锁】
• APT $31M 15:00 | 占流通 2.8%
• IMX $18M 20:00 | 占流通 1.2%

⚠️ 情报观察，不构成交易建议。
```

### Hyperliquid Board

```text
🐋 Hyperliquid 大额仓位

• BTC +$127M 多头 @$64.2K | 新开
• ETH +$34M 多头 @$3.45K | 新开
• HYPE -$23M 空头 @$22.8 | 新开

重点看：是否继续加仓、是否快速平仓、是否接近清算。
```

### Token Unlock Board

```text
🔓 今日解锁雷达

1. APT $31M | 15:00 UTC+8 | 占流通 2.8%
2. IMX $18M | 20:00 UTC+8 | 占流通 1.2%

排序依据：解锁美元规模、流通占比、释放对象、历史影响。
```

## Detail Card Rules

### Security Event Detail

Must show:

- risk level
- risk tag
- affected asset/protocol
- estimated loss
- core cause
- key facts
- affected addresses/contracts
- source attribution
- current market impact

### Hyperliquid Detail

Must show:

- asset
- side
- notional size
- entry price
- current price
- unrealized PnL if available
- address
- position age
- liquidation distance
- leverage if available
- previous state/history
- warning that the position can change anytime

Avoid saying "smart money" or implying the user should follow the wallet.

### Stablecoin/CEX Flow Detail

Must show:

- asset
- exchange/entity
- inflow/outflow/mint/burn
- 1h/24h amount
- baseline multiple
- sample count
- possible interpretations
- follow-up observation points

Do not imply stablecoin mint, CEX outflow, or CEX inflow has one fixed directional meaning.

## Ranking And Quality Gates

Use a simple deterministic ranking first:

```text
score = absolute_size + relative_size + first_hand_bonus + liquidity_weight - noise_penalties
```

Recommended buckets:

- `interrupt`: immediate, rare, high confidence.
- `board`: include in next scheduled ranked board.
- `archive`: keep for history/follow-up, no notification.
- `discard`: log and suppress.

Hard filters:

- microcap or very low 24h volume: never interrupt
- same token: max 1 interrupt per day, max 3 board mentions per day unless severity escalates
- same source: cap interruptions per day
- token unlock below 10M USD: generally archive only
- token unlock 10-50M USD: digest/board only
- token unlock above 50M USD or above 5% circulating: board eligible

False urgency checks:

- if the event was knowable for weeks/months, prefer digest over interrupt
- if signal is only reacting to a price move, prefer board/digest
- if source is a recycled news article, penalize it
- if a large position is old, do not treat it as new

## Metrics That Matter

Primary live product metrics:

- board views or board command usage per day
- repeat viewers per day
- alert-to-board click/view rate if buttons/links are available
- digest open/view timing by China-time window
- alert volume per day
- source concentration
- token concentration

Signal quality metrics:

- alert to 1h/4h/24h/72h price movement
- abnormal return versus BTC/ETH
- false-positive rate by alert class
- missed large movers without prior alert
- source usefulness by event type
- whether combined signals outperform isolated signals

Do not optimize for:

- total message count
- number of sources connected
- raw feature count
- Telegram reactions/replies

## Historical Replay Policy

Use historical replay for:

- threshold calibration
- source/event-type triage
- timing-window checks
- pre-event price-in checks
- false-positive pattern detection
- benchmark pollution detection

Do not pretend historical replay proves:

- user attention
- future causality
- rare black-swan behavior
- stable performance across market regimes

Replay should support live product tuning, not become the product.

## AI Usage Policy

Use deterministic rules for most live alert decisions:

- numerical thresholds
- OI/funding changes
- CEX/stablecoin flow thresholds
- token unlock timing/size
- cooldown/rate limit

Use AI selectively for:

- messy news deduplication
- exploit/security event severity summaries
- long governance/protocol document summarization
- borderline event classification
- Chinese rewrite of already-validated facts

Do not use AI as the primary gate for numerical signals. Do not let AI invent numbers, source facts, or directional trade conclusions.

## 7-Day Execution Plan

1. Build a ranked board generator from existing watcher outputs.
   - OI/position changes.
   - funding extremes.
   - token unlocks.
   - stablecoin/CEX flows.

2. Change TG live monitor routing.
   - main channel: boards, digests, rare interrupts.
   - full detail cards only for interrupt-grade or linked detail items.

3. Add board-style TG formatting.
   - compact Chinese lines.
   - ranked rows.
   - amount, percent, asset, source, China time.

4. Tighten interrupt thresholds.
   - Hyperliquid snapshot alerts should be board-first unless very large/new.
   - token unlocks should be board-first unless unusually large.

5. Add source concentration and token concentration reports to the daily quality loop.

6. Add OI/funding board context from public exchange APIs where available.

7. Run the live system for several China-time sessions and compare:
   - number of main-channel messages
   - board readability
   - false urgency
   - follow-up returns

## 30-Day Plan

Week 1:

- ship board-first TG surface
- keep existing live watchers
- reduce full-card spam

Week 2:

- strengthen CEX flow and stablecoin baselines
- add better 1h/24h market-structure boards
- track Hyperliquid alerted-position outcomes

Week 3:

- improve token unlock ranking using historical impact and recipient type
- add pre-event/predictable-event handling
- add missed-mover analysis

Week 4:

- test with real users, but measure behavior rather than relying on feedback
- kill weakest alert class
- double down on the source with best usefulness and lowest noise

## Do Not Build Yet

- broad social sentiment scraping
- Discord/Telegram scraping
- web dashboard
- portfolio tracking
- AI chatbot
- generalized strategy builder
- broad multi-chain support
- generic macro/news feed

## Minimum Useful Product Bar

The first useful version is not "many sources connected".

The first useful version is:

- users can check a concise TG board 3 times per day
- the board is faster than checking multiple market apps manually
- alerts are few enough that users do not mute the group
- every interrupt feels justified after reading it
- daily digest helps users catch up without scrolling
- follow-up reports show which source classes are producing signal versus noise

## Immediate Engineering Implication

Next work should prioritize:

1. board generator
2. TG routing by severity bucket
3. compact board/card templates
4. stronger interrupt thresholds
5. source/token concentration metrics

This is a product-shape change, not a data-source expansion sprint.

## 2026-05-28 Local Implementation Pass

Implemented:

- `scripts/build_tg_market_radar_board.py`
  - Reads current watcher outputs.
  - Builds compact Chinese HTML Telegram board text.
  - Current sections:
    - Hyperliquid 大额仓位
    - 解锁雷达
    - 多空拥挤
    - 资金/稳定币流向 when rows exist
- `scripts/route_tg_items_by_severity.py`
  - Adds `delivery_bucket`:
    - `interrupt`
    - `board`
    - `archive`
    - `discard`
  - Adds routing reason and eligibility flags.
- `scripts/run_v09_market_radar_cycle.py`
  - Runs first-hand watchers.
  - Routes TG draft items.
  - Builds the market radar board.
- `scripts/send_tg_market_radar_board.py`
  - Sends the latest market radar board only when `--send` is explicitly passed.
  - Records sent boards in `data/tg_board_sent_state.csv`.
  - Prevents duplicate board sends in the same China-time hour unless `--force` is used.

Latest local command:

```powershell
python -X utf8 scripts/run_v09_market_radar_cycle.py --hours 24 --limit-alerts 100 --sample-if-no-key false
```

Optional live send after preview:

```powershell
python -X utf8 scripts/run_v09_market_radar_cycle.py --hours 24 --limit-alerts 100 --sample-if-no-key false --send-board
```

Latest local outputs:

```text
data/tg_market_radar_boards.csv
data/tg_drafts_v09_routed.csv
data/tg_board_sent_state.csv
results/v09_tg_market_radar_board.md
results/v09_tg_market_radar_board_summary.csv
results/v09_tg_market_radar_send_summary.csv
results/v09_tg_delivery_routing_summary.csv
results/v09_market_radar_cycle_summary.csv
```

Latest local summary:

```text
status: pass
board_section_count: 3
board_hyperliquid_rows: 5
board_token_unlock_rows: 1
board_long_short_rows: 5
interrupt_count: 1
board_count: 5
archive_count: 4
discard_count: 0
```

Important product fix:

- Small token unlocks no longer enter the main board only because percentage is high.
- Current default unlock board rule:
  - amount >= 10M USD, or
  - amount >= 1M USD and circulating unlock percent >= 5%.

Next implementation step:

- Wire the live monitor to send board snapshots in active China-time windows.
- Keep individual interrupt alerts rare.
- Archive or suppress lower-priority full cards from the main group.

## 2026-05-28 Server Integration

Deployed to server:

```text
/opt/crypto-event-intel-watchers/scripts/build_tg_market_radar_board.py
/opt/crypto-event-intel-watchers/scripts/route_tg_items_by_severity.py
/opt/crypto-event-intel-watchers/scripts/run_v09_market_radar_cycle.py
/opt/crypto-event-intel-watchers/scripts/send_tg_market_radar_board.py
/opt/crypto-event-intel-watchers/run_v09_tg_market_radar_server.sh
```

Systemd service changed:

```text
service: crypto-event-intel-watchers.service
old ExecStart: /opt/crypto-event-intel-watchers/run_v07_tg_live_monitor_server.sh
new ExecStart: /opt/crypto-event-intel-watchers/run_v09_tg_market_radar_server.sh
status: active
```

Server runner behavior:

- Runs the existing first-hand watcher pipeline.
- Routes draft items into interrupt / board / archive / discard.
- Refreshes Binance long-short context.
- Builds a compact market radar board.
- Sends the board to Telegram with duplicate-hour protection.
- Sleeps for `V09_RADAR_INTERVAL_SECONDS`, default 7200 seconds.

First server send evidence:

```text
results/v09_market_radar_cycle_summary.csv
status: pass
board_section_count: 4
board_hyperliquid_rows: 5
board_token_unlock_rows: 1
board_long_short_rows: 5
interrupt_count: 2
board_count: 7
archive_count: 4
send_board_status: sent

results/v09_tg_market_radar_send_summary.csv
status: sent
board_label: 盘中市场雷达
telegram_message_id: 596
```

After restart, duplicate-hour protection worked:

```text
send_board_status: skipped_duplicate_hour
```

Operational note:

- The old v0.7 script remains on the server for rollback.
- The active service now runs v0.9 board-first Telegram output instead of the old full-card-first loop.

## 2026-05-28 Reference Document Learning

Reference files reviewed:

- `data/reference_docs/coin_nebula_ai_quant.pptx`
- `data/reference_docs/bazhuo_quant_robot_manual.pdf`

Accepted learning:

- Use ranking surfaces: 1h / 4h / 24h / daily boards.
- Make trigger parameters visible: source, metric, threshold, amount, relative size, route.
- Treat anti-spam/quality controls as our equivalent of "risk controls":
  - token cooldown
  - source cap
  - microcap filter
  - interrupt threshold
  - archive-only routing
- Keep traceability:
  - board_id
  - alert_id
  - raw source
  - threshold rule
  - routing reason
  - follow-up result
- Use the principle:
  - We do not predict markets or provide trading instructions.
  - We organize market structure and event changes into verifiable intelligence.

Rejected learning:

- Do not copy trading robot execution logic.
- Do not add copy trading.
- Do not add API key trading flows.
- Do not add buy/sell/long/short recommendations.
- Do not use "stable profit" or trading-promise language.
