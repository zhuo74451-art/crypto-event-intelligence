# Open Questions

These questions should be answered before building TG automation or first-party on-chain watchers.

## Product Questions

1. Should the TG group receive only `auto_publish` items, or also `human_review` items after manual approval?
2. What is the acceptable false-positive rate for group publishing?
3. Should market-wide macro events be published, or only single-asset / sector events?
4. Should Chinese and English sources be mixed in one stream or separated?
5. Should source attribution always be displayed in the group message?

## Data Questions

1. How many historical raw news rows can the backend export for 6-24 months?
2. Are there stable source IDs to support source quality scoring?
3. Are duplicate news rows linked by URL, source, or title similarity?
4. Which rows represent first-party observations versus syndicated news?
5. Which fields can be safely used in real-time without hindsight leakage?

## Research Questions

1. What minimum sample size should be required per event bucket: 10, 20, or 30?
2. Should BTC/ETH events be excluded from BTC/ETH abnormal-return summaries?
3. Should market-wide events have a separate benchmark methodology?
4. Which event types deserve L2 subtypes first?
5. How should pre-event price-in be interpreted for stale news?

## First-Party Watcher Questions

1. Which 10-30 addresses should be monitored first?
2. Are they whale, project/team, CEX, hacker, fund, or market-maker addresses?
3. What transfer threshold should trigger an event?
4. Which chains matter first: Ethereum, Bitcoin, Solana, BNB Chain, Tron?
5. Is contract position monitoring available from a reliable public source?

## Immediate Decision Needed

The next implementation should start with v0.6 Event Intake Quality Layer unless there is a hard reason to prioritize TG publishing earlier.
