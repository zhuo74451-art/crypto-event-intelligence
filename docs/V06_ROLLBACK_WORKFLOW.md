# v0.6 Rollback Workflow

Last updated: 2026-05-27

This workflow keeps AI-first labeling reversible. It is required before building any TG draft workflow.

## What Can Be Rolled Back

| artifact | rollback source |
|---|---|
| low-risk released rows | `data/v06_manual_review_released_rows.csv` |
| macro holdout rows | `data/v06_macro_holdout_queue.csv` |
| macro discard released rows | `data/v06_macro_discard_released_rows.csv` |
| holdout sample | `data/v06_holdout_audit_sample.csv` |
| synthetic edge cases | `data/v06_synthetic_edge_cases.csv` |

## Rollback Triggers

Rollback or pause the related rule if any of these occur:

- UTC conversion error is found.
- More than 2 false asset attributions per 100 audited rows.
- Low-risk discard produces more than 1 false negative in a week.
- Event taxonomy disagreement exceeds 5% in audit.
- `manual_review_required_rate` rises above 0.085 after a new batch.
- `secret_leak_count` is greater than 0 in `results/secret_leak_summary.csv`.
- A released row would have been an `approve_publish` item after review.
- A macro/multi-asset row was incorrectly converted into a single-asset alert.

## Rollback Steps

1. Stop applying the suspected release or auto-label rule.
2. Find the released rows in the relevant audit CSV.
3. Restore these fields in `data/v06_manual_label_sheet.csv`:

```text
manual_review_required=true
review_queue=
label_origin=rollback_required
manual_notes=<previous notes> | rollback:<reason>
```

4. Re-run:

```powershell
python scripts/check_secret_leaks.py
python scripts/audit_v06_manual_review_required.py
python scripts/build_v06_holdout_audit_sample.py --size 201
python scripts/check_v06_tg_pilot_gate.py
python scripts/refresh_project_state.py
python scripts/render_project_dashboard.py
```

5. Record the reason in `docs/DECISIONS.md` if the rollback changes policy.

## Current Non-Negotiables

- `auto_publish` remains disabled.
- No auto-send to Telegram.
- No trading advice.
- No order execution.
- TG work, when allowed, is draft-only formatting and routing.

## Preferred Fix Order

1. Fix time/source parsing first.
2. Fix asset/entity attribution second.
3. Fix taxonomy third.
4. Adjust channel routing last.

Routing changes are last because they directly affect what a user would see.
