# Run-History Parent-Child Link — R02

## Problem

The bounded shadow runner (R01) inserts a child wrapper row into `run_history`
for each callable invocation.  However, when the injected one-shot callable
*already writes its own row* (as Integration will do), two `INSERT` statements
target the same `child_run_id`, causing a UNIQUE constraint violation:

```
UNIQUE constraint failed: run_history.run_id
```

## Solution

Two complementary changes:

1. **Schema v2** — adds `parent_run_id`, `run_ordinal`, and `run_kind` columns
   to `run_history` for formal parent-child linking.
2. **`child_history_mode`** — a new `BoundedShadowConfig` field that selects
   between two persistence strategies.

---

## `child_history_mode` — Insert vs Link-Existing

### `insert` (default)

- Bounded shadow writes a child wrapper row into `run_history` with
  `parent_run_id`, `run_ordinal`, and `run_kind='shadow_child'`.
- Suitable for fake callables, test callables, or any callable that does not
  persist its own run record.
- This was the R01 behaviour.

### `link_existing`

- The callable has already written its own row into the same `run_history` DB.
- Bounded shadow calls `link_existing_run_to_parent()` which **updates** the
  existing row with `parent_run_id`, `run_ordinal`, and `run_kind='shadow_child'`.
- No duplicate row, no UNIQUE collision, no `INSERT OR IGNORE`.
- Suitable for Integration one-shot callables.

---

## Schema v2 Migration

```
v1 → v2:  ALTER TABLE run_history ADD COLUMN parent_run_id TEXT
          ALTER TABLE run_history ADD COLUMN run_ordinal INTEGER
          ALTER TABLE run_history ADD COLUMN run_kind TEXT DEFAULT 'standalone'
```

- **Non-destructive**: existing columns and data are untouched.
- **Idempotent**: repeated `initialize_sqlite` calls are safe.
- **Backward-compatible**: `insert_run()` still works with the same positional
  arguments; v2 columns are optional.
- **PRAGMA user_version = 2**.

### New columns

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `parent_run_id` | TEXT | NULL | Links child to parent shadow run |
| `run_ordinal` | INTEGER | NULL | Round number within parent (1-based) |
| `run_kind` | TEXT | `'standalone'` | `standalone`, `shadow_parent`, `shadow_child`, `shadow_wrapper` |

### New indexes

- `idx_run_history_parent` — on `parent_run_id`
- `idx_run_history_parent_ordinal` — UNIQUE on `(parent_run_id, run_ordinal)` WHERE `parent_run_id IS NOT NULL`
- `idx_run_history_kind` — on `run_kind`

---

## Parent-Child Query Methods

### `link_existing_run_to_parent(db_path, run_id, parent_run_id, run_ordinal, run_kind)`

Links an existing run record to a parent.  Rules:

1. `run_id` must already exist.
2. `parent_run_id` must already exist.
3. `run_ordinal` must be a positive integer.
4. Will not overwrite a different `parent_run_id`.
5. Will not overwrite a different `run_ordinal`.
6. Repeated calls are idempotent.
7. Different children cannot share the same `(parent_run_id, run_ordinal)`.
8. Does not modify `status`, `started_at`, `finished_at`, `summary`, or `error`.

### `list_child_runs(db_path, parent_run_id)`

Returns all child runs linked to `parent_run_id`, ordered by `run_ordinal` ASC.

---

## Failure Rules

Any persistence failure forces the child run to `status=failed` and the parent
to `status=failed`:

| Failure | Effect |
|---------|--------|
| child does not exist (link) | `ValueError` → `result.errors` → parent `failed` |
| parent does not exist (link) | `ValueError` → `result.errors` → parent `failed` |
| ordinal conflict | `ValueError` → `result.errors` → parent `failed` |
| SQLite UNIQUE constraint | `Exception` → `result.errors` → parent `failed` |
| `INSERT` error | `Exception` → `result.errors` → parent `failed` |

`completed` status is only possible when `result.errors == []` and
contains no persistence failures.

---

## Integration Onboarding (W1+)

When Integration is ready to use the bounded shadow with `link_existing`:

```python
from market_radar.operations.bounded_shadow import (
    BoundedShadowConfig,
    run_bounded_shadow,
)

config = BoundedShadowConfig(
    state_dir="/path/to/state",
    child_history_mode="link_existing",  # ← key change
)

result = run_bounded_shadow(config, my_integration_callable)
```

The Integration callable must:
1. Write its own run-history row using the `child_run_id` it returns.
2. Use the **same `run_history.db`** as the bounded shadow (shared `state_dir`).

The bounded shadow will then `link` the existing row instead of inserting
a duplicate.

---

## Known Limitations

- `link_existing` requires the callable and the shadow to share the same
  SQLite database file.
- Schema v2 migration is one-way (v1 → v2, no downgrade).
- The UNIQUE index `idx_run_history_parent_ordinal` only applies when
  `parent_run_id IS NOT NULL`, so standalone runs are unaffected.
