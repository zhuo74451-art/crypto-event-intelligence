import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_FILES = [
    "AGENTS.md",
    "docs/PROJECT_STATE.md",
    "docs/PROJECT_DASHBOARD.md",
    "docs/ACTIVE_GOALS.md",
    "docs/DECISIONS.md",
    "docs/CLAUDE_RESPONSE_INDEX.md",
    "docs/CLAUDE_DECISION_REVIEW.md",
    "docs/COMMAND_REGISTRY.md",
    "docs/ARTIFACT_MANIFEST.md",
    "docs/PROJECT_REVIEW_ACTIONS.md",
    "docs/VALIDATION_CHECKLIST.md",
    "docs/V06_REVIEW_FAILURE_MODES.md",
    "docs/V06_ROLLBACK_WORKFLOW.md",
    "docs/CURSOR_TASK_BACKLOG.md",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a paste-ready Cursor task prompt from local project state.")
    parser.add_argument("--output", default=str(ROOT / "docs" / "CURSOR_NEXT_PROMPT.md"))
    parser.add_argument("--copy", action="store_true", help="Copy generated prompt to Windows clipboard via clip.exe.")
    parser.add_argument("--open-cursor", action="store_true", help="Open the project folder in Cursor if cursor CLI exists.")
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def read_text(path: Path, limit_chars: int = 5000) -> str:
    if not path.exists():
        return f"(missing: {path})"
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) > limit_chars:
        return text[:limit_chars] + "\n\n...(truncated)"
    return text


def csv_summary(path: Path, group_column: str = "") -> str:
    if not path.exists():
        return f"- missing: {path.relative_to(ROOT)}"
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
    except Exception as exc:
        return f"- failed to read {path.relative_to(ROOT)}: {exc}"
    lines = [f"- {path.relative_to(ROOT)}: {len(df)} rows"]
    if group_column and group_column in df.columns:
        counts = df[group_column].value_counts().head(10)
        for name, count in counts.items():
            lines.append(f"  - {group_column}={name or '(blank)'}: {count}")
    return "\n".join(lines)


def build_prompt() -> str:
    context_sections = []
    for rel in DEFAULT_FILES:
        path = ROOT / rel
        context_sections.append(f"## {rel}\n\n```text\n{read_text(path)}\n```")

    data_snapshot = "\n".join(
        [
            csv_summary(ROOT / "data" / "event_candidates_v06_publish_review_queue.csv", "channel_route"),
            csv_summary(ROOT / "data" / "event_candidates_v06_other_review_queue.csv", "discard_reason"),
            csv_summary(ROOT / "data" / "event_candidates_v06_discard_audit_sample.csv", "discard_reason"),
            csv_summary(ROOT / "data" / "event_candidates_real_500_older_review.csv", "source_timezone_assumption"),
            csv_summary(ROOT / "results" / "v043_time_provenance_summary.csv"),
            csv_summary(ROOT / "results" / "v06_manual_label_eval_summary.csv"),
            csv_summary(ROOT / "results" / "v043_stratified_selection_diagnostics.csv", "cap_binding"),
            csv_summary(ROOT / "results" / "v043_stratified_selection_blocked_examples.csv", "candidate_event_type"),
            csv_summary(ROOT / "results" / "v043_selection_vs_v06_relevance_summary.csv"),
            csv_summary(ROOT / "results" / "v043_selection_vs_v06_discard_breakdown.csv", "primary_discard_reason"),
            csv_summary(ROOT / "results" / "v043_selection_vs_v06_event_type_impact.csv", "candidate_event_type"),
            csv_summary(ROOT / "results" / "v06_filtered_mature_sample_preview_summary.csv"),
            csv_summary(ROOT / "results" / "v06_filtered_preview_asset_attribution_summary.csv"),
            csv_summary(ROOT / "results" / "v06_clean_low_risk_preview_summary.csv"),
            csv_summary(ROOT / "results" / "backtest_readiness_summary.csv"),
            csv_summary(ROOT / "results" / "v06_asset_attribution_fix_plan_summary.csv", "recommended_action"),
            csv_summary(ROOT / "results" / "v06_entity_rule_review_packet_summary.csv", "entity_review_type"),
        ]
    )

    return f"""# Cursor Next Prompt

You are taking over one review cycle for Crypto Event Intelligence.

Workspace:

```text
{ROOT}
```

Hard rules:

- No Notion
- No trading integration
- No web app work
- No buy/sell/long/short advice
- Do not overwrite historical outputs
- Human review uses China-time fields (`*_china`)
- API/math uses UTC fields (`*_utc`)
- `auto_publish` must stay disabled

Read the project memory below, then execute the task checklist.

{chr(10).join(context_sections)}

## Data Snapshot

```text
{data_snapshot}
```

## Your Task

Run one v0.6 intake-quality review pass. Prefer concrete rule or dictionary improvements over open-ended manual labeling:

1. Find rows in `data/event_candidates_v06_publish_review_queue.csv` that still should not be publish candidates (opinion/analysis, generic price recap, footer noise, weak trading relevance).
2. Review rows with blank `primary_asset_symbol`: decide between `market_wide + human_review` vs `discard`.
3. Review `unsupported_research` rows (especially HYPE/ONDO/WLD): not backtestable on Binance but potentially research-worthy.
4. Check Curvance/Echo/eBTC-like `hack_security/protocol_incident` classification quality and whether a dedicated L1 type is needed.
5. Review `source_timezone_assumption=default_china` rows and decide whether to add entries in `data/source_timezone_rules.csv`.
6. Decide whether miner equities, AI data-center stories, enforcement/fraud news, and Polymarket stories belong in the main publish stream.
7. Read `results/v043_stratified_selection_diagnostics.md`; do not relax macro/other caps unless you can justify it as a product decision.
8. Inspect `results/v043_stratified_selection_blocked_examples.csv` for scarce event-type false positives and missing-symbol cases.
9. Read `results/v043_selection_vs_v06_relevance_audit.md`; treat v043 backtest as historical baseline if selected rows are now discarded by v0.6 relevance scoring.
10. Read `results/v043_selection_vs_v06_discard_breakdown.csv` and `results/v043_selection_vs_v06_event_type_impact.csv`; do not cite v043 event-type performance without this caveat.
11. Read `results/v06_filtered_mature_sample_preview.md`; evaluate whether this preview is a safer basis for a future v0.6-filtered backtest branch.
12. Read `results/v06_filtered_preview_asset_attribution_audit.md`; identify asset attribution fixes needed before a clean backtest branch.
13. Read `results/v06_clean_low_risk_preview.md`; treat it as a sanity-check subset only, not a statistical backtest sample.
14. Read `results/backtest_readiness_report.md`; do not cite event-type performance as a product conclusion while readiness is `not_ready`.
15. Read `results/v06_asset_attribution_fix_plan.md`; focus on rule/dictionary changes that reduce false BTC/ETH attribution without forcing unsupported assets into Binance backtests.
16. Read `results/v06_entity_rule_review_packet.md`; focus on protocol exploit primary-asset policy, unsupported HYPE/Hyperliquid attribution, and multi-chain regulatory flow without forcing Binance symbols.

Output requirements:

- Include `candidate_id`
- Explain issue cause
- Propose rule/dictionary/script changes
- If editing files, keep changes minimal and list verification commands
- Do not touch TG automation
- Do not provide trading advice
- Do not overwrite historical results
"""


def copy_to_clipboard(text: str) -> None:
    subprocess.run("clip", input=text, text=True, check=True)


def open_cursor() -> None:
    try:
        subprocess.Popen(["cursor", str(ROOT)])
    except Exception as exc:
        print(f"failed to open Cursor: {exc}")


def main() -> int:
    args = parse_args()
    output_path = normalize_path(args.output)
    prompt = build_prompt()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(prompt, encoding="utf-8")
    print(f"wrote Cursor prompt to {output_path}")
    if args.copy:
        copy_to_clipboard(prompt)
        print("copied Cursor prompt to clipboard")
    if args.open_cursor:
        open_cursor()
        print("opened project folder in Cursor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
