# Permission Envelope v1 — MVP+

## Overview

Defines what each Lane is permitted to access, read, modify, and execute. Follows `deny by default` and `least privilege` principles.

## Lane Permissions

### Lane 1 — Hyperliquid Provider

| Resource | Permission |
|----------|-----------|
| Hyperliquid public Info API | Allow |
| hyperliquid-python-sdk | Allow |
| GitHub/PyPI for dependency verification | Allow |
| Project `scripts/mvpplus/lane1_hyperliquid/` | Read/Write |
| Contract schemas (read-only) | Read |
| All other network destinations | Deny |
| Wallet/Exchange APIs | Deny |

### Lane 2 — Whale Position Change & Risk Engine

| Resource | Permission |
|----------|-----------|
| Network access | **Deny** (use fixtures) |
| Project `scripts/mvpplus/lane2_whale_engine/` | Read/Write |
| Contract schemas (read-only) | Read |
| Fixtures | Read |

### Lane 3 — Market Context Provider

| Resource | Permission |
|----------|-----------|
| CCXT public market APIs | Allow |
| Binance public market API | Allow |
| Hyperliquid public Info API | Allow |
| GitHub/PyPI for dependency verification | Allow |
| Project `scripts/mvpplus/lane3_market_context/` | Read/Write |
| Contract schemas (read-only) | Read |

### Lane 4 — Existing Flash/News/TG Feeds

| Resource | Permission |
|----------|-----------|
| Server read-only data entry points | Allow (existing only) |
| Project `scripts/mvpplus/lane4_existing_feeds/` | Read/Write |
| `data/`, `runs/`, `results/` | Read |
| Contract schemas (read-only) | Read |
| Self-discovering new server paths | Deny |

### Lane 5 — Workbench UI

| Resource | Permission |
|----------|-----------|
| Network access | **Deny** (static HTML generation only) |
| Project `scripts/mvpplus/lane5_workbench_ui/` | Read/Write |
| `results/mvpplus/` | Read/Write |
| Contract schemas (read-only) | Read |

### Lane 6 — Integration

| Resource | Permission |
|----------|-----------|
| All project paths (via ownership map) | Read/Write |
| Public read-only APIs (verification only) | Allow |
| All other project resources | Read |
| Production databases | Deny |
| Trading endpoints | Deny |
| Secret/credential stores | Deny |

## Common Restrictions

All Lanes:

- **Never** read, write, or transmit wallet keys, API secrets, or passwords.
- **Never** place, modify, or simulate trades.
- **Never** access production databases.
- **Never** send Telegram/X messages.
- **Never** write credentials to code, logs, or git.
- **Never** scan user home directory, Documents, Downloads, or SSH configs.
- All HTTP requests: connect timeout, read timeout, bounded retry with exponential backoff, rate-limit awareness.
