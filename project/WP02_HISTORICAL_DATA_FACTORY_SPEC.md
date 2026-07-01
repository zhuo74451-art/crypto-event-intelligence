# WP-02 Historical Evidence and Point-in-Time Data Factory

**Status:** Active specification  
**Delivery target:** reproducible historical corpus and data factory for later replay and blind evaluation

## Purpose

Build a deterministic, auditable historical dataset that can test whether the future cognition system improves judgment without using future information.

WP-02 is a data-engineering and evidence-integrity package. It does not run semantic cognition, tune prompts, score trading performance, or start live Shadow.

## Corpus target

Produce at least **1,500 qualified historical cases** covering:

- regulatory;
- corporate;
- macro;
- technology;
- market;
- security.

Coverage must span multiple regimes and include at least:

- bull;
- bear;
- ranging;
- high volatility;
- crisis;
- recovery.

Unknown labels may exist during intake but may not dominate the accepted corpus.

## Historical range

Default collection window:

```text
2021-01-01 through 2026-06-30 UTC
```

Older cases may be included when they materially improve regime or event-family coverage.

## Source policy

Use only public, read-only and legally accessible sources that require no paid API, private credential, login bypass or access-control circumvention.

Preferred source classes:

- official regulator and government releases;
- official company, protocol and exchange notices;
- public security advisories and incident disclosures;
- public macroeconomic releases;
- approved public market-data endpoints;
- existing read-only repository providers that pass provenance and permission review.

Do not store full copyrighted articles. Store source metadata, permitted short evidence excerpts or normalized fact records, timestamps, URLs and content hashes.

## Canonical artifacts

The accepted corpus must be reproducible from versioned text artifacts:

```text
data/historical_v1/
  source_registry.yaml
  cases.jsonl
  evidence.jsonl
  correction_chains.jsonl
  outcome_windows.jsonl
  split_manifest.json
  build_manifest.json
  corpus_report.md
  quality_report.json
```

A generated SQLite database may be produced locally for validation and replay, but the text artifacts are the canonical rebuild source.

## Case requirements

Every qualified case must include:

- deterministic case ID;
- event family;
- event identity ID;
- correction-chain identity when applicable;
- source and provenance references;
- publication, effective, first-seen, retrieval and assessment times where applicable;
- explicit source authority and fact permission;
- affected asset or benchmark mapping;
- market-regime label with rule/version evidence;
- BUILD, DEVELOPMENT or BLIND split;
- immutable evidence-manifest hash;
- correction, retraction, contradiction or supersession relationships;
- outcome windows at 1h, 6h, 24h, 3d and 7d;
- exact build and validator versions.

## Point-in-time rule

Evidence may be available to a case assessment only when the permitted availability time is at or before the assessment cutoff.

At minimum:

```text
availability_time = max(first_seen_at, retrieval_time)
```

Publication or effective time alone cannot make later-retrieved information available earlier.

Corrections, retractions and contradictions first observed after the cutoff remain future information for the earlier case.

## Outcome separation

Outcome data is label data, not cognition input.

- outcome records must be stored separately from evidence inputs;
- outcome fields must not affect the input manifest hash;
- BLIND outcome data must not enter BUILD or DEVELOPMENT tuning paths;
- every outcome observation must record provider, instrument, interval, retrieval time and hash;
- missing outcome data must remain explicit rather than silently imputed.

## Split policy

Use frozen chronological boundaries by correction-chain root time.

Target distribution:

- BUILD: approximately 60%;
- DEVELOPMENT: approximately 20%;
- BLIND: approximately 20%.

The final allocation may vary slightly to preserve event and correction-chain integrity.

Rules:

- one case cannot occur in multiple splits;
- one event identity cannot cross splits;
- one correction chain cannot cross splits;
- BLIND case, identity, chain or outcome data cannot enter tuning input;
- adding newer data cannot retroactively move a frozen BLIND case;
- split boundaries and allocation versions are immutable after acceptance.

## Quality gates

The package exits only when all mandatory gates pass:

- at least 1,500 qualified cases;
- all six event families represented with no family below 150 cases unless a documented source-feasibility decision is accepted;
- multiple regimes represented, with exact distribution reported;
- critical point-in-time fields complete for 100% of accepted cases;
- source authority and fact permission complete for 100%;
- future-evidence leakage violations: 0;
- cross-split event identities: 0;
- cross-split correction chains: 0;
- BLIND tuning contamination: 0;
- duplicate accepted case IDs: 0;
- outcome-window structural violations: 0;
- deterministic rebuild produces identical canonical hashes twice;
- every accepted case has an audit trail from source registry through evidence and outcomes;
- all generated reports agree with the exact final remote Head.

## Source and data-quality classifications

Each intake record must end in one of:

- QUALIFIED;
- INCOMPLETE;
- DUPLICATE;
- LEAKED;
- UNAUTHORIZED_SOURCE;
- IDENTITY_UNRESOLVED;
- OUTCOME_UNAVAILABLE;
- QUARANTINED.

Only QUALIFIED records count toward the 1,500-case target.

## Engineering components

Add production modules under:

```text
market_radar/cognition_v2/data_factory/
```

Expected responsibilities:

- source registry;
- finite acquisition adapters;
- normalization;
- source and evidence hashing;
- event identity and correction-chain assembly;
- point-in-time availability validation;
- asset and benchmark mapping;
- market-regime labeling;
- outcome-window acquisition;
- frozen split allocation;
- canonical JSONL writing;
- SQLite materialization;
- rebuild verification;
- quality audit and operator commands.

## Runtime policy

- finite commands only;
- no daemon, cron, login item or hidden loop;
- every acquisition run has explicit source, range, limit, checkpoint and stop behavior;
- interrupted runs resume from durable checkpoints;
- no paid API or real model call;
- no public posting or external write effect beyond ordinary source reads;
- large acquisition runs must produce progress and cost reports without requiring routine owner supervision.

## Required reports

- source feasibility and permission register;
- corpus distribution report;
- point-in-time integrity report;
- duplicate and correction-chain report;
- outcome coverage report;
- deterministic rebuild report;
- rejected/quarantined-record report;
- exact test and command receipt.

## Exit boundary

WP-02 proves that the project has a reproducible and auditable historical evidence substrate. It does not prove cognition quality. WP-03 begins only after the corpus, split and leakage guarantees are independently accepted and merged.
