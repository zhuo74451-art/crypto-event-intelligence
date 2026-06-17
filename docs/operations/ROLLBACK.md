# Operations Foundation — Rollback Procedure

## When to Rollback

- Schema migration introduced a bug affecting run history.
- File lock mechanism prevents legitimate operations from starting.
- Shadow run produces unexpected results due to ops config error.

## Rollback Steps

| Step | Action | Risk | Reversible |
|------|--------|------|------------|
| 1 | `touch STOP_MARKER` to stop running operations | low | yes |
| 2 | `cp ops.db ops.db.pre_rollback` — backup DB | low | yes |
| 3 | Drop ops tables: run_history, source_health, snapshot_metadata, alert_candidates | high | no |
| 4 | `git revert <ops-commit>` | medium | yes |
| 5 | Run `python -m pytest tests/ -q --tb=line` | low | yes |

## No Business Impact

Rolling back operations has zero impact on:
- `market_radar/shared/` — business pipeline code
- Signal Spine event processing
- Price backfill data
- Research dataset files
