# Stage 3 WP-02 Live Pilot and Scale 005

Issue #29 · Draft PR #30 · Branch `feat/stage3-wp02-historical-data-factory`  
Reviewed Head: `bc59f6c5601b20e7c6bce680cf527c48f2fc70fa`

Continue the same branch and PR. Do not begin WP-03.

## T00 Safe sync

Fetch refs, checkout the existing branch, fast-forward only. Stop for tracked local changes or unexplained untracked product files. No reset, clean, stash, rebase or new branch.

## T01 Close durable recovery evidence

Before live data work, replace weak recovery assertions with exact tests:

- output-write failure against an existing run leaves previous output bytes and checkpoint bytes unchanged;
- compare record count, SHA-256, byte size, page token, completed pages and status before/after failure;
- inject a real checkpoint-write failure after output commit and reconcile the ahead output exactly once without duplicates;
- completed resume makes zero adapter calls and reports zero newly acquired records;
- same-size/same-line-count content mutation is rejected by SHA-256;
- truncation is rejected;
- adapter and parser version mismatches are independently rejected;
- process reopen restores records and dedupe state;
- remove or strengthen broad `>=`, `<=` and file-exists-only assertions.

Do not stop after T01.

## T02 Bounded live probes

Probe every adapter intended for the pilot using finite public read-only requests. Record source/family, endpoint, UTC range, request count, status or typed failure, parser/adapter versions, parsed item count, earliest/latest publication time, malformed count, pilot eligibility and fallback result.

Every event family needs at least one pilot-eligible QUALIFYING_EVIDENCE source. OHLCV does not count as market-event evidence. Remove unsupported feasibility claims.

## T03 Production auditor

Audit actual canonical artifacts using explicit `assessment_time`. Missing files fail. Compute exact violating IDs for future leakage, missing authority/permission, duplicates, cross-split identity/chain, BLIND contamination, broken outcome references/windows and broken provenance. Require 24h outcome coverage >=95%, provenance coverage 100%, and a real second rebuild with all artifact/root hashes matching. Add mutation tests for every gate.

## T04 Canonical artifacts and SQLite

Create deterministic source registry, evidence, cases, correction chains, market bars, outcome windows, split manifest, build manifest, quality report, rejected records and corpus report under `data/historical_v1/`. Use sorted-key JSONL, deterministic ordering/shards and SHA-256 manifests. Materialize to SQLite and reverse-export to identical canonical records/hashes.

## T05 Real 120-case pilot

Build at least 120 QUALIFIED cases, at least 20 per family, from bounded public reads only. Every accepted case needs permitted evidence, exact URL, stable identity, publication/first-seen/retrieval/assessment times, authority, permission, asset mapping, versioned regime, separate 1h/6h/24h outcomes, 3d/7d outcome or missing reason, and complete provenance.

Pilot must have zero leakage, duplicate accepted IDs, cross-split identity/chain and BLIND contamination; 100% time/permission/provenance completeness; >=95% 24h outcome coverage; two identical rebuilds. If not achievable after fallbacks, stop honestly with a blocked state. Do not fabricate or scale.

## T06 Scale to >=1,500 QUALIFIED cases

Only after the pilot passes. Each family >=150, no family >35%; required regimes represented; unknown <=10%; frozen chronological BUILD/DEVELOPMENT/BLIND splits; all mandatory integrity gates zero; 24h coverage >=95%; provenance 100%; two identical full rebuilds. No synthetic/cloned/timestamp-shifted cases.

## T07 Reports

Complete and synchronize:

- `docs/stage3/WP02_SOURCE_FEASIBILITY.md`
- `docs/stage3/WP02_DATA_FACTORY_REPORT.md`
- `docs/stage3/WP02_CORPUS_AUDIT.md`
- `docs/stage3/WP02_REJECTION_REPORT.md`
- PR #30 body and Issue #29 receipt

Generate counts from canonical artifacts, not handwritten totals.

## T08 Verification and terminal state

Run focused WP-02, all cognition_v2, Stage 2 regressions, full branch suite, the same full command on current `origin/main`, and `git diff --check`.

`WP02_ACCEPTED_CANDIDATE` is valid only when the 120-case pilot and final >=1,500-case corpus pass every gate. Otherwise use `WP02_SOURCE_FEASIBILITY_BLOCKED`, `WP02_DATA_QUALITY_BLOCKED`, or `LOCAL_STATE_REVIEW_REQUIRED`.

Push only this branch; update PR #30 and Issue #29; do not merge.

Receipt must include exact final Head, live probes, pilot and final distributions, all integrity counts, outcome/provenance coverage, two rebuild hashes, focused/regression/full-suite results, zero paid/model calls, zero background processes, PR #16 still unmerged, and blockers.
