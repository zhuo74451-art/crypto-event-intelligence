# Unresolved Questions — w1_001

## P0 (Blocks Development Set Completion)

None — all eight objects can be created with honest "unknown" markers.

## P1 (Should Be Answered Before Pilot Calibration)

1. **Does Hyperliquid candleSnapshot retain data for 2026-05-25?** If not, HYPE price backfill is impossible and the Outcome will permanently have null reaction data.

2. **What is a reasonable t0_uncertainty_seconds for whale position events?** 3600s (1 hour) is a guess. Analysis of typical delay between on-chain action and third-party detection is needed.

3. **Is there a known HYPE/USD or HYPE/USDT price feed alternative?** DexScreener, CoinGecko, or Hyperliquid REST API may provide historical data. This needs investigation.

## P2 (Can Be Answered Later)

4. **Should HYPE have a different benchmark than BTC?** HYPE's correlation with BTC may be low. An altcoin index or no benchmark might be more appropriate. This is a protocol-level question for v1.1.

5. **What is the typical volatility profile for HYPE?** Without historical data, materiality assessment is impossible. This affects the historical_materiality assessment in Outcome.

6. **Is the 15m candle interval appropriate for HYPE?** The protocol supports 1m for Binance assets but HYPE via Hyperliquid defaults to 15m. The impact of this reduced granularity on attribution sensitivity is unquantified.

## Protocol-Level Questions (Not Actionable Here)

7. The protocol requires `usable_t0` hard gate but allows `broadcast_time` as `actual_time_basis`. When the difference between broadcast_time and actual action_time is large (potentially hours for whale positions), at what point does `usable_t0` become "fail" rather than "unknown"? No threshold is defined.
