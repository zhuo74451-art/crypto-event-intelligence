# Stage 3 WP-02 Historical Qualification 008

Issue #29 · Draft PR #30 · Branch `feat/stage3-wp02-historical-data-factory`  
Reviewed Head: `d58a75330d0b2f4cdc8a1c4a3565fc1942aa7611`

Continue the same branch and Draft PR. Preserve valid source adapters and acquisition infrastructure. Do not begin WP-03.

## W00 — Safe synchronization

Fetch refs, check out the existing branch and fast-forward only. Stop for tracked local changes or unexplained untracked product files. No reset, clean, stash, rebase or new branch.

## W01 — Reclassify the 490 current records honestly

The current records are public-source intake records, not yet an accepted historical corpus.

Required:

- retain raw/source snapshots and acquisition lineage;
- mark each record INCOMPLETE or QUARANTINED unless it passes every historical authority, crypto relevance, outcome and split gate;
- do not count exchange OHLCV rows as macro events;
- do not count generic CVEs/KEVs or arbitrary SEC filings as crypto-market cases without source-derived relevance;
- remove `WP02_ACCEPTED_CANDIDATE`, 1,500/PASS and unsupported six-family claims from reports and PR/Issue receipts;
- generate all counts from canonical artifacts.

## W02 — Complete the historical availability model

Historical replay requires source-native event/publication time plus auditable historical availability while retaining actual 2026 collection time.

Every qualified record must contain:

- `collection_retrieved_at`: actual acquisition time;
- `source_native_published_at` and/or effective time;
- `historical_available_at`;
- typed `historical_authority`;
- immutable archive/source-native identifier and URL;
- response/content SHA-256;
- parser/adapter version and acquisition checkpoint lineage;
- explicit `assessment_time` at or after permitted historical availability and before all outcome windows.

Rules:

- never set event, publication or assessment time from current collection merely to make a row pass;
- never overwrite actual collection time;
- current-only records cannot satisfy a multi-year historical pilot;
- absence of immutable/versioned historical authority makes a record INCOMPLETE;
- future leakage is computed against `assessment_time`.

## W03 — Build six real crypto-relevant evidence routes

### Regulatory

Use official crypto-specific rules, enforcement actions, approvals, denials or policy releases from SEC, CFTC or equivalent authorities. Arbitrary company filings do not qualify as regulatory events.

### Corporate

Use official disclosures from crypto exchanges, miners, custodians, stablecoin issuers, ETF issuers or other materially crypto-exposed entities. Preserve issuer, filing type, filing date and crypto relevance evidence. Do not alternate arbitrary SEC rows between families.

### Macro

Use official macroeconomic releases and observations from working Federal Reserve, BLS and/or Eurostat routes. Exchange prices are outcomes/market observations and must never count as macro evidence.

### Technology

Use official advisories, releases or repository events with deterministic crypto relevance, such as affected blockchain clients, cryptographic libraries, wallets, exchanges, custody infrastructure or dependencies with documented exposure. Generic CVEs without relevance evidence are rejected.

### Market

Use official exchange incidents, outages, maintenance, listing/delisting or market-structure notices from Kraken, Coinbase or other approved official archives.

### Security

Use official incidents/advisories directly affecting crypto protocols, bridges, wallets, exchanges, custody or critical dependencies with documented crypto exposure. Generic CISA/NVD items do not qualify automatically.

For every route, record exact endpoint, historical range, request count, pagination, parsed native IDs, publication dates, failures and fallback results.

## W04 — Deterministic case qualification and relevance

A case counts only when code proves:

- source-derived title and native ID;
- one event family with rule/version evidence;
- crypto-market relevance and affected entity/asset evidence;
- source-native event/publication time;
- historical authority and permitted availability;
- stable event identity;
- no cloning across families;
- no hash-only titles or generic count padding;
- unresolved classification or relevance becomes INCOMPLETE/QUARANTINED.

Add mutation tests for arbitrary SEC alternation, generic CVE assignment, OHLCV-as-macro, cloned cross-family rows and unsupported asset mappings.

## W05 — Real outcome labels

For every qualified case, acquire actual public market observations for the mapped asset or documented benchmark.

Required intervals:

- 1h;
- 6h;
- 24h;
- 3d;
- 7d.

Each outcome must preserve provider, instrument, provider-native timestamps, prices, volume when available, retrieval time, source hash and missing-data reason.

Rules:

- outcome records remain separate from evidence inputs and hashes;
- empty `outcome_refs` cannot qualify;
- every outcome reference resolves exactly once;
- benchmark 24h coverage must be at least 95%;
- outcome structural violations must be zero.

## W06 — Repair the production auditor

Required changes:

- future leakage compares evidence availability to case `assessment_time`;
- missing outcome artifacts fail when qualified cases exist;
- all canonical artifacts are required;
- source, evidence, case and every outcome reference are resolved, not merely checked for field presence;
- 24h coverage >=95% and provenance coverage 100% are mandatory parts of `all_gates_pass`;
- historical authority, crypto relevance and placeholder/authenticity gates are mandatory;
- missing second rebuild fails;
- exact violating IDs and reasons are retained;
- grouped indexes replace all-pairs scans where practical.

Add mutation tests for every mandatory gate.

## W07 — Build real chronological splits

Create frozen chronological BUILD / DEVELOPMENT / BLIND splits, approximately 60/20/20, by correction-chain root/event time.

Required:

- all three splits non-empty;
- multiple historical dates/years represented;
- event identities and correction chains stay within one split;
- BLIND cases, identities, chains and outcomes cannot enter tuning inputs;
- immutable boundary/version records;
- exact split distribution in canonical manifests and reports.

## W08 — Real six-family historical pilot

Before scaling, build at least 120 real QUALIFIED historical cases, at least 20 per family.

Pilot gates:

- all six families >=20;
- evidence spans multiple dates and more than one year where official archives permit;
- source-native IDs/URLs/timestamps 100%;
- historical authority and critical-time completeness 100%;
- crypto relevance and asset mapping 100%;
- outcomes and provenance requirements pass;
- non-empty BUILD/DEVELOPMENT/BLIND splits;
- future leakage, duplicates, cross-split identities/chains and BLIND contamination all zero;
- zero synthetic, current-time substitution, arbitrary category assignment or count padding;
- two independent rebuilds from persisted raw snapshots produce identical artifact and root hashes.

If any family cannot reach 20 after documented official fallbacks, stop `WP02_SOURCE_FEASIBILITY_BLOCKED`. If real records cannot meet time, relevance, outcome or split gates, stop `WP02_DATA_QUALITY_BLOCKED`. Do not scale or claim acceptance.

## W09 — Scale only after pilot acceptance

Only after W08 passes, scale to at least 1,500 real QUALIFIED historical cases under the existing WP-02 family, regime, split, outcome, leakage and deterministic-rebuild requirements.

## W10 — Reports, tests and terminal receipt

Rewrite and synchronize:

- `docs/stage3/WP02_SOURCE_FEASIBILITY.md`;
- `docs/stage3/WP02_DATA_FACTORY_REPORT.md`;
- `docs/stage3/WP02_CORPUS_AUDIT.md`;
- `docs/stage3/WP02_REJECTION_REPORT.md`;
- PR #30 body;
- Issue #29 receipt.

Run focused WP-02 tests, all cognition_v2 regressions, Stage 2 regressions, full branch suite, the same full-suite command on current `origin/main`, and `git diff --check`.

Valid terminal states:

- `WP02_ACCEPTED_CANDIDATE` only after the real six-family historical pilot and real >=1,500-case corpus pass every gate;
- `WP02_SOURCE_FEASIBILITY_BLOCKED` only after the specified official routes and fallbacks have been executed;
- `WP02_DATA_QUALITY_BLOCKED` for historical authority, relevance, outcome, provenance or split failures;
- `LOCAL_STATE_REVIEW_REQUIRED` for unsafe local state.

Push only this branch, update only PR #30 and Issue #29, and do not merge or begin WP-03.

Receipt must include exact final Head, current-record reclassification counts, historical-authority coverage, six-family route evidence, real pilot and final distributions, date/year and split distributions, outcome/provenance coverage, all integrity violations, two independent rebuild hashes, test results and blockers.
