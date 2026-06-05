# market_radar_v112t_live_to_mock_adapter_spec

**Version**: v1.12-t  
**Status**: plan-only (no execution)  
**Generated**: 2026-06-05 03:44:00 UTC+8  

## Purpose

This spec defines how a `LiveSourceResponse` (v112T normalized live response) is converted to v112R mock adapter input format. This conversion is the bridge between the free-source live data layer and the existing mock-signal pipeline. It is defined here for v112T planning; actual execution is deferred to v112U (with user confirmation).

## Input: LiveSourceResponse

The input is a normalized response conforming to `schemas/market_radar_v112t_live_source_response_schema.json`. Key characteristics:

- `source_name`: Identifies which free source produced the data (`coingecko_public_rest` or `coincap_public_rest`)
- `request_mode`: Always `planned_one_shot` in v112T; will be `live_one_shot` in v112U
- `assets[]`: Array of normalized asset objects with price, change%, volume, timestamp
- `stop_decision`: One of `CONTINUE`, `ABORT`, `DEGRADE_TO_MOCK`
- `eligible_for_real_send`: Always `false` in v112T

## Output: v112R Mock Adapter Input

The v112R mock adapter (`scripts/run_market_radar_v112r_multi_asset_mock_adapter_envelope_compatibility.py`) expects input with:

- `card_type`: "multi_asset_market_sync"
- `signal_id`: Deterministic ID string
- `assets[]`: Asset data matching v112R envelope schema
- `direction`: Market sync direction (up/down/mixed)
- `confidence`: Signal confidence level
- `source_lineage`: Where the data came from
- `mock_mode`: Whether this is mock data
- `eligible_for_real_send`: Whether it can be sent to production TG

## Conversion Rules

### 1. Stop Decision Gate (FIRST)

```
IF stop_decision == "ABORT":
    → Do NOT convert. Log abort reason. No v112R input generated.

IF stop_decision == "DEGRADE_TO_MOCK":
    → Convert with degraded flags. Set confidence = "low_confidence".
      Mark mock_mode = true. eligible_for_real_send = false.

IF stop_decision == "CONTINUE":
    → Convert normally, but still set eligible_for_real_send = false.
      This is a v112T policy constraint.
```

### 2. Asset Field Mapping

| LiveSourceResponse Field | v112R Adapter Field | Notes |
|---|---|---|
| `asset.asset_id` | `asset.asset_id` | Direct pass-through |
| `asset.symbol` | `asset.symbol` | Uppercase normalized |
| `asset.price_usd` | `asset.price_usd` | Direct pass-through |
| `asset.price_change_pct` | `asset.price_change_pct_24h` | Primary price change metric |
| `asset.price_change_pct_1h` | `asset.price_change_pct_1h` | Nullable; null if source doesn't provide |
| `asset.volume_change_pct` | `asset.volume_change_pct` | Nullable; compute from raw if possible |
| `asset.open_interest_change_pct` | `asset.oi_change_pct` | Always null from free sources |
| `asset.last_updated_at` | `asset.observation_timestamp` | ISO-8601 pass-through |
| `asset.source_latency_ms` | `asset.source_latency_ms` | Nullable |
| `asset.raw_source_fields` | (preserved in `asset.raw_source_fields`) | For lineage/debugging |

### 3. Inheriting v112Q Stricter Thresholds

The converted adapter input MUST be evaluated against v112Q thresholds from `config/market_radar_v112q_multi_asset_thresholds.json`:

```
- small_basket_max_size: 3
- small_basket_required_direction_agreement: 1.0
- large_basket_required_direction_agreement: 0.8
- min_per_asset_abs_price_change_pct: 2.0
- min_assets_meeting_price_threshold_ratio: 0.8
- require_price_and_one_secondary_metric: true
- max_timestamp_skew_seconds: 60
- leader_driven_downgrade_enabled: true
- historical_baseline_required_before_real_send: true
```

**OI gap handling**: Since free sources do NOT provide `open_interest_change_pct`, the `require_price_and_one_secondary_metric` check can only use `volume_change_pct` as the secondary metric. If volume data is also missing for an asset, that asset fails the secondary metric check. If more than 20% of assets fail, the threshold check fails and the signal is DEGRADE_TO_MOCK.

**Direction agreement**: Computed from `price_change_pct` signs across assets. For small baskets (≤3 assets), 100% agreement required. For larger baskets (>3), 80% agreement required.

**Leader-driven detection**: If one asset's price change magnitude is >4× the average of the rest, flag as leader-driven and downgrade confidence.

### 4. Source Lineage Preservation

Every converted asset object includes:

```json
{
  "source_lineage": {
    "primary_source": "<source_name from LiveSourceResponse>",
    "fallback_used": false,
    "plan_version": "v1.12-t",
    "request_mode": "planned_one_shot",
    "cross_source_validated": true|false,
    "cross_source_verdict": "<from cross_source_validation.verdict>",
    "original_source_name": "<source_name>",
    "fetched_at": "<ISO-8601>"
  }
}
```

This lineage is propagated through the entire pipeline so reviewers can trace any signal back to its source.

### 5. Deterministic Mock signal_id / payload_hash

Signal IDs are generated deterministically from the source data so that repeated runs with the same input produce the same IDs:

```
signal_id = sha256(
  card_type + "|" +
  source_name + "|" +
  fetched_at + "|" +
  sorted_asset_symbols.join(",") + "|" +
  direction + "|" +
  plan_version
)[:16]

payload_hash = sha256(
  signal_id + "|" +
  sorted_asset_data_canonical_json
)[:16]
```

This ensures:
- **Idempotent replay**: Same input → same signal_id → dedupe works
- **Content-addressed**: Different data → different hash → no collision
- **Deterministic**: No randomness, no timestamp-based entropy

### 6. Default eligible_for_real_send = false

The adapter MUST enforce:

```
v112R_input.eligible_for_real_send = false  // ALWAYS, regardless of CONTINUE or data quality
```

This is checked at multiple levels:
1. **LiveSourceResponse level**: `eligible_for_real_send` is `const: false` in schema
2. **Adapter level**: Hard-coded to false during conversion
3. **v112R run level**: v112R adapter checks this flag before allowing real send path

### 7. ABORT / DEGRADE_TO_MOCK Handling

| Decision | Adapter Action | v112R Input Generated? | Card Generated? |
|---|---|---|---|
| ABORT | Log abort reason to result. Write abort entry. | No | No |
| DEGRADE_TO_MOCK | Convert with degraded flags. confidence="low_confidence". mock_mode=true. eligible_for_real_send=false. | Yes (degraded) | Yes (low_confidence card) |
| CONTINUE | Convert normally. eligible_for_real_send=false. | Yes | Yes (normal card, still not real send) |

### 8. Example Conversion

**Input (LiveSourceResponse, simplified):**
```json
{
  "source_name": "coingecko_public_rest",
  "fetched_at": "2026-06-05T03:44:00Z",
  "request_mode": "planned_one_shot",
  "stop_decision": "CONTINUE",
  "assets": [
    {
      "asset_id": "bitcoin",
      "symbol": "BTC",
      "price_usd": 102000,
      "price_change_pct": 3.5,
      "price_change_pct_1h": 1.2,
      "volume_change_pct": 15.0,
      "last_updated_at": "2026-06-05T03:43:30Z"
    },
    {
      "asset_id": "ethereum",
      "symbol": "ETH",
      "price_usd": 5200,
      "price_change_pct": 2.8,
      "price_change_pct_1h": 0.9,
      "volume_change_pct": 12.0,
      "last_updated_at": "2026-06-05T03:43:30Z"
    }
  ],
  "eligible_for_real_send": false
}
```

**Output (v112R Adapter Input, simplified):**
```json
{
  "card_type": "multi_asset_market_sync",
  "signal_id": "a1b2c3d4e5f6a7b8",
  "payload_hash": "x1y2z3w4v5u6t7s8",
  "direction": "up",
  "confidence": "high",
  "mock_mode": false,
  "eligible_for_real_send": false,
  "source_lineage": {
    "primary_source": "coingecko_public_rest",
    "plan_version": "v1.12-t",
    "request_mode": "planned_one_shot"
  },
  "assets": [
    {
      "asset_id": "bitcoin",
      "symbol": "BTC",
      "price_usd": 102000,
      "price_change_pct_24h": 3.5,
      "price_change_pct_1h": 1.2,
      "volume_change_pct": 15.0,
      "oi_change_pct": null,
      "observation_timestamp": "2026-06-05T03:43:30Z",
      "source_lineage": {
        "primary_source": "coingecko_public_rest",
        "fetched_at": "2026-06-05T03:44:00Z"
      }
    },
    {
      "asset_id": "ethereum",
      "symbol": "ETH",
      "price_usd": 5200,
      "price_change_pct_24h": 2.8,
      "price_change_pct_1h": 0.9,
      "volume_change_pct": 12.0,
      "oi_change_pct": null,
      "observation_timestamp": "2026-06-05T03:43:30Z",
      "source_lineage": {
        "primary_source": "coingecko_public_rest",
        "fetched_at": "2026-06-05T03:44:00Z"
      }
    }
  ]
}
```

## v112U Prerequisites (for actual live dry-run)

Before v112U executes this adapter with real live data:

1. **User explicit confirmation required**: v112U must not proceed without user acknowledgment that a one-shot free-source dry-run will make real HTTP requests to CoinGecko/CoinCap public APIs.
2. **Network access verified**: The execution environment must have outbound internet access to `api.coingecko.com` and `api.coincap.io`.
3. **Rate limit awareness**: The user must be informed of free-tier rate limits and potential 429 responses.
4. **No state mutation**: v112U must NOT write to any production state file. Outputs go to `results/` and `runs/` only.
5. **No TG send**: v112U must NOT send any Telegram message, even to test channels.
6. **Timeout enforcement**: The 15s per-request and 120s total duration limits must be enforced.
