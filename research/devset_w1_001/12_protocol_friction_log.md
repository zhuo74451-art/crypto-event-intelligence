# Protocol Friction Log — w1_001

## Friction 1: Price Data Unavailability for Non-Binance Assets

**Severity:** Moderate

**Description:** The protocol and schemas assume price data availability (Binance klines with 1m granularity). HYPE is not on Binance. Hyperliquid candleSnapshot is the alternative but:
- Retention window is unknown (may not cover 2026-05-25)
- Minimum interval is 15m (reduced precision)
- No standard fallback provider defined

**Impact:** Outcome fields are null. This is technically allowed (null is valid) but produces an anemic Outcome object.

## Friction 2: Retrospective Reconstruction vs Protocol Requirements

**Severity:** Moderate (Development Set only)

**Description:** The protocol requires Registration before Outcome computation. For a Development Set conversion from historical data, this ordering is inherently violated. The meta fields document this,
but the current validator schema does not distinguish retrospective from prospective Registrations.

**Impact:** Development Set conversions are always marked as `retrospective_reconstruction`. The pre_outcome_registration hard gate is correctly set to "unknown" for retrospective cases.

## Friction 3: BTC Benchmark Weak Proxy for Altcoins

**Severity:** Minor

**Description:** The protocol requires a primary_benchmark that differs from target_asset. For HYPE, BTC is the default choice but is acknowledged as a weak proxy. The attribution_assessment schema has a `btc_benchmark_weak_proxy_note` field but this is optional and there's no equivalent for other weak-proxy pairs.

**Impact:** benchmark_validity hard gate is "unknown" for non-standard assets.

## Friction 4: insufficient_inventory vs isolated for Single-Source Events

**Severity:** Minor

**Description:** The interference schema requires collision_set but for a single-source event with limited monitoring coverage, `insufficient_inventory` is the correct separability status. However, the schema's collision_set items have optional `event_id` (null). This feels semantically awkward — there IS no collision to record.

**Impact:** The collision_set entry with null event_id is technically valid but reads oddly.

## Friction 5: No Development-Specific Registration workflow

**Severity:** Minor

**Description:** The protocol provides lifecycle stages "registered" and "outcome_revealed" but no "development" stage that acknowledges retrospective construction. The bundle validator correctly allows development partitions, but some checks (registration_time_utc before outcome_time) cannot be genuinely satisfied for retrospective conversions.

**Workaround:** Set registration_time_utc to the reconstruction time and document the retrospective nature in meta fields.
