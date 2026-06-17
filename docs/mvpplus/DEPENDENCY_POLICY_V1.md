# Dependency Policy v1 — MVP+

## Principles

1. **Prefer mature projects** over custom implementations.
2. **Thin adapters only** — no deep forks or reimplementations.
3. **No duplicate dependencies** — one HTTP client (httpx), one exchange SDK (ccxt if needed, else direct REST).
4. **No large frameworks** for static HTML (no React/Vue/etc.)
5. **Pin versions** for reproducibility.
6. **No new dependencies without review** by Lane 6.

## Approved for MVP+

| Dependency | Version | Lane | Usage |
|-----------|---------|------|-------|
| hyperliquid-python-sdk | 0.23.0 | L1 | Hyperliquid Info API |
| httpx | 0.28.1 | L1, L3, L4 | HTTP requests |
| ccxt | latest* | L3 | Exchange market data |
| pytest | 9.0.3 | All | Testing |
| pydantic | 2.13.3 | All | Data validation (existing) |

*ccxt not yet installed — Lane 3 may install pinned version.

## Internal Production Phase (NOT MVP+)

| Dependency | Reason deferred |
|-----------|----------------|
| APScheduler 3.11.x | No daemon/scheduler in MVP+ (one-shot only) |
| SQLite | No persistent state in MVP+ |
| Any message broker (Kafka/Redis) | Out of scope |

## Installation Rules

- Lane 1 may install/verify: `hyperliquid-python-sdk` (already installed 0.23.0)
- Lane 3 may install: `ccxt`
- All other lanes: use existing dependencies only
- No `pip install --upgrade` of packages that would break existing code
- All installations recorded in THIRD_PARTY_REUSE_MANIFEST.json
