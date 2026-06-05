# HL-to-Whale Adapter Spec — v112W

**Version:** v1.12-w  
**Status:** Plan-only, NOT implemented  
**Generated:** 2026-06-05 04:13 UTC+8

## Purpose

Define how a HyperLiquid `clearinghouseState` live response is transformed into a
v112F-compatible `whale_position_alert` local feed input — with strict invariants
that prevent accidental production use.

## Input: HyperLiquid Live Response

```json
{
  "type": "clearinghouseState",
  "assetPositions": [
    {
      "position": {
        "coin": "BTC",
        "szi": "1.5",
        "entryPx": "87200.5",
        "liquidationPx": "69800.0",
        "unrealizedPnl": "86800.0",
        "leverage": {"type": "cross", "value": 5},
        "marginUsed": "1040000.0",
        "positionValue": "5200000.0",
        "cumFunding": {"allTime": "-1200.5", "sinceOpen": "-500.0", "sinceChange": "-300.0"}
      },
      "type": "oneWay"
    }
  ]
}
```

## Output: v112F-Compatible Whale Event

```json
{
  "wallet": "0x7a9f2c8d4e6b1a3f5c7d9e2b4a6f8c0d2e4a6b8c",
  "asset": "BTC",
  "side": "long",
  "position_size_usd": 5200000.0,
  "leverage": 5.0,
  "entry_price": 87200.5,
  "mark_price": 88650.0,
  "unrealized_pnl_usd": 86800.0,
  "unrealized_pnl_pct": 1.67,
  "liquidation_price": 69800.0,
  "observed_at": "2026-06-05T04:13:00+08:00",
  "label": "Smart Money Alpha",
  "entity_type": "smart_money",
  "label_confidence": "high",
  "previous_position_size_usd": 0.0,
  "position_delta_usd": 5200000.0,
  "data_mode": "live_like_planned",
  "source": "hyperliquid_info_public_v112w_plan",
  "eligible_for_real_send": false
}
```

## Transformation Rules

### 1. Address / Wallet

- HyperLiquid response does NOT include the wallet address directly — it's the `user`
  parameter in the request.
- Adapter must pair the request address with the response.
- For v112W plan: address comes from `data/hyperliquid_position_state.csv` tracked addresses.

### 2. Symbol / Asset

- `assetPositions[].position.coin` → `asset`
- Map to uppercase: `"btc"` → `"BTC"`, `"eth"` → `"ETH"`
- Keep as-is if already uppercase.

### 3. Side Determination

- `assetPositions[].position.szi` is a string-represented float.
- `szi > 0` → `"long"`, `szi < 0` → `"short"`, `szi == 0` → skip (no position).
- NO assumption about position type field — szi sign is canonical.

### 4. Position Size (USD)

- Primary: `assetPositions[].position.positionValue` (string → float)
- Fallback: `abs(parseFloat(szi)) * mark_price`
- Both must produce consistent results (±5% tolerance). Flag if mismatch.

### 5. Entry Price

- `assetPositions[].position.entryPx` (string → float)
- Must be > 0. Zero entry price → ABORT (numeric parse failure).

### 6. Mark Price

- HyperLiquid response may NOT include mark price directly.
- **v112W plan:** Mark price will be fetched separately from CoinGecko public API
  (free, no key) for the asset symbol.
- Fallback: use entry price if mark price unavailable (DEGRADE_TO_MOCK).

### 7. Unrealized PnL

- `assetPositions[].position.unrealizedPnl` (string → float) → `unrealized_pnl_usd`
- Compute `unrealized_pnl_pct = unrealized_pnl_usd / (position_size_usd - unrealized_pnl_usd) * 100`
  (approximate — actual formula depends on leverage type).

### 8. Leverage

- Parse from `assetPositions[].position.leverage.value` (number).
- If leverage object has `type: "cross"` or `type: "isolated"`, preserve but only use
  `value` for the numeric field.
- If leverage is missing, DEGRADE_TO_MOCK.

### 9. Liquidation Price

- `assetPositions[].position.liquidationPx` (string → float or null)
- Null liquidation price → DEGRADE_TO_MOCK (not ABORT — other fields may be valid).
- If present, compute `liquidation_distance_pct`.

### 10. Timestamp / Observed At

- Use server response timestamp if available.
- If not available, generate safe local timestamp via `datetime.now(CN_TZ).isoformat()`.
- DEGRADE_TO_MOCK if timestamp freshness uncertain.

## Address Label / Label Confidence Handling

### Label Resolution Priority

1. **Local label DB** (`data/hyperliquid_position_state.csv` entity column)
2. **HyperLiquid observer label** (if the API provides any)
3. **Unknown Whale fallback** — always available, always low confidence.

### Confidence Mapping

| Condition | Confidence |
|-----------|-----------|
| Label from known entity DB (Arkham, Nansen, onchain confirmed) | `high` |
| Label from HyperLiquid observer or heuristic | `medium` |
| Unknown Whale fallback or stale label (>30 days) | `low` |

### Unknown Whale Handling

- If no label is found: `label = "Unknown Whale"`, `entity_type = "unknown_whale"`, `label_confidence = "low"`.
- This is a DEGRADE_TO_MOCK condition but does NOT prevent signal generation.
- The public card will display "Unknown Whale" — this is acceptable for observation purposes.

## Deterministic ID Generation

### signal_id

```
signal_id = f"sig-wpa-{md5(asset + wallet + observed_at + position_size_usd)[:8]}-{observed_at_compact}"
```

- `wpa` = whale_position_alert
- Uses first 8 chars of MD5 hash of composite key.
- `observed_at_compact` = YYYYMMDDHHMM format.

### dedupe_key

```
dedupe_key = sha256(asset + wallet + side + str(position_size_usd) + str(observed_at_date))[:16]
```

- Uses date-level granularity to dedupe same position within a day.
- Position size change triggers new dedupe window.

### cooldown_key

```
cooldown_key = sha256(card_type + asset + wallet)[:16]
```

- Per-asset-per-wallet cooldown. Same address can alert on different assets.

### payload_hash

```
payload_hash = sha256(json.dumps(envelope_payload, sort_keys=True))[:12]
```

- Deterministic hash of the full envelope payload for integrity verification.

## Preventing Live-Like Data from Being Marked as Real Send

### Invariants (enforced at adapter level)

1. `eligible_for_real_send` is ALWAYS `false` in v112W output.
2. `data_mode` is ALWAYS `"live_like_planned"` (NOT `"live"`, NOT `"production"`).
3. `source` includes `"v112w_plan"` suffix to prevent confusion with production sources.
4. No TG send function is ever called from the adapter.
5. No production state file is ever written from the adapter.
6. `live_ready` is ALWAYS `false`.
7. `real_tg_sent` is ALWAYS `false`.

### Envelope Guard

The v112H envelope wrapper additionally enforces:
- `eligible_for_real_send` is read-only in the envelope layer and cannot be overridden.
- Any attempt to set it to `true` from a v112W source triggers an ABORT.

## ABORT / DEGRADE_TO_MOCK / CONTINUE → Envelope / Preview

### How the Decision Propagates

| Stop Decision | Envelope created? | Preview card created? | Envelope metadata |
|---|---|---|---|
| CONTINUE | Yes | Yes (eligible=false) | `stop_decision: "CONTINUE"` |
| DEGRADE_TO_MOCK | Yes (degraded) | Yes (eligible=false, degraded flag) | `stop_decision: "DEGRADE_TO_MOCK"`, `degraded: true` |
| ABORT | No | No | N/A (no envelope) |

### Envelope Metadata Fields

```json
{
  "stop_decision": "CONTINUE | DEGRADE_TO_MOCK",
  "stop_decision_reasons": ["condition_id_1", "condition_id_2"],
  "degraded": true/false,
  "eligible_for_real_send": false,
  "source_plan": "v112w_hyperliquid_one_shot_plan",
  "data_tier": "planned_live_like_not_production"
}
```

## Why v112W Does NOT Request HyperLiquid API

1. **This is a planning step, not an execution step.** v112W defines the plan, stop conditions,
   field mapping, schema, and adapter spec. The actual API call is deferred to v112X.
2. **User confirmation is required.** The v112X one-shot dry-run requires explicit user
   confirmation because it makes an external network request, even though it's read-only.
3. **Risk isolation.** Keeping plan and execution separate allows independent verification
   of each layer before any external call is made.
4. **The plan itself is the deliverable.** v112W produces a complete, reviewable plan
   that answers: (a) is whale_position_alert suitable? (b) what fields are needed?
   (c) what are the stop conditions? (d) is label quality sufficient?

## v112X Prerequisites

Before v112X can execute the one-shot dry-run:
1. User MUST explicitly confirm.
2. All v112W tests MUST pass.
3. Label quality audit MUST show `label_quality_ready_for_one_shot_plan: true`.
4. Stop conditions config MUST be reviewed and approved.
5. Field mapping MUST be verified against actual HyperLiquid API response shape.
6. No credentials, keys, or auth tokens may be read or sent.
