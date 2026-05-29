# Reference Document Learnings

Sources:

- `data/reference_docs/coin_nebula_ai_quant.pptx`
- `data/reference_docs/bazhuo_quant_robot_manual.pdf`
- extracted text:
  - `results/reference_coin_nebula_ppt_text.md`
  - `results/reference_bazhuo_pdf_text.md`

## Important Boundary

These reference files describe quant robots, strategy execution, copy trading, API binding, stop loss, take profit, position management, and monetization.

Our project should not copy the trading-bot/execution part.

Useful ideas should be translated into a Telegram intelligence product:

- data organization
- user-facing ranking
- risk explanation
- logs and traceability
- parameter transparency
- dashboard/board thinking
- operational clarity

Do not implement:

- exchange API trading
- copy trading
- explicit directional trade-signal output
- automated execution
- portfolio/wallet management
- referral/payment/activation-code logic

## Useful Product Ideas

### 1. Ranking Is A Core User Surface

The Bazhuo document mentions real-time rankings with daily, weekly, and total boards.

Applicable to us:

- TG should have ranked boards, not only one-off alerts.
- Useful ranking periods:
  - 1h radar
  - 4h radar
  - 24h radar
  - daily recap
  - weekly source usefulness

Concrete boards:

- Hyperliquid large-position board
- OI/funding crowding board
- token unlock board
- stablecoin/CEX flow board
- source usefulness board

### 2. Every Signal Needs Parameter Transparency

Both references explain strategy parameters in detail:

- strategy type
- time period
- indicator
- threshold
- trigger condition
- stop/exit condition

Applicable to us:

Every TG alert/board item should expose why it appeared:

- source
- metric
- threshold
- amount
- relative size
- time
- whether it is new or known-in-advance
- whether it is board-only or interrupt-grade

This improves trust more than generic prose.

### 3. Risk Controls Should Be Visible

Coin Nebula repeatedly emphasizes risk control:

- anti-crash mechanism
- trailing stop
- reverse signal handling
- frequency control
- asset/product control
- trading session control
- 24h monitoring

Applicable to us:

Replace trading controls with information controls:

- anti-spam mechanism
- token cooldown
- source daily cap
- microcap filter
- time-window routing
- interrupt threshold
- archive-only bucket
- false-urgency detection

These controls should appear in internal reports and occasionally in user-facing wording:

```text
本条进入雷达板原因：金额超过阈值，且为结构化一手数据。
未作为实时打断原因：属于计划内解锁，非突发事件。
```

### 4. "We Do Not Predict, We Respond" Fits Our Product

Coin Nebula has a useful sentence:

> 我们不对行情作预测，但是我们可以对行情作出应对。

For us, a safer version:

```text
我们不预测行情，也不提供交易指令；我们把市场结构、链上资金和事件变化整理成可复核情报，帮助用户更快发现值得关注的变化。
```

This should become a product principle.

### 5. Logs And Traceability Matter

Bazhuo emphasizes robot logs and operation logs.

Applicable to us:

Every TG board/alert should be traceable:

- board_id / alert_id
- source file/API
- generated time China
- raw watcher row
- threshold rule
- routing decision
- follow-up backfill result

This supports post-event review and makes the system credible.

### 6. User-Facing Lists Should Show State, Not Just Text

Bazhuo's strategy pages show parameters in both list and detail views.

Applicable to us:

Main TG board should show compact state:

- asset
- metric
- magnitude
- time
- reason

Detail view/file should show:

- raw source
- threshold
- context
- follow-up
- caveats

## Concrete Changes To Our v0.9 Plan

Add to v0.9:

1. Board period labels:
   - 1h
   - 4h
   - 24h
   - daily

2. Routing reason should be user-readable:
   - `major_position_over_100m`
   - `unlock_board`
   - `small_unlock_archive_only`

3. Add source/routing transparency to board footer or detail card:

```text
筛选：金额阈值 + 冷却时间 + 来源上限 + 微盘过滤。
```

4. Add weekly source usefulness ranking:

```text
本周信号源表现
1. Hyperliquid 大额仓位：23 条，4h 后正向异常 61%
2. Token Unlock：12 条，24h 可计算 9 条
3. Stablecoin Flow：8 条，样本不足
```

5. Add "known-in-advance" label:

- token unlock: planned
- listing announcement: fresh announcement
- whale/position/netflow: live observation

This prevents scheduled events from feeling like false breaking news.

## What Not To Adopt

Do not adopt:

- "稳定收益" style promises
- trading strategy promotion language
- copy-trading framing
- API key binding workflow
- leverage/position management UX
- user wallet/payment/rebate modules
- "AI trading" claims

These would move the project away from event intelligence and toward a regulated/high-risk trading system.
