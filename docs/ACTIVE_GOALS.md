# Active Goals

## Goal 1: Project OS

Status: active

Objective:

Create a local file-based working memory and handoff system so Codex can continue the project without losing context, and Claude can be consulted when question backlog reaches threshold.

Acceptance:

- `AGENTS.md` exists.
- `docs/PROJECT_STATE.md` exists.
- `docs/ACTIVE_GOALS.md` exists.
- `docs/DECISIONS.md` exists.
- `docs/VALIDATION_CHECKLIST.md` exists.
- `docs/DAILY_WORKFLOW.md` exists.
- `scripts/render_project_dashboard.py` generates a readable status dashboard.

## Goal 2: Event Intake Ground Truth

Status: active

Objective:

Create and maintain an AI-first labeled dataset for v0.6 review quality with audit gates instead of heavy manual labeling.

Acceptance:

- `data/v06_manual_label_sheet.csv` exists.
- Labeled rows reach at least 200.
- AI-owned labels have audit samples and rollback gates.
- `scripts/check_v06_tg_pilot_gate.py` can decide whether TG draft pilot is allowed.

## Goal 3: TG Draft System

Status: active

Boundary:

Draft-only local files are allowed. Telegram API calls and auto-send remain disabled.

Objective:

Generate TG message drafts for approved intelligence events, but do not auto-send.

Acceptance:

- Only reviewed or low-risk pilot events can generate drafts.
- Drafts include factual summary, affected asset, route, confidence, time, source, and risk note.
- No buy/sell/long/short language.
- Drafts are written to local CSV/Markdown and default to `pending_review`.
