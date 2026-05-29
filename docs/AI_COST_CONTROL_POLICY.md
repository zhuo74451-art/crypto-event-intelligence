# AI Cost Control Policy

Last updated: 2026-05-27 UTC+8

## Decision

Claude-level models must not review every raw event.

Claude is reserved for:

- Borderline cases after local rules and cheaper review have low confidence.
- Complex editorial judgment.
- Ambiguous multi-asset/security/macro context.
- Random audit samples.
- Periodic rule-improvement reviews.

The default architecture is:

```text
raw event
-> deterministic local rules
-> dedup / source / length / spam / entity checks
-> structured candidate
-> cheap review tier or local scoring
-> Claude only for uncertain or audit rows
-> approved draft pool
```

## Current Sources

Current implemented source:

- Server/exported real fast-news CSV.

Planned sources:

- Telegram/news/backend feeds.
- First-party on-chain watchers.
- Whale wallets.
- CEX inflow/outflow.
- Project/team wallets.
- Hacker/exploit wallets.
- Stablecoin mint/burn.

On-chain watchers should generate structured alerts, not raw text blobs. Most on-chain events must be handled by deterministic thresholds and templates, not LLM review.

## Routing Policy

### Local Rules First

Use local rules before any model call:

- Exact/near duplicate detection.
- Short/empty/truncated content rejection.
- Known spam/source blacklist.
- Generic price recap rejection.
- URL-heavy/link spam rejection.
- Low crypto relevance rejection.
- Known event template detection.
- Source/time normalization.
- Entity and asset extraction.

Target: eliminate 60-80% of raw news events locally.

### Cheap Review Tier

Use a cheaper model or local classifier for:

- Simple binary relevance checks.
- Structured extraction cleanup.
- Confidence scoring.
- Semantic duplicate checks.
- Template matching.

Target: decide most remaining non-obvious rows without Claude.

### Claude Tier

Use Claude for:

- Small uncertain band.
- High-impact ambiguous events.
- Protocol exploit attribution.
- Multi-asset/macro ambiguity.
- Sample audits.
- Rule-improvement review from failed drafts.

Target:

- Early stage: Claude reviews no more than 5-10% of raw events.
- Growth stage: Claude reviews 2-5% of raw events.
- Scale stage: Claude reviews below 2% of raw events, plus audit sampling.

## On-Chain Cost Policy

Do not pass raw transactions to Claude.

On-chain flow:

```text
transaction stream
-> magnitude threshold
-> known wallet / contract tags
-> exchange / bridge / protocol template
-> anomaly detector
-> structured alert
-> cheap enrichment
-> Claude only for novel/ambiguous/high-impact alert
```

Examples:

- Small routine transfers: discard/log only.
- Known wallet > threshold to CEX: structured alert.
- Hacker wallet movement: priority alert.
- Novel exploit-like pattern: Claude review or human escalation.

## Scale Policy

For 1,000 events/day:

- Local rules should filter around 80%.
- Cheap review handles most of the rest.
- Claude handles roughly 40-60 rows/day including audit.

For 10,000 events/day:

- Local rules should filter 80-85%.
- Claude target: around 300-500 rows/day including audit.

For 100,000 events/day:

- Local rules and structured on-chain templates are mandatory.
- Claude target: below 2,000 rows/day including audit.
- Consider self-hosted or very cheap small-model inference.

## Metrics

Track weekly:

- Cost per raw event.
- Cost per approved draft.
- Percent filtered by local rules.
- Percent sent to Claude.
- AI approval rate.
- AI reject reason distribution.
- Duplicate/stale rejection rate.
- Human/spot-audit override rate.
- Missed critical event count.
- Latency by event type.

## Current Implementation Gap

Current system can run Claude on 20 draft rows, but this is a pilot calibration step.

Next implementation step:

- Use Claude-reviewed rejects to improve local filtering.
- Add approved-only draft pool.
- Add stricter dedup before Claude review.
- Introduce cheaper/local review tier before scaling beyond the current batch size.
