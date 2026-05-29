# Project Review Actions

Last updated: 2026-05-29 12:52:24 UTC+8

This queue turns dashboard `review` metrics into explicit next actions. It does not approve product-direction changes.

## Counts

| field | value |
|---|---:|
| open_actions | 12 |
| requires_claude_yes | 3 |
| can_do_locally_yes | 6 |

## Actions

| action_id | owner | value | next_step | evidence |
|---|---|---:|---|---|
| `review_project_os_validation_review_count` | project_os | 2 | Keep review items visible; do not treat Project OS validation review rows as blocking failures. | `results/project_os_validation_report.md` |
| `review_other_review_keep_review_count` | local_rules | 5 | Inspect the remaining keep_review rows from the other_review split and convert recurring patterns into explicit taxonomy/entity rules. | `results/v06_other_review_reason_summary.md` |
| `review_private_pilot_draft_count` | local_rules | 9 | Keep the first private-pilot queue intentionally small after prefilter tightening; expand only by adding higher-quality sources or eligible event types, not by relaxing noise filters. | `results/daily_private_pilot_report.md` |
| `review_stratified_selected_count` | claude_product | 37 | Decide whether to relax event_type caps or improve scarce event-type classification first. Do not change caps locally without direction approval. | `results/v043_stratified_selection_diagnostics.md` |
| `review_v043_selected_v06_discard_rows` | local_research | 14 | Treat v043 backtest as historical baseline and inspect discarded selected rows before using it as current evidence. | `results/v043_selection_vs_v06_relevance_audit.md` |
| `review_v043_selected_v06_discard_rate` | local_research | 0.3784 | Use v0.6-filtered preview rather than old v043 selection for any future clean backtest branch. | `results/v043_selection_vs_v06_relevance_audit.md` |
| `review_v043_safe_as_current_evidence` | local_research | no | Keep v043 labeled as historical_baseline_only until a v0.6-filtered clean sample is approved and backtested. | `results/v043_selection_vs_v06_relevance_audit.md` |
| `review_v06_preview_asset_high_risk` | local_rules_then_claude | 11 | Apply only obvious dictionary/rule fixes; route protocol exploit and multi-chain policy questions to Claude/product direction. | `results/v06_filtered_preview_asset_attribution_audit.md` |
| `review_ready_for_statistical_conclusions` | local_research_then_claude | no | Do not cite event-type performance as a product conclusion; use the readiness report to decide what local cleanup remains and what needs Claude/product approval. | `results/backtest_readiness_report.md` |
| `review_backtest_readiness_review_count` | local_research_then_claude | 5 | Reduce local data-quality review items where possible; route policy-level blockers to Claude/product direction. | `results/backtest_readiness_report.md` |
| `review_v06_entity_protocol_exploit_policy_rows` | claude_product | 5 | Define primary-asset policy for exploit rows that mix protocol, chain, minted asset, stolen asset, and returned asset. | `results/v06_entity_rule_review_packet.md` |
| `review_pending_claude_decision_items` | project_direction | 778 | Send docs/CLAUDE_NEXT_PROMPT.md, then convert accepted recommendations into docs/DECISIONS.md before implementation. | `docs/CLAUDE_DECISION_REVIEW.md` |
