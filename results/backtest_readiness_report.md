# Backtest Readiness Report

Last updated: 2026-05-29 12:52:21 UTC+8

overall_conclusion_status: not_ready
review_count: 5
local_review_count: 3
claude_review_count: 1
mixed_local_claude_review_count: 1
pass_count: 3

## Interpretation

- `ready_for_statistical_conclusions=no` means do not cite event-type performance as a product conclusion.
- `v043` remains a historical baseline because current v0.6 relevance scoring discards some selected rows.
- `v06_low_risk` is a pipeline sanity-check branch only; its sample is intentionally small.

| area | check | actual | required | status | owner | blocker_type | next_action |
|---|---|---:|---|---|---|---|---|
| v043 | historical_sample_current_evidence | no | yes | review | local_research | historical_baseline | Keep v043 out of current claims; use v0.6-filtered branches for future clean runs. |
| v043 | v06_discard_contamination | 14 | 0 | review | local_research | sample_contamination | Inspect discarded v043 rows only as historical contamination evidence. |
| v06_preview | filtered_preview_selected_count | 50 | 50 desired | pass | local_research | sample_size | Use this preview for planning after attribution cleanup, not as conclusion evidence. |
| v06_preview | asset_high_risk_rows | 11 | 0 before clean backtest | review | local_rules_then_claude | asset_attribution | Apply obvious dictionary/symbol fixes locally; send policy rows to Claude/product. |
| v06_preview | protocol_policy_rows | 5 | 0 unresolved policy rows | review | claude_product | policy_decision | Ask Claude/product for protocol exploit and multi-chain attribution policy. |
| v06_low_risk | low_risk_preview_rows | 22 | >=50 for real sample, current is sanity-check | review | local_research | sample_size | Use as sanity-check only; grow clean sample after attribution policy is settled. |
| v06_low_risk | low_risk_backfill_ok_rows | 22 | matches low-risk preview rows | pass | local_research | pipeline_health | Keep as green sanity-check evidence. |
| v06_low_risk | low_risk_quality_pass_rows | 22 | matches low-risk preview rows | pass | local_research | pipeline_health | Keep as green quality evidence. |
