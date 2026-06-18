# Extension C: Operator Recovery Runbook

This runbook covers common failure scenarios and their resolution steps.

## DB locked

```bash
# Check if another process holds the lock
lsof ops.db          # Linux
Handle64.exe ops.db  # Windows (Sysinternals)

# Wait for the lock to clear, or:
kill <pid>           # If the holder is stuck
```

## Schema mismatch

1. Run `initialize_sqlite()` — it handles v1→v2 migration.
2. If manual: `PRAGMA user_version = <expected_version>`
3. Verify: `PRAGMA user_version`

## Corrupt cursor (summary_json)

1. Identify corrupt records via Doctor:
   ```bash
   python -c "from market_radar.operations.doctor import run_doctor; ...
   ```
2. Manually review and correct the JSON field.
3. Always backup before modifying.

## Missing artifact

1. Locate the artifact in the audit bundle.
2. If missing from state_dir, restore from the latest backup.
3. If missing from backup, reconstruct from run-history data.

## Incomplete parent (children missing or orphaned)

1. Run Doctor to identify the issue:
   ```
   check_id: orphanychildren / parent_child:count_*
   ```
2. Use the Recovery Plan to generate proposed actions.
3. Manually re-insert or re-link after approval.

## Failed bundle verification

1. Re-export from the source state_dir.
2. Compare `SHA256SUMS` with the failed bundle.
3. Determine which file was tampered or corrupted.
4. Restore from backup if needed.
