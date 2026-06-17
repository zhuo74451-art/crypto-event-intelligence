# Operations Foundation — Architecture

## Purpose

The `market_radar/operations/` package provides generic internal-run infrastructure
decoupled from all business lanes (Signal Spine, Event Intelligence, Whale Tracking, etc.).

## Design Principles

1. **Zero business coupling.** Operations imports only stdlib and its own modules.
   No imports from `market_radar/shared/`.
2. **No network access.** All operations are local-only.
3. **No daemon or background processes.** Operations runs on demand.
4. **No credentials, keys, or secrets.**
5. **No trading language or concepts.**
6. **Atomicity by default.** All writes use temp-file-then-rename.

## Module Map

| Module | Responsibility |
|---|---|
| `runner_protocol.py` | Generic RunnerProtocol and InjectedRunner |
| `run_once.py` | Single-execution wrapper |
| `config_validator.py` | Dict-based config validation |
| `file_lock.py` | PID-file single-instance lock with stale detection |
| `sqlite_schema.py` | SQLite schema initialization and migration |
| `run_history.py` | Run record persistence |
| `source_health.py` | Source health check history |
| `snapshot_index.py` | Snapshot metadata index |
| `alert_index.py` | Alert candidate index |
| `status_cmd.py` | Operations subsystem status |
| `shadow_run.py` | Bounded shadow execution with stop marker support |
| `stop_marker.py` | File-based graceful termination |
| `atomic_json.py` | Atomic JSON artifact writer |
| `recovery.py` | Interrupted-run detection and recovery state |
| `rollback.py` | Documented rollback procedure (read-only) |
| `scheduler_config.py` | APScheduler configuration model (disabled by default) |

## Data Flow

```
Caller
  ↓
run_once(runner)
  → RunnerProtocol.run(context)
      ↕ Operation-specific logic
  → RunResult
  ↓
run_history.insert_run()  (SQLite)
  ↓
atomic_json (optional artifact)
```

## Scheduler

APScheduler is optional. The `scheduler_config.py` module:
- Defaults to `enabled=False`
- Requires exact pinned version `3.10.4`
- Enforces `max_instances=1`, `coalesce=True`
- No scheduler process is ever started by the package itself
