# Project Status

**Status:** `MAINLINE_REBASELINED`

This project has been rebaselined to the mainline contract defined in [`PROJECT_MAINLINE.md`](../PROJECT_MAINLINE.md). Earlier roadmaps, phase plans, handoff packets, RC1 documents, and version-based planning no longer define current work.

## Product Identity

**Crypto Market Cognition & Signal OS** — an AI-first crypto market research and intelligence system that combines:

1. a multi-domain market world model;
2. point-in-time evidence and source health;
3. research claims, conflicts, and knowledge decay;
4. structured strategy distillation;
5. historical and shadow validation;
6. calibrated assessments with an explicit insufficient-evidence state.

## Five Core Subsystems

| Subsystem | Description |
|-----------|-------------|
| **Market World Model** | Macro, regulatory, geopolitical, spot, derivatives, stablecoin, on-chain, DeFi, token supply, fundamentals, security, sentiment, and data quality |
| **Research Intelligence** | Papers, official reports, industry research, conflicting evidence, knowledge decay, and testable hypotheses |
| **Trader Strategy Distillation** | Distillation of trader variable combinations, triggers, confirmations, time scales, and failure conditions — without persona mimicry |
| **Strategy Registry & Arbitration** | Strategy invocation by market regime and evidence, preserving disagreements and allowing `INSUFFICIENT_EVIDENCE` |
| **Evidence Acquisition** | Official APIs, RSS, web changes, body extraction, evidence archiving, academic discovery, and notification services |

## Existing Code

All existing modules (event normalization, Registry, deduplication, price backfill, run history, audit, market readers, whale domain, rendering, and operator capabilities) are treated as **engineering candidates** awaiting audit.

Each module will be assigned one of:

- `RETAIN`
- `ADAPT`
- `QUARANTINE`
- `DELETE`

Old test counts, old release labels, and old documentation do not alone justify retention.

## Current Implementation Boundary

The immediate target is a **one-shot, read-only acquisition and evidence pilot** for regulatory, legislative, macroeconomic, software-release, and security sources.

The pilot establishes:
- Source identity and timestamps
- Raw evidence or snapshot references
- Content hashes
- Fallback evidence
- Source health
- Normalized observations

## Default Operating Mode

The following are **disabled by default** and require explicit approval before activation:

- ❌ Recurring daemon / scheduler / cron services
- ❌ Production Telegram or external publishing
- ❌ Paid API subscriptions
- ❌ Order execution or auto-trading
- ❌ Systemd or OS-level service registration

Only one-shot, manual, or test-mode runs are permitted under the current boundary.

## Current Canonical Documents

- [`README.md`](../README.md)
- [`PROJECT_MAINLINE.md`](../PROJECT_MAINLINE.md)
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- [`docs/INDEX.md`](INDEX.md)
- [`docs/PROJECT_STATUS.md`](PROJECT_STATUS.md) (this file)

Historical release and audit materials (in `docs/releases/`, `docs/audits/`) serve as records of past commits and do not have current planning authority.
