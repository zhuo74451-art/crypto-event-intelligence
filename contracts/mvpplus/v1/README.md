# MVP+ Contracts v1

## Overview

Public JSON Contract definitions for the Crypto Signal Intelligence MVP+ Workbench.

These contracts define the **shape, null policy, units, and constraints** for all data exchanged between lanes. Lane 6 is the sole authority for contract modifications.

## Null Policy

| Situation | Value |
|-----------|-------|
| Data not requested | `null` |
| Data requested but unavailable | `null` |
| Data source degraded | `null` or `degraded` source_health |
| Not applicable to this asset/context | `null` |
| Computation not possible | `null` |
| **Never** use `0` or `""` as missing data sentinel | — |

## Time Format

All timestamps: **ISO-8601 UTC** (`yyyy-MM-ddTHH:mm:ssZ`).

## Monetary Units

All USD amounts: **US Dollars**, floating point.
All percentages: **decimal percentage** (e.g., 0.35 for 0.35%, -22.8 for -22.8%).

## Degraded Data

When a data source cannot provide fresh data, the contract field MUST be `null` AND `source_health.status` MUST be `"degraded"` or `"unavailable"`. Degraded entries MUST include `error_type`, `occurred_at_utc`, and `message_summary`.

## Contracts

| File | Description |
|------|-------------|
| `whale_position.schema.json` | Single whale position snapshot |
| `whale_position_change.schema.json` | Detected position change between snapshots |
| `market_context.schema.json` | Market context for an asset on a venue |
| `unified_feed_item.schema.json` | Unified feed item (flash/news/Telegram) |
| `source_claim.schema.json` | Claim extracted from a source item |
| `event_cluster.schema.json` | Cluster of related observations and claims |
| `source_health.schema.json` | Data source health status (embedded) |
| `run_report.schema.json` | Run execution report |

## Direction Convention

direction MUST be `"long"` or `"short"`. **Never `"buy"` or `"sell"`.**

## Examples

See `examples/` for sample JSON payloads.
