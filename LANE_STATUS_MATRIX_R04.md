# Lane Status Matrix — W1_PARALLEL_REPAIR_CONTROL_R04

**Author**: Project Controller (read-only)
**Updated**: 2026-06-17
**Authoritative Main**: `cfc1e09b9c4e0c734ae4bfc913b726c6e2b145f9`

---

## Status Overview

| Lane | Branch | HEAD SHA | Status | Worktree | Merge-Base |
|------|--------|----------|--------|----------|------------|
| **main** | `main` | `cfc1e09` | **FROZEN** | — | — |
| **W2** | `workbench/mvpplus-whale-prod-v2` | `dde800b` | **REPAIR_REQUIRED** | — | `cfc1e09` ✓ |
| **W3** | `workbench/mvpplus-feeds-market-ui-v2` | `dbb15da` | **REPAIR_REQUIRED** | `feeds-market-ui-v2` | `cfc1e09` ✓ |
| **W4** | `workbench/mvpplus-open-source-adapters-v1` | `dab56b3` | **REPAIR_REQUIRED** | `mvpplus-open-source-adapters-v1` | `cfc1e09` ✓ |
| **W5** | `workbench/mvpplus-ops-foundation-v1` | `e1d5d5c` | **REPAIR_REQUIRED** | — | `cfc1e09` ✓ |
| **W6** | `workbench/mvpplus-independent-qa-v1` | `504518c` | **REPAIR_REQUIRED** | — | `cfc1e09` ✓ |

All five lanes fork cleanly from `main` at `cfc1e09`. All local branches match their `origin/` counterparts.

---

## Lane Details

### W2 — Whale Production v2
- **Branch**: `workbench/mvpplus-whale-prod-v2`
- **HEAD**: `dde800b` — `evidence(w2): update tested_commit and record previous_remote_head`
- **Commits on lane** (vs main):
  1. `dba3460` — feat(whale-domain): deterministic whale intelligence domain v2
  2. `4d43340` — fix(whale-domain): W2 delta repair — semantic fixes
  3. `dde800b` — evidence(w2): update tested_commit and record previous_remote_head
- **Owned paths**: `market_radar/whale_domain/`, `tests/mvpplus/whale_domain/`, `artifacts/evidence/w2_*`
- **Worktree**: None
- **Remote match**: ✓

### W3 — Feeds Market UI v2
- **Branch**: `workbench/mvpplus-feeds-market-ui-v2`
- **HEAD**: `dbb15da` — `evidence(w3): update tested_commit and record previous_remote_head`
- **Commits on lane** (vs main):
  1. `a69b4b6` — w3v2: intelligence feed truth layer + market view models + secure workbench
  2. `1a99511` — fix(feeds-market-ui): W3 delta repair — fixture truth, provenance, freshness
  3. `dbb15da` — evidence(w3): update tested_commit and record previous_remote_head
- **Owned paths**: `market_radar/intelligence_feed/`, `market_radar/market_view/`, `market_radar/workbench/`, `tests/mvpplus/feeds_market_ui/`, `artifacts/evidence/w3_*`
- **Worktree**: `crypto-event-intelligence-worktrees/feeds-market-ui-v2`
- **Remote match**: ✓

### W4 — Open Source Adapters v1
- **Branch**: `workbench/mvpplus-open-source-adapters-v1`
- **HEAD**: `dab56b3` — `docs(mvpplus): add W4 repair R02 evidence report`
- **Commits on lane** (vs main):
  1. `85df823` — feat(mvpplus): Window 4 — HTTPX transport, Hyperliquid SDK adapter, CCXT public adapter
  2. `0125fe6` — docs(mvpplus): add W4 adapter foundation evidence report
  3. `23d3cc0` — fix(mvpplus): W4 adapter interface repair R02
  4. `dab56b3` — docs(mvpplus): add W4 repair R02 evidence report
- **Owned paths**: `market_radar/external_adapters/`, `tests/mvpplus/adapters/`, `docs/adapters/`, `artifacts/evidence/w4_*`
- **Worktree**: `crypto-event-intelligence-wt/mvpplus-open-source-adapters-v1`
- **Remote match**: ✓

### W5 — Operations Foundation v1
- **Branch**: `workbench/mvpplus-ops-foundation-v1`
- **HEAD**: `e1d5d5c` — `docs(evidence): R02 repair evidence — tested_commit=9e590dda, 61/61 p...`
- **Commits on lane** (vs main):
  1. `1b11d56` — feat(ops): W5 — operations foundation, generic internal-run infrastructure
  2. `9e590dd` — fix(ops): W5 delta concurrency repair — atomic lock, unique tmp, schema...
  3. `e1d5d5c` — docs(evidence): R02 repair evidence — tested_commit=9e590dda, 61/61 p...
- **Owned paths**: `market_radar/operations/`, `tests/mvpplus/operations/`, `docs/operations/`, `artifacts/evidence/w5_*`
- **Worktree**: None
- **Remote match**: ✓

### W6 — Independent QA v1
- **Branch**: `workbench/mvpplus-independent-qa-v1`
- **HEAD**: `504518c` — `qa: establish independent QA foundation — mvpplus`
- **Commits on lane** (vs main):
  1. `504518c` — qa: establish independent QA foundation — mvpplus
- **Owned paths**: `qa/mvpplus/`, `tests/mvpplus/independent_qa/`, `docs/qa/`, `artifacts/evidence/w6_*`
- **Worktree**: None
- **Remote match**: ✓

---

## Repair Activity Detected (post-ticket-activation)

| Lane | R02 Repair Pushed? | Evidence Present? | Notes |
|------|-------------------|-------------------|-------|
| W2 | ✓ `4d43340` + `dde800b` | `artifacts/evidence/w2_whale_domain_report.json` | Semantic fix + evidence update |
| W3 | ✓ `1a99511` + `dbb15da` | `artifacts/evidence/w3_feeds_market_ui_report.json` | Fixture truth/provenance fix + evidence |
| W4 | ✓ `23d3cc0` + `dab56b3` | `artifacts/evidence/w4_adapter_foundation_report.json` + local delta evidence | Adapter interface repair |
| W5 | ✓ `9e590dd` + `e1d5d5c` | Evidence commit present | Concurrency/lock/tmp repair |
| W6 | — | `artifacts/evidence/w6_qa_foundation_report.json` | Baseline only; no R02 repair pushed |

---

## Blocking Rules (enforced)

- [x] **main frozen** — `cfc1e09` pinned; no local changes
- [x] **No merge** — no lane merged into main or into each other
- [x] **No Integration-v2** — not created
- [x] **No business code modification** — controller is read-only
- [ ] **Delta repair tickets only** — pending audit of each lane's R02 result

---

## Pending Audits

Before any lane can be accepted, the following must be verified per lane:
1. **Remote SHA** — matches the ticket's claimed commit
2. **Diff scope** — only owned paths modified; no cross-lane contamination
3. **Test results** — evidence file claims test pass counts
4. **Forbidden capability scan** — no wallet/exchange/signing imports (W4-specific)
5. **Independent verification** — W6 must be able to scan W2, W3, W4 once accepted
