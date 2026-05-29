# Validation Checklist

Run these before trusting results.

## Time

```powershell
python scripts/audit_event_time_provenance.py --candidates data/event_candidates_real_500_older_review.csv --backfill results/v043_older_mature50_event_price_backfill.csv --output results/v043_time_provenance_report.csv --summary results/v043_time_provenance_summary.csv
```

Required:

- `fail_count = 0`
- `price_kline_lag_out_of_range_count = 0`
- Any `source_lag_over_30m_count` must be reviewed.

## Price

```powershell
python scripts/validate_price_sources.py --sample-size 30 --output results/price_source_validation_report.csv --recent-output results/recent_price_point_sample.csv
```

Required:

- No `mismatch`.
- Request failures can be retried, but cannot be treated as validated prices.

## Backfill Quality

```powershell
python scripts/validate_backfill_results.py --input results/v043_older_mature50_event_price_backfill.csv --output results/v043_older_mature50_event_quality_report.csv
```

Required:

- `quality_status=fail` rows must be understood.
- `suspicious_extreme_return` rows must be manually reviewed.

## Review Quality

Required before TG:

- At least 200 labeled rows (AI prefill allowed, plus manual sampling).
- Clear false-positive categories.
- Clear false-negative categories.
- Clear wrong-asset examples.
- Clear wrong-time examples.

Evaluate manual labels:

```powershell
python scripts/auto_label_v06_sheet.py --input data/v06_manual_label_sheet.csv --output data/v06_manual_label_sheet.csv --summary results/v06_auto_label_summary.csv --apply-high-confidence --min-confidence 0.90 --apply-provisional --provisional-min-confidence 0.75
python scripts/auto_verify_v06_provisional_labels.py --input data/v06_manual_label_sheet.csv --output data/v06_manual_label_sheet.csv --summary results/v06_auto_verify_summary.csv --audit-output data/v06_auto_verify_audit_sample.csv --audit-size 20
python scripts/auto_close_low_risk_unlabeled.py --input data/v06_manual_label_sheet.csv --output data/v06_manual_label_sheet.csv --summary results/v06_auto_close_summary.csv --audit-output data/v06_auto_close_audit_sample.csv --audit-size 20
python scripts/auto_fill_unlabeled_review_required.py --input data/v06_manual_label_sheet.csv --output data/v06_manual_label_sheet.csv --summary results/v06_auto_fill_unlabeled_summary.csv --audit-output data/v06_auto_fill_unlabeled_audit_sample.csv --audit-size 20
python scripts/evaluate_manual_labels.py --input data/v06_manual_label_sheet.csv --summary results/v06_manual_label_eval_summary.csv --errors results/v06_manual_label_eval_errors.csv
python scripts/prepare_labeling_batch.py --input data/v06_manual_label_sheet.csv --output data/v06_manual_label_batch.csv --summary results/v06_labeling_batch_summary.csv --batch-size 30
python scripts/export_v06_review_packet.py --input data/v06_manual_label_batch.csv --output data/v06_manual_label_batch_review.csv
python scripts/apply_v06_review_packet.py --sheet data/v06_manual_label_sheet.csv --packet data/v06_manual_label_batch_review.csv --output data/v06_manual_label_sheet.csv
```

Required before TG:

- `labeled_rows >= 200`
- `false_positive_review_count` is understood and reduced.
- `false_negative_discard_count` is understood and reduced.
- Wrong asset/type/route patterns are converted into explicit rule or dictionary tasks.

## Publishing Safety

Required:

- `auto_publish` disabled.
- Draft generation only after manual approval.
- No buy/sell/long/short language.

TG draft pilot gate:

```powershell
python scripts/check_v06_tg_pilot_gate.py
```

Required:

- All rows in `results/v06_tg_pilot_gate_report.csv` have `status=pass`.
- Passing this gate allows draft generation only, not auto-send.

## Project OS

Check local environment:

```powershell
python scripts/check_local_environment.py
```

Run the consolidated project validation:

```powershell
python scripts/validate_project_os.py
```

Preferred full refresh:

```powershell
python scripts/run_v06_quality_gate.py
```

Required:

- `fail_count = 0` in `results/local_environment_summary.csv`.
- `requirements.txt` must exist and declare required packages.
- `blocking_or_fail_count = 0` in `results/project_os_validation_report.md`.
- `missing_script_count = 0` in `results/command_registry_summary.csv`.
- `unknown_rule_count = 0` in `results/project_review_action_summary.csv`.
- `missing_required_count = 0` in `results/artifact_manifest_summary.csv`.
- `stale_required_count = 0` in `results/artifact_manifest_summary.csv`.
- `review` items must remain visible and tracked; they are not completion proof.
- Hard boundary static scan must have zero findings.
- Key inputs checked by `validate_project_os.py` must be fresh within 24 hours by default.
- Accepted Claude decision review items must reference an existing `Dxxx` entry in `docs/DECISIONS.md`.
- `implementation_status=done` in the Claude decision review queue requires `decision_status=accepted`.
- `docs/PROJECT_DASHBOARD.md` must be rendered after `results/project_os_validation_summary.csv` is generated. `scripts/run_v06_quality_gate.py` handles this order.
