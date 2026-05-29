# v0.9 Telegram Readability Redesign

Source:

- `docs/CLAUDE_V09_TG_READABILITY_REVIEW_PROMPT.md`
- `results/v09_claude_tg_readability_review.md`

## Diagnosis

The current Telegram output is technically correct but product-poor. It looks like a database dump rather than intelligence.

Main failures:

- The board shows too many rows and too many fields.
- Backend terms leak into user-facing messages.
- Raw scores, addresses, source codes, and liquidation prices are shown without context.
- Detail cards repeat the same event in title, event, details, and interpretation.
- The generic interpretation text does not add usable information.
- Hyperliquid position size is treated as a signal by itself, which creates noise.

## Product Decision

Pause v0.9 auto-send until the message surface passes a mobile readability gate.

The main Telegram group should receive:

- Rare urgent interrupts.
- Compact hourly/digest radar messages.
- Only high-materiality items.

The main group should not receive:

- Hyperliquid leaderboards.
- Long/short ratio tables unless extreme.
- Small token unlocks.
- Stablecoin or CEX flow rows without size context.
- Generic interpretation paragraphs.
- Raw backend labels or unknown wallet addresses.

## New Main Feed Rules

Every market radar message must follow these constraints:

- Max 5 items total.
- Max 2 sections.
- Each item is one natural Chinese sentence.
- No raw scores.
- No raw addresses.
- No backend source labels.
- No repeated event/detail/interpretation blocks.
- Every number must have a user-level meaning.

Default sections:

```text
📡 HH:MM 市场雷达

⚠️ 优先关注
• ...

📊 结构信号
• ...

仅供市场观察，不构成交易建议。
```

## Signal Thresholds

Main-feed thresholds:

- Token unlock: amount >= 10M USD and circulating share >= 5%.
- CEX netflow: amount >= 500M USD.
- Stablecoin mint/treasury flow: amount >= 500M USD unless cumulative context is added.
- Hyperliquid: only if liquidation distance <= 5%, position change >= 50%, known entity with unusual asset exposure, or realized close/PnL event.
- Long/short crowding: only if crowding score >= 80, then translate to user language.

Archive-only:

- Static Hyperliquid position snapshots.
- Unknown whale rows without liquidation risk.
- Ordinary long/short ratio readings.
- Small unlocks.
- Small stablecoin flows.

## Detail Card Rules

Detail cards must not repeat the same sentence across title, event, details, and interpretation.

Required shape:

```text
⚡ Title

时间：China time
主体：entity
规模：amount

关键事实：
...

关注点：
...

仅供市场观察，不构成交易建议。
```

The `关注点` line must contain a specific implication or be omitted. Generic phrases such as “需结合价格、资金费率复核” are banned.

## Engineering Tasks

1. Replace the board generator with a compact two-section radar.
2. Add readability lint for backend leakage, item count, and line length.
3. Simplify watcher detail-card generation.
4. Keep the server sender paused until local preview passes.
5. Restart server only after a manual preview check.

## Rolling Intraday Radar Update

Accepted after live preview:

- The intraday radar can run more often, roughly every 1 hour during active periods.
- It should summarize the last cycle's effective signals rather than repeat static facts.
- Priority order:
  1. Hyperliquid / whale position changes.
  2. CEX netflow or stablecoin flow above threshold.
  3. Extreme long/short or funding indicators.
  4. Static known-entity large positions.
  5. Token unlocks, at most one intraday item unless it becomes urgent.
- Price context can be attached to non-stablecoin items when available.
- Static items use repeat cooldowns:
  - token unlock: 8h intraday cooldown
  - static large position: 4h cooldown
  - long/short indicator: 2h cooldown
  - flow item: 1h cooldown
- If all candidates are suppressed as repeats, the sender skips the board instead of posting an empty radar.

Implementation:

- `data/tg_radar_item_state.csv`
- `scripts/build_tg_market_radar_board.py`
- `scripts/send_tg_market_radar_board.py`
- `scripts/run_v09_market_radar_cycle.py`
