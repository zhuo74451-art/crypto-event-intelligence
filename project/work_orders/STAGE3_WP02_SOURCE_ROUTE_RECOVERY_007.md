# Stage 3 WP-02 Source Route Recovery 007

Issue #29 · Draft PR #30 · Branch `feat/stage3-wp02-historical-data-factory`  
Reviewed Head: `17a947f6f219480d1489bc929615cfb03539d71b`

Continue the same branch and Draft PR. Preserve valid infrastructure, invalidate unsupported data claims, and do not begin WP-03.

## V00 — Safe synchronization

Fetch refs, check out the existing branch and fast-forward only. Stop for tracked local changes or unexplained untracked product files. No reset, clean, stash, rebase or new branch.

## V01 — Revoke the current 300-case QUALIFIED status

The current rows are not valid point-in-time cases because collection occurred in July 2026 while assessment/event times were set to 2024, and outcome records are absent.

Required:

- move all current rows to rejected/quarantined artifacts with exact reasons;
- do not count them as pilot or final cases;
- remove stale 1,500/PASS claims from all reports and the PR body;
- delete or prevent any code path that assigns arbitrary historical event/assessment times;
- no case with `availability_time > assessment_time` may be QUALIFIED;
- no case without required outcomes and resolvable provenance may be QUALIFIED.

## V02 — Separate historical availability from collection time

Do not backdate actual acquisition metadata.

Add explicit fields and rules for historical backfill:

- `collection_retrieved_at`: actual current acquisition time;
- `source_native_published_at` or accepted/effective timestamp from the official source;
- `historical_available_at`: allowed only when proven by an immutable/versioned official archive or independently timestamped archive;
- `historical_authority`: typed authority such as OFFICIAL_IMMUTABLE_ARCHIVE, OFFICIAL_VERSIONED_FEED, or ARCHIVE_SNAPSHOT;
- archive/source-native ID, URL, content hash, parser version and acquisition lineage.

Rules:

- live evidence availability remains based on actual first-seen/retrieval time;
- historical backfill may use `historical_available_at` only when the authority and immutable source record pass validation;
- actual collection time is always retained and never substituted with a historical value;
- assessment cutoff must be on or after the permitted historical availability time;
- missing historical authority means the record is INCOMPLETE for historical replay.

Update contracts, reports and mutation tests accordingly without silently weakening WP-01 leakage controls.

## V03 — Repair Macro routes

Implement and probe official public routes rather than the current broken RSS assumptions.

Required routes and fallbacks:

1. Federal Reserve official press-release RSS feeds discovered from the official feeds page;
2. Federal Reserve yearly press-release archive pages for 2021–2026;
3. BLS Public Data API for official published macro series, with source series IDs, period/year, API response hash and release-time authority when available;
4. Eurostat Statistics API as a public official fallback.

Requirements:

- preserve source-native title/series ID/date/URL;
- use bounded date windows and pagination;
- do not swallow failures as empty success;
- record HTTP status, request count, earliest/latest source timestamps and parsed item count;
- qualify only actual macro releases/observations with auditable availability time.

## V04 — Repair Technology routes

### NVD

- split requests into date windows no longer than 120 consecutive days;
- paginate with `startIndex` and `resultsPerPage` until `totalResults` is exhausted or the explicit budget is reached;
- use a conservative unauthenticated request cadence and retry/backoff;
- persist CVE ID, publication/modified timestamp, source identifier and response hash;
- return a real next token rather than always `None`.

### GitHub Global Advisories

- use the public global-advisories endpoint;
- filter by `published` date range;
- use `per_page=100` and cursor/Link pagination;
- respect unauthenticated rate limits through checkpoints and scheduled finite waits;
- persist GHSA ID, publication timestamp, URL and content hash;
- never classify a rate-limit response as source infeasibility.

At least one technology route must produce 20 real pilot-eligible cases.

## V05 — Add real Market-event evidence routes

OHLCV is an outcome source, not market-event evidence.

Implement official public event sources, starting with:

- Kraken official status incidents and scheduled-maintenance APIs;
- Coinbase official status incident history/API;
- additional official exchange status or announcement archives only when public, read-only and auditable.

Qualifying market events include exchange outages, degraded trading, API incidents, maintenance, listing/delisting or market-structure notices. Preserve incident/announcement ID, created/published time, update history, affected components/assets and official URL.

At least one market route must produce 20 real pilot-eligible cases.

## V06 — Repair case qualification and relevance

A source record is not automatically a crypto-market case.

Required deterministic qualification:

- source-derived event title and native ID;
- event-family classifier with rule/version evidence;
- crypto-market relevance or material affected-asset mapping;
- arbitrary SEC filings may not be alternated between regulatory and corporate;
- generic CVEs may not be assigned BTC/SPX without a supported relevance path;
- event time comes from the source record;
- no hash-only titles;
- one source record cannot be cloned across families;
- unresolved relevance becomes INCOMPLETE or QUARANTINED.

## V07 — Real outcomes and provenance

For every accepted case:

- acquire real public OHLCV observations for the mapped asset or documented benchmark;
- produce separate 1h, 6h, 24h, 3d and 7d records or an explicit missing reason;
- retain provider-native timestamps, instrument, prices and response hashes;
- all evidence/outcome references must resolve exactly once;
- 24h outcome coverage must be at least 95% before pilot acceptance;
- empty `outcome_refs` cannot qualify.

## V08 — Real split allocator

Build non-empty chronological BUILD/DEVELOPMENT/BLIND splits, approximately 60/20/20 by correction-chain root/event time.

Required:

- all three splits non-empty;
- identity and correction-chain integrity;
- BLIND exclusion from tuning inputs;
- immutable split version and boundaries;
- exact computed split distribution in the manifest and reports.

## V09 — Real six-family pilot

Build at least 120 real QUALIFIED cases, at least 20 per family, only after V03–V08 pass.

Pilot gates:

- six qualifying evidence routes proven;
- 20 real cases per family;
- real native IDs, URLs and source timestamps for 100%;
- historical authority and time completeness 100%;
- outcome/provenance coverage requirements pass;
- zero placeholders, arbitrary backdating, clones or generic count padding;
- future leakage 0;
- duplicates 0;
- cross-split identity/chain 0;
- BLIND contamination 0;
- non-empty 60/20/20-style splits;
- two independent rebuilds from persisted source snapshots have identical hashes.

If a family cannot reach 20 cases after the official fallbacks above, stop `WP02_SOURCE_FEASIBILITY_BLOCKED` with exact executed evidence. Do not scale.

## V10 — Scale only after the pilot

Only after the real pilot passes, scale to at least 1,500 real QUALIFIED cases under the existing WP-02 distribution and integrity gates. Do not synthesize or pad.

## V11 — Reports and verification

Rewrite and synchronize:

- `docs/stage3/WP02_SOURCE_FEASIBILITY.md`;
- `docs/stage3/WP02_DATA_FACTORY_REPORT.md`;
- `docs/stage3/WP02_CORPUS_AUDIT.md`;
- `docs/stage3/WP02_REJECTION_REPORT.md`;
- PR #30 body;
- Issue #29 receipt.

Reports must be generated from actual artifacts and clearly separate configured routes, executed probes, rejected records, pilot cases and final cases.

Run focused WP-02 tests, all cognition_v2 regressions, Stage 2 regressions, the full branch suite, the same command on current `origin/main`, and `git diff --check`.

Push only this branch, update only PR #30 and Issue #29, and do not merge.

Valid terminal states:

- `WP02_ACCEPTED_CANDIDATE` only after the real six-family pilot and real >=1,500-case corpus pass every gate;
- `WP02_SOURCE_FEASIBILITY_BLOCKED` only after all specified official routes/fallbacks were executed and one or more families remain infeasible;
- `WP02_DATA_QUALITY_BLOCKED` for real-data integrity/outcome failures;
- `LOCAL_STATE_REVIEW_REQUIRED` for unsafe local state.

Receipt must include exact final Head, invalidated-row count, historical-authority coverage, route probe evidence, pilot/final distributions, split distribution, outcome/provenance coverage, integrity violations, independent rebuild hashes, test results and blockers.
