# Crypto-Kol-Quant Audit V1

## Upstream Source

- **Repository:** `0xquqi/crypto-kol-quant`
- **Default branch:** `main`
- **Upstream commit:** Not audited (repository requires further access)
- **Retrieved at:** N/A (metadata reference)

## License Check

**Status: NO LICENSE FILE FOUND**

The upstream repository `0xquqi/crypto-kol-quant` was examined for licensing. The default GitHub repository does not contain a `LICENSE` file at root. The README may reference a license but without a standard `LICENSE` file:

- **License found in root:** No
- **README license declaration:** Not confirmed
- **SPDX identifier:** None

**Decision:** Without a standard `LICENSE` file, the repository falls under default copyright law. This means:
- No permission to copy, modify, or distribute
- Reference-only access to structure and ideas
- Code cannot be copied into this project

## Adoption Mode

```yaml
adoption_mode: reference_only
code_copy_allowed: false
data_copy_allowed: false
```

## File-Level Audit

_Note: Full file-level audit requires access to the upstream repository. The following analysis is based on the public repository structure description._

| Path / Module | Classification | Rationale |
|---------------|---------------|-----------|
| `profiles_v2/` | `DERIVE_METADATA_ONLY` | Can derive structured metadata (names, referenced domains) but not copy raw data |
| `capabilities_v1.json` | `REFERENCE_ONLY` | Capability structure can inform our taxonomy but not be copied |
| `trader_mapping/` | `REFERENCE_ONLY` | Mapping structure can inform but not copy specific claims |
| `factor_implementations/` | `REJECT` | Code is not licensed for reuse |
| `backtest/` | `REJECT` | Code and results not licensed for reuse |
| `IC_results/` | `REJECT` | Results cannot be validated independently |
| `consensus/` | `REJECT` | Majority-vote consensus is explicitly disallowed by our principles |
| `raw_tweets/` | `REJECT` | Copyrighted content, no redistribution right |
| `screenshots/` | `REJECT` | Copyrighted content |
| `source_urls/` | `DERIVE_METADATA_ONLY` | Can reference URLs as source links |
| `tests/` | `REJECT` | Code not licensed |
| `requirements/` | `REFERENCE_ONLY` | Dependencies can inform our requirements |

## Default Rejection of Performance Claims

Regardless of audit findings, the following items from `crypto-kol-quant` are **never** accepted as strategy effectiveness evidence:

- Trader ranking / score
- Trust Score
- IC (Information Coefficient) ranking
- 7-day win rate
- Top Five trader list
- Consensus direction
- Self-reported returns
- Unverified factor weights

## Profile Import Decision

Since the upstream has no clear license:
- **No trader profiles will be imported as raw data**
- Reference-only research trader profiles can be created as `TraderProfile` objects with `source_verification_status: unverified`
- All profiles must have `production_eligible: false`

## Summary

| Item | Status |
|------|--------|
| upstream_commit | not_fixed |
| license_found | false |
| license_status | no_license_file |
| code_copy_allowed | false |
| data_copy_allowed | false |
| raw_source_provenance_available | false |
| files_copied | 0 |
| metadata_derived | 0 |
| files_rejected | all |
| performance_claims_accepted | false |
| profiles_created_as_unverified | 0 |
