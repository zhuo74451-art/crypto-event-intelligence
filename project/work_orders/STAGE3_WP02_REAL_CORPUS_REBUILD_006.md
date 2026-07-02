# Stage 3 WP-02 Real Corpus Rebuild 006

Issue #29 · Draft PR #30 · Branch `feat/stage3-wp02-historical-data-factory`  
Reviewed Head: `fa263120c86488c8fd23c3b4cb4241aa3d298a5b`

Continue the same branch and PR. Preserve useful infrastructure, but invalidate the current seed-derived corpus. Do not begin WP-03.

## U00 — Safe synchronization

Fetch refs, check out the existing branch and fast-forward only. Stop for tracked local changes or unexplained untracked product files. No reset, clean, stash, rebase or new branch.

## U01 — Invalidate synthetic acceptance evidence

The current 1,500-case artifacts are not accepted historical data.

Remove them from accepted-corpus status and rewrite reports so they cannot be mistaken for evidence. No QUALIFIED case may contain or derive from:

- `seed-*` source IDs;
- `example.com` evidence URLs;
- generic titles such as `<Family> Event <n>`;
- placeholder hashes such as `hash-*` or `oh-*`;
- fabricated first-seen, retrieval, publication or assessment times;
- fixed/template outcome prices;
- manually rotated regime labels;
- cloned, timestamp-shifted or count-padding records.

Delete seed-filler code. A missing family or insufficient count must produce a blocked or incomplete state, never synthetic replacement.

## U02 — Add authenticity and provenance gates

A case counts as QUALIFIED only when all conditions are machine-verifiable:

- source ID exists in the registry and is QUALIFYING_EVIDENCE for that family;
- exact public source URL and source-native record ID exist;
- normalized evidence content has a real SHA-256 derived from the stored permitted fact/excerpt and source metadata;
- publication/effective time comes from the source when available;
- first-seen and retrieval times come from the acquisition run, never backdated;
- assessment time is explicit and not earlier than evidence availability;
- event identity is derived from actual source records;
- asset mapping and regime assignment have versioned rules and real market inputs;
- outcome observations come from real public OHLCV responses and carry provider-native timestamps and hashes;
- every evidence and outcome reference resolves to exactly one canonical record.

Add hard rejection gates for placeholder hosts, placeholder hashes, seed IDs, generic titles, repeated templates, impossible timestamp patterns and fixed-price duplication.

## U03 — Repair source feasibility by family

Prove at least one real QUALIFYING_EVIDENCE route for each family before the pilot:

- regulatory: official regulator enforcement/rule/filing evidence;
- corporate: official issuer filing or primary corporate disclosure, not discovery-only material;
- macro: working official economic release/API with historical records;
- technology: official advisory/repository release evidence;
- market: official exchange listing, delisting, outage, maintenance or market-structure notice; OHLCV alone does not qualify;
- security: official security incident/advisory evidence.

Run bounded probes with exact endpoint, range, request count, item IDs, parsed publication dates, failure class and fallback result. Unsupported routes remain rejected. If one family lacks a working route after documented fallbacks, stop `WP02_SOURCE_FEASIBILITY_BLOCKED`.

## U04 — Build reproducible raw snapshots

Persist permitted, minimal raw intake snapshots or normalized source records sufficient for deterministic rebuild:

- source-native ID;
- URL;
- source metadata and timestamps;
- permitted short excerpt or normalized facts;
- acquisition request fingerprint;
- adapter/parser version;
- response/content hash;
- retrieval time and checkpoint lineage.

Do not store full copyrighted articles. A rebuild must start from these persisted snapshots, not from an already-built case list.

## U05 — Repair auditor and split gates

The auditor must fail unless all canonical artifacts exist and all references resolve.

Required gates:

- future leakage uses evidence availability versus case `assessment_time`;
- missing outcome files fail when cases exist;
- each accepted case resolves source -> evidence -> case -> all required outcome windows;
- 24h coverage >=95% is included in `all_gates_pass`;
- provenance coverage 100% is included in `all_gates_pass`;
- authenticity/placeholder violations are included in `all_gates_pass`;
- split distribution is non-empty and approximately BUILD 60%, DEVELOPMENT 20%, BLIND 20%;
- event identities and correction chains remain within one split;
- BLIND case/identity/chain/outcome data cannot enter tuning inputs;
- diagnostics contain exact IDs and reasons;
- grouped indexes replace all-pairs scans where practical.

## U06 — Real 120-case pilot

Build at least 120 real QUALIFIED cases, at least 20 per family, from persisted public-source snapshots.

The pilot must span more than one year when source history permits and must not be artificially balanced by rewriting dates or labels. Report observed distributions honestly.

Required:

- all six families >=20;
- real source URLs and native IDs for 100%;
- real SHA-256 evidence hashes for 100%;
- critical time and permission completeness 100%;
- zero placeholder/synthetic records;
- zero future leakage and duplicate accepted IDs;
- valid BUILD/DEVELOPMENT/BLIND split allocation;
- 24h outcome coverage >=95%;
- provenance coverage 100%;
- two independent rebuilds from the same raw snapshots produce identical artifacts and root hashes.

If the pilot fails, stop with the correct blocked state. Do not scale.

## U07 — Scale to the real 1,500-case corpus

Scale only after the real pilot passes.

Final requirements:

- at least 1,500 real QUALIFIED cases;
- each family >=150 and no family >35%;
- coverage across the accepted historical range, not a patterned single-year template;
- multiple observed regimes derived from real market data;
- frozen BUILD/DEVELOPMENT/BLIND splits;
- zero synthetic/placeholder records;
- zero future leakage, duplicate IDs, cross-split identities/chains and BLIND contamination;
- outcome structural violations 0;
- 24h coverage >=95%;
- provenance coverage 100%;
- two clean rebuilds from persisted raw snapshots with identical file and root hashes.

## U08 — Canonical artifacts and manifest truth

The build manifest must list every artifact/shard hash and computed family, regime, year, source and split distributions. `total_intake_records` must reflect real intake. Correction-chain and rejected-record artifacts must be honest, including zero only when verified.

Canonical SQLite materialization and reverse export must preserve equivalent records and hashes.

## U09 — Reports, tests and terminal state

Complete the four WP-02 reports, PR body and Issue receipt from computed artifacts. Explicitly disclose rejected sources and records.

Run focused WP-02 tests, all cognition_v2 regressions, Stage 2 regressions, full branch suite, identical full-suite command on current `origin/main`, and `git diff --check`.

Valid terminal states:

- `WP02_ACCEPTED_CANDIDATE` only when the real 120-case pilot and real >=1,500-case corpus pass every gate;
- `WP02_SOURCE_FEASIBILITY_BLOCKED` when a family cannot obtain qualifying public evidence;
- `WP02_DATA_QUALITY_BLOCKED` when real records cannot meet integrity/outcome gates;
- `LOCAL_STATE_REVIEW_REQUIRED` for unsafe local state.

Push only this branch, update only PR #30 and Issue #29, and do not merge.

The receipt must include exact final Head, raw snapshot counts, source-native-ID coverage, placeholder violations, real pilot/final distributions, split distribution, all integrity counts, outcome/provenance coverage, two independent rebuild hashes, test results, and blockers.
