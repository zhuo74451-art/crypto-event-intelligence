# Protocol 01: Research Unit and Eligibility

**对应决策: 1**

## Scope

Defines what constitutes a Research Unit in Pilot v1, how eligibility is determined, and the boundary between Research Eligibility and Legacy Noise Gate.

## Research Unit

A Research Unit in v1 is a `point_event_study` defined by:
- one discrete event fact;
- one selected clock;
- one pre-registered t0;
- one target asset;
- one primary window;
- one registered benchmark.

broadcast_time is NOT the default. It is only one possible value of actual_time_basis.

### information_form

The Research Unit's `information_form` must be one of:

| Form | Description |
|------|-------------|
| discrete_information_release | A single, discrete piece of information released at a known time |
| discrete_observable_action | A single, observable action taken by a market participant |
| state_snapshot | A snapshot of a system state at a point in time |
| cumulative_trend | An aggregate or cumulative trend over a period |
| interpretation_or_narrative | An interpretation, opinion, or narrative framing |
| market_outcome_or_context | A market outcome or contextual condition |

### source_medium

`source_medium` is a separate field with its own taxonomy:

| Medium | Description |
|--------|-------------|
| news_article | Journalistic news article |
| official_announcement | Official project or organization announcement |
| social_media_post | Post on social media platform |
| onchain_data_feed | Data directly from an on-chain feed |
| analyst_report | Report from an analyst or research firm |
| regulatory_filing | Filing with a regulatory body |
| market_data_feed | Market data feed (e.g., exchange data) |
| messaging_or_alert | Message or alert from any channel |
| other | Other source medium not covered above |

### Routing by information_form

- `discrete_information_release` and `discrete_observable_action` → `point_event_study` candidate
- `state_snapshot` → context / monitoring
- `cumulative_trend` → other design
- `interpretation_or_narrative` → split from underlying fact
- `market_outcome_or_context` → interference / context

## Eligibility Statuses

| Status | Meaning |
|--------|---------|
| eligible | Full study inclusion |
| conditionally_eligible | Inclusion with noted caveats |
| context_only | Provides background, not for primary attribution |
| routed_to_other_design | Belongs in a different study design |
| ineligible | Does not meet inclusion criteria |
| insufficient_information | Cannot determine eligibility |

## Boundary

Research Eligibility is determined independently of the Legacy Noise Gate. A Candidate that passed Noise Gate could still be `ineligible` for research; one that was rejected by Noise Gate could be `eligible` for research if the rejection reason was unrelated to research criteria.
