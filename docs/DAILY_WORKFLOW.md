# Daily Workflow

## 0. Fast Path (Recommended)

For the local private-pilot MVP:

```powershell
python scripts/run_daily_private_pilot.py
```

This generates draft files, validates draft safety, summarizes draft feedback, classifies `other_review` reasons, and refreshes the Project Dashboard.
It now runs local candidate prefiltering before any optional AI review.

For AI-first review, set `OPENROUTER_API_KEY` only in the current terminal environment and run:

```powershell
python scripts/run_daily_private_pilot.py --ai-review
```

This uses Claude/OpenRouter to fill `reviewer_decision`, `reviewer_usefulness`, `reviewer_issue_type`, and `reviewer_notes`. It still does not call Telegram and does not auto-send.

Primary daily report:

```text
results/daily_private_pilot_report.md
results/tg_draft_rule_improvement_report.md
data/tg_drafts_v06_approved_pool.csv
results/tg_draft_approved_pool.md
```

Compact review packet:

```text
data/tg_draft_review_packet.csv
results/tg_draft_review_packet.md
```

After editing the packet, apply it back:

```powershell
python scripts/apply_tg_draft_review_packet.py --drafts data/tg_drafts_v06_private_pilot.csv --packet data/tg_draft_review_packet.csv --output data/tg_drafts_v06_private_pilot.csv
python scripts/summarize_tg_draft_feedback.py --input data/tg_drafts_v06_private_pilot.csv --summary results/tg_draft_feedback_summary.csv --markdown-output results/tg_draft_feedback_summary.md
python scripts/build_daily_private_pilot_report.py
```

For the v0.6 labeling cycle:

```powershell
python scripts/run_v06_labeling_cycle.py --sheet data/v06_manual_label_sheet.csv --batch-size 30 --review-required-quota 10 --min-confidence 0.90 --apply-provisional --provisional-min-confidence 0.75 --auto-verify-provisional --auto-verify-audit-size 20 --auto-close-low-risk --auto-close-audit-size 20 --auto-fill-unlabeled --auto-fill-unlabeled-audit-size 20
```

This command runs:

1. AI-assisted pre-label.
2. Conservative provisional auto-verify (with audit sample).
3. Conservative low-risk unlabeled auto-close (with audit sample).
4. Fill remaining unlabeled rows as review-required (with audit sample).
5. Label evaluation summary.
6. Next manual batch generation.
7. Review packet export.
8. Project state and dashboard refresh.

Review workflow:

```powershell
# 1) Edit packet file (manual fields only)
data/v06_manual_label_batch_review.csv

# 2) Apply edits back to master sheet
python scripts/apply_v06_review_packet.py --sheet data/v06_manual_label_sheet.csv --packet data/v06_manual_label_batch_review.csv --output data/v06_manual_label_sheet.csv
```

## 1. Refresh Candidates

```powershell
python scripts/run_v04_real_200_candidate_pipeline.py --raw-input data/raw_news_real_500_older.csv --mapping data/raw_news_column_mapping.json --limit 500 --normalized-output data/raw_news_real_500_older_normalized.csv --candidates-output data/event_candidates_real_500_older_review.csv --summary-prefix v043_older
```

## 2. Suggest Review Decisions

```powershell
python scripts/suggest_review_decisions.py --input data/event_candidates_real_500_older_review.csv --output data/event_candidates_real_500_older_review_suggested.csv --summary results/v043_older_review_suggestion_summary.csv
```

## 3. Filter Mature Candidates

```powershell
python scripts/filter_mature_candidates.py --input data/event_candidates_real_500_older_review_suggested.csv --output data/event_candidates_real_500_older_mature_review_suggested.csv --summary results/v043_older_mature_filter_summary.csv --min-age-hours 80
```

## 4. Build Stratified Review Sample

```powershell
python scripts/build_stratified_auto_review.py --input data/event_candidates_real_500_older_mature_review_suggested.csv --output data/event_candidates_real_500_older_mature_review_auto50.csv --summary results/v043_older_stratified_selection_summary.csv --limit 50
```

## 5. Run Mature Backtest

```powershell
python scripts/run_v043_older_mature50_backtest.py --review-input data/event_candidates_real_500_older_mature_review_auto50.csv --limit 50
```

## 6. Audit Time

```powershell
python scripts/audit_event_time_provenance.py --candidates data/event_candidates_real_500_older_review.csv --backfill results/v043_older_mature50_event_price_backfill.csv --output results/v043_time_provenance_report.csv --summary results/v043_time_provenance_summary.csv
```

## 7. Auto-Label (AI-Assisted) Before Manual Review

```powershell
python scripts/auto_label_v06_sheet.py --input data/v06_manual_label_sheet.csv --output data/v06_manual_label_sheet.csv --summary results/v06_auto_label_summary.csv --apply-high-confidence --min-confidence 0.90
```

## 8. Evaluate Labels

```powershell
python scripts/evaluate_manual_labels.py --input data/v06_manual_label_sheet.csv --summary results/v06_manual_label_eval_summary.csv --errors results/v06_manual_label_eval_errors.csv
```

## 9. Prepare Next Labeling Batch

```powershell
python scripts/prepare_labeling_batch.py --input data/v06_manual_label_sheet.csv --output data/v06_manual_label_batch.csv --summary results/v06_labeling_batch_summary.csv --batch-size 30
```

## 10. Refresh Project State

```powershell
python scripts/refresh_project_state.py
```

## 11. Render Project Dashboard

```powershell
python scripts/render_project_dashboard.py
```

## 12. Build Claude Manual-Reduction Prompt

```powershell
python scripts/build_claude_manual_reduction_prompt.py --sheet data/v06_manual_label_sheet.csv --eval-summary results/v06_manual_label_eval_summary.csv --output docs/CLAUDE_MANUAL_REDUCTION_PROMPT.md
```

Outputs:

```text
docs/PROJECT_DASHBOARD.md
results/project_dashboard_metrics.csv
docs/CLAUDE_MANUAL_REDUCTION_PROMPT.md
```

## v0.6 Strict Quality Gate

Run this after any labeling/routing rule change:

```powershell
python scripts/run_v06_quality_gate.py
```

This command regenerates synthetic edge cases, rebuilds the 201-row holdout audit sample, audits the remaining review queue, checks the strict TG draft pilot gate, and refreshes project state/dashboard.

Current strict gate:

```text
manual_review_required_rate <= 0.085
audit_sample_rows >= 200
synthetic_edge_cases >= 15
false_positive_rate <= 0.02
timezone_fail_count = 0
auto_publish_count = 0
```

Passing this gate does not allow auto-send. It only means draft-only TG formatting can be considered after direction approval.

## TG Draft Private Pilot

Generate local review drafts only:

```powershell
python scripts/generate_tg_drafts.py --input data/event_candidates_v06_clean_low_risk_preview.csv --output data/tg_drafts_v06_private_pilot.csv --markdown-output results/tg_drafts_v06_private_pilot.md --limit 20
```

Rules:

- This does not call Telegram.
- This does not auto-send.
- Every row defaults to `draft_status=pending_review`.
- Reviewers edit `reviewer_decision`, `reviewer_usefulness`, `reviewer_issue_type`, and `reviewer_notes` in the CSV.
- Do not use realized 24h/72h returns in the live-facing draft text.

Summarize local review feedback:

```powershell
python scripts/summarize_tg_draft_feedback.py --input data/tg_drafts_v06_private_pilot.csv --summary results/tg_draft_feedback_summary.csv --markdown-output results/tg_draft_feedback_summary.md
```

Validate draft safety:

```powershell
python scripts/validate_tg_drafts.py --input data/tg_drafts_v06_private_pilot.csv --output results/tg_draft_validation_report.csv --summary results/tg_draft_validation_summary.csv --markdown-output results/tg_draft_validation_report.md
```

Suggested review values:

- `reviewer_decision`: `approve`, `edit`, `reject`
- `reviewer_usefulness`: `useful`, `interesting`, `noise`
- `reviewer_issue_type`: `none`, `factual_issue`, `asset_issue`, `time_issue`, `tone_issue`, `not_price_relevant`
