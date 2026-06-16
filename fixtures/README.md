# Signal Spine IO v1 — Fixtures

## Purpose
Deterministic test fixtures for the signal-spine-io-v1 verification lane.
All fixtures are offline-safe, credential-free, and timestamped for repeatability.

## Fixture Inventory

| File | Type | Expected Decision | Dedup Key |
|------|------|-------------------|-----------|
| `event_high_quality.json` | High-signal market event | `观察` | `cei_dedup:btc-etf-options-2026-06-16` |
| `event_duplicate.json` | Exact duplicate of high-quality | `丢弃` (dedup) | `cei_dedup:btc-etf-options-2026-06-16` |
| `event_old_news_rehash.json` | Old news recycled | `风险提示` | `cei_dedup:old-news-rehash-btc-2026-06` |
| `event_no_asset.json` | Event with no clear asset | `观察` | `cei_dedup:no-asset-event-2026-06-16` |
| `event_insufficient_source.json` | Single unverifiable source | `丢弃` | `cei_dedup:insufficient-source-2026-06-16` |
| `event_pump_risk.json` | High pump/FOMO risk signal | `禁止` | `cei_dedup:pump-risk-sol-2026-06-16` |
| `event_missing_fields.json` | Data fields missing | `丢弃` | `cei_dedup:missing-fields-2026-06-16` |
| `real_binance_response_sample.json` | Sample Binance 24hr ticker response | — | — |

## Usage
```python
from fixtures.loader import load_fixture, load_golden
data = load_fixture("event_high_quality")
expected = load_golden("multi_asset_market_sync")
```
