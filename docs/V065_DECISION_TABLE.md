# v0.6.5 Decision Table

## Main Decision

Do not connect TG yet.

v0.6.5 continues to improve event understanding and review queues. TG publishing starts only after manual ground truth exists.

## Channel Routes

| route | meaning | examples | current action |
|---|---|---|---|
| `alpha_candidate` | Direct asset event with tradable asset and likely market relevance | hack, whale transfer, exchange flow, concrete on-chain data | human review only |
| `macro_policy` | Market-wide macro, regulation, BTC reserve, policy | SEC, Fed, Bitcoin reserve, market structure bills | separate review queue later |
| `research_only` | Indirect adoption, payment, legal, miner equity, broad research | Revolut crypto card, HIVE AI factory, fraud sentence, RWA adoption | no TG main stream yet |
| `unsupported_research` | Relevant asset but pricing/backtest support incomplete | HYPE, ONDO, WLD if no supported price source | research only, may inform whitelist expansion |

Important rule: unsupported pricing is not the same as irrelevant news.

- Do not invent Binance symbols for assets Binance does not support.
- Keep the symbol map honest. Empty Binance fields mean the asset cannot enter the Binance price backtest.
- If the event is high-value and the asset is unsupported, route it to `unsupported_research` and `human_review`.
- Supported-price events can enter backtest; unsupported-price events can only enter research review until a real public pricing provider is added.

## Auto Publish Rule

`auto_publish` remains disabled in practice for now.

The scoring script now hard-downgrades every would-be `auto_publish` row to `human_review`. This prevents accidental TG publishing before manual ground truth exists.

Minimum future standard:

- source_count >= 2
- direct asset event
- supported price source
- cluster primary
- not macro/regulation
- not other_review
- not research_only
- reviewed event_type historically has acceptable outcome

## Human Review Rule

`human_review` is the only path toward future TG publishing.

Required manual labels:

```text
manual_decision = approve_publish / keep_review / discard / fix_taxonomy
manual_event_type_l1
manual_event_type_l2
manual_primary_asset_symbol
manual_channel_route
manual_useful_for_research
manual_notes
```

Use this command to generate a single review sheet:

```powershell
python scripts/prepare_v06_manual_label_sheet.py --output data/v06_manual_label_sheet.csv --summary results/v06_manual_label_sheet_summary.csv
```

## Taxonomy Updates

Added:

- `onchain_data`
- `legal_enforcement`
- `protocol_incident` under `hack_security` for first-party protocol incident statements such as abnormal markets, paused markets, and investigation notices
- `tradability_tier`
- `primary_discard_reason`
- `secondary_discard_reasons`
- `channel_route`

## Ground Truth Requirement

Before v0.7 TG publishing, collect at least 200 manually reviewed rows.

Minimum labels:

- publish decision correctness
- event type correctness
- primary asset correctness
- whether event was concrete/factual
- whether event was useful for trading research
- whether it should appear in TG main stream, macro stream, or research-only

## Current v0.6.5 Result

Latest older500 run:

- total: 500
- auto_publish: 0
- human_review: 72
- discard: 428
- other_review: 210
- T1: 46
- T2: 163
- T3: 281
- T4: 10
- unsupported_research: 10 total, 5 currently in publish review queue

Interpretation:

- The system is correctly conservative.
- The review queue is still broad.
- `other_review` and `missing_entity` remain the biggest quality targets.
- Ground truth is now the main blocker before TG.
