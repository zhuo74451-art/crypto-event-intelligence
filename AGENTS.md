# Crypto Event Intelligence Agent Rules

## Project Direction

This project is a local crypto event intelligence and research pipeline.

It converts historical or real-time news into structured event candidates, audits time and price quality, filters low-value events, and prepares reviewed intelligence items.

## Hard Boundaries

- Do not connect Notion.
- Do not place trades.
- Do not generate buy/sell/long/short signals.
- Do not connect exchange order APIs.
- Do not build a web app unless explicitly requested.
- Keep the core workflow local: CSV, SQLite, Python scripts, and Markdown docs.
- Human-facing time is China time: `Asia/Shanghai`, `UTC+8`.
- Machine/API time is UTC: `*_utc` and Unix milliseconds.

## Working Style

- Keep project momentum high.
- If key information is missing and guessing would damage the architecture, stop and ask.
- If a better technical path is obvious, state it and take it.
- Prefer scripts and repeatable checks over manual one-off operations.
- Preserve outputs with versioned prefixes when changing major pipeline behavior.
- Use `docs/PROJECT_DASHBOARD.md` as the first human-readable status view before inspecting detailed code or CSVs.

## Required Validation

Before treating a result as usable:

- Time provenance audit must pass or warnings must be understood.
- Price source validation should have no mismatches in sampled rows.
- Backfill quality report should not contain unexplained `fail`.
- Review queues should be manually sampled before any publishing workflow.
- `auto_publish` remains disabled until manually labeled ground truth exists.

## Collaboration

- Codex implements and verifies.
- Cursor is optional and not required for project progress.
- Claude is consulted only for direction-level questions once enough unresolved questions accumulate.
- All cross-agent handoffs must be written to files under `docs/`.
- Project state should be refreshed with `python scripts/refresh_project_state.py`.
- Project dashboard should be rendered with `python scripts/render_project_dashboard.py`.
