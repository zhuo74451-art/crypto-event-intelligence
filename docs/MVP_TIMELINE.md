# MVP Timeline

Last updated: 2026-05-27 UTC+8

## Definition

The first usable version is not a trading system. It is a private event-intelligence workflow:

```text
real news export -> event intake -> relevance/entity filter -> local TG-style drafts -> review feedback -> research/backtest audit
```

It does not connect exchange order APIs, does not auto-send, and does not generate buy/sell/long/short recommendations.

## Current Status

Already working:

- Real 500-row news export pipeline.
- Time normalization with China-time review fields and UTC API fields.
- Symbol/entity enrichment.
- Relevance scoring and discard routing.
- Binance price backfill and quality checks.
- Claude consultation loop.
- Local TG draft generation.
- TG draft validation.
- TG draft feedback summary.
- One-command daily private-pilot runner.
- One-page daily private-pilot report.
- Project dashboard and command registry.

Current product constraint:

- Statistical event-type conclusions are not ready.
- TG draft private pilot can proceed as a product smoke test.

## Estimate

### Local Private Draft MVP: 0-1 day

Status: implemented locally.

Remaining:

- Review 20 generated local drafts.
- Record `reviewer_decision`, `reviewer_usefulness`, `reviewer_issue_type`, and `reviewer_notes`.
- Run the feedback summary.

### Operator-Usable Daily Workflow: 1-2 days

Status: first local version implemented.

Implemented:

- One-command local daily runner: `python scripts/run_daily_private_pilot.py`
- Daily report: `results/daily_private_pilot_report.md`

Remaining:

- Tighten `other_review` and obvious entity gaps found in private drafts.
- Add reviewer-facing examples after the first 10+ draft reviews are filled.

### Semi-Automated TG Posting MVP: 3-5 days after approval to connect Telegram

This requires an explicit decision to allow Telegram bot/API integration.

Scope:

- Send only human-approved drafts.
- Keep auto-send disabled by default.
- Log every sent message locally.
- Add rollback/delete instructions if the operator posts a bad message.

### First-Party Watcher MVP: 1-3 weeks after source selection

Scope depends on data source availability.

Narrow first version:

- A small allowlist of whale/project/team/hacker addresses.
- Large inflow/outflow and position-change events.
- Same TG draft/review flow as news events.

Do not attempt broad chain indexing first.

## Practical Launch Recommendation

Start with the local private draft MVP immediately. The success metric is not abnormal return. The first metric is whether reviewed drafts are useful, factual, timely, and not noisy.

Minimum pilot bar:

- 20 local drafts generated.
- 0 draft validation failures.
- 10+ reviewed drafts.
- More than half reviewed as `useful` or `interesting`.
- No factual/asset/time issue pattern that repeats more than twice.

Only after that should Telegram integration be considered.
