import argparse
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mark currently open Claude backlog questions as asked.")
    parser.add_argument("--backlog", default=str(ROOT / "docs" / "CLAUDE_QUESTION_BACKLOG.md"))
    parser.add_argument("--response", default="")
    parser.add_argument("--batch-id", default="")
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def mark_lines(text: str, batch_id: str) -> tuple[str, int]:
    marked_count = 0
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("|---"):
            lines.append(line)
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 4:
            lines.append(line)
            continue
        idx, area, question, status = cells[:4]
        if idx.isdigit() and status.lower() == "open":
            lines.append(f"| {idx} | {area} | {question} | asked:{batch_id} |")
            marked_count += 1
        else:
            lines.append(line)

    output = "\n".join(lines)
    output = re.sub(r"## Current Count: \d+ / 20", "## Current Count: 0 / 20", output)
    return output + ("\n" if text.endswith("\n") else ""), marked_count


def append_history(text: str, batch_id: str, response: str, marked_count: int) -> str:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC+8")
    section = "## Consultation History"
    row = f"| {stamp} | {batch_id} | {marked_count} | {response or '(not recorded)'} |"
    table_header = "| asked_at | batch_id | question_count | response |\n|---|---|---:|---|"
    if section not in text:
        return text.rstrip() + f"\n\n{section}\n\n{table_header}\n{row}\n"
    return text.rstrip() + f"\n{row}\n"


def main() -> int:
    args = parse_args()
    backlog_path = normalize_path(args.backlog)
    if not backlog_path.exists():
        print(f"backlog not found: {backlog_path}")
        return 1

    batch_id = args.batch_id.strip() or datetime.now().strftime("%Y%m%d_%H%M%S")
    response = args.response
    if response:
        try:
            response = str(normalize_path(response).relative_to(ROOT))
        except ValueError:
            response = str(normalize_path(response))

    text = backlog_path.read_text(encoding="utf-8", errors="replace")
    marked_text, marked_count = mark_lines(text, batch_id)
    if marked_count:
        marked_text = append_history(marked_text, batch_id, response, marked_count)
    backlog_path.write_text(marked_text, encoding="utf-8")
    print(f"marked_open_questions={marked_count}")
    print(f"batch_id={batch_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
