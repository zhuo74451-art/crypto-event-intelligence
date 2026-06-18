# Personal-Use RC1 Status

## Current State

- Post-MVP business capabilities are merged.
- Curated Feed loopback configuration is merged.
- Telegram UTF-8 rendering and card hardening are merged.
- Whale alert-state work is merged, but the final RC1 integrator must verify actual main behavior for cooldown, delivery marking, and single-source-of-truth state.
- Server one-shot and Telegram staging delivery have already been demonstrated.

## Remaining Before RC1

1. Verify actual latest `main` alert-state behavior.
2. Remove any remaining JSON side-state if SQLite is intended as the only truth.
3. Ensure `mark_delivered` is called only after a successful Telegram send.
4. Add one small `publish-once` entry point.
5. Add a concise personal runbook with manual run, optional schedule, stop, status, and rollback.
6. Run a short server verification and record the final SHA, run ID, and Telegram message ID.

## Release Decision

RC1 is ready when the acceptance criteria in `docs/PERSONAL_USE_RC1_PLAN.md` pass on the server.

Do not block RC1 on Semgrep cloud setup, enterprise deployment packaging, dashboards, multi-user support, or broad refactors.
