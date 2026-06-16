# Protocol 02: Temporal Model and Registration

**对应决策: 2**

## Temporal Anchor

### selected_clock

`selected_clock` is either:
- **action_clock**: Real-world action time (when the event actually occurred)
- **information_clock**: When information reached the market (when the market first learned of the event)

`broadcast_time` is NOT a valid `selected_clock` value — it is only a proxy/`actual_time_basis`.

### actual_time_basis

The `actual_time_basis` field supports the following values:
- `occurrence_time`
- `action_time`
- `onchain_confirmation_time`
- `official_publication_time`
- `first_reliable_public_time`
- `detection_time`
- `broadcast_time`
- `ingestion_time`

### Clock Selection Rules

- The same underlying event can form TWO Study Cases if two different clocks are selected
- A single Study Case MUST NOT mix two clocks
- `primary_t0` is locked before Outcome reveal

### Separate Concepts

`event_time_uncertainty`, `price_alignment_lag`, and `price_precision` are separate concepts managed in the Outcome schema, not part of the Temporal Anchor definition.

## Registration Requirements

Each Research Unit MUST have a Registration before Outcome is computed or revealed. Registration records:

- Target asset
- Selected clock and t0
- t0 type and uncertainty
- Primary window (1h / 4h / 24h)
- Primary benchmark (MUST differ from target asset)
- Sensitivity benchmarks (optional, pre-registered)
- Pre-event movement check definition
- Git commit and file SHA
- Data partition (development / calibration / holdout)
- Outcome status: `not_revealed`

## Prohibitions

- Outcome data MUST NOT be present in Registration
- Primary benchmark MUST NOT equal target asset
- t0, primary window, and primary benchmark MUST NOT be modified after Outcome computation
- Development Set registrations MUST NOT count toward Pilot statistics
