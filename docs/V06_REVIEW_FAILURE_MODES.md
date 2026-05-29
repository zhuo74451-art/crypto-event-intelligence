# v0.6 Review Failure Modes

Last updated: 2026-05-27

This file records why rows still require review after AI-first labeling. It is used to improve rules without turning the project back into a manual labeling workflow.

## Current Summary

Source files:

- `data/v06_manual_review_required_audit.csv`
- `results/v06_manual_review_required_report.md`
- `data/v06_synthetic_edge_cases.csv`

Current strict gate:

```text
manual_review_required_rows: 13
manual_review_required_rate: 0.0647
target_rate: <= 0.085
```

## Failure Modes

| mode | current meaning | handling |
|---|---|---|
| asset_missing | The event may matter, but no reliable primary asset was found. | Keep in review or route to macro/research holdout. Do not force a fake asset. |
| scope_ambiguous | The event may affect several assets or the full market. | Avoid single-asset TG drafts unless a clear primary asset exists. |
| low_ai_confidence | Confidence is below the publish-review floor. | Keep in review, improve rules, or discard if clearly non-actionable. |
| route_research_only | Useful context, but not a direct fast-alert item. | Keep as research material; do not push into TG draft flow by default. |
| route_macro_policy | Macro/regulatory event that needs separate treatment. | Route through macro policy; do not attribute to one coin unless explicit. |
| auto_provisional_needs_audit | AI found a likely label but not enough certainty for final routing. | Use audit sample and synthetic cases to improve rules. |
| medium_confidence_review | Model/rule confidence is medium and needs a second pass. | Keep in review or improve entity/taxonomy dictionary. |

## Examples Still Requiring Caution

- Market-wide liquidation headlines with no primary asset.
- ZachXBT or security items where the target asset/protocol is not clear.
- RWA/stablecoin growth metrics without a tradable primary asset.
- Tokenized stock/regulatory headlines where crypto asset attribution is weak.
- Payment adoption/product-card announcements that may be long-term relevant but not alert-worthy.

## Rules Not To Add Yet

- Do not map all macro or regulatory news to BTC by default.
- Do not convert every RWA or stablecoin metric into an alpha candidate.
- Do not publish market-wide liquidation or broad TVL metrics as single-asset alerts.
- Do not treat unsupported assets as irrelevant; route them to `unsupported_research`.
- Do not release `approve_publish` rows from review just to improve a gate metric.

## Regression Cases

Synthetic edge cases live in:

```text
data/v06_synthetic_edge_cases.csv
```

They cover:

- macro without asset
- explicit ETH regulatory event
- unsupported but relevant HYPE event
- soft hack/security language
- generic price recap
- product announcement noise
- legal enforcement macro
- network upgrade
- stablecoin mint/flow
- scraped footer noise
- token unlock
- non-crypto noise
- institutional BTC flow
- multi-asset macro
- hack with unknown asset

Any future labeling rule change should be checked against these cases before TG draft work resumes.
