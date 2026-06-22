# Code Retention Audit V1

**Audit Date:** 2026-06-22  
**Baseline:** `PROJECT_MAINLINE.md`  
**Scope:** All top-level directories and core modules in `market_radar/`

Each entry is classified as:
- **RETAIN** — directly usable for the mainline product
- **ADAPT** — useful concept but needs refactoring/reintegration
- **QUARANTINE** — not immediately needed; keep for reference, no active development
- **DELETE_CANDIDATE** — no information increment for the new mainline

---

## Top-Level Directories

### `market_radar/` — Core Engine
| Module | Classification | Current Purpose | Referenced By | Info Increment | Deletion Risk | Evidence |
|--------|---------------|-----------------|---------------|----------------|---------------|----------|
| `shared/` | **RETAIN** | Shared pipeline contracts, models, gates, renderers | All pipeline code, tests | High — models, gates, evidence contracts are mainline building blocks | High — would break entire pipeline | Core pipeline architecture |
| `operations/` | **ADAPT** | Run history, recovery, shadow runs, source health | Integration layer, CLI tools | Medium — run lifecycle, evidence ledger useful; scheduler_config needs review | Medium — no active scheduler use | Operational foundation |
| `integration/` | **ADAPT** | One-shot pilot, operator catalog, feed providers | Shared pipeline, scripts | Medium — one-shot runner aligns with pilot boundary | Medium — operator workbench may need quarantine | Current pilot boundary |
| `whale_domain/` | **QUARANTINE** | Whale position tracking, portfolio engine | Integration, scripts | Low — interesting domain but not in current pilot scope | Low — isolated module | Not in evidence-pilot scope |
| `external_adapters/` | **ADAPT** | CCXT, Hyperliquid, HTTP transport adapters | Shared pipeline | High — adapter contract is mainline relevant | High — active test coverage | Adapter contract architecture |
| `intelligence_feed/` | **QUARANTINE** | Event intelligence clustering, dedup, narrative | Integration, scripts | Medium — dedup/scoring concepts useful later | Low — feed pipeline inactive | Not in current pilot |
| `market_view/` | **QUARANTINE** | Market data loader and view models | Not actively referenced | Low — market view not in pilot scope | Low — isolated module | Outside pilot boundary |
| `workbench/` | **QUARANTINE** | Operator workbench bundle/renderer | Integration | Low — operator UI not in scope | Low — isolated module | Outside pilot boundary |

### `scripts/` — Utility & Automation Scripts
| Classification | Count | Rationale |
|---------------|-------|-----------|
| **ADAPT** | ~15 | Core validation, evidence, and pilot-relevant scripts (`validate_mainline_docs.py`, `validate_source_adapter_outputs.py`, etc.) |
| **QUARANTINE** | ~180 | Market radar version-specific run scripts (`run_market_radar_v112*`, `run_market_radar_v113*`, etc.) — historical execution records |
| **DELETE_CANDIDATE** | ~5 | Legacy planning scripts no longer referenced (`build_claude_manual_reduction_prompt.py`, old Claude query scripts with hardcoded old paths) |

### `tests/` — Test Suite
| Classification | Rationale |
|---------------|-----------|
| **RETAIN** | Tests validate existing contracts. Run on current main. Cannot delete without losing regression coverage. |

### `docs/` — Documentation
| Classification | Rationale |
|---------------|-----------|
| **RETAIN** | Canonical 5 docs: `README.md`, `PROJECT_MAINLINE.md`, `ARCHITECTURE.md`, `INDEX.md`, `PROJECT_STATUS.md` |
| **ADAPT** | Operational docs: `operations/`, `qa/`, `feeds_market_ui/` — useful reference but may need rebranding |
| **QUARANTINE** | Historical release/audit evidence in `releases/`, `audits/`, `research/` — keep as commit records |
| **DELETE_CANDIDATE** | Already purged legacy planning docs (26 files removed in this task) |

### `results/` — Output Reports
| Classification | Rationale |
|---------------|-----------|
| **QUARANTINE** | Historical execution outputs. Keep as evidence of past runs. No active development. |

### `runs/` — Run Artifacts
| Classification | Rationale |
|---------------|-----------|
| **QUARANTINE** | Historical run records from market radar versions v110-v119. Keep as execution evidence. |

### `data/` — Data Files
| Classification | Rationale |
|---------------|-----------|
| **QUARANTINE** | Historical CSV and SQLite data. May be useful for replay/reference later. |

### `config/` — Configuration
| Classification | Rationale |
|---------------|-----------|
| **ADAPT** | Configuration files. May need cleanup to remove old version references. |

### `deploy/` — Deployment
| Classification | Rationale |
|---------------|-----------|
| **QUARANTINE** | Deployment artifacts. Not applicable until production boundary is approved. |

### `fixtures/` — Test Fixtures
| Classification | Rationale |
|---------------|-----------|
| **RETAIN** | Shared test fixtures used by the test suite. |

### `remote_x_monitor/` — Telegram Publisher
| Classification | Rationale |
|---------------|-----------|
| **QUARANTINE** | Telegram publisher with docker-compose. Not in current one-shot pilot scope. Keep for future reference. |

### `qa/` — QA Framework
| Classification | Rationale |
|---------------|-----------|
| **ADAPT** | Independent QA scanners — read-only, deterministic. Valuable for mainline verification. |

### `research/` — Research Scripts
| Classification | Rationale |
|---------------|-----------|
| **QUARANTINE** | Week 1 research dataset builders. Historical research tools. |

### `memory/` — Project Memory
| Classification | Rationale |
|---------------|-----------|
| **DELETE_CANDIDATE** | Contains old project state, roadmap, handoffs under `事件情报系统/`. Duplicates now-purged docs. No active reference. |

### `requirements/` — Dependencies
| Classification | Rationale |
|---------------|-----------|
| **RETAIN** | Requirements files define the project's Python dependencies. |

### `schemas/` — Schema Definitions
| Classification | Rationale |
|---------------|-----------|
| **ADAPT** | Market radar adapter schemas. Useful reference for future adapter work. |

### `artifacts/` — Build Artifacts
| Classification | Rationale |
|---------------|-----------|
| **DELETE_CANDIDATE** | Build artifacts. Not useful without the build pipeline that produced them. |

### `logs/` — Log Files
| Classification | Rationale |
|---------------|-----------|
| **DELETE_CANDIDATE** | Runtime logs. Not useful as committed artifacts. |

### `runtime/` — Runtime Data
| Classification | Rationale |
|---------------|-----------|
| **QUARANTINE** | Runtime state files. May be needed for local operation. |

---

## Summary Counts

| Classification | Count |
|---------------|-------|
| **RETAIN** | 6 (shared/, tests/, fixtures/, requirements/, docs canonical 5, ~180 test scripts) |
| **ADAPT** | 7 (operations/, integration/, external_adapters/, scripts core, config/, qa/, schemas/, docs operational) |
| **QUARANTINE** | 12 (whale_domain/, intelligence_feed/, market_view/, workbench/, results/, runs/, data/, deploy/, remote_x_monitor/, research/, runtime/, docs historical) |
| **DELETE_CANDIDATE** | 4 (memory/, artifacts/, logs/, scripts legacy planning helpers, docs purged) |

**Note:** `scripts/` and `docs/` span multiple classifications at sub-directory level. Counts above are by primary classification.

---

## Audit Principles

1. **No business code deleted in this round** — only pure legacy planning docs and empty/unreferenced auxiliary files.
2. **DELETE_CANDIDATE** means the item should be reviewed in a future cleanup round, not deleted now.
3. **RETAIN** items are actively used by the test suite or are canonical mainline documents.
4. **ADAPT** items contain useful engineering value but need naming/scope changes to match mainline.
5. **QUARANTINE** items are kept as-is with no active development budget.

---

## Next Steps

1. Run detailed module-level audit for `scripts/` to identify specific DELETE_CANDIDATE files.
2. Refactor `market_radar/` module names and package descript
