import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a focused Claude prompt for reducing manual workload in v0.6 intake.")
    parser.add_argument("--sheet", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--eval-summary", default=str(ROOT / "results" / "v06_manual_label_eval_summary.csv"))
    parser.add_argument("--output", default=str(ROOT / "docs" / "CLAUDE_MANUAL_REDUCTION_PROMPT.md"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def read_first_row(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
        return df.iloc[0].to_dict() if not df.empty else {}
    except Exception:
        return {}


def manual_review_required_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
        if "manual_review_required" not in df.columns:
            return 0
        return int(df["manual_review_required"].astype(str).str.lower().eq("true").sum())
    except Exception:
        return 0


def build_prompt(eval_summary: dict, manual_review_required: int) -> str:
    labeled = eval_summary.get("labeled_rows", "unknown")
    unlabeled = eval_summary.get("unlabeled_rows", "unknown")
    coverage = eval_summary.get("label_coverage_pct", "unknown")
    return f"""# Claude Manual Reduction Prompt

You are acting as a strict Web3-native AI PM/architect.
Do not be polite or generic. Give concrete decisions.

Project: Crypto Event Intelligence (local CSV/SQLite/Python only)

Current state snapshot:
- labeled_rows: {labeled}
- unlabeled_rows: {unlabeled}
- label_coverage_pct: {coverage}
- manual_review_required_rows: {manual_review_required}
- auto_publish: disabled

Hard boundaries:
- No Notion
- No trading integration
- No web app
- No buy/sell/long/short advice

Core question:
We want a Web3-aware AI system, not a human-heavy pipeline.
For each manual-heavy step, decide whether it should remain manual or be automated by AI.

Please output:
1. A hard yes/no decision table for these steps:
   - candidate classification
   - asset attribution
   - event taxonomy
   - timezone/source normalization checks
   - low-risk discard confirmation
   - publish-review approval
2. For each step marked "AI", define:
   - minimum confidence rule
   - mandatory audit sample size
   - rollback trigger
3. A 2-phase migration plan from manual-heavy to AI-heavy:
   - Phase A (this week)
   - Phase B (next 2-4 weeks)
4. The top 5 failure modes specific to Web3 news/event intelligence.
5. The exact gate to allow first TG draft pilot without reintroducing heavy manual review.
"""


def main() -> int:
    args = parse_args()
    sheet_path = normalize_path(args.sheet)
    eval_path = normalize_path(args.eval_summary)
    output_path = normalize_path(args.output)

    summary = read_first_row(eval_path)
    manual_review_required = manual_review_required_count(sheet_path)
    prompt = build_prompt(summary, manual_review_required)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(prompt, encoding="utf-8")
    print(f"wrote manual-reduction Claude prompt to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
