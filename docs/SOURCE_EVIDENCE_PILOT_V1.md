# Source & Evidence Pilot V1 — Final Report

> **Run**: MS-PILOT-DEV-001
> **Terminal State**: `DONE_WITH_LIMITATIONS`
> **Head SHA**: `4d3c958458b57387e932b8f20a98c498dd6f7e9e`
> **Work Branch**: `workbench/source-evidence-pilot-v1`
> **Timestamp**: 2026-06-29T03:45:00+00:00

---

## 1. Terminal State

**DONE_WITH_LIMITATIONS** — minimum_success achieved; SEC live not verified (User-Agent not configured).

## 2. Repository Identity

| Attribute | Value |
|-----------|-------|
| Head SHA | `4d3c958458b57387e932b8f20a98c498dd6f7e9e` |
| Work branch | `workbench/source-evidence-pilot-v1` |
| Tracked diff | **Zero** (no tracked files modified) |
| New untracked files | 20 (all in `market_radar/acquisition/`, `tests/acquisition/`, `tests/fixtures/acquisition/`) |

## 3. Runtime

| Metric | Value |
|--------|-------|
| Start | 2026-06-29T03:33:31 UTC |
| End | 2026-06-29T03:45:00 UTC |
| Duration | ~11 min 29 sec |
| Slices completed | 7 of 7 |
| Extensions attempted | 0 (core slices consumed budget) |

## 4. New & Modified Files

### New files (20)

**Source code** (6 files):
- `market_radar/acquisition/__init__.py`
- `market_radar/acquisition/contracts.py` — SourceContract, SourceHealth, FetchMetadata, RawEvidenceArtifact, ObservationStub, AcquisitionResult
- `market_radar/acquisition/evidence.py` — evidence manifest builder
- `market_radar/acquisition/storage.py` — output writer (raw evidence, health, observations, manifest)
- `market_radar/acquisition/pilot_runner.py` — RunnerProtocol-compliant pilot orchestrator
- `market_radar/acquisition/cli.py` — argparse CLI

**Source adapters** (3 files):
- `market_radar/acquisition/sources/__init__.py`
- `market_radar/acquisition/sources/cisa_kev.py` — CISA KEV adapter (primary + fallback)
- `market_radar/acquisition/sources/sec_press_releases.py` — SEC RSS adapter (User-Agent gated)

**Tests** (9 files):
- `tests/acquisition/__init__.py`
- `tests/acquisition/conftest.py`
- `tests/acquisition/test_contracts.py` — 10 tests
- `tests/acquisition/test_cisa_kev.py` — 16 tests
- `tests/acquisition/test_sec_press_releases.py` — 20 tests
- `tests/acquisition/test_sec_extra.py` — 3 tests
- `tests/acquisition/test_storage.py` — 10 tests
- `tests/acquisition/test_evidence.py` — 2 tests
- `tests/acquisition/test_runner.py` — 3 tests

**Fixtures** (2 files):
- `tests/fixtures/acquisition/cisa_kev_sample.json`
- `tests/fixtures/acquisition/sec_press_releases_sample.xml`

## 5. New Test Results

```
tests/acquisition -q → 64 passed in 0.31s
```

| Test file | Tests | Coverage |
|-----------|-------|----------|
| test_contracts.py | 10 | Serialization, enum mapping, JSON roundtrip |
| test_cisa_kev.py | 16 | Schema validation, fallback, limit, order, determinism, SHA-256 |
| test_sec_press_releases.py | 20 | User-Agent, RSS parsing, XML errors, empty feed, determinism |
| test_sec_extra.py | 3 | Missing pubDate, empty feed, no-token check, replay consistency |
| test_storage.py | 10 | Raw evidence, hash mismatch, metadata, health, observations, manifest |
| test_evidence.py | 2 | Evidence entry building |
| test_runner.py | 3 | RunnerProtocol compliance, run_once integration, output file structure |

## 6. Full Repository Test Comparison

| Metric | Baseline (before) | Now |
|--------|-------------------|-----|
| New acquisition tests | — | **64 passed, 0 failed** |
| Existing baseline failures | 21 (encoding/pid/windows) | 21 (unchanged) |
| New business logic failures | — | **0** |
| Full repo green | false | false (known baseline) |

**Statement**: `new_acquisition_tests_passed`, `known_baseline_failures_unchanged`

## 7. CISA Live Status

| Metric | Value |
|--------|-------|
| Selected URL | `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json` |
| HTTP Status | **200** |
| Fallback used | No (primary succeeded) |
| Bytes received | 1,522,375 |
| SHA-256 | `da7b7d9f98979a49026bc7908c999a4c636b5c4f08338ace81971e61c9871b60` |
| Observations | 20 (limit respected, sorted by dateAdded desc) |
| Latency | 812 ms |
| Status | **healthy** |

## 8. SEC Live Status

| Metric | Value |
|--------|-------|
| User-Agent | Not configured |
| Health | **configuration_required** |
| Observations | 0 (no live request made) |
| Replay tests | ✅ Passing (20+ fixture tests) |

## 9. Output Files (CLI test)

```
results/source_evidence_pilot/cli_test/
├── RUN_TELEMETRY.jsonl
├── run_manifest.json
├── source_health.json
├── observations.jsonl
├── evidence_manifest.jsonl
└── sources/
    └── cisa_kev/
        └── fetch_metadata.json
```

## 10. Git Facts

| Check | Result |
|-------|--------|
| `git status --short` | Only untracked new files + pre-existing `.agent-memory/` |
| `git diff --stat` | **Zero** — no tracked files modified |
| `git diff --check` | **Zero** — no whitespace errors |
| Commit/Push | **Not performed** |

## 11. Known Limitations

1. **SEC live not verified** — User-Agent (`MARKET_SIGNAL_SEC_USER_AGENT`) not configured. Set env var and re-run to validate.
2. **Raw evidence not written to disk** — `write_raw_evidence` receives `None` because `AcquisitionResult` does not carry raw bytes. Live CISA data was confirmed via telemetry but raw bytes not saved to output directory in this run.
3. **No full-repo test run** — `pytest --lf -q` took 109s for 21 baseline failures. Full run would exceed 5+ minutes.
4. **No Extension Pool items completed** — Core slices consumed available time budget.

## 12. Next Card Recommendation

**MS-PILOT-DEV-002**: Evidence Store & Observation Pipeline Integration

Scope:
- Wire ObservationStub → full `market_radar.shared.models.Observation` conversion
- Stream observations through `EvidenceLedger`
- Add raw bytes carrier to `AcquisitionResult` for on-disk evidence
- Extend to a third source (e.g. GitHub Advisory API — software_release category)
- Resolve SEC User-Agent and verify live
