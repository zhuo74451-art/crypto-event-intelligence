# Protocol 02: Temporal Model and Registration

**对应决策: 2**

## Temporal Anchor

Primary t0 is `broadcast_time` — the verifiable UTC timestamp of when the event was first reported. `event_time_utc` is recorded when available but may be null.

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
