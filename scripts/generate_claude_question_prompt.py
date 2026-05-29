import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THRESHOLD = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Claude consultation prompt when the open-question backlog reaches threshold."
    )
    parser.add_argument("--backlog", default=str(ROOT / "docs" / "CLAUDE_QUESTION_BACKLOG.md"))
    parser.add_argument("--output", default=str(ROOT / "docs" / "CLAUDE_NEXT_PROMPT.md"))
    parser.add_argument("--copy", action="store_true")
    parser.add_argument("--force", action="store_true", help="Generate even if open questions are below threshold.")
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def extract_open_questions(text: str) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("|---"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 4:
            continue
        idx, area, question, status = cells[:4]
        if idx.isdigit() and status.lower() == "open":
            rows.append((idx, area, question))
    return rows


def read_optional(path: Path, limit: int = 6000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) > limit:
        return text[:limit] + "\n...(truncated)"
    return text


def build_prompt(questions: list[tuple[str, str, str]]) -> str:
    question_lines = "\n".join(f"{n}. [{area}] {q}" for n, area, q in questions)
    project_state = read_optional(ROOT / "docs" / "PROJECT_STATE.md")
    dashboard = read_optional(ROOT / "docs" / "PROJECT_DASHBOARD.md")
    decisions = read_optional(ROOT / "docs" / "DECISIONS.md")
    entity_packet = read_optional(ROOT / "results" / "v06_entity_rule_review_packet.md")
    asset_fix_plan = read_optional(ROOT / "results" / "v06_asset_attribution_fix_plan.md")
    return f"""# Claude Consultation Prompt

You are an external project manager and architecture reviewer for this project.
Give direct, critical, and practical feedback.

Project: Crypto Event Intelligence

Goal:
Convert Web3/crypto news into structured event intelligence, filter low-value items,
audit time/price quality, and produce human-reviewable high-value candidates.
No trading advice and no auto-order execution.

Please focus on:
- Whether the product direction is correct
- Which event types should be in the main workflow
- Which categories should be split into separate channels/rules
- Which rules create systemic misclassification
- What should be solved now vs later
- Any major architecture gaps

## Project State

```text
{project_state}
```

## Dashboard

```text
{dashboard}
```

## Decisions

```text
{decisions}
```

## Current Attribution Review Packet

```text
{entity_packet}
```

## Current Asset Attribution Fix Plan

```text
{asset_fix_plan}
```

## Questions

{question_lines}

Please output:
1. The 3 assumptions you disagree with most.
2. The 5 highest-priority actions now.
3. Concrete recommendation per question.
4. Which questions are not worth solving now.
5. Which data/manual-label assets are most critical.
"""


def copy_to_clipboard(text: str) -> None:
    subprocess.run("clip", input=text, text=True, check=True)


def main() -> int:
    args = parse_args()
    backlog_path = normalize_path(args.backlog)
    output_path = normalize_path(args.output)
    if not backlog_path.exists():
        print(f"backlog not found: {backlog_path}")
        return 1

    backlog_text = backlog_path.read_text(encoding="utf-8", errors="replace")
    questions = extract_open_questions(backlog_text)
    if len(questions) < THRESHOLD and not args.force:
        print(f"open questions: {len(questions)}/{THRESHOLD}; not generating Claude prompt yet")
        return 0

    prompt = build_prompt(questions)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(prompt, encoding="utf-8")
    print(f"wrote Claude prompt to {output_path}")
    if args.copy:
        copy_to_clipboard(prompt)
        print("copied Claude prompt to clipboard")
    return 0


if __name__ == "__main__":
    sys.exit(main())
