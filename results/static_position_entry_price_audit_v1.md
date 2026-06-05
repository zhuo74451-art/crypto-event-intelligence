# Entry Price Consistency Audit v1.8F-hotfix

## Formula
- long: implied = (position_value - unrealized_pnl) / abs(size)
- short: implied = (position_value + unrealized_pnl) / abs(size)
- blocked if deviation > 2%

| address | entity | asset | side | displayed | implied | dev% | blocked |
|---|---:|---:|---:|---:|---:|---|
| 0x6c8512516ce566 | Matrixport Related | ETH | long | 2265.44 | 2265.44 | 0.0% | False |
| 0x8def9f50456c6c | loraclexyz | TON | long | 1.87 | 1.87 | 0.0% | False |
| 0x8def9f50456c6c | loraclexyz | HYPE | short | 45.51 | 45.51 | 0.0% | False |
| 0x8def9f50456c6c | loraclexyz | VVV | short | 18.97 | 18.97 | 0.0% | False |
| 0x8def9f50456c6c | loraclexyz | LIT | short | 1.20 | 1.20 | 0.0% | False |
| 0x082e843a431aef | Unknown HYPE Whale | HYPE | long | 38.68 | 38.68 | 0.0% | False |
| 0x8def9f50456c6c | loraclexyz | ASTER | long | 0.74 | 0.74 | 0.0% | False |
| 0x8def9f50456c6c | loraclexyz | ZEC | long | 543.62 | 543.62 | 0.0% | False |
| 0x8def9f50456c6c | loraclexyz | XMR | long | 339.70 | 339.70 | 0.0% | False |
