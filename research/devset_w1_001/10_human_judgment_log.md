# Human Judgment Log — w1_001

## 1. information_form Selection

**Decision:** `discrete_observable_action`

**Rationale:** A whale opening/increasing a short position is a discrete, observable action on-chain. It is not a news report (discrete_information_release), not a state snapshot, not a cumulative trend, not an interpretation, and not market context.

**Confidence:** High

## 2. source_medium Selection

**Decision:** `onchain_data_feed`

**Rationale:** The data comes from HyperLiquid address data queried by 币界快讯ai's monitoring system. This is an automated on-chain data feed, not a news article or social media post.

**Confidence:** High

## 3. source_quality_status

**Decision:** `单来源，无法交叉验证`

**Rationale:** Only one source (币界快讯ai) reported this position. The underlying data (HyperLiquid on-chain state) is independently verifiable by querying the same address directly, but the event as a packaged observation has only one carrier.

**Confidence:** Medium — the data is technically independently verifiable but practically requires HyperLiquid API access.

## 4. selected_clock

**Decision:** `information_clock`

**Rationale:** The actual whale position change time is unknown. Only the broadcast time (13:02 UTC) is recorded. `action_clock` cannot be used because there is no verifiable action timestamp.

**Confidence:** High — this is a factual constraint, not a judgment call.

## 5. actual_time_basis

**Decision:** `broadcast_time`

**Rationale:** Only the broadcast timestamp is available. No occurrence_time, action_time, or onchain_confirmation_time was recorded.

**Confidence:** High (factual constraint)

## 6. primary_window Selection

**Decision:** `1h (t0_to_t_plus_1h)`

**Rationale:** A 1h window is the shortest standard window. For a whale position event, the market reaction should be observable within 1 hour if the event is material. Longer windows (4h, 24h) would accumulate more interference from unrelated market movements.

**Confidence:** Medium — 1h is a reasonable default but not empirically validated for HYPE specifically.

## 7. primary_benchmark Selection

**Decision:** `BTC`

**Rationale:** BTC is the standard crypto market benchmark. However, HYPE is a non-Binance altcoin with different market microstructure, so BTC is a weak proxy.

**Confidence:** Low — documented as weak proxy.

## 8. pre_event_movement_check_definition

**Decision:** 1h window before t0, 20 bps threshold

**Rationale:** Standard conservative threshold. 20 bps is low enough to detect meaningful pre-event movement but high enough to avoid noise.

**Confidence:** Low — not empirically calibrated.

## 9. outcome data availability

**Decision:** All price fields marked null/insufficient_data

**Rationale:** Hyperliquid candleSnapshot historical data retention for 2026-05-25 could not be confirmed. Rather than fabricating price data, all reactive fields are marked as unavailable.

**Confidence:** High — this is the honest approach per protocol rules.

## 10. attribution hard_gates

**Decision:** research_eligibility=pass, event_evidence=pass, all others=unknown

**Rationale:** The event is research-eligible (discrete action with clear evidence). But t0 is approximate, registration is retrospective, data is unavailable, benchmark is weak, and interference cannot be assessed.

**Confidence:** High

## 11. attribution_verdict

**Decision:** `insufficient_evidence`

**Rationale:** With 5 of 7 hard gates at "unknown" (not "pass"), no positive verdict (attribution_compatible or limited_attribution_support) is permitted per protocol. The honest verdict is insufficient_evidence.

**Confidence:** High — this is the correct protocol-compliant outcome.
