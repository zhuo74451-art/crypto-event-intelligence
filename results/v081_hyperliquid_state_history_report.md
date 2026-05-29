# v0.8.1 Hyperliquid State History Report

- status: needs_more_history
- history_rows: 9
- position_count: 9
- ready_positions: 0
- max_snapshots: 1 / 12
- large_change_steps: 0

## Positions

| entity | asset | side | snapshots | latest_value_usd | max_step_change_usd | status |
|---|---|---|---:|---:|---:|---|
| loraclexyz | HYPE | short | 1 | 102825385.9 | 0.0 | needs_more_history |
| Matrixport Related | ETH | long | 1 | 79076000.0 | 0.0 | needs_more_history |
| Unknown HYPE Whale | HYPE | long | 1 | 78492686.37 | 0.0 | needs_more_history |
| Unknown Hyperliquid Whale | BTC | long | 1 | 34750293.94 | 0.0 | needs_more_history |
| loraclexyz | BTC | short | 1 | 34169057.12 | 0.0 | needs_more_history |
| Unknown Hyperliquid Whale | BTC | short | 1 | 8409080.57 | 0.0 | needs_more_history |
| loraclexyz | VVV | short | 1 | 707903.03 | 0.0 | needs_more_history |
| loraclexyz | LIT | short | 1 | 697326.13 | 0.0 | needs_more_history |
| loraclexyz | TON | short | 1 | 6682.0 | 0.0 | needs_more_history |

## Rule

Use state history to detect position changes. A single current snapshot is not enough to prove a position-change alert.
