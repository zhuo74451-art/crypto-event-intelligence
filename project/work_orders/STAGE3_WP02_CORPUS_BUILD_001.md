# Stage 3 WP-02 Corpus Build 001

**Issue:** #29  
**Draft PR:** #30  
**Branch:** `feat/stage3-wp02-historical-data-factory`  
**Reviewed Head:** `9fbd501a5d7f31404bea7312ae009447f684f47f`

Continue the same WP-02 branch and Draft PR. Preserve valid infrastructure. Do not begin WP-03.

## C00 — Safe synchronization

Fetch refs, check out the existing branch and fast-forward only. Stop for tracked local changes or unexplained untracked product files. Do not reset, clean, stash, rebase or create another branch.

## C01 — Correct the source registry and prove feasibility

Reconcile the machine registry, family bindings and report. The current report claims 15 entries, its table sums to 12, and the implementation registers 11 source IDs.

Create explicit source-to-family bindings rather than double-counting one source as multiple registry entries. For every source and binding record:

- exact source ID and family;
- class: QUALIFYING_EVIDENCE, DISCOVERY_ONLY, MARKET_OUTCOME or REJECTED;
- public read-only endpoint;
- authority and fact permission;
- parser version;
- observed historical coverage from bounded probes;
- rate-limit response evidence;
- health-check timestamp and result;
- fallback source;
- permission and excerpt-storage note.

Run bounded live probes. Do not state coverage, permissions, rate limits or feasibility solely from configuration. Record exact request count, response status, sample dates and parser result. If a source blocks or requires credentials, classify it honestly and try documented public fallbacks.

The machine registry and feasibility report must have identical counts.

## C02 — Concrete production adapters

Implement real finite adapters for enough official/public sources to support every family. An abstract base class and MockAdapter are not production acquisition.

Minimum pilot route:

- regulatory: at least one SEC/CFTC or equivalent official adapter;
- corporate: official filing or issuer-release adapter with primary-source verification;
- macro: at least one Fed/BLS/Eurostat official adapter;
- technology: GitHub Advisory or NVD official public adapter;
- market events: official exchange announcement/listing/delisting adapter, not only price bars;
- security: CISA/NVD/GitHub Advisory or other official disclosure adapter;
- outcomes: one primary and one fallback public OHLCV adapter.

Each adapter must implement bounded pagination, timeout, retry, rate limiting, parser version, source URL preservation and typed error classification. No credentialed endpoint or access bypass.

## C03 — Repair acquisition durability and budgets

Fix the current false guarantees.

Required behavior:

- `record_limit` and `max_record_budget` are hard ceilings; do not return 20 records for a limit of 12;
- a completed checkpoint does not restart from page 1;
- resume after interruption continues from the first uncommitted page;
- accepted raw records are written atomically page-by-page before the checkpoint advances;
- checkpoint and output commit form one recoverable unit;
- duplicate pages or unstable page tokens do not duplicate intake records;
- request fingerprint includes source, range, limits, page size, parser version and adapter version;
- failed terminal runs preserve the last committed data and exact error;
- completed resume returns zero new records and the same committed total.

Add host-observable tests for kill/interruption, output-before-checkpoint failure, checkpoint-before-output failure, completed resume, exact ceilings and duplicate-page recovery.

## C04 — Implement missing production responsibilities

Add the production modules and tests absent from the current Head:

- `checkpoints.py` for atomic checkpoint/output transactions;
- `provenance.py` for source-to-evidence-to-case edges;
- `regimes.py` for versioned deterministic regime assignment;
- `outcomes.py` for separate 1h/6h/24h/3d/7d observations;
- source-specific adapters under a clear adapter package;
- SQLite materialization and reverse round-trip verification.

Do not put outcome values into case or evidence input hashes.

## C05 — Replace placeholder auditing with computed auditing

`CorpusAuditor` must inspect the actual artifacts. Remove every hard-coded or assumed pass, including:

- future leakage = 0;
- cross-split identity = 0;
- cross-split chain = 0;
- BLIND contamination = 0;
- outcome violations = 0;
- deterministic rebuild = true without a second build;
- audit coverage = 100% without traversal.

Compute and report exact violating IDs for every gate. Missing required artifacts or a missing second rebuild must fail, not pass.

Required mutation tests:

- future evidence;
- duplicate accepted case;
- cross-split event identity;
- cross-split correction chain;
- BLIND case/identity/chain/outcome contamination;
- missing source permission;
- missing point-in-time fields;
- invalid outcome window;
- outcome data entering an input hash;
- broken provenance edge;
- nondeterministic ordering;
- changed source content;
- missing second rebuild.

## C06 — Real 120-case pilot

Run actual bounded public reads and build at least 120 QUALIFIED cases, at least 20 per family.

Pilot requirements:

- all six families represented;
- no synthetic, cloned or timestamp-shifted cases;
- every case traces to permitted public evidence;
- every accepted case has explicit authority, permission, first-seen, retrieval and assessment times;
- every case has a stable event identity;
- correction-chain fields are explicit when applicable;
- affected asset or benchmark mapping is explicit;
- regime assignment includes rule version;
- outcome records remain separate;
- at least 1h, 6h and 24h outcome coverage for every accepted case;
- 3d and 7d coverage reported honestly;
- pilot future leakage, duplicate IDs, cross-split identity/chain and BLIND contamination are all zero;
- two clean pilot rebuilds produce identical hashes.

Before scaling, write a pilot gate section with exact distributions, source failure rates, rejection reasons, missing outcomes and runtime.

If fewer than 120 qualified cases or fewer than 20 per family can be supported after real fallback attempts, stop with `WP02_SOURCE_FEASIBILITY_BLOCKED` or `WP02_DATA_QUALITY_BLOCKED`. Do not claim acceptance.

## C07 — Scale to the complete 1,500-case corpus

Only after the pilot passes, continue the same finite checkpointed workflow to at least 1,500 QUALIFIED cases covering 2021-01-01 through 2026-06-30 UTC.

Mandatory gates:

- all six event families;
- at least 150 qualified cases per family;
- no family above 35%;
- bull, bear, ranging, high_volatility, crisis and recovery represented;
- unknown regime at most 10%;
- critical point-in-time completeness 100%;
- authority and permission completeness 100%;
- accepted future leakage 0;
- duplicate accepted case IDs 0;
- cross-split event identities 0;
- cross-split correction chains 0;
- BLIND case/identity/chain/outcome contamination 0;
- outcome structural violations 0;
- source-to-evidence-to-case-to-outcome audit coverage 100%;
- benchmark 24h outcome coverage at least 95%;
- two clean full rebuilds produce identical root and artifact hashes.

Do not meet counts through repeated descriptions of one event, cloned records, synthetic events or timestamp shifting.

## C08 — Canonical artifacts

Produce the full canonical corpus under `data/historical_v1/`:

- `source_registry.yaml`;
- `cases.jsonl` or documented deterministic shards;
- `evidence.jsonl` or shards;
- `correction_chains.jsonl`;
- `market_bars.jsonl` or deterministic shards;
- `outcome_windows.jsonl` or shards;
- `split_manifest.json`;
- `build_manifest.json`;
- `quality_report.json`;
- `rejected_records.jsonl`;
- `corpus_report.md`.

Keep tracked files within GitHub limits. Record every shard and hash in the build manifest. Canonical artifacts must contain no credentials, private paths, full article bodies or volatile build timestamps inside deterministic hashes.

## C09 — Reports and evidence consistency

Complete and synchronize:

- `docs/stage3/WP02_SOURCE_FEASIBILITY.md`;
- `docs/stage3/WP02_DATA_FACTORY_REPORT.md`;
- `docs/stage3/WP02_CORPUS_AUDIT.md`;
- `docs/stage3/WP02_REJECTION_REPORT.md`;
- PR #30 body;
- Issue #29 receipt.

Reports must distinguish executed live evidence, configuration, assumptions, rejected sources, incomplete cases and unsupported claims. Counts must be derived from canonical artifacts, never handwritten independently.

## C10 — Tests and final receipt

Run focused data-factory tests, all cognition_v2 regressions, Stage 2 regressions, the full repository suite, the same full command on current `origin/main` for claimed pre-existing blockers, and `git diff --check`.

Push only the existing branch and update only Draft PR #30 and Issue #29. Do not self-merge.

Stop with:

```text
terminal_state: <WP02_ACCEPTED_CANDIDATE|WP02_SOURCE_FEASIBILITY_BLOCKED|WP02_DATA_QUALITY_BLOCKED|LOCAL_STATE_REVIEW_REQUIRED>
repo: zhuo74451-art/crypto-event-intelligence
issue: 29
pr: 30
branch: feat/stage3-wp02-historical-data-factory
start_head: 9fbd501a5d7f31404bea7312ae009447f684f47f
final_remote_head: <exact 40-char SHA>
actual_registry_source_ids: <integer>
source_family_bindings: <integer>
registry_report_counts_match: <pass/fail>
live_source_probes: <exact mapping>
concrete_source_adapters: <exact list>
completed_resume_new_records: 0
record_limit_hard_ceiling: <pass/fail>
atomic_output_checkpoint_recovery: <pass/fail>
placeholder_audit_values_remaining: 0
pilot_qualified_cases: <integer>
pilot_family_distribution: <exact mapping>
pilot_rebuild_one_hash: <sha256>
pilot_rebuild_two_hash: <sha256>
pilot_gate: <pass/fail>
total_intake_records: <integer>
qualified_cases: <integer>
rejected_or_quarantined_cases: <integer>
family_distribution: <exact mapping>
regime_distribution: <exact mapping>
year_distribution: <exact mapping>
source_distribution: <exact mapping>
critical_time_completeness: <percent>
authority_permission_completeness: <percent>
future_leakage_violations: <integer>
duplicate_accepted_case_ids: <integer>
cross_split_event_identities: <integer>
cross_split_correction_chains: <integer>
blind_tuning_contamination: <integer>
outcome_structural_violations: <integer>
benchmark_24h_outcome_coverage: <percent>
audit_path_coverage: <percent>
rebuild_one_root_hash: <sha256>
rebuild_two_root_hash: <sha256>
deterministic_rebuild: <pass/fail>
canonical_artifact_size_bytes: <integer>
focused_tests: <exact result>
cognition_v2_regression: <exact result>
stage2_regression: <exact result>
full_suite_branch: <exact result>
full_suite_main_comparison: <exact result>
git_diff_check: <pass/fail>
old_cognition_core_modified: no
pr_16_draft_unmerged: <pass/fail>
paid_api_calls: 0
real_model_calls: 0
postgres_installed_or_started: no
background_processes_created: 0
blockers: <none-or-list>
```

`WP02_ACCEPTED_CANDIDATE` is valid only when `qualified_cases >= 1500`, all mandatory gates pass and the full reports exist. Do not begin WP-03.
