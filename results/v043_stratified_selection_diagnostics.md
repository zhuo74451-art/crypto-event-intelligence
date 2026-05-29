# Stratified Selection Diagnostics

input_rows: 500
selected_rows: 37
target_limit: 50
underfill: 13

## Interpretation

- The sample did not reach the requested limit.
- This is expected when high-volume categories are capped and smaller categories have too few eligible rows.
- Do not relax caps automatically without a product decision; otherwise macro/other can dominate the sample again.

## By Event Type

| event_type | total | eligible | selected | cap | unused_eligible_after_cap |
|---|---:|---:|---:|---:|---:|
| macro | 172 | 135 | 10 | 10 | 125 |
| hack_security | 24 | 12 | 8 | 8 | 4 |
| other | 254 | 18 | 5 | 5 | 13 |
| institutional_flow | 15 | 3 | 3 | 10 | 0 |
| network_upgrade | 12 | 3 | 3 | 8 | 0 |
| token_unlock | 7 | 3 | 3 | 8 | 0 |
| halving | 4 | 3 | 3 | 5 | 0 |
| staking_governance | 8 | 2 | 2 | 5 | 0 |
| exchange_listing | 2 | 0 | 0 | 8 | 0 |
| whale_position | 2 | 0 | 0 | 10 | 0 |

## Top Block Reasons

| reason | count |
|---|---:|
| missing_binance_symbol | 279 |
| suggested_exclude | 265 |
| missing_asset_flag | 263 |
| missing_asset_symbol | 263 |
| multi_asset_score_below_90 | 43 |

## Next Safe Actions

1. Improve classification for scarce event types before changing caps.
2. Keep macro capped unless Claude approves a separate macro stream.
3. Split `other` before allowing it to fill more backtest slots.
4. Add source/entity rules for unsupported but relevant assets instead of faking Binance symbols.
5. Inspect `results/v043_stratified_selection_blocked_examples.csv` for scarce event-type examples.
